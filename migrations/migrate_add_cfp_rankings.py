"""
Add cfp_rankings table
EPIC-046: CFP committee rankings on the comparison page

Stores the College Football Playoff committee's weekly top 25 so ELO
predictions can be graded against it, beside the AP Poll.

A separate table rather than a poll_type row on ap_poll_rankings: that table
carries UNIQUE (season, week, team_id), so a committee row would collide with
the AP row for every team both polls rank.

The app's startup create_all() also creates this table; this script is for
running ahead of a restart, or against a database the app never opens.
"""

import sqlite3
import sys


def migrate(db_path: str = "cfb_rankings.db") -> int:
    """Create the cfp_rankings table and its indexes. Safe to re-run."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cfp_rankings (
                id INTEGER NOT NULL PRIMARY KEY,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                CONSTRAINT uq_cfp_season_week_team UNIQUE (season, week, team_id),
                FOREIGN KEY(team_id) REFERENCES teams (id)
            )
            """
        )
        print("✓ Table cfp_rankings ready")

        for name, cols in [
            ("ix_cfp_rankings_id", "id"),
            ("ix_cfp_rankings_season", "season"),
            ("ix_cfp_rankings_week", "week"),
            ("ix_cfp_rankings_team_id", "team_id"),
            ("idx_cfp_season_week", "season, week"),
        ]:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {name} ON cfp_rankings ({cols})")
            print(f"✓ Index {name} ready")

        conn.commit()
        conn.close()

        print("\nNext: backfill committee weeks with scripts/import_ap_poll_only.py")
        return 0

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate(*sys.argv[1:]))
