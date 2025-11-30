#!/usr/bin/env python3
"""
Find teams that played in conference championships
Used for testing Story 22.2 frontend display
"""

from database import SessionLocal
from models import Game, Team
import sys


def find_championship_teams():
    """Find all teams that played in conference championships"""
    try:
        db = SessionLocal()

        # Find all conference championship games
        champ_games = db.query(Game).filter(
            Game.game_type == 'conference_championship',
            Game.season == 2024
        ).order_by(Game.week).all()

        if not champ_games:
            print("No conference championship games found for 2024")
            print("Did you run the import? Try: import_real_data.py --season 2024")
            return 1

        print("=" * 80)
        print("CONFERENCE CHAMPIONSHIP GAMES - 2024")
        print("=" * 80)
        print()

        for game in champ_games:
            away_team = game.away_team
            home_team = game.home_team

            print(f"Week {game.week}: {game.notes if hasattr(game, 'notes') else 'Championship Game'}")
            print(f"  {away_team.name} @ {home_team.name}")

            if game.is_processed:
                winner = away_team if game.away_score > game.home_score else home_team
                score = f"{game.away_score}-{game.home_score}"
                print(f"  Final Score: {score} (Winner: {winner.name})")
            else:
                print(f"  Status: Scheduled (not played yet)")

            print()
            print(f"  TEST URLs:")
            print(f"    Away Team: https://cfb.bdailey.com/team.html?id={away_team.id}&season=2024")
            print(f"               ({away_team.name} - ID: {away_team.id})")
            print(f"    Home Team: https://cfb.bdailey.com/team.html?id={home_team.id}&season=2024")
            print(f"               ({home_team.name} - ID: {home_team.id})")
            print()
            print("-" * 80)
            print()

        print("=" * 80)
        print("TESTING INSTRUCTIONS")
        print("=" * 80)
        print()
        print("1. Open any of the TEST URLs above in your browser")
        print("2. Scroll to the schedule table")
        print("3. Find the Week 14 game")
        print("4. Look for a GOLD badge with text 'CONF CHAMP' next to the opponent name")
        print("5. Hover over the badge to see tooltip: 'Conference Championship Game'")
        print()
        print("Expected Result:")
        print("  - Gold badge appears next to opponent name")
        print("  - Badge text: 'CONF CHAMP'")
        print("  - Tooltip on hover: 'Conference Championship Game'")
        print("  - Regular season games (Weeks 1-13) have NO badge")
        print()

        db.close()
        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(find_championship_teams())
