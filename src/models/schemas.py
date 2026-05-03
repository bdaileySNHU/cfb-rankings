"""Pydantic Schemas - API Request/Response Validation

This module defines all Pydantic schemas for FastAPI request validation
and response serialization. Schemas provide automatic validation, type
checking, and API documentation generation.

Schema Categories:
    - Team Schemas: Team creation, updates, and responses with preseason data
    - Game Schemas: Game records, results, and processing responses
    - Ranking Schemas: Current rankings and historical snapshots
    - Prediction Schemas: Game predictions and accuracy tracking
    - Stats Schemas: System statistics and schedules
    - Admin Schemas: API usage monitoring and update task management
    - AP Poll Schemas: Comparison analysis with AP Poll rankings

Key Features:
    - Automatic validation using Pydantic Field constraints (ge, le, max_length)
    - Type hints for IDE autocomplete and type checking
    - Field descriptions for auto-generated API documentation
    - ORM compatibility via Config.from_attributes

Example:
    Create and validate a team:
        >>> team_data = TeamCreate(
        ...     name="Georgia",
        ...     conference=ConferenceType.POWER_5,
        ...     recruiting_rank=3
        ... )
        >>> # Pydantic automatically validates types and constraints

Note:
    Field descriptions are used by FastAPI to generate OpenAPI/Swagger docs
    at /docs endpoint. Keep descriptions clear and concise.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models.models import ConferenceType


# Team Schemas
class TeamBase(BaseModel):
    """Base schema for team data with preseason factors.

    Contains core team information including conference, recruiting data,
    transfer portal metrics, and returning production. Used as the foundation
    for team creation and update operations.

    All fields have validation constraints and descriptions that appear in
    the auto-generated API documentation at /docs.
    """

    name: str = Field(..., description="Team name", max_length=100)
    conference: ConferenceType = Field(..., description="Conference type (P5, G5, FCS)")
    conference_name: Optional[str] = Field(
        None, description="Actual conference name (Big Ten, SEC, etc.)", max_length=50
    )
    recruiting_rank: Optional[int] = Field(999, description="247Sports recruiting rank", ge=1)
    transfer_rank: Optional[int] = Field(
        999, description="DEPRECATED: Use transfer_portal_rank instead", ge=1
    )
    returning_production: Optional[float] = Field(
        0.5, description="Returning production percentage", ge=0.0, le=1.0
    )

    # EPIC-026: Transfer portal metrics (calculated from player transfers)
    transfer_portal_points: Optional[int] = Field(
        0, description="Total star points from incoming transfers", ge=0
    )
    transfer_portal_rank: Optional[int] = Field(
        999, description="Transfer portal national rank (1=best, 999=N/A)", ge=1
    )
    transfer_count: Optional[int] = Field(0, description="Number of incoming transfers", ge=0)


class TeamCreate(TeamBase):
    """Schema for creating a new team"""

    pass


class TeamUpdate(BaseModel):
    """Schema for updating team information"""

    name: Optional[str] = Field(None, max_length=100)
    conference: Optional[ConferenceType] = None
    conference_name: Optional[str] = Field(None, max_length=50)
    recruiting_rank: Optional[int] = Field(None, ge=1)
    transfer_rank: Optional[int] = Field(None, ge=1)
    returning_production: Optional[float] = Field(None, ge=0.0, le=1.0)

    # EPIC-026: Transfer portal metrics
    transfer_portal_points: Optional[int] = Field(None, ge=0)
    transfer_portal_rank: Optional[int] = Field(None, ge=1)
    transfer_count: Optional[int] = Field(None, ge=0)


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
        """Pydantic config enabling ORM model attribute reading."""

        from_attributes = True


class TeamDetail(Team):
    """Detailed team response with additional stats"""

    sos: Optional[float] = Field(None, description="Strength of schedule")
    rank: Optional[int] = Field(None, description="Current ranking")


# Player Schemas
class PlayerBase(BaseModel):
    """Base schema for player data with recruiting information.

    Contains individual player recruiting data including position, star rating,
    and national ranking. Used for position group strength calculations in the
    preseason rating enhancement.

    Part of Preseason Enhancement Epic: Player Position Metrics
    """

    name: str = Field(..., description="Player full name", max_length=100)
    cfbd_athlete_id: int = Field(..., description="CollegeFootballData.com athlete ID")
    team_id: int = Field(..., description="Team ID (committed team)")
    position: str = Field(..., description="Position abbreviation (QB, OL, RB, etc.)", max_length=10)
    stars: Optional[int] = Field(None, description="Star rating 1-5", ge=1, le=5)
    rating: Optional[float] = Field(None, description="Numerical recruiting rating score")
    ranking: Optional[int] = Field(None, description="Overall national recruit ranking (1=best)", ge=1)
    recruiting_year: int = Field(..., description="Recruiting class year", ge=2000, le=2100)


class PlayerCreate(PlayerBase):
    """Schema for creating a new player record.

    Used during player data import from CollegeFootballData API.
    """

    pass


class PlayerResponse(PlayerBase):
    """Schema for player response in API endpoints.

    Includes database-generated fields (id, created_at) for complete
    player information display.
    """

    id: int
    created_at: datetime

    class Config:
        """Pydantic config enabling ORM model attribute reading."""

        from_attributes = True


class TeamPlayersResponse(BaseModel):
    """Schema for /api/teams/{id}/players endpoint response.

    Returns paginated list of players for a team with metadata including
    total count and team information.
    """

    team_id: int
    team_name: str
    total: int
    players: List[PlayerResponse]


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
    game_type: Optional[str] = Field(None, description="Game classification: 'conference_championship', 'bowl', 'playoff', or None for regular season")
    postseason_name: Optional[str] = Field(None, description="Bowl or playoff name (e.g., 'Rose Bowl Game', 'CFP Semifinal')")


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
        """Pydantic config enabling ORM model attribute reading."""

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
    conference_name: Optional[str] = None
    elo_rating: float
    wins: int
    losses: int
    sos: float
    sos_rank: Optional[int] = None

    # EPIC-026: Transfer portal metrics
    transfer_portal_rank: Optional[int] = Field(
        None, description="Transfer portal national rank (1=best, 999=N/A)"
    )
    recruiting_rank: Optional[int] = Field(None, description="247Sports recruiting rank")

    # EPIC-031 Story 31.2: Rank change and ELO trend sparkline
    rank_change: Optional[int] = Field(
        None, description="Change in rank from prior week (positive=moved up, negative=moved down, None=new entry)"
    )
    elo_history: Optional[List[float]] = Field(
        None, description="Last 8 weekly ELO values for sparkline (ascending week order)"
    )


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
        """Pydantic config enabling ORM model attribute reading."""

        from_attributes = True


# Game Processing Schemas
class GameResult(BaseModel):
    """Response schema for game processing results.

    Returns comprehensive details about ELO rating changes after a game
    is processed, including winner/loser information, rating changes,
    new ratings, expected probabilities, and margin of victory multiplier.

    Used by POST /api/games to show the immediate impact of processing
    a game through the Modified ELO algorithm.
    """

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
    game_date: Optional[str] = Field(None, description="Game date in ISO format (EPIC-GAME-DATE-SORTING)")
    opponent_id: int
    opponent_name: str
    opponent_conference: Optional[str] = None
    is_home: bool
    is_neutral_site: bool = Field(False, description="Is this a neutral site game?")
    score: Optional[str] = None  # "W 35-14" or "L 21-28" or None if not played
    is_played: bool
    excluded_from_rankings: bool = Field(
        False, description="Is this game excluded from rankings (e.g., FCS game)?"
    )
    is_fcs: bool = Field(False, description="Is the opponent an FCS team?")

    # EPIC-022: Game type classification
    game_type: Optional[str] = Field(
        None, description="Game type: NULL (regular), 'conference_championship', 'bowl', 'playoff'"
    )

    # EPIC-023: Postseason game name
    postseason_name: Optional[str] = Field(
        None, description="Bowl name or playoff round (e.g., 'Rose Bowl Game', 'CFP Semifinal')"
    )


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
        """Pydantic config enabling ORM model attribute reading."""

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
# Preseason Simulator Schemas (EPIC-032)
# ============================================================================


class PreseasonWeightsUpdate(BaseModel):
    """Request body for PUT /api/admin/preseason-weights.

    Updates the EPIC-030 regression parameters in position_weights.json.
    Only the three tunable regression params are exposed here; position
    group weights and bonus tiers are not changed via this endpoint.
    """

    previous_season_weight: float = Field(
        ..., ge=0.0, le=1.0,
        description="Blend weight for previous season ELO (0=disabled, 0.35=recommended)"
    )
    mean_regression_factor: float = Field(
        ..., ge=0.0, le=1.0,
        description="Base regression toward 1500 (0=full reset, 1=no regression)"
    )
    returning_regression_scale: float = Field(
        ..., ge=0.0, le=1.0,
        description="How much returning_production modulates the regression factor"
    )


class PreseasonWeightsResponse(BaseModel):
    """Response body for GET/PUT /api/admin/preseason-weights."""

    previous_season_weight: float
    mean_regression_factor: float
    returning_regression_scale: float


class PreseasonComponent(BaseModel):
    """Raw preseason rating components for a single team.

    Returned by GET /api/preseason/components to allow client-side
    recalculation of preseason ratings with custom weight multipliers.
    The simulator uses these to rerank teams without server round-trips.
    """

    team_id: int = Field(..., description="Team database ID")
    team_name: str = Field(..., description="Team name")
    conference: Optional[str] = Field(None, description="Conference type value")
    is_fcs: bool = Field(False, description="True if FCS team")

    # Input factors
    recruiting_rank: int = Field(999, description="247Sports recruiting rank")
    transfer_portal_rank: int = Field(999, description="Transfer portal national rank")
    returning_production: float = Field(0.5, description="Returning production percentage")

    # Bonus components (additive contributions to base_formula_rating)
    base: float = Field(..., description="Base ELO (1500 FBS / 1300 FCS)")
    recruiting_bonus: float = Field(..., description="Recruiting rank bonus (0–200)")
    transfer_bonus: float = Field(..., description="Transfer portal bonus (0–100)")
    returning_bonus: float = Field(..., description="Returning production bonus (0–40)")
    position_strength_bonus: float = Field(..., description="Position strength bonus (0–150)")

    # Previous season data (for EPIC-030 regression blend)
    prev_season_elo: Optional[float] = Field(
        None, description="Team's final ELO from previous season (None if no data)"
    )

    # Current official rating (for computing Δ in the simulator)
    current_rating: float = Field(..., description="Current official preseason ELO rating")


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
        """Pydantic config enabling ORM model attribute reading."""

        from_attributes = True


# ============================================================================
# Historical Prediction Simulation Schema
# ============================================================================


class HistoricalPrediction(BaseModel):
    """A simulated prediction for a completed historical game.

    Returned by GET /api/predictions/historical — runs the current ELO
    prediction formula against the teams' ratings as they were at game time
    (from ranking_history) and compares against the actual result.
    """

    game_id: int
    week: int
    season: int
    game_date: Optional[str] = None
    is_neutral_site: bool

    home_team_id: int
    home_team: str
    home_team_rating: float          # ELO at game time from ranking_history
    home_win_probability: float      # 0–100

    away_team_id: int
    away_team: str
    away_team_rating: float
    away_win_probability: float

    predicted_winner: str
    predicted_winner_id: int
    predicted_home_score: int
    predicted_away_score: int
    confidence: str

    # Actual result (game is already processed)
    actual_home_score: Optional[int] = None
    actual_away_score: Optional[int] = None
    actual_winner: Optional[str] = None
    actual_winner_id: Optional[int] = None
    prediction_correct: Optional[bool] = None   # None if no result recorded

    class Config:
        from_attributes = True


class HistoricalPredictionSummary(BaseModel):
    """Summary stats for a week of historical predictions."""

    season: int
    week: int
    total_games: int
    games_with_results: int
    correct_predictions: int
    accuracy_percentage: Optional[float] = None   # None if no results yet
    predictions: List[HistoricalPrediction]


# ============================================================================
# Prediction Accuracy Schemas (EPIC-009)
# ============================================================================


class PredictionAccuracyStats(BaseModel):
    """Overall prediction accuracy statistics"""

    total_predictions: int = Field(..., description="Total predictions made")
    evaluated_predictions: int = Field(
        ..., description="Predictions that have been evaluated (games completed)"
    )
    correct_predictions: int = Field(..., description="Number of correct predictions")
    accuracy_percentage: float = Field(..., description="Accuracy percentage (0-100)", ge=0, le=100)

    # Breakdown by confidence level
    high_confidence_accuracy: Optional[float] = Field(
        None, description="Accuracy for high confidence predictions"
    )
    medium_confidence_accuracy: Optional[float] = Field(
        None, description="Accuracy for medium confidence predictions"
    )
    low_confidence_accuracy: Optional[float] = Field(
        None, description="Accuracy for low confidence predictions"
    )


class TeamPredictionAccuracy(BaseModel):
    """Prediction accuracy for a specific team"""

    team_id: int
    team_name: str
    total_predictions: int = Field(..., description="Total predictions involving this team")
    evaluated_predictions: int = Field(..., description="Evaluated predictions for this team")
    correct_predictions: int = Field(..., description="Correct predictions for this team")
    accuracy_percentage: float = Field(..., description="Accuracy percentage", ge=0, le=100)
    as_favorite_accuracy: Optional[float] = Field(
        None, description="Accuracy when predicted to win"
    )
    as_underdog_accuracy: Optional[float] = Field(
        None, description="Accuracy when predicted to lose"
    )


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
        """Pydantic config enabling ORM model attribute reading."""

        from_attributes = True


# EPIC-010: AP Poll Comparison Schemas


class DisagreementDetail(BaseModel):
    """Schema for games where ELO and AP Poll disagreed"""

    game_id: int
    week: int
    game_type: Optional[str] = Field(None, description="Game type (bowl, playoff, conference_championship)")
    postseason_name: Optional[str] = Field(None, description="Postseason game name (e.g., CFP Semifinal - Rose Bowl)")
    matchup: str = Field(..., description="Game matchup (Away @ Home)")
    elo_predicted: str = Field(..., description="Team ELO predicted to win")
    ap_predicted: str = Field(..., description="Team AP Poll predicted to win")
    actual_winner: str = Field(..., description="Actual game winner")
    elo_correct: bool
    ap_correct: bool


class WeeklyComparisonStats(BaseModel):
    """Schema for weekly comparison statistics"""

    week: int
    elo_accuracy: float = Field(..., ge=0, le=1.0)
    ap_accuracy: float = Field(..., ge=0, le=1.0)
    games: int = Field(..., ge=0)
    game_type: Optional[str] = Field(None, description="Game type (bowl, playoff, conference_championship)")
    postseason_name: Optional[str] = Field(None, description="Postseason game name (e.g., CFP Semifinal - Rose Bowl)")


class ComparisonStats(BaseModel):
    """
    Schema for ELO vs AP Poll comparison statistics

    Part of EPIC-010: AP Poll Prediction Comparison
    """

    season: int
    elo_accuracy: float = Field(
        ..., description="ELO prediction accuracy vs AP Poll (0-1)", ge=0, le=1.0
    )
    ap_accuracy: float = Field(..., description="AP Poll prediction accuracy (0-1)", ge=0, le=1.0)
    elo_advantage: float = Field(..., description="ELO advantage over AP (can be negative)")
    total_games_compared: int = Field(
        ..., description="Total games with both ELO and AP predictions", ge=0
    )
    elo_correct: int = Field(
        ..., description="Games ELO predicted correctly (compared subset)", ge=0
    )
    ap_correct: int = Field(..., description="Games AP predicted correctly", ge=0)
    both_correct: int = Field(..., description="Games both systems predicted correctly", ge=0)
    elo_only_correct: int = Field(..., description="Games only ELO predicted correctly", ge=0)
    ap_only_correct: int = Field(..., description="Games only AP predicted correctly", ge=0)
    both_wrong: int = Field(..., description="Games both systems predicted incorrectly", ge=0)
    by_week: List[WeeklyComparisonStats] = Field(
        default_factory=list, description="Weekly breakdown"
    )
    disagreements: List[DisagreementDetail] = Field(
        default_factory=list, description="Games where systems disagreed"
    )
    # Overall ELO accuracy (all predictions, not just compared)
    overall_elo_accuracy: float = Field(
        ..., description="Overall ELO prediction accuracy across ALL games (0-1)", ge=0, le=1.0
    )
    overall_elo_total: int = Field(..., description="Total ELO predictions evaluated", ge=0)
    overall_elo_correct: int = Field(..., description="Total ELO predictions correct", ge=0)
    # EPIC-COMPARISON-BOWL-PLAYOFF: Postseason-specific statistics
    regular_season_elo_accuracy: float = Field(
        ..., description="ELO accuracy for regular season games (weeks 1-15)", ge=0, le=1.0
    )
    regular_season_ap_accuracy: float = Field(
        ..., description="AP Poll accuracy for regular season games (weeks 1-15)", ge=0, le=1.0
    )
    postseason_elo_accuracy: float = Field(
        ..., description="ELO accuracy for postseason games (weeks 16-20)", ge=0, le=1.0
    )
    postseason_ap_accuracy: float = Field(
        ..., description="AP Poll accuracy for postseason games (weeks 16-20)", ge=0, le=1.0
    )
    message: Optional[str] = Field(
        None, description="Optional message for empty state or error conditions"
    )
