#!/usr/bin/env python3
"""
Generate predictions for upcoming games
Used after deployment to populate prediction data
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from ranking_service import generate_predictions
from models import Prediction
from datetime import datetime

def main():
    print("Generating predictions for upcoming games...")

    db = SessionLocal()
    try:
        # Generate prediction dictionaries
        prediction_dicts = generate_predictions(db)
        print(f"\n📊 Generated {len(prediction_dicts)} prediction calculations")

        if not prediction_dicts:
            print("\nℹ️  No upcoming games to predict")
            print("   Predictions will be generated when new games are imported")
            return

        # Save predictions to database
        print("💾 Saving predictions to database...")
        saved_count = 0

        for pred_dict in prediction_dicts:
            # Create Prediction model instance
            prediction = Prediction(
                game_id=pred_dict['game_id'],
                predicted_winner_id=pred_dict['predicted_winner_id'],
                predicted_home_score=pred_dict['predicted_home_score'],
                predicted_away_score=pred_dict['predicted_away_score'],
                win_probability=pred_dict['win_probability'],
                home_elo_at_prediction=pred_dict['home_elo_at_prediction'],
                away_elo_at_prediction=pred_dict['away_elo_at_prediction'],
                was_correct=None,  # Will be evaluated after game is played
                created_at=datetime.now()
            )
            db.add(prediction)
            saved_count += 1

        # Commit all predictions
        db.commit()
        print(f"\n✅ Successfully saved {saved_count} predictions to database")

        # Show sample of saved predictions
        print("\nSample predictions:")
        for pred_dict in prediction_dicts[:5]:
            print(f"  - Game {pred_dict['game_id']}: Winner {pred_dict['predicted_winner_id']} (confidence: {pred_dict['win_probability']:.1%})")

    except Exception as e:
        print(f"\n❌ Error generating predictions: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
