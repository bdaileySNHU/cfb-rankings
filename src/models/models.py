"""Database Models - College Football Ranking System

This module defines all SQLAlchemy ORM models for the ranking system,
including teams, games, rankings, predictions, and metadata tracking.

The database schema supports:
    - Team data with preseason factors (recruiting, transfers, returning production)
    - Game records with quarter-by-quarter scoring and postseason classification
    - Weekly ranking snapshots for historical tracking
    - Prediction storage and accuracy tracking
    - API usage monitoring and update task management
    - AP Poll integration for comparison analysis

Models:
    Team: College football team with ELO rating and preseason factors
    Game: Individual game with scores, quarter data, and processing status
    RankingHistory: Weekly ranking snapshots for historical analysis
    Season: Season metadata with current week tracking
    APIUsage: CFBD API call tracking for quota management
    UpdateTask: Manual and automated update task tracking
    Prediction: Stored game predictions for accuracy analysis
    APPollRanking: AP Poll rankings for comparison with ELO

Example:
    Create a team and initialize rating:
        >>> team = Team(name="Georgia", conference=ConferenceType.POWER_5,
        ...             recruiting_rank=3, returning_production=0.85)
        >>> session.add(team)
        >>> session.commit()
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ConferenceType(str, enum.Enum):
    """Conference classification for college football teams.

    Defines the three major tiers of college football conferences used
    for ELO calculations and matchup multipliers:

    Attributes:
        POWER_5: Power 5 conferences (SEC, Big Ten, Big 12, ACC, Pac-12)
        GROUP_5: Group of 5 conferences (AAC, C-USA, MAC, MWC, Sun Belt)
        FCS: Football Championship Subdivision (lower division)

    Note:
        Conference tier affects base ELO rating and cross-tier matchup
        multipliers. FCS teams start at 1300 ELO vs 1500 for FBS teams.
    """

    POWER_5 = "P5"
    GROUP_5 = "G5"
    FCS = "FCS"


class Team(Base):
    """SQLAlchemy ORM model representing a college football team.

    Stores team information including name, conference, preseason metrics,
    and current ELO rating. Preseason factors (recruiting, transfers, returning
    production) are used to calculate initial ratings at season start.

    Attributes:
        id: Unique team identifier (primary key)
        name: Official team name (e.g., "Georgia", "Ohio State")
        conference: Conference tier (P5, G5, or FCS)
        conference_name: Actual conference name (e.g., "SEC", "Big Ten")
        is_fcs: Boolean flag indicating FCS division
        recruiting_rank: 247Sports recruiting class rank (1-133)
        transfer_rank: DEPRECATED - Legacy transfer rank field
        returning_production: Percentage of returning production (0.0-1.0)
        transfer_portal_points: Total star points from incoming transfers
        transfer_portal_rank: National transfer portal rank (1=best)
        transfer_count: Number of incoming transfer players
        elo_rating: Current Modified ELO rating
        initial_rating: Preseason ELO rating (before any games)
        wins: Cumulative win count (all seasons)
        losses: Cumulative loss count (all seasons)
        created_at: Record creation timestamp
        updated_at: Last modification timestamp

    Relationships:
        home_games: Games where this team is the home team
        away_games: Games where this team is the away team
        ranking_history: Historical ranking snapshots by week

    Example:
        >>> team = Team(name="Georgia", conference=ConferenceType.POWER_5,
        ...             recruiting_rank=3, transfer_portal_rank=5,
        ...             returning_production=0.85)
        >>> team.elo_rating = 1850.0
        >>> db.add(team)
        >>> db.commit()
    """

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    conference = Column(Enum(ConferenceType), nullable=False)

    # EPIC-012: Actual conference name (Big Ten, SEC, etc.)
    conference_name = Column(String(50), nullable=True)

    # FCS flag
    is_fcs = Column(Boolean, default=False, nullable=False)

    # Preseason factors
    recruiting_rank = Column(Integer, default=999)
    transfer_rank = Column(Integer, default=999)  # DEPRECATED: Use transfer_portal_rank instead
    returning_production = Column(Float, default=0.5)

    # EPIC-026: Transfer portal metrics (calculated from player transfers)
    transfer_portal_points = Column(Integer, default=0)  # Total star points from transfers
    transfer_portal_rank = Column(Integer, default=999)  # National rank (1 = best)
    transfer_count = Column(Integer, default=0)  # Number of incoming transfers

    # Current season stats
    elo_rating = Column(Float, default=1500.0)
    initial_rating = Column(Float, default=1500.0)  # Store preseason rating
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")
    ranking_history = relationship("RankingHistory", back_populates="team")

    def __repr__(self):
        return f"<Team(name='{self.name}', rating={self.elo_rating:.2f}, record={self.wins}-{self.losses})>"


class Game(Base):
    """SQLAlchemy ORM model representing a college football game.

    Stores comprehensive game information including teams, scores, quarter-by-
    quarter data, game metadata, and ELO rating changes from processing.

    Supports regular season, conference championship, bowl, and playoff games
    with optional quarter-level scoring for garbage time detection.

    Attributes:
        id: Unique game identifier (primary key)
        home_team_id: Foreign key to home team
        away_team_id: Foreign key to away team
        home_score: Final home team score
        away_score: Final away team score
        q1_home, q2_home, q3_home, q4_home: Quarter scores for home team
        q1_away, q2_away, q3_away, q4_away: Quarter scores for away team
        week: Week number (0=preseason, 1-15=regular/postseason)
        season: Season year (e.g., 2024)
        is_neutral_site: Boolean indicating neutral site game
        game_date: Date and time of game
        game_type: Game classification ('conference_championship', 'bowl', 'playoff', or None)
        postseason_name: Bowl/playoff name (e.g., "Rose Bowl Game", "CFP Semifinal")
        is_processed: Boolean indicating if ELO has been updated
        excluded_from_rankings: Boolean to exclude FCS or exhibition games
        home_rating_change: ELO points gained/lost by home team
        away_rating_change: ELO points gained/lost by away team
        created_at: Record creation timestamp

    Relationships:
        home_team: Team object for home team
        away_team: Team object for away team
        prediction: Associated prediction (if exists)

    Properties:
        winner_id: ID of winning team
        loser_id: ID of losing team

    Example:
        >>> game = Game(home_team_id=1, away_team_id=2,
        ...             home_score=35, away_score=28,
        ...             week=5, season=2024, is_neutral_site=False)
        >>> db.add(game)
        >>> db.commit()
    """

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)

    # Teams
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    # Scores
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)

    # Quarter-by-quarter scores (nullable for backward compatibility)
    q1_home = Column(Integer, nullable=True)
    q1_away = Column(Integer, nullable=True)
    q2_home = Column(Integer, nullable=True)
    q2_away = Column(Integer, nullable=True)
    q3_home = Column(Integer, nullable=True)
    q3_away = Column(Integer, nullable=True)
    q4_home = Column(Integer, nullable=True)
    q4_away = Column(Integer, nullable=True)

    # Game info
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    is_neutral_site = Column(Boolean, default=False)
    game_date = Column(DateTime, nullable=True)

    # EPIC-022: Game type classification
    # NULL = regular season (default for backward compatibility)
    # 'conference_championship' = conference championship game
    # 'bowl' = bowl game (EPIC-023)
    # 'playoff' = playoff game (EPIC-023)
    game_type = Column(String(50), nullable=True)

    # EPIC-023: Postseason game name
    # NULL = regular season or unnamed game
    # Bowl games: "Rose Bowl Game", "Sugar Bowl", etc.
    # Playoff games: "CFP Semifinal", "CFP Championship", etc.
    postseason_name = Column(String(100), nullable=True)

    # Game processed flag
    is_processed = Column(Boolean, default=False)

    # FCS exclusion flag
    # Purpose: Mark FCS games or other non-ranked matchups
    # Default False: FBS games are included in rankings
    # Indexed: Performance for filtered queries
    excluded_from_rankings = Column(Boolean, default=False, nullable=False, index=True)

    # ELO changes from this game
    home_rating_change = Column(Float, default=0.0)
    away_rating_change = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    prediction = relationship("Prediction", uselist=False, back_populates="game")

    @property
    def winner_id(self):
        """Return the ID of the winning team"""
        return self.home_team_id if self.home_score > self.away_score else self.away_team_id

    @property
    def loser_id(self):
        """Return the ID of the losing team"""
        return self.away_team_id if self.home_score > self.away_score else self.home_team_id

    def validate_quarter_scores(self):
        """
        Validate quarter scores sum to final scores if provided.

        Raises:
            ValueError: If quarter scores don't sum to final scores
        """
        # Validate home team quarters
        if all(
            [
                self.q1_home is not None,
                self.q2_home is not None,
                self.q3_home is not None,
                self.q4_home is not None,
            ]
        ):
            home_sum = self.q1_home + self.q2_home + self.q3_home + self.q4_home
            if home_sum != self.home_score:
                raise ValueError(
                    f"Home quarter scores sum to {home_sum}, expected {self.home_score}"
                )

        # Validate away team quarters
        if all(
            [
                self.q1_away is not None,
                self.q2_away is not None,
                self.q3_away is not None,
                self.q4_away is not None,
            ]
        ):
            away_sum = self.q1_away + self.q2_away + self.q3_away + self.q4_away
            if away_sum != self.away_score:
                raise ValueError(
                    f"Away quarter scores sum to {away_sum}, expected {self.away_score}"
                )

    def __repr__(self):
        return f"<Game(week={self.week}, {self.home_team.name} {self.home_score} vs {self.away_team.name} {self.away_score})>"


class RankingHistory(Base):
    """SQLAlchemy ORM model for weekly ranking snapshots.

    Stores historical rankings for each team at each week, enabling
    week-by-week tracking of ELO ratings, win/loss records, and strength
    of schedule over time. Used for ranking charts and historical analysis.

    Attributes:
        id: Unique record identifier (primary key)
        team_id: Foreign key to team
        week: Week number (0-15)
        season: Season year (e.g., 2024)
        rank: National rank for this team this week (1=best)
        elo_rating: ELO rating snapshot at this week
        wins: Season wins through this week
        losses: Season losses through this week
        sos: Strength of schedule (average opponent ELO)
        sos_rank: National SOS rank (1=hardest schedule)
        created_at: Record creation timestamp

    Relationships:
        team: Team object for this ranking

    Note:
        Unique constraint on (team_id, season, week) prevents duplicate entries.

    Example:
        >>> history = RankingHistory(team_id=1, week=5, season=2024,
        ...                          rank=3, elo_rating=1850.5,
        ...                          wins=4, losses=1, sos=1650.2)
        >>> db.add(history)
        >>> db.commit()
    """

    __tablename__ = "ranking_history"
    __table_args__ = (
        # EPIC-024 FIX: Prevent duplicate entries for same team/season/week
        Index("idx_ranking_history_unique", "team_id", "season", "week", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)

    # Rankings
    rank = Column(Integer, nullable=False)
    elo_rating = Column(Float, nullable=False)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # Strength of Schedule
    sos = Column(Float, default=0.0)
    sos_rank = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="ranking_history")

    def __repr__(self):
        return f"<RankingHistory(week={self.week}, rank={self.rank}, team={self.team.name}, rating={self.elo_rating:.2f})>"


class Season(Base):
    """SQLAlchemy ORM model for season metadata and current week tracking.

    Stores configuration and state for each football season, including
    the current week number and active status. Used by the weekly update
    system to track progress through the season.

    Attributes:
        id: Unique record identifier (primary key)
        year: Season year (e.g., 2024) - unique constraint
        current_week: Current week number (0-15)
        is_active: Boolean indicating if this is the active season
        created_at: Record creation timestamp
        updated_at: Last modification timestamp

    Note:
        Only one season should have is_active=True at a time. Week 0
        indicates preseason, weeks 1-14 are regular season, week 15+ is
        postseason/playoffs.

    Example:
        >>> season = Season(year=2024, current_week=5, is_active=True)
        >>> db.add(season)
        >>> db.commit()
    """

    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, unique=True, nullable=False)
    current_week = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Season(year={self.year}, week={self.current_week}, active={self.is_active})>"


class APIUsage(Base):
    """SQLAlchemy ORM model for tracking CFBD API call usage.

    Records every API call made to the College Football Data API for
    quota monitoring and usage analysis. Enables monthly usage tracking
    to prevent exceeding the API limit.

    Attributes:
        id: Unique record identifier (primary key)
        endpoint: API endpoint called (e.g., "/games")
        timestamp: Date and time of API call (indexed)
        status_code: HTTP status code returned
        response_time_ms: Response time in milliseconds
        month: Month of call in YYYY-MM format (indexed for aggregation)
        created_at: Record creation timestamp

    Note:
        The month field is indexed for fast monthly usage queries.
        Default CFBD API limit is 1000 calls/month.

    Example:
        >>> usage = APIUsage(endpoint="/games", status_code=200,
        ...                  response_time_ms=250.5, month="2024-09")
        >>> db.add(usage)
        >>> db.commit()
    """

    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, default=0.0)
    month = Column(String(7), index=True, nullable=False)  # YYYY-MM format
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<APIUsage(endpoint='{self.endpoint}', status={self.status_code}, month='{self.month}')>"


class UpdateTask(Base):
    """SQLAlchemy ORM model for tracking weekly update task execution.

    Records status and results of manual and automated weekly update tasks
    that fetch new game data from CFBD API and update rankings. Used for
    monitoring update success and debugging failures.

    Attributes:
        id: Unique record identifier (primary key)
        task_id: Unique task identifier string (e.g., "update-20240915-120000")
        status: Task status ("started", "running", "completed", "failed")
        trigger_type: How task was initiated ("manual" or "automated")
        started_at: Task start timestamp
        completed_at: Task completion timestamp (None if still running)
        duration_seconds: Total execution time in seconds
        result_json: JSON string containing task result details
        created_at: Record creation timestamp
        updated_at: Last modification timestamp

    Note:
        The task_id field is unique and indexed for fast status lookups.
        result_json contains stdout/stderr and error messages for debugging.

    Example:
        >>> task = UpdateTask(task_id="update-20240915-120000",
        ...                   status="started", trigger_type="manual",
        ...                   started_at=datetime.utcnow())
        >>> db.add(task)
        >>> db.commit()
    """

    __tablename__ = "update_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False)  # started, running, completed, failed
    trigger_type = Column(String(20), nullable=False)  # manual, automated
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    result_json = Column(String(2000), nullable=True)  # JSON string of result
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UpdateTask(task_id='{self.task_id}', status='{self.status}', trigger_type='{self.trigger_type}')>"


class Prediction(Base):
    """
    Game predictions stored before games are played.

    Used to track prediction accuracy by storing pre-game predictions
    and comparing them to actual results after games complete.

    Part of EPIC-009: Prediction Accuracy Tracking
    """

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    # Game reference (unique - one prediction per game)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, unique=True, index=True)

    # Prediction details
    predicted_winner_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    predicted_home_score = Column(Integer, nullable=False)
    predicted_away_score = Column(Integer, nullable=False)
    win_probability = Column(Float, nullable=False)  # Probability for predicted winner (0.0-1.0)

    # ELO ratings at time of prediction (snapshot for analysis)
    home_elo_at_prediction = Column(Float, nullable=False)
    away_elo_at_prediction = Column(Float, nullable=False)

    # Accuracy evaluation (set after game completes)
    was_correct = Column(Boolean, nullable=True, index=True)  # None until game completes

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    game = relationship("Game", foreign_keys=[game_id])
    predicted_winner = relationship("Team", foreign_keys=[predicted_winner_id])

    @property
    def predicted_margin(self):
        """Return predicted margin of victory"""
        return abs(self.predicted_home_score - self.predicted_away_score)

    def __repr__(self):
        correct_str = "✓" if self.was_correct else "✗" if self.was_correct is False else "?"
        return f"<Prediction(game_id={self.game_id}, winner={self.predicted_winner.name if self.predicted_winner else 'Unknown'}, prob={self.win_probability:.1%}, correct={correct_str})>"


class APPollRanking(Base):
    """
    AP Poll rankings stored weekly for comparison with ELO predictions.

    Used to generate AP-implied predictions (higher ranked team should win)
    and compare AP prediction accuracy against ELO prediction accuracy.

    Part of EPIC-010: AP Poll Prediction Comparison
    """

    __tablename__ = "ap_poll_rankings"

    id = Column(Integer, primary_key=True, index=True)

    # Week/Season reference
    season = Column(Integer, nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)

    # Poll metadata
    poll_type = Column(String(50), default="AP Top 25", nullable=False)
    rank = Column(Integer, nullable=False)

    # Team reference
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    # Ranking details
    first_place_votes = Column(Integer, default=0)
    points = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", foreign_keys=[team_id])

    # Unique constraint: one rank per team per week per season
    __table_args__ = (
        Index("idx_ap_season_week", "season", "week"),
        Index("idx_ap_team_season", "team_id", "season"),
        UniqueConstraint("season", "week", "team_id", name="uq_ap_season_week_team"),
    )

    def __repr__(self):
        return f"<APPollRanking(season={self.season}, week={self.week}, rank=#{self.rank}, team={self.team.name if self.team else 'Unknown'})>"
