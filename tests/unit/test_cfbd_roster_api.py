"""Unit Tests for CFBD Roster API Client

Tests the get_roster() method of CFBDClient including:
- Successful API response parsing
- Error handling (API returns None)
- Empty results handling
- Parameter passing (team, year)
- Correct endpoint path

Part of EPIC-039 (Roster-Based Position Strength) - Story 39.1

CFBD API Schema Reference:
- Response: Array of roster player objects with fields:
  - id (str): CFBD athlete identifier (joins to recruiting athleteId)
  - firstName, lastName (str): Player name
  - team (str): Team name
  - position (str): Position abbreviation
  - year (int): Class year (1=FR, 2=SO, 3=JR, 4=SR)
  - recruitIds (list): Linked recruiting record IDs
"""

from unittest.mock import patch

import pytest

from src.integrations.cfbd_client import CFBDClient


@pytest.mark.unit
class TestGetRoster:
    """Tests for get_roster() method"""

    def _mock_roster(self):
        return [
            {
                "id": "4432738",
                "firstName": "Micah",
                "lastName": "Morris",
                "team": "Georgia",
                "position": "OL",
                "year": 4,
                "jersey": 56,
                "recruitIds": ["115808"],
            },
            {
                "id": "5141464",
                "firstName": "Elijah",
                "lastName": "Griffin",
                "team": "Georgia",
                "position": "DL",
                "year": 1,
                "recruitIds": ["106194"],
            },
            {
                "id": "9999999",
                "firstName": "Walk",
                "lastName": "On",
                "team": "Georgia",
                "position": "WR",
                "year": 2,
                "recruitIds": [],
            },
        ]

    def test_successful_api_response(self):
        """Test parsing a successful roster response"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=self._mock_roster()):
            roster = client.get_roster(team="Georgia", year=2025)

            assert len(roster) == 3
            assert roster[0]["id"] == "4432738"
            assert roster[0]["position"] == "OL"
            assert roster[0]["year"] == 4
            assert roster[1]["recruitIds"] == ["106194"]

    def test_api_returns_none_on_error(self):
        """Test handling when API call fails (returns None)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=None):
            roster = client.get_roster(team="Georgia", year=2025)

            assert roster == []
            assert isinstance(roster, list)

    def test_empty_results_handling(self):
        """Test handling empty results (unknown team/year)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]):
            roster = client.get_roster(team="UnknownTeam", year=2025)

            assert roster == []
            assert isinstance(roster, list)

    def test_params_passed(self):
        """Test that team and year are passed as params"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_roster(team="Georgia", year=2025)

            params = mock_get.call_args[1]["params"]
            assert params["team"] == "Georgia"
            assert params["year"] == 2025

    def test_omits_unset_params(self):
        """Test that unset filters are omitted (no team/year keys)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_roster()

            params = mock_get.call_args[1]["params"]
            assert "team" not in params
            assert "year" not in params

    def test_endpoint_path(self):
        """Test that the correct endpoint is called"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_roster(team="Georgia", year=2025)

            assert mock_get.call_args[0][0] == "/roster"

    def test_api_usage_tracking(self):
        """Test that the call routes through _get (which tracks usage)"""
        client = CFBDClient()

        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_roster(team="Georgia", year=2025)

            mock_get.assert_called_once()
