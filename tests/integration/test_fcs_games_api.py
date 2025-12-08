"""
Integration tests for FCS Game Import and API (Story 008)

Tests cover:
- FCS games are imported with excluded_from_rankings=True
- Team schedule API returns FCS games with proper flags
- FCS games don't affect team W-L records in rankings
- Complete flow from import to API response
"""

import sys

import pytest
from factories import GameFactory, TeamFactory, configure_factories
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.models.models import ConferenceType, Game, Team
from src.core.ranking_service import RankingService


@pytest.mark.integration
class TestFCSGameImport:
    """Tests for FCS game import functionality"""

    def test_fcs_game_created_with_exclusion_flag(self, test_db: Session):
        """Test that FCS games are created with excluded_from_rankings=True"""
        configure_factories(test_db)

        fbs_team = TeamFactory(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            is_fcs=False
        )
        fcs_team = TeamFactory(
            name="UT Martin",
            conference=ConferenceType.FCS,
            is_fcs=True
        )

        # Create FCS game
        game = GameFactory(
            home_team=fbs_team,
            away_team=fcs_team,
            home_score=70,
            away_score=7,
            week=2,
            season=2025,
            excluded_from_rankings=True,
            is_processed=False
        )

        # Verify game was created correctly
        assert game.excluded_from_rankings is True
        assert game.home_team.is_fcs is False
        assert game.away_team.is_fcs is True

    def test_fcs_game_cannot_be_processed_for_rankings(self, test_db: Session):
        """Test that FCS games cannot be processed for rankings"""
        configure_factories(test_db)

        fbs_team = TeamFactory(elo_rating=1600.0, wins=0, losses=0)
        fcs_team = TeamFactory(elo_rating=1200.0, is_fcs=True, wins=0, losses=0)

        game = GameFactory(
            home_team=fbs_team,
            away_team=fcs_team,
            home_score=70,
            away_score=7,
            excluded_from_rankings=True,
            is_processed=False
        )

        # Attempt to process
        ranking_service = RankingService(test_db)

        with pytest.raises(ValueError, match="Cannot process excluded game for rankings"):
            ranking_service.process_game(game)

        # Verify team records unchanged
        test_db.refresh(fbs_team)
        test_db.refresh(fcs_team)
        assert fbs_team.wins == 0
        assert fbs_team.losses == 0
        assert fcs_team.wins == 0
        assert fcs_team.losses == 0


@pytest.mark.integration
class TestTeamScheduleAPIWithFCS:
    """Tests for team schedule API returning FCS games"""

    def test_schedule_returns_fcs_games(self, test_client: TestClient, test_db: Session):
        """Test that team schedule API returns FCS games with proper flags"""

        # Create teams with explicit names
        fbs_team = Team(
            name="Georgia",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1700.0,
            initial_rating=1700.0,
            recruiting_rank=5,
            transfer_rank=10,
            returning_production=0.75,
            wins=0,
            losses=0
        )
        test_db.add(fbs_team)

        fcs_opponent = Team(
            name="Samford",
            conference=ConferenceType.FCS,
            is_fcs=True,
            elo_rating=1200.0,
            initial_rating=1200.0,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=0.5,
            wins=0,
            losses=0
        )
        test_db.add(fcs_opponent)

        fbs_opponent = Team(
            name="Auburn",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1650.0,
            initial_rating=1650.0,
            recruiting_rank=20,
            transfer_rank=15,
            returning_production=0.65,
            wins=0,
            losses=0
        )
        test_db.add(fbs_opponent)
        test_db.commit()
        test_db.refresh(fbs_team)
        test_db.refresh(fcs_opponent)
        test_db.refresh(fbs_opponent)

        # Create FCS game (excluded)
        fcs_game = Game(
            home_team_id=fbs_team.id,
            away_team_id=fcs_opponent.id,
            home_score=56,
            away_score=7,
            week=2,
            season=2025,
            is_neutral_site=False,
            excluded_from_rankings=True,
            is_processed=False
        )
        test_db.add(fcs_game)

        # Create FBS game (included)
        fbs_game = Game(
            home_team_id=fbs_team.id,
            away_team_id=fbs_opponent.id,
            home_score=27,
            away_score=20,
            week=3,
            season=2025,
            is_neutral_site=False,
            excluded_from_rankings=False,
            is_processed=True
        )
        test_db.add(fbs_game)
        test_db.commit()

        # Call API
        response = test_client.get(f"/api/teams/{fbs_team.id}/schedule?season=2025")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["team_id"] == fbs_team.id
        assert data["team_name"] == "Georgia"
        assert data["season"] == 2025
        assert len(data["games"]) == 2

        # Check FCS game
        fcs_game_data = next((g for g in data["games"] if g["week"] == 2), None)
        assert fcs_game_data is not None
        assert fcs_game_data["opponent_name"] == "Samford"
        assert fcs_game_data["excluded_from_rankings"] is True
        assert fcs_game_data["is_fcs"] is True
        assert fcs_game_data["opponent_conference"] == "FCS"

        # Check FBS game
        fbs_game_data = next((g for g in data["games"] if g["week"] == 3), None)
        assert fbs_game_data is not None
        assert fbs_game_data["opponent_name"] == "Auburn"
        assert fbs_game_data["excluded_from_rankings"] is False
        assert fbs_game_data["is_fcs"] is False
        assert fbs_game_data["opponent_conference"] == "P5"

    def test_schedule_ordered_by_week(self, test_client: TestClient, test_db: Session):
        """Test that schedule games are ordered by week"""
        # Create team
        team = Team(
            name="Florida",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1600.0,
            initial_rating=1600.0,
            recruiting_rank=15,
            transfer_rank=20,
            returning_production=0.7,
            wins=0,
            losses=0
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Create games in random week order
        for week in [5, 1, 3, 2, 4]:
            opponent = Team(
                name=f"Opponent Week {week}",
                conference=ConferenceType.FCS if week == 2 else ConferenceType.POWER_5,
                is_fcs=(week == 2),
                elo_rating=1500.0,
                initial_rating=1500.0,
                recruiting_rank=50,
                transfer_rank=50,
                returning_production=0.5,
                wins=0,
                losses=0
            )
            test_db.add(opponent)
            test_db.commit()
            test_db.refresh(opponent)

            game = Game(
                home_team_id=team.id,
                away_team_id=opponent.id,
                home_score=35,
                away_score=14,
                week=week,
                season=2025,
                is_neutral_site=False,
                excluded_from_rankings=(week == 2),
                is_processed=False
            )
            test_db.add(game)
        test_db.commit()

        # Call API
        response = test_client.get(f"/api/teams/{team.id}/schedule?season=2025")

        # Assert
        assert response.status_code == 200
        data = response.json()

        weeks = [game["week"] for game in data["games"]]
        assert weeks == [1, 2, 3, 4, 5], "Games should be ordered by week"

    def test_schedule_distinguishes_fbs_and_fcs_opponents(self, test_client: TestClient, test_db: Session):
        """Test that schedule clearly distinguishes FBS and FCS opponents"""
        # Create main team
        team = Team(
            name="LSU",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1700.0,
            initial_rating=1700.0,
            recruiting_rank=8,
            transfer_rank=12,
            returning_production=0.72,
            wins=0,
            losses=0
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Create multiple FCS games
        for i in range(2):
            fcs_opp = Team(
                name=f"FCS Team {i+1}",
                conference=ConferenceType.FCS,
                is_fcs=True,
                elo_rating=1200.0,
                initial_rating=1200.0,
                recruiting_rank=999,
                transfer_rank=999,
                returning_production=0.5,
                wins=0,
                losses=0
            )
            test_db.add(fcs_opp)
            test_db.commit()
            test_db.refresh(fcs_opp)

            game = Game(
                home_team_id=team.id,
                away_team_id=fcs_opp.id,
                home_score=52,
                away_score=10,
                week=i+1,
                season=2025,
                is_neutral_site=False,
                excluded_from_rankings=True,
                is_processed=False
            )
            test_db.add(game)

        # Create FBS games
        for i in range(3):
            fbs_opp = Team(
                name=f"FBS Team {i+1}",
                conference=ConferenceType.POWER_5,
                is_fcs=False,
                elo_rating=1600.0,
                initial_rating=1600.0,
                recruiting_rank=30,
                transfer_rank=25,
                returning_production=0.6,
                wins=0,
                losses=0
            )
            test_db.add(fbs_opp)
            test_db.commit()
            test_db.refresh(fbs_opp)

            game = Game(
                home_team_id=team.id,
                away_team_id=fbs_opp.id,
                home_score=31,
                away_score=24,
                week=i+3,
                season=2025,
                is_neutral_site=False,
                excluded_from_rankings=False,
                is_processed=False
            )
            test_db.add(game)

        test_db.commit()

        # Call API
        response = test_client.get(f"/api/teams/{team.id}/schedule?season=2025")

        # Assert
        assert response.status_code == 200
        data = response.json()

        fcs_games = [g for g in data["games"] if g["is_fcs"]]
        fbs_games = [g for g in data["games"] if not g["is_fcs"]]

        assert len(fcs_games) == 2, "Should have 2 FCS games"
        assert len(fbs_games) == 3, "Should have 3 FBS games"

        # All FCS games should be excluded
        for game in fcs_games:
            assert game["excluded_from_rankings"] is True
            assert game["opponent_conference"] == "FCS"

        # All FBS games should be included
        for game in fbs_games:
            assert game["excluded_from_rankings"] is False
            assert game["opponent_conference"] == "P5"


@pytest.mark.integration
class TestFCSGameRecordExclusion:
    """Tests that FCS games don't affect W-L records in rankings"""

    def test_team_records_exclude_fcs_games(self, test_db: Session):
        """Test that team records only count FBS games"""
        configure_factories(test_db)

        team = TeamFactory(
            name="Ohio State",
            conference=ConferenceType.POWER_5,
            elo_rating=1700.0,
            wins=0,
            losses=0
        )

        # FCS opponent (game excluded)
        fcs_opp = TeamFactory(
            name="Youngstown State",
            conference=ConferenceType.FCS,
            is_fcs=True,
            elo_rating=1200.0,
            wins=0,
            losses=0
        )

        # FBS opponent (game included)
        fbs_opp = TeamFactory(
            name="Penn State",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1650.0,
            wins=0,
            losses=0
        )

        # Create FCS game (should NOT be processed)
        fcs_game = GameFactory(
            home_team=team,
            away_team=fcs_opp,
            home_score=56,
            away_score=10,
            week=1,
            season=2025,
            excluded_from_rankings=True,
            is_processed=False
        )

        # Create FBS game (should be processed)
        fbs_game = GameFactory(
            home_team=team,
            away_team=fbs_opp,
            home_score=31,
            away_score=24,
            week=2,
            season=2025,
            excluded_from_rankings=False,
            is_processed=False
        )

        # Process only the FBS game
        ranking_service = RankingService(test_db)
        ranking_service.process_game(fbs_game)

        # Refresh teams
        test_db.refresh(team)
        test_db.refresh(fcs_opp)
        test_db.refresh(fbs_opp)

        # Assert - Only FBS game affects records
        assert team.wins == 1, "Should have 1 win (FBS game only)"
        assert team.losses == 0
        assert fbs_opp.losses == 1
        assert fcs_opp.wins == 0, "FCS opponent record unchanged"
        assert fcs_opp.losses == 0, "FCS opponent record unchanged"

    def test_rankings_only_include_fbs_games(self, test_db: Session):
        """Test that rankings calculations only include FBS games"""
        configure_factories(test_db)

        # Team with mixed schedule
        team = TeamFactory(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            elo_rating=1750.0,
            wins=0,
            losses=0
        )

        # Create 2 FCS games
        for i in range(2):
            fcs_opp = TeamFactory(
                name=f"FCS {i+1}",
                conference=ConferenceType.FCS,
                is_fcs=True,
                elo_rating=1200.0
            )
            GameFactory(
                home_team=team,
                away_team=fcs_opp,
                home_score=50,
                away_score=7,
                week=i+1,
                season=2025,
                excluded_from_rankings=True,
                is_processed=False
            )

        # Create 3 FBS games and process them
        fbs_opponents = []
        fbs_initial_ratings = []
        for i in range(3):
            initial_rating = 1600.0 + (i * 50)
            fbs_opp = TeamFactory(
                name=f"FBS Opp {i+1}",
                conference=ConferenceType.POWER_5,
                elo_rating=initial_rating,
                wins=0,
                losses=0
            )
            fbs_opponents.append(fbs_opp)
            fbs_initial_ratings.append(initial_rating)

            game = GameFactory(
                home_team=team,
                away_team=fbs_opp,
                home_score=35,
                away_score=21,
                week=i+3,
                season=2025,
                excluded_from_rankings=False,
                is_processed=False
            )

            # Process FBS game
            ranking_service = RankingService(test_db)
            ranking_service.process_game(game)

        # Refresh team and opponents
        test_db.refresh(team)
        for opp in fbs_opponents:
            test_db.refresh(opp)

        # Assert - Only FBS games count
        assert team.wins == 3, "Should have 3 wins (FBS games only)"
        assert team.losses == 0

        # Calculate SOS - should only include FBS opponents (using their CURRENT ratings after games)
        ranking_service = RankingService(test_db)
        sos = ranking_service.calculate_sos(team.id, 2025)

        # SOS should average FBS opponents' CURRENT ratings (not initial)
        # After losing, their ratings will have decreased
        current_ratings = [opp.elo_rating for opp in fbs_opponents]
        expected_sos = sum(current_ratings) / len(current_ratings)
        assert sos == pytest.approx(expected_sos, abs=0.1)
