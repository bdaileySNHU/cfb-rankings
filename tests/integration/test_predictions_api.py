"""
Integration tests for Predictions API Endpoint

Tests cover:
- GET /api/predictions - Get predictions with filtering
- next_week parameter
- week parameter
- team_id parameter
- season parameter
- Empty results handling
- Error cases
"""

import sys
from datetime import datetime

import pytest
from factories import GameFactory, SeasonFactory, TeamFactory, configure_factories
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Game, Season, Team


@pytest.mark.integration
class TestPredictionsEndpoint:
    """Tests for GET /api/predictions endpoint"""

    def test_predictions_empty_when_no_unprocessed_games(
        self, test_client: TestClient, test_db: Session
    ):
        """Test endpoint returns empty array when no unprocessed games exist"""
        # Arrange - create only processed games
        configure_factories(test_db)
        season = SeasonFactory(year=datetime.now().year, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)
        game = GameFactory(
            home_team=team1, away_team=team2, season=datetime.now().year, week=2, is_processed=True
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_predictions_next_week_default(self, test_client: TestClient, test_db: Session):
        """Test next_week=true returns only next week's games"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=3)
        team1 = TeamFactory(name="Team A", elo_rating=1600)
        team2 = TeamFactory(name="Team B", elo_rating=1500)
        team3 = TeamFactory(name="Team C", elo_rating=1550)

        # Create unprocessed games for different weeks
        game_week4 = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=4, is_processed=False
        )
        game_week5 = GameFactory(
            home_team=team2, away_team=team3, season=current_year, week=5, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 1
        assert predictions[0]["week"] == 4  # Only next week (current + 1)

    def test_predictions_specific_week(self, test_client: TestClient, test_db: Session):
        """Test filtering predictions by specific week"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)
        team3 = TeamFactory(elo_rating=1550)

        # Create unprocessed games for different weeks
        game_week2 = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=2, is_processed=False
        )
        game_week5 = GameFactory(
            home_team=team2, away_team=team3, season=current_year, week=5, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?week=5&next_week=false")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 1
        assert predictions[0]["week"] == 5

    def test_predictions_filter_by_team(self, test_client: TestClient, test_db: Session):
        """Test filtering predictions by team_id"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(name="Team A", elo_rating=1600)
        team2 = TeamFactory(name="Team B", elo_rating=1500)
        team3 = TeamFactory(name="Team C", elo_rating=1550)

        # Create unprocessed games
        game1 = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=2, is_processed=False
        )
        game2 = GameFactory(
            home_team=team2, away_team=team3, season=current_year, week=2, is_processed=False
        )
        test_db.commit()

        # Act - filter by team1's ID
        response = test_client.get(f"/api/predictions?team_id={team1.id}&next_week=false")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 1
        # Should only return game involving team1
        assert predictions[0]["home_team"] == "Team A" or predictions[0]["away_team"] == "Team A"

    def test_predictions_response_structure(self, test_client: TestClient, test_db: Session):
        """Test that prediction response has all required fields"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(name="Georgia", elo_rating=1700)
        team2 = TeamFactory(name="Alabama", elo_rating=1650)
        game = GameFactory(
            home_team=team1,
            away_team=team2,
            season=current_year,
            week=2,
            is_processed=False,
            is_neutral_site=False,
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 1

        prediction = predictions[0]
        # Check all required fields
        required_fields = [
            "game_id",
            "home_team_id",
            "home_team",
            "away_team_id",
            "away_team",
            "week",
            "season",
            "game_date",
            "is_neutral_site",
            "predicted_winner",
            "predicted_winner_id",
            "predicted_home_score",
            "predicted_away_score",
            "home_win_probability",
            "away_win_probability",
            "confidence",
            "home_team_rating",
            "away_team_rating",
        ]
        for field in required_fields:
            assert field in prediction, f"Missing field: {field}"

        # Check data types and values
        assert isinstance(prediction["game_id"], int)
        assert isinstance(prediction["home_team"], str)
        assert isinstance(prediction["away_team"], str)
        assert isinstance(prediction["predicted_home_score"], int)
        assert isinstance(prediction["predicted_away_score"], int)
        assert isinstance(prediction["home_win_probability"], (int, float))
        assert isinstance(prediction["away_win_probability"], (int, float))
        assert prediction["confidence"] in ["High", "Medium", "Low"]

    def test_predictions_probabilities_valid(self, test_client: TestClient, test_db: Session):
        """Test that win probabilities are valid percentages"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)
        game = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=2, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        prediction = predictions[0]

        # Probabilities should be between 0 and 100
        assert 0 <= prediction["home_win_probability"] <= 100
        assert 0 <= prediction["away_win_probability"] <= 100

        # Probabilities should sum to approximately 100
        total = prediction["home_win_probability"] + prediction["away_win_probability"]
        assert 99.9 <= total <= 100.1

    def test_predictions_scores_within_range(self, test_client: TestClient, test_db: Session):
        """Test that predicted scores are within valid range"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)
        game = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=2, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        prediction = predictions[0]

        # Scores should be between 0 and 150
        assert 0 <= prediction["predicted_home_score"] <= 150
        assert 0 <= prediction["predicted_away_score"] <= 150

    def test_predictions_home_field_advantage(self, test_client: TestClient, test_db: Session):
        """Test that home field advantage affects predictions"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        # Equal rated teams
        team1 = TeamFactory(name="Home Team", elo_rating=1500)
        team2 = TeamFactory(name="Away Team", elo_rating=1500)
        game = GameFactory(
            home_team=team1,
            away_team=team2,
            season=current_year,
            week=2,
            is_processed=False,
            is_neutral_site=False,
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        prediction = predictions[0]

        # Home team should have advantage despite equal ratings
        assert prediction["home_win_probability"] > 50.0
        assert prediction["away_win_probability"] < 50.0

    def test_predictions_neutral_site(self, test_client: TestClient, test_db: Session):
        """Test that neutral site removes home field advantage"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        # Equal rated teams
        team1 = TeamFactory(elo_rating=1500)
        team2 = TeamFactory(elo_rating=1500)
        game = GameFactory(
            home_team=team1,
            away_team=team2,
            season=current_year,
            week=2,
            is_processed=False,
            is_neutral_site=True,
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        prediction = predictions[0]

        # Equal ratings on neutral site should be 50/50
        assert prediction["home_win_probability"] == 50.0
        assert prediction["away_win_probability"] == 50.0

    def test_predictions_invalid_week_validation(self, test_client: TestClient, test_db: Session):
        """Test that invalid week parameter returns validation error"""
        # Act
        response = test_client.get("/api/predictions?week=99&next_week=false")

        # Assert
        assert response.status_code == 422  # Validation error

    def test_predictions_no_season(self, test_client: TestClient, test_db: Session):
        """Test predictions when no season exists returns empty array"""
        # Arrange - no season created
        configure_factories(test_db)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)
        game = GameFactory(
            home_team=team1, away_team=team2, season=datetime.now().year, week=2, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        assert response.json() == []  # No active season, no predictions

    def test_predictions_multiple_games(self, test_client: TestClient, test_db: Session):
        """Test predictions with multiple unprocessed games"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)
        team3 = TeamFactory(elo_rating=1550)
        team4 = TeamFactory(elo_rating=1450)

        # Create multiple unprocessed games for next week
        game1 = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=2, is_processed=False
        )
        game2 = GameFactory(
            home_team=team3, away_team=team4, season=current_year, week=2, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 2

    def test_predictions_skips_teams_with_zero_rating(
        self, test_client: TestClient, test_db: Session
    ):
        """Test that predictions skip games with invalid team ratings"""
        # Arrange
        configure_factories(test_db)
        current_year = datetime.now().year
        season = SeasonFactory(year=current_year, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=0)  # Invalid rating
        game = GameFactory(
            home_team=team1, away_team=team2, season=current_year, week=2, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 0  # Should skip invalid game

    def test_predictions_season_parameter(self, test_client: TestClient, test_db: Session):
        """Test filtering predictions by season year"""
        # Arrange
        configure_factories(test_db)
        season_2024 = SeasonFactory(year=2024, current_week=1)
        season_2025 = SeasonFactory(year=2025, current_week=1)
        team1 = TeamFactory(elo_rating=1600)
        team2 = TeamFactory(elo_rating=1500)

        game_2024 = GameFactory(
            home_team=team1, away_team=team2, season=2024, week=2, is_processed=False
        )
        game_2025 = GameFactory(
            home_team=team1, away_team=team2, season=2025, week=2, is_processed=False
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/predictions?season=2024&next_week=true")

        # Assert
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) == 1
        assert predictions[0]["season"] == 2024
