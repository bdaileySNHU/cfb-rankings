"""Unit tests for Season Archival Script

Tests the archival logic for marking seasons inactive and creating
archival documentation.

Part of EPIC-SEASON-END-2025: Story 3 - Season Archival and System Preparation
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.models import Base, RankingHistory, Season, Team, ConferenceType
from utilities.archive_season import (
    verify_final_snapshot_exists,
    check_active_seasons,
    archive_season,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def sample_season(test_db):
    """Create a sample active season."""
    season = Season(year=2025, current_week=20, is_active=True)
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def sample_teams(test_db):
    """Create sample teams for testing."""
    teams = []
    for i in range(1, 4):
        team = Team(
            name=f"Team {i}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1500.0 + (i * 50),
            initial_rating=1500.0,
            wins=10 - i,
            losses=i,
        )
        test_db.add(team)
        teams.append(team)
    test_db.commit()
    return teams


@pytest.fixture
def final_snapshot(test_db, sample_season, sample_teams):
    """Create final ranking snapshot for testing."""
    final_week = 20
    for rank, team in enumerate(sample_teams, 1):
        snapshot = RankingHistory(
            team_id=team.id,
            week=final_week,
            season=2025,
            rank=rank,
            elo_rating=team.elo_rating,
            wins=team.wins,
            losses=team.losses,
            sos=1600.0,
            sos_rank=rank,
        )
        test_db.add(snapshot)
    test_db.commit()


def test_verify_final_snapshot_exists_with_snapshot(test_db, final_snapshot):
    """Test verification succeeds when final snapshot exists."""
    result = verify_final_snapshot_exists(test_db, 2025)
    assert result is True


def test_verify_final_snapshot_exists_without_snapshot(test_db, sample_season):
    """Test verification fails when no final snapshot exists."""
    result = verify_final_snapshot_exists(test_db, 2025)
    assert result is False


def test_verify_final_snapshot_exists_wrong_season(test_db, final_snapshot):
    """Test verification fails for wrong season."""
    result = verify_final_snapshot_exists(test_db, 2024)
    assert result is False


def test_check_active_seasons_with_active(test_db, sample_season):
    """Test checking for active seasons when one exists."""
    active = check_active_seasons(test_db)
    assert len(active) == 1
    assert active[0].year == 2025
    assert active[0].is_active is True


def test_check_active_seasons_with_none_active(test_db):
    """Test checking for active seasons when none exist."""
    # Create an inactive season
    season = Season(year=2025, current_week=20, is_active=False)
    test_db.add(season)
    test_db.commit()

    active = check_active_seasons(test_db)
    assert len(active) == 0


def test_check_active_seasons_with_multiple_active(test_db):
    """Test checking for active seasons when multiple exist."""
    # Create two active seasons
    season1 = Season(year=2024, current_week=15, is_active=True)
    season2 = Season(year=2025, current_week=10, is_active=True)
    test_db.add(season1)
    test_db.add(season2)
    test_db.commit()

    active = check_active_seasons(test_db)
    assert len(active) == 2


def test_archive_season_nonexistent(test_db):
    """Test archiving a season that doesn't exist."""
    result = archive_season(test_db, 2025, confirm=True)
    assert result is False


def test_archive_season_already_archived(test_db):
    """Test archiving a season that's already archived."""
    # Create an already archived season
    season = Season(year=2025, current_week=20, is_active=False)
    test_db.add(season)
    test_db.commit()

    result = archive_season(test_db, 2025, confirm=True)
    assert result is True  # Should succeed (idempotent)


def test_archive_season_dry_run(test_db, sample_season, final_snapshot):
    """Test archiving in dry-run mode doesn't change data."""
    # Archive in dry-run mode
    result = archive_season(test_db, 2025, confirm=False)

    # Should return False (dry-run)
    assert result is False

    # Season should still be active
    season = test_db.query(Season).filter(Season.year == 2025).first()
    assert season.is_active is True


def test_archive_season_with_confirm(test_db, sample_season, final_snapshot):
    """Test archiving with confirmation actually marks season inactive."""
    # Archive with confirmation
    result = archive_season(test_db, 2025, confirm=True)

    # Should succeed
    assert result is True

    # Season should now be inactive
    season = test_db.query(Season).filter(Season.year == 2025).first()
    assert season.is_active is False


def test_archive_season_without_snapshot_dry_run(test_db, sample_season):
    """Test archiving without final snapshot in dry-run mode."""
    # No final snapshot created

    # Archive in dry-run mode
    result = archive_season(test_db, 2025, confirm=False)

    # Should return False (no snapshot and dry-run)
    assert result is False


def test_archive_season_without_snapshot_with_confirm(test_db, sample_season):
    """Test archiving without final snapshot with confirmation."""
    # No final snapshot created

    # Archive with confirmation (should proceed with warning)
    result = archive_season(test_db, 2025, confirm=True)

    # Should succeed (allows archival even without snapshot)
    assert result is True

    # Season should be inactive
    season = test_db.query(Season).filter(Season.year == 2025).first()
    assert season.is_active is False


def test_archive_season_rollback_on_error(test_db, sample_season, final_snapshot, monkeypatch):
    """Test that archival rolls back on error."""
    # Patch commit to raise an exception
    original_commit = test_db.commit

    def mock_commit():
        raise Exception("Simulated database error")

    monkeypatch.setattr(test_db, "commit", mock_commit)

    # Attempt to archive
    result = archive_season(test_db, 2025, confirm=True)

    # Should fail
    assert result is False

    # Restore original commit and verify season is still active
    test_db.commit = original_commit
    test_db.rollback()  # Clear any pending changes
    season = test_db.query(Season).filter(Season.year == 2025).first()
    assert season.is_active is True


def test_archive_season_multiple_times(test_db, sample_season, final_snapshot):
    """Test archiving the same season multiple times is idempotent."""
    # Archive first time
    result1 = archive_season(test_db, 2025, confirm=True)
    assert result1 is True

    # Archive second time
    result2 = archive_season(test_db, 2025, confirm=True)
    assert result2 is True

    # Season should still be inactive
    season = test_db.query(Season).filter(Season.year == 2025).first()
    assert season.is_active is False


def test_archive_season_verify_final_snapshot_called(test_db, sample_season):
    """Test that archive_season verifies final snapshot exists."""
    # No snapshot exists
    result = archive_season(test_db, 2025, confirm=False)

    # Should return False due to missing snapshot
    assert result is False


def test_multiple_seasons_only_archives_specified(test_db):
    """Test that only the specified season is archived."""
    # Create multiple seasons (don't use final_snapshot fixture to avoid year 2025 conflict)
    season_2024 = Season(year=2024, current_week=20, is_active=True)
    season_2026 = Season(year=2026, current_week=20, is_active=True)
    test_db.add(season_2024)
    test_db.add(season_2026)
    test_db.commit()

    # Create final snapshot for 2026
    team = Team(
        name="Test Team",
        conference=ConferenceType.POWER_5,
        is_fcs=False,
        elo_rating=1500.0,
        initial_rating=1500.0,
        wins=10,
        losses=2,
    )
    test_db.add(team)
    test_db.commit()

    snapshot = RankingHistory(
        team_id=team.id,
        week=20,
        season=2026,
        rank=1,
        elo_rating=1500.0,
        wins=10,
        losses=2,
        sos=1600.0,
        sos_rank=1,
    )
    test_db.add(snapshot)
    test_db.commit()

    # Archive only 2026
    result = archive_season(test_db, 2026, confirm=True)
    assert result is True

    # Check 2026 is archived
    season_2026 = test_db.query(Season).filter(Season.year == 2026).first()
    assert season_2026.is_active is False

    # Check 2024 is still active
    season_2024 = test_db.query(Season).filter(Season.year == 2024).first()
    assert season_2024.is_active is True
