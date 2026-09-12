"""
Add sp_plus_ratings table
SP+ prediction comparison

Stores a weekly snapshot of SP+ ratings so ELO predictions can be graded
against a source that covers every FBS team, not just the AP Top 25.

A separate table rather than a poll_type row on ap_poll_rankings: that table
carries UNIQUE (season, week, team_id), so SP+ rows would collide with AP rows
for every ranked team.
"""

import sqlite3
import sys


def migrate(db_path: str = "cfb_rankings.db") -> int:
    """Create the sp_plus_ratings table and its indexes. Safe to re-run."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("=" * 80)
        print("MIGRATION: Add sp_plus_ratings table")
        print("=" * 80)
        print()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sp_plus_ratings (
                id INTEGER NOT NULL PRIMARY KEY,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                ranking INTEGER NOT NULL,
                rating FLOAT NOT NULL,
                created_at DATETIME NOT NULL,
                CONSTRAINT uq_sp_season_week_team UNIQUE (season, week, team_id),
                FOREIGN KEY(team_id) REFERENCES teams (id)
            )
            """
        )
        print("✓ Table sp_plus_ratings ready")

        for name, cols in [
            ("ix_sp_plus_ratings_season", "season"),
            ("ix_sp_plus_ratings_week", "week"),
            ("ix_sp_plus_ratings_team_id", "team_id"),
            ("idx_sp_season_week", "season, week"),
        ]:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {name} ON sp_plus_ratings ({cols})")
            print(f"✓ Index {name} ready")

        conn.commit()

        cursor.execute("PRAGMA table_info(sp_plus_ratings)")
        print(f"\n✓ Verification: {len(cursor.fetchall())} columns in sp_plus_ratings")
        conn.close()

        print()
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Run the weekly update; SP+ snapshots start accumulating from")
        print("     the current week onward.")
        print("  2. Past weeks CANNOT be backfilled -- CFBD serves only current")
        print("     SP+ values, so an old week would be stamped with ratings that")
        print("     already saw its results.")
        print()

        return 0

    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
