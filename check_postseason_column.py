#!/usr/bin/env python3
"""
Check if postseason_name column exists in games table
"""

from database import SessionLocal
from sqlalchemy import text


def check_column():
    """Check if postseason_name column exists"""

    db = SessionLocal()

    print("="*80)
    print("CHECK POSTSEASON_NAME COLUMN")
    print("="*80)
    print()

    # Get table info
    result = db.execute(text("PRAGMA table_info(games)"))
    columns = {row[1]: row[2] for row in result.fetchall()}  # name: type

    if 'postseason_name' in columns:
        print(f"✓ postseason_name column exists")
        print(f"  Type: {columns['postseason_name']}")
        print()

        # Check if any games have postseason names
        result = db.execute(text(
            "SELECT COUNT(*) as total, "
            "COUNT(postseason_name) as with_names "
            "FROM games"
        ))
        row = result.fetchone()

        print(f"Games in database:")
        print(f"  Total: {row[0]}")
        print(f"  With postseason_name: {row[1]}")
        print(f"  Without postseason_name: {row[0] - row[1]}")
    else:
        print("✗ postseason_name column does NOT exist")
        print()
        print("Run migration:")
        print("  ALTER TABLE games ADD COLUMN postseason_name VARCHAR(100) NULL;")

    print()

    db.close()


if __name__ == "__main__":
    check_column()
