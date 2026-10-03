"""
Add betting_lines table
ELO vs Vegas spread comparison

One consensus closing spread per game (median across CFBD /lines providers),
home-team perspective: negative = home favored.
"""

import sqlite3
import sys


def migrate(db_path: str = "cfb_rankings.db") -> int:
    """Create the betting_lines table. Safe to re-run."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS betting_lines (
                id INTEGER NOT NULL PRIMARY KEY,
                game_id INTEGER NOT NULL UNIQUE,
                spread FLOAT NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(game_id) REFERENCES games (id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS ix_betting_lines_game_id ON betting_lines (game_id)")
        conn.commit()
        conn.close()
        print("✓ Table betting_lines ready")
        print()
        print("Next: the weekly import fills the current season. Closing lines never")
        print("change, so past seasons can be backfilled (one API call each):")
        print("  set -a && source .env && set +a && python -c \"from src.models.database import SessionLocal; "
              "from src.models.models import Team; from src.integrations.cfbd_client import CFBDClient; "
              "from src.importers.polls import import_betting_lines as f; db=SessionLocal(); "
              "t={x.name: x for x in db.query(Team)}; [print(y, f(CFBDClient(), db, t, y)) for y in (2024, 2025)]\"")
        return 0
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
