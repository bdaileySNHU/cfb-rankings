"""Regression tests for weekly ranking snapshots.

save_weekly_rankings() writes the CURRENT teams-table ratings under the week it
is given. Three call sites used to loop it over every completed week, which
overwrote all prior snapshots with today's numbers and flattened the recorded
history — rank movement went to zero and the team ELO charts became straight
lines. These tests pin down that behaviour so the loop cannot come back.
"""

import pytest

from src.core.ranking_service import RankingService
from src.models.models import ConferenceType, RankingHistory, Team


@pytest.fixture
def teams(test_db):
    """Three FBS teams with distinct ratings."""
    created = []
    for name, elo in [("Alpha", 1800.0), ("Bravo", 1700.0), ("Charlie", 1600.0)]:
        team = Team(
            name=name,
            conference=ConferenceType.POWER_5,
            conference_name="Test",
            is_fcs=False,
            elo_rating=elo,
        )
        test_db.add(team)
        created.append(team)
    test_db.commit()
    return created


def _ratings_for(db, season, week):
    """Return {team_id: elo} recorded for a season/week."""
    rows = db.query(RankingHistory).filter(
        RankingHistory.season == season, RankingHistory.week == week
    ).all()
    return {r.team_id: r.elo_rating for r in rows}


def test_snapshot_records_current_team_ratings(test_db, teams):
    """A snapshot captures the teams table as it stands at call time."""
    rs = RankingService(test_db)
    rs.save_weekly_rankings(season=2026, week=1)
    test_db.commit()

    recorded = _ratings_for(test_db, 2026, 1)
    assert recorded[teams[0].id] == 1800.0
    assert recorded[teams[1].id] == 1700.0


def test_resnapshotting_a_past_week_overwrites_it(test_db, teams):
    """The hazard itself: re-snapshotting an old week rewrites it with today's
    ratings. This is why call sites must only ever snapshot the current week."""
    rs = RankingService(test_db)

    rs.save_weekly_rankings(season=2026, week=1)
    test_db.commit()
    week1_original = _ratings_for(test_db, 2026, 1)

    # Ratings move as the season progresses.
    teams[0].elo_rating = 1500.0
    teams[2].elo_rating = 1900.0
    test_db.commit()

    rs.save_weekly_rankings(season=2026, week=1)
    test_db.commit()
    week1_now = _ratings_for(test_db, 2026, 1)

    assert week1_now != week1_original
    assert week1_now[teams[0].id] == 1500.0, "past week was rewritten with current ratings"


def test_snapshotting_current_week_leaves_history_intact(test_db, teams):
    """The fixed behaviour: snapshot only the latest week and earlier weeks keep
    the ratings that were true at the time."""
    rs = RankingService(test_db)

    rs.save_weekly_rankings(season=2026, week=1)
    test_db.commit()
    week1_original = _ratings_for(test_db, 2026, 1)

    teams[0].elo_rating = 1500.0
    teams[2].elo_rating = 1900.0
    test_db.commit()

    rs.save_weekly_rankings(season=2026, week=2)
    test_db.commit()

    assert _ratings_for(test_db, 2026, 1) == week1_original, "week 1 must not change"
    assert _ratings_for(test_db, 2026, 2)[teams[2].id] == 1900.0

    # And the two weeks must actually differ — that difference is what rank
    # movement and the ELO charts are computed from.
    assert _ratings_for(test_db, 2026, 1) != _ratings_for(test_db, 2026, 2)


def test_snapshot_is_idempotent_within_a_week(test_db, teams):
    """Re-running the weekly update the same day must not duplicate rows."""
    rs = RankingService(test_db)
    rs.save_weekly_rankings(season=2026, week=3)
    test_db.commit()
    rs.save_weekly_rankings(season=2026, week=3)
    test_db.commit()

    rows = test_db.query(RankingHistory).filter(
        RankingHistory.season == 2026, RankingHistory.week == 3
    ).all()
    assert len(rows) == len(teams)
