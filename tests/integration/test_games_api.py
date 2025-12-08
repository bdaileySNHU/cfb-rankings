"""
Integration tests for Game API Endpoints

Tests cover:
- GET /api/games - List games with filtering and pagination
- GET /api/games/{id} - Get game detail with team names
- POST /api/games - Create and process game (updates rankings)
- Error cases (404, 400, etc.)
"""

import sys

import pytest
from factories import GameFactory, SeasonFactory, TeamFactory, configure_factories
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Game, Season, Team


@pytest.mark.integration
class TestGetGamesList:
    """Tests for GET /api/games endpoint"""

    def test_get_games_empty_list(self, test_client: TestClient, test_db: Session):
        """Test getting games when database is empty"""
        # Act
        response = test_client.get("/api/games")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_games_returns_all_games(self, test_client: TestClient, test_db: Session):
        """Test getting all games without filtering"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory(name="Alabama")
        team2 = TeamFactory(name="Georgia")
        team3 = TeamFactory(name="LSU")

        game1 = GameFactory(home_team=team1, away_team=team2, season=2024, week=1)
        game2 = GameFactory(home_team=team2, away_team=team3, season=2024, week=2)
        game3 = GameFactory(home_team=team3, away_team=team1, season=2024, week=3)
        test_db.commit()

        # Act
        response = test_client.get("/api/games")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_games_pagination_skip(self, test_client: TestClient, test_db: Session):
        """Test pagination with skip parameter"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()

        for i in range(5):
            GameFactory(home_team=team1, away_team=team2, week=i+1)
        test_db.commit()

        # Act
        response = test_client.get("/api/games?skip=2")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_games_pagination_limit(self, test_client: TestClient, test_db: Session):
        """Test pagination with limit parameter"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()

        for i in range(10):
            GameFactory(home_team=team1, away_team=team2, week=i+1)
        test_db.commit()

        # Act
        response = test_client.get("/api/games?limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_games_filter_by_season(self, test_client: TestClient, test_db: Session):
        """Test filtering games by season"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()

        game_2024 = GameFactory(home_team=team1, away_team=team2, season=2024, week=1)
        game_2023 = GameFactory(home_team=team1, away_team=team2, season=2023, week=1)
        test_db.commit()

        # Act
        response = test_client.get("/api/games?season=2024")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["season"] == 2024

    def test_get_games_filter_by_week(self, test_client: TestClient, test_db: Session):
        """Test filtering games by week"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()

        game_week1 = GameFactory(home_team=team1, away_team=team2, week=1)
        game_week2 = GameFactory(home_team=team1, away_team=team2, week=2)
        game_week3 = GameFactory(home_team=team1, away_team=team2, week=3)
        test_db.commit()

        # Act
        response = test_client.get("/api/games?week=2")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["week"] == 2

    def test_get_games_filter_by_team_id(self, test_client: TestClient, test_db: Session):
        """Test filtering games by team"""
        # Arrange
        configure_factories(test_db)
        alabama = TeamFactory(name="Alabama")
        georgia = TeamFactory(name="Georgia")
        lsu = TeamFactory(name="LSU")

        # Games involving Alabama
        game1 = GameFactory(home_team=alabama, away_team=georgia, week=1)
        game2 = GameFactory(home_team=lsu, away_team=alabama, week=2)
        # Game not involving Alabama
        game3 = GameFactory(home_team=georgia, away_team=lsu, week=3)
        test_db.commit()

        # Act
        response = test_client.get(f"/api/games?team_id={alabama.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Verify Alabama is in both games
        for game in data:
            assert alabama.id in [game["home_team_id"], game["away_team_id"]]

    def test_get_games_filter_by_processed(self, test_client: TestClient, test_db: Session):
        """Test filtering games by processed status"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()

        processed_game = GameFactory(home_team=team1, away_team=team2, is_processed=True, week=1)
        unprocessed_game = GameFactory(home_team=team1, away_team=team2, is_processed=False, week=2)
        test_db.commit()

        # Act
        response = test_client.get("/api/games?processed=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_processed"] is True

    def test_get_games_multiple_filters(self, test_client: TestClient, test_db: Session):
        """Test combining multiple filters"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()
        team3 = TeamFactory()

        # Target game: season=2024, week=2, team1
        target_game = GameFactory(home_team=team1, away_team=team2, season=2024, week=2)
        # Other games
        GameFactory(home_team=team1, away_team=team2, season=2023, week=2)  # Wrong season
        GameFactory(home_team=team1, away_team=team2, season=2024, week=1)  # Wrong week
        GameFactory(home_team=team2, away_team=team3, season=2024, week=2)  # Wrong team
        test_db.commit()

        # Act
        response = test_client.get(f"/api/games?season=2024&week=2&team_id={team1.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == target_game.id

    def test_get_games_sorted_by_week_desc(self, test_client: TestClient, test_db: Session):
        """Test that games are sorted by week descending"""
        # Arrange
        configure_factories(test_db)
        team1 = TeamFactory()
        team2 = TeamFactory()

        game1 = GameFactory(home_team=team1, away_team=team2, week=1)
        game2 = GameFactory(home_team=team1, away_team=team2, week=3)
        game3 = GameFactory(home_team=team1, away_team=team2, week=2)
        test_db.commit()

        # Act
        response = test_client.get("/api/games")

        # Assert
        assert response.status_code == 200
        data = response.json()
        weeks = [game["week"] for game in data]
        assert weeks == [3, 2, 1]  # Descending order


@pytest.mark.integration
class TestGetGameDetail:
    """Tests for GET /api/games/{id} endpoint"""

    def test_get_game_by_id_success(self, test_client: TestClient, test_db: Session):
        """Test getting game by ID returns correct game"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(name="Alabama")
        away_team = TeamFactory(name="Georgia")
        game = GameFactory(
            home_team=home_team,
            away_team=away_team,
            home_score=35,
            away_score=28,
            week=5
        )
        test_db.commit()

        # Act
        response = test_client.get(f"/api/games/{game.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game.id
        assert data["home_score"] == 35
        assert data["away_score"] == 28
        assert data["week"] == 5

    def test_get_game_includes_team_names(self, test_client: TestClient, test_db: Session):
        """Test that game detail includes team names"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(name="Alabama")
        away_team = TeamFactory(name="Georgia")
        game = GameFactory(
            home_team=home_team,
            away_team=away_team,
            home_score=35,
            away_score=28
        )
        test_db.commit()

        # Act
        response = test_client.get(f"/api/games/{game.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["home_team_name"] == "Alabama"
        assert data["away_team_name"] == "Georgia"

    def test_get_game_includes_winner_loser(self, test_client: TestClient, test_db: Session):
        """Test that game detail includes winner and loser names"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(name="Alabama")
        away_team = TeamFactory(name="Georgia")
        game = GameFactory(
            home_team=home_team,
            away_team=away_team,
            home_score=35,
            away_score=28
        )
        test_db.commit()

        # Act
        response = test_client.get(f"/api/games/{game.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["winner_name"] == "Alabama"  # Higher score
        assert data["loser_name"] == "Georgia"

    def test_get_game_includes_point_differential(self, test_client: TestClient, test_db: Session):
        """Test that game detail includes point differential"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory()
        away_team = TeamFactory()
        game = GameFactory(
            home_team=home_team,
            away_team=away_team,
            home_score=42,
            away_score=14
        )
        test_db.commit()

        # Act
        response = test_client.get(f"/api/games/{game.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["point_differential"] == 28  # 42 - 14

    def test_get_game_by_id_not_found(self, test_client: TestClient, test_db: Session):
        """Test getting non-existent game returns 404"""
        # Act
        response = test_client.get("/api/games/99999")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
class TestCreateGame:
    """Tests for POST /api/games endpoint"""

    def test_create_game_success(self, test_client: TestClient, test_db: Session):
        """Test creating a new game successfully"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(name="Alabama", elo_rating=1700.0)
        away_team = TeamFactory(name="Georgia", elo_rating=1650.0)
        test_db.commit()

        game_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "home_score": 35,
            "away_score": 28,
            "week": 5,
            "season": 2024,
            "is_neutral_site": False
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 201
        data = response.json()

        # Verify game result data
        assert data["game_id"] is not None
        assert data["winner_name"] == "Alabama"
        assert data["loser_name"] == "Georgia"
        assert data["score"] == "35-28"

        # Verify ELO changes occurred
        assert data["winner_rating_change"] > 0
        assert data["loser_rating_change"] < 0
        assert data["winner_new_rating"] > 1700.0
        assert data["loser_new_rating"] < 1650.0

    def test_create_game_processes_immediately(self, test_client: TestClient, test_db: Session):
        """Test that creating a game processes it immediately"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(name="Alabama", elo_rating=1700.0, wins=0, losses=0)
        away_team = TeamFactory(name="Georgia", elo_rating=1650.0, wins=0, losses=0)
        test_db.commit()

        initial_home_rating = home_team.elo_rating
        initial_away_rating = away_team.elo_rating

        game_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "home_score": 35,
            "away_score": 28,
            "week": 5,
            "season": 2024,
            "is_neutral_site": False
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 201

        # Refresh teams from database
        test_db.refresh(home_team)
        test_db.refresh(away_team)

        # Verify ratings changed
        assert home_team.elo_rating != initial_home_rating
        assert away_team.elo_rating != initial_away_rating

        # Verify records updated
        assert home_team.wins == 1
        assert home_team.losses == 0
        assert away_team.wins == 0
        assert away_team.losses == 1

    def test_create_game_team_not_found(self, test_client: TestClient, test_db: Session):
        """Test creating game with non-existent team fails"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory()
        test_db.commit()

        game_data = {
            "home_team_id": home_team.id,
            "away_team_id": 99999,  # Non-existent
            "home_score": 35,
            "away_score": 28,
            "week": 5,
            "season": 2024,
            "is_neutral_site": False
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_game_team_plays_itself_fails(self, test_client: TestClient, test_db: Session):
        """Test that a team cannot play itself"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory()
        test_db.commit()

        game_data = {
            "home_team_id": team.id,
            "away_team_id": team.id,  # Same team!
            "home_score": 35,
            "away_score": 28,
            "week": 5,
            "season": 2024,
            "is_neutral_site": False
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 400
        assert "cannot play itself" in response.json()["detail"].lower()

    def test_create_game_neutral_site(self, test_client: TestClient, test_db: Session):
        """Test creating a neutral site game"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(elo_rating=1700.0)
        away_team = TeamFactory(elo_rating=1700.0)  # Equal ratings
        test_db.commit()

        game_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "home_score": 35,
            "away_score": 28,
            "week": 5,
            "season": 2024,
            "is_neutral_site": True  # Neutral site
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 201
        data = response.json()

        # Verify game was processed
        assert data["winner_rating_change"] > 0

        # On neutral site with equal ratings, expected probability should be ~0.5
        # (no home field advantage)
        assert 0.45 <= data["winner_expected_probability"] <= 0.55

    def test_create_game_invalid_week(self, test_client: TestClient, test_db: Session):
        """Test creating game with invalid week fails validation"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory()
        away_team = TeamFactory()
        test_db.commit()

        game_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "home_score": 35,
            "away_score": 28,
            "week": 25,  # Invalid - should be 0-20
            "season": 2024,
            "is_neutral_site": False
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_create_game_blowout_has_mov_multiplier(self, test_client: TestClient, test_db: Session):
        """Test that blowout games have appropriate MOV multiplier"""
        # Arrange
        configure_factories(test_db)
        home_team = TeamFactory(elo_rating=1700.0)
        away_team = TeamFactory(elo_rating=1700.0)
        test_db.commit()

        game_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "home_score": 63,
            "away_score": 14,  # 49 point blowout
            "week": 5,
            "season": 2024,
            "is_neutral_site": False
        }

        # Act
        response = test_client.post("/api/games", json=game_data)

        # Assert
        assert response.status_code == 201
        data = response.json()

        # Large margin should have higher MOV multiplier
        # MOV multiplier is min(ln(point_diff + 1), 2.5)
        # For 49 points: ln(50) ≈ 3.9, capped at 2.5
        assert data["mov_multiplier"] == pytest.approx(2.5, abs=0.01)
