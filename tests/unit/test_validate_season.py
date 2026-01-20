"""Unit tests for Season Data Validation Script

Tests the validation logic for season data integrity checks.

Part of EPIC-SEASON-END-2025: Story 1 - Season Data Validation
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.models import APPollRanking, Base, Game, Season, Team, ConferenceType
from utilities.validate_season import (
    ValidationReport,
    validate_game_completeness,
    validate_elo_integrity,
    validate_ap_poll_completeness,
    validate_missing_data,
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
    """Create a sample season for testing."""
    season = Season(year=2025, current_week=15, is_active=True)
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def sample_teams(test_db):
    """Create sample teams for testing."""
    teams = [
        Team(
            name="Georgia",
            conference=ConferenceType.POWER_5,
            conference_name="SEC",
            is_fcs=False,
            elo_rating=1850.0,
            initial_rating=1800.0,
            wins=10,
            losses=2,
        ),
        Team(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            conference_name="SEC",
            is_fcs=False,
            elo_rating=1820.0,
            initial_rating=1780.0,
            wins=9,
            losses=3,
        ),
        Team(
            name="Idaho State",
            conference=ConferenceType.FCS,
            conference_name="Big Sky",
            is_fcs=True,
            elo_rating=1300.0,
            initial_rating=1300.0,
            wins=5,
            losses=6,
        ),
    ]
    for team in teams:
        test_db.add(team)
    test_db.commit()
    return teams


def test_validation_report_initialization():
    """Test that ValidationReport initializes correctly."""
    report = ValidationReport(2025)
    assert report.season == 2025
    assert report.status == "PASS"
    assert len(report.findings) == 0
    assert len(report.warnings) == 0
    assert len(report.errors) == 0


def test_validation_report_add_error():
    """Test that adding an error changes status to FAIL."""
    report = ValidationReport(2025)
    assert report.status == "PASS"

    report.add_error("Test error")

    assert report.status == "FAIL"
    assert len(report.errors) == 1
    assert report.errors[0] == "Test error"


def test_validation_report_add_warning():
    """Test that adding a warning doesn't change status."""
    report = ValidationReport(2025)
    assert report.status == "PASS"

    report.add_warning("Test warning")

    assert report.status == "PASS"
    assert len(report.warnings) == 1
    assert report.warnings[0] == "Test warning"


def test_validation_report_generate_markdown():
    """Test markdown report generation."""
    report = ValidationReport(2025)
    report.summary["Total Games"] = 100
    report.add_warning("Test warning")

    markdown = report.generate_markdown()

    assert "# Season 2025 Validation Report" in markdown
    assert "**Status:** ✅ PASS" in markdown
    assert "**Total Games:** 100" in markdown
    assert "⚠ Test warning" in markdown


def test_validate_game_completeness_no_games(test_db, sample_season):
    """Test validation when no games exist."""
    report = ValidationReport(2025)

    validate_game_completeness(test_db, 2025, report, verbose=False)

    assert report.status == "FAIL"
    assert any("No games found" in error for error in report.errors)


def test_validate_game_completeness_with_processed_games(test_db, sample_season, sample_teams):
    """Test validation with all games processed."""
    # Create processed games
    for week in range(1, 6):
        game = Game(
            home_team_id=sample_teams[0].id,
            away_team_id=sample_teams[1].id,
            home_score=35,
            away_score=28,
            week=week,
            season=2025,
            is_processed=True,
            home_rating_change=10.0,
            away_rating_change=-10.0,
        )
        test_db.add(game)
    test_db.commit()

    report = ValidationReport(2025)
    validate_game_completeness(test_db, 2025, report, verbose=False)

    assert report.summary["Total Games"] == 5
    assert "100.0%" in report.summary["Games Processed"]
    # May have warnings about missing weeks, but no errors about unprocessed games
    assert not any("unprocessed" in error.lower() for error in report.errors)


def test_validate_game_completeness_with_unprocessed_games(test_db, sample_season, sample_teams):
    """Test validation detects unprocessed games."""
    # Create one unprocessed game
    game = Game(
        home_team_id=sample_teams[0].id,
        away_team_id=sample_teams[1].id,
        home_score=35,
        away_score=28,
        week=1,
        season=2025,
        is_processed=False,
    )
    test_db.add(game)
    test_db.commit()

    report = ValidationReport(2025)
    validate_game_completeness(test_db, 2025, report, verbose=False)

    assert report.status == "FAIL"
    assert any("not processed" in error for error in report.errors)


def test_validate_elo_integrity_zero_sum_pass(test_db, sample_season, sample_teams):
    """Test ELO integrity validation when zero-sum holds."""
    # Create game with zero-sum rating changes
    game = Game(
        home_team_id=sample_teams[0].id,
        away_team_id=sample_teams[1].id,
        home_score=35,
        away_score=28,
        week=1,
        season=2025,
        is_processed=True,
        home_rating_change=12.5,
        away_rating_change=-12.5,
    )
    test_db.add(game)
    test_db.commit()

    report = ValidationReport(2025)
    validate_elo_integrity(test_db, 2025, report, verbose=False)

    # Should not have ELO imbalance errors
    assert not any("imbalance" in error.lower() for error in report.errors)


def test_validate_elo_integrity_zero_sum_fail(test_db, sample_season, sample_teams):
    """Test ELO integrity validation detects imbalances."""
    # Create game with non-zero-sum rating changes
    game = Game(
        home_team_id=sample_teams[0].id,
        away_team_id=sample_teams[1].id,
        home_score=35,
        away_score=28,
        week=1,
        season=2025,
        is_processed=True,
        home_rating_change=15.0,
        away_rating_change=-10.0,  # Imbalance: 15 + (-10) = 5
    )
    test_db.add(game)
    test_db.commit()

    report = ValidationReport(2025)
    validate_elo_integrity(test_db, 2025, report, verbose=False)

    assert report.status == "FAIL"
    assert any("imbalance" in error.lower() for error in report.errors)


def test_validate_elo_integrity_suspicious_large_changes(test_db, sample_season, sample_teams):
    """Test validation warns about large rating changes."""
    # Create game with large rating change (>200 points)
    game = Game(
        home_team_id=sample_teams[0].id,
        away_team_id=sample_teams[1].id,
        home_score=70,
        away_score=0,
        week=1,
        season=2025,
        is_processed=True,
        home_rating_change=250.0,
        away_rating_change=-250.0,
    )
    test_db.add(game)
    test_db.commit()

    report = ValidationReport(2025)
    validate_elo_integrity(test_db, 2025, report, verbose=False)

    assert len(report.warnings) > 0
    assert any("large rating change" in warning.lower() for warning in report.warnings)


def test_validate_ap_poll_completeness_no_data(test_db, sample_season):
    """Test validation when no AP Poll data exists."""
    report = ValidationReport(2025)
    validate_ap_poll_completeness(test_db, 2025, report, verbose=False)

    assert len(report.warnings) > 0
    assert any("no ap poll" in warning.lower() for warning in report.warnings)


def test_validate_ap_poll_completeness_with_data(test_db, sample_season, sample_teams):
    """Test validation with complete AP Poll data."""
    # Create more teams to avoid unique constraint violations
    extra_teams = []
    for i in range(3, 28):  # Create teams for ranks 3-27
        team = Team(
            name=f"Team {i}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1500.0,
            initial_rating=1500.0,
            wins=0,
            losses=0,
        )
        test_db.add(team)
        extra_teams.append(team)
    test_db.commit()

    all_teams = sample_teams + extra_teams

    # Create AP Poll rankings for multiple weeks
    for week in range(1, 6):
        for rank in range(1, 26):  # 25 teams
            # Use different teams for each rank to avoid unique constraint violation
            team_idx = min(rank - 1, len(all_teams) - 1)
            ap_ranking = APPollRanking(
                season=2025,
                week=week,
                rank=rank,
                team_id=all_teams[team_idx].id,
                points=1500 - (rank * 50),
            )
            test_db.add(ap_ranking)
    test_db.commit()

    report = ValidationReport(2025)
    validate_ap_poll_completeness(test_db, 2025, report, verbose=False)

    assert report.summary["AP Poll Entries"] == 125  # 5 weeks * 25 teams
    assert "25.0" in str(report.summary.get("Avg AP Poll Teams/Week", ""))


def test_validate_missing_data_duplicates(test_db, sample_season, sample_teams):
    """Test validation detects duplicate games."""
    # Create two identical games (duplicate)
    for _ in range(2):
        game = Game(
            home_team_id=sample_teams[0].id,
            away_team_id=sample_teams[1].id,
            home_score=35,
            away_score=28,
            week=1,
            season=2025,
            is_processed=True,
        )
        test_db.add(game)
    test_db.commit()

    report = ValidationReport(2025)
    validate_missing_data(test_db, 2025, report, verbose=False)

    assert report.status == "FAIL"
    assert any("duplicate" in error.lower() for error in report.errors)


def test_validate_missing_data_unusual_records(test_db, sample_season):
    """Test validation warns about unusual team records."""
    # Create team with 0-0 record
    team = Team(
        name="Test Team",
        conference=ConferenceType.POWER_5,
        is_fcs=False,
        wins=0,
        losses=0,
        elo_rating=1500.0,
        initial_rating=1500.0,
    )
    test_db.add(team)
    test_db.commit()

    report = ValidationReport(2025)
    validate_missing_data(test_db, 2025, report, verbose=False)

    assert len(report.warnings) > 0
    assert any("unusual record" in warning.lower() for warning in report.warnings)


def test_validate_missing_data_missing_preseason_data(test_db, sample_season):
    """Test validation warns about missing preseason data."""
    # Create team with missing recruiting data (999)
    team = Team(
        name="Test Team",
        conference=ConferenceType.POWER_5,
        is_fcs=False,
        recruiting_rank=999,
        wins=5,
        losses=5,
        elo_rating=1500.0,
        initial_rating=1500.0,
    )
    test_db.add(team)
    test_db.commit()

    report = ValidationReport(2025)
    validate_missing_data(test_db, 2025, report, verbose=False)

    assert len(report.warnings) > 0
    assert any("preseason" in warning.lower() for warning in report.warnings)


def test_validation_report_markdown_with_errors():
    """Test markdown report includes errors and recommendations."""
    report = ValidationReport(2025)
    report.add_error("Critical error 1")
    report.add_error("Critical error 2")

    markdown = report.generate_markdown()

    assert "**Status:** ❌ FAIL" in markdown
    assert "Critical error 1" in markdown
    assert "Critical error 2" in markdown
    assert "Not Ready for Finalization" in markdown


def test_validation_report_markdown_with_pass_status():
    """Test markdown report shows success message when passing."""
    report = ValidationReport(2025)
    report.summary["Total Games"] = 800

    markdown = report.generate_markdown()

    assert "**Status:** ✅ PASS" in markdown
    assert "Ready for Finalization" in markdown
    assert "None - validation successful" in markdown
