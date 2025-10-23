"""
Backfill Historical Predictions for Completed Games
EPIC-010: AP Poll Prediction Comparison

This script generates predictions for all completed games using the ELO ratings
that were in effect BEFORE each game was played (from saved_rankings table).
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Game, Prediction, Team, RankingHistory


def get_team_elo_before_game(db, team_id: int, season: int, week: int) -> float:
    """
    Get team's ELO rating before a game in a specific week.

    For week N, we want the rating from week N-1 (before the game was played).
    For week 1, we use the initial rating from the preseason.
    """
    if week == 1:
        # For week 1, get the team's initial rating
        team = db.query(Team).filter(Team.id == team_id).first()
        return team.initial_rating if team else 1500.0

    # For other weeks, get the saved ranking from the previous week
    prev_week_ranking = db.query(RankingHistory).filter(
        RankingHistory.team_id == team_id,
        RankingHistory.season == season,
        RankingHistory.week == week - 1
    ).first()

    if prev_week_ranking:
        return prev_week_ranking.elo_rating

    # Fallback: get team's current rating
    team = db.query(Team).filter(Team.id == team_id).first()
    return team.elo_rating if team else 1500.0


def backfill_historical_predictions(db, season: int):
    """
    Create predictions for all completed games using historical ELO ratings.

    Args:
        db: Database session
        season: Season year
    """
    # Get all completed games without predictions
    games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False  # Only FBS vs FBS games
    ).order_by(Game.week, Game.id).all()

    total_games = len(games)
    games_with_predictions = 0
    predictions_created = 0
    errors = 0

    print(f"\nFound {total_games} completed games for season {season}")
    print("Creating historical predictions using pre-game ELO ratings...\n")

    for game in games:
        # Check if prediction already exists
        existing = db.query(Prediction).filter(Prediction.game_id == game.id).first()

        if existing:
            games_with_predictions += 1
            continue

        try:
            # Get ELO ratings BEFORE the game was played
            home_elo = get_team_elo_before_game(db, game.home_team_id, game.season, game.week)
            away_elo = get_team_elo_before_game(db, game.away_team_id, game.season, game.week)

            # Apply home field advantage (unless neutral site)
            home_rating_adjusted = home_elo + (0 if game.is_neutral_site else 65)
            away_rating_adjusted = away_elo

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

            # Determine actual winner
            actual_winner_id = game.home_team_id if game.home_score > game.away_score else game.away_team_id
            was_correct = (predicted_winner_id == actual_winner_id)

            # Create prediction record
            prediction = Prediction(
                game_id=game.id,
                predicted_winner_id=predicted_winner_id,
                predicted_home_score=predicted_home_score,
                predicted_away_score=predicted_away_score,
                win_probability=win_probability,
                home_elo_at_prediction=home_elo,
                away_elo_at_prediction=away_elo,
                was_correct=was_correct,
                created_at=datetime.utcnow()
            )

            db.add(prediction)
            predictions_created += 1

            if predictions_created % 50 == 0:
                db.commit()  # Commit in batches
                print(f"  Created {predictions_created} predictions...")

        except Exception as e:
            print(f"  Error creating prediction for game {game.id}: {e}")
            errors += 1

    # Final commit
    db.commit()

    print(f"\nBackfill complete!")
    print(f"  Total games: {total_games}")
    print(f"  Already had predictions: {games_with_predictions}")
    print(f"  Predictions created: {predictions_created}")
    if errors > 0:
        print(f"  Errors: {errors}")


def main():
    """Main backfill function"""
    print("="*80)
    print("BACKFILL HISTORICAL PREDICTIONS FOR COMPLETED GAMES")
    print("EPIC-010: AP Poll Prediction Comparison")
    print("="*80)
    print()
    print("This will create predictions for completed games using the ELO ratings")
    print("that were in effect BEFORE each game was played.")
    print()

    # Get database session
    db = SessionLocal()

    # Backfill for 2025 season
    backfill_historical_predictions(db, 2025)

    db.close()

    print()
    print("✓ Done! You can now view the comparison page.")
    print()


if __name__ == "__main__":
    main()
