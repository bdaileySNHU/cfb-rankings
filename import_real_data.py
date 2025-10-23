"""
Import Real College Football Data
Fetches data from CollegeFootballData API and populates the database
"""

from dotenv import load_dotenv

# Load environment variables from .env file (if accessible)
try:
    load_dotenv()
except (PermissionError, FileNotFoundError):
    # .env file not accessible or doesn't exist
    # Will fall back to system environment variables
    pass

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


def parse_game_date(game_data: dict) -> datetime:
    """
    Parse game date from CFBD API response.

    EPIC-008: CFBD provides dates in ISO 8601 format:
    "start_date": "2025-09-06T19:00:00.000Z"

    Args:
        game_data: Game data dictionary from CFBD API

    Returns:
        datetime: Parsed game date or current datetime as fallback
    """
    date_str = game_data.get('start_date')
    if date_str:
        try:
            # CFBD uses ISO 8601 format with Z suffix (UTC)
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    return datetime.now()  # Fallback if date parsing fails


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


def get_or_create_fcs_team(db, team_name: str, team_objects: dict) -> Team:
    """
    Get or create FCS team placeholder.

    Args:
        db: Database session
        team_name: Name of FCS team
        team_objects: Dictionary to update with new team

    Returns:
        Team object for FCS team
    """
    # Check if already in our cache
    if team_name in team_objects:
        return team_objects[team_name]

    # Check if exists in database
    team = db.query(Team).filter(Team.name == team_name).first()

    if not team:
        # Create new FCS team placeholder
        team = Team(
            name=team_name,
            conference=ConferenceType.FCS,
            is_fcs=True,
            elo_rating=0,  # Not used for FCS
            initial_rating=0,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=0.5
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    # Add to cache
    team_objects[team_name] = team
    return team


# EPIC-008 Story 003: Validation and duplicate detection functions

def check_for_duplicates(db) -> list:
    """
    Check for duplicate games in the database.

    A duplicate is defined as two games with the same:
    - home_team_id
    - away_team_id
    - week
    - season

    Args:
        db: Database session

    Returns:
        list: List of duplicate game groups with details
    """
    from sqlalchemy import func

    # Query for duplicate games
    duplicates = db.query(
        Game.home_team_id,
        Game.away_team_id,
        Game.week,
        Game.season,
        func.count(Game.id).label('count')
    ).group_by(
        Game.home_team_id,
        Game.away_team_id,
        Game.week,
        Game.season
    ).having(func.count(Game.id) > 1).all()

    if not duplicates:
        return []

    # Get details for each duplicate group
    duplicate_details = []
    for dup in duplicates:
        games = db.query(Game).filter(
            Game.home_team_id == dup.home_team_id,
            Game.away_team_id == dup.away_team_id,
            Game.week == dup.week,
            Game.season == dup.season
        ).all()

        home_team = db.query(Team).filter(Team.id == dup.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == dup.away_team_id).first()

        duplicate_details.append({
            'home_team': home_team.name if home_team else 'Unknown',
            'away_team': away_team.name if away_team else 'Unknown',
            'week': dup.week,
            'season': dup.season,
            'count': dup.count,
            'game_ids': [g.id for g in games],
            'scores': [(g.home_score, g.away_score) for g in games]
        })

    return duplicate_details


def print_duplicate_report(duplicates: list):
    """Print a formatted report of duplicate games."""
    if not duplicates:
        print("✓ No duplicate games found")
        return

    print("\n" + "="*80)
    print("⚠ WARNING: DUPLICATE GAMES DETECTED")
    print("="*80)

    for dup in duplicates:
        print(f"\n{dup['away_team']} @ {dup['home_team']} (Week {dup['week']}, {dup['season']})")
        print(f"  Found {dup['count']} duplicate records:")
        for game_id, scores in zip(dup['game_ids'], dup['scores']):
            print(f"    - Game ID {game_id}: {scores[1]}-{scores[0]}")

    print("\nTo fix duplicates manually:")
    print("  sqlite3 cfb_rankings.db")
    print("  DELETE FROM games WHERE id IN (...);")
    print("="*80)


def validate_import_results(db, import_stats: dict, year: int):
    """
    Validate import results and print summary.

    Args:
        db: Database session
        import_stats: Dictionary with import counts
        year: Season year
    """
    print("\n" + "="*80)
    print("IMPORT VALIDATION")
    print("="*80)

    # Check for duplicates
    duplicates = check_for_duplicates(db)
    print_duplicate_report(duplicates)

    # Verify game counts
    total_games = db.query(Game).filter(Game.season == year).count()
    future_games = db.query(Game).filter(
        Game.season == year,
        Game.home_score == 0,
        Game.away_score == 0
    ).count()
    completed_games = total_games - future_games

    print(f"\nDatabase Game Counts (Season {year}):")
    print(f"  Total Games: {total_games}")
    print(f"  Completed Games: {completed_games}")
    print(f"  Future Games: {future_games}")

    # Verify against import stats
    print(f"\nImport Stats:")
    print(f"  FBS Games Imported: {import_stats.get('imported', 0)}")
    print(f"  FCS Games Imported: {import_stats.get('fcs_imported', 0)}")
    print(f"  Future Games Imported: {import_stats.get('future_imported', 0)}")
    print(f"  Games Updated: {import_stats.get('games_updated', 0)}")
    print(f"  Games Skipped: {import_stats.get('skipped', 0)}")

    # Warnings for anomalies
    if duplicates:
        print("\n⚠ WARNING: Duplicates detected (see above)")

    if total_games == 0:
        print("\n⚠ WARNING: No games in database!")

    if future_games > 300:
        print(f"\n⚠ WARNING: Unusually high future game count ({future_games})")

    print("="*80)


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
    fcs_games_imported = 0  # NEW: Track FCS games separately
    future_games_imported = 0  # EPIC-008: Track future games
    total_updated = 0  # EPIC-008 Story 002: Track updated games
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
        week_updated = 0  # EPIC-008 Story 002: Track updated games per week

        for game_data in games_data:
            # API uses camelCase
            home_team_name = game_data.get('homeTeam')
            away_team_name = game_data.get('awayTeam')
            home_score = game_data.get('homePoints')
            away_score = game_data.get('awayPoints')

            game_desc = f"{away_team_name} @ {home_team_name}"

            # EPIC-008: Detect future games (no scores yet) and import them
            is_future_game = home_score is None or away_score is None

            if is_future_game:
                # Future game - use placeholder scores and don't process for ELO
                home_score = 0
                away_score = 0
                print(f"    Found future game: {game_desc}")

            # Determine if FBS vs FBS, FBS vs FCS, or both FCS
            home_is_fbs = home_team_name in team_objects
            away_is_fbs = away_team_name in team_objects

            # Case 1: Both FCS (skip entirely)
            if not home_is_fbs and not away_is_fbs:
                week_skipped += 1
                total_skipped += 1
                skipped_fcs += 1
                skipped_details.append((week, "Both teams FCS", game_desc))
                continue

            # Case 2: FBS vs FCS game - import with excluded flag
            is_fcs_game = not (home_is_fbs and away_is_fbs)

            # Get team objects (create FCS team if needed)
            if home_is_fbs:
                home_team = team_objects[home_team_name]
            else:
                home_team = get_or_create_fcs_team(db, home_team_name, team_objects)

            if away_is_fbs:
                away_team = team_objects[away_team_name]
            else:
                away_team = get_or_create_fcs_team(db, away_team_name, team_objects)

            # EPIC-008 Story 002: Check if game already exists (upsert logic)
            existing_game = db.query(Game).filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.week == week,
                Game.season == year
            ).first()

            if existing_game:
                # Game exists - decide whether to update, skip, or process
                if is_future_game:
                    # Still a future game (no scores yet) - skip
                    # This can happen if we re-import the same future week
                    continue

                # Game now has scores - check if we should update
                if existing_game.home_score == 0 and existing_game.away_score == 0:
                    # Future game that now has scores - UPDATE IT
                    print(f"    Updating game: {game_desc} -> {home_score}-{away_score}")

                    existing_game.home_score = home_score
                    existing_game.away_score = away_score
                    existing_game.is_neutral_site = game_data.get('neutralSite', False)
                    existing_game.excluded_from_rankings = is_fcs_game  # Update based on actual FCS status
                    existing_game.game_date = parse_game_date(game_data)

                    # Mark as unprocessed so ELO calculation runs
                    existing_game.is_processed = False

                    db.commit()
                    db.refresh(existing_game)

                    # Now process the game for ELO ratings (if FBS vs FBS)
                    if not is_fcs_game:
                        result = ranking_service.process_game(existing_game)
                        winner = result['winner_name']
                        loser = result['loser_name']
                        score = result['score']
                        print(f"      Processed: {winner} defeats {loser} {score}")
                        week_imported += 1
                        total_imported += 1

                    week_updated += 1
                    total_updated += 1
                    continue

                elif existing_game.is_processed:
                    # Already processed - skip
                    continue
                else:
                    # Has scores but not processed yet - process it
                    # But first check if it's actually a future game (0-0)
                    if existing_game.home_score == 0 and existing_game.away_score == 0:
                        # This is a future game that still has no scores - skip
                        continue

                    if not is_fcs_game:
                        result = ranking_service.process_game(existing_game)
                        week_imported += 1
                        total_imported += 1
                    continue

            # EPIC-008 Story 002: Game doesn't exist - INSERT NEW GAME

            # In validate-only mode, just count
            if validate_only:
                week_imported += 1
                total_imported += 1
                if is_future_game:
                    future_games_imported += 1
                continue

            # Create game
            is_neutral = game_data.get('neutralSite', False)

            # EPIC-008: Future games are excluded from rankings for safety
            excluded_from_rankings = is_fcs_game or is_future_game

            game = Game(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=home_score,  # 0 for future games, real score for completed
                away_score=away_score,  # 0 for future games, real score for completed
                week=week,
                season=year,
                is_neutral_site=is_neutral,
                excluded_from_rankings=excluded_from_rankings,
                game_date=parse_game_date(game_data)  # EPIC-008: Parse actual date from CFBD
            )

            db.add(game)
            db.commit()
            db.refresh(game)

            # EPIC-008: Process game to update rankings (ONLY for completed FBS vs FBS games)
            if is_future_game:
                # Future game - don't process for rankings
                print(f"    {game_desc} (scheduled - not ranked)")
                future_games_imported += 1
                week_imported += 1
            elif not is_fcs_game:
                # Completed FBS vs FBS game - process for rankings
                result = ranking_service.process_game(game)

                winner = result['winner_name']
                loser = result['loser_name']
                score = result['score']

                print(f"    {winner} defeats {loser} {score}")
                week_imported += 1
                total_imported += 1
            else:
                # FCS game - don't process for rankings, just track
                fcs_opponent = away_team if home_is_fbs else home_team
                fbs_team_obj = home_team if home_is_fbs else away_team
                print(f"    {fbs_team_obj.name} vs {fcs_opponent.name} (FCS - not ranked)")
                fcs_games_imported += 1

        # Print week summary
        total_week_games = week_stats['completed']
        if total_week_games > 0:
            completion_rate = (week_imported / total_week_games) * 100
            status = "✓" if completion_rate >= 95 else "⚠"
            print(f"\n  {status} Week {week} Summary:")
            print(f"    Expected: {total_week_games} games")
            print(f"    Imported: {week_imported} games ({completion_rate:.0f}%)")
            if week_updated > 0:  # EPIC-008 Story 002
                print(f"    Updated: {week_updated} games")
            if week_skipped > 0:
                print(f"    Skipped: {week_skipped} games")

    # Print final import summary
    print("\n" + "="*80)
    print("IMPORT SUMMARY")
    print("="*80)
    print(f"Total FBS Games Imported: {total_imported}")
    print(f"Total FCS Games Imported: {fcs_games_imported}")
    print(f"Total Future Games Imported: {future_games_imported}")  # EPIC-008
    print(f"Total Games Updated: {total_updated}")  # EPIC-008 Story 002
    print(f"Total Games Skipped: {total_skipped}")
    if skipped_fcs > 0:
        print(f"  - FCS Opponents: {skipped_fcs}")
    if skipped_not_found > 0:
        print(f"  - Team Not Found: {skipped_not_found}")
    if skipped_incomplete > 0:
        print(f"  - Incomplete Games (now imported as future): {skipped_incomplete}")

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
        "fcs_imported": fcs_games_imported,
        "future_imported": future_games_imported,  # EPIC-008
        "games_updated": total_updated,  # EPIC-008 Story 002
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

    # EPIC-008 Story 003: Validate import results
    validate_import_results(db, import_stats, season)

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
    print(f"  - {import_stats['imported']} FBS games imported")
    if import_stats.get('fcs_imported', 0) > 0:
        print(f"  - {import_stats['fcs_imported']} FCS games imported (not ranked)")
    if import_stats['skipped'] > 0:
        print(f"  - {import_stats['skipped']} games skipped")
    print(f"  - Rankings calculated through Week {max_week}")
    print("="*80)

    db.close()


if __name__ == "__main__":
    main()
