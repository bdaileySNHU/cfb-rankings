"""Full-import CLI pipeline: teams, games, postseason, validation, rankings."""

import argparse
import sys

from dotenv import load_dotenv

# Load environment variables from .env file (if accessible)
try:
    load_dotenv()
except (PermissionError, FileNotFoundError):
    # .env file not accessible or doesn't exist
    # Will fall back to system environment variables
    pass

from src.core.ranking_service import RankingService
from src.importers.games import import_games
from src.importers.postseason import (
    import_bowl_games,
    import_conference_championships,
    import_playoff_games,
)
from src.importers.teams import import_teams
from src.importers.validation import validate_api_connection, validate_import_results
from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal, reset_db
from src.models.models import Game, Season


def main():
    """Main import function"""
    print("=" * 80)
    print("COLLEGE FOOTBALL DATA IMPORT")
    print("=" * 80)
    print()
    print("This script imports real college football data from CollegeFootballData.com")
    print()

    # Parse command-line arguments
    import os

    api_key = os.getenv("CFBD_API_KEY")

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
        description="Import college football data from CFBD API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Incremental update (default) - import new data without resetting database
  python3 import_real_data.py

  # Full reset - wipe database and reimport everything
  python3 import_real_data.py --reset

  # Override season year
  python3 import_real_data.py --season 2024

  # Override max week to import
  python3 import_real_data.py --max-week 10

  # Specify both season and week
  python3 import_real_data.py --season 2024 --max-week 12
        """,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before import (WARNING: destroys all existing data)",
    )
    parser.add_argument(
        "--season", type=int, help=f"Season year (default: auto-detect, currently {current_season})"
    )
    parser.add_argument(
        "--max-week",
        type=int,
        help=f"Maximum week to import (default: all available, currently {max_week_available})",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate import without making changes (dry-run mode)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on validation warnings (exit with error if games skipped)",
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
    if args.reset:
        print(f"  → RESET MODE: Database will be wiped and rebuilt")
    else:
        print(f"  → INCREMENTAL MODE: New data will be added to existing database")
    print()

    # Initialize database
    db = SessionLocal()

    # Conditional reset based on --reset flag
    if args.reset:
        # Confirm reset
        print("WARNING: This will reset your database and replace all data!")
        response = input("Continue? (yes/no): ")

        if response.lower() != "yes":
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
    else:
        # Incremental mode - get or create season
        print(f"Incremental mode: Getting or creating {season} season...")
        season_obj = db.query(Season).filter(Season.year == season).first()
        if not season_obj:
            print(f"  Season {season} not found, creating new season...")
            season_obj = Season(year=season, current_week=0, is_active=True)
            db.add(season_obj)
            db.commit()
        else:
            print(f"  Found existing season {season} (current week: {season_obj.current_week})")

    # Import teams
    team_objects = import_teams(cfbd, db, year=season)

    if not team_objects:
        print("\nFailed to import teams. Check your API key.")
        return

    # Import games (using detected/overridden max_week)
    print(f"\nImporting games through Week {max_week}...")
    import_stats = import_games(
        cfbd,
        db,
        team_objects,
        year=season,
        max_week=max_week,
        validate_only=args.validate_only,
        strict=args.strict,
    )

    # EPIC-022: Import conference championship games
    # EPIC-023: Import bowl games
    if not args.validate_only:
        ranking_service = RankingService(db)

        # Import conference championships
        conf_champ_count = import_conference_championships(
            cfbd, db, team_objects, season, ranking_service
        )
        import_stats["conf_championships_imported"] = conf_champ_count

        # Import bowl games
        bowl_count = import_bowl_games(cfbd, db, team_objects, season, ranking_service)
        import_stats["bowl_games_imported"] = bowl_count

        # Import playoff games
        playoff_count = import_playoff_games(cfbd, db, team_objects, season, ranking_service)
        import_stats["playoff_games_imported"] = playoff_count

    # Skip remaining steps if validate-only mode
    if args.validate_only:
        print("\n✓ Validation complete - no changes made to database")
        db.close()
        return

    # EPIC-008 Story 003: Validate import results
    validate_import_results(db, import_stats, season)

    # EPIC-022: Determine actual max week including championship games
    # Conference championships may be in Week 15, even if max_week was 14
    actual_max_week = (
        db.query(Game)
        .filter(Game.season == season, Game.is_processed == True)
        .order_by(Game.week.desc())
        .first()
    )

    if actual_max_week:
        final_week = actual_max_week.week
    else:
        final_week = max_week

    # Update season current week to actual max
    season_obj.current_week = final_week
    db.commit()

    # Save rankings through actual max week (including championship week if present)
    print(f"\nSaving final rankings through Week {final_week}...")
    # ranking_service already created above for conference championships
    for week in range(1, final_week + 1):
        ranking_service.save_weekly_rankings(season, week)

    # Show final rankings
    print("\n" + "=" * 80)
    print("FINAL RANKINGS")
    print("=" * 80)

    rankings = ranking_service.get_current_rankings(season, limit=25)
    print(f"\n{'RANK':<6} {'TEAM':<30} {'RATING':<10} {'RECORD':<10} {'SOS':<10}")
    print("-" * 80)

    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        print(
            f"{r['rank']:<6} {r['team_name']:<30} {r['elo_rating']:<10.2f} {record:<10} {r['sos']:<10.2f}"
        )

    print()
    print("=" * 80)
    print(f"✓ Import Complete!")
    print(f"  - {len(team_objects)} teams imported")
    print(f"  - {import_stats['imported']} FBS games imported")
    if import_stats.get("fcs_imported", 0) > 0:
        print(f"  - {import_stats['fcs_imported']} FCS games imported (not ranked)")
    if import_stats.get("conf_championships_imported", 0) > 0:
        print(
            f"  - {import_stats['conf_championships_imported']} conference championships imported"
        )
    if import_stats.get("bowl_games_imported", 0) > 0:
        print(f"  - {import_stats['bowl_games_imported']} bowl games imported")
    if import_stats.get("playoff_games_imported", 0) > 0:
        print(f"  - {import_stats['playoff_games_imported']} playoff games imported")
    if import_stats["skipped"] > 0:
        print(f"  - {import_stats['skipped']} games skipped")
    print(f"  - Rankings calculated through Week {final_week}")
    print("=" * 80)

    db.close()
