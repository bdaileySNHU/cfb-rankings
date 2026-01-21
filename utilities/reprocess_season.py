#!/usr/bin/env python3
"""Reprocess Season - Fix ELO Imbalances

This script resets and reprocesses all games for a season to fix ELO
rating imbalances and ensure all games are properly processed with
correct rating changes.

Usage:
    python utilities/reprocess_season.py --season 2025
    python utilities/reprocess_season.py --season 2025 --dry-run

⚠️ WARNING: This script resets all team ratings and game processing
for the specified season. Make sure to backup your database first!

Part of Season-End Finalization Utilities
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import SessionLocal
from src.core.ranking_service import RankingService
from src.models.models import Game, Team, Season


def check_season_exists(db, season: int):
    """Verify season exists in database."""
    season_obj = db.query(Season).filter(Season.year == season).first()
    if not season_obj:
        print(f"✗ Season {season} not found in database")
        return False
    return True


def analyze_current_state(db, season: int):
    """Analyze current state of season data."""
    print(f"\nAnalyzing current state of season {season}...")

    total_games = db.query(Game).filter(Game.season == season).count()
    processed_games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True
    ).count()
    excluded_games = db.query(Game).filter(
        Game.season == season,
        Game.excluded_from_rankings == True
    ).count()

    # Check for ELO imbalances
    games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False
    ).all()

    imbalances = 0
    for game in games:
        rating_sum = game.home_rating_change + game.away_rating_change
        if abs(rating_sum) > 0.01:
            imbalances += 1

    print(f"\nCurrent State:")
    print(f"  Total games: {total_games}")
    print(f"  Processed games: {processed_games}")
    print(f"  Excluded games: {excluded_games}")
    print(f"  Games with ELO imbalances: {imbalances}")
    print()

    return total_games, processed_games, excluded_games, imbalances


def reset_season_data(db, season: int, dry_run: bool = False):
    """Reset all game processing and team ratings for the season."""
    print(f"{'[DRY-RUN] ' if dry_run else ''}Resetting season {season} data...")

    # Count games to reset (exclude FCS games)
    games_to_reset = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False
    ).count()

    print(f"  Games to reset: {games_to_reset}")

    if dry_run:
        print("[DRY-RUN] Would reset game processing data")
    else:
        # Reset game processing
        db.query(Game).filter(
            Game.season == season,
            Game.is_processed == True,
            Game.excluded_from_rankings == False
        ).update({
            'is_processed': False,
            'home_rating_change': 0.0,
            'away_rating_change': 0.0
        })
        print(f"  ✓ Reset {games_to_reset} games to unprocessed")

    # Count teams to reset
    teams = db.query(Team).filter(Team.is_fcs == False).all()
    print(f"  Teams to reset: {len(teams)}")

    if dry_run:
        print("[DRY-RUN] Would reset team ratings and records")
    else:
        # Reset team ratings and records
        for team in teams:
            team.elo_rating = team.initial_rating
            team.wins = 0
            team.losses = 0

        db.commit()
        print(f"  ✓ Reset {len(teams)} teams to initial ratings")

    return games_to_reset, len(teams)


def reprocess_season(db, season: int, dry_run: bool = False):
    """Reprocess all games for the season."""
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Reprocessing season {season}...")

    if dry_run:
        print("[DRY-RUN] Would reprocess all games using RankingService")
        return True

    try:
        ranking_service = RankingService(db)

        # Get all unprocessed games (excluding FCS games) ordered by week and date
        games = db.query(Game).filter(
            Game.season == season,
            Game.is_processed == False,
            Game.excluded_from_rankings == False
        ).order_by(Game.week, Game.game_date).all()

        print(f"  Processing {len(games)} games...")

        processed_count = 0
        for game in games:
            try:
                ranking_service.process_game(game)
                processed_count += 1
                if processed_count % 100 == 0:
                    print(f"  Processed {processed_count}/{len(games)} games...")
            except Exception as e:
                print(f"  ⚠ Error processing game {game.id} (Week {game.week}): {e}")
                continue

        db.commit()
        print(f"✓ Successfully reprocessed {processed_count}/{len(games)} games")
        return True
    except Exception as e:
        print(f"✗ Error reprocessing season: {e}")
        db.rollback()
        return False


def verify_reprocessing(db, season: int):
    """Verify that reprocessing was successful."""
    print(f"\nVerifying reprocessing results...")

    # Check processed games
    total_games = db.query(Game).filter(
        Game.season == season,
        Game.excluded_from_rankings == False
    ).count()

    processed_games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False
    ).count()

    # Check for remaining imbalances
    games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False
    ).all()

    imbalances = 0
    for game in games:
        rating_sum = game.home_rating_change + game.away_rating_change
        if abs(rating_sum) > 0.01:
            imbalances += 1

    print(f"  Processed: {processed_games}/{total_games} games")
    print(f"  ELO imbalances: {imbalances}")

    if processed_games == total_games and imbalances == 0:
        print("\n✓ Reprocessing successful - all games processed correctly")
        return True
    else:
        print("\n⚠ WARNING: Some issues remain after reprocessing")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reprocess season to fix ELO imbalances"
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to reprocess (e.g., 2025)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Reprocess Season {args.season}")
    if args.dry_run:
        print("DRY-RUN MODE - No changes will be made")
    else:
        print("⚠️  WARNING: This will reset and reprocess all games")
        print("⚠️  Make sure you have a database backup!")
    print(f"{'='*60}\n")

    db = SessionLocal()

    try:
        # Check season exists
        if not check_season_exists(db, args.season):
            sys.exit(1)

        # Analyze current state
        before_total, before_processed, before_excluded, before_imbalances = analyze_current_state(db, args.season)

        # Reset season data
        games_reset, teams_reset = reset_season_data(db, args.season, args.dry_run)

        # Reprocess season
        if not args.dry_run:
            success = reprocess_season(db, args.season, args.dry_run)
            if not success:
                print("\n✗ Reprocessing failed")
                sys.exit(1)

            # Verify results
            verify_reprocessing(db, args.season)

        # Summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print(f"Games reset: {games_reset}")
        print(f"Teams reset: {teams_reset}")

        if not args.dry_run:
            after_total, after_processed, after_excluded, after_imbalances = analyze_current_state(db, args.season)
            print(f"\nBefore: {before_imbalances} imbalances")
            print(f"After:  {after_imbalances} imbalances")

            if after_imbalances == 0:
                print("\n✓ All ELO imbalances fixed!")
            else:
                print(f"\n⚠ {after_imbalances} imbalances remain")

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
