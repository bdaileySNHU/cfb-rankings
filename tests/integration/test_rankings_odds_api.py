"""Integration tests for the Monte Carlo projection columns on /api/rankings.

The four numbers (BID% / CONF% / NAT% / PROJ W) come from the cached
``playoff_simulation`` row for the *exact* week being displayed. These tests
insert that row directly rather than running a simulation, which keeps them
fast and lets them cover payload shapes a real simulation never produces —
notably a row written before the ``teams`` key existed.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.models import (
    ConferenceType,
    PlayoffSimulation,
    RankingHistory,
    Season,
    Team,
)

ODDS = {"bid_pct": 62.5, "conf_title_pct": 21.4, "title_pct": 8.1, "proj_wins": 9.3}


def seed(db: Session, week: int = 5, season: int = 2024):
    """Two ranked teams in a season sitting at ``week``."""
    db.add(Season(year=season, current_week=week, is_active=True))
    teams = [
        Team(name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0),
        Team(name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1840.0),
    ]
    db.add_all(teams)
    db.flush()
    for rank, t in enumerate(teams, start=1):
        db.add(RankingHistory(
            team_id=t.id, season=season, week=week, rank=rank,
            elo_rating=t.elo_rating, wins=4, losses=1,
        ))
    db.commit()
    return teams


def store(db: Session, payload: dict, week: int = 5, season: int = 2024):
    db.add(PlayoffSimulation(
        season=season, week=week, runs=10, payload=json.dumps(payload)
    ))
    db.commit()


def entries(response):
    return {e["team_name"]: e for e in response.json()["rankings"]}


@pytest.mark.integration
class TestRankingsProjectionColumns:
    def test_odds_attached_for_matching_week(self, test_client: TestClient, test_db: Session):
        teams = seed(test_db)
        store(test_db, {"teams": [dict(ODDS, team_id=teams[0].id, name="Alabama")]})

        rows = entries(test_client.get("/api/rankings"))

        for key, value in ODDS.items():
            assert rows["Alabama"][key] == value

    def test_fields_present_and_null_without_a_simulation(
        self, test_client: TestClient, test_db: Session
    ):
        """The keys must survive the response model even when there is no data.

        RankingEntry is a plain pydantic model, so a field it does not declare is
        silently dropped. Asserting presence is what catches that.
        """
        seed(test_db)

        rows = entries(test_client.get("/api/rankings"))

        for key in ODDS:
            assert key in rows["Alabama"]
            assert rows["Alabama"][key] is None

    def test_simulation_from_another_week_is_not_shown(
        self, test_client: TestClient, test_db: Session
    ):
        """A week-8 simulation beside week-3 rankings would be quietly wrong."""
        teams = seed(test_db, week=8)
        # The same teams also have a week-3 snapshot, so week 3 renders a board.
        for rank, t in enumerate(teams, start=1):
            test_db.add(RankingHistory(
                team_id=t.id, season=2024, week=3, rank=rank,
                elo_rating=t.elo_rating, wins=2, losses=1,
            ))
        test_db.commit()
        store(test_db, {"teams": [dict(ODDS, team_id=teams[0].id, name="Alabama")]}, week=8)

        rows = entries(test_client.get("/api/rankings?week=3"))

        assert set(rows) == {"Alabama", "Georgia"}  # the board did render
        assert rows["Alabama"]["bid_pct"] is None
        assert entries(test_client.get("/api/rankings?week=8"))["Alabama"]["bid_pct"] == 62.5

    def test_team_missing_from_payload_gets_nulls(
        self, test_client: TestClient, test_db: Session
    ):
        teams = seed(test_db)
        store(test_db, {"teams": [dict(ODDS, team_id=teams[0].id, name="Alabama")]})

        rows = entries(test_client.get("/api/rankings"))

        assert rows["Alabama"]["bid_pct"] == ODDS["bid_pct"]
        assert rows["Georgia"]["bid_pct"] is None
        assert rows["Georgia"]["proj_wins"] is None

    def test_payload_without_teams_key_still_serves(
        self, test_client: TestClient, test_db: Session
    ):
        """Rows cached before this feature shipped have field/bubble only."""
        teams = seed(test_db)
        store(test_db, {
            "field": [dict(ODDS, team_id=teams[0].id, name="Alabama", seed=1)],
            "bubble": [],
        })

        response = test_client.get("/api/rankings")

        assert response.status_code == 200
        assert entries(response)["Alabama"]["bid_pct"] is None
