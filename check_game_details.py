#!/usr/bin/env python3
"""
Check detailed information for a specific game
"""

from database import SessionLocal
from models import Team, Game
import sys


def check_game_details(game_id):
    """Check detailed information for a specific game"""

    db = SessionLocal()

    game = db.query(Game).filter(Game.id == game_id).first()

    if not game:
        print(f"Game ID {game_id} not found")
        return 1

    print("="*80)
    print("GAME DETAILS")
    print("="*80)
    print()
    print(f"Game ID: {game.id}")
    print(f"Season: {game.season}")
    print(f"Week: {game.week}")
    print()
    print(f"Home Team: {game.home_team.name} (ID: {game.home_team_id})")
    print(f"Away Team: {game.away_team.name} (ID: {game.away_team_id})")
    print()
    print(f"Score: {game.home_score} - {game.away_score}")
    print(f"Is Processed: {game.is_processed}")
    print(f"Is Neutral Site: {game.is_neutral_site}")
    print(f"Game Type: {game.game_type}")
    print(f"Excluded from Rankings: {game.excluded_from_rankings}")
    print()
    print(f"Home Rating Change: {game.home_rating_change}")
    print(f"Away Rating Change: {game.away_rating_change}")
    print()

    # Check if this game should have been played
    max_week_game = db.query(Game).filter(
        Game.season == game.season,
        Game.is_processed == True
    ).order_by(Game.week.desc()).first()

    if max_week_game:
        print(f"Latest processed week in {game.season}: {max_week_game.week}")
        if game.week < max_week_game.week:
            print(f"⚠️  This game is in Week {game.week}, but Week {max_week_game.week} has been processed")
            print(f"   This game should probably be marked as processed")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_game_details.py <game_id>")
        print()
        print("To find game IDs, use check_team_games.py first")
        sys.exit(1)

    game_id = int(sys.argv[1])
    sys.exit(check_game_details(game_id))
