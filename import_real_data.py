"""
Import Real College Football Data
Fetches data from CollegeFootballData API and populates the database
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from database import SessionLocal, reset_db
from models import Team, Game, Season, ConferenceType
from ranking_service import RankingService
from cfbd_client import CFBDClient
from datetime import datetime
import sys
import argparse


# Conference mapping from CFBD to our system
CONFERENCE_MAP = {
    'SEC': ConferenceType.POWER_5,
    'Big Ten': ConferenceType.POWER_5,
    'ACC': ConferenceType.POWER_5,
    'Big 12': ConferenceType.POWER_5,
    'Pac-12': ConferenceType.POWER_5,
    'American Athletic': ConferenceType.GROUP_5,
    'Mountain West': ConferenceType.GROUP_5,
    'Conference USA': ConferenceType.GROUP_5,
    'Mid-American': ConferenceType.GROUP_5,
    'Sun Belt': ConferenceType.GROUP_5,
    'FBS Independents': ConferenceType.GROUP_5,
}


def validate_api_connection(cfbd: CFBDClient, year: int) -> bool:
    """
    Test CFBD API connectivity and authentication.

    Args:
        cfbd: CFBD client instance
        year: Year to test with

    Returns:
        bool: True if API accessible, False otherwise
    """
    try:
        print("Validating CFBD API connection...")
        teams = cfbd.get_teams(year)
        if teams and len(teams) > 0:
            print(f"✓ API Connection OK ({len(teams)} teams found)")
            return True
        else:
            print("✗ API Connection Failed: No teams returned")
            return False
    except Exception as e:
        print(f"✗ API Connection Failed: {e}")
        return False


def get_week_statistics(cfbd: CFBDClient, year: int, week: int) -> dict:
    """
    Get statistics about games available for a given week.

    Args:
        cfbd: CFBD client instance
        year: Season year
        week: Week number

    Returns:
        dict: Statistics including total games, completed games
    """
    games = cfbd.get_games(year, week=week)
    if not games:
        return {"total": 0, "completed": 0, "scheduled": 0}

    completed = sum(1 for g in games if g.get('homePoints') is not None and g.get('awayPoints') is not None)
    total = len(games)

    return {
        "total": total,
        "completed": completed,
        "scheduled": total - completed
    }


def import_teams(cfbd: CFBDClient, db, year: int):
    """Import all FBS teams"""
    print(f"\nImporting FBS teams for {year}...")

    # Fetch teams from CFBD
    teams_data = cfbd.get_teams(year)
    if not teams_data:
        print("✗ Failed to fetch teams from CFBD API")
        return {}

    # Fetch recruiting data
    print("Fetching recruiting rankings...")
    recruiting_data = cfbd.get_recruiting_rankings(year) or []
    recruiting_map = {r['team']: r['rank'] for r in recruiting_data if 'team' in r and 'rank' in r}

    # Fetch talent ratings
    print("Fetching talent composite...")
    talent_data = cfbd.get_team_talent(year) or []
    talent_map = {t['school']: t['talent'] for t in talent_data if 'school' in t and 'talent' in t}

    # Fetch returning production
    print("Fetching returning production...")
    returning_data = cfbd.get_returning_production(year) or []
    returning_map = {}
    for r in returning_data:
        if 'team' in r and 'returningProduction' in r:
            team = r['team']
            prod = r['returningProduction']
            # Average the returning production percentage
            if isinstance(prod, dict):
                values = [v for v in prod.values() if isinstance(v, (int, float))]
                returning_map[team] = sum(values) / len(values) / 100 if values else 0.5
            elif isinstance(prod, (int, float)):
                returning_map[team] = prod / 100

    team_objects = {}
    ranking_service = RankingService(db)

    for team_data in teams_data:
        team_name = team_data['school']
        conference_name = team_data.get('conference', 'FBS Independents')

        # Map conference
        conference = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)

        # Get preseason data
        recruiting_rank = recruiting_map.get(team_name, 999)
        transfer_rank = 999  # CFBD doesn't have transfer portal rankings easily accessible
        returning_prod = returning_map.get(team_name, 0.5)

        # Create team
        team = Team(
            name=team_name,
            conference=conference,
            recruiting_rank=recruiting_rank,
            transfer_rank=transfer_rank,
            returning_production=returning_prod
        )

        ranking_service.initialize_team_rating(team)
        db.add(team)
        team_objects[team_name] = team

        print(f"  Added: {team_name} ({conference.value}) - Recruiting: #{recruiting_rank}, Returning: {returning_prod*100:.0f}%")

    db.commit()
    print(f"\n✓ Imported {len(team_objects)} teams")
    return team_objects


def import_games(cfbd: CFBDClient, db, team_objects: dict, year: int, max_week: int = None, validate_only: bool = False, strict: bool = False):
    """
    Import games for the season with validation and completeness reporting.

    Args:
        cfbd: CFBD client instance
        db: Database session
        team_objects: Dictionary mapping team names to Team objects
        year: Season year
        max_week: Maximum week to import
        validate_only: If True, don't actually import (dry-run)
        strict: If True, fail on validation warnings

    Returns:
        dict: Import statistics including total imported, skipped, etc.
    """
    print(f"\nImporting games for {year}...")
    if validate_only:
        print("**VALIDATION MODE** - No changes will be made to database\n")

    ranking_service = RankingService(db)

    # Determine which weeks to import
    weeks = range(1, (max_week or 15) + 1)

    # Track statistics
    total_imported = 0
    total_skipped = 0
    skipped_fcs = 0
    skipped_not_found = 0
    skipped_incomplete = 0
    skipped_details = []  # List of (week, reason, game_description) tuples

    for week in weeks:
        print(f"\nWeek {week}...")
        games_data = cfbd.get_games(year, week=week)

        if not games_data:
            print(f"  No games found for week {week}")
            continue

        # Get week statistics for validation
        week_stats = get_week_statistics(cfbd, year, week)
        week_imported = 0
        week_skipped = 0

        for game_data in games_data:
            # API uses camelCase
            home_team_name = game_data.get('homeTeam')
            away_team_name = game_data.get('awayTeam')
            home_score = game_data.get('homePoints')
            away_score = game_data.get('awayPoints')

            game_desc = f"{away_team_name} @ {home_team_name}"

            # Skip if game not completed
            if home_score is None or away_score is None:
                week_skipped += 1
                skipped_incomplete += 1
                skipped_details.append((week, "Game not completed", game_desc))
                continue

            # Skip if teams not in our database (filters out FCS games)
            if home_team_name not in team_objects or away_team_name not in team_objects:
                week_skipped += 1
                total_skipped += 1

                # Determine if it's FCS or just not found
                if home_team_name not in team_objects and away_team_name not in team_objects:
                    skipped_not_found += 1
                    skipped_details.append((week, "Teams not in database", game_desc))
                elif home_team_name not in team_objects:
                    skipped_fcs += 1
                    skipped_details.append((week, f"{home_team_name} not in database (likely FCS)", game_desc))
                else:
                    skipped_fcs += 1
                    skipped_details.append((week, f"{away_team_name} not in database (likely FCS)", game_desc))
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
                continue

            # In validate-only mode, just count
            if validate_only:
                week_imported += 1
                total_imported += 1
                continue

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
                game_date=datetime.now()  # CFBD has date but in different format
            )

            db.add(game)
            db.commit()
            db.refresh(game)

            # Process game to update rankings
            result = ranking_service.process_game(game)

            winner = result['winner_name']
            loser = result['loser_name']
            score = result['score']

            print(f"    {winner} defeats {loser} {score}")
            week_imported += 1
            total_imported += 1

        # Print week summary
        total_week_games = week_stats['completed']
        if total_week_games > 0:
            completion_rate = (week_imported / total_week_games) * 100
            status = "✓" if completion_rate >= 95 else "⚠"
            print(f"\n  {status} Week {week} Summary:")
            print(f"    Expected: {total_week_games} games")
            print(f"    Imported: {week_imported} games ({completion_rate:.0f}%)")
            if week_skipped > 0:
                print(f"    Skipped: {week_skipped} games")

    # Print final import summary
    print("\n" + "="*80)
    print("IMPORT SUMMARY")
    print("="*80)
    print(f"Total Games Imported: {total_imported}")
    print(f"Total Games Skipped: {total_skipped}")
    if skipped_fcs > 0:
        print(f"  - FCS Opponents: {skipped_fcs}")
    if skipped_not_found > 0:
        print(f"  - Team Not Found: {skipped_not_found}")
    if skipped_incomplete > 0:
        print(f"  - Incomplete Games: {skipped_incomplete}")

    # Show details of skipped games (limit to first 10)
    if skipped_details and not validate_only:
        print(f"\nSkipped Game Details (showing first 10 of {len(skipped_details)}):")
        for week, reason, game in skipped_details[:10]:
            print(f"  Week {week}: {game} - {reason}")

    # Check for strict mode failures
    if strict and total_skipped > 0:
        print("\n✗ STRICT MODE: Import failed due to skipped games")
        sys.exit(1)

    print("="*80)

    return {
        "imported": total_imported,
        "skipped": total_skipped,
        "skipped_fcs": skipped_fcs,
        "skipped_not_found": skipped_not_found,
        "skipped_incomplete": skipped_incomplete
    }


def main():
    """Main import function"""
    print("="*80)
    print("COLLEGE FOOTBALL DATA IMPORT")
    print("="*80)
    print()
    print("This script imports real college football data from CollegeFootballData.com")
    print()

    # Parse command-line arguments
    import os
    api_key = os.getenv('CFBD_API_KEY')

    # Initialize CFBD client first (needed for auto-detection)
    if not api_key:
        print("ERROR: No API key found!")
        print()
        print("To get real data:")
        print("1. Visit: https://collegefootballdata.com/key")
        print("2. Sign up for a free API key")
        print("3. Set environment variable:")
        print("   export CFBD_API_KEY='your-key-here'")
        print()
        print("Then run this script again.")
        sys.exit(1)

    cfbd = CFBDClient(api_key)

    # Auto-detect current season and week
    current_season = cfbd.get_current_season()
    max_week_available = cfbd.get_current_week(current_season)

    # If API doesn't have week data yet, estimate from calendar
    if max_week_available is None:
        max_week_available = cfbd.estimate_current_week(current_season)
        if max_week_available == 0:
            max_week_available = 1  # Default to week 1 if pre-season

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Import college football data from CFBD API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Auto-detect season and import all available weeks
  python3 import_real_data.py

  # Override season year
  python3 import_real_data.py --season 2024

  # Override max week to import
  python3 import_real_data.py --max-week 10

  # Specify both
  python3 import_real_data.py --season 2024 --max-week 12
        """
    )
    parser.add_argument(
        '--season',
        type=int,
        help=f'Season year (default: auto-detect, currently {current_season})'
    )
    parser.add_argument(
        '--max-week',
        type=int,
        help=f'Maximum week to import (default: all available, currently {max_week_available})'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate import without making changes (dry-run mode)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fail on validation warnings (exit with error if games skipped)'
    )

    args = parser.parse_args()

    # Use overrides or detected values
    season = args.season or current_season
    max_week = args.max_week or max_week_available

    # Validate API connection
    if not validate_api_connection(cfbd, season):
        print("\n✗ Cannot proceed without valid API connection")
        sys.exit(1)

    print(f"✓ Detected current season: {current_season}")
    print(f"✓ Latest completed week: {max_week_available}")
    if args.season:
        print(f"  → Using season override: {season}")
    if args.max_week:
        print(f"  → Using max week override: {max_week}")
    if args.validate_only:
        print(f"  → VALIDATE-ONLY MODE: No database changes will be made")
    if args.strict:
        print(f"  → STRICT MODE: Will fail on validation warnings")
    print()

    # Initialize database
    db = SessionLocal()

    # Confirm reset
    print("WARNING: This will reset your database and replace all data!")
    response = input("Continue? (yes/no): ")

    if response.lower() != 'yes':
        print("Cancelled.")
        return

    # Reset database
    print("\nResetting database...")
    reset_db()

    # Create season
    print(f"Creating {season} season...")
    season_obj = Season(year=season, current_week=0, is_active=True)
    db.add(season_obj)
    db.commit()

    # Import teams
    team_objects = import_teams(cfbd, db, year=season)

    if not team_objects:
        print("\nFailed to import teams. Check your API key.")
        return

    # Import games (using detected/overridden max_week)
    print(f"\nImporting games through Week {max_week}...")
    import_stats = import_games(
        cfbd, db, team_objects,
        year=season,
        max_week=max_week,
        validate_only=args.validate_only,
        strict=args.strict
    )

    # Skip remaining steps if validate-only mode
    if args.validate_only:
        print("\n✓ Validation complete - no changes made to database")
        db.close()
        return

    # Update season current week
    season_obj.current_week = max_week
    db.commit()

    # Save rankings
    print("\nSaving final rankings...")
    ranking_service = RankingService(db)
    for week in range(1, max_week + 1):
        ranking_service.save_weekly_rankings(season, week)

    # Show final rankings
    print("\n" + "="*80)
    print("FINAL RANKINGS")
    print("="*80)

    rankings = ranking_service.get_current_rankings(season, limit=25)
    print(f"\n{'RANK':<6} {'TEAM':<30} {'RATING':<10} {'RECORD':<10} {'SOS':<10}")
    print("-"*80)

    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        print(f"{r['rank']:<6} {r['team_name']:<30} {r['elo_rating']:<10.2f} {record:<10} {r['sos']:<10.2f}")

    print()
    print("="*80)
    print(f"✓ Import Complete!")
    print(f"  - {len(team_objects)} teams imported")
    print(f"  - {import_stats['imported']} games imported")
    if import_stats['skipped'] > 0:
        print(f"  - {import_stats['skipped']} games skipped")
    print(f"  - Rankings calculated through Week {max_week}")
    print("="*80)

    db.close()


if __name__ == "__main__":
    main()
