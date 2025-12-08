"""
Test Data Factories using Factory Boy

These factories provide convenient test data generation for all models.
They integrate with the test database and support traits for common scenarios.

Usage:
    # Simple usage
    team = TeamFactory()
    game = GameFactory()

    # With custom attributes
    elite_team = TeamFactory(recruiting_rank=1, elo_rating=1850.0)

    # Using traits
    p5_team = TeamFactory(conference=ConferenceType.POWER_5)
    g5_team = TeamFactory(conference=ConferenceType.GROUP_5)

    # With sequences (unique names)
    team1 = TeamFactory()  # "Team 1"
    team2 = TeamFactory()  # "Team 2"
"""

from datetime import datetime, timedelta

import factory
from factory.alchemy import SQLAlchemyModelFactory

from models import ConferenceType, Game, RankingHistory, Season, Team


# Base factory that works with SQLAlchemy session
class BaseFactory(SQLAlchemyModelFactory):
    """Base factory for all model factories"""

    class Meta:
        abstract = True
        # sqlalchemy_session will be set by test fixtures
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"


class TeamFactory(BaseFactory):
    """Factory for Team model with realistic defaults"""

    class Meta:
        model = Team

    # Sequences for unique names
    name = factory.Sequence(lambda n: f"Team {n}")

    # Default to Power 5 conference
    conference = ConferenceType.POWER_5

    # Default preseason factors (mid-tier team)
    recruiting_rank = 50
    transfer_rank = 50
    returning_production = 0.60

    # Default ratings and record
    elo_rating = 1500.0
    initial_rating = 1500.0
    wins = 0
    losses = 0

    # Timestamps handled by model defaults

    class Params:
        # Trait for elite team
        elite = factory.Trait(
            recruiting_rank=5,
            transfer_rank=5,
            returning_production=0.85,
            elo_rating=1850.0,
            initial_rating=1800.0,
            wins=10,
            losses=1
        )

        # Trait for struggling team
        struggling = factory.Trait(
            recruiting_rank=100,
            transfer_rank=100,
            returning_production=0.35,
            elo_rating=1350.0,
            initial_rating=1400.0,
            wins=2,
            losses=8
        )

        # Conference-specific traits
        p5 = factory.Trait(
            conference=ConferenceType.POWER_5,
            recruiting_rank=35,
            elo_rating=1550.0
        )

        g5 = factory.Trait(
            conference=ConferenceType.GROUP_5,
            recruiting_rank=75,
            elo_rating=1450.0
        )

        fcs = factory.Trait(
            conference=ConferenceType.FCS,
            recruiting_rank=999,
            elo_rating=1300.0,
            initial_rating=1300.0
        )


class GameFactory(BaseFactory):
    """Factory for Game model with related teams"""

    class Meta:
        model = Game

    # Create related teams using SubFactory
    home_team = factory.SubFactory(TeamFactory)
    away_team = factory.SubFactory(TeamFactory)

    # Default scores (close game)
    home_score = 24
    away_score = 21

    # Default game info
    week = 1
    season = 2024
    is_neutral_site = False
    game_date = factory.LazyFunction(datetime.utcnow)

    # Default processing state
    is_processed = False
    home_rating_change = 0.0
    away_rating_change = 0.0

    class Params:
        # Trait for home blowout
        home_blowout = factory.Trait(
            home_score=42,
            away_score=14
        )

        # Trait for away upset
        away_upset = factory.Trait(
            home_score=17,
            away_score=24
        )

        # Trait for neutral site
        neutral = factory.Trait(
            is_neutral_site=True
        )

        # Trait for processed game
        processed = factory.Trait(
            is_processed=True,
            home_rating_change=15.5,
            away_rating_change=-15.5
        )


class SeasonFactory(BaseFactory):
    """Factory for Season model"""

    class Meta:
        model = Season

    # Sequence for unique years
    year = factory.Sequence(lambda n: 2020 + n)

    # Default values
    current_week = 0
    is_active = True

    class Params:
        # Trait for active mid-season
        mid_season = factory.Trait(
            current_week=6,
            is_active=True
        )

        # Trait for completed season
        completed = factory.Trait(
            current_week=15,
            is_active=False
        )


class RankingHistoryFactory(BaseFactory):
    """Factory for RankingHistory model"""

    class Meta:
        model = RankingHistory

    # Related team
    team = factory.SubFactory(TeamFactory)

    # Default week/season
    week = 1
    season = 2024

    # Default ranking data
    rank = 25
    elo_rating = 1500.0
    wins = 0
    losses = 0
    sos = 0.0
    sos_rank = None

    class Params:
        # Trait for top 5 team
        top_five = factory.Trait(
            rank=1,  # Top 5 rank (can be overridden)
            elo_rating=1850.0,
            wins=10,
            losses=0,
            sos=1750.0,
            sos_rank=5
        )

        # Trait for unranked team
        unranked = factory.Trait(
            rank=75,
            elo_rating=1400.0,
            wins=3,
            losses=7,
            sos=1500.0,
            sos_rank=50
        )


# Convenience factory combinations
class EliteTeamFactory(TeamFactory):
    """Factory for elite Power 5 team"""
    conference = ConferenceType.POWER_5
    recruiting_rank = 5
    transfer_rank = 8
    returning_production = 0.80
    elo_rating = 1850.0
    initial_rating = 1800.0
    wins = 10
    losses = 1


class G5ChampionFactory(TeamFactory):
    """Factory for strong Group of 5 team"""
    conference = ConferenceType.GROUP_5
    recruiting_rank = 60
    transfer_rank = 40
    returning_production = 0.70
    elo_rating = 1600.0
    initial_rating = 1550.0
    wins = 11
    losses = 2


class FCSTeamFactory(TeamFactory):
    """Factory for FCS team"""
    conference = ConferenceType.FCS
    recruiting_rank = 999
    transfer_rank = 999
    returning_production = 0.55
    elo_rating = 1300.0
    initial_rating = 1300.0
    wins = 0
    losses = 0


class ProcessedGameFactory(GameFactory):
    """Factory for a processed game with rating changes"""
    is_processed = True
    home_rating_change = 15.5
    away_rating_change = -15.5


class NeutralSiteGameFactory(GameFactory):
    """Factory for neutral site game"""
    is_neutral_site = True


# Helper function to set up factories with test database
def configure_factories(db_session):
    """
    Configure all factories to use the test database session.

    This should be called in test setup (e.g., in conftest.py fixture).

    Args:
        db_session: SQLAlchemy session from test_db fixture

    Example:
        @pytest.fixture
        def factories(test_db):
            configure_factories(test_db)
            return {
                'team': TeamFactory,
                'game': GameFactory,
                'season': SeasonFactory,
                'history': RankingHistoryFactory
            }
    """
    BaseFactory._meta.sqlalchemy_session = db_session

    # Set session for all factory classes
    for factory_class in [TeamFactory, GameFactory, SeasonFactory,
                          RankingHistoryFactory, EliteTeamFactory,
                          G5ChampionFactory, FCSTeamFactory,
                          ProcessedGameFactory, NeutralSiteGameFactory]:
        factory_class._meta.sqlalchemy_session = db_session
