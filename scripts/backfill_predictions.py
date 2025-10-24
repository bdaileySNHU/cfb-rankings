"""
Backfill Predictions for Completed Games
EPIC-010: AP Poll Prediction Comparison

This script generates predictions for all completed games that don't have predictions yet.
This is needed for the comparison feature to work with historical games.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Game, Prediction
from ranking_service import create_and_store_prediction


def backfill_predictions(db, season: int):
    """
    Create predictions for all completed games that don't have predictions.

    Args:
        db: Database session
        season: Season year
    """
    # Get all completed games without predictions
    games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False  # Only FBS vs FBS games
    ).all()

    total_games = len(games)
    games_with_predictions = 0
    predictions_created = 0

    print(f"\nFound {total_games} completed games for season {season}")
    print("Checking for missing predictions...\n")

    for game in games:
        # Check if prediction already exists
        existing = db.query(Prediction).filter(Prediction.game_id == game.id).first()

        if existing:
            games_with_predictions += 1
            continue

        # Create prediction for this game
        prediction = create_and_store_prediction(db, game)

        if prediction:
            predictions_created += 1
            if predictions_created % 50 == 0:
                print(f"  Created {predictions_created} predictions...")

    print(f"\nBackfill complete!")
    print(f"  Total games: {total_games}")
    print(f"  Already had predictions: {games_with_predictions}")
    print(f"  Predictions created: {predictions_created}")


def main():
    """Main backfill function"""
    print("="*80)
    print("BACKFILL PREDICTIONS FOR COMPLETED GAMES")
    print("EPIC-010: AP Poll Prediction Comparison")
    print("="*80)
    print()

    # Get database session
    db = SessionLocal()

    # Backfill for 2025 season
    backfill_predictions(db, 2025)

    db.close()

    print()
    print("✓ Done! You can now view the comparison page.")
    print()


if __name__ == "__main__":
    main()
