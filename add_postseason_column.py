#!/usr/bin/env python3
"""
Add postseason_name column to games table
"""

from database import SessionLocal
from sqlalchemy import text


def add_column():
    """Add postseason_name column"""

    db = SessionLocal()

    print("="*80)
    print("ADD POSTSEASON_NAME COLUMN")
    print("="*80)
    print()

    try:
        print("Adding postseason_name column to games table...")

        db.execute(text(
            "ALTER TABLE games ADD COLUMN postseason_name VARCHAR(100)"
        ))
        db.commit()

        print("✓ Column added successfully")
        print()

        # Verify
        result = db.execute(text("PRAGMA table_info(games)"))
        columns = [row[1] for row in result.fetchall()]

        if 'postseason_name' in columns:
            print("✓ Verified: postseason_name column exists")
        else:
            print("✗ Verification failed: column not found")

        print()

    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Column already exists")
        else:
            print(f"✗ Error: {e}")
            db.rollback()

    db.close()


if __name__ == "__main__":
    add_column()
