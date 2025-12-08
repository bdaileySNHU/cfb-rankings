"""
Integration tests for Rankings and Seasons API Endpoints

Tests cover:
- GET /api/rankings - Get current rankings with limit
- GET /api/rankings/history - Get team ranking history
- POST /api/rankings/save - Save rankings to history
- GET /api/seasons - List all seasons
- POST /api/seasons - Create new season
- POST /api/seasons/{year}/reset - Reset season ratings
- Error cases (404, 400, etc.)
"""

import sys

import pytest
from factories import (
    GameFactory,
    RankingHistoryFactory,
    SeasonFactory,
    TeamFactory,
    configure_factories,
)
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Game, RankingHistory, Season, Team


@pytest.mark.integration
class TestGetRankings:
    """Tests for GET /api/rankings endpoint"""

    def test_get_rankings_empty(self, test_client: TestClient, test_db: Session):
        """Test getting rankings when no teams exist"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, is_active=True)
        test_db.commit()

        # Act
        response = test_client.get("/api/rankings")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2024
        assert len(data["rankings"]) == 0
        assert data["total_teams"] == 0

    def test_get_rankings_returns_top_teams(self, test_client: TestClient, test_db: Session):
        """Test getting rankings returns teams sorted by ELO"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, is_active=True, current_week=5)

        # Create teams with different ratings
        team1 = TeamFactory(name="Alabama", elo_rating=1850.0, wins=5, losses=0)
        team2 = TeamFactory(name="Georgia", elo_rating=1840.0, wins=4, losses=1)
        team3 = TeamFactory(name="Ohio State", elo_rating=1830.0, wins=5, losses=0)
        team4 = TeamFactory(name="Michigan", elo_rating=1820.0, wins=4, losses=1)
        test_db.commit()

        # Act
        response = test_client.get("/api/rankings")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2024
        assert data["week"] == 5
        assert len(data["rankings"]) == 4
        assert data["total_teams"] == 4

        # Verify sorted by ELO descending
        assert data["rankings"][0]["team_name"] == "Alabama"
        assert data["rankings"][0]["rank"] == 1
        assert data["rankings"][0]["elo_rating"] == 1850.0

        assert data["rankings"][1]["team_name"] == "Georgia"
        assert data["rankings"][1]["rank"] == 2

    def test_get_rankings_limit(self, test_client: TestClient, test_db: Session):
        """Test rankings limit parameter"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, is_active=True)

        # Create 10 teams
        for i in range(10):
            TeamFactory(elo_rating=1500.0 + i)
        test_db.commit()

        # Act
        response = test_client.get("/api/rankings?limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["rankings"]) == 5

    def test_get_rankings_includes_sos(self, test_client: TestClient, test_db: Session):
        """Test that rankings include strength of schedule"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, is_active=True)

        team1 = TeamFactory(name="Alabama", elo_rating=1800.0)
        team2 = TeamFactory(name="Georgia", elo_rating=1750.0)

        # Create a game so team1 has SOS
        GameFactory(
            home_team=team1,
            away_team=team2,
            season=2024,
            is_processed=True
        )
        test_db.commit()

        # Act
        response = test_client.get("/api/rankings")

        # Assert
        assert response.status_code == 200
        data = response.json()

        alabama_rank = data["rankings"][0]
        assert "sos" in alabama_rank
        # SOS should be opponent's rating
        assert alabama_rank["sos"] > 0

    def test_get_rankings_specific_season(self, test_client: TestClient, test_db: Session):
        """Test getting rankings for a specific season"""
        # Arrange
        configure_factories(test_db)
        season_2024 = SeasonFactory(year=2024, is_active=True)
        season_2023 = SeasonFactory(year=2023, is_active=False)

        team = TeamFactory(elo_rating=1800.0)
        test_db.commit()

        # Act
        response = test_client.get("/api/rankings?season=2023")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2023

    def test_get_rankings_includes_conference(self, test_client: TestClient, test_db: Session):
        """Test that rankings include conference information"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, is_active=True)

        team = TeamFactory(name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1800.0)
        test_db.commit()

        # Act
        response = test_client.get("/api/rankings")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["rankings"][0]["conference"] == "P5"


@pytest.mark.integration
class TestGetRankingHistory:
    """Tests for GET /api/rankings/history endpoint"""

    def test_get_ranking_history_success(self, test_client: TestClient, test_db: Session):
        """Test getting ranking history for a team"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory(name="Alabama")

        # Create history for multiple weeks
        for week in range(1, 6):
            RankingHistoryFactory(
                team=team,
                season=2024,
                week=week,
                rank=week,
                elo_rating=1800.0 + week * 10
            )
        test_db.commit()

        # Act
        response = test_client.get(f"/api/rankings/history?team_id={team.id}&season=2024")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Verify sorted by week
        assert data[0]["week"] == 1
        assert data[4]["week"] == 5

    def test_get_ranking_history_empty(self, test_client: TestClient, test_db: Session):
        """Test getting history when none exists"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory()
        test_db.commit()

        # Act
        response = test_client.get(f"/api/rankings/history?team_id={team.id}&season=2024")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_ranking_history_specific_season(self, test_client: TestClient, test_db: Session):
        """Test getting history for specific season only"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory()

        # Create history for different seasons
        RankingHistoryFactory(team=team, season=2024, week=1)
        RankingHistoryFactory(team=team, season=2023, week=1)
        test_db.commit()

        # Act
        response = test_client.get(f"/api/rankings/history?team_id={team.id}&season=2024")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["season"] == 2024


@pytest.mark.integration
class TestSaveRankings:
    """Tests for POST /api/rankings/save endpoint"""

    def test_save_rankings_success(self, test_client: TestClient, test_db: Session):
        """Test saving current rankings to history"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, current_week=5)

        team1 = TeamFactory(name="Alabama", elo_rating=1850.0, wins=5, losses=0)
        team2 = TeamFactory(name="Georgia", elo_rating=1840.0, wins=4, losses=1)
        test_db.commit()

        # Act
        response = test_client.post("/api/rankings/save?season=2024&week=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Rankings saved" in data["message"]
        assert data["data"]["season"] == 2024
        assert data["data"]["week"] == 5

        # Verify history was created
        history = test_db.query(RankingHistory).filter(
            RankingHistory.season == 2024,
            RankingHistory.week == 5
        ).all()
        assert len(history) == 2

    def test_save_rankings_creates_history_records(self, test_client: TestClient, test_db: Session):
        """Test that save creates proper history records"""
        # Arrange
        configure_factories(test_db)
        team = TeamFactory(name="Alabama", elo_rating=1850.0, wins=5, losses=0)
        test_db.commit()

        # Act
        response = test_client.post("/api/rankings/save?season=2024&week=5")

        # Assert
        assert response.status_code == 200

        # Verify history record
        history = test_db.query(RankingHistory).filter(
            RankingHistory.team_id == team.id,
            RankingHistory.season == 2024,
            RankingHistory.week == 5
        ).first()

        assert history is not None
        assert history.elo_rating == 1850.0
        assert history.wins == 5
        assert history.losses == 0


@pytest.mark.integration
class TestGetSeasons:
    """Tests for GET /api/seasons endpoint"""

    def test_get_seasons_empty(self, test_client: TestClient, test_db: Session):
        """Test getting seasons when none exist"""
        # Act
        response = test_client.get("/api/seasons")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_seasons_returns_all(self, test_client: TestClient, test_db: Session):
        """Test getting all seasons"""
        # Arrange
        configure_factories(test_db)
        season1 = SeasonFactory(year=2024, is_active=True)
        season2 = SeasonFactory(year=2023, is_active=False)
        season3 = SeasonFactory(year=2022, is_active=False)
        test_db.commit()

        # Act
        response = test_client.get("/api/seasons")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_seasons_sorted_desc(self, test_client: TestClient, test_db: Session):
        """Test that seasons are sorted by year descending"""
        # Arrange
        configure_factories(test_db)
        SeasonFactory(year=2022)
        SeasonFactory(year=2024)
        SeasonFactory(year=2023)
        test_db.commit()

        # Act
        response = test_client.get("/api/seasons")

        # Assert
        assert response.status_code == 200
        data = response.json()
        years = [s["year"] for s in data]
        assert years == [2024, 2023, 2022]

    def test_get_seasons_includes_metadata(self, test_client: TestClient, test_db: Session):
        """Test that seasons include all metadata"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024, current_week=5, is_active=True)
        test_db.commit()

        # Act
        response = test_client.get("/api/seasons")

        # Assert
        assert response.status_code == 200
        data = response.json()[0]
        assert data["year"] == 2024
        assert data["current_week"] == 5
        assert data["is_active"] is True
        assert "created_at" in data
        assert "updated_at" in data


@pytest.mark.integration
class TestCreateSeason:
    """Tests for POST /api/seasons endpoint"""

    def test_create_season_success(self, test_client: TestClient, test_db: Session):
        """Test creating a new season"""
        # Act
        response = test_client.post("/api/seasons?year=2025")

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["year"] == 2025
        assert data["current_week"] == 0
        assert data["is_active"] is True

        # Verify persisted to database
        season = test_db.query(Season).filter(Season.year == 2025).first()
        assert season is not None

    def test_create_season_duplicate_fails(self, test_client: TestClient, test_db: Session):
        """Test that creating duplicate season fails"""
        # Arrange
        configure_factories(test_db)
        SeasonFactory(year=2024)
        test_db.commit()

        # Act
        response = test_client.post("/api/seasons?year=2024")

        # Assert
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_season_defaults(self, test_client: TestClient, test_db: Session):
        """Test that new season has correct defaults"""
        # Act
        response = test_client.post("/api/seasons?year=2025")

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["current_week"] == 0
        assert data["is_active"] is True


@pytest.mark.integration
class TestResetSeason:
    """Tests for POST /api/seasons/{year}/reset endpoint"""

    def test_reset_season_success(self, test_client: TestClient, test_db: Session):
        """Test resetting a season recalculates team ratings"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024)

        # Create teams with preseason factors
        team = TeamFactory(
            name="Alabama",
            recruiting_rank=5,
            transfer_rank=10,
            returning_production=0.75,
            elo_rating=1600.0,  # Some rating from previous season
            initial_rating=1600.0
        )
        test_db.commit()

        # Act
        response = test_client.post("/api/seasons/2024/reset")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "reset successfully" in data["message"].lower()
        assert data["data"]["year"] == 2024

        # Verify team rating was recalculated based on preseason factors
        test_db.refresh(team)
        # Rating should be recalculated from preseason factors, not kept at 1600
        # Base (1500) + recruiting bonus + transfer bonus + returning production
        assert team.elo_rating != 1600.0
        assert team.initial_rating == team.elo_rating

    def test_reset_season_resets_records(self, test_client: TestClient, test_db: Session):
        """Test that reset clears wins/losses"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024)

        team = TeamFactory(
            wins=5,
            losses=2,
            recruiting_rank=50,
            transfer_rank=50,
            returning_production=0.5
        )
        test_db.commit()

        # Act
        response = test_client.post("/api/seasons/2024/reset")

        # Assert
        assert response.status_code == 200

        # Verify wins/losses reset
        test_db.refresh(team)
        assert team.wins == 0
        assert team.losses == 0

    def test_reset_season_multiple_teams(self, test_client: TestClient, test_db: Session):
        """Test that reset affects all teams"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2024)

        team1 = TeamFactory(wins=5, losses=2, recruiting_rank=5)
        team2 = TeamFactory(wins=3, losses=4, recruiting_rank=10)
        team3 = TeamFactory(wins=8, losses=1, recruiting_rank=1)
        test_db.commit()

        # Act
        response = test_client.post("/api/seasons/2024/reset")

        # Assert
        assert response.status_code == 200

        # Verify all teams reset
        test_db.refresh(team1)
        test_db.refresh(team2)
        test_db.refresh(team3)

        assert team1.wins == 0 and team1.losses == 0
        assert team2.wins == 0 and team2.losses == 0
        assert team3.wins == 0 and team3.losses == 0


@pytest.mark.integration
class TestGetActiveSeason:
    """Tests for GET /api/seasons/active endpoint"""

    def test_get_active_season_success(self, test_client: TestClient, test_db: Session):
        """Test active season endpoint with valid data"""
        # Arrange
        configure_factories(test_db)
        season = SeasonFactory(year=2025, current_week=8, is_active=True)
        test_db.commit()

        # Act
        response = test_client.get("/api/seasons/active")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2025
        assert data["current_week"] == 8
        assert data["is_active"] is True

    def test_get_active_season_not_found(self, test_client: TestClient, test_db: Session):
        """Test active season endpoint with no active season"""
        # Arrange
        configure_factories(test_db)
        # No active season in database

        # Act
        response = test_client.get("/api/seasons/active")

        # Assert
        assert response.status_code == 404
        assert "No active season found" in response.json()["detail"]

    def test_get_active_season_multiple_active(self, test_client: TestClient, test_db: Session):
        """Test returns most recent when multiple active seasons exist"""
        # Arrange
        configure_factories(test_db)
        season_2024 = SeasonFactory(year=2024, current_week=15, is_active=True)
        season_2025 = SeasonFactory(year=2025, current_week=8, is_active=True)
        test_db.commit()

        # Act
        response = test_client.get("/api/seasons/active")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2025  # Returns most recent
        assert data["current_week"] == 8

    def test_get_active_season_inactive_season_ignored(self, test_client: TestClient, test_db: Session):
        """Test inactive seasons are ignored"""
        # Arrange
        configure_factories(test_db)
        season_inactive = SeasonFactory(year=2023, is_active=False)
        season_active = SeasonFactory(year=2025, current_week=5, is_active=True)
        test_db.commit()

        # Act
        response = test_client.get("/api/seasons/active")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2025
        assert data["current_week"] == 5
