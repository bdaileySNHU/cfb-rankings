#!/usr/bin/env python3
"""Backtest the EPIC-045 efficiency blend to tune EFFICIENCY_WEIGHT / EFFICIENCY_MIN_WEEK.

Replays a season week by week against a throwaway copy of the database. For each
week N it predicts every game using only information available before that week
was played — ELO from replaying weeks 1..N-1, efficiency from PPA through
week N-1 — then processes week N and moves on. No lookahead anywhere.

Efficiency source
-----------------
Production reads CFBD's opponent-adjusted ``/ppa/teams``, which only ever returns
*today's* season-to-date values; there is no way to ask it what a team looked like
in week 6 of a past season. So the backtest reconstructs week-by-week efficiency
from ``/ppa/games`` (one API call per season, cached to data/) as the running mean
of per-game net PPA.

That proxy was validated against CFBD's own adjusted numbers for 2025: the plain
running mean correlates **0.987** with ``/ppa/teams``, with near-identical spread
(sd 0.137 vs 0.132). Refitting CORE's opponent adjustment scored *worse* (0.94-0.98)
— at full season, FBS schedules balance out enough that the adjustment is a small
correction. Since the blend standardizes both signals to z-scores, only the
correlation matters, not the scale.

Known limitation: that 0.987 is a full-season comparison. There is no historical
CFBD snapshot to validate the proxy at week 6, and unbalanced early schedules are
exactly where opponent adjustment earns its keep — so treat early-week results as
softer evidence than late-week ones.

Usage:
    python3 scripts/backtest_efficiency_blend.py
    python3 scripts/backtest_efficiency_blend.py --seasons 2025 --weights 0 0.25 0.5
"""

import argparse
import json
import logging
import os
import shutil
import statistics
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.core import ranking_service as rs  # noqa: E402
from src.core.ranking_service import RankingService, blend_rating  # noqa: E402
from src.integrations.cfbd_client import CFBDClient  # noqa: E402
from src.models.models import Game, Team  # noqa: E402

# Regular season only. /ppa/games numbers postseason rounds on its own scheme,
# which does not line up with the games table's weeks 16-19.
MAX_WEEK = 15

DEFAULT_WEIGHTS = [0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
DEFAULT_MIN_WEEKS = [4, 6, 8, 10]

# Mirrors _calculate_game_prediction; see that function for the derivation.
HOME_FIELD_ADVANTAGE = 65
RATING_SCALE = 400
POINTS_PER_100_ELO = 7.0


def load_ppa_games(year: int, cache_dir: Path, exclude_garbage_time: bool = False) -> list:
    """Fetch /ppa/games for a season, caching so re-runs cost no API calls.

    ``exclude_garbage_time`` asks CFBD to drop plays its garbage-time classifier
    flags, and caches to a separate file so both variants can coexist.
    """
    suffix = "_nogarbage" if exclude_garbage_time else ""
    cache = cache_dir / f"ppa_games_{year}{suffix}.json"
    if cache.exists():
        print(f"  using cached {cache.relative_to(project_root)}")
        return json.loads(cache.read_text())

    api_key = os.getenv("CFBD_API_KEY")
    if not api_key:
        sys.exit("ERROR: CFBD_API_KEY not set and no cache available")

    print(f"  fetching /ppa/games for {year} (1 API call)...")
    params = {"year": year}
    if exclude_garbage_time:
        params["excludeGarbageTime"] = "true"
    rows = CFBDClient(api_key)._get("/ppa/games", params=params)
    if not rows:
        sys.exit(f"ERROR: no PPA game data returned for {year}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows))
    print(f"  cached {len(rows)} rows to {cache.relative_to(project_root)}")
    return rows


def build_weekly_efficiency(ppa_rows: list) -> dict:
    """{week: {team: (mean_off_ppa, mean_def_ppa)}} using games strictly before `week`.

    FBS-vs-FBS only, matching what CORE counts.
    """
    fbs = {r["team"] for r in ppa_rows}
    by_week = defaultdict(list)
    for r in ppa_rows:
        if r["seasonType"] != "regular" or r["opponent"] not in fbs:
            continue
        off = (r.get("offense") or {}).get("overall")
        deff = (r.get("defense") or {}).get("overall")
        if off is None or deff is None:
            continue
        by_week[r["week"]].append((r["team"], off, deff))

    running = defaultdict(list)
    out = {}
    for week in range(1, MAX_WEEK + 2):
        # snapshot BEFORE folding in this week's games
        out[week] = {
            t: (statistics.fmean(o for o, _ in v), statistics.fmean(d for _, d in v))
            for t, v in running.items()
            if len(v) >= 2  # one game is noise, not a rating
        }
        for team, off, deff in by_week.get(week, []):
            running[team].append((off, deff))
    return out


def replay_season(db_path: Path, season: int, weekly_eff: dict) -> list:
    """Replay a season point-in-time, returning one record per predicted game.

    Each record holds the pure ELO and efficiency rating that were knowable before
    kickoff, so the weight sweep afterwards is pure arithmetic — the expensive
    replay happens once.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    session = sessionmaker(bind=engine)()
    service = RankingService(session)

    # Rewind: preseason ratings, and mark the season's games unplayed
    service.reset_season(season)
    session.query(Game).filter(Game.season == season).update({Game.is_processed: False})
    session.commit()

    weeks = sorted(
        w[0]
        for w in session.query(Game.week)
        .filter(Game.season == season, Game.week <= MAX_WEEK)
        .distinct()
        .all()
    )

    records = []
    for week in weeks:
        # Efficiency as known before this week kicked off
        eff_for_week = weekly_eff.get(week, {})
        for team in session.query(Team).all():
            vals = eff_for_week.get(team.name)
            team.offense_ppa, team.defense_ppa = vals if vals else (None, None)
        session.commit()

        scale = rs.efficiency_scale(session)

        games = (
            session.query(Game)
            .filter(
                Game.season == season,
                Game.week == week,
                Game.excluded_from_rankings == False,  # noqa: E712
            )
            .all()
        )

        for game in games:
            if game.home_score == 0 and game.away_score == 0:
                continue  # unplayed
            home, away = game.home_team, game.away_team
            if not home or not away:
                continue

            records.append(
                {
                    "week": week,
                    "neutral": bool(game.is_neutral_site),
                    "home_elo": home.elo_rating,
                    "away_elo": away.elo_rating,
                    "home_eff": rs.efficiency_rating(home, scale) if scale else None,
                    "away_eff": rs.efficiency_rating(away, scale) if scale else None,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                }
            )

        # Advance state past this week
        for game in games:
            if game.home_score == 0 and game.away_score == 0:
                continue
            try:
                service.process_game(game)
            except ValueError:
                continue  # invalid game for ranking purposes; skip like production does

    session.close()
    return records


def score(records: list, weight: float, min_week: int) -> dict:
    """Accuracy, Brier score and margin error for one (weight, min_week) setting."""
    correct = brier = margin_err = 0.0
    n = 0
    for r in records:
        home = blend_rating(r["home_elo"], r["home_eff"], weight, r["week"], min_week)
        away = blend_rating(r["away_elo"], r["away_eff"], weight, r["week"], min_week)

        diff = (home + (0 if r["neutral"] else HOME_FIELD_ADVANTAGE)) - away
        home_wp = 1 / (1 + 10 ** (-diff / RATING_SCALE))

        home_won = r["home_score"] > r["away_score"]
        if r["home_score"] == r["away_score"]:
            continue  # ties are not predictable either way

        n += 1
        correct += (home_wp > 0.5) == home_won
        brier += (home_wp - (1.0 if home_won else 0.0)) ** 2
        predicted_margin = (diff / 100) * POINTS_PER_100_ELO
        margin_err += abs(predicted_margin - (r["home_score"] - r["away_score"]))

    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "accuracy": correct / n,
        "brier": brier / n,
        "margin_mae": margin_err / n,
    }


def main():
    # Replaying a season re-derives every preseason rating, which logs per team.
    logging.getLogger("src").setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2025])
    parser.add_argument("--weights", type=float, nargs="+", default=DEFAULT_WEIGHTS)
    parser.add_argument("--min-weeks", type=int, nargs="+", default=DEFAULT_MIN_WEEKS)
    parser.add_argument("--db", default=str(project_root / "cfb_rankings.db"))
    parser.add_argument(
        "--exclude-garbage-time",
        action="store_true",
        help="source efficiency from CFBD's garbage-time-filtered PPA",
    )
    args = parser.parse_args()

    source_db = Path(args.db)
    if not source_db.exists():
        sys.exit(f"ERROR: database not found: {source_db}")

    all_records = []
    tmpdir = Path(tempfile.mkdtemp(prefix="blend-backtest-"))
    try:
        for season in args.seasons:
            print(f"\n{'=' * 70}\nSeason {season}\n{'=' * 70}")
            ppa_rows = load_ppa_games(
                season, project_root / "data", args.exclude_garbage_time
            )
            weekly_eff = build_weekly_efficiency(ppa_rows)

            # Replay against a copy — the real database is never touched
            work_db = tmpdir / f"backtest_{season}.db"
            shutil.copy(source_db, work_db)

            print("  replaying season...")
            records = replay_season(work_db, season, weekly_eff)
            covered = sum(1 for r in records if r["home_eff"] is not None)
            print(f"  {len(records)} games predicted, {covered} with efficiency data")
            all_records.append((season, records))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    combined = [r for _, recs in all_records for r in recs]
    for label, records in [(f"{s}", r) for s, r in all_records] + [("ALL", combined)]:
        if len(all_records) == 1 and label == "ALL":
            continue
        print(f"\n{'=' * 70}\n{label}: accuracy / Brier / margin MAE\n{'=' * 70}")
        header = "  w     " + "".join(f"{'min_wk ' + str(m):>22}" for m in args.min_weeks)
        print(header)
        baseline = score(records, 0.0, 99)
        print(f"  pure ELO baseline: n={baseline['n']} acc={baseline['accuracy']:.4f} "
              f"brier={baseline['brier']:.4f} mae={baseline['margin_mae']:.2f}")
        for w in args.weights:
            cells = []
            for m in args.min_weeks:
                s = score(records, w, m)
                delta = s["accuracy"] - baseline["accuracy"]
                cells.append(f"{s['accuracy']:.4f}/{s['brier']:.4f}/{delta:+.4f}".rjust(22))
            print(f"  {w:<6.2f}" + "".join(cells))

        best = max(
            ((w, m, score(records, w, m)) for w in args.weights for m in args.min_weeks),
            key=lambda x: -x[2]["brier"],
        )
        print(f"\n  best Brier: w={best[0]} min_week={best[1]} "
              f"brier={best[2]['brier']:.4f} acc={best[2]['accuracy']:.4f} "
              f"(baseline brier={baseline['brier']:.4f})")


if __name__ == "__main__":
    main()
