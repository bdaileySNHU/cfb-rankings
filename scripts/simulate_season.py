#!/usr/bin/env python3
"""Simulate the rest of a season and cache the playoff projection.

Run on demand; the weekly import calls the same code path automatically.

    python3 scripts/simulate_season.py                    # active season, 10k runs
    python3 scripts/simulate_season.py --season 2026
    python3 scripts/simulate_season.py --runs 2000 --seed 7 --dry-run
"""

import argparse
import os
import sys

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

from src.core.season_simulation import DEFAULT_RUNS, build_projection, refresh_projection
from src.models.database import SessionLocal
from src.models.models import Season


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, help="Season year (defaults to the active season)")
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS, help=f"Simulated seasons (default {DEFAULT_RUNS})")
    p.add_argument("--seed", type=int, help="Random seed, for a reproducible run")
    p.add_argument("--dry-run", action="store_true", help="Print the projection without caching it")
    return p.parse_args()


def main():
    args = parse_args()
    db = SessionLocal()
    try:
        season = args.season
        if not season:
            active = db.query(Season).filter(Season.is_active == True).first()  # noqa: E712
            if not active:
                print("❌ No active season found. Pass --season explicitly.")
                return 1
            season = active.year

        print(f"Simulating {season} — {args.runs:,} seasons...")
        started = time.time()
        if args.dry_run:
            projection = build_projection(db, season, runs=args.runs, seed=args.seed)
        else:
            projection = refresh_projection(db, season, runs=args.runs, seed=args.seed)
        elapsed = time.time() - started

        if not projection["field"]:
            print(f"⚠️  Not enough teams to build a field for {season}")
            return 1

        print(f"✓ Done in {elapsed:.1f}s (through week {projection['through_week']})\n")
        header = f'{"SEED":>4}  {"TEAM":<22} {"CONFERENCE":<18} {"RATING":>8} {"BID%":>6} {"CONF%":>6} {"NAT%":>6} {"PROJ W":>7}'
        print(header)
        print("-" * len(header))
        for t in projection["field"]:
            print(
                f'{t["seed"]:>4}  {t["name"]:<22} {str(t["conference_name"]):<18} '
                f'{t["elo"]:8.1f} {t["bid_pct"]:6.1f} {t["conf_title_pct"]:6.1f} '
                f'{t["title_pct"]:6.1f} {t["proj_wins"]:7.1f}'
            )

        if projection["bubble"]:
            print("\nBubble:")
            for b in projection["bubble"][:8]:
                print(f'      {b["name"]:<22} {str(b["conference_name"]):<18} {b["elo"]:8.1f} {b["bid_pct"]:6.1f}')

        print(f'\nProjected champion: {projection["champion"]["name"]}')
        if args.dry_run:
            print("(dry run — nothing was written)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
