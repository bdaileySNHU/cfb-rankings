#!/usr/bin/env python3
"""
EPIC-024 FIX: Clean up duplicate entries in ranking_history table

This script removes duplicate entries where the same team has multiple
ranking records for the same season/week combination. It keeps the most
recent entry (highest ID) for each team/season/week.
"""

import os
import sys

# Add parent directory to path so we can import from project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, func

from src.models.database import SessionLocal
from src.models.models import RankingHistory


def find_duplicates(db):
    """Find all duplicate team/season/week combinations"""
    duplicates = (
        db.query(
            RankingHistory.team_id,
            RankingHistory.season,
            RankingHistory.week,
            func.count(RankingHistory.id).label("count"),
            func.group_concat(RankingHistory.id).label("ids"),
        )
        .group_by(RankingHistory.team_id, RankingHistory.season, RankingHistory.week)
        .having(func.count(RankingHistory.id) > 1)
        .all()
    )

    return duplicates


def cleanup_duplicates(db, dry_run=True):
    """
    Remove duplicate ranking_history entries, keeping the most recent (highest ID)

    Args:
        db: Database session
        dry_run: If True, only show what would be deleted without actually deleting
    """
    duplicates = find_duplicates(db)

    if not duplicates:
        print("✅ No duplicates found!")
        return 0

    print(f"Found {len(duplicates)} duplicate team/season/week combinations")
    print()

    total_to_delete = 0

    for dup in duplicates:
        team_id = dup.team_id
        season = dup.season
        week = dup.week
        count = dup.count

        # Get all entries for this team/season/week
        entries = (
            db.query(RankingHistory)
            .filter(
                and_(
                    RankingHistory.team_id == team_id,
                    RankingHistory.season == season,
                    RankingHistory.week == week,
                )
            )
            .order_by(RankingHistory.id.desc())
            .all()
        )

        # Keep the first (most recent ID), delete the rest
        keep_entry = entries[0]
        delete_entries = entries[1:]

        print(f"Team {team_id}, Season {season}, Week {week}: {count} entries")
        print(
            f"  Keeping: ID {keep_entry.id} (ELO: {keep_entry.elo_rating:.2f}, Rank: {keep_entry.rank})"
        )

        for entry in delete_entries:
            print(
                f"  {'[DRY RUN] Would delete' if dry_run else 'Deleting'}: ID {entry.id} (ELO: {entry.elo_rating:.2f}, Rank: {entry.rank})"
            )
            if not dry_run:
                db.delete(entry)
            total_to_delete += 1

        print()

    if not dry_run:
        db.commit()
        print(f"✅ Deleted {total_to_delete} duplicate entries")
    else:
        print(f"[DRY RUN] Would delete {total_to_delete} entries")
        print()
        print("To actually delete these entries, run:")
        print("  python scripts/cleanup_ranking_duplicates.py --execute")

    return total_to_delete


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Clean up duplicate ranking_history entries")
    parser.add_argument(
        "--execute", action="store_true", help="Actually delete duplicates (default is dry-run)"
    )
    args = parser.parse_args()

    db = SessionLocal()

    print("=" * 80)
    print("EPIC-024: Ranking History Duplicate Cleanup")
    print("=" * 80)
    print()

    if not args.execute:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    try:
        cleanup_duplicates(db, dry_run=not args.execute)
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
