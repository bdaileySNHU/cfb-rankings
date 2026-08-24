"""Shared seeding helper for the browser-driven E2E tests.

Since EPIC-024 the rankings board is served from ``ranking_history`` rows rather
than the ``teams`` table, so a test that only inserts ``Team`` records renders an
empty board no matter what ELO it set. ``seed_board`` inserts the season, the
teams, and the matching week snapshot together.
"""

import json

import pytest

from src.models.models import PlayoffSimulation, RankingHistory, Season


@pytest.fixture
def seed_board(test_db):
    """Return a callable that seeds Team rows plus the ranking snapshot behind them.

    Usage:
        alabama = Team(name="Alabama", conference=ConferenceType.POWER_5, ...)
        seed_board(alabama)

    Ranks are assigned by ELO descending, matching what the ranking service
    would produce for a real week.

    Pass ``odds={"Alabama": {"bid_pct": 62.5, ...}}`` to also cache a playoff
    simulation for the same (year, week), keyed by team name because the ids
    do not exist until the flush below. The rankings endpoint only reads a
    simulation whose week matches the board's, so seeding both together is the
    point.
    """

    def _seed(*teams, year=2024, week=5, odds=None):
        test_db.add(Season(year=year, current_week=week, is_active=True))
        test_db.add_all(teams)
        test_db.flush()  # assign team ids

        for rank, team in enumerate(
            sorted(teams, key=lambda t: t.elo_rating, reverse=True), start=1
        ):
            test_db.add(
                RankingHistory(
                    team_id=team.id,
                    season=year,
                    week=week,
                    rank=rank,
                    elo_rating=team.elo_rating,
                    wins=team.wins,
                    losses=team.losses,
                )
            )

        if odds:
            payload = {"teams": [
                dict(odds[t.name], team_id=t.id, name=t.name)
                for t in teams if t.name in odds
            ]}
            test_db.add(PlayoffSimulation(
                season=year, week=week, runs=10, payload=json.dumps(payload)
            ))

        test_db.commit()
        return teams

    return _seed
