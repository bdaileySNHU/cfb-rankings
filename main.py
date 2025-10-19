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
from models import Team, Game, RankingHistory, Season, ConferenceType
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
