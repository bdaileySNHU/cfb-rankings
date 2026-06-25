"""Season management API routes.

Auto-extracted from the former monolithic main.py during the EPIC-043
backend modularization. Route paths and handler logic are unchanged.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.ranking_service import RankingService
from src.models import schemas
from src.models.database import get_db
from src.models.models import Season

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/seasons", response_model=List[schemas.SeasonResponse], tags=["Seasons"])
async def get_seasons(db: Session = Depends(get_db)):
    """Get all seasons sorted by year (most recent first).

    Retrieves a list of all seasons in the system with their year, current
    week, and active status. Used for season selection in the UI.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        List[schemas.SeasonResponse]: List of season objects

    Example:
        GET /api/seasons
    """
    seasons = db.query(Season).order_by(Season.year.desc()).all()
    return seasons


@router.post("/api/seasons", response_model=schemas.SeasonResponse, status_code=201, tags=["Seasons"])
async def create_season(year: int, db: Session = Depends(get_db)):
    """Create a new season with initial configuration.

    Creates a new season record with current_week set to 0 and is_active
    set to True. Use this at the start of each new football season.

    Args:
        year: Season year (e.g., 2024)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.SeasonResponse: Created season object

    Raises:
        HTTPException: 400 if season already exists for that year

    Example:
        POST /api/seasons?year=2025
    """
    existing = db.query(Season).filter(Season.year == year).first()
    if existing:
        raise HTTPException(status_code=400, detail="Season already exists")

    season = Season(year=year, current_week=0, is_active=True)
    db.add(season)
    db.commit()
    db.refresh(season)

    return season


@router.post("/api/seasons/{year}/reset", response_model=schemas.SuccessResponse, tags=["Seasons"])
async def reset_season(year: int, db: Session = Depends(get_db)):
    """Reset all team ratings for a new season.

    Recalculates initial ELO ratings for all teams based on their preseason
    factors (recruiting, transfers, returning production). Use this at the
    start of a new season before processing any games.

    Args:
        year: Season year to reset (e.g., 2024)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.SuccessResponse: Confirmation message

    Note:
        This resets all teams' ELO ratings to their calculated preseason
        values. Any in-season rating changes will be lost.

    Example:
        POST /api/seasons/2024/reset
    """
    ranking_service = RankingService(db)
    ranking_service.reset_season(year)

    return {"message": f"Season {year} reset successfully", "data": {"year": year}}


@router.get("/api/seasons/active", tags=["Seasons"])
async def get_active_season(db: Session = Depends(get_db)):
    """
    Get the currently active season.

    Returns:
        dict: Active season data with year, current_week, is_active

    Raises:
        HTTPException: 404 if no active season found
    """
    season = db.query(Season).filter(Season.is_active == True).order_by(Season.year.desc()).first()

    if not season:
        raise HTTPException(status_code=404, detail="No active season found")

    return {"year": season.year, "current_week": season.current_week, "is_active": season.is_active}


@router.get("/api/seasons/{year}", tags=["Seasons"])
async def get_season(year: int, db: Session = Depends(get_db)):
    """
    Get a specific season by year.

    EPIC-024 Story 24.3: Expose season status for management and UI

    Args:
        year: Season year

    Returns:
        dict: Season data with year, current_week, is_active

    Raises:
        HTTPException: 404 if season not found
    """
    season = db.query(Season).filter(Season.year == year).first()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {year} not found")

    return {"year": season.year, "current_week": season.current_week, "is_active": season.is_active}


# ============================================================================
# STATS ENDPOINTS
# ============================================================================


