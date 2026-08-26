"""Slate windowing: a CFB "week" is not a week, so predictions window by date."""

from datetime import date, datetime

import pytest

from src.core.ranking_service import next_slate_window
from src.models.models import Game, Team
from src.models.schemas import iso_utc


@pytest.fixture
def two_teams(db_session):
    home = Team(name="Home U", conference="P5")
    away = Team(name="Away U", conference="P5")
    db_session.add_all([home, away])
    db_session.commit()
    return home, away


def _game(home, away, when, week):
    return Game(
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=0,
        away_score=0,
        week=week,
        season=2026,
        game_date=when,
        is_processed=False,
    )


@pytest.fixture
def split_week_one(db_session, two_teams):
    """CFBD's real 2026 week 1: Aug 29-30, then a gap, then Sep 3-7."""
    home, away = two_teams
    days = ["2026-08-29 16:00", "2026-08-30 02:00",
            "2026-09-03 23:00", "2026-09-04 23:00", "2026-09-05 20:00",
            "2026-09-06 18:00", "2026-09-07 23:00",
            "2026-09-11 23:00", "2026-09-12 20:00"]
    weeks = [1, 1, 1, 1, 1, 1, 1, 2, 2]
    db_session.add_all(
        _game(home, away, datetime.strptime(d, "%Y-%m-%d %H:%M"), w)
        for d, w in zip(days, weeks)
    )
    db_session.commit()


def test_opening_saturday_is_its_own_slate(db_session, split_week_one):
    """Week 1 spans nine days; the opener must not drag the Labor Day games in."""
    week, start, end = next_slate_window(db_session, 2026, today=date(2026, 8, 26))
    assert week == 1
    assert start == datetime(2026, 8, 29)
    assert end == datetime(2026, 8, 31)


def test_slate_stays_live_on_its_final_day(db_session, split_week_one):
    _, start, _ = next_slate_window(db_session, 2026, today=date(2026, 8, 30))
    assert start == datetime(2026, 8, 29)


def test_advances_once_the_slate_is_over(db_session, split_week_one):
    week, start, end = next_slate_window(db_session, 2026, today=date(2026, 8, 31))
    assert week == 1
    assert start == datetime(2026, 9, 3)
    assert end == datetime(2026, 9, 8)


def test_midweek_games_stay_with_their_saturday(db_session, split_week_one):
    """Week 2 opens Friday — a 2-3 day gap is normal and must not split a slate."""
    week, start, end = next_slate_window(db_session, 2026, today=date(2026, 9, 8))
    assert week == 2
    assert start == datetime(2026, 9, 11)
    assert end == datetime(2026, 9, 13)


def test_none_when_season_is_done(db_session, split_week_one):
    assert next_slate_window(db_session, 2026, today=date(2027, 1, 1)) is None


def test_none_when_nothing_is_dated(db_session, two_teams):
    home, away = two_teams
    db_session.add(_game(home, away, None, 1))
    db_session.commit()
    assert next_slate_window(db_session, 2026, today=date(2026, 8, 26)) is None


def test_iso_utc_marks_naive_datetimes_as_utc():
    """Bare ISO makes JS read a Saturday night kickoff as Sunday."""
    assert iso_utc(datetime(2026, 8, 30, 0, 0)) == "2026-08-30T00:00:00+00:00"
    assert iso_utc(None) is None
