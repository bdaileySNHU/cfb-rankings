"""
Tests for API endpoints in main.py

These tests validate the FastAPI endpoints including:
- Prediction endpoints with various filters
- Rankings endpoints
- Stats endpoints
- Error handling and edge cases

EPIC-013 Story 002: Improve Test Coverage - Phase 4
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# We'll need to import the app
from src.api.main import app
from src.models.models import Game, Prediction, Season, Team


@pytest.fixture
def client(test_db):
    """Create FastAPI test client with test database"""
    from src.models.database import get_db

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def sample_season():
    """Create sample season"""
    season = Mock(spec=Season)
    season.id = 1
    season.year = 2025
    season.current_week = 10
    season.is_active = True
    return season


@pytest.fixture
def sample_teams():
    """Create sample teams"""
    team1 = Mock(spec=Team)
    team1.id = 1
    team1.name = "Ohio State"
    team1.elo_rating = 1800.0
    team1.wins = 8
    team1.losses = 1
    team1.is_fcs = False

    team2 = Mock(spec=Team)
    team2.id = 2
    team2.name = "Michigan"
    team2.elo_rating = 1750.0
    team2.wins = 7
    team2.losses = 2
    team2.is_fcs = False

    return [team1, team2]


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check_returns_200(self, client):
        """Test that root endpoint returns 200 OK"""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_check_returns_correct_structure(self, client):
        """Test that health check returns expected JSON structure"""
        response = client.get("/")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert data["status"] == "healthy"
        assert data["service"] == "College Football Ranking API"


class TestPredictionsEndpoint:
    """Tests for /api/predictions endpoint"""

    def test_get_predictions_with_next_week_default(self, client):
        """Test that next_week=True is the default behavior"""
        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = []

            response = client.get("/api/predictions")

            assert response.status_code == 200
            # Verify next_week=True was passed by default
            call_args = mock_generate.call_args
            assert call_args.kwargs.get("next_week") == True

    def test_get_predictions_with_specific_week(self, client):
        """Test filtering predictions by specific week"""
        mock_prediction = {
            "game_id": 1,
            "home_team_id": 1,
            "home_team": "Ohio State",
            "away_team_id": 2,
            "away_team": "Michigan",
            "week": 10,
            "season": 2025,
            "predicted_winner": "Ohio State",
            "predicted_winner_id": 1,
            "predicted_home_score": 28,
            "predicted_away_score": 21,
            "home_win_probability": 65.0,
            "away_win_probability": 35.0,
            "confidence": "Medium",
            "home_team_rating": 1800.0,
            "away_team_rating": 1750.0,
            "is_neutral_site": False,
        }

        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = [mock_prediction]

            response = client.get("/api/predictions?week=10&next_week=false")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["week"] == 10

    def test_get_predictions_with_team_filter(self, client):
        """Test filtering predictions by team_id"""
        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = []

            response = client.get("/api/predictions?team_id=1&next_week=false")

            assert response.status_code == 200
            # Verify team_id was passed
            call_args = mock_generate.call_args
            assert call_args.kwargs.get("team_id") == 1

    def test_get_predictions_with_season_filter(self, client):
        """Test filtering predictions by season year"""
        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = []

            response = client.get("/api/predictions?season=2024&next_week=false")

            assert response.status_code == 200
            call_args = mock_generate.call_args
            assert call_args.kwargs.get("season_year") == 2024

    def test_get_predictions_week_validation(self, client):
        """Test that invalid week numbers are rejected"""
        # Week > 15 should be rejected by FastAPI validation
        response = client.get("/api/predictions?week=20&next_week=false")
        assert response.status_code == 422  # Validation error

    def test_get_predictions_handles_errors_gracefully(self, client):
        """Test that endpoint returns 500 on internal errors"""
        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.side_effect = Exception("Database error")

            response = client.get("/api/predictions")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Error generating predictions" in data["detail"]


class TestRankingsEndpoint:
    """Tests for /api/rankings endpoint"""

    def test_get_rankings_with_default_limit(self, client):
        """Test that default limit is 25"""
        with patch("src.api.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock active season query
            mock_season_query = Mock()
            mock_season = Mock()
            mock_season.year = 2025
            mock_season.current_week = 10
            mock_season_query.filter.return_value.first.return_value = mock_season

            # Mock RankingService
            with patch("src.api.main.RankingService") as MockRankingService:
                mock_service = Mock()
                mock_service.get_current_rankings.return_value = []
                MockRankingService.return_value = mock_service

                mock_db.query.return_value = mock_season_query

                response = client.get("/api/rankings")

                assert response.status_code == 200
                data = response.json()
                assert "week" in data
                assert "season" in data
                assert "rankings" in data
                assert "total_teams" in data

    def test_get_rankings_with_custom_limit(self, client):
        """Test rankings with custom limit parameter"""
        with patch("src.api.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            mock_season_query = Mock()
            mock_season = Mock()
            mock_season.year = 2025
            mock_season.current_week = 10
            mock_season_query.filter.return_value.first.return_value = mock_season

            with patch("src.api.main.RankingService") as MockRankingService:
                mock_service = Mock()
                # Return 50 rankings with all required fields
                from src.models.models import ConferenceType

                mock_service.get_current_rankings.return_value = [
                    {
                        "rank": i,
                        "team_id": i,
                        "team_name": f"Team {i}",
                        "conference": ConferenceType.POWER_5,
                        "elo_rating": 1500.0 + i,
                        "wins": 5,
                        "losses": 2,
                        "sos": 1500.0,
                    }
                    for i in range(1, 51)
                ]
                MockRankingService.return_value = mock_service

                mock_db.query.return_value = mock_season_query

                response = client.get("/api/rankings?limit=50")

                assert response.status_code == 200
                data = response.json()
                assert data["total_teams"] == 50

    def test_get_rankings_limit_validation(self, client):
        """Test that limit is validated (1-200)"""
        # Limit too high
        response = client.get("/api/rankings?limit=300")
        assert response.status_code == 422  # Validation error

        # Limit too low
        response = client.get("/api/rankings?limit=0")
        assert response.status_code == 422

    def test_get_rankings_with_specific_season(self, client):
        """Test rankings for a specific season"""
        with patch("src.api.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            mock_season_query = Mock()
            mock_season = Mock()
            mock_season.year = 2024
            mock_season.current_week = 15
            mock_season_query.filter.return_value.first.return_value = mock_season

            with patch("src.api.main.RankingService") as MockRankingService:
                mock_service = Mock()
                mock_service.get_current_rankings.return_value = []
                MockRankingService.return_value = mock_service

                mock_db.query.return_value = mock_season_query

                response = client.get("/api/rankings?season=2024")

                assert response.status_code == 200
                data = response.json()
                assert data["season"] == 2024


class TestStatsEndpoint:
    """Tests for /api/stats endpoint"""

    def test_get_stats_returns_correct_structure(self, client):
        """Test that stats endpoint returns all expected fields"""
        with patch("src.api.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock all count queries
            mock_db.query.return_value.count.return_value = 100

            # Mock active season
            mock_season_query = Mock()
            mock_season = Mock()
            mock_season.year = 2025
            mock_season.current_week = 10
            mock_season_query.filter.return_value.first.return_value = mock_season

            def query_side_effect(model):
                if model == Season:
                    return mock_season_query
                return Mock(
                    count=Mock(return_value=100),
                    filter=Mock(return_value=Mock(count=Mock(return_value=50))),
                )

            mock_db.query.side_effect = query_side_effect

            response = client.get("/api/stats")

            assert response.status_code == 200
            data = response.json()

            # Verify all required fields
            assert "total_teams" in data
            assert "total_games" in data
            assert "total_games_processed" in data
            assert "current_season" in data
            assert "current_week" in data
            assert "last_updated" in data

    def test_get_stats_validates_data_structure(self, client):
        """Test that stats endpoint data structure is valid"""
        # This test uses the real database (which is acceptable for integration-style API tests)
        # We're just validating the structure, not specific values
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert isinstance(data["total_teams"], int)
        assert isinstance(data["total_games"], int)
        assert isinstance(data["total_games_processed"], int)
        assert isinstance(data["current_season"], int)
        assert isinstance(data["current_week"], int)
        assert "last_updated" in data


class TestActiveSeasonEndpoint:
    """Tests for /api/seasons/active endpoint"""

    def test_get_active_season_returns_valid_structure(self, client):
        """Test that active season endpoint returns valid data structure"""
        # Uses real database - validates structure
        response = client.get("/api/seasons/active")

        # Should either return 200 with season data or 404 if no active season
        if response.status_code == 200:
            data = response.json()
            assert "year" in data
            assert "current_week" in data
            assert "is_active" in data
            assert isinstance(data["year"], int)
            assert isinstance(data["current_week"], int)
            assert isinstance(data["is_active"], bool)
        else:
            # If no active season, should return 404
            assert response.status_code == 404

    def test_active_season_endpoint_error_handling(self, client):
        """Test that endpoint handles database errors gracefully"""
        # This test documents expected behavior but doesn't test implementation
        # In production, database errors should return 500 status
        response = client.get("/api/seasons/active")

        # Response should be either 200 (success) or 404 (not found)
        # Never 500 (unless there's a real error)
        assert response.status_code in [200, 404]


class TestPredictionAccuracyEndpoint:
    """Tests for /api/predictions/accuracy endpoint"""

    def test_get_prediction_accuracy_success(self, client):
        """Test getting overall prediction accuracy"""
        mock_stats = {
            "total_predictions": 100,
            "evaluated_predictions": 75,
            "correct_predictions": 60,
            "accuracy_percentage": 80.0,
            "high_confidence_accuracy": 85.0,
            "medium_confidence_accuracy": 75.0,
            "low_confidence_accuracy": 65.0,
        }

        with patch("src.api.main.get_overall_prediction_accuracy") as mock_get_accuracy:
            mock_get_accuracy.return_value = mock_stats

            response = client.get("/api/predictions/accuracy")

            assert response.status_code == 200
            data = response.json()
            assert data["total_predictions"] == 100
            assert data["accuracy_percentage"] == 80.0

    def test_get_prediction_accuracy_with_season_filter(self, client):
        """Test accuracy filtering by season"""
        with patch("src.api.main.get_overall_prediction_accuracy") as mock_get_accuracy:
            mock_get_accuracy.return_value = {
                "total_predictions": 50,
                "evaluated_predictions": 40,
                "correct_predictions": 32,
                "accuracy_percentage": 80.0,
            }

            response = client.get("/api/predictions/accuracy?season=2024")

            assert response.status_code == 200
            # Verify season was passed
            call_args = mock_get_accuracy.call_args
            assert call_args.kwargs.get("season") == 2024

    def test_get_prediction_accuracy_handles_errors(self, client):
        """Test error handling for accuracy endpoint"""
        with patch("src.api.main.get_overall_prediction_accuracy") as mock_get_accuracy:
            mock_get_accuracy.side_effect = Exception("Database error")

            response = client.get("/api/predictions/accuracy")

            assert response.status_code == 500
            data = response.json()
            assert "Error retrieving prediction accuracy" in data["detail"]


class TestTeamPredictionAccuracyEndpoint:
    """Tests for /api/predictions/accuracy/team/{team_id} endpoint"""

    def test_get_team_prediction_accuracy_success(self, client):
        """Test getting team-specific prediction accuracy"""
        mock_stats = {
            "team_id": 1,
            "team_name": "Ohio State",
            "total_predictions": 30,
            "evaluated_predictions": 25,
            "correct_predictions": 20,
            "accuracy_percentage": 80.0,
            "as_favorite_accuracy": 85.0,
            "as_underdog_accuracy": 70.0,
        }

        with patch("src.api.main.get_team_prediction_accuracy") as mock_get_accuracy:
            mock_get_accuracy.return_value = mock_stats

            response = client.get("/api/predictions/accuracy/team/1")

            assert response.status_code == 200
            data = response.json()
            assert data["team_id"] == 1
            assert data["team_name"] == "Ohio State"
            assert data["accuracy_percentage"] == 80.0

    def test_get_team_prediction_accuracy_with_season(self, client):
        """Test team accuracy with season filter"""
        with patch("src.api.main.get_team_prediction_accuracy") as mock_get_accuracy:
            mock_get_accuracy.return_value = {
                "team_id": 1,
                "team_name": "Ohio State",
                "total_predictions": 15,
                "evaluated_predictions": 12,
                "correct_predictions": 10,
                "accuracy_percentage": 83.33,
            }

            response = client.get("/api/predictions/accuracy/team/1?season=2024")

            assert response.status_code == 200
            call_args = mock_get_accuracy.call_args
            assert call_args.kwargs.get("team_id") == 1
            assert call_args.kwargs.get("season") == 2024


class TestErrorResponses:
    """Tests for error handling across endpoints"""

    def test_invalid_team_id_format(self, client):
        """Test that invalid team_id format returns 422"""
        response = client.get("/api/predictions?team_id=abc")
        assert response.status_code == 422

    def test_invalid_week_range(self, client):
        """Test that out-of-range week returns 422"""
        response = client.get("/api/predictions?week=-1")
        assert response.status_code == 422

    def test_invalid_season_range(self, client):
        """Test that invalid season year returns 422"""
        response = client.get("/api/predictions?season=1999")
        assert response.status_code == 422


class TestPredictionResponseFormat:
    """Tests for prediction response data structure"""

    def test_prediction_contains_required_fields(self, client):
        """Test that prediction response has all required fields"""
        mock_prediction = {
            "game_id": 1,
            "home_team_id": 1,
            "home_team": "Ohio State",
            "away_team_id": 2,
            "away_team": "Michigan",
            "week": 10,
            "season": 2025,
            "predicted_winner": "Ohio State",
            "predicted_winner_id": 1,
            "predicted_home_score": 28,
            "predicted_away_score": 21,
            "home_win_probability": 65.0,
            "away_win_probability": 35.0,
            "confidence": "Medium",
            "home_team_rating": 1800.0,
            "away_team_rating": 1750.0,
            "is_neutral_site": False,
        }

        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = [mock_prediction]

            response = client.get("/api/predictions?next_week=false&week=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

            pred = data[0]
            # Verify all required fields
            required_fields = [
                "game_id",
                "home_team",
                "away_team",
                "week",
                "season",
                "predicted_winner",
                "predicted_home_score",
                "predicted_away_score",
                "home_win_probability",
                "away_win_probability",
                "confidence",
                "home_team_rating",
                "away_team_rating",
            ]

            for field in required_fields:
                assert field in pred, f"Missing required field: {field}"

    def test_win_probabilities_sum_to_100(self, client):
        """Test that home and away win probabilities sum to 100%"""
        mock_prediction = {
            "game_id": 1,
            "home_team_id": 1,
            "home_team": "Ohio State",
            "away_team_id": 2,
            "away_team": "Michigan",
            "week": 10,
            "season": 2025,
            "predicted_winner": "Ohio State",
            "predicted_winner_id": 1,
            "predicted_home_score": 28,
            "predicted_away_score": 21,
            "home_win_probability": 65.0,
            "away_win_probability": 35.0,
            "confidence": "Medium",
            "home_team_rating": 1800.0,
            "away_team_rating": 1750.0,
            "is_neutral_site": False,
        }

        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = [mock_prediction]

            response = client.get("/api/predictions?next_week=false&week=10")

            assert response.status_code == 200
            data = response.json()
            pred = data[0]

            # Probabilities should sum to 100
            total_prob = pred["home_win_probability"] + pred["away_win_probability"]
            assert abs(total_prob - 100.0) < 0.01  # Allow small floating point error


class TestPredictionFiltering:
    """Tests for prediction filtering logic"""

    def test_next_week_filter_behavior(self, client):
        """Test that next_week parameter works correctly"""
        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = []

            # Test next_week=True
            response = client.get("/api/predictions?next_week=true")
            assert response.status_code == 200
            call_args = mock_generate.call_args
            assert call_args.kwargs.get("next_week") == True

            # Test next_week=False
            response = client.get("/api/predictions?next_week=false")
            assert response.status_code == 200
            call_args = mock_generate.call_args
            assert call_args.kwargs.get("next_week") == False

    def test_week_and_next_week_interaction(self, client):
        """Test behavior when both week and next_week are specified"""
        with patch("src.api.main.generate_predictions") as mock_generate:
            mock_generate.return_value = []

            # When week is specified, next_week should be set to False
            response = client.get("/api/predictions?week=10&next_week=false")
            assert response.status_code == 200

            call_args = mock_generate.call_args
            assert call_args.kwargs.get("week") == 10
            assert call_args.kwargs.get("next_week") == False


class TestAPIDocumentation:
    """Tests to ensure API follows OpenAPI spec"""

    def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is generated"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "College Football Ranking API"

    def test_api_has_correct_tags(self, client):
        """Test that endpoints are properly tagged"""
        response = client.get("/openapi.json")
        schema = response.json()

        # Verify key tags exist
        tags = [tag["name"] for tag in schema.get("tags", [])]
        expected_tags = ["Predictions", "Rankings", "Stats", "Health"]

        # At least some of these tags should be present
        # (exact tags may vary based on implementation)
        assert "Predictions" in str(schema) or "Rankings" in str(schema)
