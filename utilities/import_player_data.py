#!/usr/bin/env python3
"""Import Player Recruiting Data from CFBD API

This script imports individual player recruiting rankings from the
CollegeFootballData API into the database to enable position-based
preseason rating calculations.

Usage:
    python utilities/import_player_data.py --year 2024
    python utilities/import_player_data.py --year 2024 --team Georgia
    python utilities/import_player_data.py --year 2024 --dry-run
    python utilities/import_player_data.py --year 2024 --force

Part of: Preseason Enhancement Epic - Story 1.4
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integrations.cfbd_client import CFBDClient, get_monthly_usage
from src.models.database import SessionLocal
from src.models.models import Player, Team


def check_api_quota(force: bool = False) -> bool:
    """Check API quota before importing large dataset.

    Estimates the number of API calls needed and warns if it would
    exceed recommended quota thresholds.

    Args:
        force: If True, proceed even if quota is low

    Returns:
        bool: True if safe to proceed, False if quota too low

    Note:
        - Estimates 133 API calls for full FBS season import
        - Warns if usage would exceed 90% of monthly quota
    """
    print("\nChecking API quota...")

    usage = get_monthly_usage()
    total_calls = usage["total_calls"]
    monthly_limit = usage["monthly_limit"]
    percentage = usage["percentage_used"]
    remaining = usage["remaining_calls"]

    print(f"  Current usage: {total_calls}/{monthly_limit} calls ({percentage:.1f}%)")
    print(f"  Remaining: {remaining} calls")

    # Estimate calls needed for full import (133 FBS teams)
    estimated_calls = 133
    print(f"  Estimated calls for full import: {estimated_calls}")

    # Check if we'd exceed 90% after import
    projected_total = total_calls + estimated_calls
    projected_percentage = (projected_total / monthly_limit) * 100

    if projected_percentage > 90:
        print(f"\n⚠ WARNING: Import would use {projected_percentage:.1f}% of monthly quota")
        print(f"  This may impact other operations this month")

        if not force:
            print("\n  Run with --force to proceed anyway")
            return False
        else:
            print("\n  --force flag set, proceeding...")
            return True

    print("✓ Sufficient API quota available")
    return True


def import_players_for_team(
    db,
    client: CFBDClient,
    team_name: str,
    year: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Import player data for a single team.

    Args:
        db: Database session
        client: CFBD API client
        team_name: Team name (e.g., "Georgia")
        year: Recruiting class year
        dry_run: If True, don't write to database

    Returns:
        tuple[int, int]: (players_imported, players_updated)
    """
    # Fetch player data from CFBD API
    players_data = client.get_recruiting_players(year=year, team=team_name)

    if not players_data:
        return 0, 0

    # Look up team in database
    team = db.query(Team).filter(Team.name == team_name).first()
    if not team:
        print(f"  ⚠ Team '{team_name}' not found in database, skipping...")
        return 0, 0

    imported = 0
    updated = 0

    for player_data in players_data:
        # Extract required fields
        cfbd_athlete_id = player_data.get("athleteId")
        name = player_data.get("name")
        position = player_data.get("position")
        stars = player_data.get("stars")
        rating = player_data.get("rating")
        ranking = player_data.get("ranking")

        # Skip if missing required fields
        if not all([cfbd_athlete_id, name, position]):
            continue

        if dry_run:
            print(f"    [DRY-RUN] Would import: {name} ({position}, {stars}★)")
            imported += 1
            continue

        # Upsert logic: check if player already exists
        existing_player = (
            db.query(Player)
            .filter(Player.cfbd_athlete_id == cfbd_athlete_id)
            .first()
        )

        if existing_player:
            # Update existing player
            existing_player.name = name
            existing_player.team_id = team.id
            existing_player.position = position
            existing_player.stars = stars
            existing_player.rating = rating
            existing_player.ranking = ranking
            existing_player.recruiting_year = year
            updated += 1
        else:
            # Create new player
            player = Player(
                cfbd_athlete_id=cfbd_athlete_id,
                name=name,
                team_id=team.id,
                position=position,
                stars=stars,
                rating=rating,
                ranking=ranking,
                recruiting_year=year,
            )
            db.add(player)
            imported += 1

        # Batch commit every 100 players for performance
        if (imported + updated) % 100 == 0:
            db.commit()

    # Final commit
    if not dry_run:
        db.commit()

    return imported, updated


def import_all_teams(
    db,
    client: CFBDClient,
    year: int,
    dry_run: bool = False,
) -> tuple[int, int, int, list]:
    """Import player data for all FBS teams.

    Args:
        db: Database session
        client: CFBD API client
        year: Recruiting class year
        dry_run: If True, don't write to database

    Returns:
        tuple[int, int, int, list]: (teams_processed, total_imported, total_updated, errors)
    """
    # Get all FBS teams from database
    teams = db.query(Team).filter(Team.is_fcs == False).all()

    print(f"\nImporting players for {len(teams)} FBS teams...")
    print()

    teams_processed = 0
    total_imported = 0
    total_updated = 0
    errors = []

    for i, team in enumerate(teams, 1):
        try:
            print(f"[{i}/{len(teams)}] Fetching players for {team.name}...", end=" ")

            imported, updated = import_players_for_team(
                db, client, team.name, year, dry_run
            )

            if imported > 0 or updated > 0:
                print(f"✓ {imported} imported, {updated} updated")
            elif imported == 0 and updated == 0:
                print("⚠ No player data")
            else:
                print("⚠ Skipped")

            teams_processed += 1
            total_imported += imported
            total_updated += updated

        except Exception as e:
            error_msg = f"{team.name}: {str(e)}"
            errors.append(error_msg)
            print(f"✗ Error: {e}")
            continue

        # Polite delay between teams to avoid rate limiting (CFBD allows ~1 req/sec)
        time.sleep(1.5)

    return teams_processed, total_imported, total_updated, errors


def verify_import(db, year: int):
    """Verify that player data was imported successfully.

    Args:
        db: Database session
        year: Recruiting class year
    """
    print("\nVerifying import...")

    # Count total players
    total_players = db.query(Player).filter(Player.recruiting_year == year).count()
    print(f"  Total players imported: {total_players}")

    # Count teams with players
    teams_with_players = (
        db.query(Team.id)
        .join(Player)
        .filter(Player.recruiting_year == year)
        .distinct()
        .count()
    )
    print(f"  Teams with players: {teams_with_players}")

    # Sample some players
    sample_players = (
        db.query(Player)
        .filter(Player.recruiting_year == year)
        .order_by(Player.ranking)
        .limit(5)
        .all()
    )

    if sample_players:
        print(f"\n  Top 5 recruits (by ranking):")
        for player in sample_players:
            stars = f"{player.stars}★" if player.stars else "N/A"
            rank = f"#{player.ranking}" if player.ranking else "Unranked"
            print(
                f"    {rank:>10} - {player.name:30} ({player.position:3}) "
                f"{stars:4} → {player.team.name if player.team else 'Unknown'}"
            )


def main():
    """Main entry point for player data import script."""
    parser = argparse.ArgumentParser(
        description="Import player recruiting data from CFBD API"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Recruiting class year (e.g., 2024)",
    )
    parser.add_argument(
        "--team",
        type=str,
        help="Optional: Import for specific team only (e.g., 'Georgia')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without writing to database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force import even if API quota is low",
    )

    args = parser.parse_args()

    print("=" * 60)
    print(f"Import Player Recruiting Data - {args.year} Class")
    if args.dry_run:
        print("DRY-RUN MODE - No changes will be made")
    print("=" * 60)
    print()

    # Initialize CFBD client and database
    client = CFBDClient()
    db = SessionLocal()

    try:
        # Check API quota (unless dry-run or single team)
        if not args.dry_run and not args.team:
            if not check_api_quota(args.force):
                print("\n✗ Aborting import due to API quota concerns")
                print("  Use --force to override")
                sys.exit(1)

        # Import for specific team or all teams
        if args.team:
            print(f"\nImporting players for {args.team}...")
            imported, updated = import_players_for_team(
                db, client, args.team, args.year, args.dry_run
            )

            print()
            print("=" * 60)
            print("Summary")
            print("=" * 60)
            print(f"Team: {args.team}")
            print(f"Players imported: {imported}")
            print(f"Players updated: {updated}")
            print("=" * 60)

        else:
            # Import all teams
            teams_processed, total_imported, total_updated, errors = import_all_teams(
                db, client, args.year, args.dry_run
            )

            print()
            print("=" * 60)
            print("Summary")
            print("=" * 60)
            print(f"Teams processed: {teams_processed}")
            print(f"Players imported: {total_imported}")
            print(f"Players updated: {total_updated}")
            print(f"Errors: {len(errors)}")

            if errors:
                print("\nErrors encountered:")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"  ✗ {error}")
                if len(errors) > 10:
                    print(f"  ... and {len(errors) - 10} more")

            print("=" * 60)

        # Verify import (skip if dry-run)
        if not args.dry_run:
            verify_import(db, args.year)

        print()
        if args.dry_run:
            print("DRY-RUN complete - no changes made")
            print("Run without --dry-run to actually import data")
        else:
            print("✓ Import completed successfully!")

            # Next steps
            print("\nNext steps:")
            print(f"  1. Verify data: sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM players WHERE recruiting_year={args.year};'")
            print(f"  2. Check position strength: python utilities/calculate_position_strength.py --team Georgia")
            print(f"  3. Enable feature: Edit src/core/position_weights.json, set enabled=true")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
