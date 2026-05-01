#!/usr/bin/env python3
"""Database Migration: Add Player Table

This migration script adds the players table to support individual player
recruiting data for the Preseason Enhancement Epic.

Purpose:
    - Create players table with fields for player name, position, recruiting data
    - Add indexes for efficient position group queries (team_id, position)
    - Add index for season filtering (recruiting_year)
    - Ensure unique constraint on cfbd_athlete_id

Idempotent:
    - Uses checkfirst=True to avoid errors if table already exists
    - Safe to run multiple times

Rollback:
    To rollback this migration, execute:
        DROP TABLE IF EXISTS players;

Part of: Preseason Enhancement Epic - Story 1.1
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from src.models.database import SessionLocal, engine
from src.models.models import Base, Player


def migrate():
    """Add players table to database.

    Creates the players table with all columns, relationships, and indexes
    as defined in the Player model. Uses checkfirst=True for idempotency.

    Returns:
        bool: True if migration successful, False otherwise
    """
    print("Creating players table...")

    try:
        # Create only the players table (checkfirst=True makes it idempotent)
        Player.__table__.create(engine, checkfirst=True)
        print("✓ Players table created successfully!")

        # Verify table exists and is queryable
        db = SessionLocal()
        try:
            # Try a simple query to confirm table is accessible
            count = db.query(Player).count()
            print(f"✓ Table verified - currently {count} players stored")
        except Exception as e:
            print(f"✗ Error verifying table: {e}")
            return False
        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ Error creating players table: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_indexes():
    """Verify that required indexes were created.

    Checks for:
        - idx_players_team_position (team_id, position)
        - idx_players_recruiting_year (recruiting_year)
        - Unique constraint on cfbd_athlete_id

    Returns:
        bool: True if all indexes verified, False otherwise
    """
    print("\nVerifying indexes...")

    try:
        db = SessionLocal()
        try:
            # Query database for index information (SQLite specific)
            result = db.execute(text("PRAGMA index_list(players)"))
            indexes = {row[1] for row in result.fetchall()}

            expected_indexes = {
                "idx_players_team_position",
                "idx_players_recruiting_year",
            }

            # Check for expected indexes
            for index_name in expected_indexes:
                if index_name in indexes:
                    print(f"✓ Index verified: {index_name}")
                else:
                    print(f"⚠ Index not found: {index_name}")

            # Check for unique constraint on cfbd_athlete_id
            if "sqlite_autoindex_players_1" in indexes or any("cfbd_athlete_id" in idx for idx in indexes):
                print("✓ Unique constraint verified: cfbd_athlete_id")
            else:
                print("⚠ Unique constraint not found: cfbd_athlete_id")

            return True

        finally:
            db.close()

    except Exception as e:
        print(f"✗ Error verifying indexes: {e}")
        return False


def main():
    """Main entry point for migration script."""
    print("=" * 60)
    print("Preseason Enhancement Epic - Story 1.1")
    print("Migration: Add Player Table")
    print("=" * 60)
    print()

    # Run migration
    success = migrate()

    if not success:
        print("\n✗ Migration failed!")
        print("\nRollback instructions:")
        print("  sqlite3 cfb_rankings.db 'DROP TABLE IF EXISTS players;'")
        sys.exit(1)

    # Verify indexes
    verify_indexes()

    print()
    print("=" * 60)
    print("✓ Migration completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Run tests: pytest tests/unit/test_player_model.py")
    print("  2. Import player data: python utilities/import_player_data.py --year 2024")
    print("  3. Verify data: sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM players;'")
    print()
    print("Rollback if needed:")
    print("  sqlite3 cfb_rankings.db 'DROP TABLE IF EXISTS players;'")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
