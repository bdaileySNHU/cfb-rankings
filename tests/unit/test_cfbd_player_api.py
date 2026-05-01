"""Unit Tests for CFBD Player API Client

Tests the get_recruiting_players() method of CFBDClient including:
- Successful API response parsing
- Error handling (HTTP 404, 500, timeout)
- Empty results handling
- Filtering by position and team
- Mock API responses following CFBD API schema

Part of Preseason Enhancement Epic - Story 1.2

CFBD API Schema Reference:
- Response: Array of recruit objects with fields:
  - athleteId (int): CFBD athlete identifier
  - name (str): Player full name
  - position (str): Position abbreviation
  - stars (int): Star rating 1-5
  - rating (float): Numerical recruiting rating
  - ranking (int): Overall national ranking
  - committedTo (str): Team name
  - year (int): Recruiting class year
"""

from unittest.mock import Mock, patch

import pytest

from src.integrations.cfbd_client import CFBDClient


@pytest.mark.unit
class TestGetRecruitingPlayers:
    """Tests for get_recruiting_players() method"""

    def test_successful_api_response(self):
        """Test parsing successful API response with player data"""
        client = CFBDClient()

        # Mock response matching CFBD API schema
        mock_players = [
            {
                "id": 1,
                "athleteId": 12345,
                "name": "John Smith",
                "position": "QB",
                "stars": 5,
                "rating": 98.5,
                "ranking": 3,
                "committedTo": "Georgia",
                "year": 2024,
                "school": "IMG Academy",
                "city": "Bradenton",
                "state": "FL",
                "height": "6-3",
                "weight": 215,
            },
            {
                "id": 2,
                "athleteId": 67890,
                "name": "Mike Johnson",
                "position": "OL",
                "stars": 4,
                "rating": 92.3,
                "ranking": 45,
                "committedTo": "Georgia",
                "year": 2024,
                "school": "Grayson High School",
                "city": "Loganville",
                "state": "GA",
                "height": "6-5",
                "weight": 305,
            },
        ]

        with patch.object(client, "_get", return_value=mock_players):
            players = client.get_recruiting_players(year=2024, team="Georgia")

            assert len(players) == 2
            assert players[0]["name"] == "John Smith"
            assert players[0]["position"] == "QB"
            assert players[0]["stars"] == 5
            assert players[1]["position"] == "OL"
            assert players[1]["stars"] == 4

    def test_api_returns_none_on_error(self):
        """Test handling when API call fails (returns None)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=None):
            players = client.get_recruiting_players(year=2024, team="Georgia")

            # Should return empty list on error
            assert players == []
            assert isinstance(players, list)

    def test_empty_results_handling(self):
        """Test handling empty results from API (team with no recruits)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]):
            players = client.get_recruiting_players(year=2024, team="UnknownTeam")

            assert players == []
            assert isinstance(players, list)

    def test_filter_by_position(self):
        """Test filtering players by position"""
        client = CFBDClient()

        mock_qbs = [
            {
                "athleteId": 111,
                "name": "QB One",
                "position": "QB",
                "stars": 5,
                "rating": 98.0,
                "committedTo": "Alabama",
                "year": 2024,
            },
            {
                "athleteId": 222,
                "name": "QB Two",
                "position": "QB",
                "stars": 4,
                "rating": 95.0,
                "committedTo": "Georgia",
                "year": 2024,
            },
        ]

        with patch.object(client, "_get", return_value=mock_qbs) as mock_get:
            players = client.get_recruiting_players(year=2024, position="QB")

            # Verify _get was called with position parameter
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["position"] == "QB"

            # Verify results
            assert len(players) == 2
            assert all(p["position"] == "QB" for p in players)

    def test_filter_by_team_and_position(self):
        """Test filtering by both team and position"""
        client = CFBDClient()

        mock_players = [
            {
                "athleteId": 333,
                "name": "Georgia QB",
                "position": "QB",
                "stars": 5,
                "committedTo": "Georgia",
                "year": 2024,
            }
        ]

        with patch.object(client, "_get", return_value=mock_players) as mock_get:
            players = client.get_recruiting_players(year=2024, team="Georgia", position="QB")

            # Verify parameters passed correctly
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["team"] == "Georgia"
            assert params["position"] == "QB"
            assert params["year"] == 2024
            assert params["classification"] == "HighSchool"

            assert len(players) == 1
            assert players[0]["committedTo"] == "Georgia"
            assert players[0]["position"] == "QB"

    def test_default_classification_highschool(self):
        """Test that classification defaults to HighSchool"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_recruiting_players(year=2024)

            # Verify classification parameter
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["classification"] == "HighSchool"

    def test_custom_classification(self):
        """Test specifying custom classification (JUCO, PrepSchool)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_recruiting_players(year=2024, classification="JUCO")

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["classification"] == "JUCO"

    def test_multiple_recruiting_years(self):
        """Test fetching players from different recruiting years"""
        client = CFBDClient()

        # Year 2023
        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_recruiting_players(year=2023)
            call_args = mock_get.call_args
            assert call_args[1]["params"]["year"] == 2023

        # Year 2024
        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_recruiting_players(year=2024)
            call_args = mock_get.call_args
            assert call_args[1]["params"]["year"] == 2024

    def test_endpoint_path(self):
        """Test that correct API endpoint is called"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_recruiting_players(year=2024)

            # Verify endpoint path
            call_args = mock_get.call_args
            assert call_args[0][0] == "/recruiting/players"

    def test_players_with_missing_optional_fields(self):
        """Test handling players with missing optional fields (stars, rating, ranking)"""
        client = CFBDClient()

        mock_players = [
            {
                "athleteId": 444,
                "name": "Unranked Player",
                "position": "WR",
                "committedTo": "Some Team",
                "year": 2024,
                # Missing: stars, rating, ranking
            }
        ]

        with patch.object(client, "_get", return_value=mock_players):
            players = client.get_recruiting_players(year=2024)

            assert len(players) == 1
            assert players[0]["name"] == "Unranked Player"
            assert "stars" not in players[0] or players[0].get("stars") is None

    def test_five_star_players_only(self):
        """Test filtering to 5-star players (application-level filter example)"""
        client = CFBDClient()

        mock_players = [
            {"athleteId": 1, "name": "5 Star", "position": "QB", "stars": 5, "year": 2024},
            {"athleteId": 2, "name": "4 Star", "position": "RB", "stars": 4, "year": 2024},
            {"athleteId": 3, "name": "5 Star", "position": "WR", "stars": 5, "year": 2024},
        ]

        with patch.object(client, "_get", return_value=mock_players):
            all_players = client.get_recruiting_players(year=2024)

            # Application-level filtering (not API-level)
            five_stars = [p for p in all_players if p.get("stars") == 5]

            assert len(five_stars) == 2
            assert all(p["stars"] == 5 for p in five_stars)

    def test_large_dataset_handling(self):
        """Test handling large dataset (many players)"""
        client = CFBDClient()

        # Simulate 85 players for a full recruiting class
        mock_players = [
            {
                "athleteId": 10000 + i,
                "name": f"Player {i}",
                "position": "OL",
                "stars": 3 + (i % 3),
                "year": 2024,
            }
            for i in range(85)
        ]

        with patch.object(client, "_get", return_value=mock_players):
            players = client.get_recruiting_players(year=2024, team="Alabama")

            assert len(players) == 85
            assert all(isinstance(p["athleteId"], int) for p in players)

    def test_api_usage_tracking(self):
        """Test that API calls are tracked via _get decorator"""
        client = CFBDClient()

        # The _get method has @track_api_usage decorator
        # When we call get_recruiting_players, it should invoke _get which triggers tracking

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_recruiting_players(year=2024, team="Georgia")

            # Verify _get was called (which has tracking)
            mock_get.assert_called_once()
            # The actual API usage tracking happens in the _get decorator
            # This test confirms the method goes through _get

    def test_position_abbreviations(self):
        """Test various position abbreviations used in college football"""
        client = CFBDClient()

        positions = ["QB", "RB", "WR", "TE", "OL", "OT", "OG", "C", "DL", "DT", "DE", "LB", "DB", "CB", "S", "K", "P"]

        for pos in positions:
            mock_players = [
                {
                    "athleteId": 500 + positions.index(pos),
                    "name": f"Player {pos}",
                    "position": pos,
                    "stars": 3,
                    "year": 2024,
                }
            ]

            with patch.object(client, "_get", return_value=mock_players):
                players = client.get_recruiting_players(year=2024, position=pos)

                assert len(players) == 1
                assert players[0]["position"] == pos
