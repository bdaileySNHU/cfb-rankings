#!/usr/bin/env python3
"""
Save final season ELO snapshot to ranking_history before preseason init.

EPIC-030: Captures each team's true postseason-final ELO (including bowl games
and CFP results) as a week=999 sentinel entry in ranking_history. Must be run
BEFORE initializing next season's preseason ratings, otherwise the postseason
ELO values in teams.elo_rating are overwritten.

Usage:
    python utilities/save_final_season_snapshot.py --season 2025
    python utilities/save_final_season_snapshot.py --season 2025 --dry-run
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import SessionLocal
from src.models.models import Team
from src.core.ranking_service import RankingService


def main():
    parser = argparse.ArgumentParser(description="Save final season ELO snapshot")
    parser.add_argument("--season", type=int, required=True, help="Season year to snapshot (e.g. 2025)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rs = RankingService(db)

        # Preview top 10 by ELO
        top_teams = db.query(Team).order_by(Team.elo_rating.desc()).limit(10).all()
        print(f"\nTop 10 teams by current elo_rating (season {args.season}):")
        for i, t in enumerate(top_teams, 1):
            print(f"  #{i:2}  {t.name:<30}  {t.elo_rating:.2f}")

        if args.dry_run:
            total = db.query(Team).count()
            print(f"\n[DRY RUN] Would write week=999 snapshot for {total} teams to ranking_history.")
            print("Re-run without --dry-run to commit.")
            return

        count = rs.save_final_season_snapshot(args.season)
        print(f"\n✓ Saved week=999 final snapshot for {count} teams (season {args.season}).")
        print("  These entries will be used by EPIC-030 previous season regression.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
