"""
Import AP Poll and CFP Committee Rankings Only
EPIC-010 / EPIC-046: poll prediction comparison

Imports AP Poll and CFP committee rankings for an existing season without
resetting the database or re-importing games. Uses the same importer as the
weekly update, so it also backfills committee weeks (~10 on).
"""

import os
import sys

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.importers.polls import import_ap_poll_rankings
from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal
from src.models.models import Team


def main():
    """Main import function"""
    print("=" * 80)
    print("AP POLL + CFP COMMITTEE RANKINGS IMPORT")
    print("EPIC-010 / EPIC-046: poll prediction comparison")
    print("=" * 80)
    print()

    # Get API key
    api_key = os.getenv("CFBD_API_KEY")
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

    weeks_input = input(
        f"Enter weeks to import (e.g., '1-{max_week_available}' or '1,3,5'): "
    ).strip()

    # Parse weeks
    if not weeks_input:
        weeks = range(1, max_week_available + 1)
    elif "-" in weeks_input:
        start, end = weeks_input.split("-")
        weeks = range(int(start), int(end) + 1)
    else:
        weeks = [int(w.strip()) for w in weeks_input.split(",")]

    print()
    print(f"Importing AP + CFP rankings for {season}, weeks: {list(weeks)}")
    print()

    # Initialize database
    db = SessionLocal()

    team_objects = {t.name: t for t in db.query(Team).all()}

    # Import AP Poll + CFP committee rankings
    total_imported = 0
    weeks_with_data = 0

    for week in weeks:
        print(f"Week {week}...")
        count = import_ap_poll_rankings(cfbd, db, team_objects, season, week)

        if count > 0:
            print(f"  ✓ Imported {count} rankings")
            total_imported += count
            weeks_with_data += 1
        else:
            print("  - No new poll rankings")

    # Print summary
    print()
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total rankings imported: {total_imported}")
    print(f"Weeks with new rankings: {weeks_with_data}")
    print("=" * 80)
    print()
    print("✓ Import complete!")
    print()
    print("You can now view the comparison page to see ELO vs AP Poll predictions.")

    db.close()


if __name__ == "__main__":
    main()
