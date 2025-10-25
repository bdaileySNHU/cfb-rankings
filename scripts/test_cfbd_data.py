#!/usr/bin/env python3
"""
Test what data CFBD returns for future weeks
"""

from dotenv import load_dotenv
import os
import sys

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
    print("TESTING CFBD DATA AVAILABILITY")
    print("=" * 60)
    print()

    season = 2025

    print(f"Checking CFBD for {season} season, weeks 8-15:")
    print()

    for week in range(8, 16):
        print(f"Week {week}:")
        try:
            games = cfbd.get_games(season, week=week, season_type='regular')
            if games:
                print(f"  ✓ Found {len(games)} games")
                # Show first game as sample
                if len(games) > 0:
                    first_game = games[0]
                    home = first_game.get('home_team', 'N/A')
                    away = first_game.get('away_team', 'N/A')
                    print(f"  Sample: {away} @ {home}")
            else:
                print(f"  ✗ No games returned by CFBD")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        print()

    print("=" * 60)

if __name__ == "__main__":
    main()
