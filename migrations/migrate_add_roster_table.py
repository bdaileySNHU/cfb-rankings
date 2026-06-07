#!/usr/bin/env python3
"""Database Migration: Add roster_players Table

Adds the roster_players table that holds season-scoped roster snapshots, so
position strength can reflect a team's actual roster (transfers in, departures
out, all class years) rather than recruiting-class signings.

Purpose:
    - Create roster_players table as defined by the RosterPlayer model
    - Unique constraint on (season, team_id, athlete_id)
    - Composite index on (season, team_id, position) for position queries

Idempotent:
    - Uses checkfirst=True to avoid errors if the table already exists
    - Safe to run multiple times

Rollback:
    DROP TABLE IF EXISTS roster_players;

Part of: EPIC-039 (Roster-Based Position Strength) - Story 39.3
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.database import SessionLocal, engine
from src.models.models import RosterPlayer


def migrate():
    """Create the roster_players table (idempotent).

    Returns:
        bool: True if migration successful, False otherwise
    """
    print("Creating roster_players table...")

    try:
        RosterPlayer.__table__.create(engine, checkfirst=True)
        print("✓ roster_players table created successfully!")

        db = SessionLocal()
        try:
            count = db.query(RosterPlayer).count()
            print(f"✓ Table verified - currently {count} roster rows stored")
        except Exception as e:
            print(f"✗ Error verifying table: {e}")
            return False
        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


if __name__ == "__main__":
    sys.exit(0 if migrate() else 1)
