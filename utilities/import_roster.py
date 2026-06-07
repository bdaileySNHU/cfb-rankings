#!/usr/bin/env python3
"""Import Team Rosters from CFBD API

Pulls each team's actual roster for a season from the CFBD ``/roster`` endpoint
and snapshots it into the ``roster_players`` table, resolving each player's
recruiting rating via athlete-id join to the ``players`` table.

This is what makes position strength reflect the real roster (transfers in,
departures out, all class years) instead of recruiting-class signings. For full
rating coverage, import recruiting classes ~5 years deep first (see
utilities/import_player_data.py), so upperclassmen resolve a rating.

Usage:
    python utilities/import_roster.py --year 2025
    python utilities/import_roster.py --year 2025 --team Georgia
    python utilities/import_roster.py --year 2025 --dry-run
    python utilities/import_roster.py --year 2025 --force

Part of: EPIC-039 (Roster-Based Position Strength) - Story 39.3
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integrations.cfbd_client import CFBDClient, get_monthly_usage
from src.models.database import SessionLocal
from src.models.models import Player, RosterPlayer, Team


def check_api_quota(estimated_calls: int, force: bool = False) -> bool:
    """Check API quota before importing.

    Args:
        estimated_calls: Number of CFBD calls the import will make
        force: If True, proceed even if quota would exceed 90%

    Returns:
        bool: True if safe to proceed, False otherwise
    """
    print("\nChecking API quota...")
    usage = get_monthly_usage()
    total_calls = usage["total_calls"]
    monthly_limit = usage["monthly_limit"]

    print(f"  Current usage: {total_calls}/{monthly_limit} calls ({usage['percentage_used']:.1f}%)")
    print(f"  Estimated calls for this import: {estimated_calls}")

    projected_percentage = ((total_calls + estimated_calls) / monthly_limit) * 100
    if projected_percentage > 90:
        print(f"\n⚠ WARNING: Import would use {projected_percentage:.1f}% of monthly quota")
        if not force:
            print("  Run with --force to proceed anyway")
            return False
        print("  --force flag set, proceeding...")
        return True

    print("✓ Sufficient API quota available")
    return True


def build_rating_lookup(db) -> dict:
    """Build {athlete_id: rating} from imported recruiting data.

    A given athlete appears at most once in ``players`` (unique
    cfbd_athlete_id), so the mapping is 1:1.
    """
    lookup = {}
    for athlete_id, rating in db.query(Player.cfbd_athlete_id, Player.rating).all():
        if athlete_id is not None:
            lookup[athlete_id] = rating
    return lookup


def import_roster_for_team(
    db,
    client: CFBDClient,
    team: Team,
    year: int,
    rating_lookup: dict,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Import the roster snapshot for a single team.

    Replaces any existing snapshot for (year, team) so the import is idempotent.

    Returns:
        tuple[int, int]: (rows_written, rows_with_rating)
    """
    roster = client.get_roster(team=team.name, year=year)
    if not roster:
        return 0, 0

    if not dry_run:
        # Idempotent: clear this team's existing snapshot for the season
        db.query(RosterPlayer).filter(
            RosterPlayer.season == year, RosterPlayer.team_id == team.id
        ).delete(synchronize_session=False)

    written = 0
    with_rating = 0

    for entry in roster:
        athlete_raw = entry.get("id")
        position = entry.get("position")
        first = entry.get("firstName") or ""
        last = entry.get("lastName") or ""
        name = f"{first} {last}".strip()

        # Skip rows missing the fields we need
        if athlete_raw is None or not position or not name:
            continue

        try:
            athlete_id = int(athlete_raw)
        except (TypeError, ValueError):
            continue

        rating = rating_lookup.get(athlete_id)
        source = "recruiting-join" if rating is not None else "unrated"
        if rating is not None:
            with_rating += 1

        if dry_run:
            written += 1
            continue

        db.add(
            RosterPlayer(
                season=year,
                team_id=team.id,
                athlete_id=athlete_id,
                name=name,
                position=position,
                class_year=entry.get("year"),
                rating=rating,
                source=source,
            )
        )
        written += 1

    if not dry_run:
        db.commit()

    return written, with_rating


def import_all_teams(db, client: CFBDClient, year: int, dry_run: bool = False):
    """Import rosters for all FBS teams."""
    teams = db.query(Team).filter(Team.is_fcs == False).all()  # noqa: E712
    print(f"\nImporting rosters for {len(teams)} FBS teams (season {year})...\n")

    rating_lookup = build_rating_lookup(db)
    print(f"Rating lookup built from {len(rating_lookup)} recruiting records.\n")

    teams_processed = 0
    total_written = 0
    total_rated = 0
    errors = []

    for i, team in enumerate(teams, 1):
        try:
            print(f"[{i}/{len(teams)}] {team.name}...", end=" ")
            written, rated = import_roster_for_team(
                db, client, team, year, rating_lookup, dry_run
            )
            if written:
                teams_processed += 1
                total_written += written
                total_rated += rated
                print(f"{written} players ({rated} rated)")
            else:
                print("no roster data")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{team.name}: {e}")
            print(f"ERROR: {e}")

    return teams_processed, total_written, total_rated, errors


def main():
    parser = argparse.ArgumentParser(description="Import team rosters from CFBD API")
    parser.add_argument("--year", type=int, required=True, help="Season year (e.g., 2025)")
    parser.add_argument("--team", type=str, help="Import for a specific team only")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--force", action="store_true", help="Proceed even if API quota is low")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Import Team Rosters - {args.year} season")
    if args.dry_run:
        print("DRY-RUN MODE - No changes will be made")
    print("=" * 60)

    client = CFBDClient()
    db = SessionLocal()

    try:
        if args.team:
            team = db.query(Team).filter(Team.name == args.team).first()
            if not team:
                print(f"✗ Team '{args.team}' not found in database")
                sys.exit(1)
            rating_lookup = build_rating_lookup(db)
            written, rated = import_roster_for_team(
                db, client, team, args.year, rating_lookup, args.dry_run
            )
            print(f"\n{args.team}: {written} players ({rated} rated)")
        else:
            if not args.dry_run and not check_api_quota(135, args.force):
                print("\n✗ Aborting import due to API quota concerns")
                sys.exit(1)
            processed, written, rated, errors = import_all_teams(
                db, client, args.year, args.dry_run
            )
            print()
            print("=" * 60)
            print("Summary")
            print("=" * 60)
            print(f"Teams processed: {processed}")
            print(f"Roster players written: {written}")
            print(f"  ...with a resolved rating: {rated}")
            print(f"Errors: {len(errors)}")
            for error in errors[:10]:
                print(f"  ✗ {error}")

        if not args.dry_run:
            verify = db.query(RosterPlayer).filter(RosterPlayer.season == args.year).count()
            print(f"\nVerifying: {verify} roster rows stored for {args.year}")

        print("\n✓ Roster import completed successfully!")
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ Error during import: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
