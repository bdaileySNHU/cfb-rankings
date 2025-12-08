"""
Database migration: Add FCS-related fields
Story 007: Game Model Exclusion Flag for FCS Games

Adds:
- Team.is_fcs (boolean, default=False)
- Game.excluded_from_rankings (boolean, default=False, indexed)
"""

import os
import sqlite3


def migrate():
    """Run migration to add FCS fields"""
    db_path = "cfb_rankings.db"

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Starting migration...")

        # Add is_fcs to teams table
        print("  Adding teams.is_fcs column...")
        cursor.execute("ALTER TABLE teams ADD COLUMN is_fcs BOOLEAN DEFAULT 0 NOT NULL")

        # Add excluded_from_rankings to games table
        print("  Adding games.excluded_from_rankings column...")
        cursor.execute("ALTER TABLE games ADD COLUMN excluded_from_rankings BOOLEAN DEFAULT 0 NOT NULL")

        # Create index on excluded_from_rankings for query performance
        print("  Creating index on games.excluded_from_rankings...")
        cursor.execute("CREATE INDEX idx_games_excluded_from_rankings ON games(excluded_from_rankings)")

        # Verify migration
        print("\nVerifying migration...")

        # Check teams table
        cursor.execute("PRAGMA table_info(teams)")
        teams_cols = [col[1] for col in cursor.fetchall()]
        assert 'is_fcs' in teams_cols, "teams.is_fcs not found"
        print("  ✓ teams.is_fcs exists")

        # Check games table
        cursor.execute("PRAGMA table_info(games)")
        games_cols = [col[1] for col in cursor.fetchall()]
        assert 'excluded_from_rankings' in games_cols, "games.excluded_from_rankings not found"
        print("  ✓ games.excluded_from_rankings exists")

        # Check index
        cursor.execute("PRAGMA index_list(games)")
        indexes = [idx[1] for idx in cursor.fetchall()]
        assert 'idx_games_excluded_from_rankings' in indexes, "Index not found"
        print("  ✓ Index idx_games_excluded_from_rankings exists")

        # Verify all existing games are False (0)
        cursor.execute("SELECT COUNT(*) FROM games WHERE excluded_from_rankings = 1")
        excluded_count = cursor.fetchone()[0]
        assert excluded_count == 0, f"Expected 0 excluded games, found {excluded_count}"
        print(f"  ✓ All existing games have excluded_from_rankings=False")

        # Verify all existing teams are FBS (is_fcs=0)
        cursor.execute("SELECT COUNT(*) FROM teams WHERE is_fcs = 1")
        fcs_count = cursor.fetchone()[0]
        assert fcs_count == 0, f"Expected 0 FCS teams, found {fcs_count}"
        print(f"  ✓ All existing teams have is_fcs=False")

        conn.commit()
        print("\nMigration completed successfully!")
        return True

    except Exception as e:
        print(f"\nMigration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def rollback():
    """Rollback migration (remove FCS fields)"""
    db_path = "cfb_rankings.db"

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Rolling back migration...")

        # Drop index
        print("  Dropping index idx_games_excluded_from_rankings...")
        cursor.execute("DROP INDEX IF EXISTS idx_games_excluded_from_rankings")

        # SQLite doesn't support DROP COLUMN directly
        # Would need to recreate tables without these columns
        # For now, just warn
        print("\nWARNING: SQLite doesn't support DROP COLUMN.")
        print("To fully rollback, restore from backup or recreate database.")
        print("Columns teams.is_fcs and games.excluded_from_rankings remain but index is dropped.")

        conn.commit()
        print("Partial rollback completed.")
        return True

    except Exception as e:
        print(f"Rollback failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
