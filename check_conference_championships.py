#!/usr/bin/env python3
"""
Check conference championship games in database for Story 22.3
"""

from database import SessionLocal
from models import Game
import sys


def check_conference_championships(season=2025):
    """Check all conference championship games for a season"""

    db = SessionLocal()

    print("="*80)
    print(f"CONFERENCE CHAMPIONSHIP GAMES - {season}")
    print("="*80)
    print()

    # Get all conference championship games
    conf_champ_games = db.query(Game).filter(
        Game.season == season,
        Game.game_type == 'conference_championship'
    ).order_by(Game.week).all()

    print(f"Total conference championship games: {len(conf_champ_games)}")
    print()

    if not conf_champ_games:
        print("⚠️  No conference championship games found")
        print("   Run import_real_data.py to import postseason games")
        db.close()
        return 1

    # Display each game
    print(f"{'Week':<6} {'Game ID':<8} {'Matchup':<50} {'Score':<12} {'Processed':<10}")
    print("-"*100)

    for game in conf_champ_games:
        matchup = f"{game.away_team.name} @ {game.home_team.name}"

        if game.is_processed:
            score = f"{game.away_score}-{game.home_score}"
            processed = "Yes"
        else:
            score = "TBD"
            processed = "No"

        print(f"{game.week:<6} {game.id:<8} {matchup:<50} {score:<12} {processed:<10}")

    print()

    # Summary statistics
    processed_count = sum(1 for g in conf_champ_games if g.is_processed)
    unprocessed_count = len(conf_champ_games) - processed_count

    print("Summary:")
    print(f"  Processed: {processed_count}")
    print(f"  Unprocessed: {unprocessed_count}")
    print(f"  Total: {len(conf_champ_games)}")
    print()

    # Check for teams that played in championships
    print("Teams in Conference Championships:")
    print()

    teams_in_champs = set()
    for game in conf_champ_games:
        if game.is_processed:
            teams_in_champs.add((game.home_team.name, game.home_team.id,
                               game.home_score > game.away_score))
            teams_in_champs.add((game.away_team.name, game.away_team.id,
                               game.away_score > game.home_score))

    for team_name, team_id, won in sorted(teams_in_champs, key=lambda x: x[0]):
        result = "Won" if won else "Lost"
        print(f"  {team_name:<40} (ID: {team_id:<4})  {result}")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    season = 2025
    if len(sys.argv) > 1:
        season = int(sys.argv[1])

    sys.exit(check_conference_championships(season))
