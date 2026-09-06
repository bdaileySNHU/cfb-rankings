"""Unit tests for orientation-tolerant game lookup (duplicate-row bugfix).

CFBD reissues a matchup with the host and visitor swapped once a venue is
settled. Matching on the exact home/away pair inserted a second copy of the
game instead of updating the first, so 2026 week 1 carried both
"Notre Dame @ Wisconsin" and "Wisconsin @ Notre Dame".
"""

import pytest
from factories import GameFactory, TeamFactory, configure_factories
from sqlalchemy.orm import Session

from src.importers.common import find_existing_game
from src.models.models import Game


@pytest.mark.unit
class TestFindExistingGame:
    def test_matches_exact_orientation(self, test_db: Session):
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        game = GameFactory(home_team=home, away_team=away, week=3, season=2026)

        found = find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert found is not None and found.id == game.id

    def test_returns_none_for_unknown_matchup(self, test_db: Session):
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()

        assert find_existing_game(test_db, home.id, away.id, 3, 2026) is None

    def test_reuses_flipped_row_and_reorients_it(self, test_db: Session):
        """The flip must update the existing row, not insert a second one."""
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        # Stored the other way round, still scheduled.
        game = GameFactory(
            home_team=away,
            away_team=home,
            week=3,
            season=2026,
            home_score=0,
            away_score=0,
            is_processed=False,
        )

        found = find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert found is not None and found.id == game.id
        assert found.home_team_id == home.id
        assert found.away_team_id == away.id
        assert test_db.query(Game).count() == 1

    def test_reorienting_swaps_scores_and_quarters(self, test_db: Session):
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        GameFactory(
            home_team=away,
            away_team=home,
            week=3,
            season=2026,
            home_score=17,
            away_score=31,
            q1_home=7, q2_home=3, q3_home=7, q4_home=0,
            q1_away=14, q2_away=7, q3_away=3, q4_away=7,
            is_processed=False,
        )

        found = find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert (found.home_score, found.away_score) == (31, 17)
        assert (found.q1_home, found.q2_home, found.q3_home, found.q4_home) == (14, 7, 3, 7)
        assert (found.q1_away, found.q2_away, found.q3_away, found.q4_away) == (7, 3, 7, 0)

    def test_processed_row_is_left_alone(self, test_db: Session):
        """A scored game's rating changes are keyed to the sides it was scored with."""
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        game = GameFactory(
            home_team=away,
            away_team=home,
            week=3,
            season=2026,
            home_score=21,
            away_score=14,
            is_processed=True,
        )

        found = find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert found.id == game.id
        assert found.home_team_id == away.id
        assert (found.home_score, found.away_score) == (21, 14)

    def test_both_orientations_collapse_to_one_row(self, test_db: Session):
        """The duplicates already in the database heal on the next import."""
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        older = GameFactory(home_team=away, away_team=home, week=3, season=2026,
                            home_score=0, away_score=0, is_processed=False)
        newer = GameFactory(home_team=home, away_team=away, week=3, season=2026,
                            home_score=0, away_score=0, is_processed=False)

        found = find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert test_db.query(Game).count() == 1
        assert found.id == newer.id  # already facing the way the feed does
        assert test_db.query(Game).filter(Game.id == older.id).first() is None

    def test_processed_copy_survives_the_dedupe(self, test_db: Session):
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        scheduled = GameFactory(home_team=home, away_team=away, week=3, season=2026,
                                home_score=0, away_score=0, is_processed=False)
        played = GameFactory(home_team=away, away_team=home, week=3, season=2026,
                             home_score=28, away_score=10, is_processed=True)

        found = find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert found.id == played.id
        assert test_db.query(Game).filter(Game.id == scheduled.id).first() is None

    def test_other_weeks_are_untouched(self, test_db: Session):
        configure_factories(test_db)
        home, away = TeamFactory(), TeamFactory()
        GameFactory(home_team=home, away_team=away, week=3, season=2026)
        rematch = GameFactory(home_team=away, away_team=home, week=12, season=2026)

        find_existing_game(test_db, home.id, away.id, 3, 2026)

        assert test_db.query(Game).filter(Game.id == rematch.id).first() is not None
