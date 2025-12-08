"""
Add quarter score fields to games table
EPIC-021: Quarter-Weighted ELO with Garbage Time Adjustment

This migration adds 8 new nullable columns to store quarter-by-quarter
scores for enhanced ELO calculation with garbage time detection.
"""

import sqlite3
import sys


def migrate():
    """Add quarter score columns to games table"""
    try:
        # Connect to database
        conn = sqlite3.connect('cfb_rankings.db')
        cursor = conn.cursor()

        print("=" * 80)
        print("MIGRATION: Add quarter score fields")
        print("EPIC-021: Quarter-Weighted ELO")
        print("=" * 80)
        print()

        # Add quarter score columns
        columns_to_add = [
            ('q1_home', 'INTEGER NULL'),
            ('q1_away', 'INTEGER NULL'),
            ('q2_home', 'INTEGER NULL'),
            ('q2_away', 'INTEGER NULL'),
            ('q3_home', 'INTEGER NULL'),
            ('q3_away', 'INTEGER NULL'),
            ('q4_home', 'INTEGER NULL'),
            ('q4_away', 'INTEGER NULL'),
        ]

        for col_name, col_type in columns_to_add:
            print(f"Adding {col_name} column...")
            try:
                cursor.execute(f"ALTER TABLE games ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️  Column '{col_name}' already exists - skipping")
                else:
                    raise

        print()

        # Commit changes
        conn.commit()

        # Verify columns added
        cursor.execute("PRAGMA table_info(games)")
        columns = cursor.fetchall()
        quarter_cols = [col for col in columns if col[1].startswith('q')]
        print(f"✓ Verification: {len(quarter_cols)} quarter score columns in games table")

        conn.close()

        print()
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Update import scripts to populate quarter scores from CFBD API")
        print("  2. Implement quarter-weighted ELO algorithm (Story 21.2)")
        print("  3. Run backfill script to populate historical data (Story 21.3)")
        print()

        return 0

    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = migrate()
    sys.exit(exit_code)
