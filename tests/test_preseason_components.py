"""
Story 32.4 — Tests for preseason component calculation (EPIC-032)

Covers:
- _calculate_preseason_bonuses(): all bonus tiers, FCS vs FBS base
- get_preseason_components(): field presence, FCS exclusion, prev_season_elo
- GET /api/preseason/components: HTTP 200, list shape, required fields
"""

import pytest
from unittest.mock import Mock

from src.models.models import ConferenceType, Team
from src.core.ranking_service import RankingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_team(
    *,
    conference=ConferenceType.POWER_5,
    recruiting_rank=50,
    transfer_portal_rank=50,
    returning_production=0.60,
    elo_rating=1500.0,
    is_fcs=False,
    position_strength=None,
):
    """Build a lightweight Mock Team for unit tests."""
    team = Mock(spec=Team)
    team.conference = conference
    team.recruiting_rank = recruiting_rank
    team.transfer_portal_rank = transfer_portal_rank
    team.returning_production = returning_production
    team.elo_rating = elo_rating
    team.is_fcs = is_fcs
    # position_strength attributes used by _calculate_position_strength_bonus
    team.qb_rating = position_strength
    team.skill_rating = position_strength
    team.line_rating = position_strength
    team.defense_rating = position_strength
    return team


def _make_service(db=None):
    """Return a RankingService with a mock or real db."""
    if db is None:
        db = Mock()
    return RankingService(db)


# ---------------------------------------------------------------------------
# Unit: _calculate_preseason_bonuses — base rating
# ---------------------------------------------------------------------------

class TestPreseasonBonusBase:
    def test_fbs_base_is_1500(self):
        svc = _make_service()
        team = _make_team(conference=ConferenceType.POWER_5)
        result = svc._calculate_preseason_bonuses(team)
        assert result["base"] == 1500.0

    def test_g5_base_is_1500(self):
        svc = _make_service()
        team = _make_team(conference=ConferenceType.GROUP_5)
        result = svc._calculate_preseason_bonuses(team)
        assert result["base"] == 1500.0

    def test_fcs_base_is_1300(self):
        svc = _make_service()
        team = _make_team(conference=ConferenceType.FCS)
        result = svc._calculate_preseason_bonuses(team)
        assert result["base"] == 1300.0


# ---------------------------------------------------------------------------
# Unit: _calculate_preseason_bonuses — recruiting bonus tiers
# ---------------------------------------------------------------------------

class TestRecruitingBonus:
    @pytest.mark.parametrize("rank,expected", [
        (1, 200.0),   # top-5
        (5, 200.0),   # boundary top-5
        (6, 150.0),   # top-10
        (10, 150.0),  # boundary top-10
        (11, 100.0),  # top-25
        (25, 100.0),  # boundary top-25
        (26, 50.0),   # top-50
        (50, 50.0),   # boundary top-50
        (51, 25.0),   # top-75
        (75, 25.0),   # boundary top-75
        (76, 0.0),    # outside all tiers
        (999, 0.0),   # worst possible
    ])
    def test_recruiting_bonus_tiers(self, rank, expected):
        svc = _make_service()
        team = _make_team(recruiting_rank=rank)
        result = svc._calculate_preseason_bonuses(team)
        assert result["recruiting_bonus"] == expected


# ---------------------------------------------------------------------------
# Unit: _calculate_preseason_bonuses — transfer portal bonus tiers
# ---------------------------------------------------------------------------

class TestTransferBonus:
    @pytest.mark.parametrize("rank,expected", [
        (1, 100.0),   # top-5
        (5, 100.0),   # boundary top-5
        (6, 75.0),    # top-10
        (10, 75.0),   # boundary top-10
        (11, 50.0),   # top-25
        (25, 50.0),   # boundary top-25
        (26, 25.0),   # top-50
        (50, 25.0),   # boundary top-50
        (51, 0.0),    # outside all tiers
        (999, 0.0),   # worst possible / None-equivalent
    ])
    def test_transfer_bonus_tiers(self, rank, expected):
        svc = _make_service()
        team = _make_team(transfer_portal_rank=rank)
        result = svc._calculate_preseason_bonuses(team)
        assert result["transfer_bonus"] == expected

    def test_null_transfer_rank_treated_as_999(self):
        svc = _make_service()
        team = _make_team()
        team.transfer_portal_rank = None
        result = svc._calculate_preseason_bonuses(team)
        assert result["transfer_bonus"] == 0.0


# ---------------------------------------------------------------------------
# Unit: _calculate_preseason_bonuses — returning production bonus tiers
# ---------------------------------------------------------------------------

class TestReturningBonus:
    @pytest.mark.parametrize("prod,expected", [
        (0.80, 40.0),   # threshold
        (0.90, 40.0),   # above threshold
        (1.00, 40.0),   # max
        (0.79, 25.0),   # just below 0.80
        (0.60, 25.0),   # threshold
        (0.59, 10.0),   # just below 0.60
        (0.40, 10.0),   # threshold
        (0.39, 0.0),    # just below 0.40
        (0.25, 0.0),    # low production
        (0.00, 0.0),    # zero
    ])
    def test_returning_bonus_tiers(self, prod, expected):
        svc = _make_service()
        team = _make_team(returning_production=prod)
        result = svc._calculate_preseason_bonuses(team)
        assert result["returning_bonus"] == expected


# ---------------------------------------------------------------------------
# Unit: _calculate_preseason_bonuses — result shape
# ---------------------------------------------------------------------------

class TestPreseasonBonusShape:
    def test_result_has_all_keys(self):
        svc = _make_service()
        team = _make_team()
        result = svc._calculate_preseason_bonuses(team)
        assert set(result.keys()) == {
            "base",
            "recruiting_bonus",
            "transfer_bonus",
            "returning_bonus",
            "position_strength_bonus",
        }

    def test_all_values_are_numeric(self):
        svc = _make_service()
        team = _make_team()
        result = svc._calculate_preseason_bonuses(team)
        for key, val in result.items():
            assert isinstance(val, (int, float)), f"{key} is not numeric: {val!r}"


# ---------------------------------------------------------------------------
# Integration: get_preseason_components (uses real in-memory DB)
# ---------------------------------------------------------------------------

class TestGetPreseasonComponents:
    def test_returns_list(self, factories, test_db):
        from factories import TeamFactory
        TeamFactory()
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        assert isinstance(result, list)

    def test_required_fields_present(self, factories, test_db):
        from factories import TeamFactory
        TeamFactory()
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        assert len(result) >= 1
        item = result[0]
        required = {
            "team_id", "team_name", "conference", "is_fcs",
            "recruiting_rank", "transfer_portal_rank", "returning_production",
            "base", "recruiting_bonus", "transfer_bonus", "returning_bonus",
            "position_strength_bonus", "prev_season_elo", "current_rating",
        }
        assert required.issubset(item.keys())

    def test_fcs_teams_excluded(self, factories, test_db):
        from factories import TeamFactory, FCSTeamFactory
        fbs_team = TeamFactory(name="FBS Team")
        fcs_team = FCSTeamFactory(name="FCS Team", is_fcs=True)
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        team_names = {r["team_name"] for r in result}
        assert "FBS Team" in team_names
        assert "FCS Team" not in team_names

    def test_sorted_by_current_rating_desc(self, factories, test_db):
        from factories import TeamFactory
        TeamFactory(elo_rating=1800.0)
        TeamFactory(elo_rating=1500.0)
        TeamFactory(elo_rating=1350.0)
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        ratings = [r["current_rating"] for r in result]
        assert ratings == sorted(ratings, reverse=True)

    def test_prev_season_elo_from_ranking_history(self, factories, test_db):
        from factories import TeamFactory, RankingHistoryFactory
        team = TeamFactory(name="History Team")
        # Create a ranking history record for the previous season
        RankingHistoryFactory(team=team, season=2024, week=999, elo_rating=1650.0)
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        entry = next(r for r in result if r["team_name"] == "History Team")
        assert entry["prev_season_elo"] == 1650.0

    def test_prev_season_elo_none_when_no_history(self, factories, test_db):
        from factories import TeamFactory
        TeamFactory(name="No History Team")
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        entry = next(r for r in result if r["team_name"] == "No History Team")
        assert entry["prev_season_elo"] is None

    def test_bonus_values_match_calculate_method(self, factories, test_db):
        from factories import TeamFactory
        team = TeamFactory(recruiting_rank=1, transfer_portal_rank=5, returning_production=0.85)
        svc = RankingService(test_db)
        result = svc.get_preseason_components(2025)
        entry = next(r for r in result if r["team_id"] == team.id)
        assert entry["recruiting_bonus"] == 200.0
        assert entry["transfer_bonus"] == 100.0
        assert entry["returning_bonus"] == 40.0
        assert entry["base"] == 1500.0


# ---------------------------------------------------------------------------
# Integration: GET /api/preseason/components
# ---------------------------------------------------------------------------

class TestPreseasonComponentsEndpoint:
    def test_returns_200(self, test_client, factories):
        from factories import TeamFactory, SeasonFactory
        SeasonFactory(year=2025, is_active=True)
        TeamFactory()
        response = test_client.get("/api/preseason/components?season=2025")
        assert response.status_code == 200

    def test_returns_list_of_dicts(self, test_client, factories):
        from factories import TeamFactory, SeasonFactory
        SeasonFactory(year=2025, is_active=True)
        TeamFactory()
        response = test_client.get("/api/preseason/components?season=2025")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert isinstance(data[0], dict)

    def test_response_items_have_required_fields(self, test_client, factories):
        from factories import TeamFactory, SeasonFactory
        SeasonFactory(year=2025, is_active=True)
        TeamFactory()
        response = test_client.get("/api/preseason/components?season=2025")
        item = response.json()[0]
        for field in ["team_id", "team_name", "base", "recruiting_bonus",
                      "transfer_bonus", "returning_bonus", "current_rating"]:
            assert field in item, f"Missing field: {field}"

    def test_fcs_teams_not_in_response(self, test_client, factories):
        from factories import TeamFactory, FCSTeamFactory, SeasonFactory
        SeasonFactory(year=2025, is_active=True)
        TeamFactory(name="FBS Only")
        FCSTeamFactory(name="FCS Only", is_fcs=True)
        response = test_client.get("/api/preseason/components?season=2025")
        names = {item["team_name"] for item in response.json()}
        assert "FBS Only" in names
        assert "FCS Only" not in names

    def test_missing_season_defaults_to_active(self, test_client, factories):
        from factories import TeamFactory, SeasonFactory
        SeasonFactory(year=2025, is_active=True)
        TeamFactory()
        # season param is optional; endpoint defaults to active season
        response = test_client.get("/api/preseason/components")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
