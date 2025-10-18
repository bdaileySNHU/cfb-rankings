"""
Update College Football Games Data
Fetches new games from CollegeFootballData API and adds them to existing database
This does NOT reset your database - it only adds new games
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from database import SessionLocal
from models import Team, Game, Season
from ranking_service import RankingService
from cfbd_client import CFBDClient
from datetime import datetime
import sys
import os


def get_active_season(db) -> int:
    """Get currently active season from database"""
    season = db.query(Season).filter(Season.is_active == True).order_by(Season.year.desc()).first()
    return season.year if season else None


def get_last_imported_week(db, year: int) -> int:
    """Get highest week number in database for season"""
    highest = db.query(Game).filter(Game.season == year).order_by(Game.week.desc()).first()
    return highest.week if highest else 0


def update_games(year: int = None, start_week: int = None, end_week: int = None):
    """
    Update games for specified weeks

    Args:
        year: Season year (defaults to active season in database)
        start_week: First week to import (defaults to next week after last imported)
        end_week: Last week to import (defaults to current week of season from API)
    """

    # Check for API key
    api_key = os.getenv('CFBD_API_KEY')
    if not api_key:
        print("ERROR: No API key found!")
        print("Set CFBD_API_KEY environment variable")
        sys.exit(1)

    # Initialize
    cfbd = CFBDClient(api_key)
    db = SessionLocal()
    ranking_service = RankingService(db)

    print("="*80)
    print("UPDATE COLLEGE FOOTBALL GAMES DATA")
    print("="*80)
    print()

    # Auto-detect season if not provided
    if year is None:
        year = get_active_season(db) or cfbd.get_current_season()
        print(f"✓ Auto-detected season: {year}")

    # Get current season info
    season = db.query(Season).filter(Season.year == year).first()
    if not season:
        print(f"ERROR: Season {year} not found in database")
        print(f"Run import_real_data.py first to initialize the database")
        sys.exit(1)

    # Get all teams
    teams = db.query(Team).all()
    team_objects = {team.name: team for team in teams}

    if not team_objects:
        print(f"ERROR: No teams found in database")
        print(f"Run import_real_data.py first to initialize the database")
        sys.exit(1)

    print(f"Season: {year}")
    print(f"Teams in database: {len(team_objects)}")
    print(f"Current database week: {season.current_week}")
    print()

    # Determine week range to import
    if start_week is None:
        # Auto-detect starting week from last imported week
        start_week = get_last_imported_week(db, year)
        if start_week > 0:
            print(f"✓ Last imported week: {start_week}")
        else:
            start_week = 1
            print(f"✓ No games in database, starting from Week 1")

    if end_week is None:
        # Auto-detect end week from CFBD API
        current_week_api = cfbd.get_current_week(year)
        if current_week_api:
            end_week = current_week_api + 1  # Include in-progress week
            print(f"✓ Current week from API: {current_week_api}")
        else:
            # Fallback to calendar estimation
            estimated_week = cfbd.estimate_current_week(year)
            end_week = max(estimated_week, start_week + 4)
            print(f"✓ Estimated current week: {estimated_week}")

    print(f"Checking weeks {start_week} through {end_week}...")
    print()

    # Import games
    total_imported = 0
    latest_week = season.current_week

    for week in range(start_week, end_week + 1):
        print(f"Week {week}...")
        games_data = cfbd.get_games(year, week=week)

        if not games_data:
            print(f"  No games found for week {week}")
            continue

        week_count = 0

        for game_data in games_data:
            # API uses camelCase
            home_team_name = game_data.get('homeTeam')
            away_team_name = game_data.get('awayTeam')
            home_score = game_data.get('homePoints')
            away_score = game_data.get('awayPoints')

            # Skip if game not completed
            if home_score is None or away_score is None:
                continue

            # Skip if teams not in our database (filters out FCS games)
            if home_team_name not in team_objects or away_team_name not in team_objects:
                continue

            home_team = team_objects[home_team_name]
            away_team = team_objects[away_team_name]

            # Check if game already exists
            existing = db.query(Game).filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.week == week,
                Game.season == year
            ).first()

            if existing:
                continue  # Skip already imported games

            # Create game
            is_neutral = game_data.get('neutralSite', False)

            game = Game(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=home_score,
                away_score=away_score,
                week=week,
                season=year,
                is_neutral_site=is_neutral,
                game_date=datetime.now()
            )

            db.add(game)
            db.commit()
            db.refresh(game)

            # Process game to update rankings
            result = ranking_service.process_game(game)

            winner = result['winner_name']
            loser = result['loser_name']
            score = result['score']

            print(f"  ✓ {winner} defeats {loser} {score}")
            week_count += 1
            total_imported += 1

            # Track latest week with games
            if week > latest_week:
                latest_week = week

        if week_count > 0:
            print(f"  Imported {week_count} games for week {week}")

            # Save rankings for this week
            print(f"  Saving rankings for week {week}...")
            ranking_service.save_weekly_rankings(year, week)
        else:
            print(f"  No new games for week {week}")

    # Update season current week
    if latest_week > season.current_week:
        season.current_week = latest_week
        db.commit()
        print()
        print(f"✓ Updated season current_week to {latest_week}")

    # Show final rankings
    if total_imported > 0:
        print()
        print("="*80)
        print("UPDATED RANKINGS")
        print("="*80)

        rankings = ranking_service.get_current_rankings(year, limit=25)
        print(f"\n{'RANK':<6} {'TEAM':<30} {'RATING':<10} {'RECORD':<10} {'SOS':<10}")
        print("-"*80)

        for r in rankings:
            record = f"{r['wins']}-{r['losses']}"
            print(f"{r['rank']:<6} {r['team_name']:<30} {r['elo_rating']:<10.2f} {record:<10} {r['sos']:<10.2f}")

    print()
    print("="*80)
    print(f"✓ Update Complete!")
    print(f"  - {total_imported} new games imported")
    print(f"  - Current week: {latest_week}")
    print("="*80)

    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Update college football games data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect everything (season, start week, end week)
  python3 update_games.py

  # Override season year
  python3 update_games.py --year 2024

  # Override week range
  python3 update_games.py --start-week 5 --end-week 10

  # Specify all parameters
  python3 update_games.py --year 2024 --start-week 8 --end-week 12
        """
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Season year (default: auto-detect from active season in database)'
    )
    parser.add_argument(
        '--start-week',
        type=int,
        help='First week to check (default: last imported week from database)'
    )
    parser.add_argument(
        '--end-week',
        type=int,
        help='Last week to check (default: current week from CFBD API + 1)'
    )

    args = parser.parse_args()

    update_games(
        year=args.year,
        start_week=args.start_week,
        end_week=args.end_week
    )
