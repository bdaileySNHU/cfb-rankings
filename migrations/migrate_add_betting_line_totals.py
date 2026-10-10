"""
Add over_under and moneyline columns to betting_lines

Medians across CFBD /lines providers, stored next to the spread for future
model comparisons. Nullable: not every provider posts them.
"""

import sqlite3
import sys

COLUMNS = (("over_under", "FLOAT"), ("home_moneyline", "INTEGER"), ("away_moneyline", "INTEGER"))


def migrate(db_path: str = "cfb_rankings.db") -> int:
    """Add the columns that are missing. Safe to re-run."""
    try:
        conn = sqlite3.connect(db_path)
        have = {row[1] for row in conn.execute("PRAGMA table_info(betting_lines)")}
        if not have:
            print("❌ betting_lines table missing — run migrate_add_betting_lines.py first")
            return 1
        for name, sql_type in COLUMNS:
            if name in have:
                print(f"  {name} already present")
            else:
                conn.execute(f"ALTER TABLE betting_lines ADD COLUMN {name} {sql_type}")
                print(f"✓ Added betting_lines.{name}")
        conn.commit()
        conn.close()
        print()
        print("Next: re-run the betting-line import to fill them (one API call per season):")
        print("  set -a && source .env && set +a && python -c \"from src.models.database import SessionLocal; "
              "from src.models.models import Team; from src.integrations.cfbd_client import CFBDClient; "
              "from src.importers.polls import import_betting_lines as f; db=SessionLocal(); "
              "t={x.name: x for x in db.query(Team)}; [print(y, f(CFBDClient(), db, t, y)) for y in (2024, 2025, 2026)]\"")
        return 0
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate(*sys.argv[1:2]))
