"""
Unit tests for EPIC-032 Story 32.1: Preseason Components

Tests cover:
- _calculate_preseason_bonuses(): correct bonus values for each tier
- get_preseason_components(): correct structure, prev_season_elo lookup,
  FCS exclusion, sorting
"""

import pytest
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, RankingHistory, Team
from src.core.ranking_service import RankingService


@pytest.mark.unit
class TestCalculatePreseasonBonuses:
    """Tests for _calculate_preseason_bonuses() helper"""

    def test_recruiting_bonus_tiers(self, test_db: Session):
        service = RankingService(test_db)
        cases = [
            (1, 200.0),
            (5, 200.0),
            (6, 150.0),
            (10, 150.0),
            (11, 100.0),
            (25, 100.0),
            (26, 50.0),
            (50, 50.0),
            (51, 25.0),
            (75, 25.0),
            (76, 0.0),
            (999, 0.0),
        ]
        for rank, expected in cases:
            team = Team(
                name=f"Team {rank}",
                conference=ConferenceType.POWER_5,
                recruiting_rank=rank,
                transfer_portal_rank=999,
                returning_production=0.0,
            )
            bonuses = service._calculate_preseason_bonuses(team)
            assert bonuses["recruiting_bonus"] == expected, (
                f"recruiting_rank={rank}: expected {expected}, got {bonuses['recruiting_bonus']}"
            )

    def test_transfer_portal_bonus_tiers(self, test_db: Session):
        service = RankingService(test_db)
        cases = [
            (1, 100.0),
            (5, 100.0),
            (6, 75.0),
            (10, 75.0),
            (11, 50.0),
            (25, 50.0),
            (26, 25.0),
            (50, 25.0),
            (51, 0.0),
            (999, 0.0),
        ]
        for rank, expected in cases:
            team = Team(
                name=f"Team tp{rank}",
                conference=ConferenceType.POWER_5,
                recruiting_rank=999,
                transfer_portal_rank=rank,
                returning_production=0.0,
            )
            bonuses = service._calculate_preseason_bonuses(team)
            assert bonuses["transfer_bonus"] == expected, (
                f"transfer_portal_rank={rank}: expected {expected}, got {bonuses['transfer_bonus']}"
            )

    def test_returning_bonus_tiers(self, test_db: Session):
        service = RankingService(test_db)
        cases = [
            (0.80, 40.0),
            (0.90, 40.0),
            (0.60, 25.0),
            (0.79, 25.0),
            (0.40, 10.0),
            (0.59, 10.0),
            (0.39, 0.0),
            (0.00, 0.0),
        ]
        for prod, expected in cases:
            team = Team(
                name=f"Team ret{prod}",
                conference=ConferenceType.POWER_5,
                recruiting_rank=999,
                transfer_portal_rank=999,
                returning_production=prod,
            )
            bonuses = service._calculate_preseason_bonuses(team)
            assert bonuses["returning_bonus"] == expected, (
                f"returning_production={prod}: expected {expected}, got {bonuses['returning_bonus']}"
            )

    def test_base_fbs(self, test_db: Session):
        service = RankingService(test_db)
        team = Team(name="FBS", conference=ConferenceType.POWER_5,
                    recruiting_rank=999, transfer_portal_rank=999, returning_production=0.0)
        assert service._calculate_preseason_bonuses(team)["base"] == 1500.0

    def test_base_fcs(self, test_db: Session):
        service = RankingService(test_db)
        team = Team(name="FCS", conference=ConferenceType.FCS,
                    recruiting_rank=999, transfer_portal_rank=999, returning_production=0.0)
        assert service._calculate_preseason_bonuses(team)["base"] == 1300.0

    def test_bonuses_sum_matches_base_formula(self, test_db: Session):
        """Sum of all bonuses should equal base_formula_rating when prev_weight=0"""
        service = RankingService(test_db)
        team = Team(
            name="Checksum Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=3,
            transfer_portal_rank=8,
            returning_production=0.65,
        )
        bonuses = service._calculate_preseason_bonuses(team)
        expected_total = (
            bonuses["base"]
            + bonuses["recruiting_bonus"]
            + bonuses["transfer_bonus"]
            + bonuses["returning_bonus"]
            + bonuses["position_strength_bonus"]
        )
        # calculate_preseason_rating with no season should return same total
        actual = service.calculate_preseason_rating(team, season=None)
        assert abs(actual - expected_total) < 0.01


@pytest.mark.unit
class TestGetPreseasonComponents:
    """Tests for get_preseason_components()"""

    def _make_team(self, db, name, conference=ConferenceType.POWER_5,
                   recruiting_rank=50, transfer_portal_rank=999,
                   returning_production=0.5, elo=1550.0, is_fcs=False):
        team = Team(
            name=name,
            conference=conference,
            recruiting_rank=recruiting_rank,
            transfer_portal_rank=transfer_portal_rank,
            returning_production=returning_production,
            elo_rating=elo,
            is_fcs=is_fcs,
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        return team

    def test_returns_fbs_teams_only(self, test_db: Session):
        self._make_team(test_db, "FBS Team A", elo=1600.0)
        self._make_team(test_db, "FBS Team B", elo=1550.0)
        self._make_team(test_db, "FCS Team", conference=ConferenceType.FCS,
                        elo=1300.0, is_fcs=True)
        service = RankingService(test_db)
        components = service.get_preseason_components(season=2026)
        names = [c["team_name"] for c in components]
        assert "FCS Team" not in names
        assert "FBS Team A" in names
        assert "FBS Team B" in names

    def test_sorted_by_current_rating_desc(self, test_db: Session):
        self._make_team(test_db, "Low Team", elo=1500.0)
        self._make_team(test_db, "High Team", elo=1800.0)
        self._make_team(test_db, "Mid Team", elo=1650.0)
        service = RankingService(test_db)
        components = service.get_preseason_components(season=2026)
        ratings = [c["current_rating"] for c in components]
        assert ratings == sorted(ratings, reverse=True)

    def test_contains_required_fields(self, test_db: Session):
        self._make_team(test_db, "Test Team", elo=1600.0)
        service = RankingService(test_db)
        components = service.get_preseason_components(season=2026)
        required = {
            "team_id", "team_name", "conference", "is_fcs",
            "recruiting_rank", "transfer_portal_rank", "returning_production",
            "base", "recruiting_bonus", "transfer_bonus", "returning_bonus",
            "position_strength_bonus", "prev_season_elo", "current_rating",
        }
        assert required.issubset(set(components[0].keys()))

    def test_prev_season_elo_from_ranking_history(self, test_db: Session):
        team = self._make_team(test_db, "Historic Team", elo=1600.0)
        # Add a ranking_history entry for season 2025
        history = RankingHistory(
            team_id=team.id,
            season=2025,
            week=20,
            rank=5,
            elo_rating=1950.0,
            wins=12,
            losses=0,
        )
        test_db.add(history)
        test_db.commit()

        service = RankingService(test_db)
        components = service.get_preseason_components(season=2026)
        team_data = next(c for c in components if c["team_name"] == "Historic Team")
        assert team_data["prev_season_elo"] == 1950.0

    def test_prev_season_elo_none_when_no_history(self, test_db: Session):
        self._make_team(test_db, "New Team", elo=1500.0)
        service = RankingService(test_db)
        components = service.get_preseason_components(season=2026)
        team_data = next(c for c in components if c["team_name"] == "New Team")
        assert team_data["prev_season_elo"] is None

    def test_bonus_components_sum_to_current_rating_when_no_regression(self, test_db: Session):
        """When prev_season_weight=0, base+bonuses should equal what calculate_preseason_rating returns"""
        team = self._make_team(test_db, "Sum Team", recruiting_rank=3,
                               transfer_portal_rank=8, returning_production=0.65, elo=1600.0)
        service = RankingService(test_db)
        components = service.get_preseason_components(season=2026)
        t = next(c for c in components if c["team_name"] == "Sum Team")
        component_sum = (
            t["base"] + t["recruiting_bonus"] + t["transfer_bonus"]
            + t["returning_bonus"] + t["position_strength_bonus"]
        )
        # calculate_preseason_rating with no season (no regression)
        expected = service.calculate_preseason_rating(team, season=None)
        assert abs(component_sum - expected) < 0.01
