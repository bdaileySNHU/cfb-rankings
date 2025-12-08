#!/usr/bin/env python3
"""
Quick script to update the current_week in the seasons table.
Usage: python3 scripts/fix_current_week.py --year 2024 --week 10
"""

import argparse
import os
import sys

# Add parent directory to path to import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import SessionLocal
from src.models.models import Season


def update_current_week(year: int, week: int) -> bool:
    """
    Update the current_week for a specific season.

    Args:
        year: Season year
        week: Week number to set (0-15)

    Returns:
        bool: True if successful, False otherwise
    """
    if not (0 <= week <= 15):
        print(f"Error: Week must be between 0 and 15, got {week}")
        return False

    db = SessionLocal()
    try:
        season = db.query(Season).filter(Season.year == year).first()

        if not season:
            print(f"Error: Season {year} not found in database")
            return False

        old_week = season.current_week
        season.current_week = week
        db.commit()

        print(f"✓ Updated season {year}: current_week {old_week} → {week}")
        return True

    except Exception as e:
        print(f"Error updating season: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Update the current_week for a season',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update 2024 season to week 10
  python3 scripts/fix_current_week.py --year 2024 --week 10

  # Update 2025 season to week 8
  python3 scripts/fix_current_week.py --year 2025 --week 8
        """
    )

    parser.add_argument('--year', type=int, required=True,
                        help='Season year to update')
    parser.add_argument('--week', type=int, required=True,
                        help='Week number to set (0-15)')

    args = parser.parse_args()

    success = update_current_week(args.year, args.week)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
