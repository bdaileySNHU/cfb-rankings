"""Unit Tests for Position Strength Integration with Ranking Service

Tests the integration of position strength calculation into preseason rating
calculation, including feature flag behavior and graceful degradation.

Part of Preseason Enhancement Epic - Story 1.6
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from src.core.ranking_service import RankingService
from src.models.models import ConferenceType, Player, Team


@pytest.mark.unit
class TestPositionStrengthIntegration:
    """Tests for position strength integration in preseason rating calculation"""

    def test_preseason_rating_with_feature_disabled(self, test_db: Session):
        """Test that position bonus is 0.0 when feature disabled"""
        # Create team with good traditional metrics
        team = Team(
            name="Georgia",
            conference=ConferenceType.POWER_5,
            recruiting_rank=1,
            transfer_portal_rank=1,
            returning_production=0.85,
        )
        test_db.add(team)
        test_db.commit()

        # Add excellent players (should give bonus if enabled)
        for i in range(10):
            player = Player(
                cfbd_athlete_id=10000 + i,
                name=f"5-Star Player {i}",
                team_id=team.id,
                position="QB" if i < 3 else "OL",
                stars=5,
                rating=98.0,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Calculate preseason rating (feature disabled by default)
        ranking_service = RankingService(test_db)
        rating = ranking_service.calculate_preseason_rating(team)

        # Expected: base (1500) + recruiting (200) + transfer (100) + returning (40) = 1840
        # Position bonus should be 0.0 since feature is disabled
        expected_without_position = 1500 + 200 + 100 + 40
        assert rating == expected_without_position

    def test_preseason_rating_with_feature_enabled(self, test_db: Session):
        """Test that position bonus is included when feature enabled"""
        # Create temporary config with feature enabled
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0",
                "enabled": True,  # Enable feature
                "weights": {
                    "QB": 0.50,
                    "OL": 0.50,
                    "DL": 0.0,
                    "DB": 0.0,
                    "LB": 0.0,
                    "RB": 0.0,
                    "WR": 0.0,
                    "TE": 0.0,
                    "ST": 0.0,
                },
                "max_bonus": 100,
                "top_players_per_position": {
                    "QB": 3,
                    "OL": 3,
                    "DL": 3,
                    "DB": 3,
                    "LB": 3,
                    "RB": 3,
                    "WR": 3,
                    "TE": 3,
                    "ST": 3,
                },
            }
            json.dump(config, f)
            temp_path = f.name

        try:
            # Create team
            team = Team(
                name="Alabama",
                conference=ConferenceType.POWER_5,
                recruiting_rank=2,
                transfer_portal_rank=5,
                returning_production=0.70,
            )
            test_db.add(team)
            test_db.commit()

            # Add excellent QB and OL players (both weighted at 50%)
            for i in range(3):
                qb = Player(
                    cfbd_athlete_id=20000 + i,
                    name=f"QB {i}",
                    team_id=team.id,
                    position="QB",
                    rating=95.0,
                    recruiting_year=2024,
                )
                ol = Player(
                    cfbd_athlete_id=21000 + i,
                    name=f"OL {i}",
                    team_id=team.id,
                    position="OL",
                    rating=90.0,
                    recruiting_year=2024,
                )
                test_db.add(qb)
                test_db.add(ol)
            test_db.commit()

            # Mock load_position_weights to use temp config
            with patch(
                "src.core.position_service.load_position_weights"
            ) as mock_load:
                mock_load.return_value = config

                ranking_service = RankingService(test_db)
                rating = ranking_service.calculate_preseason_rating(team)

                # Expected without position: 1500 + 200 + 100 + 25 = 1825
                # (transfer_rank=5 → 100, not 75; returning=0.70 → 25)
                # Position bonus: QB (95.0 * 0.5) + OL (90.0 * 0.5) = 47.5 + 45.0 = 92.5
                # Total: 1825 + 92.5 = 1917.5
                expected_base = 1500 + 200 + 100 + 25
                assert rating > expected_base  # Should include position bonus
                assert rating <= expected_base + 100  # Shouldn't exceed max_bonus

        finally:
            Path(temp_path).unlink()

    def test_preseason_rating_without_player_data(self, test_db: Session):
        """Test that bonus is 0.0 when team has no player data"""
        team = Team(
            name="Team With No Players",
            conference=ConferenceType.POWER_5,
            recruiting_rank=10,
            transfer_portal_rank=10,
            returning_production=0.60,
        )
        test_db.add(team)
        test_db.commit()

        # Enable feature but team has no players
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0",
                "enabled": True,
                "weights": {"QB": 1.0},
                "max_bonus": 150,
                "top_players_per_position": {"QB": 3},
            }
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch(
                "src.core.position_service.load_position_weights"
            ) as mock_load:
                mock_load.return_value = config

                ranking_service = RankingService(test_db)
                rating = ranking_service.calculate_preseason_rating(team)

                # Should get base + recruiting + transfer + returning, but no position bonus
                expected = 1500 + 150 + 75 + 25
                assert rating == expected

        finally:
            Path(temp_path).unlink()

    def test_preseason_rating_handles_config_error_gracefully(self, test_db: Session):
        """Test that config loading errors don't break rating calculation"""
        team = Team(
            name="Test Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=5,
            transfer_portal_rank=5,
            returning_production=0.80,
        )
        test_db.add(team)
        test_db.commit()

        # Mock load_position_weights to raise FileNotFoundError
        with patch(
            "src.core.position_service.load_position_weights"
        ) as mock_load:
            mock_load.side_effect = FileNotFoundError("Config not found")

            ranking_service = RankingService(test_db)
            rating = ranking_service.calculate_preseason_rating(team)

            # Should still calculate rating without position bonus
            expected = 1500 + 200 + 100 + 40
            assert rating == expected

    def test_preseason_rating_handles_calculation_error_gracefully(self, test_db: Session):
        """Test that calculation errors don't break rating calculation"""
        team = Team(
            name="Test Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=1,
            transfer_portal_rank=1,
            returning_production=0.85,
        )
        test_db.add(team)
        test_db.commit()

        # Mock calculate_position_strength to raise exception
        with patch(
            "src.core.position_service.calculate_position_strength"
        ) as mock_calc:
            mock_calc.side_effect = Exception("Calculation error")

            # Also need to mock load_position_weights to enable feature
            with patch(
                "src.core.position_service.load_position_weights"
            ) as mock_load:
                mock_load.return_value = {
                    "enabled": True,
                    "weights": {"QB": 1.0},
                    "max_bonus": 150,
                }

                ranking_service = RankingService(test_db)
                rating = ranking_service.calculate_preseason_rating(team)

                # Should still calculate rating without position bonus
                expected = 1500 + 200 + 100 + 40
                assert rating == expected

    def test_initialize_team_rating_includes_position_strength(self, test_db: Session):
        """Test that initialize_team_rating uses calculate_preseason_rating"""
        team = Team(
            name="Clemson",
            conference=ConferenceType.POWER_5,
            recruiting_rank=3,
            transfer_portal_rank=8,
            returning_production=0.75,
        )
        test_db.add(team)
        test_db.commit()

        # Add some players
        for i in range(5):
            player = Player(
                cfbd_athlete_id=30000 + i,
                name=f"Player {i}",
                team_id=team.id,
                position="QB",
                rating=92.0,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        ranking_service = RankingService(test_db)

        # Initialize team rating
        ranking_service.initialize_team_rating(team)
        test_db.refresh(team)

        # Verify rating was set
        assert team.elo_rating > 0
        assert team.initial_rating == team.elo_rating

        # Rating should include base + recruiting + transfer + returning
        # (position bonus is 0.0 since feature disabled by default)
        expected_min = 1500 + 100  # At least base + some bonuses
        assert team.elo_rating >= expected_min

    def test_fcs_team_base_rating_unchanged(self, test_db: Session):
        """Test that FCS teams still get correct base rating"""
        team = Team(
            name="FCS Team",
            conference=ConferenceType.FCS,
            recruiting_rank=999,
            transfer_portal_rank=999,
            returning_production=0.30,
        )
        test_db.add(team)
        test_db.commit()

        ranking_service = RankingService(test_db)
        rating = ranking_service.calculate_preseason_rating(team)

        # FCS base is 1300, no bonuses
        assert rating == 1300.0

    def test_position_bonus_respects_max_bonus_limit(self, test_db: Session):
        """Test that position bonus doesn't exceed configured max"""
        # Create team with perfect players
        team = Team(
            name="Super Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=1,
            transfer_portal_rank=1,
            returning_production=0.90,
        )
        test_db.add(team)
        test_db.commit()

        # Add perfect players at all positions
        positions = ["QB", "OL", "DL", "DB", "LB", "RB", "WR"]
        for pos in positions:
            for i in range(5):
                player = Player(
                    cfbd_athlete_id=40000 + hash(f"{pos}{i}") % 10000,
                    name=f"{pos} Player {i}",
                    team_id=team.id,
                    position=pos,
                    rating=99.0,  # Perfect rating
                    recruiting_year=2024,
                )
                test_db.add(player)
        test_db.commit()

        # Enable feature with low max_bonus
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0",
                "enabled": True,
                "weights": {
                    "QB": 0.30,
                    "OL": 0.25,
                    "DL": 0.20,
                    "DB": 0.15,
                    "LB": 0.05,
                    "RB": 0.025,
                    "WR": 0.025,
                    "TE": 0.0,
                    "ST": 0.0,
                },
                "max_bonus": 50,  # Low max
                "top_players_per_position": {
                    "QB": 3,
                    "OL": 5,
                    "DL": 5,
                    "DB": 4,
                    "LB": 3,
                    "RB": 2,
                    "WR": 3,
                    "TE": 2,
                    "ST": 1,
                },
            }
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch(
                "src.core.position_service.load_position_weights"
            ) as mock_load:
                mock_load.return_value = config

                ranking_service = RankingService(test_db)
                rating = ranking_service.calculate_preseason_rating(team)

                # Position bonus should not exceed 50
                expected_base = 1500 + 200 + 100 + 40  # 1840
                assert rating <= expected_base + 50

        finally:
            Path(temp_path).unlink()
