"""
Update Current Week for Active Season

This script updates the current_week field for the active season.
Useful for correcting week after data imports or manual adjustments.
"""

import sqlite3
import sys


def update_current_week(week: int, season: int = 2025):
    """
    Update the current week for a given season.

    Args:
        week: The week number to set (1-19, includes playoff weeks 16-19)
        season: The season year (default: 2025)
    """
    if not (1 <= week <= 19):
        print(f"❌ Error: Week must be between 1 and 19 (got {week})")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect("cfb_rankings.db")
        cursor = conn.cursor()

        # Check if season exists
        cursor.execute("SELECT year, current_week FROM seasons WHERE year = ?", (season,))
        result = cursor.fetchone()

        if not result:
            print(f"❌ Error: Season {season} not found in database")
            conn.close()
            return False

        old_week = result[1]

        # Update current week
        cursor.execute("UPDATE seasons SET current_week = ? WHERE year = ?", (week, season))
        conn.commit()

        # Verify update
        cursor.execute("SELECT current_week FROM seasons WHERE year = ?", (season,))
        new_week = cursor.fetchone()[0]

        conn.close()

        print(f"✓ Updated season {season}")
        print(f"  Previous week: {old_week}")
        print(f"  New week: {new_week}")

        return True

    except Exception as e:
        print(f"❌ Error updating week: {e}")
        return False


def main():
    """Main function with user input"""
    print("=" * 60)
    print("UPDATE CURRENT WEEK")
    print("=" * 60)
    print()

    # Get week number from user
    if len(sys.argv) > 1:
        # Week provided as command line argument
        try:
            week = int(sys.argv[1])
        except ValueError:
            print(f"❌ Error: Invalid week number '{sys.argv[1]}'")
            print("Usage: python3 update_current_week.py [week_number]")
            sys.exit(1)
    else:
        # Prompt user for week
        week_input = input("Enter the current week number (1-19): ").strip()
        try:
            week = int(week_input)
        except ValueError:
            print(f"❌ Error: Invalid input '{week_input}'. Must be a number.")
            sys.exit(1)

    # Get season (default to 2025)
    if len(sys.argv) > 2:
        try:
            season = int(sys.argv[2])
        except ValueError:
            print(f"❌ Error: Invalid season '{sys.argv[2]}'")
            sys.exit(1)
    else:
        season = 2025

    # Update the week
    success = update_current_week(week, season)

    if success:
        print()
        print("=" * 60)
        print("✓ COMPLETE")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Restart backend service: sudo systemctl restart cfb-rankings")
        print("  2. Verify on website that current week is correct")
        print()
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
