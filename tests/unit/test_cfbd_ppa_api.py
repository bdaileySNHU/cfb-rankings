"""Unit Tests for CFBD Player PPA API Client

Tests get_player_ppa_season() of CFBDClient: response parsing, error handling,
parameter passing, and endpoint path.

Part of EPIC-040 (Production-Blended Position Strength) - Story 40.1
"""

from unittest.mock import patch

import pytest

from src.integrations.cfbd_client import CFBDClient


@pytest.mark.unit
class TestGetPlayerPpaSeason:
    """Tests for get_player_ppa_season() method"""

    def _mock_ppa(self):
        return [
            {
                "season": 2024,
                "id": "4429105",
                "name": "Arian Smith",
                "position": "WR",
                "team": "Georgia",
                "conference": "SEC",
                "averagePPA": {"all": 0.915},
                "totalPPA": {"all": 55.79},
            },
            {
                "season": 2024,
                "id": "5000001",
                "name": "Carson Beck",
                "position": "QB",
                "team": "Georgia",
                "averagePPA": {"all": 0.32},
                "totalPPA": {"all": 120.4},
            },
        ]

    def test_successful_response(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=self._mock_ppa()):
            ppa = client.get_player_ppa_season(year=2024, team="Georgia")
            assert len(ppa) == 2
            assert ppa[0]["id"] == "4429105"
            assert ppa[0]["averagePPA"]["all"] == 0.915

    def test_returns_empty_on_error(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=None):
            assert client.get_player_ppa_season(year=2024, team="Georgia") == []

    def test_empty_results(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=[]):
            assert client.get_player_ppa_season(year=2024) == []

    def test_params_and_endpoint(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_player_ppa_season(year=2024, team="Georgia")
            assert mock_get.call_args[0][0] == "/ppa/players/season"
            params = mock_get.call_args[1]["params"]
            assert params["year"] == 2024
            assert params["team"] == "Georgia"

    def test_team_omitted_when_unset(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_player_ppa_season(year=2024)
            assert "team" not in mock_get.call_args[1]["params"]
