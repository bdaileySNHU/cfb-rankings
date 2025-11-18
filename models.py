"""
Database models for College Football Ranking System
Using SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class ConferenceType(str, enum.Enum):
    """Conference types"""
    POWER_5 = "P5"
    GROUP_5 = "G5"
    FCS = "FCS"


class Team(Base):
    """Team model"""
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
    transfer_rank = Column(Integer, default=999)
    returning_production = Column(Float, default=0.5)

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
    """Game model"""
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
        if all([self.q1_home is not None, self.q2_home is not None,
                self.q3_home is not None, self.q4_home is not None]):
            home_sum = self.q1_home + self.q2_home + self.q3_home + self.q4_home
            if home_sum != self.home_score:
                raise ValueError(f"Home quarter scores sum to {home_sum}, expected {self.home_score}")

        # Validate away team quarters
        if all([self.q1_away is not None, self.q2_away is not None,
                self.q3_away is not None, self.q4_away is not None]):
            away_sum = self.q1_away + self.q2_away + self.q3_away + self.q4_away
            if away_sum != self.away_score:
                raise ValueError(f"Away quarter scores sum to {away_sum}, expected {self.away_score}")

    def __repr__(self):
        return f"<Game(week={self.week}, {self.home_team.name} {self.home_score} vs {self.away_team.name} {self.away_score})>"


class RankingHistory(Base):
    """Historical rankings by week"""
    __tablename__ = "ranking_history"

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
    """Season metadata"""
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
    """API usage tracking for CFBD API calls"""
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
    """Track manual and automated update tasks"""
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
    poll_type = Column(String(50), default='AP Top 25', nullable=False)
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
        Index('idx_ap_season_week', 'season', 'week'),
        Index('idx_ap_team_season', 'team_id', 'season'),
        UniqueConstraint('season', 'week', 'team_id', name='uq_ap_season_week_team'),
    )

    def __repr__(self):
        return f"<APPollRanking(season={self.season}, week={self.week}, rank=#{self.rank}, team={self.team.name if self.team else 'Unknown'})>"
