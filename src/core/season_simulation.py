"""Monte Carlo simulation of the remaining season, used to seed the CFP bracket.

The projected playoff bracket used to be seeded from *today's* ratings: the
highest-rated team in each conference was called its champion, and the field was
the top 12 by rating. In Week 1 that is a preseason-ratings bracket wearing a
playoff costume — it knows nothing about who still has to play whom.

This module plays the rest of the schedule out thousands of times instead. Each
run samples every remaining game from the same logistic win probability the
prediction endpoint uses, feeds the result back through the ELO update so
ratings drift across the simulated season, synthesizes a conference
championship game for every eligible league, and selects a CFP field. Counting
across runs turns that into playoff bid odds, conference title odds and an
average seed per team.

Why the loop is written on plain lists rather than the ORM:

    ``RankingService.process_game`` mutates Team rows, marks the game processed
    and commits. It also refuses any game flagged ``excluded_from_rankings``,
    which every unplayed future game is. None of that is usable here, so the ELO
    arithmetic is mirrored on in-memory arrays. The shared constants and helpers
    (:func:`RankingService.get_k_factor`, ``calculate_mov_multiplier``,
    ``get_conference_multiplier``) are imported rather than re-derived, so the
    simulated update tracks the real one.

Simplifications, all deliberate:

    * Games against FCS opponents are skipped entirely. That matches production,
      where FCS games are excluded from rankings and therefore never touch ELO
      or the displayed win/loss record.
    * Conference championship participants are the top two by conference record.
      The Team model carries no division field, and post-2023 realignment most
      conferences seed their title game exactly this way.
    * Game outcomes are independent. No injuries, weather, or rivalry effects.
"""

import json
import logging
import math
import random
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.core.ranking_service import (
    FIELD_SIZE,
    MIN_CONFERENCE_SIZE,
    RankingService,
    _INDEPENDENT_CONFS,
    blend_rating,
    conference_sizes,
    efficiency_rating,
    efficiency_scale,
    run_bracket,
    select_cfp_field,
)
from src.models.models import ConferenceType, Game, PlayoffSimulation, Season, Team

logger = logging.getLogger(__name__)

# Points of final margin implied by one ELO point. Mirrors the prediction
# formula in _calculate_game_prediction: (rating_diff / 100) * 3.5 per team,
# so 7 points of margin per 100 ELO.
MARGIN_PER_ELO = 0.07

# Spread of actual results around that expectation. ~16 points is the residual
# scale of college football finals against a rating-implied line.
# ponytail: a single global sigma, not a per-team or pace-aware one. Revisit if
# the simulated ELO spread drifts away from the real end-of-season spread.
MARGIN_SIGMA = 16.0

# Conference championship games are played the week after the regular season.
CHAMPIONSHIP_WEEK = 14

DEFAULT_RUNS = 10_000


@dataclass
class SimInputs:
    """Everything the simulation loop needs, flattened to index-addressed lists.

    Teams are addressed by a dense index (0..n-1), not by database id, so the
    inner loop works on plain list lookups.
    """

    season: int
    through_week: int
    team_ids: List[int]
    names: List[str]
    tiers: List[str]  # "P5" / "G5"
    conf_names: List[Optional[str]]
    base_elo: List[float]  # pure ELO, as stored on teams.elo_rating
    eff: List[Optional[float]]  # efficiency rating on the ELO scale, or None
    wins: List[int]  # already banked this season
    losses: List[int]
    conf_wins: List[int]
    conf_losses: List[int]
    games: List[Tuple[int, int, int, bool, bool]]  # home, away, week, neutral, is_conference
    conf_members: Dict[str, List[int]] = dc_field(default_factory=dict)

    @property
    def n_teams(self) -> int:
        return len(self.team_ids)


def load_sim_inputs(db: Session, season: int) -> SimInputs:
    """Read the FBS teams, their banked records and the unplayed schedule.

    The only database work the simulation does. Everything after this is pure
    arithmetic on lists.
    """
    teams = db.query(Team).filter(Team.is_fcs == False).all()  # noqa: E712
    teams.sort(key=lambda t: t.id)
    idx = {t.id: i for i, t in enumerate(teams)}

    scale = efficiency_scale(db)
    eff = [
        efficiency_rating(t, scale) if scale is not None else None
        for t in teams
    ]

    season_obj = db.query(Season).filter(Season.year == season).first()
    through_week = season_obj.current_week if season_obj else 0

    conf_members: Dict[str, List[int]] = {}
    for i, t in enumerate(teams):
        if t.conference_name in _INDEPENDENT_CONFS:
            continue
        conf_members.setdefault(t.conference_name, []).append(i)

    sizes = conference_sizes(db)
    conf_members = {
        name: members
        for name, members in conf_members.items()
        if sizes.get(name, 0) >= MIN_CONFERENCE_SIZE and len(members) >= 2
    }

    n = len(teams)
    wins, losses = [0] * n, [0] * n
    conf_wins, conf_losses = [0] * n, [0] * n
    games: List[Tuple[int, int, int, bool, bool]] = []

    for g in db.query(Game).filter(Game.season == season).order_by(Game.week).all():
        h, a = idx.get(g.home_team_id), idx.get(g.away_team_id)
        if h is None or a is None:
            continue  # FCS opponent: never affects ELO or the displayed record
        same_conf = (
            teams[h].conference_name == teams[a].conference_name
            and teams[h].conference_name not in _INDEPENDENT_CONFS
        )
        if g.is_processed:
            hi, lo = (h, a) if g.home_score > g.away_score else (a, h)
            wins[hi] += 1
            losses[lo] += 1
            if same_conf:
                conf_wins[hi] += 1
                conf_losses[lo] += 1
        else:
            games.append((h, a, g.week, bool(g.is_neutral_site), same_conf))

    return SimInputs(
        season=season,
        through_week=through_week,
        team_ids=[t.id for t in teams],
        names=[t.name for t in teams],
        tiers=[
            "G5" if t.conference == ConferenceType.GROUP_5 else "P5" for t in teams
        ],
        conf_names=[t.conference_name for t in teams],
        base_elo=[t.elo_rating for t in teams],
        eff=eff,
        wins=wins,
        losses=losses,
        conf_wins=conf_wins,
        conf_losses=conf_losses,
        games=games,
        conf_members=conf_members,
    )


def _k_factor(week: int) -> float:
    """Progressive K-factor, straight from RankingService (64 → 48 → 32)."""
    if week <= 4:
        return RankingService.K_FACTOR_EARLY
    if week <= 8:
        return RankingService.K_FACTOR_MID
    return RankingService.K_FACTOR_LATE


def _conf_multipliers(winner_tier: str, loser_tier: str) -> Tuple[float, float]:
    """Cross-tier ELO multipliers. Mirrors RankingService.get_conference_multiplier.

    FCS branches are omitted because FCS games never reach the simulation.
    """
    if winner_tier == "P5" and loser_tier == "G5":
        return (0.9, 1.1)
    if winner_tier == "G5" and loser_tier == "P5":
        return (1.1, 0.9)
    return (1.0, 1.0)


def _play(sim, h: int, a: int, week: int, neutral: bool, is_conf: bool, rng) -> int:
    """Sample one game, apply the ELO update in place, return the winner's index.

    `sim` is the mutable per-run state produced by :func:`_new_run_state`.
    """
    elo = sim["elo"]
    home_rating = elo[h] + (0 if neutral else RankingService.HOME_FIELD_ADVANTAGE)
    away_rating = elo[a]
    home_wp = 1.0 / (1.0 + 10 ** ((away_rating - home_rating) / RankingService.RATING_SCALE))

    home_won = rng.random() < home_wp
    winner, loser = (h, a) if home_won else (a, h)
    winner_expected = home_wp if home_won else 1.0 - home_wp

    # Margin is sampled conditional on who actually won: when the favorite wins
    # it is centered on the rating-implied margin, when the underdog wins it is
    # centered on zero. Upsets therefore tend to be close games, which is both
    # true and what keeps the MOV multiplier from rewarding flukes.
    edge = abs(home_rating - away_rating) * MARGIN_PER_ELO
    favorite_won = home_won == (home_rating >= away_rating)
    margin = abs(rng.gauss(edge if favorite_won else 0.0, MARGIN_SIGMA))
    mov = min(math.log(max(margin, 1.0) + 1.0), RankingService.MAX_MOV_MULTIPLIER)

    k = _k_factor(week)
    winner_mult, loser_mult = _conf_multipliers(sim["tiers"][winner], sim["tiers"][loser])
    elo[winner] += k * (1.0 - winner_expected) * mov * winner_mult
    elo[loser] += k * (0.0 - (1.0 - winner_expected)) * mov * loser_mult

    sim["wins"][winner] += 1
    sim["losses"][loser] += 1
    if is_conf:
        sim["conf_wins"][winner] += 1
        sim["conf_losses"][loser] += 1
    return winner


def _new_run_state(inputs: SimInputs) -> dict:
    return {
        "elo": list(inputs.base_elo),
        "wins": list(inputs.wins),
        "losses": list(inputs.losses),
        "conf_wins": list(inputs.conf_wins),
        "conf_losses": list(inputs.conf_losses),
        "tiers": inputs.tiers,
    }


def _conference_champions(inputs: SimInputs, sim: dict, rng) -> List[int]:
    """Synthesize a title game per eligible conference; return winners' indices.

    The two participants are the best two by conference winning percentage,
    rating as the tiebreak. The 2026 schedule contains no championship games at
    all — CFBD only publishes them in weeks 14-15, once the matchups are known.
    """
    champions = []
    for members in inputs.conf_members.values():
        ranked = sorted(
            members,
            key=lambda i: (
                sim["conf_wins"][i] / max(sim["conf_wins"][i] + sim["conf_losses"][i], 1),
                sim["elo"][i],
            ),
            reverse=True,
        )
        one, two = ranked[0], ranked[1]
        champions.append(_play(sim, one, two, CHAMPIONSHIP_WEEK, True, True, rng))
    return champions


def _final_ratings(inputs: SimInputs, sim: dict) -> List[float]:
    """Blend each team's simulated ELO with its (fixed) efficiency rating.

    Efficiency is held at its current value: adjusted PPA cannot be re-measured
    for games that never happened. `week=None` skips the early-season gate,
    since a simulated season is by definition complete.
    """
    elo = sim["elo"]
    return [blend_rating(elo[i], inputs.eff[i], week=None) for i in range(inputs.n_teams)]


def simulate_season(
    inputs: SimInputs, runs: int = DEFAULT_RUNS, seed: Optional[int] = None
) -> dict:
    """Run the season `runs` times and aggregate per-team outcomes.

    Returns a dict keyed by team index with bid counts, seed sums, conference
    title counts, national title counts and summed final ratings — raw counters,
    converted to percentages by :func:`build_projection`.
    """
    rng = random.Random(seed)
    n = inputs.n_teams

    bid_count = [0] * n
    seed_sum = [0] * n
    conf_title_count = [0] * n
    title_count = [0] * n
    rating_sum = [0.0] * n
    win_sum = [0] * n

    by_index = {}
    team_dicts = [
        {
            "team_id": inputs.team_ids[i],
            "team_name": inputs.names[i],
            "conference": inputs.tiers[i],
            "conference_name": inputs.conf_names[i],
            "elo_rating": 0.0,
            "_i": i,
        }
        for i in range(n)
    ]
    for d in team_dicts:
        by_index[d["team_id"]] = d["_i"]

    for _ in range(runs):
        sim = _new_run_state(inputs)
        for h, a, week, neutral, is_conf in inputs.games:
            _play(sim, h, a, week, neutral, is_conf, rng)

        champion_idx = _conference_champions(inputs, sim, rng)
        finals = _final_ratings(inputs, sim)

        for d in team_dicts:
            d["elo_rating"] = finals[d["_i"]]
        ranked = sorted(team_dicts, key=lambda d: d["elo_rating"], reverse=True)
        champs = [team_dicts[i] for i in champion_idx]

        seeded = select_cfp_field(ranked, champs)
        bracket = run_bracket(seeded, rng)

        for i in champion_idx:
            conf_title_count[i] += 1
        for t in seeded:
            i = by_index[t["team_id"]]
            bid_count[i] += 1
            seed_sum[i] += t["seed"]
        title_count[by_index[bracket["champion"]["team_id"]]] += 1

        for i in range(n):
            rating_sum[i] += finals[i]
            win_sum[i] += sim["wins"][i]

    return {
        "runs": runs,
        "bid_count": bid_count,
        "seed_sum": seed_sum,
        "conf_title_count": conf_title_count,
        "title_count": title_count,
        "rating_sum": rating_sum,
        "win_sum": win_sum,
    }


# Teams outside the projected field that are still worth showing as "on the bubble".
BUBBLE_SIZE = 13


def build_projection(
    db: Session, season: int, runs: int = DEFAULT_RUNS, seed: Optional[int] = None
) -> dict:
    """Simulate the season and return a playoff projection payload.

    The bracket rendered is the *consensus* field, not a single simulated one:
    the twelve teams with the highest playoff-bid probability, ordered by their
    average seed, advanced on their mean final rating. A literal modal bracket is
    not usable — across ten thousand runs no exact twelve-team field recurs often
    enough to be meaningful. The consensus field is stable across reruns and is
    what every published playoff projection shows.

    The payload is a superset of :func:`project_playoff_bracket`'s, so the board
    renders it unchanged and can layer the probabilities on top.
    """
    inputs = load_sim_inputs(db, season)
    if inputs.n_teams < FIELD_SIZE:
        return {
            "season": season, "field": [], "first_round": [], "quarterfinals": [],
            "semifinals": [], "final": None, "champion": None, "bubble": [],
            "runs": 0, "method": "monte_carlo", "through_week": inputs.through_week,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    agg = simulate_season(inputs, runs=runs, seed=seed)
    r = float(agg["runs"])

    stats = []
    for i in range(inputs.n_teams):
        bids = agg["bid_count"][i]
        stats.append({
            "team_id": inputs.team_ids[i],
            "team_name": inputs.names[i],
            "conference": inputs.tiers[i],
            "conference_name": inputs.conf_names[i],
            # Mean final blended rating: what the bracket is advanced on.
            "elo_rating": round(agg["rating_sum"][i] / r, 2),
            "bid_pct": round(100.0 * bids / r, 1),
            "avg_seed": round(agg["seed_sum"][i] / bids, 1) if bids else None,
            "conf_title_pct": round(100.0 * agg["conf_title_count"][i] / r, 1),
            "title_pct": round(100.0 * agg["title_count"][i] / r, 1),
            "proj_wins": round(agg["win_sum"][i] / r, 1),
            "_i": i,
        })

    # Each conference's most frequent champion stands as its projected champion.
    by_team_id = {st["team_id"]: st for st in stats}
    champions = [
        by_team_id[inputs.team_ids[max(members, key=lambda i: agg["conf_title_count"][i])]]
        for members in inputs.conf_members.values()
    ]

    # Consensus field. Selecting the plain top twelve by bid probability would
    # produce an illegal bracket: bid probability is a marginal, so the five
    # auto-bids every individual run honours do not survive the averaging. So the
    # field goes through the same selection rule the runs use, with bid
    # probability standing in as the ordering signal — that keeps the displayed
    # bracket a field the CFP could actually produce.
    for st in stats:
        st["elo_rating"], st["mean_rating"] = st["bid_pct"], st["elo_rating"]
    ranked_by_bid = sorted(stats, key=lambda st: -st["bid_pct"])
    selected = select_cfp_field(ranked_by_bid, champions)
    for st in stats:
        st["elo_rating"] = st.pop("mean_rating")

    # Seeds come from the average seed each team actually drew, and the bracket
    # is advanced on mean final rating rather than on bid probability.
    stat_by_id = {st["team_id"]: st for st in stats}
    selected.sort(key=lambda t: stat_by_id[t["team_id"]]["avg_seed"] or FIELD_SIZE + 1)

    seeded = []
    for pos, t in enumerate(selected):
        st = stat_by_id[t["team_id"]]
        seeded.append({
            "seed": pos + 1,
            "team_id": st["team_id"],
            "name": st["team_name"],
            "elo": st["elo_rating"],
            "conference_name": st["conference_name"],
            "is_champ": t["is_champ"],
            "auto_bid": t["auto_bid"],
            "bid_pct": st["bid_pct"],
            "avg_seed": st["avg_seed"],
            "conf_title_pct": st["conf_title_pct"],
            "title_pct": st["title_pct"],
            "proj_wins": st["proj_wins"],
        })

    in_field = {t["team_id"] for t in seeded}
    consensus = [st for st in ranked_by_bid if st["team_id"] not in in_field]

    bubble = [
        {"team_id": s["team_id"], "name": s["team_name"], "elo": s["elo_rating"],
         "conference_name": s["conference_name"], "bid_pct": s["bid_pct"],
         "avg_seed": s["avg_seed"], "conf_title_pct": s["conf_title_pct"],
         "title_pct": s["title_pct"], "proj_wins": s["proj_wins"]}
        for s in consensus[:BUBBLE_SIZE]
    ]

    return {
        "season": season,
        "field": seeded,
        "bubble": bubble,
        "runs": agg["runs"],
        "method": "monte_carlo",
        "through_week": inputs.through_week,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **run_bracket(seeded),
    }


# ── Cache: the simulation is too slow to run inside a request ────────────────


def refresh_projection(
    db: Session, season: int, runs: int = DEFAULT_RUNS, seed: Optional[int] = None
) -> dict:
    """Simulate the season and store the result, replacing any row for this week.

    Called by the weekly import once new results have landed, and by
    ``scripts/simulate_season.py`` on demand.
    """
    projection = build_projection(db, season, runs=runs, seed=seed)
    week = projection["through_week"]

    db.query(PlayoffSimulation).filter(
        PlayoffSimulation.season == season, PlayoffSimulation.week == week
    ).delete()
    db.add(
        PlayoffSimulation(
            season=season,
            week=week,
            runs=projection["runs"],
            payload=json.dumps(projection),
        )
    )
    db.commit()
    logger.info(
        "Stored playoff simulation for %s week %s (%s runs)", season, week, projection["runs"]
    )
    return projection


def load_cached_projection(db: Session, season: int, week: Optional[int] = None) -> Optional[dict]:
    """Return the stored projection for a season/week, or None if there is none.

    With no `week`, returns the most recently simulated week for that season.
    """
    query = db.query(PlayoffSimulation).filter(PlayoffSimulation.season == season)
    if week is not None:
        query = query.filter(PlayoffSimulation.week == week)
    row = query.order_by(PlayoffSimulation.week.desc()).first()
    return json.loads(row.payload) if row else None
