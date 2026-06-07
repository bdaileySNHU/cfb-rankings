"""Unit tests for CFBDClient.get_player_season_stats() (EPIC-040 Phase 2)."""

from unittest.mock import patch

import pytest

from src.integrations.cfbd_client import CFBDClient


@pytest.mark.unit
class TestGetPlayerSeasonStats:
    def _mock(self):
        return [
            {"playerId": "1", "player": "A", "position": "DL", "team": "Georgia",
             "category": "defensive", "statType": "SACKS", "stat": "8.0"},
            {"playerId": "1", "player": "A", "position": "DL", "team": "Georgia",
             "category": "defensive", "statType": "TOT", "stat": "40"},
        ]

    def test_successful_response(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=self._mock()):
            rows = client.get_player_season_stats(year=2024, category="defensive")
            assert len(rows) == 2
            assert rows[0]["playerId"] == "1"
            assert rows[0]["statType"] == "SACKS"

    def test_returns_empty_on_error(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=None):
            assert client.get_player_season_stats(year=2024) == []

    def test_params_and_endpoint(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_player_season_stats(year=2024, team="Georgia", category="defensive")
            assert mock_get.call_args[0][0] == "/stats/player/season"
            params = mock_get.call_args[1]["params"]
            assert params == {"year": 2024, "team": "Georgia", "category": "defensive"}

    def test_optional_params_omitted(self):
        client = CFBDClient()
        with patch.object(client, "_get", return_value=[]) as mock_get:
            client.get_player_season_stats(year=2024)
            params = mock_get.call_args[1]["params"]
            assert "team" not in params and "category" not in params
