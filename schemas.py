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
    opponent_conference: Optional[str] = None
    is_home: bool
    score: Optional[str] = None  # "W 35-14" or "L 21-28" or None if not played
    is_played: bool
    excluded_from_rankings: bool = Field(False, description="Is this game excluded from rankings (e.g., FCS game)?")
    is_fcs: bool = Field(False, description="Is the opponent an FCS team?")


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


# API Usage Schemas
class EndpointUsage(BaseModel):
    """Usage stats for a specific endpoint"""
    endpoint: str
    count: int
    percentage: Optional[float] = None


class APIUsageResponse(BaseModel):
    """Response for API usage endpoint"""
    month: str
    total_calls: int
    monthly_limit: int
    percentage_used: float
    remaining_calls: int
    average_calls_per_day: float
    warning_level: Optional[str] = None  # "80%", "90%", "95%" or null
    top_endpoints: List[EndpointUsage]
    last_updated: datetime


# ============================================================================
# Admin - Manual Update Trigger Schemas
# ============================================================================

class UpdateTriggerResponse(BaseModel):
    """Response from triggering a manual update"""
    status: str  # "started", "failed"
    message: str
    task_id: Optional[str] = None
    started_at: Optional[datetime] = None
    error_code: Optional[str] = None


class UpdateTaskResult(BaseModel):
    """Result details from an update task"""
    success: bool
    games_imported: Optional[int] = None
    teams_updated: Optional[int] = None
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class UpdateTaskStatus(BaseModel):
    """Status of an update task"""
    task_id: str
    status: str  # "started", "running", "completed", "failed"
    trigger_type: str  # "manual", "automated"
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result: Optional[UpdateTaskResult] = None


# ============================================================================
# Admin - Usage Dashboard Schemas
# ============================================================================

class DailyUsage(BaseModel):
    """Daily API usage stats"""
    date: str
    calls: int


class CurrentMonthStats(BaseModel):
    """Extended monthly stats for dashboard"""
    month: str
    total_calls: int
    monthly_limit: int
    percentage_used: float
    remaining_calls: int
    average_calls_per_day: float
    warning_level: Optional[str] = None
    days_until_reset: int
    projected_end_of_month: int


class UsageDashboardResponse(BaseModel):
    """Comprehensive usage dashboard data"""
    current_month: CurrentMonthStats
    top_endpoints: List[EndpointUsage]
    daily_usage: List[DailyUsage]
    last_update: datetime


# ============================================================================
# Admin - Configuration Schemas
# ============================================================================

class SystemConfig(BaseModel):
    """System configuration values"""
    cfbd_monthly_limit: int
    update_schedule: str
    api_usage_warning_thresholds: List[int]
    active_season_start: str
    active_season_end: str


class ConfigUpdate(BaseModel):
    """Configuration update request"""
    cfbd_monthly_limit: Optional[int] = None


# ============================================================================
# Prediction Schemas
# ============================================================================

class GamePrediction(BaseModel):
    """Schema for game prediction response"""
    game_id: int
    home_team_id: int
    home_team: str
    away_team_id: int
    away_team: str
    week: int
    season: int
    game_date: Optional[str] = None
    is_neutral_site: bool
    predicted_winner: str
    predicted_winner_id: int
    predicted_home_score: int = Field(..., ge=0, le=150)
    predicted_away_score: int = Field(..., ge=0, le=150)
    home_win_probability: float = Field(..., ge=0, le=100)
    away_win_probability: float = Field(..., ge=0, le=100)
    confidence: str = Field(..., pattern="^(High|Medium|Low)$")
    home_team_rating: float
    away_team_rating: float

    class Config:
        from_attributes = True


# ============================================================================
# Prediction Accuracy Schemas (EPIC-009)
# ============================================================================

class PredictionAccuracyStats(BaseModel):
    """Overall prediction accuracy statistics"""
    total_predictions: int = Field(..., description="Total predictions made")
    evaluated_predictions: int = Field(..., description="Predictions that have been evaluated (games completed)")
    correct_predictions: int = Field(..., description="Number of correct predictions")
    accuracy_percentage: float = Field(..., description="Accuracy percentage (0-100)", ge=0, le=100)

    # Breakdown by confidence level
    high_confidence_accuracy: Optional[float] = Field(None, description="Accuracy for high confidence predictions")
    medium_confidence_accuracy: Optional[float] = Field(None, description="Accuracy for medium confidence predictions")
    low_confidence_accuracy: Optional[float] = Field(None, description="Accuracy for low confidence predictions")


class TeamPredictionAccuracy(BaseModel):
    """Prediction accuracy for a specific team"""
    team_id: int
    team_name: str
    total_predictions: int = Field(..., description="Total predictions involving this team")
    evaluated_predictions: int = Field(..., description="Evaluated predictions for this team")
    correct_predictions: int = Field(..., description="Correct predictions for this team")
    accuracy_percentage: float = Field(..., description="Accuracy percentage", ge=0, le=100)
    as_favorite_accuracy: Optional[float] = Field(None, description="Accuracy when predicted to win")
    as_underdog_accuracy: Optional[float] = Field(None, description="Accuracy when predicted to lose")


class StoredPrediction(BaseModel):
    """Schema for a stored prediction with evaluation status"""
    id: int
    game_id: int
    predicted_winner_id: int
    predicted_winner_name: Optional[str] = None
    predicted_home_score: int
    predicted_away_score: int
    win_probability: float = Field(..., ge=0, le=1.0)
    home_elo_at_prediction: float
    away_elo_at_prediction: float
    was_correct: Optional[bool] = None
    created_at: datetime

    # Game details (optional, for enriched responses)
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    actual_home_score: Optional[int] = None
    actual_away_score: Optional[int] = None
    week: Optional[int] = None
    season: Optional[int] = None

    class Config:
        from_attributes = True
