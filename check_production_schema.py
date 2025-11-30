#!/usr/bin/env python3
"""
Check production database schema for required migrations
"""

import sqlite3
import sys


def check_schema():
    """Check which migrations have been applied"""
    try:
        conn = sqlite3.connect('cfb_rankings.db')
        cursor = conn.cursor()

        # Get all columns from games table
        cursor.execute('PRAGMA table_info(games)')
        columns = cursor.fetchall()

        # Check for quarter score columns (EPIC-021)
        quarter_cols = [col for col in columns if 'q1' in col[1] or 'q2' in col[1] or 'q3' in col[1] or 'q4' in col[1]]

        # Check for game_type column (EPIC-022)
        game_type_col = [col for col in columns if col[1] == 'game_type']

        print("=" * 80)
        print("PRODUCTION DATABASE SCHEMA CHECK")
        print("=" * 80)
        print()

        # Report EPIC-021 status
        print("EPIC-021: Quarter Score Columns")
        if quarter_cols:
            print(f"  ✓ Found {len(quarter_cols)} quarter score columns")
            for col in quarter_cols:
                print(f"    - {col[1]} ({col[2]})")
        else:
            print("  ✗ NOT FOUND - Migration needed!")
            print("    Run: sudo -u www-data venv/bin/python migrate_add_quarter_scores.py")

        print()

        # Report EPIC-022 status
        print("EPIC-022: Game Type Column")
        if game_type_col:
            print(f"  ✓ Found: {game_type_col[0][1]} ({game_type_col[0][2]})")
        else:
            print("  ✗ NOT FOUND - Migration needed!")
            print("    Run: sudo -u www-data venv/bin/python migrate_add_game_type.py")

        print()
        print("=" * 80)

        # Check for data
        if game_type_col:
            cursor.execute("SELECT COUNT(*) FROM games WHERE game_type = 'conference_championship'")
            conf_champ_count = cursor.fetchone()[0]
            print(f"Conference Championships Imported: {conf_champ_count}")

        if quarter_cols:
            cursor.execute("SELECT COUNT(*) FROM games WHERE q1_home IS NOT NULL")
            quarter_data_count = cursor.fetchone()[0]
            print(f"Games with Quarter Scores: {quarter_data_count}")

        print("=" * 80)

        conn.close()

        # Return status
        if not quarter_cols or not game_type_col:
            return 1
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(check_schema())
