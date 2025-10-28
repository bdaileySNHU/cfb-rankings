#!/usr/bin/env python3
"""
Backfill Historical Predictions Script for College Football Rankings System

Generates predictions for past games using historical ELO ratings that existed
immediately before each game was played. This populates the Prediction Comparison
feature with historically accurate prediction data.

**Key Principle:** Uses only data that was available before each game - never
uses future information.

Usage:
    python3 scripts/backfill_historical_predictions.py

Part of EPIC-017: Retrospective Prediction Generation
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import SessionLocal
from models import Game, Prediction, Team, RankingHistory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_historical_rating(db, team_id: int, season: int, week: int) -> float:
    """
    Get historical ELO rating for a team at a specific week.

    For a game in week N, this retrieves the rating from week N-1
    (the rating that existed before the game was played).

    Args:
        db: Database session
        team_id: ID of the team
        season: Season year
        week: Week to get rating for

    Returns:
        float: Historical ELO rating, or 1500 (default) if not found

    Notes:
        - For Week 1 games, uses week 0 (preseason) ratings from RankingHistory
        - If no historical rating found, logs warning and returns 1500
    """
    # For week N game, get week N-1 rating
    # For week 1, use week 0 (preseason)
    lookup_week = max(0, week - 1)

    rating = db.query(RankingHistory.elo_rating).filter(
        RankingHistory.team_id == team_id,
        RankingHistory.season == season,
        RankingHistory.week == lookup_week
    ).scalar()

    if rating is None:
        # Get team name for better logging
        team = db.query(Team).filter(Team.id == team_id).first()
        team_name = team.name if team else f"Team {team_id}"

        logger.warning(
            f"No historical rating for {team_name} (season {season}, week {lookup_week}), "
            f"using default 1500"
        )
        return 1500.0

    return rating


def calculate_prediction_timestamp(game: Game) -> datetime:
    """
    Calculate timestamp for when prediction would have been made.

    Predictions are created 2 days before the game date.
    If game_date is null, estimates based on season start + week offset.

    Args:
        game: Game object

    Returns:
        datetime: Timestamp for prediction creation
    """
    if game.game_date:
        # Prediction made 2 days before game
        return game.game_date - timedelta(days=2)
    else:
        # Fallback: estimate game date and subtract 2 days
        # Approximate: season starts late August, ~7 days per week
        season_start = datetime(game.season, 8, 25)
        estimated_game_date = season_start + timedelta(weeks=game.week)
        return estimated_game_date - timedelta(days=2)


def prediction_exists(db, game_id: int) -> bool:
    """
    Check if a prediction already exists for a game.

    Args:
        db: Database session
        game_id: ID of the game to check

    Returns:
        bool: True if prediction exists, False otherwise
    """
    count = db.query(Prediction).filter(Prediction.game_id == game_id).count()
    return count > 0


def detect_anomalies(home_team: str, away_team: str, home_rating: float,
                     away_rating: float, home_win_prob: float) -> list:
    """
    Detect unusual predictions or ratings.

    Args:
        home_team: Home team name
        away_team: Away team name
        home_rating: Home team ELO rating
        away_rating: Away team ELO rating
        home_win_prob: Home team win probability (0.0-1.0)

    Returns:
        list: List of warning messages
    """
    warnings = []

    # Convert win prob to percentage for checks
    win_prob_pct = home_win_prob * 100

    # Check win probability range (5-95%)
    if win_prob_pct < 5 or win_prob_pct > 95:
        warnings.append(
            f"Unusual prediction: {home_team} vs {away_team} - {win_prob_pct:.1f}% confidence"
        )

    # Check rating ranges (1000-2500)
    if home_rating < 1000 or home_rating > 2500:
        warnings.append(f"Unusual rating: {home_team} has rating {home_rating:.0f}")

    if away_rating < 1000 or away_rating > 2500:
        warnings.append(f"Unusual rating: {away_team} has rating {away_rating:.0f}")

    # Check large rating gap (>500 points)
    rating_diff = abs(home_rating - away_rating)
    if rating_diff > 500:
        warnings.append(
            f"Large rating gap: {home_team} ({home_rating:.0f}) vs "
            f"{away_team} ({away_rating:.0f}) - difference: {rating_diff:.0f}"
        )

    return warnings


def rollback_predictions(db, start_time: str, end_time: str, dry_run: bool = False) -> int:
    """
    Delete predictions created within a time range.

    Args:
        db: Database session
        start_time: Start timestamp (format: "YYYY-MM-DD HH:MM:SS")
        end_time: End timestamp (format: "YYYY-MM-DD HH:MM:SS")
        dry_run: If True, only count predictions without deleting

    Returns:
        int: Number of predictions deleted (or would be deleted in dry-run)
    """
    # Parse timestamps
    try:
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {e}")
        logger.error('Expected format: "YYYY-MM-DD HH:%M:%S"')
        return 0

    # Query predictions in range
    predictions = db.query(Prediction).filter(
        Prediction.created_at >= start_dt,
        Prediction.created_at <= end_dt
    ).all()

    count = len(predictions)

    if count == 0:
        logger.info(f"No predictions found between {start_time} and {end_time}")
        return 0

    # Show what would be deleted
    logger.warning(f"Found {count} predictions to delete")

    if dry_run:
        logger.info(f"DRY RUN - Would delete {count} predictions")
        return count

    # Confirm deletion
    confirmation = input(f"Delete {count} predictions? (yes/no): ")
    if confirmation.lower() != 'yes':
        logger.info("Deletion cancelled")
        return 0

    # Delete predictions
    for pred in predictions:
        db.delete(pred)

    db.commit()
    logger.info(f"✓ Deleted {count} predictions from backfill run")

    return count


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Backfill historical predictions using historical ELO ratings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be created (no changes)
  python3 scripts/backfill_historical_predictions.py --dry-run

  # Backfill all historical predictions
  python3 scripts/backfill_historical_predictions.py

  # Backfill only 2025 season
  python3 scripts/backfill_historical_predictions.py --season 2025

  # Rollback predictions created between specific times
  python3 scripts/backfill_historical_predictions.py --delete-backfilled \\
    --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to database')
    parser.add_argument('--delete-backfilled', action='store_true',
                        help='Delete predictions from previous backfill run')
    parser.add_argument('--start-time', type=str,
                        help='Start time for rollback (format: "YYYY-MM-DD HH:MM:SS")')
    parser.add_argument('--end-time', type=str,
                        help='End time for rollback (format: "YYYY-MM-DD HH:MM:SS")')
    parser.add_argument('--season', type=int,
                        help='Process only specific season')

    args = parser.parse_args()

    # Validate rollback arguments
    if args.delete_backfilled:
        if not args.start_time or not args.end_time:
            parser.error('--delete-backfilled requires both --start-time and --end-time')

    return args


def backfill_predictions_for_season(db, season_year: int, dry_run: bool = False) -> dict:
    """
    Backfill predictions for all processed games in a season.

    Args:
        db: Database session
        season_year: Year of the season to process
        dry_run: If True, only preview changes without writing to database

    Returns:
        dict: Statistics about the backfill operation
    """
    stats = {
        'total_games': 0,
        'predictions_created': 0,
        'predictions_skipped': 0,
        'warnings': 0,
        'errors': 0
    }

    # Query all processed games without predictions (using outerjoin)
    games = db.query(Game).outerjoin(
        Prediction, Game.id == Prediction.game_id
    ).filter(
        Game.season == season_year,
        Game.is_processed == True,
        Prediction.id == None  # No prediction exists
    ).order_by(Game.week, Game.id).all()

    stats['total_games'] = len(games)

    if stats['total_games'] == 0:
        logger.info(f"No games found without predictions for season {season_year}")
        return stats

    logger.info(f"Found {stats['total_games']} processed games without predictions")

    # Process games by week for better logging
    games_by_week = {}
    for game in games:
        if game.week not in games_by_week:
            games_by_week[game.week] = []
        games_by_week[game.week].append(game)

    # Process each week
    for week in sorted(games_by_week.keys()):
        week_games = games_by_week[week]
        logger.info(f"\nWeek {week}: Processing {len(week_games)} games...")

        week_created = 0
        week_warnings = 0

        for game in week_games:
            try:
                # Get teams
                home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
                away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

                if not home_team or not away_team:
                    logger.error(f"Game {game.id}: Missing team data")
                    stats['errors'] += 1
                    continue

                # Get historical ratings (from week before game)
                home_rating = get_historical_rating(db, home_team.id, game.season, game.week)
                away_rating = get_historical_rating(db, away_team.id, game.season, game.week)

                # Track if we used default ratings
                if home_rating == 1500.0 or away_rating == 1500.0:
                    stats['warnings'] += 1
                    week_warnings += 1

                # Apply home field advantage (unless neutral site)
                home_rating_adjusted = home_rating + (0 if game.is_neutral_site else 65)
                away_rating_adjusted = away_rating

                # Calculate win probability
                home_win_prob = 1 / (1 + 10 ** ((away_rating_adjusted - home_rating_adjusted) / 400))
                away_win_prob = 1 - home_win_prob

                # Estimate scores
                base_score = 30
                rating_diff = home_rating_adjusted - away_rating_adjusted
                score_adjustment = (rating_diff / 100) * 3.5

                predicted_home_score = max(0, min(round(base_score + score_adjustment), 150))
                predicted_away_score = max(0, min(round(base_score - score_adjustment), 150))

                # Determine predicted winner
                if home_win_prob > 0.5:
                    predicted_winner_id = game.home_team_id
                    win_probability = home_win_prob
                else:
                    predicted_winner_id = game.away_team_id
                    win_probability = away_win_prob

                # Calculate timestamp (2 days before game)
                prediction_timestamp = calculate_prediction_timestamp(game)

                # Create Prediction object
                prediction = Prediction(
                    game_id=game.id,
                    predicted_winner_id=predicted_winner_id,
                    predicted_home_score=predicted_home_score,
                    predicted_away_score=predicted_away_score,
                    win_probability=win_probability,
                    home_elo_at_prediction=home_rating,
                    away_elo_at_prediction=away_rating,
                    was_correct=None,  # Will be calculated later
                    created_at=prediction_timestamp
                )

                db.add(prediction)
                week_created += 1

            except Exception as e:
                logger.error(f"Game {game.id}: Error creating prediction - {e}")
                stats['errors'] += 1
                continue

        # Commit all predictions for this week (or skip in dry-run mode)
        if dry_run:
            # In dry-run mode, rollback instead of commit
            db.rollback()
            stats['predictions_created'] += week_created

            # Log week summary
            if week_warnings > 0:
                logger.info(
                    f"  [DRY RUN] Would create {week_created} predictions "
                    f"({week_warnings} warnings for missing historical ratings)"
                )
            else:
                logger.info(f"  [DRY RUN] Would create {week_created} predictions")
        else:
            try:
                db.commit()
                stats['predictions_created'] += week_created

                # Log week summary
                if week_warnings > 0:
                    logger.info(
                        f"  ✓ Generated {week_created} predictions "
                        f"({week_warnings} warnings for missing historical ratings)"
                    )
                else:
                    logger.info(f"  ✓ Generated {week_created} predictions")

            except Exception as e:
                logger.error(f"Week {week}: Failed to commit predictions - {e}")
                db.rollback()
                stats['errors'] += len(week_games)

    return stats


def main():
    """
    Main entry point for historical prediction backfill.

    Processes all seasons with processed games and generates predictions
    using historical ELO ratings from before each game.
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Handle rollback mode
    if args.delete_backfilled:
        logger.info("=" * 80)
        logger.info("Retrospective Prediction Rollback")
        logger.info("=" * 80)

        db = SessionLocal()
        try:
            count = rollback_predictions(db, args.start_time, args.end_time, args.dry_run)
            logger.info("=" * 80)
            sys.exit(0)
        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            sys.exit(1)
        finally:
            db.close()
        return

    # Normal backfill mode
    if args.dry_run:
        logger.info("=" * 80)
        logger.info("Retrospective Prediction Backfill - DRY RUN MODE")
        logger.info("=" * 80)
    else:
        logger.info("=" * 80)
        logger.info("Retrospective Prediction Backfill")
        logger.info("=" * 80)

    start_time = datetime.now()
    db = SessionLocal()

    try:
        # Get all seasons with processed games (or specific season if provided)
        if args.season:
            seasons = [(args.season,)]
            logger.info(f"Processing only season: {args.season}")
        else:
            seasons = db.query(Game.season).filter(
                Game.is_processed == True
            ).distinct().order_by(Game.season).all()

        if not seasons:
            logger.info("No processed games found in database")
            logger.info("Run import_real_data.py first to import game data")
            return

        all_stats = {
            'total_games': 0,
            'predictions_created': 0,
            'predictions_skipped': 0,
            'warnings': 0,
            'errors': 0
        }

        # Process each season
        for (season_year,) in seasons:
            logger.info(f"\nSeason: {season_year}")
            season_stats = backfill_predictions_for_season(db, season_year, args.dry_run)

            # Aggregate stats
            all_stats['total_games'] += season_stats['total_games']
            all_stats['predictions_created'] += season_stats['predictions_created']
            all_stats['predictions_skipped'] += season_stats['predictions_skipped']
            all_stats['warnings'] += season_stats['warnings']
            all_stats['errors'] += season_stats['errors']

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Print summary
        logger.info("-" * 80)
        logger.info("Summary:")
        logger.info(f"  Total games processed: {all_stats['total_games']}")

        if args.dry_run:
            logger.info(f"  Predictions that would be created: {all_stats['predictions_created']}")
        else:
            logger.info(f"  Predictions created: {all_stats['predictions_created']}")

        logger.info(f"  Predictions skipped: {all_stats['predictions_skipped']} (already existed)")
        logger.info(f"  Warnings: {all_stats['warnings']} (missing historical ratings)")
        logger.info(f"  Errors: {all_stats['errors']}")
        logger.info(f"  Duration: {duration:.1f} seconds")

        if all_stats['predictions_created'] > 0 and not args.dry_run:
            avg_time = duration / all_stats['predictions_created']
            logger.info(f"  Average time per prediction: {avg_time:.3f} seconds")

        if args.dry_run:
            logger.info("\nDRY RUN - No changes written to database")
            logger.info("Run without --dry-run to commit changes")
        elif all_stats['errors'] == 0:
            logger.info("\n✅ Backfill completed successfully")
        else:
            logger.warning(f"\n⚠️  Backfill completed with {all_stats['errors']} errors")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
