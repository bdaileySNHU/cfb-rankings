#!/usr/bin/env python3
"""Database Migration: Add calllimit_remaining to api_usage

CFBD reports the account's remaining monthly calls on every response via the
`x-calllimit-remaining` header. Recording it makes quota reporting authoritative
instead of derived: the local api_usage row count only sees calls made from this
host (prod and dev each undercount), and CFBD_MONTHLY_LIMIT is a hand-configured
value that silently goes stale when the plan changes.

Purpose:
    - Add nullable calllimit_remaining column to api_usage

Idempotent:
    - Checks for the column first; re-running is a no-op

Rollback:
    SQLite cannot drop columns before 3.35. The column is nullable and unused by
    older code, so leaving it in place is harmless.
"""

import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def migrate(db_path: Path = None) -> int:
    """Add the calllimit_remaining column if it is not already present."""
    db_path = db_path or project_root / "cfb_rankings.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1

    print(f"Migrating {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(api_usage)")
        columns = [row[1] for row in cursor.fetchall()]

        if not columns:
            print("❌ Table 'api_usage' does not exist — run the app once to create it")
            conn.close()
            return 1

        if "calllimit_remaining" in columns:
            print("⚠️  Column 'calllimit_remaining' already exists — nothing to do")
            conn.close()
            return 0

        cursor.execute("ALTER TABLE api_usage ADD COLUMN calllimit_remaining INTEGER")
        conn.commit()
        conn.close()

        print("✓ Added calllimit_remaining column to api_usage")
        print()
        print("Existing rows stay NULL — the value is only known for calls made")
        print("after this migration. The next CFBD call populates it.")
        print()
        print("Next steps:")
        print("  1. Restart the API service")
        print("  2. Check /api/admin/api-usage for reported_remaining_calls")
        return 0

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  Column 'calllimit_remaining' already exists — migration already applied")
            return 0
        print(f"❌ Migration failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
