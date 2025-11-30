"""
Add game_type field to games table
EPIC-022: Conference Championship Game Support

This migration adds a game_type column to distinguish between regular season,
conference championship, bowl, and playoff games.
"""

import sqlite3
import sys


def migrate():
    """Add game_type column to games table"""
    try:
        # Connect to database
        conn = sqlite3.connect('cfb_rankings.db')
        cursor = conn.cursor()

        print("=" * 80)
        print("MIGRATION: Add game_type field")
        print("EPIC-022: Conference Championship Game Support")
        print("=" * 80)
        print()

        # Add game_type column
        print("Adding game_type column...")
        try:
            cursor.execute("ALTER TABLE games ADD COLUMN game_type VARCHAR(50) NULL")
            print("✓ Added game_type column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  Column 'game_type' already exists - skipping")
            else:
                raise

        print()

        # Commit changes
        conn.commit()

        # Verify column added
        cursor.execute("PRAGMA table_info(games)")
        columns = cursor.fetchall()
        game_type_col = [col for col in columns if col[1] == 'game_type']

        if game_type_col:
            print("✓ Verification: game_type column added successfully")
            print(f"  Column details: {game_type_col[0]}")
        else:
            print("❌ Verification failed: game_type column not found")
            return 1

        conn.close()

        print()
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Game Type Values:")
        print("  NULL                      - Regular season game (default)")
        print("  'conference_championship' - Conference championship game")
        print("  'bowl'                    - Bowl game (EPIC-023)")
        print("  'playoff'                 - Playoff game (EPIC-023)")
        print()
        print("Next steps:")
        print("  1. Update CFBD client to support season_type parameter (Story 22.1)")
        print("  2. Import conference championship games (Story 22.1)")
        print("  3. Update frontend to display conference championship badge (Story 22.2)")
        print("  4. Verify ranking processing (Story 22.3)")
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
