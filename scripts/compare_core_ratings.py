#!/usr/bin/env python3
"""Check our ELO against CFBD's CORE ratings.

CORE is an independent opponent-adjusted rating on a points scale, which makes
it a useful outside yardstick: if our ordering and CORE's disagree wildly, one
of us is wrong and it is worth knowing which games drove it.

This deliberately does not feed CORE into the model. CORE is built from the same
adjusted PPA that already feeds the efficiency blend, so blending it in would
double-count one signal and call it two.

Two numbers come out of it:

  Rank agreement   Spearman correlation between the two orderings.
  Scale agreement  Our ELO converted to points-above-average against CORE's, in
                   points. Catches a compressed or inflated spread even when the
                   ordering is fine — the failure mode where every team is ranked
                   correctly and nobody is rated far enough apart.

Usage:
    python3 scripts/compare_core_ratings.py
    python3 scripts/compare_core_ratings.py --season 2025 --top 20
"""

import argparse
import statistics
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import os  # noqa: E402

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.integrations.cfbd_client import CFBDClient  # noqa: E402
from src.models.models import RankingHistory, Team  # noqa: E402

# Same conversion the prediction code uses; see _calculate_game_prediction.
POINTS_PER_100_ELO = 7.0


def ranks(values: list) -> dict:
    """Map each value to its 1-based rank, highest first. Ties share a rank."""
    order = sorted(set(values), reverse=True)
    return {v: i + 1 for i, v in enumerate(order)}


def our_ratings(db, season: int, week: int = None):
    """Our ratings for a season, from the ranking snapshot rather than live ELO.

    teams.elo_rating holds one number — wherever the model is right now — so
    reading it while comparing against a finished season would put this season's
    preseason ratings up against last season's results. ranking_history has the
    point-in-time value, which is the like-for-like comparison.

    Returns (ratings by team name, description of where they came from).
    """
    snapshot_week = week
    if snapshot_week is None:
        latest = (
            db.query(RankingHistory.week)
            .filter(RankingHistory.season == season)
            .order_by(RankingHistory.week.desc())
            .first()
        )
        snapshot_week = latest[0] if latest else None

    if snapshot_week is not None:
        rows = (
            db.query(RankingHistory, Team)
            .join(Team, Team.id == RankingHistory.team_id)
            .filter(
                RankingHistory.season == season,
                RankingHistory.week == snapshot_week,
                Team.is_fcs == False,  # noqa: E712
            )
            .all()
        )
        if rows:
            return (
                {team.name: hist.elo_rating for hist, team in rows},
                f"week {snapshot_week} snapshot",
            )

    teams = db.query(Team).filter(Team.is_fcs == False).all()  # noqa: E712
    return {t.name: t.elo_rating for t in teams}, "current live ratings"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--season", type=int, default=None, help="default: current season")
    parser.add_argument("--week", type=int, default=None, help="default: season to date")
    parser.add_argument("--top", type=int, default=15, help="how many disagreements to show")
    parser.add_argument("--db", default=str(project_root / "cfb_rankings.db"))
    args = parser.parse_args()

    api_key = os.getenv("CFBD_API_KEY")
    if not api_key:
        sys.exit("ERROR: CFBD_API_KEY not set")

    cfbd = CFBDClient(api_key)
    season = args.season or cfbd.get_current_season()

    core = cfbd.get_core_ratings(season, week=args.week)
    if not core:
        sys.exit(f"ERROR: no CORE ratings available for {season}")

    db = sessionmaker(bind=create_engine(f"sqlite:///{args.db}"))()
    try:
        ours, source = our_ratings(db, season, args.week)
    finally:
        db.close()

    paired = [
        (row["team"], ours[row["team"]], row["overall"])
        for row in core
        if row.get("team") in ours and row.get("overall") is not None
    ]
    if len(paired) < 10:
        sys.exit(f"ERROR: only {len(paired)} teams matched between CORE and our table")

    missing = sorted({row["team"] for row in core if row.get("team") not in ours})

    elos = [e for _, e, _ in paired]
    cores = [c for _, _, c in paired]
    mean_elo = statistics.fmean(elos)

    # Our rating expressed the way CORE expresses its own: points better than
    # an average team.
    our_points = [(e - mean_elo) / 100 * POINTS_PER_100_ELO for e in elos]

    spearman = statistics.correlation(elos, cores, method="ranked")
    pearson = statistics.correlation(our_points, cores)
    gaps = [abs(p - c) for p, c in zip(our_points, cores)]

    print(f"\nCORE vs our ELO — {season}" + (f" week {args.week}" if args.week else " (season to date)"))
    print(f"ours: {source}")
    print(f"{len(paired)} teams matched" + (f", {len(missing)} CORE teams not in our table" if missing else ""))
    print(f"\n  rank agreement (Spearman):  {spearman:.3f}")
    print(f"  scale agreement (Pearson):  {pearson:.3f}")
    print(f"  mean gap in points:         {statistics.fmean(gaps):.2f}")
    print(f"  our spread (sd, points):    {statistics.stdev(our_points):.2f}")
    print(f"  CORE spread (sd, points):   {statistics.stdev(cores):.2f}")

    elo_rank = ranks(elos)
    core_rank = ranks(cores)
    rows = [
        (name, elo_rank[e], core_rank[c], (e - mean_elo) / 100 * POINTS_PER_100_ELO, c)
        for name, e, c in paired
    ]
    rows.sort(key=lambda r: abs(r[1] - r[2]), reverse=True)

    print(f"\n  Biggest disagreements (top {args.top}):")
    print(f"  {'team':<24}{'ours':>6}{'CORE':>6}{'gap':>6}{'our pts':>10}{'CORE pts':>10}")
    for name, our_r, core_r, our_p, core_p in rows[: args.top]:
        print(f"  {name:<24}{our_r:>6}{core_r:>6}{our_r - core_r:>+6}{our_p:>10.1f}{core_p:>10.1f}")

    if missing:
        print(f"\n  Not in our teams table: {', '.join(missing[:12])}")


if __name__ == "__main__":
    main()
