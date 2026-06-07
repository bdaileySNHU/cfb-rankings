"""Integration Tests for Player and Position Strength API Endpoints

Tests the new API endpoints added for the Preseason Enhancement Epic:
- GET /api/teams/{team_id}/players
- GET /api/teams/{team_id}/position-strength

Part of Preseason Enhancement Epic - Story 1.5
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.models.database import get_db
from src.models.models import ConferenceType, Player, RosterPlayer, Team


@pytest.fixture
def client(test_db: Session):
    """Create FastAPI test client wired to the test database"""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.integration
class TestTeamPlayersEndpoint:
    """Tests for GET /api/teams/{team_id}/players endpoint"""

    def test_get_players_for_team(self, client, test_db):
        """Test retrieving all players for a team"""
        # Create team
        team = Team(name="Georgia", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Add players
        for i in range(5):
            player = Player(
                cfbd_athlete_id=10000 + i,
                name=f"Player {i}",
                team_id=team.id,
                position="QB",
                stars=4 + (i % 2),
                rating=90.0 + i,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Call API
        response = client.get(f"/api/teams/{team.id}/players")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team.id
        assert data["team_name"] == "Georgia"
        assert data["total"] == 5
        assert len(data["players"]) == 5

    def test_get_players_with_recruiting_year_filter(self, client, test_db):
        """Test filtering players by recruiting year"""
        team = Team(name="Alabama", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add players from different years
        for year in [2023, 2024]:
            for i in range(3):
                player = Player(
                    cfbd_athlete_id=20000 + (year * 10) + i,
                    name=f"Player {year} {i}",
                    team_id=team.id,
                    position="QB",
                    rating=90.0,
                    recruiting_year=year,
                )
                test_db.add(player)
        test_db.commit()

        # Filter by 2024
        response = client.get(f"/api/teams/{team.id}/players?recruiting_year=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(p["recruiting_year"] == 2024 for p in data["players"])

    def test_get_players_with_position_filter(self, client, test_db):
        """Test filtering players by position"""
        team = Team(name="Clemson", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add players at different positions
        positions = ["QB", "QB", "OL", "OL", "DL"]
        for i, pos in enumerate(positions):
            player = Player(
                cfbd_athlete_id=30000 + i,
                name=f"Player {pos} {i}",
                team_id=team.id,
                position=pos,
                rating=85.0,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Filter by QB
        response = client.get(f"/api/teams/{team.id}/players?position=QB")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(p["position"] == "QB" for p in data["players"])

    def test_get_players_with_both_filters(self, client, test_db):
        """Test filtering by both recruiting year and position"""
        team = Team(name="Ohio State", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add diverse roster
        configs = [
            (2023, "QB"),
            (2024, "QB"),
            (2024, "QB"),
            (2024, "OL"),
        ]
        for i, (year, pos) in enumerate(configs):
            player = Player(
                cfbd_athlete_id=40000 + i,
                name=f"Player {year} {pos} {i}",
                team_id=team.id,
                position=pos,
                rating=88.0,
                recruiting_year=year,
            )
            test_db.add(player)
        test_db.commit()

        # Filter by 2024 QBs
        response = client.get(
            f"/api/teams/{team.id}/players?recruiting_year=2024&position=QB"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(p["recruiting_year"] == 2024 for p in data["players"])
        assert all(p["position"] == "QB" for p in data["players"])

    def test_get_players_pagination(self, client, test_db):
        """Test pagination parameters"""
        team = Team(name="Michigan", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add 10 players
        for i in range(10):
            player = Player(
                cfbd_athlete_id=50000 + i,
                name=f"Player {i}",
                team_id=team.id,
                position="OL",
                rating=80.0 + i,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Get first 5
        response = client.get(f"/api/teams/{team.id}/players?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["players"]) == 5

        # Get next 5
        response = client.get(f"/api/teams/{team.id}/players?skip=5&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["players"]) == 5

    def test_get_players_team_not_found(self, client, test_db):
        """Test 404 response when team doesn't exist"""
        response = client.get("/api/teams/99999/players")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_players_empty_roster(self, client, test_db):
        """Test team with no players returns empty list"""
        team = Team(name="Empty Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/players")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["players"]) == 0

    def test_players_ordered_by_rating(self, client, test_db):
        """Test that players are ordered by rating (best first)"""
        team = Team(name="Texas", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add players with varying ratings
        ratings = [85.0, 95.0, 80.0, 92.0, 88.0]
        for i, rating in enumerate(ratings):
            player = Player(
                cfbd_athlete_id=60000 + i,
                name=f"Player {i}",
                team_id=team.id,
                position="QB",
                rating=rating,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/players")

        assert response.status_code == 200
        data = response.json()
        players = data["players"]

        # Verify descending order
        ratings_returned = [p["rating"] for p in players if p["rating"] is not None]
        assert ratings_returned == sorted(ratings_returned, reverse=True)


@pytest.mark.integration
class TestTeamPositionStrengthEndpoint:
    """Tests for GET /api/teams/{team_id}/position-strength endpoint"""

    def test_get_position_strength_with_players(self, client, test_db):
        """Test position strength calculation for team with players"""
        team = Team(name="Georgia", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add diverse roster
        positions_ratings = [
            ("QB", 98.0),
            ("QB", 95.0),
            ("OL", 92.0),
            ("OL", 90.0),
            ("DL", 93.0),
            ("DB", 89.0),
            ("LB", 85.0),
        ]
        for i, (pos, rating) in enumerate(positions_ratings):
            player = Player(
                cfbd_athlete_id=70000 + i,
                name=f"Player {pos} {i}",
                team_id=team.id,
                position=pos,
                rating=rating,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/position-strength")

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team.id
        assert data["team_name"] == "Georgia"
        assert "enabled" in data
        assert "position_scores" in data
        assert "position_bonus" in data
        assert "max_bonus" in data
        assert "weights" in data
        assert data["recruiting_year"] == 2024

        # Verify position scores structure
        assert "QB" in data["position_scores"]
        assert "OL" in data["position_scores"]
        assert "DL" in data["position_scores"]

    def test_get_position_strength_no_players(self, client, test_db):
        """Test position strength for team with no players"""
        team = Team(name="Empty Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/position-strength")

        assert response.status_code == 200
        data = response.json()
        assert data["position_bonus"] == 0.0
        assert data["recruiting_year"] is None
        assert "No player data" in data.get("message", "")

    def test_position_strength_roster_source(self, client, test_db):
        """EPIC-039: with a roster snapshot, the endpoint reports source=roster"""
        team = Team(name="Reload State", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        for i, rating in enumerate([0.97, 0.95]):
            test_db.add(
                RosterPlayer(
                    season=2025,
                    team_id=team.id,
                    athlete_id=80000 + i,
                    name=f"QB {i}",
                    position="QB",
                    class_year=3,
                    rating=rating,
                    source="recruiting-join",
                    # blended_rating populated so the test is robust to the
                    # default config's blend flag (EPIC-040)
                    blended_rating=90.0 - i,
                )
            )
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/position-strength?season=2025")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "roster"
        assert data["season"] == 2025
        assert data["recruiting_year"] is None
        assert "blend" in data
        assert data["position_scores"]["QB"] > 0

    def test_position_strength_falls_back_to_recruiting(self, client, test_db):
        """EPIC-039: no roster snapshot → endpoint falls back to recruiting source"""
        team = Team(name="Fallback State", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        test_db.add(
            Player(
                cfbd_athlete_id=81000,
                name="Recruit QB",
                team_id=team.id,
                position="QB",
                rating=0.95,
                recruiting_year=2025,
            )
        )
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/position-strength?season=2025")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "recruiting"
        assert data["season"] is None
        assert data["recruiting_year"] == 2025

    def test_get_position_strength_with_year_filter(self, client, test_db):
        """Test specifying recruiting year parameter"""
        team = Team(name="Alabama", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add players from 2023
        player = Player(
            cfbd_athlete_id=80000,
            name="Player 2023",
            team_id=team.id,
            position="QB",
            rating=95.0,
            recruiting_year=2023,
        )
        test_db.add(player)
        test_db.commit()

        response = client.get(
            f"/api/teams/{team.id}/position-strength?recruiting_year=2023"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recruiting_year"] == 2023

    def test_get_position_strength_team_not_found(self, client, test_db):
        """Test 404 when team doesn't exist"""
        response = client.get("/api/teams/99999/position-strength")
        assert response.status_code == 404

    def test_position_strength_uses_most_recent_year(self, client, test_db):
        """Test that endpoint uses most recent recruiting year by default"""
        team = Team(name="Clemson", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add players from multiple years
        for year in [2022, 2023, 2024]:
            player = Player(
                cfbd_athlete_id=90000 + year,
                name=f"Player {year}",
                team_id=team.id,
                position="QB",
                rating=90.0,
                recruiting_year=year,
            )
            test_db.add(player)
        test_db.commit()

        response = client.get(f"/api/teams/{team.id}/position-strength")

        assert response.status_code == 200
        data = response.json()
        # Should use 2024 (most recent)
        assert data["recruiting_year"] == 2024
