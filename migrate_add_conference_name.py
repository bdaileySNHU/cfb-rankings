"""
Add conference_name field to teams table
EPIC-012: Conference Display

This migration adds a new field to store actual conference names
(Big Ten, SEC, ACC, etc.) while keeping the existing conference tier
enum (P5/G5/FCS) for ranking logic.
"""

import sqlite3
import sys


def migrate():
    """Add conference_name column to teams table"""
    try:
        # Connect to database
        conn = sqlite3.connect('cfb_rankings.db')
        cursor = conn.cursor()

        print("=" * 80)
        print("MIGRATION: Add conference_name field")
        print("EPIC-012: Conference Display")
        print("=" * 80)
        print()

        # Add conference_name column
        print("Adding conference_name column to teams table...")
        cursor.execute("""
            ALTER TABLE teams
            ADD COLUMN conference_name VARCHAR(50) NULL
        """)

        print("✓ Added conference_name field")
        print()

        # Commit changes
        conn.commit()
        conn.close()

        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Run import script to populate conference names")
        print("  2. Restart backend service")
        print()

        return 0

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  Column 'conference_name' already exists - migration already applied")
            return 0
        else:
            print(f"❌ Migration failed: {e}")
            return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = migrate()
    sys.exit(exit_code)
