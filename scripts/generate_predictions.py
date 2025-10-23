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

def main():
    print("Generating predictions for upcoming games...")

    db = SessionLocal()
    try:
        predictions = generate_predictions(db)
        print(f"\n✅ Successfully generated {len(predictions)} predictions")

        if predictions:
            print("\nSample predictions:")
            for pred in predictions[:5]:
                print(f"  - Game {pred.game_id}: {pred.predicted_winner_id} (confidence: {pred.win_probability:.1%})")
        else:
            print("\nℹ️  No upcoming games to predict")
            print("   Predictions will be generated when new games are imported")

    except Exception as e:
        print(f"\n❌ Error generating predictions: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
