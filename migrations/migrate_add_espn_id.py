"""
Add espn_id field to teams table
EPIC-037: ESPN Team Logo Integration

Adds espn_id column so the frontend can serve real ESPN CDN logos:
  https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png
"""

import sqlite3
import sys


def migrate():
    try:
        conn = sqlite3.connect('cfb_rankings.db')
        cursor = conn.cursor()

        print("=" * 70)
        print("MIGRATION: Add espn_id field to teams table")
        print("EPIC-037: ESPN Team Logo Integration")
        print("=" * 70)

        cursor.execute("ALTER TABLE teams ADD COLUMN espn_id INTEGER NULL")
        conn.commit()
        conn.close()

        print("✓ Added espn_id column to teams table")
        print()
        print("Next steps:")
        print("  1. Run: python3 utilities/populate_espn_ids.py")
        print("  2. Restart backend service")
        return 0

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  Column 'espn_id' already exists — migration already applied")
            return 0
        print(f"❌ Migration failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
