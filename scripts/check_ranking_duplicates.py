#!/usr/bin/env python3
"""
Check for duplicate entries in ranking_history table

Quick diagnostic script to verify no duplicates exist for team/season/week combinations.
"""

import os
import sys

# Add parent directory to path so we can import from project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, func

from database import SessionLocal
from models import RankingHistory


def check_duplicates(db, verbose=False):
    """
    Check for duplicate ranking_history entries

    Args:
        db: Database session
        verbose: If True, show details of each duplicate

    Returns:
        Number of duplicate groups found
    """
    duplicates = db.query(
        RankingHistory.team_id,
        RankingHistory.season,
        RankingHistory.week,
        func.count(RankingHistory.id).label('count')
    ).group_by(
        RankingHistory.team_id,
        RankingHistory.season,
        RankingHistory.week
    ).having(func.count(RankingHistory.id) > 1).all()

    if not duplicates:
        print("✅ No duplicates found!")
        return 0

    print(f"❌ Found {len(duplicates)} duplicate team/season/week combinations")
    print()

    total_duplicate_records = 0

    for dup in duplicates[:10] if not verbose else duplicates:  # Show first 10 unless verbose
        team_id = dup.team_id
        season = dup.season
        week = dup.week
        count = dup.count

        total_duplicate_records += count - 1  # -1 because we keep one

        if verbose:
            # Get all entries for this team/season/week
            entries = db.query(RankingHistory).filter(
                and_(
                    RankingHistory.team_id == team_id,
                    RankingHistory.season == season,
                    RankingHistory.week == week
                )
            ).order_by(RankingHistory.id.desc()).all()

            print(f"Team {team_id}, Season {season}, Week {week}: {count} entries")
            for entry in entries:
                team_name = entry.team.name if entry.team else "Unknown"
                print(f"  - ID {entry.id}: {team_name} (ELO: {entry.elo_rating:.2f}, Rank: {entry.rank}, W-L: {entry.wins}-{entry.losses})")
            print()
        else:
            print(f"Team {team_id}, Season {season}, Week {week}: {count} entries")

    if not verbose and len(duplicates) > 10:
        print(f"... and {len(duplicates) - 10} more (use --verbose to see all)")

    print()
    print(f"Total duplicate records that should be removed: {total_duplicate_records}")
    print()
    print("To clean up duplicates, run:")
    print("  python scripts/cleanup_ranking_duplicates.py --execute")

    return len(duplicates)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Check for duplicate ranking_history entries')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information about each duplicate')
    args = parser.parse_args()

    db = SessionLocal()

    print("="*80)
    print("EPIC-024: Ranking History Duplicate Check")
    print("="*80)
    print()

    try:
        duplicate_count = check_duplicates(db, verbose=args.verbose)
        sys.exit(1 if duplicate_count > 0 else 0)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
