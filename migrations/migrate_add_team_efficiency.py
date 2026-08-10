#!/usr/bin/env python3
"""Database Migration: Add efficiency columns to teams

Adds the EPIC-045 CORE-style efficiency columns to the existing teams table:
    - offense_ppa (FLOAT)  opponent-adjusted offensive PPA per play, NULL until imported
    - defense_ppa (FLOAT)  opponent-adjusted defensive PPA allowed per play

Idempotent: skips columns that already exist. Safe to run multiple times.

Rollback: columns are nullable; with EFFICIENCY_WEIGHT=0 they are ignored entirely,
so leaving them in place is harmless.

Part of: EPIC-045 (CORE-style efficiency blend) - Story 45.2
"""

import sqlite3
import sys

COLUMNS = [
    ("offense_ppa", "FLOAT"),
    ("defense_ppa", "FLOAT"),
]


def migrate(db_path: str = "cfb_rankings.db") -> int:
    print("=" * 70)
    print("MIGRATION: Add efficiency columns to teams (EPIC-045)")
    print("=" * 70)
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for name, coltype in COLUMNS:
            try:
                cur.execute(f"ALTER TABLE teams ADD COLUMN {name} {coltype}")
                print(f"✓ Added column {name} {coltype}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️  Column '{name}' already exists — skipping")
                else:
                    raise
        conn.commit()
        conn.close()
        print("\n✓ Migration complete")
        return 0
    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
