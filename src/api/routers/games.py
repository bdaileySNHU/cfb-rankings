"""Game API routes.

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

@router.get("/api/games", response_model=List[schemas.Game], tags=["Games"])
async def get_games(
    season: Optional[int] = None,
    week: Optional[int] = None,
    team_id: Optional[int] = None,
    processed: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get games with flexible filtering options.

    Retrieves a paginated list of games with support for filtering by season,
    week, team, and processing status. Results are sorted by week (descending),
    then by game date (descending), then by game ID (descending) to show most
    recent games first in chronological order. Games without dates appear last
    within each week.

    Args:
        season: Filter by season year (e.g., 2024)
        week: Filter by specific week number (0-19, includes playoff weeks 16-19)
        team_id: Filter games involving specific team (home or away)
        processed: Filter by processing status (True=completed, False=scheduled)
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100, max: 500)
        db: Database session (injected by FastAPI)

    Returns:
        List[schemas.Game]: List of game objects matching filters, sorted
        chronologically (week DESC → date DESC → id DESC)

    Example:
        Get all Week 5 games in 2024:
            GET /api/games?season=2024&week=5

        Get unprocessed games for team 42:
            GET /api/games?team_id=42&processed=false
    """
    query = db.query(Game)

    if season:
        query = query.filter(Game.season == season)
    if week is not None:
        query = query.filter(Game.week == week)
    if team_id:
        query = query.filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    if processed is not None:
        query = query.filter(Game.is_processed == processed)

    # Sort by: week descending (most recent first)
    #          → game_date descending (most recent date first within week)
    #          → id descending (consistent tiebreaker)
    # Note: nulls_last() ensures games without dates appear after games with dates
    games = (
        query.order_by(
            Game.week.desc(), Game.game_date.desc().nulls_last(), Game.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return games


@router.get("/api/games/{game_id}", response_model=schemas.GameDetail, tags=["Games"])
async def get_game(game_id: int, db: Session = Depends(get_db)):
    """Get a specific game with comprehensive details.

    Retrieves detailed game information including team names, scores,
    winner/loser, and point differential for easy display.

    Args:
        game_id: Unique game identifier
        db: Database session (injected by FastAPI)

    Returns:
        schemas.GameDetail: Game object enriched with:
            - home_team_name, away_team_name
            - winner_name, loser_name
            - point_differential

    Raises:
        HTTPException: 404 if game not found

    Example:
        GET /api/games/123
    """
    game = db.query(Game).filter(Game.id == game_id).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    winner_name = game.home_team.name if game.home_score > game.away_score else game.away_team.name
    loser_name = game.away_team.name if game.home_score > game.away_score else game.home_team.name

    return {
        **game.__dict__,
        "home_team_name": game.home_team.name,
        "away_team_name": game.away_team.name,
        "winner_name": winner_name,
        "loser_name": loser_name,
        "point_differential": abs(game.home_score - game.away_score),
    }


@router.post("/api/games", response_model=schemas.GameResult, status_code=201, tags=["Games"])
async def create_game(game: schemas.GameCreate, db: Session = Depends(get_db)):
    """Create a new game and immediately update ELO rankings.

    Creates a game record and automatically processes it through the Modified
    ELO algorithm, updating both teams' ratings based on the outcome, score
    differential, and game context (home advantage, neutral site, etc.).

    Args:
        game: Game creation data including teams, scores, week, and season
        db: Database session (injected by FastAPI)

    Returns:
        schemas.GameResult: Processing result with ELO changes for both teams

    Raises:
        HTTPException: 404 if one or both teams not found
        HTTPException: 400 if team tries to play itself

    Example:
        POST /api/games
        {
            "home_team_id": 42,
            "away_team_id": 57,
            "home_score": 35,
            "away_score": 28,
            "season": 2024,
            "week": 5,
            "is_neutral_site": false
        }
    """
    # Verify teams exist
    home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
    away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

    if not home_team or not away_team:
        raise HTTPException(status_code=404, detail="One or both teams not found")

    if game.home_team_id == game.away_team_id:
        raise HTTPException(status_code=400, detail="Team cannot play itself")

    # Create game
    db_game = Game(**game.model_dump())
    db.add(db_game)
    db.commit()
    db.refresh(db_game)

    # Process game to update rankings
    ranking_service = RankingService(db)
    result = ranking_service.process_game(db_game)

    return result


# ============================================================================
# PREDICTION ENDPOINTS
# ============================================================================


