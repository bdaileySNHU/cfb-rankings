"""
Unit tests for FCS Game Exclusion from Rankings (Story 007)

Tests cover:
- Excluded games don't affect ELO ratings
- Excluded games don't affect team W-L records
- Excluded games don't affect SOS calculations
- RankingService explicitly rejects processing excluded games
"""

import sys

import pytest
from factories import GameFactory, TeamFactory, configure_factories
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Game, Team
from src.core.ranking_service import RankingService


@pytest.mark.unit
class TestExcludedGameRankingProtection:
    """Tests that excluded games cannot affect rankings"""

    def test_process_game_raises_error_for_excluded_game(self, test_db: Session):
        """Test that processing an excluded game raises ValueError"""
        # Arrange
        configure_factories(test_db)
        fbs_team = TeamFactory(elo_rating=1600.0)
        fcs_team = TeamFactory(elo_rating=1200.0, is_fcs=True)

        # Create excluded game (FCS matchup)
        game = GameFactory(
            home_team=fbs_team,
            away_team=fcs_team,
            home_score=70,
            away_score=0,
            excluded_from_rankings=True,
            is_processed=False,
        )

        ranking_service = RankingService(test_db)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot process excluded game for rankings"):
            ranking_service.process_game(game)

    def test_excluded_game_does_not_affect_elo_ratings(self, test_db: Session):
        """Test that excluded games don't change ELO ratings"""
        # Arrange
        configure_factories(test_db)
        fbs_team = TeamFactory(elo_rating=1500.0)
        fcs_team = TeamFactory(elo_rating=1400.0, is_fcs=True)

        # Record initial ratings
        initial_fbs_rating = fbs_team.elo_rating
        initial_fcs_rating = fcs_team.elo_rating

        # Create excluded game
        game = GameFactory(
            home_team=fbs_team,
            away_team=fcs_team,
            home_score=70,
            away_score=0,
            excluded_from_rankings=True,
            is_processed=False,
        )

        # Attempt to process (should raise error)
        ranking_service = RankingService(test_db)
        try:
            ranking_service.process_game(game)
        except ValueError:
            pass  # Expected error

        # Refresh from DB
        test_db.refresh(fbs_team)
        test_db.refresh(fcs_team)

        # Assert - Ratings should be unchanged
        assert fbs_team.elo_rating == initial_fbs_rating
        assert fcs_team.elo_rating == initial_fcs_rating

    def test_excluded_game_does_not_affect_team_records(self, test_db: Session):
        """Test that excluded games don't affect team W-L records"""
        # Arrange
        configure_factories(test_db)
        fbs_team = TeamFactory(wins=0, losses=0)
        fcs_team = TeamFactory(wins=0, losses=0, is_fcs=True)

        # Create excluded game (FBS wins)
        game = GameFactory(
            home_team=fbs_team,
            away_team=fcs_team,
            home_score=70,
            away_score=0,
            excluded_from_rankings=True,
            is_processed=False,
        )

        # Attempt to process
        ranking_service = RankingService(test_db)
        try:
            ranking_service.process_game(game)
        except ValueError:
            pass  # Expected

        # Refresh from DB
        test_db.refresh(fbs_team)
        test_db.refresh(fcs_team)

        # Assert - Records should be unchanged
        assert fbs_team.wins == 0
        assert fbs_team.losses == 0
        assert fcs_team.wins == 0
        assert fcs_team.losses == 0


@pytest.mark.unit
class TestSOSCalculationWithExcludedGames:
    """Tests that SOS calculation excludes FCS games"""

    def test_sos_excludes_fcs_games(self, test_db: Session):
        """Test that SOS only considers non-excluded games"""
        # Arrange: Team A plays 2 FBS opponents and 1 FCS opponent
        configure_factories(test_db)
        team_a = TeamFactory(name="Team A", elo_rating=1600.0)
        fbs_opp_1 = TeamFactory(name="FBS Opp 1", elo_rating=1700.0)
        fbs_opp_2 = TeamFactory(name="FBS Opp 2", elo_rating=1550.0)
        fcs_opp = TeamFactory(name="FCS Opp", elo_rating=1200.0, is_fcs=True)

        # FBS games (included in rankings)
        game1 = GameFactory(
            home_team=team_a,
            away_team=fbs_opp_1,
            home_score=24,
            away_score=27,
            excluded_from_rankings=False,
            is_processed=True,
            season=2025,
        )
        game2 = GameFactory(
            home_team=team_a,
            away_team=fbs_opp_2,
            home_score=35,
            away_score=28,
            excluded_from_rankings=False,
            is_processed=True,
            season=2025,
        )

        # FCS game (excluded from rankings)
        game3 = GameFactory(
            home_team=team_a,
            away_team=fcs_opp,
            home_score=70,
            away_score=0,
            excluded_from_rankings=True,
            is_processed=False,  # Not processed
            season=2025,
        )

        # Act
        ranking_service = RankingService(test_db)
        sos = ranking_service.calculate_sos(team_a.id, 2025)

        # Assert
        # SOS should average only FBS opponents: (1700 + 1550) / 2 = 1625
        # Should NOT include FCS opponent (1200)
        expected_sos = (1700.0 + 1550.0) / 2
        assert sos == pytest.approx(expected_sos, abs=0.1)

    def test_sos_with_only_excluded_games(self, test_db: Session):
        """Test SOS when team only played excluded games"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory(elo_rating=1600.0)
        fcs_opp_1 = TeamFactory(elo_rating=1200.0, is_fcs=True)
        fcs_opp_2 = TeamFactory(elo_rating=1150.0, is_fcs=True)

        # Only FCS games (all excluded)
        GameFactory(
            home_team=team,
            away_team=fcs_opp_1,
            excluded_from_rankings=True,
            is_processed=False,
            season=2025,
        )
        GameFactory(
            home_team=team,
            away_team=fcs_opp_2,
            excluded_from_rankings=True,
            is_processed=False,
            season=2025,
        )

        # Act
        ranking_service = RankingService(test_db)
        sos = ranking_service.calculate_sos(team.id, 2025)

        # Assert - SOS should be 0.0 (no valid opponents)
        assert sos == 0.0

    def test_sos_with_mixed_games(self, test_db: Session):
        """Test SOS calculation with mix of FBS and FCS games"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory(elo_rating=1650.0)

        # 3 FBS opponents (included)
        fbs_1 = TeamFactory(elo_rating=1800.0)
        fbs_2 = TeamFactory(elo_rating=1600.0)
        fbs_3 = TeamFactory(elo_rating=1750.0)

        # 2 FCS opponents (excluded)
        fcs_1 = TeamFactory(elo_rating=1100.0, is_fcs=True)
        fcs_2 = TeamFactory(elo_rating=1250.0, is_fcs=True)

        # Create games
        for opp in [fbs_1, fbs_2, fbs_3]:
            GameFactory(
                home_team=team,
                away_team=opp,
                excluded_from_rankings=False,
                is_processed=True,
                season=2025,
            )

        for opp in [fcs_1, fcs_2]:
            GameFactory(
                home_team=team,
                away_team=opp,
                excluded_from_rankings=True,
                is_processed=False,
                season=2025,
            )

        # Act
        ranking_service = RankingService(test_db)
        sos = ranking_service.calculate_sos(team.id, 2025)

        # Assert - Should only average FBS opponents
        expected_sos = (1800.0 + 1600.0 + 1750.0) / 3
        assert sos == pytest.approx(expected_sos, abs=0.1)


@pytest.mark.unit
class TestRegressionExistingGames:
    """Tests that existing games (excluded_from_rankings=False) still work"""

    def test_existing_games_still_included_in_rankings(self, test_db: Session):
        """Test that existing games (pre-migration) are included in rankings"""
        # Arrange - Simulate existing game (default excluded_from_rankings=False)
        configure_factories(test_db)
        team_a = TeamFactory(elo_rating=1500.0, wins=0, losses=0)
        team_b = TeamFactory(elo_rating=1500.0, wins=0, losses=0)

        game = GameFactory(
            home_team=team_a,
            away_team=team_b,
            home_score=28,
            away_score=24,
            excluded_from_rankings=False,
            is_processed=False,
        )

        ranking_service = RankingService(test_db)

        # Act - Should process without error
        result = ranking_service.process_game(game)

        # Assert
        assert result is not None
        assert "game_id" in result
        assert game.is_processed is True

        # Ratings should have changed
        test_db.refresh(team_a)
        test_db.refresh(team_b)
        assert team_a.elo_rating != 1500.0  # Winner rating increased
        assert team_b.elo_rating != 1500.0  # Loser rating decreased

        # Records should have updated
        assert team_a.wins == 1
        assert team_a.losses == 0
        assert team_b.wins == 0
        assert team_b.losses == 1

    def test_sos_calculation_unchanged_for_fbs_only(self, test_db: Session):
        """Test that SOS calculation works same as before for FBS-only schedule"""
        # Arrange - Team with only FBS opponents (no excluded games)
        configure_factories(test_db)
        team = TeamFactory(elo_rating=1600.0)
        opp_1 = TeamFactory(elo_rating=1700.0)
        opp_2 = TeamFactory(elo_rating=1650.0)
        opp_3 = TeamFactory(elo_rating=1550.0)

        # All FBS games
        for opp in [opp_1, opp_2, opp_3]:
            GameFactory(
                home_team=team,
                away_team=opp,
                excluded_from_rankings=False,
                is_processed=True,
                season=2025,
            )

        # Act
        ranking_service = RankingService(test_db)
        sos = ranking_service.calculate_sos(team.id, 2025)

        # Assert
        expected_sos = (1700.0 + 1650.0 + 1550.0) / 3
        assert sos == pytest.approx(expected_sos, abs=0.1)
