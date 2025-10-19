"""
Database models for College Football Ranking System
Using SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum
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

    @property
    def winner_id(self):
        """Return the ID of the winning team"""
        return self.home_team_id if self.home_score > self.away_score else self.away_team_id

    @property
    def loser_id(self):
        """Return the ID of the losing team"""
        return self.away_team_id if self.home_score > self.away_score else self.home_team_id

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
