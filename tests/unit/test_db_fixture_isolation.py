"""Guards the per-test isolation of the `test_db` fixture.

The fixture used to hand every test the same process-wide
"file::memory:?cache=shared" database and rely on drop_all to clean it. That
drop raced the session-scoped E2E server thread ("database table is locked:
sqlite_master"), and a half-finished drop left rows behind, so the next test to
seed a season died with "UNIQUE constraint failed: seasons.year".

Each test now gets a privately named in-memory database and there is no
drop_all, so these two tests only pass while that isolation holds: a shared
name would carry the first season into the second test.
"""

from src.models.models import Season


def test_seeds_a_season(test_db):
    test_db.add(Season(year=2024, current_week=5, is_active=True))
    test_db.commit()

    assert test_db.query(Season).count() == 1


def test_seeds_the_same_season_again(test_db):
    # Year is unique. Leakage from the test above shows up here as an
    # IntegrityError rather than a silent extra row.
    test_db.add(Season(year=2024, current_week=9, is_active=True))
    test_db.commit()

    seasons = test_db.query(Season).all()
    assert len(seasons) == 1
    assert seasons[0].current_week == 9
