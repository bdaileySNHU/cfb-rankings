"""weekly_update.sh sends its success message only from the run that closes a week.

Game day has five cron slots that can each process finals, and each used to
send the same growing big-movers list: up to five near-identical messages.
"""

from datetime import datetime

from src.models.models import ConferenceType, Game, Team, week_is_complete

NOW = datetime(2026, 9, 27, 4, 45)  # Sunday 04:45 UTC slot


def _game(db, kickoff, processed):
    home = Team(name=f"H{kickoff}", conference=ConferenceType.POWER_5, is_fcs=False)
    away = Team(name=f"A{kickoff}", conference=ConferenceType.POWER_5, is_fcs=False)
    db.add_all([home, away])
    db.flush()
    db.add(Game(home_team_id=home.id, away_team_id=away.id, home_score=0, away_score=0,
                week=4, season=2026, game_date=kickoff, is_processed=processed))
    db.commit()


def test_open_while_a_game_is_still_to_come(test_db):
    _game(test_db, datetime(2026, 9, 26, 16, 0), processed=True)
    _game(test_db, datetime(2026, 9, 27, 3, 30), processed=False)  # late Pacific game
    assert not week_is_complete(test_db, 2026, 4, NOW)


def test_closed_once_every_game_is_processed(test_db):
    _game(test_db, datetime(2026, 9, 26, 16, 0), processed=True)
    _game(test_db, datetime(2026, 9, 27, 3, 30), processed=True)
    assert week_is_complete(test_db, 2026, 4, NOW)


def test_a_postponed_game_does_not_hold_the_week_open(test_db):
    _game(test_db, datetime(2026, 9, 26, 16, 0), processed=True)
    _game(test_db, datetime(2026, 9, 25, 23, 0), processed=False)  # Friday, never played
    assert week_is_complete(test_db, 2026, 4, NOW)
