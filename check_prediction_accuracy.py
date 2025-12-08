"""
Check actual prediction accuracy from database
"""

from database import SessionLocal
from models import Game, Prediction

db = SessionLocal()

try:
    # Get all evaluated predictions
    total = db.query(Prediction).filter(Prediction.was_correct.isnot(None)).count()
    correct = db.query(Prediction).filter(Prediction.was_correct == True).count()

    print("=" * 60)
    print("PREDICTION ACCURACY CHECK")
    print("=" * 60)
    print()
    print(f"Total predictions evaluated: {total}")
    print(f"Correct predictions: {correct}")
    print(f"Incorrect predictions: {total - correct}")

    if total > 0:
        accuracy = 100.0 * correct / total
        print(f"Accuracy: {accuracy:.1f}%")
    else:
        print("Accuracy: N/A (no predictions found)")

    print()

    # Get predictions by season
    predictions_with_games = db.query(Prediction).join(Game).filter(
        Prediction.was_correct.isnot(None)
    ).all()

    if predictions_with_games:
        seasons = {}
        for pred in predictions_with_games:
            season = pred.game.season
            if season not in seasons:
                seasons[season] = {'total': 0, 'correct': 0}
            seasons[season]['total'] += 1
            if pred.was_correct:
                seasons[season]['correct'] += 1

        print("Breakdown by season:")
        print("-" * 60)
        for season in sorted(seasons.keys()):
            total_season = seasons[season]['total']
            correct_season = seasons[season]['correct']
            accuracy_season = 100.0 * correct_season / total_season
            print(f"  {season}: {correct_season}/{total_season} = {accuracy_season:.1f}%")

    print()
    print("=" * 60)

finally:
    db.close()
