"""Unit tests for the has_been_played() query predicate.

Regression cover for the weekly-update log filling with ERROR_GAME lines: the
ELO step filtered unplayed games with ``home_score != None``, but both score
columns are NOT NULL and unplayed games are stored 0-0, so the filter excluded
nothing and handed every future game to process_game().
"""

import pytest
from sqlalchemy.orm import Session

from factories import GameFactory, TeamFactory, configure_factories
from src.models.models import Game, has_been_played


@pytest.mark.unit
class TestHasBeenPlayed:
    def _slate(self, test_db: Session):
        """One played game and two that have not kicked off."""
        configure_factories(test_db)
        played = GameFactory(
            home_team=TeamFactory(name="Ohio State"),
            away_team=TeamFactory(name="Michigan"),
            home_score=30,
            away_score=24,
            season=2026,
        )
        scheduled = GameFactory(
            home_team=TeamFactory(name="Navy"),
            away_team=TeamFactory(name="Army"),
            home_score=0,
            away_score=0,
            season=2026,
        )
        shutout = GameFactory(
            home_team=TeamFactory(name="Troy"),
            away_team=TeamFactory(name="Arkansas State"),
            home_score=21,
            away_score=0,
            season=2026,
        )
        test_db.commit()
        return played, scheduled, shutout

    def test_excludes_games_that_have_not_kicked_off(self, test_db: Session):
        played, scheduled, _ = self._slate(test_db)

        rows = test_db.query(Game).filter(has_been_played()).all()

        assert played in rows
        assert scheduled not in rows

    def test_keeps_a_shutout(self, test_db: Session):
        """A 21-0 result is played; only 0-0 means "no result yet"."""
        _, _, shutout = self._slate(test_db)

        rows = test_db.query(Game).filter(has_been_played()).all()

        assert shutout in rows

    def test_is_not_a_null_check(self, test_db: Session):
        """The bug this replaces: IS NOT NULL matches every scheduled game.

        Both score columns are NOT NULL, so the old predicate could not filter
        anything. If someone reinstates it, this fails.
        """
        self._slate(test_db)

        null_check = (
            test_db.query(Game)
            .filter(Game.home_score != None, Game.away_score != None)  # noqa: E711
            .count()
        )
        played_check = test_db.query(Game).filter(has_been_played()).count()

        assert null_check == 3, "NOT NULL columns: the null check excludes nothing"
        assert played_check == 2, "has_been_played() must drop the 0-0 game"
