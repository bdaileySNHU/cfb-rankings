"""
Unit tests for Database Models

Tests cover:
- Team model (defaults, relationships, constraints)
- Game model (computed properties, relationships)
- RankingHistory model (relationships)
- Season model (defaults, constraints)
- Database constraints and uniqueness
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import ConferenceType, Game, RankingHistory, Season, Team


@pytest.mark.unit
class TestTeamModel:
    """Tests for Team model"""

    def test_create_team_with_minimal_data(self, test_db: Session):
        """Test creating team with only required fields"""
        # Arrange & Act
        team = Team(
            name="Alabama",
            conference=ConferenceType.POWER_5
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Assert
        assert team.id is not None
        assert team.name == "Alabama"
        assert team.conference == ConferenceType.POWER_5

    def test_team_default_values(self, test_db: Session):
        """Test that Team model sets correct default values"""
        # Arrange & Act
        team = Team(
            name="Georgia",
            conference=ConferenceType.POWER_5
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Assert - Check all defaults
        assert team.recruiting_rank == 999, "Default recruiting rank should be 999"
        assert team.transfer_rank == 999, "Default transfer rank should be 999"
        assert team.returning_production == 0.5, "Default returning production should be 0.5"
        assert team.elo_rating == 1500.0, "Default ELO rating should be 1500.0"
        assert team.initial_rating == 1500.0, "Default initial rating should be 1500.0"
        assert team.wins == 0, "Default wins should be 0"
        assert team.losses == 0, "Default losses should be 0"

    def test_team_timestamps_auto_created(self, test_db: Session):
        """Test that created_at and updated_at are automatically set"""
        # Arrange & Act
        team = Team(name="Ohio State", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Assert
        assert team.created_at is not None, "created_at should be automatically set"
        assert team.updated_at is not None, "updated_at should be automatically set"
        assert isinstance(team.created_at, datetime)
        assert isinstance(team.updated_at, datetime)

    def test_team_custom_values_override_defaults(self, test_db: Session):
        """Test that custom values override defaults"""
        # Arrange & Act
        team = Team(
            name="Clemson",
            conference=ConferenceType.POWER_5,
            recruiting_rank=5,
            transfer_rank=10,
            returning_production=0.75,
            elo_rating=1750.0,
            initial_rating=1700.0,
            wins=8,
            losses=2
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Assert
        assert team.recruiting_rank == 5
        assert team.transfer_rank == 10
        assert team.returning_production == 0.75
        assert team.elo_rating == 1750.0
        assert team.initial_rating == 1700.0
        assert team.wins == 8
        assert team.losses == 2

    def test_team_name_must_be_unique(self, test_db: Session):
        """Test that team names must be unique"""
        # Arrange
        team1 = Team(name="Michigan", conference=ConferenceType.POWER_5)
        test_db.add(team1)
        test_db.commit()

        # Act & Assert
        team2 = Team(name="Michigan", conference=ConferenceType.GROUP_5)
        test_db.add(team2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_team_conference_types(self, test_db: Session):
        """Test all conference type enums"""
        # Arrange & Act
        p5_team = Team(name="USC", conference=ConferenceType.POWER_5)
        g5_team = Team(name="Boise State", conference=ConferenceType.GROUP_5)
        fcs_team = Team(name="North Dakota State", conference=ConferenceType.FCS)

        test_db.add_all([p5_team, g5_team, fcs_team])
        test_db.commit()

        # Assert
        assert p5_team.conference == ConferenceType.POWER_5
        assert g5_team.conference == ConferenceType.GROUP_5
        assert fcs_team.conference == ConferenceType.FCS

    def test_team_repr(self, test_db: Session):
        """Test Team string representation"""
        # Arrange
        team = Team(
            name="Texas",
            conference=ConferenceType.POWER_5,
            elo_rating=1650.5,
            wins=9,
            losses=3
        )
        test_db.add(team)
        test_db.commit()

        # Act
        repr_string = repr(team)

        # Assert
        assert "Texas" in repr_string
        assert "1650.50" in repr_string
        assert "9-3" in repr_string

    def test_team_is_fcs_default(self, test_db: Session):
        """Test that is_fcs defaults to False"""
        # Arrange & Act
        team = Team(name="FBS Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Assert
        assert team.is_fcs is False, "is_fcs should default to False"

    def test_team_is_fcs_explicit(self, test_db: Session):
        """Test that is_fcs can be set to True"""
        # Arrange & Act
        team = Team(name="FCS Team", conference=ConferenceType.FCS, is_fcs=True)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Assert
        assert team.is_fcs is True


@pytest.mark.unit
class TestGameModel:
    """Tests for Game model"""

    def test_create_game_with_required_fields(self, test_db: Session):
        """Test creating game with required fields"""
        # Arrange
        home_team = Team(name="Home", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=5,
            season=2024
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Assert
        assert game.id is not None
        assert game.home_team_id == home_team.id
        assert game.away_team_id == away_team.id
        assert game.home_score == 35
        assert game.away_score == 28
        assert game.week == 5
        assert game.season == 2024

    def test_game_default_values(self, test_db: Session):
        """Test that Game model sets correct default values"""
        # Arrange
        home_team = Team(name="Team A", conference=ConferenceType.POWER_5)
        away_team = Team(name="Team B", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=21,
            away_score=17,
            week=1,
            season=2024
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Assert
        assert game.is_neutral_site is False, "Default is_neutral_site should be False"
        assert game.is_processed is False, "Default is_processed should be False"
        assert game.home_rating_change == 0.0, "Default home_rating_change should be 0.0"
        assert game.away_rating_change == 0.0, "Default away_rating_change should be 0.0"
        assert game.created_at is not None

    def test_game_winner_id_property_home_wins(self, test_db: Session):
        """Test winner_id property when home team wins"""
        # Arrange
        home_team = Team(name="Winner Home", conference=ConferenceType.POWER_5)
        away_team = Team(name="Loser Away", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=42,
            away_score=21,
            week=1,
            season=2024
        )
        test_db.add(game)
        test_db.commit()

        # Act & Assert
        assert game.winner_id == home_team.id, "winner_id should be home_team_id when home team wins"
        assert game.loser_id == away_team.id, "loser_id should be away_team_id when home team wins"

    def test_game_winner_id_property_away_wins(self, test_db: Session):
        """Test winner_id property when away team wins"""
        # Arrange
        home_team = Team(name="Loser Home", conference=ConferenceType.POWER_5)
        away_team = Team(name="Winner Away", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=14,
            away_score=28,
            week=1,
            season=2024
        )
        test_db.add(game)
        test_db.commit()

        # Act & Assert
        assert game.winner_id == away_team.id, "winner_id should be away_team_id when away team wins"
        assert game.loser_id == home_team.id, "loser_id should be home_team_id when away team wins"

    def test_game_winner_id_tie_score(self, test_db: Session):
        """Test winner_id property with tied score"""
        # Arrange
        home_team = Team(name="Team Tie 1", conference=ConferenceType.POWER_5)
        away_team = Team(name="Team Tie 2", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=21,
            away_score=21,  # Tied
            week=1,
            season=2024
        )
        test_db.add(game)
        test_db.commit()

        # Act & Assert
        # When tied, logic defaults to away team as "winner" (not > comparison)
        assert game.winner_id == away_team.id
        assert game.loser_id == home_team.id

    def test_game_neutral_site_flag(self, test_db: Session):
        """Test neutral site flag"""
        # Arrange
        home_team = Team(name="Neutral 1", conference=ConferenceType.POWER_5)
        away_team = Team(name="Neutral 2", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=31,
            away_score=28,
            week=1,
            season=2024,
            is_neutral_site=True
        )
        test_db.add(game)
        test_db.commit()

        # Assert
        assert game.is_neutral_site is True

    def test_game_excluded_from_rankings_default(self, test_db: Session):
        """Test that excluded_from_rankings defaults to False"""
        # Arrange
        home_team = Team(name="Home", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=27,
            away_score=24,
            week=1,
            season=2025
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Assert
        assert game.excluded_from_rankings is False

    def test_game_excluded_from_rankings_explicit(self, test_db: Session):
        """Test that excluded_from_rankings can be set to True"""
        # Arrange
        fbs_team = Team(name="FBS", conference=ConferenceType.POWER_5)
        fcs_team = Team(name="FCS", conference=ConferenceType.FCS, is_fcs=True)
        test_db.add_all([fbs_team, fcs_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=fbs_team.id,
            away_team_id=fcs_team.id,
            home_score=70,
            away_score=0,
            week=2,
            season=2025,
            excluded_from_rankings=True
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Assert
        assert game.excluded_from_rankings is True


@pytest.mark.unit
class TestGameTeamRelationships:
    """Tests for relationships between Game and Team models"""

    def test_game_home_team_relationship(self, test_db: Session):
        """Test that game.home_team relationship works"""
        # Arrange
        home_team = Team(name="Home Rel Test", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Rel Test", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=24,
            away_score=21,
            week=1,
            season=2024
        )
        test_db.add(game)
        test_db.commit()

        # Act & Assert
        assert game.home_team is not None
        assert game.home_team.name == "Home Rel Test"
        assert game.home_team.id == home_team.id

    def test_game_away_team_relationship(self, test_db: Session):
        """Test that game.away_team relationship works"""
        # Arrange
        home_team = Team(name="Home Away Test", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Away Test", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=17,
            away_score=14,
            week=1,
            season=2024
        )
        test_db.add(game)
        test_db.commit()

        # Act & Assert
        assert game.away_team is not None
        assert game.away_team.name == "Away Away Test"
        assert game.away_team.id == away_team.id

    def test_team_home_games_relationship(self, test_db: Session):
        """Test that team.home_games relationship works"""
        # Arrange
        team = Team(name="Home Games Team", conference=ConferenceType.POWER_5)
        opponent1 = Team(name="Opponent 1", conference=ConferenceType.POWER_5)
        opponent2 = Team(name="Opponent 2", conference=ConferenceType.POWER_5)
        test_db.add_all([team, opponent1, opponent2])
        test_db.commit()

        game1 = Game(home_team_id=team.id, away_team_id=opponent1.id,
                    home_score=35, away_score=28, week=1, season=2024)
        game2 = Game(home_team_id=team.id, away_team_id=opponent2.id,
                    home_score=42, away_score=21, week=3, season=2024)
        test_db.add_all([game1, game2])
        test_db.commit()
        test_db.refresh(team)

        # Act & Assert
        assert len(team.home_games) == 2, "Team should have 2 home games"
        assert game1 in team.home_games
        assert game2 in team.home_games

    def test_team_away_games_relationship(self, test_db: Session):
        """Test that team.away_games relationship works"""
        # Arrange
        team = Team(name="Away Games Team", conference=ConferenceType.POWER_5)
        opponent1 = Team(name="Opp A", conference=ConferenceType.POWER_5)
        opponent2 = Team(name="Opp B", conference=ConferenceType.POWER_5)
        test_db.add_all([team, opponent1, opponent2])
        test_db.commit()

        game1 = Game(home_team_id=opponent1.id, away_team_id=team.id,
                    home_score=21, away_score=24, week=2, season=2024)
        game2 = Game(home_team_id=opponent2.id, away_team_id=team.id,
                    home_score=14, away_score=17, week=4, season=2024)
        test_db.add_all([game1, game2])
        test_db.commit()
        test_db.refresh(team)

        # Act & Assert
        assert len(team.away_games) == 2, "Team should have 2 away games"
        assert game1 in team.away_games
        assert game2 in team.away_games

    def test_team_total_games_home_and_away(self, test_db: Session):
        """Test that team has both home and away games"""
        # Arrange
        team = Team(name="Full Schedule Team", conference=ConferenceType.POWER_5)
        opp1 = Team(name="Opp 1", conference=ConferenceType.POWER_5)
        opp2 = Team(name="Opp 2", conference=ConferenceType.POWER_5)
        test_db.add_all([team, opp1, opp2])
        test_db.commit()

        # 1 home game, 1 away game
        home_game = Game(home_team_id=team.id, away_team_id=opp1.id,
                        home_score=28, away_score=24, week=1, season=2024)
        away_game = Game(home_team_id=opp2.id, away_team_id=team.id,
                        home_score=21, away_score=31, week=2, season=2024)
        test_db.add_all([home_game, away_game])
        test_db.commit()
        test_db.refresh(team)

        # Act & Assert
        total_games = len(team.home_games) + len(team.away_games)
        assert total_games == 2, "Team should have 2 total games"
        assert len(team.home_games) == 1
        assert len(team.away_games) == 1


@pytest.mark.unit
class TestRankingHistoryModel:
    """Tests for RankingHistory model"""

    def test_create_ranking_history(self, test_db: Session):
        """Test creating ranking history record"""
        # Arrange
        team = Team(name="History Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Act
        history = RankingHistory(
            team_id=team.id,
            week=5,
            season=2024,
            rank=3,
            elo_rating=1750.5,
            wins=5,
            losses=0,
            sos=1680.2,
            sos_rank=10
        )
        test_db.add(history)
        test_db.commit()
        test_db.refresh(history)

        # Assert
        assert history.id is not None
        assert history.team_id == team.id
        assert history.week == 5
        assert history.season == 2024
        assert history.rank == 3
        assert history.elo_rating == 1750.5
        assert history.wins == 5
        assert history.losses == 0
        assert history.sos == 1680.2
        assert history.sos_rank == 10

    def test_ranking_history_team_relationship(self, test_db: Session):
        """Test relationship between RankingHistory and Team"""
        # Arrange
        team = Team(name="Rank Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        history = RankingHistory(
            team_id=team.id,
            week=1,
            season=2024,
            rank=5,
            elo_rating=1650.0
        )
        test_db.add(history)
        test_db.commit()

        # Act & Assert
        assert history.team is not None
        assert history.team.name == "Rank Team"
        assert history.team.id == team.id

    def test_team_ranking_history_relationship(self, test_db: Session):
        """Test that team.ranking_history relationship works"""
        # Arrange
        team = Team(name="Season Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Create history for multiple weeks
        for week in range(1, 6):
            history = RankingHistory(
                team_id=team.id,
                week=week,
                season=2024,
                rank=week,
                elo_rating=1500.0 + (week * 10)
            )
            test_db.add(history)
        test_db.commit()
        test_db.refresh(team)

        # Act & Assert
        assert len(team.ranking_history) == 5, "Team should have 5 weeks of history"
        # Verify weeks are correct
        weeks = [h.week for h in team.ranking_history]
        assert set(weeks) == {1, 2, 3, 4, 5}

    def test_ranking_history_default_values(self, test_db: Session):
        """Test default values for RankingHistory"""
        # Arrange
        team = Team(name="Default History Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Act
        history = RankingHistory(
            team_id=team.id,
            week=1,
            season=2024,
            rank=10,
            elo_rating=1550.0
        )
        test_db.add(history)
        test_db.commit()
        test_db.refresh(history)

        # Assert
        assert history.wins == 0, "Default wins should be 0"
        assert history.losses == 0, "Default losses should be 0"
        assert history.sos == 0.0, "Default SOS should be 0.0"
        assert history.sos_rank is None, "Default sos_rank should be None"
        assert history.created_at is not None


@pytest.mark.unit
class TestSeasonModel:
    """Tests for Season model"""

    def test_create_season_with_required_fields(self, test_db: Session):
        """Test creating season with required field (year)"""
        # Arrange & Act
        season = Season(year=2024)
        test_db.add(season)
        test_db.commit()
        test_db.refresh(season)

        # Assert
        assert season.id is not None
        assert season.year == 2024

    def test_season_default_values(self, test_db: Session):
        """Test that Season model sets correct default values"""
        # Arrange & Act
        season = Season(year=2024)
        test_db.add(season)
        test_db.commit()
        test_db.refresh(season)

        # Assert
        assert season.current_week == 0, "Default current_week should be 0"
        assert season.is_active is True, "Default is_active should be True"
        assert season.created_at is not None
        assert season.updated_at is not None

    def test_season_year_must_be_unique(self, test_db: Session):
        """Test that season year must be unique"""
        # Arrange
        season1 = Season(year=2024)
        test_db.add(season1)
        test_db.commit()

        # Act & Assert
        season2 = Season(year=2024)
        test_db.add(season2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_season_custom_values(self, test_db: Session):
        """Test creating season with custom values"""
        # Arrange & Act
        season = Season(
            year=2023,
            current_week=12,
            is_active=False
        )
        test_db.add(season)
        test_db.commit()
        test_db.refresh(season)

        # Assert
        assert season.year == 2023
        assert season.current_week == 12
        assert season.is_active is False

    def test_multiple_seasons_different_years(self, test_db: Session):
        """Test creating multiple seasons with different years"""
        # Arrange & Act
        season1 = Season(year=2022, is_active=False)
        season2 = Season(year=2023, is_active=False)
        season3 = Season(year=2024, is_active=True)

        test_db.add_all([season1, season2, season3])
        test_db.commit()

        # Assert
        all_seasons = test_db.query(Season).all()
        assert len(all_seasons) == 3
        years = [s.year for s in all_seasons]
        assert set(years) == {2022, 2023, 2024}

    def test_season_repr(self, test_db: Session):
        """Test Season string representation"""
        # Arrange
        season = Season(year=2024, current_week=8, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        repr_string = repr(season)

        # Assert
        assert "2024" in repr_string
        assert "8" in repr_string
        assert "True" in repr_string


@pytest.mark.unit
class TestGameQuarterScores:
    """Tests for Game quarter score validation - EPIC-021"""

    def test_game_with_valid_quarter_scores(self, test_db: Session):
        """Test creating game with valid quarter scores"""
        # Arrange
        home_team = Team(name="Home Q1", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q1", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=21,
            week=1,
            season=2024,
            q1_home=7, q1_away=7,
            q2_home=7, q2_away=7,
            q3_home=7, q3_away=0,
            q4_home=7, q4_away=7
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Assert
        assert game.q1_home == 7
        assert game.q1_away == 7
        assert game.q2_home == 7
        assert game.q2_away == 7
        assert game.q3_home == 7
        assert game.q3_away == 0
        assert game.q4_home == 7
        assert game.q4_away == 7

        # Validation should pass
        game.validate_quarter_scores()  # Should not raise

    def test_game_with_null_quarter_scores(self, test_db: Session):
        """Test that NULL quarter scores are allowed (backward compatibility)"""
        # Arrange
        home_team = Team(name="Home Q2", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q2", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=1,
            season=2024
            # No quarter scores specified
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Assert
        assert game.q1_home is None
        assert game.q1_away is None
        assert game.q2_home is None
        assert game.q2_away is None
        assert game.q3_home is None
        assert game.q3_away is None
        assert game.q4_home is None
        assert game.q4_away is None

        # Validation should pass (NULLs bypass validation)
        game.validate_quarter_scores()  # Should not raise

    def test_game_quarter_score_validation_home_mismatch(self, test_db: Session):
        """Test that validation catches home team quarter score mismatch"""
        # Arrange
        home_team = Team(name="Home Q3", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q3", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,  # Final score
            away_score=21,
            week=1,
            season=2024,
            q1_home=7, q1_away=7,
            q2_home=7, q2_away=7,
            q3_home=7, q3_away=0,
            q4_home=14, q4_away=7  # Sum: 35 != 28 final score
        )

        # Assert
        with pytest.raises(ValueError) as excinfo:
            game.validate_quarter_scores()

        assert "Home quarter scores sum to 35, expected 28" in str(excinfo.value)

    def test_game_quarter_score_validation_away_mismatch(self, test_db: Session):
        """Test that validation catches away team quarter score mismatch"""
        # Arrange
        home_team = Team(name="Home Q4", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q4", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=21,  # Final score
            week=1,
            season=2024,
            q1_home=7, q1_away=3,
            q2_home=7, q2_away=7,
            q3_home=7, q3_away=7,
            q4_home=7, q4_away=7  # Away sum: 24 != 21 final score
        )

        # Assert
        with pytest.raises(ValueError) as excinfo:
            game.validate_quarter_scores()

        assert "Away quarter scores sum to 24, expected 21" in str(excinfo.value)

    def test_game_partial_quarter_data_bypasses_validation(self, test_db: Session):
        """Test that partial quarter data (some NULLs) bypasses validation"""
        # Arrange
        home_team = Team(name="Home Q5", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q5", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act - Only have Q1 and Q2 data, missing Q3 and Q4
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=21,
            week=1,
            season=2024,
            q1_home=7, q1_away=7,
            q2_home=7, q2_away=7,
            q3_home=None, q3_away=None,  # Missing data
            q4_home=None, q4_away=None   # Missing data
        )

        # Assert - Validation should pass (partial data bypasses validation)
        game.validate_quarter_scores()  # Should not raise

    def test_game_zero_scores_in_quarters(self, test_db: Session):
        """Test that zero scores in quarters are valid"""
        # Arrange
        home_team = Team(name="Home Q6", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q6", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act - Defensive game with 0-0 in some quarters
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=10,
            away_score=3,
            week=1,
            season=2024,
            q1_home=0, q1_away=0,  # 0-0 Q1
            q2_home=3, q2_away=3,  # 3-3 Q2
            q3_home=7, q3_away=0,  # 7-0 Q3
            q4_home=0, q4_away=0   # 0-0 Q4
        )
        test_db.add(game)
        test_db.commit()

        # Assert
        game.validate_quarter_scores()  # Should pass
        assert game.q1_home == 0
        assert game.q4_away == 0

    def test_game_high_scoring_quarters(self, test_db: Session):
        """Test game with high-scoring quarters"""
        # Arrange
        home_team = Team(name="Home Q7", conference=ConferenceType.POWER_5)
        away_team = Team(name="Away Q7", conference=ConferenceType.POWER_5)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Act - High-scoring game
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=63,
            away_score=56,
            week=1,
            season=2024,
            q1_home=21, q1_away=14,
            q2_home=14, q2_away=21,
            q3_home=14, q3_away=14,
            q4_home=14, q4_away=7
        )
        test_db.add(game)
        test_db.commit()

        # Assert
        game.validate_quarter_scores()  # Should pass
        assert sum([game.q1_home, game.q2_home, game.q3_home, game.q4_home]) == 63
        assert sum([game.q1_away, game.q2_away, game.q3_away, game.q4_away]) == 56
