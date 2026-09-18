"""parse_game_date must return naive UTC.

Game.game_date is a plain DateTime column, so rows come back from SQLite naive.
An aware return value made the importers' "has the kickoff moved?" comparison
always unequal, so every daily run rewrote every game date in the season.
"""

from datetime import datetime

from src.importers.common import parse_game_date


def test_returns_naive_utc():
    parsed = parse_game_date({"startDate": "2026-08-29T19:00:00.000Z"})
    assert parsed == datetime(2026, 8, 29, 19, 0)
    assert parsed.tzinfo is None


def test_non_utc_offset_is_converted_not_truncated():
    parsed = parse_game_date({"startDate": "2026-08-29T15:00:00.000-04:00"})
    assert parsed == datetime(2026, 8, 29, 19, 0)


def test_unchanged_date_compares_equal_to_stored_row():
    """The regression itself: stored naive == freshly parsed, so no rewrite."""
    stored = datetime(2026, 8, 29, 19, 0)  # as SQLite hands it back
    assert parse_game_date({"startDate": "2026-08-29T19:00:00.000Z"}) == stored


def test_missing_and_malformed_return_none():
    assert parse_game_date({}) is None
    assert parse_game_date({"startDate": "not a date"}) is None
