#!/usr/bin/env python3
"""
Generate predictions for ALL upcoming games (not just next week)
Useful for playoff games and special cases
"""

import argparse
import os
import sys

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from src.models.database import SessionLocal
from src.models.models import Prediction
from src.core.ranking_service import generate_predictions
from src.integrations.cfbd_client import CFBDClient


def main():
    parser = argparse.ArgumentParser(description="Generate predictions for all upcoming games")
    parser.add_argument(
        "--season",
        type=int,
        help="Season year (defaults to current CFB season, which handles Jan playoffs correctly)",
    )
    args = parser.parse_args()

    # Determine season year using CFB season logic
    # This correctly handles January playoffs as part of previous year's season
    if args.season:
        season_year = args.season
    else:
        client = CFBDClient()
        season_year = client.get_current_season()

    print(f"Generating predictions for ALL upcoming games in {season_year} season...")

    db = SessionLocal()
    try:
        # Generate predictions for ALL unprocessed games (next_week=False)
        prediction_dicts = generate_predictions(db, next_week=False, season_year=season_year)
        print(f"\n📊 Generated {len(prediction_dicts)} prediction calculations")

        if not prediction_dicts:
            print("\nℹ️  No upcoming games to predict")
            print("   Predictions will be generated when new games are imported")
            return

        # Save predictions to database
        print("💾 Saving predictions to database...")
        saved_count = 0

        for pred_dict in prediction_dicts:
            # Check if prediction already exists for this game
            existing = db.query(Prediction).filter(
                Prediction.game_id == pred_dict["game_id"]
            ).first()

            if existing:
                print(f"   Skipping game {pred_dict['game_id']} - prediction already exists")
                continue

            # Determine win probability for the predicted winner
            if pred_dict["predicted_winner_id"] == pred_dict["home_team_id"]:
                win_prob = pred_dict["home_win_probability"] / 100.0
            else:
                win_prob = pred_dict["away_win_probability"] / 100.0

            # Create Prediction model instance
            prediction = Prediction(
                game_id=pred_dict["game_id"],
                predicted_winner_id=pred_dict["predicted_winner_id"],
                predicted_home_score=pred_dict["predicted_home_score"],
                predicted_away_score=pred_dict["predicted_away_score"],
                win_probability=win_prob,
                home_elo_at_prediction=pred_dict["home_team_rating"],
                away_elo_at_prediction=pred_dict["away_team_rating"],
                was_correct=None,
                created_at=datetime.now(),
            )
            db.add(prediction)
            saved_count += 1

        # Commit all predictions
        db.commit()
        print(f"\n✅ Successfully saved {saved_count} predictions to database")

        # Show sample of saved predictions
        print("\nSample predictions:")
        for pred_dict in prediction_dicts[:10]:
            win_prob_display = (
                pred_dict["home_win_probability"]
                if pred_dict["predicted_winner_id"] == pred_dict["home_team_id"]
                else pred_dict["away_win_probability"]
            )
            print(
                f"  - Game {pred_dict['game_id']}: {pred_dict['predicted_winner']} (confidence: {win_prob_display}%)"
            )

    except Exception as e:
        print(f"\n❌ Error generating predictions: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
