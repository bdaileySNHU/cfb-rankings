"""
Update Games for Future Weeks

This script imports new games from CFBD for weeks that aren't in the database yet.
Unlike import_real_data.py, this does NOT reset the database - it only adds new games.

Useful for:
- Adding games for upcoming weeks
- Refreshing game data without losing rankings/predictions
"""

from dotenv import load_dotenv
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from database import SessionLocal
from models import Game, Team
from cfbd_client import CFBDClient
from datetime import datetime


def update_games(db, cfbd: CFBDClient, season: int, start_week: int, end_week: int):
    """
    Import games for specified weeks without resetting database.

    Args:
        db: Database session
        cfbd: CFBD client
        season: Season year
        start_week: First week to import
        end_week: Last week to import
    """
    print(f"\nImporting games for {season}, weeks {start_week}-{end_week}...")

    total_imported = 0
    total_skipped = 0

    for week in range(start_week, end_week + 1):
        print(f"\nWeek {week}:")

        # Get games from CFBD
        games_data = cfbd.get_games(season, week=week, season_type='regular')

        if not games_data:
            print(f"  No games found")
            continue

        week_imported = 0
        week_skipped = 0

        for game_data in games_data:
            home_name = game_data.get('home_team')
            away_name = game_data.get('away_team')

            # Get teams from database
            home_team = db.query(Team).filter(Team.name == home_name).first()
            away_team = db.query(Team).filter(Team.name == away_name).first()

            if not home_team or not away_team:
                # One or both teams not found (might be FCS)
                if not home_team:
                    # Create FCS team
                    home_team = Team(
                        name=home_name,
                        conference='FCS',
                        is_fcs=True,
                        elo_rating=1500.0,
                        initial_rating=1500.0
                    )
                    db.add(home_team)
                    db.flush()

                if not away_team:
                    # Create FCS team
                    away_team = Team(
                        name=away_name,
                        conference='FCS',
                        is_fcs=True,
                        elo_rating=1500.0,
                        initial_rating=1500.0
                    )
                    db.add(away_team)
                    db.flush()

            # Check if game already exists
            existing = db.query(Game).filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.week == week,
                Game.season == season
            ).first()

            if existing:
                week_skipped += 1
                continue

            # Parse game date
            game_date_str = game_data.get('start_date')
            game_date = None
            if game_date_str:
                try:
                    game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                except:
                    pass

            # Determine if game is excluded (FCS matchup)
            is_fcs_game = home_team.is_fcs or away_team.is_fcs

            # Create game record
            game = Game(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=game_data.get('home_points', 0),
                away_score=game_data.get('away_points', 0),
                week=week,
                season=season,
                is_neutral_site=game_data.get('neutral_site', False),
                game_date=game_date,
                is_processed=False,  # Future game, not processed yet
                excluded_from_rankings=is_fcs_game
            )

            db.add(game)
            week_imported += 1

        db.commit()
        print(f"  Imported: {week_imported}, Skipped (already exists): {week_skipped}")

        total_imported += week_imported
        total_skipped += week_skipped

    print(f"\n{'='*60}")
    print(f"TOTAL: Imported {total_imported} games, Skipped {total_skipped}")
    print(f"{'='*60}")


def main():
    """Main function"""
    print("=" * 60)
    print("UPDATE GAMES FOR FUTURE WEEKS")
    print("=" * 60)
    print()

    # Get API key
    api_key = os.getenv('CFBD_API_KEY')
    if not api_key:
        print("ERROR: No CFBD_API_KEY found in environment")
        sys.exit(1)

    # Initialize
    cfbd = CFBDClient(api_key)
    db = SessionLocal()

    # Auto-detect season and current week
    season = cfbd.get_current_season()
    current_week = cfbd.get_current_week(season)
    if current_week is None:
        current_week = cfbd.estimate_current_week(season)

    print(f"Detected: Season {season}, Current Week {current_week}")
    print()

    # Get user input
    start_week_input = input(f"Start week (default: {current_week + 1}): ").strip()
    start_week = int(start_week_input) if start_week_input else (current_week + 1)

    end_week_input = input(f"End week (default: 15): ").strip()
    end_week = int(end_week_input) if end_week_input else 15

    season_input = input(f"Season (default: {season}): ").strip()
    season = int(season_input) if season_input else season

    print()
    print(f"Will import games for {season}, weeks {start_week}-{end_week}")
    confirm = input("Continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("Cancelled")
        sys.exit(0)

    # Update games
    update_games(db, cfbd, season, start_week, end_week)

    db.close()

    print()
    print("✓ Done! Games imported for future weeks.")
    print()
    print("Next steps:")
    print("  1. Predictions will be generated automatically for these games")
    print("  2. Visit the website to see upcoming game predictions")
    print()


if __name__ == "__main__":
    main()
