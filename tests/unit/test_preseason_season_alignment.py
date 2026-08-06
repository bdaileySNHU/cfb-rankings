import itertools
import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, RosterPlayer, Season, Team
from src.core.ranking_service import RankingService


def _make_team(db: Session, name: str, elo: float = 1500.0) -> Team:
    """Helper: create and persist a minimal FBS team."""
    team = Team(
        name=name,
        conference=ConferenceType.POWER_5,
        recruiting_rank=999,
        transfer_portal_rank=999,
        returning_production=0.5,
        elo_rating=elo,
        initial_rating=elo,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


# Monotonic source of athlete ids. Not hash(name): string hashing is randomized
# per process, so hash-derived ids collide at random and trip the unique
# constraint on athlete_id.
_athlete_ids = itertools.count(500000)


def _make_roster_player(
    db: Session,
    team_id: int,
    season: int,
    name: str,
    position: str,
    rating: float,
) -> RosterPlayer:
    """Helper: create a RosterPlayer entry."""
    player = RosterPlayer(
        season=season,
        team_id=team_id,
        athlete_id=next(_athlete_ids),
        name=name,
        position=position,
        rating=rating,
        blended_rating=rating,
        source="roster",
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@pytest.mark.unit
class TestPreseasonSeasonAlignment:
    """Tests to verify that preseason calculations correctly align with the specified season."""

    def test_calculate_preseason_rating_uses_correct_season_roster(self, test_db: Session):
        """Verify calculate_preseason_rating uses the roster of the specified season."""
        team = _make_team(test_db, "TestTeam")

        # 2025: Strong roster (QB rating 95.0)
        _make_roster_player(test_db, team.id, 2025, "QB 2025", "QB", 95.0)

        # 2026: Weak roster (QB rating 65.0)
        _make_roster_player(test_db, team.id, 2026, "QB 2026", "QB", 65.0)

        # Enable position strength
        enabled_config = {
            "version": "1.0",
            "enabled": True,
            "source": "roster",
            "blend": True,
            "weights": {
                "QB": 1.0,  # 100% QB for simplicity
                "OL": 0.0, "DL": 0.0, "DB": 0.0, "LB": 0.0,
                "RB": 0.0, "WR": 0.0, "TE": 0.0, "ST": 0.0
            },
            "max_bonus": 100,
            "top_players_per_position": {
                "QB": 1, "OL": 1, "DL": 1, "DB": 1, "LB": 1,
                "RB": 1, "WR": 1, "TE": 1, "ST": 1
            },
            "previous_season_weight": 0.0,  # Disable previous season regression for isolation
        }

        service = RankingService(test_db)
        with patch("src.core.position_service.load_position_weights", return_value=enabled_config):
            # Calculate ratings for both seasons
            rating_2025 = service.calculate_preseason_rating(team, season=2025)
            rating_2026 = service.calculate_preseason_rating(team, season=2026)

            # 2025 should have higher rating due to stronger QB
            assert rating_2025 > rating_2026

            # Specific expected bonuses:
            # Base = 1500, returning production = 10, position bonus = 95/65
            assert rating_2025 == 1500.0 + 10.0 + 95.0
            assert rating_2026 == 1500.0 + 10.0 + 65.0

    def test_get_preseason_components_uses_correct_season_roster(self, test_db: Session):
        """Verify get_preseason_components uses the roster of the specified season."""
        team = _make_team(test_db, "TestTeam")

        # 2025: Strong roster (QB rating 90.0)
        _make_roster_player(test_db, team.id, 2025, "QB 2025", "QB", 90.0)

        # 2026: Weak roster (QB rating 70.0)
        _make_roster_player(test_db, team.id, 2026, "QB 2026", "QB", 70.0)

        enabled_config = {
            "version": "1.0",
            "enabled": True,
            "source": "roster",
            "blend": True,
            "weights": {
                "QB": 1.0,
                "OL": 0.0, "DL": 0.0, "DB": 0.0, "LB": 0.0,
                "RB": 0.0, "WR": 0.0, "TE": 0.0, "ST": 0.0
            },
            "max_bonus": 100,
            "top_players_per_position": {
                "QB": 1, "OL": 1, "DL": 1, "DB": 1, "LB": 1,
                "RB": 1, "WR": 1, "TE": 1, "ST": 1
            },
            "previous_season_weight": 0.0,
        }

        service = RankingService(test_db)
        with patch("src.core.position_service.load_position_weights", return_value=enabled_config):
            components_2025 = service.get_preseason_components(season=2025)
            components_2026 = service.get_preseason_components(season=2026)

            team_comp_2025 = next(c for c in components_2025 if c["team_id"] == team.id)
            team_comp_2026 = next(c for c in components_2026 if c["team_id"] == team.id)

            assert team_comp_2025["position_strength_bonus"] == 90.0
            assert team_comp_2026["position_strength_bonus"] == 70.0

    def test_reset_season_recalculates_using_correct_season_roster(self, test_db: Session):
        """Verify reset_season recalculates ELO using the correct season's roster."""
        team = _make_team(test_db, "TestTeam")

        # 2025: Strong roster (QB rating 90.0)
        _make_roster_player(test_db, team.id, 2025, "QB 2025", "QB", 90.0)

        # 2026: Weak roster (QB rating 70.0)
        _make_roster_player(test_db, team.id, 2026, "QB 2026", "QB", 70.0)

        enabled_config = {
            "version": "1.0",
            "enabled": True,
            "source": "roster",
            "blend": True,
            "weights": {
                "QB": 1.0,
                "OL": 0.0, "DL": 0.0, "DB": 0.0, "LB": 0.0,
                "RB": 0.0, "WR": 0.0, "TE": 0.0, "ST": 0.0
            },
            "max_bonus": 100,
            "top_players_per_position": {
                "QB": 1, "OL": 1, "DL": 1, "DB": 1, "LB": 1,
                "RB": 1, "WR": 1, "TE": 1, "ST": 1
            },
            "previous_season_weight": 0.0,
        }

        service = RankingService(test_db)
        with patch("src.core.position_service.load_position_weights", return_value=enabled_config):
            # Reset season for 2025
            service.reset_season(2025)
            assert team.elo_rating == 1500.0 + 10.0 + 90.0
            assert team.initial_rating == 1500.0 + 10.0 + 90.0

            # Reset season for 2026
            service.reset_season(2026)
            assert team.elo_rating == 1500.0 + 10.0 + 70.0
            assert team.initial_rating == 1500.0 + 10.0 + 70.0
