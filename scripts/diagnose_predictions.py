#!/usr/bin/env python3
"""
Diagnostic script to check why predictions aren't being generated
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Game, Season

def main():
    db = SessionLocal()

    print("=" * 60)
    print("PREDICTION DIAGNOSTIC")
    print("=" * 60)
    print()

    # Check current week
    season = db.query(Season).filter(Season.year == 2025).first()
    if season:
        print(f"✓ Current week in DB: {season.current_week}")
        print(f"✓ Season year: {season.year}")
    else:
        print("✗ No season found for 2025!")
        return

    print()

    # Check for week 10 games
    week_10_total = db.query(Game).filter(
        Game.week == 10,
        Game.season == 2025
    ).count()
    print(f"Total week 10 games in DB: {week_10_total}")

    # Check for unprocessed week 10 games
    week_10_unprocessed = db.query(Game).filter(
        Game.week == 10,
        Game.season == 2025,
        Game.is_processed == False
    ).count()
    print(f"Unprocessed week 10 games: {week_10_unprocessed}")

    # Check processed status
    week_10_processed = db.query(Game).filter(
        Game.week == 10,
        Game.season == 2025,
        Game.is_processed == True
    ).count()
    print(f"Processed week 10 games: {week_10_processed}")

    print()

    # Sample a few week 10 games
    print("Sample week 10 games:")
    sample_games = db.query(Game).filter(
        Game.week == 10,
        Game.season == 2025
    ).limit(5).all()

    if sample_games:
        for g in sample_games:
            print(f"  Game {g.id}: Week {g.week}, Season {g.season}, Processed: {g.is_processed}, Home Score: {g.home_score}, Away Score: {g.away_score}")
    else:
        print("  No week 10 games found!")

    print()

    # Check weeks 8-15
    print("Games by week (8-15):")
    for week in range(8, 16):
        total = db.query(Game).filter(
            Game.week == week,
            Game.season == 2025
        ).count()
        unprocessed = db.query(Game).filter(
            Game.week == week,
            Game.season == 2025,
            Game.is_processed == False
        ).count()
        print(f"  Week {week}: {total} total, {unprocessed} unprocessed")

    print()
    print("=" * 60)

    db.close()

if __name__ == "__main__":
    main()
