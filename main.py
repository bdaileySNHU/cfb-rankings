"""
FastAPI main application for College Football Ranking System
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import schemas
from database import get_db, init_db
from models import Team, Game, RankingHistory, Season, ConferenceType, APIUsage, UpdateTask
from ranking_service import RankingService

# Initialize FastAPI app
app = FastAPI(
    title="College Football Ranking API",
    description="Modified ELO ranking system for college football with recruiting, transfers, and returning production",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "College Football Ranking API",
        "version": "1.0.0"
    }


# ============================================================================
# TEAM ENDPOINTS
# ============================================================================

@app.get("/api/teams", response_model=List[schemas.Team], tags=["Teams"])
async def get_teams(
    conference: Optional[ConferenceType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all teams with optional filtering"""
    query = db.query(Team)

    if conference:
        query = query.filter(Team.conference == conference)

    teams = query.offset(skip).limit(limit).all()
    return teams


@app.get("/api/teams/{team_id}", response_model=schemas.TeamDetail, tags=["Teams"])
async def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get a specific team by ID with detailed stats"""
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get current season
    season = db.query(Season).filter(Season.is_active == True).first()
    season_year = season.year if season else datetime.now().year

    # Calculate SOS and rank
    ranking_service = RankingService(db)
    sos = ranking_service.calculate_sos(team_id, season_year)
    rankings = ranking_service.get_current_rankings(season_year)

    rank = next((r['rank'] for r in rankings if r['team_id'] == team_id), None)

    # Convert to TeamDetail schema
    team_dict = {
        "id": team.id,
        "name": team.name,
        "conference": team.conference,
        "recruiting_rank": team.recruiting_rank,
        "transfer_rank": team.transfer_rank,
        "returning_production": team.returning_production,
        "elo_rating": team.elo_rating,
        "initial_rating": team.initial_rating,
        "wins": team.wins,
        "losses": team.losses,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "sos": sos,
        "rank": rank
    }

    return team_dict


@app.post("/api/teams", response_model=schemas.Team, status_code=201, tags=["Teams"])
async def create_team(team: schemas.TeamCreate, db: Session = Depends(get_db)):
    """Create a new team"""
    # Check if team already exists
    existing = db.query(Team).filter(Team.name == team.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team already exists")

    # Create team
    db_team = Team(**team.model_dump())

    # Initialize rating
    ranking_service = RankingService(db)
    ranking_service.initialize_team_rating(db_team)

    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    return db_team


@app.put("/api/teams/{team_id}", response_model=schemas.Team, tags=["Teams"])
async def update_team(team_id: int, team_update: schemas.TeamUpdate, db: Session = Depends(get_db)):
    """Update team information"""
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Update fields
    update_data = team_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    # Recalculate rating if preseason factors changed
    if any(field in update_data for field in ['recruiting_rank', 'transfer_rank', 'returning_production']):
        ranking_service = RankingService(db)
        team.elo_rating = ranking_service.calculate_preseason_rating(team)
        team.initial_rating = team.elo_rating

    db.commit()
    db.refresh(team)

    return team


@app.get("/api/teams/{team_id}/schedule", response_model=schemas.TeamSchedule, tags=["Teams"])
async def get_team_schedule(team_id: int, season: int, db: Session = Depends(get_db)):
    """Get a team's schedule for a season"""
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get all games for this team (including FCS games)
    games = db.query(Game).filter(
        ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)) &
        (Game.season == season)
    ).order_by(Game.week).all()

    schedule_games = []
    for game in games:
        is_home = game.home_team_id == team_id
        opponent = game.away_team if is_home else game.home_team

        score_str = None
        if game.is_processed:
            if is_home:
                result = "W" if game.home_score > game.away_score else "L"
                score_str = f"{result} {game.home_score}-{game.away_score}"
            else:
                result = "W" if game.away_score > game.home_score else "L"
                score_str = f"{result} {game.away_score}-{game.home_score}"

        schedule_games.append({
            "game_id": game.id,
            "week": game.week,
            "opponent_id": opponent.id,
            "opponent_name": opponent.name,
            "opponent_conference": opponent.conference.value if opponent.conference else None,
            "is_home": is_home,
            "score": score_str,
            "is_played": game.is_processed,
            "excluded_from_rankings": game.excluded_from_rankings,
            "is_fcs": opponent.is_fcs
        })

    return {
        "team_id": team_id,
        "team_name": team.name,
        "season": season,
        "games": schedule_games
    }


# ============================================================================
# GAME ENDPOINTS
# ============================================================================

@app.get("/api/games", response_model=List[schemas.Game], tags=["Games"])
async def get_games(
    season: Optional[int] = None,
    week: Optional[int] = None,
    team_id: Optional[int] = None,
    processed: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get games with optional filtering"""
    query = db.query(Game)

    if season:
        query = query.filter(Game.season == season)
    if week is not None:
        query = query.filter(Game.week == week)
    if team_id:
        query = query.filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    if processed is not None:
        query = query.filter(Game.is_processed == processed)

    games = query.order_by(Game.week.desc(), Game.id.desc()).offset(skip).limit(limit).all()
    return games


@app.get("/api/games/{game_id}", response_model=schemas.GameDetail, tags=["Games"])
async def get_game(game_id: int, db: Session = Depends(get_db)):
    """Get a specific game with details"""
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
        "point_differential": abs(game.home_score - game.away_score)
    }


@app.post("/api/games", response_model=schemas.GameResult, status_code=201, tags=["Games"])
async def create_game(game: schemas.GameCreate, db: Session = Depends(get_db)):
    """Create a new game and process it (updates rankings immediately)"""
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
# RANKING ENDPOINTS
# ============================================================================

@app.get("/api/rankings", response_model=schemas.RankingsResponse, tags=["Rankings"])
async def get_rankings(
    season: Optional[int] = None,
    limit: Optional[int] = Query(25, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get current rankings"""
    # Get current season if not specified
    if not season:
        active_season = db.query(Season).filter(Season.is_active == True).first()
        season = active_season.year if active_season else datetime.now().year

    # Get current week
    active_season = db.query(Season).filter(Season.year == season).first()
    current_week = active_season.current_week if active_season else 0

    # Get rankings
    ranking_service = RankingService(db)
    rankings = ranking_service.get_current_rankings(season, limit=limit)

    return {
        "week": current_week,
        "season": season,
        "rankings": rankings,
        "total_teams": len(rankings)
    }


@app.get("/api/rankings/history", response_model=List[schemas.RankingHistory], tags=["Rankings"])
async def get_ranking_history(
    team_id: int,
    season: int,
    db: Session = Depends(get_db)
):
    """Get historical rankings for a specific team"""
    history = db.query(RankingHistory).filter(
        (RankingHistory.team_id == team_id) &
        (RankingHistory.season == season)
    ).order_by(RankingHistory.week).all()

    return history


@app.post("/api/rankings/save", response_model=schemas.SuccessResponse, tags=["Rankings"])
async def save_rankings(
    season: int,
    week: int,
    db: Session = Depends(get_db)
):
    """Save current rankings to history"""
    ranking_service = RankingService(db)
    ranking_service.save_weekly_rankings(season, week)

    return {
        "message": f"Rankings saved for Week {week}, {season}",
        "data": {"season": season, "week": week}
    }


# ============================================================================
# SEASON ENDPOINTS
# ============================================================================

@app.get("/api/seasons", response_model=List[schemas.SeasonResponse], tags=["Seasons"])
async def get_seasons(db: Session = Depends(get_db)):
    """Get all seasons"""
    seasons = db.query(Season).order_by(Season.year.desc()).all()
    return seasons


@app.post("/api/seasons", response_model=schemas.SeasonResponse, status_code=201, tags=["Seasons"])
async def create_season(year: int, db: Session = Depends(get_db)):
    """Create a new season"""
    existing = db.query(Season).filter(Season.year == year).first()
    if existing:
        raise HTTPException(status_code=400, detail="Season already exists")

    season = Season(year=year, current_week=0, is_active=True)
    db.add(season)
    db.commit()
    db.refresh(season)

    return season


@app.post("/api/seasons/{year}/reset", response_model=schemas.SuccessResponse, tags=["Seasons"])
async def reset_season(year: int, db: Session = Depends(get_db)):
    """Reset all teams for a new season"""
    ranking_service = RankingService(db)
    ranking_service.reset_season(year)

    return {
        "message": f"Season {year} reset successfully",
        "data": {"year": year}
    }


@app.get("/api/seasons/active", tags=["Seasons"])
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

    return {
        "year": season.year,
        "current_week": season.current_week,
        "is_active": season.is_active
    }


# ============================================================================
# STATS ENDPOINTS
# ============================================================================

@app.get("/api/stats", response_model=schemas.SystemStats, tags=["Stats"])
async def get_stats(db: Session = Depends(get_db)):
    """Get overall system statistics"""
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
        "last_updated": datetime.utcnow()
    }


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.post("/api/calculate", response_model=schemas.SuccessResponse, tags=["Utility"])
async def recalculate_rankings(season: int, db: Session = Depends(get_db)):
    """Recalculate all rankings from scratch for a season"""
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
        "data": {
            "season": season,
            "games_processed": processed_count
        }
    }


# ============================================================================
# ADMIN ENDPOINTS - API Usage Monitoring
# ============================================================================

@app.get("/api/admin/api-usage", response_model=schemas.APIUsageResponse, tags=["Admin"])
async def get_api_usage(month: Optional[str] = None):
    """
    Get CFBD API usage statistics for a specific month.

    Returns comprehensive usage stats including:
    - Total API calls for the month
    - Percentage of monthly limit used
    - Remaining calls available
    - Average calls per day
    - Warning level (if approaching limit)
    - Top 5 most-called endpoints

    Args:
        month: Optional month in YYYY-MM format (defaults to current month)

    Returns:
        APIUsageResponse with usage statistics

    Example:
        GET /api/admin/api-usage
        GET /api/admin/api-usage?month=2025-01
    """
    from cfbd_client import get_monthly_usage

    try:
        usage_stats = get_monthly_usage(month)

        return {
            **usage_stats,
            "last_updated": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve API usage stats: {str(e)}"
        )


# ============================================================================
# ADMIN ENDPOINTS - Manual Update Trigger
# ============================================================================

from fastapi import BackgroundTasks
import subprocess
import json
import sys
from pathlib import Path

# Global dictionary to track running updates (in-memory, resets on restart)
_running_updates = {}


def run_weekly_update_task(task_id: str, db_session):
    """Execute weekly update script as background task"""
    import logging
    logger = logging.getLogger(__name__)

    project_root = Path(__file__).parent
    script_path = project_root / "scripts" / "weekly_update.py"

    try:
        # Update status to running
        from models import UpdateTask
        task = db_session.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()
        if task:
            task.status = "running"
            db_session.commit()

        # Execute the script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
            cwd=str(project_root)
        )

        # Parse result
        success = result.returncode == 0
        result_data = {
            "success": success,
            "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "error_message": None if success else "Update script failed"
        }

        # Update task record
        task = db_session.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()
        if task:
            task.status = "completed" if success else "failed"
            task.completed_at = datetime.utcnow()
            task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
            task.result_json = json.dumps(result_data)
            db_session.commit()

        # Remove from running updates
        if task_id in _running_updates:
            del _running_updates[task_id]

        logger.info(f"Manual update task {task_id} completed with status: {task.status}")

    except subprocess.TimeoutExpired:
        logger.error(f"Manual update task {task_id} timed out")
        task = db_session.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()
        if task:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
            task.result_json = json.dumps({
                "success": False,
                "error_message": "Update timed out after 30 minutes"
            })
            db_session.commit()
        if task_id in _running_updates:
            del _running_updates[task_id]

    except Exception as e:
        logger.error(f"Manual update task {task_id} failed: {e}", exc_info=True)
        task = db_session.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()
        if task:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
            task.result_json = json.dumps({
                "success": False,
                "error_message": str(e)
            })
            db_session.commit()
        if task_id in _running_updates:
            del _running_updates[task_id]

    finally:
        db_session.close()


@app.post("/api/admin/trigger-update", response_model=schemas.UpdateTriggerResponse, tags=["Admin"])
async def trigger_manual_update(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Manually trigger a weekly data update.

    Performs pre-flight checks before starting:
    - Active season verification (August-January)
    - Current week detection from CFBD API
    - API usage threshold check (<90%)

    If all checks pass, executes the update in the background and returns immediately.
    Use the update-status endpoint to poll for completion.

    Returns:
        UpdateTriggerResponse with task_id for status tracking

    Raises:
        HTTPException 400: If in off-season
        HTTPException 429: If API usage >= 90%
        HTTPException 400: If no current week detected
    """
    task_id = f"update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Import pre-flight check functions
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))
    from weekly_update import is_active_season, check_api_usage, get_current_week_wrapper

    # Pre-flight check 1: Active season
    if not is_active_season():
        raise HTTPException(
            status_code=400,
            detail="Off-season (February-July) - updates not allowed during off-season"
        )

    # Pre-flight check 2: Current week detection
    try:
        current_week = get_current_week_wrapper()
        if not current_week:
            raise HTTPException(
                status_code=400,
                detail="No current week detected - season may not have started yet"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect current week: {str(e)}"
        )

    # Pre-flight check 3: API usage
    if not check_api_usage():
        usage = get_monthly_usage()
        raise HTTPException(
            status_code=429,
            detail=f"API usage at {usage['percentage_used']}% - update aborted to prevent quota exhaustion"
        )

    # Create task record
    task = UpdateTask(
        task_id=task_id,
        status="started",
        trigger_type="manual",
        started_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()

    # Track in memory
    _running_updates[task_id] = datetime.utcnow()

    # Create new session for background task (don't reuse request session)
    from database import SessionLocal
    bg_db = SessionLocal()

    # Run update in background
    background_tasks.add_task(run_weekly_update_task, task_id, bg_db)

    return {
        "status": "started",
        "message": f"Weekly update triggered manually for week {current_week}",
        "task_id": task_id,
        "started_at": task.started_at
    }


@app.get("/api/admin/update-status/{task_id}", response_model=schemas.UpdateTaskStatus, tags=["Admin"])
async def get_update_status(task_id: str, db: Session = Depends(get_db)):
    """
    Get the status of a manual update task.

    Args:
        task_id: Task ID returned from trigger-update endpoint

    Returns:
        UpdateTaskStatus with current status and result

    Raises:
        HTTPException 404: If task_id not found
    """
    task = db.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Parse result JSON if available
    result = None
    if task.result_json:
        try:
            result_data = json.loads(task.result_json)
            result = schemas.UpdateTaskResult(**result_data)
        except:
            result = None

    return schemas.UpdateTaskStatus(
        task_id=task.task_id,
        status=task.status,
        trigger_type=task.trigger_type,
        started_at=task.started_at,
        completed_at=task.completed_at,
        duration_seconds=task.duration_seconds,
        result=result
    )


@app.get("/api/admin/usage-dashboard", response_model=schemas.UsageDashboardResponse, tags=["Admin"])
async def get_usage_dashboard(month: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get comprehensive API usage dashboard data.

    Returns detailed usage statistics including:
    - Current month usage summary
    - Top 5 endpoints by call count
    - Daily usage for last 7 days
    - Projected end-of-month usage

    Args:
        month: Optional month in YYYY-MM format (defaults to current month)

    Returns:
        UsageDashboardResponse with comprehensive usage stats
    """
    from cfbd_client import get_monthly_usage
    from sqlalchemy import func
    import calendar

    if not month:
        month = datetime.now().strftime("%Y-%m")

    # Get monthly stats (from Story 001)
    monthly_stats = get_monthly_usage(month)

    # Calculate daily usage (last 7 days)
    daily_usage_data = (
        db.query(
            func.date(APIUsage.timestamp).label('date'),
            func.count(APIUsage.id).label('calls')
        )
        .filter(APIUsage.month == month)
        .group_by(func.date(APIUsage.timestamp))
        .order_by(func.date(APIUsage.timestamp).desc())
        .limit(7)
        .all()
    )

    # Reverse to get chronological order
    daily_usage = [
        schemas.DailyUsage(date=str(date), calls=calls)
        for date, calls in reversed(daily_usage_data)
    ]

    # Calculate days until reset
    year, month_num = map(int, month.split('-'))
    current_date = datetime.now()

    if year == current_date.year and month_num == current_date.month:
        days_in_month = calendar.monthrange(year, month_num)[1]
        days_until_reset = days_in_month - current_date.day
        days_elapsed = current_date.day
    else:
        days_in_month = calendar.monthrange(year, month_num)[1]
        days_until_reset = 0  # Past month
        days_elapsed = days_in_month

    # Project end-of-month usage
    avg_per_day = monthly_stats['total_calls'] / days_elapsed if days_elapsed > 0 else 0
    projected_eom = int(avg_per_day * days_in_month)

    # Build current month stats with extended fields
    current_month_stats = schemas.CurrentMonthStats(
        month=monthly_stats['month'],
        total_calls=monthly_stats['total_calls'],
        monthly_limit=monthly_stats['monthly_limit'],
        percentage_used=monthly_stats['percentage_used'],
        remaining_calls=monthly_stats['remaining_calls'],
        average_calls_per_day=monthly_stats['average_calls_per_day'],
        warning_level=monthly_stats['warning_level'],
        days_until_reset=days_until_reset,
        projected_end_of_month=projected_eom
    )

    return schemas.UsageDashboardResponse(
        current_month=current_month_stats,
        top_endpoints=[schemas.EndpointUsage(**ep) for ep in monthly_stats['top_endpoints']],
        daily_usage=daily_usage,
        last_update=datetime.utcnow()
    )


@app.get("/api/admin/config", response_model=schemas.SystemConfig, tags=["Admin"])
async def get_system_config():
    """
    Get current system configuration.

    Returns configuration values including:
    - CFBD monthly API limit
    - Update schedule
    - Warning thresholds
    - Active season dates

    Returns:
        SystemConfig with all configuration values
    """
    import os

    return schemas.SystemConfig(
        cfbd_monthly_limit=int(os.getenv("CFBD_MONTHLY_LIMIT", "1000")),
        update_schedule="Sun 20:00 ET",
        api_usage_warning_thresholds=[80, 90, 95],
        active_season_start="08-01",
        active_season_end="01-31"
    )


@app.put("/api/admin/config", response_model=schemas.SystemConfig, tags=["Admin"])
async def update_system_config(config_update: schemas.ConfigUpdate):
    """
    Update system configuration.

    Currently supports updating:
    - cfbd_monthly_limit: Monthly API call limit

    Note: Configuration changes are applied to the environment but
    require a service restart to take full effect in some cases.

    Args:
        config_update: Configuration values to update

    Returns:
        SystemConfig with updated values
    """
    import os

    # Update environment variable
    if config_update.cfbd_monthly_limit is not None:
        os.environ["CFBD_MONTHLY_LIMIT"] = str(config_update.cfbd_monthly_limit)

        # TODO: Persist to .env file for permanent change
        # For now, changes only affect current process

    # Return updated config
    return await get_system_config()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
