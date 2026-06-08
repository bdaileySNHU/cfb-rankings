"""Prediction API routes.

Auto-extracted from the former monolithic main.py during the EPIC-043
backend modularization. Route paths and handler logic are unchanged.
"""
import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.core.ranking_service import (
    RankingService,
    generate_predictions,
    get_overall_prediction_accuracy,
    get_team_prediction_accuracy,
)
from src.models import schemas
from src.models.database import get_db
from src.models.models import (
    APIUsage,
    ConferenceType,
    Game,
    Prediction,
    RankingHistory,
    Season,
    Team,
    UpdateTask,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/predictions", response_model=List[schemas.GamePrediction], tags=["Predictions"])
async def get_predictions(
    week: Optional[int] = Query(None, ge=0, le=20, description="Specific week number (0-20, includes playoffs)"),
    team_id: Optional[int] = Query(None, ge=1, description="Filter by team ID"),
    next_week: bool = Query(True, description="Only show next week's games"),
    season: Optional[int] = Query(None, ge=2020, description="Season year"),
    db: Session = Depends(get_db),
):
    """
    Get game predictions for upcoming games.

    Returns predictions with winner, scores, and win probabilities based on
    current ELO ratings. Predictions use the same ELO formula as game processing
    but applied in reverse to forecast outcomes.

    **Query Parameters:**
    - **week**: Get predictions for specific week (0-20, includes playoff weeks)
    - **team_id**: Filter predictions involving specific team
    - **next_week**: Only show next week's games (default: true)
    - **season**: Season year (defaults to current year)

    **Returns:**
    - Array of predictions with winner, scores, probabilities, and confidence
    """
    try:
        from sqlalchemy import or_

        # Determine season year
        if not season:
            from src.integrations.cfbd_client import CFBDClient
            client = CFBDClient()
            season = client.get_current_season()

        # First, check if we have stored predictions for unprocessed games
        query = db.query(Prediction).join(Game).filter(
            Game.is_processed == False,
            Game.season == season
        )

        # Apply filters
        if week is not None:
            query = query.filter(Game.week == week)
        if team_id:
            query = query.filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))

        stored_predictions = query.all()

        # If we have stored predictions, return those
        if stored_predictions:
            logger.info(f"Returning {len(stored_predictions)} stored predictions")
            result = []
            for pred in stored_predictions:
                game = pred.game

                # Calculate confidence level based on win probability
                win_prob = pred.win_probability * 100
                if win_prob >= 80:
                    confidence = "Very High"
                elif win_prob >= 70:
                    confidence = "High"
                elif win_prob >= 60:
                    confidence = "Medium"
                else:
                    confidence = "Low"

                result.append({
                    "game_id": game.id,
                    "home_team_id": game.home_team_id,
                    "home_team": game.home_team.name,
                    "home_team_rating": pred.home_elo_at_prediction,
                    "away_team_id": game.away_team_id,
                    "away_team": game.away_team.name,
                    "away_team_rating": pred.away_elo_at_prediction,
                    "predicted_winner_id": pred.predicted_winner_id,
                    "predicted_winner": pred.predicted_winner.name if pred.predicted_winner else None,
                    "predicted_home_score": pred.predicted_home_score,
                    "predicted_away_score": pred.predicted_away_score,
                    "home_win_probability": pred.win_probability * 100 if pred.predicted_winner_id == game.home_team_id else (1 - pred.win_probability) * 100,
                    "away_win_probability": pred.win_probability * 100 if pred.predicted_winner_id == game.away_team_id else (1 - pred.win_probability) * 100,
                    "is_neutral_site": game.is_neutral_site,
                    "confidence": confidence,
                    "week": game.week,
                    "season": game.season,
                })
            return result

        # Otherwise, generate predictions on-the-fly
        logger.info("No stored predictions found, generating new predictions")
        predictions = generate_predictions(
            db=db, week=week, team_id=team_id, next_week=next_week, season_year=season
        )
        return predictions
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting predictions: {str(e)}")


@router.get(
    "/api/predictions/historical",
    response_model=schemas.HistoricalPredictionSummary,
    tags=["Predictions"],
)
async def get_historical_predictions(
    season: int = Query(..., ge=2020, description="Season year"),
    week: int = Query(..., ge=1, le=20, description="Week number"),
    db: Session = Depends(get_db),
):
    """Simulate predictions for a completed historical week using ranking_history ELO.

    For each processed game in the specified season/week, retrieves both teams'
    ELO ratings from ranking_history at that point in time, runs the standard
    win-probability formula, and compares the simulated prediction against the
    actual game result.

    Useful for backtesting algorithm changes: adjust weights in the simulator,
    then check this endpoint to see how those weights would have performed on
    real historical matchups.
    """
    try:
        # Fetch all processed games for this season/week
        games = (
            db.query(Game)
            .filter(Game.season == season, Game.week == week, Game.is_processed == True)
            .all()
        )

        predictions = []
        for game in games:
            home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
            away_team = db.query(Team).filter(Team.id == game.away_team_id).first()
            if not home_team or not away_team:
                continue

            # Look up historical ELO — prefer the snapshot from this week,
            # fall back to the most recent snapshot before this week
            def get_elo_at_week(team_id: int) -> float:
                row = (
                    db.query(RankingHistory.elo_rating)
                    .filter(
                        RankingHistory.team_id == team_id,
                        RankingHistory.season == season,
                        RankingHistory.week <= week,
                        RankingHistory.week != 999,
                    )
                    .order_by(RankingHistory.week.desc())
                    .first()
                )
                if row:
                    return row[0]
                # No history — fall back to team's current rating
                return home_team.elo_rating if team_id == home_team.id else away_team.elo_rating

            home_elo = get_elo_at_week(home_team.id)
            away_elo = get_elo_at_week(away_team.id)

            # Win probability (home field advantage: +65 unless neutral)
            home_adj = home_elo + (0 if game.is_neutral_site else 65)
            home_win_prob = 1 / (1 + 10 ** ((away_elo - home_adj) / 400))
            away_win_prob = 1 - home_win_prob

            # Score estimate
            rating_diff = home_adj - away_elo
            score_adj = (rating_diff / 100) * 3.5
            pred_home = max(0, min(150, round(30 + score_adj)))
            pred_away = max(0, min(150, round(30 - score_adj)))

            # Confidence
            margin = abs(home_win_prob - 0.5)
            confidence = "High" if margin > 0.3 else "Medium" if margin > 0.15 else "Low"

            predicted_winner_is_home = home_win_prob >= 0.5

            # Actual result
            actual_home = game.home_score
            actual_away = game.away_score
            actual_winner_id = None
            actual_winner = None
            prediction_correct = None
            if actual_home is not None and actual_away is not None:
                actual_winner_id = home_team.id if actual_home > actual_away else away_team.id
                actual_winner = home_team.name if actual_home > actual_away else away_team.name
                predicted_winner_id = home_team.id if predicted_winner_is_home else away_team.id
                prediction_correct = (predicted_winner_id == actual_winner_id)

            predictions.append(schemas.HistoricalPrediction(
                game_id=game.id,
                week=game.week,
                season=game.season,
                game_date=game.game_date.isoformat() if game.game_date else None,
                is_neutral_site=game.is_neutral_site,
                home_team_id=home_team.id,
                home_team=home_team.name,
                home_team_rating=round(home_elo, 1),
                home_win_probability=round(home_win_prob * 100, 1),
                away_team_id=away_team.id,
                away_team=away_team.name,
                away_team_rating=round(away_elo, 1),
                away_win_probability=round(away_win_prob * 100, 1),
                predicted_winner=home_team.name if predicted_winner_is_home else away_team.name,
                predicted_winner_id=home_team.id if predicted_winner_is_home else away_team.id,
                predicted_home_score=pred_home,
                predicted_away_score=pred_away,
                confidence=confidence,
                actual_home_score=actual_home,
                actual_away_score=actual_away,
                actual_winner=actual_winner,
                actual_winner_id=actual_winner_id,
                prediction_correct=prediction_correct,
            ))

        games_with_results = sum(1 for p in predictions if p.prediction_correct is not None)
        correct = sum(1 for p in predictions if p.prediction_correct is True)
        accuracy = round(correct / games_with_results * 100, 1) if games_with_results > 0 else None

        return schemas.HistoricalPredictionSummary(
            season=season,
            week=week,
            total_games=len(predictions),
            games_with_results=games_with_results,
            correct_predictions=correct,
            accuracy_percentage=accuracy,
            predictions=predictions,
        )

    except Exception as e:
        logger.error(f"Error generating historical predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating historical predictions: {e}")


@router.get(
    "/api/predictions/accuracy",
    response_model=schemas.PredictionAccuracyStats,
    tags=["Predictions"],
)
async def get_prediction_accuracy(
    season: Optional[int] = Query(None, description="Filter by season year"),
    db: Session = Depends(get_db),
):
    """
    Get overall prediction accuracy statistics.

    Part of EPIC-009: Prediction Accuracy Tracking.
    Returns comprehensive accuracy statistics including total predictions,
    evaluated predictions, and accuracy percentage.

    **Query Parameters:**
    - **season**: Optional season filter (defaults to all seasons)

    **Returns:**
    - Overall accuracy statistics with breakdown by confidence level
    """
    try:
        stats = get_overall_prediction_accuracy(db, season=season)
        return stats
    except Exception as e:
        logger.error(f"Error retrieving prediction accuracy: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving prediction accuracy: {str(e)}"
        )


@router.get(
    "/api/predictions/accuracy/team/{team_id}",
    response_model=schemas.TeamPredictionAccuracy,
    tags=["Predictions"],
)
async def get_team_prediction_accuracy_endpoint(
    team_id: int,
    season: Optional[int] = Query(None, description="Filter by season year"),
    db: Session = Depends(get_db),
):
    """
    Get prediction accuracy for a specific team.

    Part of EPIC-009: Prediction Accuracy Tracking.
    Returns team-specific accuracy statistics including accuracy when
    predicted to win (as favorite) vs predicted to lose (as underdog).

    **Path Parameters:**
    - **team_id**: Team ID to get accuracy for

    **Query Parameters:**
    - **season**: Optional season filter (defaults to all seasons)

    **Returns:**
    - Team-specific accuracy statistics
    """
    try:
        stats = get_team_prediction_accuracy(db, team_id=team_id, season=season)
        return stats
    except Exception as e:
        logger.error(f"Error retrieving team prediction accuracy: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving team prediction accuracy: {str(e)}"
        )


@router.get(
    "/api/predictions/stored", response_model=List[schemas.StoredPrediction], tags=["Predictions"]
)
async def get_stored_predictions(
    season: Optional[int] = Query(None, description="Filter by season year"),
    week: Optional[int] = Query(None, ge=0, le=20, description="Filter by week (includes playoffs)"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    evaluated_only: bool = Query(False, description="Only return evaluated predictions"),
    db: Session = Depends(get_db),
):
    """
    Get stored predictions with evaluation results.

    Part of EPIC-009: Prediction Accuracy Tracking.
    Returns previously stored predictions with their was_correct evaluation.

    **Query Parameters:**
    - **season**: Filter by season year
    - **week**: Filter by week number (0-20, includes playoff weeks)
    - **team_id**: Filter by team ID (home or away)
    - **evaluated_only**: Only return predictions that have been evaluated

    **Returns:**
    - List of stored predictions with evaluation status
    """
    try:
        from sqlalchemy import or_

        # Build query
        query = db.query(Prediction).join(Game)

        # Apply filters
        if season:
            query = query.filter(Game.season == season)
        if week is not None:
            query = query.filter(Game.week == week)
        if team_id:
            query = query.filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))
        if evaluated_only:
            query = query.filter(Prediction.was_correct.isnot(None))

        # Execute query
        predictions = query.order_by(Game.week.desc(), Game.id.desc()).limit(100).all()

        # Enrich with game details
        result = []
        for pred in predictions:
            game = pred.game
            result.append(
                {
                    "id": pred.id,
                    "game_id": pred.game_id,
                    "predicted_winner_id": pred.predicted_winner_id,
                    "predicted_winner_name": (
                        pred.predicted_winner.name if pred.predicted_winner else None
                    ),
                    "predicted_home_score": pred.predicted_home_score,
                    "predicted_away_score": pred.predicted_away_score,
                    "win_probability": pred.win_probability,
                    "home_elo_at_prediction": pred.home_elo_at_prediction,
                    "away_elo_at_prediction": pred.away_elo_at_prediction,
                    "was_correct": pred.was_correct,
                    "created_at": pred.created_at,
                    "home_team_name": game.home_team.name if game.home_team else None,
                    "away_team_name": game.away_team.name if game.away_team else None,
                    "actual_home_score": game.home_score if game.is_processed else None,
                    "actual_away_score": game.away_score if game.is_processed else None,
                    "week": game.week,
                    "season": game.season,
                }
            )

        return result

    except Exception as e:
        logger.error(f"Error retrieving stored predictions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving stored predictions: {str(e)}"
        )


@router.get(
    "/api/predictions/comparison", response_model=schemas.ComparisonStats, tags=["Predictions"]
)
async def get_prediction_comparison(
    season: Optional[int] = Query(None, description="Season year (defaults to active season)"),
    db: Session = Depends(get_db),
):
    """
    Compare ELO prediction accuracy vs AP Poll prediction accuracy.

    Part of EPIC-010: AP Poll Prediction Comparison.

    Compares how well the ELO system predicts game outcomes versus the
    AP Poll "predictions" (where higher-ranked team is predicted to win).

    **Query Parameters:**
    - **season**: Season year to compare (defaults to active season)

    **Returns:**
    - Comprehensive comparison statistics including:
        - Overall accuracy for each system
        - Breakdown by week
        - Games where systems disagreed
        - Detailed accuracy metrics

    **Example:**
    ```
    GET /api/predictions/comparison?season=2024
    ```
    """
    try:
        from src.core.ap_poll_service import calculate_comparison_stats

        # Get active season if not specified
        if not season:
            active_season = db.query(Season).filter(Season.is_active == True).first()
            if not active_season:
                raise HTTPException(status_code=404, detail="No active season found")
            season = active_season.year

        # Calculate comparison statistics
        comparison_stats = calculate_comparison_stats(db, season)

        # Check if we have any comparison data - return graceful empty state
        if comparison_stats.get("total_games_compared", 0) == 0:
            logger.info(f"No comparison data available for season {season} - returning empty state")

        return comparison_stats

    except HTTPException:
        raise
    except Exception as e:
        # Log error with full traceback for debugging
        logger.error(f"Error calculating prediction comparison: {str(e)}", exc_info=True)
        # Return graceful empty state instead of 500 error
        return {
            "season": season if season else 2025,
            "elo_accuracy": 0.0,
            "ap_accuracy": 0.0,
            "elo_advantage": 0.0,
            "total_games_compared": 0,
            "elo_correct": 0,
            "ap_correct": 0,
            "both_correct": 0,
            "elo_only_correct": 0,
            "ap_only_correct": 0,
            "both_wrong": 0,
            "by_week": [],
            "disagreements": [],
            "overall_elo_accuracy": 0.0,
            "overall_elo_total": 0,
            "overall_elo_correct": 0,
            "message": "Comparison data is currently unavailable. Please try again later.",
        }


# ============================================================================
# RANKING ENDPOINTS
# ============================================================================


