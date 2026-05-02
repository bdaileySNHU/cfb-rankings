"""
Unit tests for EPIC-030: Previous Season Regression

Tests cover:
- save_final_season_snapshot: writes week=999 entries, idempotency, ELO accuracy
- _get_previous_season_elo: prefers week=999, falls back to highest week, handles missing
- calculate_preseason_rating with regression: weight=0 passthrough, fixed/dynamic regression,
  missing season/data fallbacks, blended value bounds
"""

import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, RankingHistory, Season, Team
from src.core.ranking_service import RankingService


def _make_team(db: Session, name: str, elo: float = 1500.0, returning_production: float = 0.5) -> Team:
    """Helper: create and persist a minimal FBS team."""
    team = Team(
        name=name,
        conference=ConferenceType.POWER_5,
        recruiting_rank=999,
        transfer_portal_rank=999,
        returning_production=returning_production,
        elo_rating=elo,
        initial_rating=elo,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def _add_ranking_history(
    db: Session,
    team_id: int,
    season: int,
    week: int,
    elo: float,
) -> RankingHistory:
    """Helper: create a RankingHistory entry."""
    entry = RankingHistory(
        team_id=team_id,
        season=season,
        week=week,
        rank=1,
        elo_rating=elo,
        wins=0,
        losses=0,
        sos=0.0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# TestSaveFinalSeasonSnapshot
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSaveFinalSeasonSnapshot:
    """Tests for RankingService.save_final_season_snapshot"""

    def test_saves_week_999_entries_for_all_teams(self, test_db: Session):
        """Creates 3 teams, calls snapshot, checks 3 week=999 entries exist."""
        _make_team(test_db, "TeamA", elo=1600.0)
        _make_team(test_db, "TeamB", elo=1700.0)
        _make_team(test_db, "TeamC", elo=1550.0)

        rs = RankingService(test_db)
        count = rs.save_final_season_snapshot(2025)

        assert count == 3

        entries = (
            test_db.query(RankingHistory)
            .filter(RankingHistory.season == 2025, RankingHistory.week == 999)
            .all()
        )
        assert len(entries) == 3

    def test_idempotent_rerun_updates_not_duplicates(self, test_db: Session):
        """Calling snapshot twice still produces 3 entries, not 6."""
        _make_team(test_db, "TeamA", elo=1600.0)
        _make_team(test_db, "TeamB", elo=1700.0)
        _make_team(test_db, "TeamC", elo=1550.0)

        rs = RankingService(test_db)
        rs.save_final_season_snapshot(2025)
        rs.save_final_season_snapshot(2025)

        entries = (
            test_db.query(RankingHistory)
            .filter(RankingHistory.season == 2025, RankingHistory.week == 999)
            .all()
        )
        assert len(entries) == 3

    def test_snapshot_uses_current_elo_rating(self, test_db: Session):
        """Team with elo=1800 should produce a week=999 entry with elo_rating=1800."""
        team = _make_team(test_db, "TeamA", elo=1800.0)

        rs = RankingService(test_db)
        rs.save_final_season_snapshot(2025)

        entry = (
            test_db.query(RankingHistory)
            .filter(
                RankingHistory.team_id == team.id,
                RankingHistory.season == 2025,
                RankingHistory.week == 999,
            )
            .first()
        )
        assert entry is not None
        assert entry.elo_rating == 1800.0


# ---------------------------------------------------------------------------
# TestGetPreviousSeasonElo
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetPreviousSeasonElo:
    """Tests for RankingService._get_previous_season_elo"""

    def test_returns_elo_when_week_999_exists(self, test_db: Session):
        """Add week=999 entry → method returns its ELO."""
        team = _make_team(test_db, "TeamA", elo=1700.0)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1720.0)

        rs = RankingService(test_db)
        result = rs._get_previous_season_elo(team.id, current_season=2026)

        assert result == 1720.0

    def test_prefers_week_999_over_lower_week(self, test_db: Session):
        """With week=15 (1700) and week=999 (1850) → returns 1850 (highest week)."""
        team = _make_team(test_db, "TeamA", elo=1700.0)
        _add_ranking_history(test_db, team.id, season=2025, week=15, elo=1700.0)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1850.0)

        rs = RankingService(test_db)
        result = rs._get_previous_season_elo(team.id, current_season=2026)

        assert result == 1850.0

    def test_returns_none_when_no_previous_season_data(self, test_db: Session):
        """No entries for prev season → returns None."""
        team = _make_team(test_db, "TeamA", elo=1600.0)
        # Only 2024 data, no 2025
        _add_ranking_history(test_db, team.id, season=2024, week=15, elo=1600.0)

        rs = RankingService(test_db)
        result = rs._get_previous_season_elo(team.id, current_season=2026)

        assert result is None

    def test_returns_highest_week_when_no_week_999(self, test_db: Session):
        """week=10 (1600) and week=15 (1750) → returns 1750."""
        team = _make_team(test_db, "TeamA", elo=1700.0)
        _add_ranking_history(test_db, team.id, season=2025, week=10, elo=1600.0)
        _add_ranking_history(test_db, team.id, season=2025, week=15, elo=1750.0)

        rs = RankingService(test_db)
        result = rs._get_previous_season_elo(team.id, current_season=2026)

        assert result == 1750.0


# ---------------------------------------------------------------------------
# TestCalculatePreseasonRatingRegression
# ---------------------------------------------------------------------------

_BASE_CONFIG = {
    "enabled": False,
    "weights": {},
    "max_bonus": 150,
    "previous_season_weight": 0.35,
    "mean_regression_factor": 0.60,
    "returning_regression_scale": 0.60,
}

_DISABLED_CONFIG = dict(_BASE_CONFIG, previous_season_weight=0.0)


@pytest.mark.unit
class TestCalculatePreseasonRatingRegression:
    """Tests for calculate_preseason_rating with EPIC-030 regression blend."""

    def test_weight_zero_returns_base_formula(self, test_db: Session):
        """With prev_elo in ranking_history but weight=0.0 → same as no-season call."""
        team = _make_team(test_db, "TeamA", elo=1800.0, returning_production=0.5)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1800.0)

        rs = RankingService(test_db)
        base = rs.calculate_preseason_rating(team)

        with patch("src.core.position_service.load_position_weights", return_value=_DISABLED_CONFIG):
            result = rs.calculate_preseason_rating(team, season=2026)

        assert result == base

    def test_fixed_regression_no_returning_production(self, test_db: Session):
        """weight=0.35, regression=0.60, returning_prod defaults to 0.5 → math check.

        Note: returning_production column default is 0.5, so after commit returning_bonus=10.0
        (>= 0.40 threshold) and dynamic_regression = 0.60 + (0.5-0.5)*0.60 = 0.60.
        """
        team = Team(
            name="TeamA",
            conference=ConferenceType.POWER_5,
            recruiting_rank=999,
            transfer_portal_rank=999,
            returning_production=None,
            elo_rating=1800.0,
            initial_rating=1800.0,
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1800.0)

        rs = RankingService(test_db)
        # After commit, returning_production defaults to 0.5 → returning_bonus=10.0
        # base_formula_rating = 1500 + 0 + 0 + 10 + 0 = 1510
        # returning_prod = 0.5 → dynamic_regression = 0.60 + (0.5-0.5)*0.60 = 0.60
        base_formula = 1510.0
        prev_elo = 1800.0
        returning_prod = 0.5
        base_regression = 0.60
        scale = 0.60
        dynamic = base_regression + (returning_prod - 0.5) * scale
        regression = max(0.30, min(0.85, dynamic))  # 0.60
        prev_regressed = 1500.0 + (prev_elo - 1500.0) * regression  # 1680.0
        expected_blended = (prev_regressed * 0.35) + (base_formula * 0.65)  # 588+981.5=1569.5

        with patch("src.core.position_service.load_position_weights", return_value=_BASE_CONFIG):
            result = rs.calculate_preseason_rating(team, season=2026)

        assert abs(result - expected_blended) < 0.01

    def test_dynamic_regression_low_returning(self, test_db: Session):
        """weight=0.35, returning_prod=0.251 → regression = clamp(0.60+(0.251-0.5)*0.60, 0.30, 0.85)."""
        returning_prod = 0.251
        team = _make_team(test_db, "TeamA", elo=1800.0, returning_production=returning_prod)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1800.0)

        rs = RankingService(test_db)
        base_regression = 0.60
        scale = 0.60
        dynamic = base_regression + (returning_prod - 0.5) * scale
        regression = max(0.30, min(0.85, dynamic))

        prev_elo = 1800.0
        base_formula = 1500.0
        prev_regressed = 1500.0 + (prev_elo - 1500.0) * regression
        expected_blended = (prev_regressed * 0.35) + (base_formula * 0.65)

        with patch("src.core.position_service.load_position_weights", return_value=_BASE_CONFIG):
            result = rs.calculate_preseason_rating(team, season=2026)

        assert abs(result - expected_blended) < 0.01

    def test_dynamic_regression_high_returning(self, test_db: Session):
        """weight=0.35, returning_prod=0.589 → regression = clamp(0.60+(0.589-0.5)*0.60, 0.30, 0.85).

        Note: returning_production=0.589 >= 0.40 → returning_bonus=10.0, so base_formula=1510.
        """
        returning_prod = 0.589
        team = _make_team(test_db, "TeamA", elo=1800.0, returning_production=returning_prod)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1800.0)

        rs = RankingService(test_db)
        base_regression = 0.60
        scale = 0.60
        dynamic = base_regression + (returning_prod - 0.5) * scale
        regression = max(0.30, min(0.85, dynamic))

        prev_elo = 1800.0
        # returning_prod=0.589 >= 0.40 → returning_bonus=10.0 → base_formula=1510
        base_formula = 1510.0
        prev_regressed = 1500.0 + (prev_elo - 1500.0) * regression
        expected_blended = (prev_regressed * 0.35) + (base_formula * 0.65)

        with patch("src.core.position_service.load_position_weights", return_value=_BASE_CONFIG):
            result = rs.calculate_preseason_rating(team, season=2026)

        assert abs(result - expected_blended) < 0.01

    def test_no_season_falls_back_to_base_formula(self, test_db: Session):
        """season=None → no regression applied, base formula returned."""
        team = _make_team(test_db, "TeamA", elo=1800.0, returning_production=0.5)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=1800.0)

        rs = RankingService(test_db)
        base = rs.calculate_preseason_rating(team)  # no season

        with patch("src.core.position_service.load_position_weights", return_value=_BASE_CONFIG):
            result = rs.calculate_preseason_rating(team, season=None)

        assert result == base

    def test_missing_prev_season_data_falls_back(self, test_db: Session):
        """season=2026 but no 2025 data → base formula returned."""
        team = _make_team(test_db, "TeamA", elo=1800.0, returning_production=0.5)
        # No ranking_history entries for 2025

        rs = RankingService(test_db)
        base = rs.calculate_preseason_rating(team)

        with patch("src.core.position_service.load_position_weights", return_value=_BASE_CONFIG):
            result = rs.calculate_preseason_rating(team, season=2026)

        assert result == base

    def test_blended_result_is_between_prev_and_base(self, test_db: Session):
        """The blended result should be between prev_regressed and base_formula_rating."""
        returning_prod = 0.5
        prev_elo = 1900.0
        team = _make_team(test_db, "TeamA", elo=prev_elo, returning_production=returning_prod)
        _add_ranking_history(test_db, team.id, season=2025, week=999, elo=prev_elo)

        rs = RankingService(test_db)
        base_formula = rs.calculate_preseason_rating(team)  # no season, no regression

        with patch("src.core.position_service.load_position_weights", return_value=_BASE_CONFIG):
            blended = rs.calculate_preseason_rating(team, season=2026)

        regression = 0.60
        prev_regressed = 1500.0 + (prev_elo - 1500.0) * regression

        lo = min(prev_regressed, base_formula)
        hi = max(prev_regressed, base_formula)
        assert lo <= blended <= hi
