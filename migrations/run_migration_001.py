#!/usr/bin/env python3
"""
Run migration 001: Add postseason_name field
EPIC-023 Story 23.1
"""

from src.models.database import SessionLocal, engine
from sqlalchemy import text
import sys


def run_migration():
    """Add postseason_name column to games table"""

    print("="*80)
    print("MIGRATION 001: Add postseason_name field")
    print("="*80)
    print()

    db = SessionLocal()

    try:
        # Check if column already exists
        result = db.execute(text("PRAGMA table_info(games)"))
        columns = [row[1] for row in result.fetchall()]

        if 'postseason_name' in columns:
            print("✓ postseason_name column already exists")
            print()
            db.close()
            return 0

        print("Adding postseason_name column to games table...")

        # Add the column
        db.execute(text(
            "ALTER TABLE games ADD COLUMN postseason_name VARCHAR(100) NULL"
        ))
        db.commit()

        print("✓ Column added successfully")
        print()

        # Verify
        result = db.execute(text(
            "SELECT COUNT(*) as total, "
            "COUNT(postseason_name) as with_names "
            "FROM games"
        ))
        row = result.fetchone()

        print("Verification:")
        print(f"  Total games: {row[0]}")
        print(f"  Games with postseason_name: {row[1]}")
        print(f"  Games with NULL (expected): {row[0] - row[1]}")
        print()

        print("="*80)
        print("✓ Migration complete!")
        print("="*80)

        db.close()
        return 0

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        db.rollback()
        db.close()
        return 1


if __name__ == "__main__":
    sys.exit(run_migration())
