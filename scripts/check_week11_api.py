#!/usr/bin/env python3
"""
Check Week 11 Data from CFBD API

Diagnostic script to see what the CFBD API is returning for Week 11 games.
This helps debug why Week 11 isn't being detected as the current week.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cfbd_client import CFBDClient
import json

def main():
    print("Checking CFBD API for Week 11 data...")
    print("=" * 80)

    # Initialize client
    cfbd = CFBDClient()

    # Check current week detection
    print("\n=== CURRENT WEEK DETECTION ===")
    current_week = cfbd.get_current_week(2025)
    print(f"API reports current week: {current_week}")

    # Get Week 11 games
    print("\n=== WEEK 11 GAMES ===")
    week11_games = cfbd.get_games(2025, week=11)

    if not week11_games:
        print("No Week 11 games found in API")
        return

    print(f"Total Week 11 games: {len(week11_games)}")

    # Check for completed games
    completed = []
    upcoming = []

    for game in week11_games:
        # Check BOTH field name formats
        home_score_camel = game.get('homePoints')
        away_score_camel = game.get('awayPoints')
        home_score_snake = game.get('home_points')
        away_score_snake = game.get('away_points')

        home_team = game.get('homeTeam') or game.get('home_team')
        away_team = game.get('awayTeam') or game.get('away_team')

        game_info = {
            'matchup': f"{away_team} @ {home_team}",
            'homePoints_camelCase': home_score_camel,
            'awayPoints_camelCase': away_score_camel,
            'home_points_snake_case': home_score_snake,
            'away_points_snake_case': away_score_snake,
        }

        # Determine if completed (check both formats)
        has_scores = (home_score_camel is not None and away_score_camel is not None) or \
                    (home_score_snake is not None and away_score_snake is not None)

        if has_scores:
            completed.append(game_info)
        else:
            upcoming.append(game_info)

    print(f"\nCompleted games: {len(completed)}")
    print(f"Upcoming games: {len(upcoming)}")

    # Show first 3 completed games
    if completed:
        print("\n=== SAMPLE COMPLETED GAMES ===")
        for i, game in enumerate(completed[:3], 1):
            print(f"\nGame {i}: {game['matchup']}")
            print(f"  homePoints (camelCase): {game['homePoints_camelCase']}")
            print(f"  awayPoints (camelCase): {game['awayPoints_camelCase']}")
            print(f"  home_points (snake_case): {game['home_points_snake_case']}")
            print(f"  away_points (snake_case): {game['away_points_snake_case']}")

    # Show first upcoming game structure
    if upcoming:
        print("\n=== SAMPLE UPCOMING GAME ===")
        game = upcoming[0]
        print(f"\nGame: {game['matchup']}")
        print(f"  homePoints (camelCase): {game['homePoints_camelCase']}")
        print(f"  awayPoints (camelCase): {game['awayPoints_camelCase']}")
        print(f"  home_points (snake_case): {game['home_points_snake_case']}")
        print(f"  away_points (snake_case): {game['away_points_snake_case']}")

    # Show full structure of first game
    print("\n=== FULL FIRST GAME STRUCTURE ===")
    print(json.dumps(week11_games[0], indent=2))

    print("\n" + "=" * 80)
    print("Diagnostic complete!")

if __name__ == "__main__":
    main()
