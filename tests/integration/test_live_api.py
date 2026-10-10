"""GET /api/live: shared file cache, name mapping, CFBD-failure fallback."""

import os
from unittest.mock import MagicMock

import pytest

from src.api.routers import live

GAME = {
    "status": "in_progress", "period": 4, "clock": "07:22", "situation": "2nd & 4 at FLA 31",
    "possession": "home", "lastPlay": "pass complete", "startDate": "2026-10-10T16:45:00.000Z",
    "tv": "SECN", "neutralSite": False, "venue": {"name": "Ben Hill Griffin Stadium"},
    "homeTeam": {"id": 57, "name": "Florida Gators", "points": 13, "lineScores": [7, 3, 3, 0],
                 "winProbability": 0.004},
    "awayTeam": {"id": 2579, "name": "South Carolina Gamecocks", "points": 38,
                 "lineScores": [7, 10, 14, 7], "winProbability": 0.996},
    "weather": {"temperature": 76.5, "description": "Heavy Rain", "windSpeed": 10.3},
    "betting": {"spread": -10.5, "overUnder": 59.5, "homeMoneyline": -490, "awayMoneyline": 355},
}


@pytest.fixture
def cfbd(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "CACHE_DIR", str(tmp_path))
    client = MagicMock()
    client.get_scoreboard.return_value = [GAME]
    client.get_all_teams.return_value = [{"id": 57, "school": "Florida"},
                                         {"id": 2579, "school": "South Carolina"}]
    monkeypatch.setattr(live, "CFBDClient", lambda: client)
    return client


@pytest.mark.integration
def test_maps_mascot_names_to_schools_and_flattens(test_client, cfbd):
    [g] = test_client.get("/api/live").json()
    assert (g["home"], g["away"]) == ("Florida", "South Carolina")
    assert (g["away_points"], g["clock"], g["over_under"]) == (38, "07:22", 59.5)
    assert g["home_line_scores"] == [7, 3, 3, 0]
    assert g["weather"]["description"] == "Heavy Rain"


@pytest.mark.integration
def test_one_cfbd_call_per_minute(test_client, cfbd):
    test_client.get("/api/live")
    test_client.get("/api/live")
    assert cfbd.get_scoreboard.call_count == 1


@pytest.mark.integration
def test_cfbd_failure_serves_stale_then_empty(test_client, cfbd, tmp_path):
    test_client.get("/api/live")
    # Age the cache past its TTL, then have CFBD fail.
    path = tmp_path / "cfb-scoreboard.json"
    os.utime(path, (0, 0))
    cfbd.get_scoreboard.return_value = []
    assert test_client.get("/api/live").json()[0]["home"] == "Florida"

    path.unlink()
    cfbd.get_scoreboard.side_effect = RuntimeError("down")
    assert test_client.get("/api/live").json() == []
