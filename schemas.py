"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models import ConferenceType


# Team Schemas
class TeamBase(BaseModel):
    """Base team schema"""
    name: str = Field(..., description="Team name", max_length=100)
    conference: ConferenceType = Field(..., description="Conference type (P5, G5, FCS)")
    recruiting_rank: Optional[int] = Field(999, description="247Sports recruiting rank", ge=1)
    transfer_rank: Optional[int] = Field(999, description="247Sports transfer portal rank", ge=1)
    returning_production: Optional[float] = Field(0.5, description="Returning production percentage", ge=0.0, le=1.0)


class TeamCreate(TeamBase):
    """Schema for creating a new team"""
    pass


class TeamUpdate(BaseModel):
    """Schema for updating team information"""
    name: Optional[str] = Field(None, max_length=100)
    conference: Optional[ConferenceType] = None
    recruiting_rank: Optional[int] = Field(None, ge=1)
    transfer_rank: Optional[int] = Field(None, ge=1)
    returning_production: Optional[float] = Field(None, ge=0.0, le=1.0)


class Team(TeamBase):
    """Schema for team response"""
    id: int
    elo_rating: float
    initial_rating: float
    wins: int
    losses: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamDetail(Team):
    """Detailed team response with additional stats"""
    sos: Optional[float] = Field(None, description="Strength of schedule")
    rank: Optional[int] = Field(None, description="Current ranking")


# Game Schemas
class GameBase(BaseModel):
    """Base game schema"""
    home_team_id: int = Field(..., description="Home team ID")
    away_team_id: int = Field(..., description="Away team ID")
    home_score: int = Field(..., description="Home team score", ge=0)
    away_score: int = Field(..., description="Away team score", ge=0)
    week: int = Field(..., description="Week number", ge=0, le=20)
    season: int = Field(..., description="Season year", ge=2000, le=2100)
    is_neutral_site: bool = Field(False, description="Is this a neutral site game?")
    game_date: Optional[datetime] = Field(None, description="Game date and time")


class GameCreate(GameBase):
    """Schema for creating a new game"""
    pass


class Game(GameBase):
    """Schema for game response"""
    id: int
    is_processed: bool
    home_rating_change: float
    away_rating_change: float
    created_at: datetime

    class Config:
        from_attributes = True


class GameDetail(Game):
    """Detailed game response with team names"""
    home_team_name: str
    away_team_name: str
    winner_name: str
    loser_name: str
    point_differential: int


# Ranking Schemas
class RankingEntry(BaseModel):
    """Single ranking entry"""
    rank: int
    team_id: int
    team_name: str
    conference: ConferenceType
    elo_rating: float
    wins: int
    losses: int
    sos: float
    sos_rank: Optional[int] = None


class RankingsResponse(BaseModel):
    """Response for rankings endpoint"""
    week: int
    season: int
    rankings: List[RankingEntry]
    total_teams: int


class RankingHistory(BaseModel):
    """Historical ranking for a team"""
    week: int
    season: int
    rank: int
    elo_rating: float
    wins: int
    losses: int
    sos: float

    class Config:
        from_attributes = True


# Game Processing Schemas
class GameResult(BaseModel):
    """Result of processing a game"""
    game_id: int
    winner_name: str
    loser_name: str
    score: str
    winner_rating_change: float
    loser_rating_change: float
    winner_new_rating: float
    loser_new_rating: float
    winner_expected_probability: float
    mov_multiplier: float


# Stats Schemas
class SystemStats(BaseModel):
    """Overall system statistics"""
    total_teams: int
    total_games: int
    total_games_processed: int
    current_season: int
    current_week: int
    last_updated: datetime


# Schedule Schemas
class ScheduleGame(BaseModel):
    """Game in a team's schedule"""
    game_id: int
    week: int
    opponent_id: int
    opponent_name: str
    is_home: bool
    score: Optional[str] = None  # "W 35-14" or "L 21-28" or None if not played
    is_played: bool


class TeamSchedule(BaseModel):
    """Team's full schedule"""
    team_id: int
    team_name: str
    season: int
    games: List[ScheduleGame]


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None


# Success Response
class SuccessResponse(BaseModel):
    """Generic success response"""
    message: str
    data: Optional[dict] = None


# Season Schemas
class SeasonResponse(BaseModel):
    """Season response schema"""
    id: int
    year: int
    current_week: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
