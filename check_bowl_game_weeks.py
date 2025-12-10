#!/usr/bin/env python3
"""
Diagnostic script to check bowl game week numbers from CFBD API.

This script fetches bowl games from the CFBD API and displays their week
numbers to help diagnose why bowl games are being imported with week=1.

Usage:
    python3 check_bowl_game_weeks.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integrations.cfbd_client import CFBDClient


def main():
    """Check bowl game week numbers from CFBD API."""
    # Get API key from environment
    api_key = os.getenv("CFBD_API_KEY")
    if not api_key:
        print("ERROR: CFBD_API_KEY environment variable not set")
        sys.exit(1)

    # Initialize client
    client = CFBDClient(api_key)
    season = 2025

    print(f"\nFetching postseason games for {season}...")
    print("=" * 80)

    # Fetch all postseason games
    postseason_games = client.get_games(season, season_type="postseason", classification="fbs")

    if not postseason_games:
        print("No postseason games found")
        sys.exit(0)

    print(f"Total postseason games: {len(postseason_games)}\n")

    # Categorize games
    bowl_games = []
    playoff_games = []
    conf_championships = []

    for game in postseason_games:
        notes = game.get("notes", "") or ""
        week = game.get("week")
        home = game.get("homeTeam", "Unknown")
        away = game.get("awayTeam", "Unknown")

        game_info = {
            "week": week,
            "notes": notes,
            "home": home,
            "away": away,
        }

        # Categorize
        if any(keyword in notes.lower() for keyword in ["playoff", "semifinal", "national championship"]):
            playoff_games.append(game_info)
        elif "Championship" in notes and any(
            conf in notes for conf in ["ACC", "Big Ten", "Big 12", "SEC", "Pac-12", "American", "MAC", "Mountain West", "Sun Belt"]
        ):
            conf_championships.append(game_info)
        else:
            bowl_games.append(game_info)

    # Display results
    print("\n" + "=" * 80)
    print("CONFERENCE CHAMPIONSHIPS")
    print("=" * 80)
    for game in conf_championships:
        print(f"Week {game['week']:2}: {game['notes'][:50]}")
        print(f"          {game['away']} @ {game['home']}\n")

    print("\n" + "=" * 80)
    print("BOWL GAMES")
    print("=" * 80)
    for game in bowl_games[:10]:  # Show first 10
        print(f"Week {game['week']:2}: {game['notes'][:50]}")
        print(f"          {game['away']} @ {game['home']}\n")

    if len(bowl_games) > 10:
        print(f"... and {len(bowl_games) - 10} more bowl games\n")

    print("\n" + "=" * 80)
    print("PLAYOFF GAMES")
    print("=" * 80)
    for game in playoff_games:
        print(f"Week {game['week']:2}: {game['notes'][:50]}")
        print(f"          {game['away']} @ {game['home']}\n")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Conference Championships: {len(conf_championships)}")
    print(f"Bowl Games: {len(bowl_games)}")
    print(f"Playoff Games: {len(playoff_games)}")
    print(f"Total: {len(conf_championships) + len(bowl_games) + len(playoff_games)}")

    # Check for problematic week numbers
    print("\n" + "=" * 80)
    print("WEEK NUMBER ANALYSIS")
    print("=" * 80)

    bowl_weeks = [g["week"] for g in bowl_games if g["week"] is not None]
    if bowl_weeks:
        min_week = min(bowl_weeks)
        max_week = max(bowl_weeks)
        print(f"Bowl games: Week {min_week} to Week {max_week}")

        if min_week < 15:
            print(f"⚠️  WARNING: Some bowl games have week < 15 (earliest: Week {min_week})")
            print("   This may cause display issues on the frontend.")

    playoff_weeks = [g["week"] for g in playoff_games if g["week"] is not None]
    if playoff_weeks:
        min_week = min(playoff_weeks)
        max_week = max(playoff_weeks)
        print(f"Playoff games: Week {min_week} to Week {max_week}")

    print("=" * 80)


if __name__ == "__main__":
    main()
