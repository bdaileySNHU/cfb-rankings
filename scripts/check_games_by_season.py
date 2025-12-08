#!/usr/bin/env python3
"""
Check what games exist in the database by season
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Game


def main():
    db = SessionLocal()

    print("=" * 60)
    print("GAMES BY SEASON AND WEEK")
    print("=" * 60)
    print()

    # Check 2024 season
    print("2024 Season:")
    for week in range(8, 16):
        count = db.query(Game).filter(
            Game.week == week,
            Game.season == 2024
        ).count()
        if count > 0:
            print(f"  Week {week}: {count} games")

    print()

    # Check 2025 season
    print("2025 Season:")
    for week in range(1, 16):
        count = db.query(Game).filter(
            Game.week == week,
            Game.season == 2025
        ).count()
        if count > 0:
            print(f"  Week {week}: {count} games")

    print()

    # Total games by season
    total_2024 = db.query(Game).filter(Game.season == 2024).count()
    total_2025 = db.query(Game).filter(Game.season == 2025).count()

    print(f"Total 2024 games: {total_2024}")
    print(f"Total 2025 games: {total_2025}")

    print()
    print("=" * 60)

    db.close()

if __name__ == "__main__":
    main()
