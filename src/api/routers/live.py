"""Live game data from the CFBD scoreboard.

Fetched on demand and cached in a file so all gunicorn workers share one
CFBD call per minute. Nothing is written to the database: in-progress
scores must never reach the ELO path.
"""
import json
import logging
import os
import tempfile
import time

from fastapi import APIRouter

from src.integrations.cfbd_client import CFBDClient

logger = logging.getLogger(__name__)
router = APIRouter()

CACHE_DIR = tempfile.gettempdir()
SCOREBOARD_TTL = 60  # CFBD refreshes about once a minute
TEAMS_TTL = 24 * 3600


def _cached(name: str, ttl: int, fetch):
    """Return the cached JSON for ``name`` if fresh, else refetch.

    A failed or empty fetch serves the stale copy (or [] if none) so a CFBD
    outage never breaks the page.
    """
    path = os.path.join(CACHE_DIR, f"cfb-{name}.json")
    try:
        if time.time() - os.path.getmtime(path) < ttl:
            with open(path) as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    # ponytail: workers can race at expiry and each refetch, at most a few
    # extra calls a minute. Add a flock if quota ever gets tight.
    try:
        data = fetch()
    except Exception:
        logger.exception("CFBD %s fetch failed", name)
        data = None
    if data:
        fd, tmp = tempfile.mkstemp(dir=CACHE_DIR)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
        return data
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _team_names() -> dict:
    teams = _cached("teams", TEAMS_TTL, lambda: [
        {"id": t["id"], "school": t["school"]} for t in CFBDClient().get_all_teams()
    ])
    return {t["id"]: t["school"] for t in teams}


def _slim(game: dict, names: dict) -> dict:
    home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
    betting = game.get("betting") or {}
    weather = game.get("weather") or {}
    return {
        "home": names.get(home.get("id"), home.get("name")),
        "away": names.get(away.get("id"), away.get("name")),
        "status": game.get("status"),
        "start_date": game.get("startDate"),
        "period": game.get("period"),
        "clock": game.get("clock"),
        "situation": game.get("situation"),
        "possession": game.get("possession"),
        "last_play": game.get("lastPlay"),
        "home_points": home.get("points"),
        "away_points": away.get("points"),
        "home_line_scores": home.get("lineScores") or [],
        "away_line_scores": away.get("lineScores") or [],
        "home_win_prob": home.get("winProbability"),
        "spread": betting.get("spread"),
        "over_under": betting.get("overUnder"),
        "home_ml": betting.get("homeMoneyline"),
        "away_ml": betting.get("awayMoneyline"),
        "weather": {
            "temperature": weather.get("temperature"),
            "description": weather.get("description"),
            "wind_speed": weather.get("windSpeed"),
        } if weather else None,
        "tv": game.get("tv"),
        "venue": (game.get("venue") or {}).get("name"),
        "neutral_site": game.get("neutralSite"),
    }


@router.get("/api/live", tags=["Games"])
def get_live():
    """Today's FBS slate with live status, clock, situation and lines.

    Team names are mapped to our school names so the frontend can match
    games by (home, away).
    """
    board = _cached("scoreboard", SCOREBOARD_TTL, lambda: CFBDClient().get_scoreboard())
    if not board:
        return []
    names = _team_names()
    return [_slim(g, names) for g in board]
