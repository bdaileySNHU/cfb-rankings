#!/usr/bin/env python3
"""Fix Unprocessed Games - Mark FCS Games as Excluded

This script identifies unprocessed games and marks FCS games as excluded
from rankings. This is typically needed when FCS games weren't properly
excluded during initial import.

Usage:
    python utilities/fix_unprocessed_games.py --season 2025
    python utilities/fix_unprocessed_games.py --season 2025 --dry-run

Part of Season-End Finalization Utilities
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import SessionLocal
from src.models.models import Game, Team


def investigate_unprocessed(db, season: int):
    """Investigate what types of games are unprocessed."""
    print(f"\nInvestigating unprocessed games for season {season}...")

    unprocessed = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == False
    ).all()

    if not unprocessed:
        print("✓ No unprocessed games found")
        return []

    print(f"Found {len(unprocessed)} unprocessed games\n")

    # Categorize by FCS involvement
    fcs_games = []
    fbs_games = []

    for game in unprocessed:
        home = db.query(Team).filter(Team.id == game.home_team_id).first()
        away = db.query(Team).filter(Team.id == game.away_team_id).first()

        if (home and home.is_fcs) or (away and away.is_fcs):
            fcs_games.append(game)
        else:
            fbs_games.append(game)

    print(f"Categories:")
    print(f"  - FCS games: {len(fcs_games)}")
    print(f"  - FBS games: {len(fbs_games)}")
    print()

    if fcs_games:
        print("Sample FCS games (first 10):")
        for game in fcs_games[:10]:
            home = db.query(Team).filter(Team.id == game.home_team_id).first()
            away = db.query(Team).filter(Team.id == game.away_team_id).first()
            home_fcs = " (FCS)" if home and home.is_fcs else ""
            away_fcs = " (FCS)" if away and away.is_fcs else ""
            print(f"  Week {game.week:2d}: {home.name if home else 'Unknown'}{home_fcs} vs {away.name if away else 'Unknown'}{away_fcs}")
        print()

    if fbs_games:
        print("⚠ WARNING: Found FBS-only games that are unprocessed!")
        print("Sample FBS games (first 10):")
        for game in fbs_games[:10]:
            home = db.query(Team).filter(Team.id == game.home_team_id).first()
            away = db.query(Team).filter(Team.id == game.away_team_id).first()
            print(f"  Week {game.week:2d}: {home.name if home else 'Unknown'} vs {away.name if away else 'Unknown'}")
        print()

    return unprocessed


def fix_fcs_games(db, season: int, dry_run: bool = False):
    """Mark FCS games as excluded from rankings and processed."""
    print(f"{'[DRY-RUN] ' if dry_run else ''}Fixing FCS games for season {season}...")

    # Find FCS games that are unprocessed
    fcs_games = db.query(Game).join(
        Team, (Game.home_team_id == Team.id) | (Game.away_team_id == Team.id)
    ).filter(
        Game.season == season,
        Game.is_processed == False,
        Team.is_fcs == True
    ).all()

    if not fcs_games:
        print("✓ No FCS games to fix")
        return 0

    print(f"Found {len(fcs_games)} FCS games to mark as excluded")

    if dry_run:
        print("[DRY-RUN] Would mark these games as excluded and processed")
        return len(fcs_games)

    # Mark them as excluded and processed
    for game in fcs_games:
        game.excluded_from_rankings = True
        game.is_processed = True

    db.commit()
    print(f"✓ Marked {len(fcs_games)} FCS games as excluded and processed")
    return len(fcs_games)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix unprocessed games by marking FCS games as excluded"
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to fix (e.g., 2025)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Fix Unprocessed Games - Season {args.season}")
    if args.dry_run:
        print("DRY-RUN MODE - No changes will be made")
    print(f"{'='*60}\n")

    db = SessionLocal()

    try:
        # Investigate unprocessed games
        unprocessed = investigate_unprocessed(db, args.season)

        if not unprocessed:
            print("\n✓ No unprocessed games to fix")
            sys.exit(0)

        # Fix FCS games
        fixed_count = fix_fcs_games(db, args.season, args.dry_run)

        # Check remaining unprocessed
        remaining = db.query(Game).filter(
            Game.season == args.season,
            Game.is_processed == False
        ).count()

        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print(f"Fixed: {fixed_count} games")
        print(f"Remaining unprocessed: {remaining} games")

        if remaining > 0:
            print("\n⚠ WARNING: There are still unprocessed games remaining")
            print("These may be FBS games that need to be processed with:")
            print("  python utilities/reprocess_season.py --season {args.season}")
        else:
            print("\n✓ All games are now processed or excluded")

        print(f"{'='*60}\n")

        if args.dry_run:
            print("DRY-RUN complete - no changes made")
            print("Run without --dry-run to apply changes")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
