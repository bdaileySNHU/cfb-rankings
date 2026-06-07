#!/usr/bin/env python3
"""Database Migration: Add production columns to roster_players

Adds the EPIC-040 production-blend columns to the existing roster_players table:
    - production_score  (FLOAT)   0–100 normalized on-field production, NULL if none
    - production_source (VARCHAR) 'ppa' | 'recruiting' | 'none'
    - blended_rating    (FLOAT)   0–100 quality used by scoring when blend is on

Idempotent: skips columns that already exist. Safe to run multiple times.

Rollback (SQLite has no DROP COLUMN pre-3.35; recreate table if needed):
    -- generally not required; columns are nullable and unused unless blend=on

Part of: EPIC-040 (Production-Blended Position Strength) - Story 40.3
"""

import sqlite3
import sys

COLUMNS = [
    ("production_score", "FLOAT"),
    ("production_source", "VARCHAR(20)"),
    ("blended_rating", "FLOAT"),
]


def migrate(db_path: str = "cfb_rankings.db") -> int:
    print("=" * 70)
    print("MIGRATION: Add production columns to roster_players (EPIC-040)")
    print("=" * 70)
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for name, coltype in COLUMNS:
            try:
                cur.execute(f"ALTER TABLE roster_players ADD COLUMN {name} {coltype}")
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
