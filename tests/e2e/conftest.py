"""Shared seeding helper for the browser-driven E2E tests.

Since EPIC-024 the rankings board is served from ``ranking_history`` rows rather
than the ``teams`` table, so a test that only inserts ``Team`` records renders an
empty board no matter what ELO it set. ``seed_board`` inserts the season, the
teams, and the matching week snapshot together.
"""

import pytest

from src.models.models import RankingHistory, Season


@pytest.fixture
def seed_board(test_db):
    """Return a callable that seeds Team rows plus the ranking snapshot behind them.

    Usage:
        alabama = Team(name="Alabama", conference=ConferenceType.POWER_5, ...)
        seed_board(alabama)

    Ranks are assigned by ELO descending, matching what the ranking service
    would produce for a real week.
    """

    def _seed(*teams, year=2024, week=5):
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

        test_db.commit()
        return teams

    return _seed
