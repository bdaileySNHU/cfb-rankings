"""Tests for the Monte Carlo season simulation that seeds the CFP bracket."""

import math
import random

import pytest

from src.core import season_simulation as ss
from src.core.ranking_service import (
    FIELD_SIZE,
    CHAMPION_AUTO_BIDS,
    RankingService,
    select_cfp_field,
)

CONFERENCES = {
    "SEC": "P5",
    "Big Ten": "P5",
    "Big 12": "P5",
    "ACC": "P5",
    "American Athletic": "G5",
    "Mountain West": "G5",
}
TEAMS_PER_CONF = 6


def build_inputs(elo_of=None, games_per_team=8):
    """A synthetic league: six conferences of six, each playing a conference schedule.

    Built directly rather than through the database so the tests exercise the
    simulation itself and not the loader.
    """
    names, tiers, conf_names, base_elo = [], [], [], []
    conf_members = {}
    for conf, tier in CONFERENCES.items():
        conf_members[conf] = []
        for j in range(TEAMS_PER_CONF):
            i = len(names)
            name = f"{conf} {j}"
            names.append(name)
            tiers.append(tier)
            conf_names.append(conf)
            base_elo.append(elo_of(name, conf, j) if elo_of else 1500.0)
            conf_members[conf].append(i)

    # Round-robin inside each conference, alternating who is at home.
    games = []
    for members in conf_members.values():
        for a_pos, a in enumerate(members):
            for b in members[a_pos + 1:]:
                games.append((a, b, 5, False, True))
                games.append((b, a, 9, False, True))

    n = len(names)
    return ss.SimInputs(
        season=2026,
        through_week=1,
        team_ids=list(range(1, n + 1)),
        names=names,
        tiers=tiers,
        conf_names=conf_names,
        base_elo=base_elo,
        eff=[None] * n,
        wins=[0] * n,
        losses=[0] * n,
        conf_wins=[0] * n,
        conf_losses=[0] * n,
        games=games,
        conf_members=conf_members,
    )


class TestEloStep:
    """The in-memory ELO update must track RankingService.process_game."""

    def test_zero_sum_within_a_tier(self):
        inputs = build_inputs()
        sim = ss._new_run_state(inputs)
        before = sum(sim["elo"])
        ss._play(sim, 0, 1, 5, False, True, random.Random(1))
        assert sum(sim["elo"]) == pytest.approx(before)

    def test_cross_tier_upset_is_not_zero_sum(self):
        """A G5 win over a P5 pays 1.1x while the P5 only loses 0.9x."""
        inputs = build_inputs()
        sim = ss._new_run_state(inputs)
        g5 = inputs.conf_names.index("American Athletic")
        p5 = 0
        assert inputs.tiers[g5] == "G5" and inputs.tiers[p5] == "P5"

        before = sim["elo"][g5] + sim["elo"][p5]
        rng = random.Random(0)
        while ss._play(sim, p5, g5, 5, True, False, rng) != g5:
            sim = ss._new_run_state(inputs)
        assert sim["elo"][g5] + sim["elo"][p5] > before

    def test_matches_process_game_arithmetic(self):
        """Hand-compute one game and check the sim lands on the same numbers."""
        inputs = build_inputs(elo_of=lambda name, conf, j: 1600.0 if j == 0 else 1400.0)
        sim = ss._new_run_state(inputs)
        home, away = 0, 1  # 1600 at home vs 1400

        home_rating = 1600.0 + RankingService.HOME_FIELD_ADVANTAGE
        expected = 1 / (1 + 10 ** ((1400.0 - home_rating) / 400))

        class FixedRNG:
            """Home team wins; margin lands exactly on the rating-implied edge."""

            def random(self):
                return 0.0  # always below the win probability → home wins

            def gauss(self, mu, sigma):
                return mu

        ss._play(sim, home, away, 3, False, True, FixedRNG())  # week 3 → K=64

        edge = (home_rating - 1400.0) * ss.MARGIN_PER_ELO
        mov = min(math.log(edge + 1.0), RankingService.MAX_MOV_MULTIPLIER)
        change = RankingService.K_FACTOR_EARLY * (1 - expected) * mov
        assert sim["elo"][home] == pytest.approx(1600.0 + change)
        assert sim["elo"][away] == pytest.approx(1400.0 - change)

    def test_k_factor_follows_the_season(self):
        assert ss._k_factor(1) == RankingService.K_FACTOR_EARLY
        assert ss._k_factor(4) == RankingService.K_FACTOR_EARLY
        assert ss._k_factor(5) == RankingService.K_FACTOR_MID
        assert ss._k_factor(8) == RankingService.K_FACTOR_MID
        assert ss._k_factor(9) == RankingService.K_FACTOR_LATE
        assert ss._k_factor(14) == RankingService.K_FACTOR_LATE

    def test_records_advance(self):
        inputs = build_inputs()
        sim = ss._new_run_state(inputs)
        winner = ss._play(sim, 0, 1, 5, False, True, random.Random(2))
        loser = 1 if winner == 0 else 0
        assert sim["wins"][winner] == 1 and sim["conf_wins"][winner] == 1
        assert sim["losses"][loser] == 1 and sim["conf_losses"][loser] == 1

    def test_non_conference_game_leaves_conference_record_alone(self):
        inputs = build_inputs()
        sim = ss._new_run_state(inputs)
        ss._play(sim, 0, 7, 5, True, False, random.Random(3))
        assert sum(sim["conf_wins"]) == 0 and sum(sim["conf_losses"]) == 0
        assert sum(sim["wins"]) == 1


class TestConferenceChampions:
    def test_one_champion_per_eligible_conference(self):
        inputs = build_inputs()
        sim = ss._new_run_state(inputs)
        rng = random.Random(4)
        for g in inputs.games:
            ss._play(sim, *g, rng)
        champions = ss._conference_champions(inputs, sim, rng)

        assert len(champions) == len(CONFERENCES)
        assert len(set(champions)) == len(CONFERENCES)
        for champ in champions:
            assert champ in inputs.conf_members[inputs.conf_names[champ]]

    def test_undersized_conference_gets_no_champion(self):
        """A stale two-team conference must not mint an auto-bid."""
        inputs = build_inputs()
        inputs.conf_members.pop("Mountain West")
        sim = ss._new_run_state(inputs)
        champions = ss._conference_champions(inputs, sim, random.Random(5))
        assert len(champions) == len(CONFERENCES) - 1
        assert all(inputs.conf_names[c] != "Mountain West" for c in champions)

    def test_title_game_participants_lead_the_conference(self):
        """The two teams playing for the title are the top two by conference record."""
        inputs = build_inputs()
        sim = ss._new_run_state(inputs)
        rng = random.Random(6)
        for g in inputs.games:
            ss._play(sim, *g, rng)

        members = inputs.conf_members["SEC"]
        pre = {i: (sim["conf_wins"][i], sim["conf_losses"][i]) for i in members}
        champion = [c for c in ss._conference_champions(inputs, sim, rng)
                    if inputs.conf_names[c] == "SEC"][0]

        best_two = sorted(
            members,
            key=lambda i: (pre[i][0] / max(pre[i][0] + pre[i][1], 1), sim["elo"][i]),
            reverse=True,
        )[:2]
        assert champion in best_two


class TestSelectCfpField:
    """The selection rule shared by the simulation and the deterministic bracket."""

    @staticmethod
    def make_rankings(n=40):
        rankings = []
        for i in range(n):
            conf = list(CONFERENCES)[i % len(CONFERENCES)]
            rankings.append({
                "team_id": i + 1,
                "team_name": f"Team {i}",
                "conference": CONFERENCES[conf],
                "conference_name": conf,
                "elo_rating": 1900.0 - i * 10,
            })
        return rankings

    def test_field_is_exactly_twelve_uniquely_seeded(self):
        rankings = self.make_rankings()
        champs = rankings[:len(CONFERENCES)]
        field = select_cfp_field(rankings, champs)
        assert len(field) == FIELD_SIZE
        assert [t["seed"] for t in field] == list(range(1, FIELD_SIZE + 1))
        assert len({t["team_id"] for t in field}) == FIELD_SIZE

    def test_seeded_strictly_by_rating(self):
        rankings = self.make_rankings()
        field = select_cfp_field(rankings, rankings[:len(CONFERENCES)])
        ratings = [t["elo"] for t in field]
        assert ratings == sorted(ratings, reverse=True)

    def test_auto_bid_count(self):
        rankings = self.make_rankings()
        champs = rankings[:len(CONFERENCES)]
        field = select_cfp_field(rankings, champs)
        assert sum(t["auto_bid"] for t in field) == CHAMPION_AUTO_BIDS

    def _tiny_champ(self, tier="G5"):
        return {
            "team_id": 999,
            "team_name": "Tiny Champ",
            "conference": tier,
            "conference_name": "Mountain West",
            "elo_rating": 1200.0,  # nowhere near the at-large cut
        }

    def test_weak_champion_rides_an_auto_bid_when_champions_are_scarce(self):
        """Only five champions exist, so even a terrible one is a top-5 champion."""
        rankings = self.make_rankings(n=60)
        tiny = self._tiny_champ()
        rankings.append(tiny)
        power = [r for r in rankings if r["conference"] == "P5"][:4]

        field = select_cfp_field(rankings, power + [tiny])

        assert next(t for t in field if t["team_id"] == 999)["auto_bid"] is True

    def test_sixth_ranked_champion_is_shut_out(self):
        """Auto-bids go to the five best champions, not one per tier.

        The old rule reserved a slot for the highest-rated G5 champion, which
        would drag this team in over a better-rated P5 champion. The real CFP
        rule has no reserved slot: with five P5 conferences chasing five spots,
        a G5 champion can miss entirely.
        """
        rankings = self.make_rankings(n=60)
        tiny = self._tiny_champ()
        rankings.append(tiny)
        power = [r for r in rankings if r["conference"] == "P5"][:5]
        assert len(power) == 5, "need five P5 champions to crowd the G5 out"

        field = select_cfp_field(rankings, power + [tiny])

        auto_ids = {t["team_id"] for t in field if t["auto_bid"]}
        assert 999 not in auto_ids
        assert auto_ids == {c["team_id"] for c in power}
        assert sum(t["auto_bid"] for t in field) == CHAMPION_AUTO_BIDS


class TestSimulateSeason:
    def test_deterministic_for_a_fixed_seed(self):
        inputs = build_inputs()
        a = ss.simulate_season(inputs, runs=25, seed=99)
        b = ss.simulate_season(inputs, runs=25, seed=99)
        assert a == b

    def test_different_seeds_diverge(self):
        inputs = build_inputs()
        a = ss.simulate_season(inputs, runs=25, seed=1)
        b = ss.simulate_season(inputs, runs=25, seed=2)
        assert a["bid_count"] != b["bid_count"]

    def test_every_run_awards_exactly_twelve_bids(self):
        runs = 40
        inputs = build_inputs()
        agg = ss.simulate_season(inputs, runs=runs, seed=11)
        assert sum(agg["bid_count"]) == FIELD_SIZE * runs

    def test_every_run_crowns_one_champion_per_conference(self):
        runs = 40
        inputs = build_inputs()
        agg = ss.simulate_season(inputs, runs=runs, seed=12)
        assert sum(agg["conf_title_count"]) == len(CONFERENCES) * runs
        assert sum(agg["title_count"]) == runs

    def test_stronger_teams_earn_more_bids(self):
        """A clearly better team should reach the field far more often."""
        inputs = build_inputs(
            elo_of=lambda name, conf, j: 1900.0 if j == 0 else 1350.0
        )
        agg = ss.simulate_season(inputs, runs=120, seed=13)
        strong = [i for i, n in enumerate(inputs.names) if n.endswith(" 0")]
        weak = [i for i in range(len(inputs.names)) if i not in strong]
        assert min(agg["bid_count"][i] for i in strong) > max(agg["bid_count"][i] for i in weak)

    def test_records_never_exceed_games_played(self):
        inputs = build_inputs()
        runs = 10
        agg = ss.simulate_season(inputs, runs=runs, seed=14)
        games_each = 2 * (TEAMS_PER_CONF - 1)
        # Every team also plays its conference title game in the runs it reaches one.
        assert max(agg["win_sum"]) <= (games_each + 1) * runs


class TestBuildProjection:
    """End-to-end payload shape, exercised against the real database session."""

    def test_payload_is_a_legal_field(self, db_session):
        from src.models.models import ConferenceType, Season, Team

        db_session.add(Season(year=2031, current_week=1, is_active=False))
        teams = []
        for conf, tier in CONFERENCES.items():
            for j in range(TEAMS_PER_CONF):
                t = Team(
                    name=f"{conf} {j}",
                    conference=(
                        ConferenceType.POWER_5 if tier == "P5" else ConferenceType.GROUP_5
                    ),
                    conference_name=conf,
                    is_fcs=False,
                    elo_rating=1500.0 + (TEAMS_PER_CONF - j) * 30,
                )
                teams.append(t)
                db_session.add(t)
        db_session.commit()

        projection = ss.build_projection(db_session, 2031, runs=30, seed=21)

        assert projection["method"] == "monte_carlo"
        assert projection["runs"] == 30
        assert len(projection["field"]) == FIELD_SIZE
        assert [t["seed"] for t in projection["field"]] == list(range(1, FIELD_SIZE + 1))
        assert sum(t["auto_bid"] for t in projection["field"]) == CHAMPION_AUTO_BIDS

        # Probabilities are present and sane.
        for t in projection["field"]:
            assert 0.0 <= t["bid_pct"] <= 100.0
            assert 0.0 <= t["conf_title_pct"] <= 100.0
            assert t["avg_seed"] is not None

        # The bubble is disjoint from the field.
        field_ids = {t["team_id"] for t in projection["field"]}
        assert not field_ids & {b["team_id"] for b in projection["bubble"]}

        # The bracket ran.
        assert len(projection["first_round"]) == 4
        assert len(projection["quarterfinals"]) == 4
        assert len(projection["semifinals"]) == 2
        assert projection["champion"]["team_id"] in field_ids

    def test_cache_round_trip(self, db_session):
        from src.models.models import ConferenceType, Season, Team

        db_session.add(Season(year=2032, current_week=3, is_active=False))
        for conf, tier in CONFERENCES.items():
            for j in range(TEAMS_PER_CONF):
                db_session.add(Team(
                    name=f"{conf} {j}",
                    conference=(
                        ConferenceType.POWER_5 if tier == "P5" else ConferenceType.GROUP_5
                    ),
                    conference_name=conf,
                    is_fcs=False,
                    elo_rating=1500.0 + (TEAMS_PER_CONF - j) * 30,
                ))
        db_session.commit()

        assert ss.load_cached_projection(db_session, 2032) is None
        stored = ss.refresh_projection(db_session, 2032, runs=20, seed=31)
        cached = ss.load_cached_projection(db_session, 2032)

        assert cached is not None
        assert cached["runs"] == stored["runs"] == 20
        assert cached["through_week"] == 3
        assert [t["team_id"] for t in cached["field"]] == [t["team_id"] for t in stored["field"]]

    def test_refresh_replaces_rather_than_duplicates(self, db_session):
        from src.models.models import ConferenceType, PlayoffSimulation, Season, Team

        db_session.add(Season(year=2033, current_week=2, is_active=False))
        for conf, tier in CONFERENCES.items():
            for j in range(TEAMS_PER_CONF):
                db_session.add(Team(
                    name=f"{conf} {j}",
                    conference=(
                        ConferenceType.POWER_5 if tier == "P5" else ConferenceType.GROUP_5
                    ),
                    conference_name=conf,
                    is_fcs=False,
                    elo_rating=1500.0,
                ))
        db_session.commit()

        ss.refresh_projection(db_session, 2033, runs=10, seed=1)
        ss.refresh_projection(db_session, 2033, runs=10, seed=2)
        rows = db_session.query(PlayoffSimulation).filter(
            PlayoffSimulation.season == 2033
        ).count()
        assert rows == 1


def test_every_run_awards_exactly_one_legal_field():
    """Bids, titles and conference crowns are conserved per run.

    This is the cheapest guard against an illegal field: if selection ever drops
    an auto-bid or double-counts a team, the per-run averages stop being whole
    numbers. A marginal probability like bid_pct cannot catch that on its own.
    """
    inputs = build_inputs()
    result = ss.simulate_season(inputs, runs=50, seed=99)
    runs = result["runs"]

    assert sum(result["bid_count"]) == FIELD_SIZE * runs
    assert sum(result["title_count"]) == runs
    assert sum(result["conf_title_count"]) == len(CONFERENCES) * runs
