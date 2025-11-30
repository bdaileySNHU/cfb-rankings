#!/usr/bin/env python3
"""
Debug script to check conference championship API responses
"""

import os
from dotenv import load_dotenv
from cfbd_client import CFBDClient

load_dotenv()

def debug_championships():
    """Check what championship games are returned from API"""

    api_key = os.getenv('CFBD_API_KEY')
    if not api_key:
        print("Error: CFBD_API_KEY not found in environment")
        return

    cfbd = CFBDClient(api_key)
    year = 2024

    print("="*80)
    print(f"DEBUGGING CONFERENCE CHAMPIONSHIPS FOR {year}")
    print("="*80)
    print()

    # Test 1: Get all games from weeks 14-15 WITHOUT classification filter
    print("Test 1: Fetching weeks 14-15 WITHOUT classification filter")
    print("-"*80)
    all_games = []
    for week in [14, 15]:
        week_games = cfbd.get_games(year, week=week, season_type='regular')
        print(f"  Week {week}: {len(week_games)} games")
        all_games.extend(week_games)

    # Count championship games
    championship_games = []
    for game in all_games:
        notes = game.get('notes', '') or ''
        if 'Championship' in notes or 'championship' in notes:
            is_cfp = 'playoff' in notes.lower() or 'semifinal' in notes.lower()
            if not is_cfp:
                championship_games.append(game)

    print(f"  Total championship games: {len(championship_games)}")
    print()

    # Show first 10 championship games
    print("Sample championship games (first 10):")
    for i, game in enumerate(championship_games[:10]):
        notes = game.get('notes', 'No notes')
        home = game.get('home_team', 'Unknown')
        away = game.get('away_team', 'Unknown')
        print(f"  {i+1}. {notes}")
        print(f"     {away} @ {home}")
    print()

    # Test 2: Get games WITH classification='fbs' filter
    print("Test 2: Fetching weeks 14-15 WITH classification='fbs' filter")
    print("-"*80)
    fbs_games = []
    for week in [14, 15]:
        week_games = cfbd.get_games(year, week=week, season_type='regular', classification='fbs')
        print(f"  Week {week}: {len(week_games)} games")
        fbs_games.extend(week_games)

    # Count FBS championship games
    fbs_championship_games = []
    for game in fbs_games:
        notes = game.get('notes', '') or ''
        if 'Championship' in notes or 'championship' in notes:
            is_cfp = 'playoff' in notes.lower() or 'semifinal' in notes.lower()
            if not is_cfp:
                fbs_championship_games.append(game)

    print(f"  Total FBS championship games: {len(fbs_championship_games)}")
    print()

    # Show FBS championship games
    if fbs_championship_games:
        print("FBS championship games found:")
        for i, game in enumerate(fbs_championship_games):
            notes = game.get('notes', 'No notes')
            home = game.get('home_team', 'Unknown')
            away = game.get('away_team', 'Unknown')
            print(f"  {i+1}. {notes}")
            print(f"     {away} @ {home}")
    else:
        print("  ⚠️  NO FBS championship games found with filter!")
        print("  The 'classification' parameter might not be working.")

    print()
    print("="*80)
    print("CONCLUSION")
    print("="*80)
    print(f"Without filter: {len(championship_games)} championship games")
    print(f"With FBS filter: {len(fbs_championship_games)} championship games")

    if len(championship_games) > 0 and len(fbs_championship_games) == 0:
        print()
        print("❌ ISSUE: The 'classification=fbs' parameter appears to be filtering out")
        print("   ALL championship games, including FBS ones.")
        print()
        print("SOLUTION: Remove the classification filter and rely on team_objects")
        print("          filtering (teams not in database will be skipped)")


if __name__ == "__main__":
    debug_championships()
