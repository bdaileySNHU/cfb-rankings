"""
Import AP Poll Rankings Only
EPIC-010: AP Poll Prediction Comparison

This script imports AP Poll rankings for an existing season without
resetting the database or re-importing games.
"""

import os
import sys

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal
from src.models.models import APPollRanking, Team


def import_ap_poll_for_week(cfbd: CFBDClient, db, year: int, week: int) -> int:
    """
    Import AP Poll rankings for a specific week.

    Args:
        cfbd: CFBD client instance
        db: Database session
        year: Season year
        week: Week number

    Returns:
        int: Number of rankings imported
    """
    # Fetch AP Poll data for this week
    ap_poll_data = cfbd.get_ap_poll(year, week)

    if not ap_poll_data:
        return 0

    rankings_imported = 0

    for ranking in ap_poll_data:
        school_name = ranking.get('school')
        rank = ranking.get('rank')

        # Find team in our database
        team = db.query(Team).filter(Team.name == school_name).first()
        if not team:
            print(f"      Warning: AP Poll team '{school_name}' not found in database")
            continue

        # Check if ranking already exists (prevent duplicates)
        existing = db.query(APPollRanking).filter(
            APPollRanking.season == year,
            APPollRanking.week == week,
            APPollRanking.team_id == team.id
        ).first()

        if existing:
            # Update existing ranking
            existing.rank = rank
            existing.first_place_votes = ranking.get('firstPlaceVotes', 0)
            existing.points = ranking.get('points', 0)
            existing.poll_type = ranking.get('poll', 'AP Top 25')
            print(f"      Updated: #{rank} {school_name}")
        else:
            # Create new ranking
            ap_ranking = APPollRanking(
                season=year,
                week=week,
                poll_type=ranking.get('poll', 'AP Top 25'),
                rank=rank,
                team_id=team.id,
                first_place_votes=ranking.get('firstPlaceVotes', 0),
                points=ranking.get('points', 0)
            )
            db.add(ap_ranking)
            rankings_imported += 1
            print(f"      Added: #{rank} {school_name}")

    db.commit()
    return rankings_imported


def main():
    """Main import function"""
    print("="*80)
    print("AP POLL RANKINGS IMPORT")
    print("EPIC-010: AP Poll Prediction Comparison")
    print("="*80)
    print()

    # Get API key
    api_key = os.getenv('CFBD_API_KEY')
    if not api_key:
        print("ERROR: No API key found!")
        print()
        print("Set environment variable:")
        print("   export CFBD_API_KEY='your-key-here'")
        sys.exit(1)

    # Initialize CFBD client
    cfbd = CFBDClient(api_key)

    # Auto-detect current season
    current_season = cfbd.get_current_season()
    max_week_available = cfbd.get_current_week(current_season)

    if max_week_available is None:
        max_week_available = cfbd.estimate_current_week(current_season)
        if max_week_available == 0:
            max_week_available = 1

    print(f"Detected current season: {current_season}")
    print(f"Latest completed week: {max_week_available}")
    print()

    # Get user input for season and weeks
    season_input = input(f"Enter season year (default: {current_season}): ").strip()
    season = int(season_input) if season_input else current_season

    weeks_input = input(f"Enter weeks to import (e.g., '1-{max_week_available}' or '1,3,5'): ").strip()

    # Parse weeks
    if not weeks_input:
        weeks = range(1, max_week_available + 1)
    elif '-' in weeks_input:
        start, end = weeks_input.split('-')
        weeks = range(int(start), int(end) + 1)
    else:
        weeks = [int(w.strip()) for w in weeks_input.split(',')]

    print()
    print(f"Importing AP Poll rankings for {season}, weeks: {list(weeks)}")
    print()

    # Initialize database
    db = SessionLocal()

    # Import AP Poll rankings
    total_imported = 0
    weeks_with_data = 0

    for week in weeks:
        print(f"Week {week}...")
        count = import_ap_poll_for_week(cfbd, db, season, week)

        if count > 0:
            print(f"  ✓ Imported {count} rankings")
            total_imported += count
            weeks_with_data += 1
        else:
            print(f"  - No AP Poll data available")

    # Print summary
    print()
    print("="*80)
    print("IMPORT SUMMARY")
    print("="*80)
    print(f"Total rankings imported: {total_imported}")
    print(f"Weeks with AP Poll data: {weeks_with_data}")
    print("="*80)
    print()
    print("✓ Import complete!")
    print()
    print("You can now view the comparison page to see ELO vs AP Poll predictions.")

    db.close()


if __name__ == "__main__":
    main()
