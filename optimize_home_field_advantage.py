"""
Test different home field advantage values to find optimal accuracy

This script backtests various HFA values to determine which produces
the best prediction accuracy.
"""

import math
import sys
from typing import List, Tuple

from database import SessionLocal
from models import Game, Team


def calculate_expected_score(rating_a: float, rating_b: float) -> float:
    """Calculate expected win probability for team A"""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))


def test_home_field_advantage(hfa: int, season: int = 2025) -> dict:
    """
    Test a specific home field advantage value

    Args:
        hfa: Home field advantage points to test
        season: Season to test on

    Returns:
        dict with accuracy metrics
    """
    db = SessionLocal()

    try:
        # Get all processed games
        games = db.query(Game).filter(
            Game.season == season,
            Game.is_processed == True,
            Game.excluded_from_rankings == False
        ).all()

        if not games:
            return {"hfa": hfa, "accuracy": 0.0, "total": 0, "correct": 0}

        # Get final team ratings (after all games processed)
        teams = {t.id: t.elo_rating for t in db.query(Team).all()}

        correct = 0
        total = 0

        for game in games:
            # Get team ratings
            home_rating = teams.get(game.home_team_id, 1500)
            away_rating = teams.get(game.away_team_id, 1500)

            # Apply home field advantage (unless neutral site)
            if not game.is_neutral_site:
                home_rating_adj = home_rating + hfa
            else:
                home_rating_adj = home_rating

            # Calculate prediction
            home_win_prob = calculate_expected_score(home_rating_adj, away_rating)

            # Predicted winner
            predicted_home_win = home_win_prob > 0.5

            # Actual winner
            actual_home_win = game.home_score > game.away_score

            # Check if correct
            if predicted_home_win == actual_home_win:
                correct += 1

            total += 1

        accuracy = correct / total if total > 0 else 0.0

        return {
            "hfa": hfa,
            "accuracy": accuracy,
            "accuracy_pct": accuracy * 100,
            "total": total,
            "correct": correct
        }

    finally:
        db.close()


def optimize_home_field_advantage(season: int = 2025):
    """
    Test multiple HFA values to find optimal setting

    Tests HFA values from 0 to 100 in increments of 5
    """
    print("=" * 80)
    print(f"HOME FIELD ADVANTAGE OPTIMIZATION - {season} Season")
    print("=" * 80)
    print()
    print("Testing different home field advantage values...")
    print()

    # Test range of HFA values
    hfa_values = range(0, 105, 5)
    results = []

    for hfa in hfa_values:
        result = test_home_field_advantage(hfa, season)
        results.append(result)
        print(f"  HFA = {hfa:3d} points: {result['accuracy_pct']:.2f}% ({result['correct']}/{result['total']})")

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    # Find best HFA
    best = max(results, key=lambda x: x['accuracy'])

    print(f"Current HFA:  65 points")
    print(f"Best HFA:     {best['hfa']} points")
    print(f"Best Accuracy: {best['accuracy_pct']:.2f}%")
    print()

    # Show improvement
    current = next((r for r in results if r['hfa'] == 65), None)
    if current and best['hfa'] != 65:
        improvement = best['accuracy_pct'] - current['accuracy_pct']
        print(f"Potential Improvement: +{improvement:.2f} percentage points")
        print(f"  ({current['accuracy_pct']:.2f}% → {best['accuracy_pct']:.2f}%)")
    elif best['hfa'] == 65:
        print("Current HFA is already optimal!")

    print()
    print("=" * 80)

    # Top 5 HFA values
    print()
    print("Top 5 HFA values:")
    print("-" * 40)
    top_5 = sorted(results, key=lambda x: x['accuracy'], reverse=True)[:5]
    for i, result in enumerate(top_5, 1):
        print(f"  {i}. HFA = {result['hfa']:3d}: {result['accuracy_pct']:.2f}%")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize home field advantage")
    parser.add_argument("--season", type=int, default=2025, help="Season to test")

    args = parser.parse_args()

    optimize_home_field_advantage(args.season)
