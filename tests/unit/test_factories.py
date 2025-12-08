"""
Unit tests for Test Data Factories

Tests verify that Factory Boy factories:
- Create valid model instances
- Support customization
- Support traits
- Generate unique sequences
- Integrate with test database
"""

import sys

import pytest
from factories import (
    EliteTeamFactory,
    FCSTeamFactory,
    G5ChampionFactory,
    GameFactory,
    RankingHistoryFactory,
    SeasonFactory,
    TeamFactory,
    configure_factories,
)
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Game, RankingHistory, Season, Team


@pytest.mark.unit
class TestTeamFactory:
    """Tests for TeamFactory"""

    def test_create_basic_team(self, test_db: Session):
        """Test creating a basic team with defaults"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = TeamFactory()

        # Assert
        assert team.id is not None, "Team should be persisted to database"
        assert team.name.startswith("Team "), "Name should use sequence"
        assert team.conference == ConferenceType.POWER_5
        assert team.elo_rating == 1500.0
        assert team.wins == 0
        assert team.losses == 0

    def test_team_sequence_generates_unique_names(self, test_db: Session):
        """Test that team factory generates unique sequential names"""
        # Arrange
        configure_factories(test_db)

        # Act
        team1 = TeamFactory()
        team2 = TeamFactory()
        team3 = TeamFactory()

        # Assert
        assert team1.name != team2.name != team3.name
        assert "Team " in team1.name
        assert "Team " in team2.name
        assert "Team " in team3.name

    def test_team_custom_attributes(self, test_db: Session):
        """Test overriding default attributes"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = TeamFactory(name="Alabama", elo_rating=1850.0, wins=10, losses=2)

        # Assert
        assert team.name == "Alabama"
        assert team.elo_rating == 1850.0
        assert team.wins == 10
        assert team.losses == 2

    def test_team_elite_trait(self, test_db: Session):
        """Test elite team trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = TeamFactory(elite=True)

        # Assert
        assert team.recruiting_rank == 5
        assert team.transfer_rank == 5
        assert team.returning_production == 0.85
        assert team.elo_rating == 1850.0
        assert team.wins == 10
        assert team.losses == 1

    def test_team_struggling_trait(self, test_db: Session):
        """Test struggling team trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = TeamFactory(struggling=True)

        # Assert
        assert team.recruiting_rank == 100
        assert team.elo_rating == 1350.0
        assert team.wins == 2
        assert team.losses == 8

    def test_team_conference_traits(self, test_db: Session):
        """Test conference-specific traits"""
        # Arrange
        configure_factories(test_db)

        # Act
        p5_team = TeamFactory(p5=True)
        g5_team = TeamFactory(g5=True)
        fcs_team = TeamFactory(fcs=True)

        # Assert
        assert p5_team.conference == ConferenceType.POWER_5
        assert p5_team.elo_rating == 1550.0

        assert g5_team.conference == ConferenceType.GROUP_5
        assert g5_team.elo_rating == 1450.0

        assert fcs_team.conference == ConferenceType.FCS
        assert fcs_team.elo_rating == 1300.0


@pytest.mark.unit
class TestGameFactory:
    """Tests for GameFactory"""

    def test_create_basic_game(self, test_db: Session):
        """Test creating a basic game with defaults"""
        # Arrange
        configure_factories(test_db)

        # Act
        game = GameFactory()

        # Assert
        assert game.id is not None
        assert game.home_team is not None
        assert game.away_team is not None
        assert game.home_team.id != game.away_team.id
        assert game.home_score == 24
        assert game.away_score == 21
        assert game.week == 1
        assert game.season == 2024
        assert game.is_neutral_site is False
        assert game.is_processed is False

    def test_game_with_specific_teams(self, test_db: Session):
        """Test creating game with specific teams"""
        # Arrange
        configure_factories(test_db)
        home = TeamFactory(name="Home Team")
        away = TeamFactory(name="Away Team")

        # Act
        game = GameFactory(home_team=home, away_team=away)

        # Assert
        assert game.home_team.name == "Home Team"
        assert game.away_team.name == "Away Team"
        assert game.home_team_id == home.id
        assert game.away_team_id == away.id

    def test_game_home_blowout_trait(self, test_db: Session):
        """Test home blowout trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        game = GameFactory(home_blowout=True)

        # Assert
        assert game.home_score == 42
        assert game.away_score == 14
        assert game.home_score > game.away_score

    def test_game_away_upset_trait(self, test_db: Session):
        """Test away upset trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        game = GameFactory(away_upset=True)

        # Assert
        assert game.home_score == 17
        assert game.away_score == 24
        assert game.away_score > game.home_score

    def test_game_neutral_trait(self, test_db: Session):
        """Test neutral site trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        game = GameFactory(neutral=True)

        # Assert
        assert game.is_neutral_site is True

    def test_game_processed_trait(self, test_db: Session):
        """Test processed game trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        game = GameFactory(processed=True)

        # Assert
        assert game.is_processed is True
        assert game.home_rating_change != 0.0
        assert game.away_rating_change != 0.0


@pytest.mark.unit
class TestSeasonFactory:
    """Tests for SeasonFactory"""

    def test_create_basic_season(self, test_db: Session):
        """Test creating a basic season"""
        # Arrange
        configure_factories(test_db)

        # Act
        season = SeasonFactory()

        # Assert
        assert season.id is not None
        assert season.year >= 2020
        assert season.current_week == 0
        assert season.is_active is True

    def test_season_sequence_generates_unique_years(self, test_db: Session):
        """Test that seasons have unique sequential years"""
        # Arrange
        configure_factories(test_db)

        # Act
        season1 = SeasonFactory()
        season2 = SeasonFactory()
        season3 = SeasonFactory()

        # Assert
        assert season1.year != season2.year != season3.year
        assert season2.year == season1.year + 1
        assert season3.year == season2.year + 1

    def test_season_mid_season_trait(self, test_db: Session):
        """Test mid-season trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        season = SeasonFactory(mid_season=True)

        # Assert
        assert season.current_week == 6
        assert season.is_active is True

    def test_season_completed_trait(self, test_db: Session):
        """Test completed season trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        season = SeasonFactory(completed=True)

        # Assert
        assert season.current_week == 15
        assert season.is_active is False


@pytest.mark.unit
class TestRankingHistoryFactory:
    """Tests for RankingHistoryFactory"""

    def test_create_basic_ranking_history(self, test_db: Session):
        """Test creating basic ranking history"""
        # Arrange
        configure_factories(test_db)

        # Act
        history = RankingHistoryFactory()

        # Assert
        assert history.id is not None
        assert history.team is not None
        assert history.week == 1
        assert history.season == 2024
        assert history.rank == 25
        assert history.elo_rating == 1500.0

    def test_ranking_history_with_specific_team(self, test_db: Session):
        """Test creating history for specific team"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory(name="Georgia")

        # Act
        history = RankingHistoryFactory(team=team, week=5, rank=1)

        # Assert
        assert history.team.name == "Georgia"
        assert history.week == 5
        assert history.rank == 1

    def test_ranking_history_top_five_trait(self, test_db: Session):
        """Test top five trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        history = RankingHistoryFactory(top_five=True)

        # Assert
        assert history.rank <= 5
        assert history.elo_rating == 1850.0
        assert history.wins == 10
        assert history.losses == 0
        assert history.sos == 1750.0

    def test_ranking_history_unranked_trait(self, test_db: Session):
        """Test unranked trait"""
        # Arrange
        configure_factories(test_db)

        # Act
        history = RankingHistoryFactory(unranked=True)

        # Assert
        assert history.rank == 75
        assert history.elo_rating == 1400.0
        assert history.wins == 3
        assert history.losses == 7


@pytest.mark.unit
class TestConvenienceFactories:
    """Tests for convenience factory classes"""

    def test_elite_team_factory(self, test_db: Session):
        """Test EliteTeamFactory"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = EliteTeamFactory()

        # Assert
        assert team.conference == ConferenceType.POWER_5
        assert team.recruiting_rank == 5
        assert team.elo_rating == 1850.0
        assert team.wins == 10
        assert team.losses == 1

    def test_g5_champion_factory(self, test_db: Session):
        """Test G5ChampionFactory"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = G5ChampionFactory()

        # Assert
        assert team.conference == ConferenceType.GROUP_5
        assert team.recruiting_rank == 60
        assert team.elo_rating == 1600.0
        assert team.wins == 11
        assert team.losses == 2

    def test_fcs_team_factory(self, test_db: Session):
        """Test FCSTeamFactory"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = FCSTeamFactory()

        # Assert
        assert team.conference == ConferenceType.FCS
        assert team.recruiting_rank == 999
        assert team.elo_rating == 1300.0


@pytest.mark.unit
class TestFactoryIntegration:
    """Tests for factory integration with database"""

    def test_factories_persist_to_database(self, test_db: Session):
        """Test that factory-created objects persist to database"""
        # Arrange
        configure_factories(test_db)

        # Act
        team = TeamFactory()
        test_db.flush()

        # Query fresh from DB
        fresh_team = test_db.query(Team).filter(Team.id == team.id).first()

        # Assert
        assert fresh_team is not None
        assert fresh_team.name == team.name

    def test_factory_relationships_work(self, test_db: Session):
        """Test that factory-created relationships work"""
        # Arrange
        configure_factories(test_db)

        # Act
        game = GameFactory()
        test_db.flush()

        # Assert
        assert game.home_team.home_games[0] == game
        assert game.away_team.away_games[0] == game

    def test_multiple_factories_in_single_test(self, test_db: Session):
        """Test using multiple factories together"""
        # Arrange
        configure_factories(test_db)

        # Act
        season = SeasonFactory(year=2024)
        team1 = EliteTeamFactory(name="Alabama")
        team2 = EliteTeamFactory(name="Georgia")
        game = GameFactory(home_team=team1, away_team=team2, season=season.year, week=5)
        history = RankingHistoryFactory(team=team1, season=season.year, week=5)

        # Assert
        assert game.season == season.year
        assert history.team.name == "Alabama"
        assert game.home_team.name == "Alabama"
        assert game.away_team.name == "Georgia"
