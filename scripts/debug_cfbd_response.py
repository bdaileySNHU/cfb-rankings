#!/usr/bin/env python3
"""
Debug the actual CFBD API response structure
"""

import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from cfbd_client import CFBDClient


def main():
    api_key = os.getenv('CFBD_API_KEY')
    if not api_key:
        print("ERROR: No CFBD_API_KEY found")
        sys.exit(1)

    cfbd = CFBDClient(api_key)

    print("=" * 60)
    print("CFBD API RESPONSE DEBUG")
    print("=" * 60)
    print()

    # Get week 10 games
    print("Fetching week 10 games for 2025 season...")
    games = cfbd.get_games(2025, week=10, season_type='regular')

    if not games:
        print("No games returned!")
        return

    print(f"Found {len(games)} games")
    print()

    # Show first 3 games with full structure
    print("First 3 games (full data):")
    print()
    for i, game in enumerate(games[:3], 1):
        print(f"Game {i}:")
        print(json.dumps(game, indent=2, default=str))
        print()
        print("-" * 60)
        print()

    print("=" * 60)

if __name__ == "__main__":
    main()
