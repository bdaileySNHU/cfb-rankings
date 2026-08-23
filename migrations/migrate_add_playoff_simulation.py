#!/usr/bin/env python3
"""Database Migration: Add the playoff_simulation cache table

Creates the table that holds the cached Monte Carlo playoff projection:
    - season      (INTEGER)  season the projection covers
    - week        (INTEGER)  week the season had reached when it ran
    - runs        (INTEGER)  number of simulated seasons behind the numbers
    - payload     (TEXT)     the full projection, JSON encoded
    - created_at  (DATETIME) when the simulation ran

Ten thousand simulated seasons take several seconds, which is too slow for a web
request and pointless to repeat — the answer only moves when new results land.
The weekly import writes here; the API reads.

Idempotent: uses CREATE TABLE IF NOT EXISTS. Safe to run multiple times.

Rollback: DROP TABLE playoff_simulation. The projection endpoint falls back to
the deterministic current-ratings bracket when no row is present, so dropping
the table degrades the feature rather than breaking it.
"""

import sqlite3
import sys

DDL = """
CREATE TABLE IF NOT EXISTS playoff_simulation (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    season      INTEGER  NOT NULL,
    week        INTEGER  NOT NULL,
    runs        INTEGER  NOT NULL,
    payload     TEXT     NOT NULL,
    created_at  DATETIME NOT NULL,
    CONSTRAINT uq_playoff_sim_season_week UNIQUE (season, week)
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_playoff_simulation_season ON playoff_simulation (season)",
    "CREATE INDEX IF NOT EXISTS ix_playoff_simulation_week ON playoff_simulation (week)",
]


def migrate(db_path: str = "cfb_rankings.db") -> int:
    print("=" * 70)
    print("MIGRATION: Add playoff_simulation table")
    print("=" * 70)
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        existed = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='playoff_simulation'"
        ).fetchone()
        cur.execute(DDL)
        for stmt in INDEXES:
            cur.execute(stmt)
        conn.commit()
        conn.close()
        if existed:
            print("⚠️  Table 'playoff_simulation' already exists — skipping")
        else:
            print("✓ Created table playoff_simulation")
        print("\n✓ Migration complete")
        return 0
    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate(sys.argv[1] if len(sys.argv) > 1 else "cfb_rankings.db"))
