#!/usr/bin/env python3
"""
Check games for a specific team to diagnose missing games
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


import sys

from database import SessionLocal
from models import Game, Team


def check_team_games(team_id, season):
    """Check all games for a team in a season"""

    db = SessionLocal()

    # Get team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        print(f"Team ID {team_id} not found")
        return 1

    print("="*80)
    print(f"GAMES CHECK: {team.name} - {season}")
    print("="*80)
    print()

    # Get all games (including unprocessed)
    games = db.query(Game).filter(
        ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)),
        Game.season == season
    ).order_by(Game.week).all()

    print(f"Total games: {len(games)}")
    print()

    # Show all games
    print(f"{'Week':<6} {'Game ID':<8} {'Opponent':<30} {'Score':<12} {'Processed':<10} {'Result':<10}")
    print("-"*100)

    for game in games:
        is_home = game.home_team_id == team_id
        opponent = game.away_team if is_home else game.home_team

        location = "Home" if is_home else "Away"
        if game.is_neutral_site:
            location = "Neutral"

        # Score
        if is_home:
            score = f"{game.home_score}-{game.away_score}"
        else:
            score = f"{game.away_score}-{game.home_score}"

        # Result
        if game.is_processed:
            if is_home:
                result = "W" if game.home_score > game.away_score else "L"
            else:
                result = "W" if game.away_score > game.home_score else "L"
        else:
            result = "Not played"
            score = "0-0"

        processed = "Yes" if game.is_processed else "No"

        print(f"{game.week:<6} {game.id:<8} {opponent.name:<30} {score:<12} {processed:<10} {result:<10}")

    print()

    # Summary
    processed_count = sum(1 for g in games if g.is_processed)
    unprocessed_count = len(games) - processed_count

    print("Summary:")
    print(f"  Processed games: {processed_count}")
    print(f"  Unprocessed games: {unprocessed_count}")
    print(f"  Total: {len(games)}")
    print()

    # Check for gaps in weeks
    weeks = [g.week for g in games]
    max_week = max(weeks) if weeks else 0
    missing_weeks = []

    for week in range(1, max_week + 1):
        if week not in weeks:
            missing_weeks.append(week)

    if missing_weeks:
        print(f"⚠️  Missing weeks (no games): {missing_weeks}")
    else:
        print("✓ No gaps in schedule")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_team_games.py <team_id> <season>")
        print("Example: python check_team_games.py 129 2025  (Ohio State)")
        sys.exit(1)

    team_id = int(sys.argv[1])
    season = int(sys.argv[2])

    sys.exit(check_team_games(team_id, season))
