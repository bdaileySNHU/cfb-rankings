#!/usr/bin/env python3
"""Report tables and columns the models expect but the database does not have.

Deploys drift when a migration is skipped: the code queries a column that was
never added and every request touching that table 500s. Run this after a deploy,
before restarting, so the failure shows up as a list instead of a traceback.

Exits non-zero when something is missing, so it can gate a deploy script.
"""

import os
import sqlite3
import sys

# Run as `python scripts/check_schema.py`, sys.path[0] is scripts/, not the
# repo root, so `src` is not importable without this.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import DATABASE_URL
from src.models.models import Base


def main() -> int:
    if not DATABASE_URL.startswith("sqlite"):
        print(f"Not a SQLite database ({DATABASE_URL}) — nothing to check.")
        return 0
    path = DATABASE_URL.split("///", 1)[1]

    # DATABASE_URL is relative, so a wrong cwd would have sqlite3 create an
    # empty file here and report every table as missing. Say which file is
    # actually absent instead.
    if not os.path.exists(path):
        print(f"No database at {os.path.abspath(path)} (cwd {os.getcwd()}).")
        return 1

    conn = sqlite3.connect(path)
    have = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    missing_tables, missing_columns = [], []
    for name, table in Base.metadata.tables.items():
        if name not in have:
            missing_tables.append(name)
            continue
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}
        for column in table.columns:
            if column.name not in cols:
                missing_columns.append(f"{name}.{column.name}")
    conn.close()

    for t in missing_tables:
        print(f"MISSING TABLE   {t}")
    for c in missing_columns:
        print(f"MISSING COLUMN  {c}")
    if missing_tables or missing_columns:
        print(f"\n✗ {path} is behind the models. Run the migrations in migrations/.")
        return 1
    print(f"✓ {path} matches the models.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
