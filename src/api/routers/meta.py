"""Meta routes: health check, system stats, ranking recalculation.

Auto-extracted from the former monolithic main.py during the EPIC-043
backend modularization. Route paths and handler logic are unchanged.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.ranking_service import RankingService
from src.models import schemas
from src.models.database import get_db
from src.models.models import Game, Season, Team

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", tags=["Health"])
async def root():
    """Health check endpoint for service monitoring.

    Returns basic service information to verify the API is running and
    responsive. Use this endpoint for load balancer health checks.

    Returns:
        dict: Service status information including:
            - status: "healthy" if service is operational
            - service: Service name
            - version: Current API version

    Example:
        >>> import requests
        >>> response = requests.get("http://localhost:8000/")
        >>> response.json()
        {'status': 'healthy', 'service': 'College Football Ranking API', 'version': '1.0.0'}
    """
    return {"status": "healthy", "service": "College Football Ranking API", "version": "1.0.0"}


# ============================================================================
# TEAM ENDPOINTS
# ============================================================================


@router.get("/api/stats", response_model=schemas.SystemStats, tags=["Stats"])
async def get_stats(db: Session = Depends(get_db)):
    """Get overall system statistics and status.

    Retrieves high-level statistics about the ranking system including total
    teams, games, current season information, and last update timestamp.
    Useful for system monitoring and dashboard displays.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        schemas.SystemStats: System statistics including:
            - total_teams: Total number of teams in database
            - total_games: Total number of games (all seasons)
            - total_games_processed: Number of processed games
            - current_season: Active season year
            - current_week: Current week number
            - last_updated: Timestamp of this request

    Example:
        GET /api/stats
    """
    total_teams = db.query(Team).count()
    total_games = db.query(Game).count()
    total_processed = db.query(Game).filter(Game.is_processed == True).count()

    active_season = db.query(Season).filter(Season.is_active == True).first()

    return {
        "total_teams": total_teams,
        "total_games": total_games,
        "total_games_processed": total_processed,
        "current_season": active_season.year if active_season else 0,
        "current_week": active_season.current_week if active_season else 0,
        "last_updated": datetime.utcnow(),
    }


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================


@router.post("/api/calculate", response_model=schemas.SuccessResponse, tags=["Utility"])
async def recalculate_rankings(season: int, db: Session = Depends(get_db)):
    """Recalculate all rankings from scratch for a season.

    Resets all team ratings to preseason values and reprocesses all games
    in chronological order. Use this to fix ranking inconsistencies or apply
    algorithm changes retroactively.

    The process:
    1. Reset all teams to preseason ELO ratings
    2. Mark all games as unprocessed
    3. Reprocess games in week/ID order
    4. Update all ELO ratings and rating changes

    Args:
        season: Season year to recalculate (e.g., 2024)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.SuccessResponse: Confirmation with games processed count

    Warning:
        This operation can take several seconds for a full season
        (100+ games). All existing rating changes will be recalculated.

    Example:
        POST /api/calculate?season=2024
    """
    # Reset all teams
    ranking_service = RankingService(db)
    ranking_service.reset_season(season)

    # Get all games for the season in order
    games = db.query(Game).filter(Game.season == season).order_by(Game.week, Game.id).all()

    # Mark all as unprocessed
    for game in games:
        game.is_processed = False
        game.home_rating_change = 0.0
        game.away_rating_change = 0.0
    db.commit()

    # Reprocess all games
    processed_count = 0
    for game in games:
        ranking_service.process_game(game)
        processed_count += 1

    return {
        "message": f"Rankings recalculated for {season}",
        "data": {"season": season, "games_processed": processed_count},
    }


# ============================================================================
# ADMIN ENDPOINTS - API Usage Monitoring
# ============================================================================


