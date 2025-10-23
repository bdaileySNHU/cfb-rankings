#!/usr/bin/env python3
"""
Check predictions in the database
Quick diagnostic script to see what predictions exist
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Prediction, Game
from sqlalchemy import func

def main():
    print("=" * 60)
    print("Prediction Database Check")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Total predictions
        total_count = db.query(Prediction).count()
        print(f"\n📊 Total predictions in database: {total_count}")

        if total_count == 0:
            print("\n⚠️  No predictions found!")
            print("   Run: python3 scripts/generate_predictions.py")
            return

        # Predictions by season
        print("\n📅 Predictions by season:")
        season_counts = db.query(
            Game.season,
            func.count(Prediction.id).label('count')
        ).join(Game, Prediction.game_id == Game.id)\
         .group_by(Game.season)\
         .all()

        for season, count in season_counts:
            print(f"   Season {season}: {count} predictions")

        # Evaluated vs unevaluated
        evaluated = db.query(Prediction).filter(Prediction.was_correct != None).count()
        unevaluated = total_count - evaluated
        print(f"\n✅ Evaluated predictions: {evaluated}")
        print(f"⏳ Unevaluated (future games): {unevaluated}")

        # Sample predictions
        print("\n📋 Sample predictions (first 5):")
        predictions = db.query(Prediction)\
            .join(Game, Prediction.game_id == Game.id)\
            .order_by(Prediction.id)\
            .limit(5)\
            .all()

        for pred in predictions:
            status = "✓" if pred.was_correct == True else ("✗" if pred.was_correct == False else "⏳")
            print(f"   {status} ID: {pred.id}, Game: {pred.game_id}, "
                  f"Winner: {pred.predicted_winner_id}, "
                  f"Probability: {pred.win_probability:.1%}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
