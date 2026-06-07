"""Unit Tests for Position Strength Calculation Service

Tests the position_service module including:
- Configuration loading and validation
- Position group score calculation
- Player rating aggregation
- Overall position strength bonus calculation
- Graceful degradation for missing data
- Edge cases and error handling

Part of Preseason Enhancement Epic - Story 1.3
"""

import copy
import json
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from src.core.position_service import (
    POSITION_GROUPS,
    aggregate_player_ratings,
    calculate_position_strength,
    get_position_group_scores,
    load_position_weights,
)
from src.models.models import ConferenceType, Player, RosterPlayer, Team


def _config_with_source(source: str, blend: bool = False) -> dict:
    """Default config with the data source overridden (blend off by default).

    Most roster tests exercise recruiting-rating scoring, so blend defaults to
    False; the EPIC-040 blend tests opt in explicitly.
    """
    cfg = copy.deepcopy(load_position_weights())
    cfg["source"] = source
    cfg["blend"] = blend
    return cfg


@pytest.mark.unit
class TestLoadPositionWeights:
    """Tests for load_position_weights() function"""

    def test_load_default_config(self):
        """Test loading default position_weights.json configuration"""
        config = load_position_weights()

        assert "version" in config
        assert "enabled" in config
        assert "weights" in config
        assert "max_bonus" in config
        assert "top_players_per_position" in config

        # Verify default values
        # Note: enabled=True was set in EPIC-029 (Story 29.4) for production use
        assert isinstance(config["enabled"], bool)
        assert config["max_bonus"] == 150
        assert config["weights"]["QB"] == 0.30
        assert config["weights"]["OL"] == 0.25

    def test_weights_sum_to_one(self):
        """Test that position weights sum to 1.0"""
        config = load_position_weights()
        weights_sum = sum(config["weights"].values())

        # Allow small floating point tolerance
        assert abs(weights_sum - 1.0) < 0.01

    def test_load_custom_config_path(self):
        """Test loading configuration from custom path"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            custom_config = {
                "version": "1.0",
                "enabled": True,
                "weights": {"QB": 0.5, "OL": 0.3, "DL": 0.2},
                "max_bonus": 200,
                "top_players_per_position": {"QB": 2, "OL": 4, "DL": 4},
            }
            json.dump(custom_config, f)
            temp_path = f.name

        try:
            config = load_position_weights(temp_path)
            assert config["enabled"] is True
            assert config["max_bonus"] == 200
            assert config["weights"]["QB"] == 0.5
        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_config_raises_error(self):
        """Test that loading non-existent config raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_position_weights("/nonexistent/path/config.json")

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises JSONDecodeError"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_position_weights(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_validation_missing_required_key(self):
        """Test that config missing required key raises ValueError"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Missing 'enabled' key
            invalid_config = {
                "version": "1.0",
                "weights": {"QB": 1.0},
                "max_bonus": 150,
                "top_players_per_position": {"QB": 3},
            }
            json.dump(invalid_config, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="missing required key"):
                load_position_weights(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_validation_weights_dont_sum_to_one(self):
        """Test that weights not summing to 1.0 raises ValueError"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            invalid_config = {
                "version": "1.0",
                "enabled": False,
                "weights": {"QB": 0.5, "OL": 0.3},  # Only sums to 0.8
                "max_bonus": 150,
                "top_players_per_position": {"QB": 3, "OL": 5},
            }
            json.dump(invalid_config, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must sum to 1.0"):
                load_position_weights(temp_path)
        finally:
            Path(temp_path).unlink()


@pytest.mark.unit
class TestGetPositionGroupScores:
    """Tests for get_position_group_scores() function"""

    def test_calculate_scores_with_players(self, test_db: Session):
        """Test calculating position scores when team has players"""
        # Create team
        team = Team(name="Georgia", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add players with varying ratings
        players_data = [
            ("QB 1", "QB", 98.0),
            ("QB 2", "QB", 95.0),
            ("QB 3", "QB", 92.0),
            ("OL 1", "OL", 90.0),
            ("OL 2", "OT", 88.0),
            ("OL 3", "OG", 85.0),
            ("DL 1", "DL", 93.0),
            ("DL 2", "DE", 91.0),
        ]

        for name, position, rating in players_data:
            player = Player(
                cfbd_athlete_id=hash(name) % 1000000,
                name=name,
                team_id=team.id,
                position=position,
                rating=rating,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Calculate scores
        scores = get_position_group_scores(team.id, test_db)

        # Verify scores calculated
        assert "QB" in scores
        assert "OL" in scores
        assert "DL" in scores

        # QB score should be average of top 3 QBs: (98 + 95 + 92) / 3 = 95.0
        assert abs(scores["QB"] - 95.0) < 0.01

        # OL score should be average of top 3 OL: (90 + 88 + 85) / 3 = 87.67
        assert abs(scores["OL"] - 87.67) < 0.1

        # DL score should be average of top 2: (93 + 91) / 2 = 92.0
        assert abs(scores["DL"] - 92.0) < 0.01

    def test_normalizes_cfbd_composite_ratings(self, test_db: Session):
        """CFBD 0–1 composite ratings are stretched to a 0–100 score.

        Regression: real CFBD recruit ratings are on a ~0.70–1.00 scale, not
        0–100. Without normalization a strong roster scored ~0.9 instead of ~90,
        making the position strength bonus effectively zero.
        """
        team = Team(name="Composite U", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Three elite QBs averaging 0.97 → (0.97 - 0.70) / 0.30 * 100 = 90.0
        for i, rating in enumerate([0.98, 0.97, 0.96]):
            test_db.add(
                Player(
                    cfbd_athlete_id=20000 + i,
                    name=f"QB {i}",
                    team_id=team.id,
                    position="QB",
                    rating=rating,
                    recruiting_year=2025,
                )
            )
        test_db.commit()

        scores = get_position_group_scores(team.id, test_db)

        assert abs(scores["QB"] - 90.0) < 0.5
        # The raw 0.97 average must NOT pass through unscaled
        assert scores["QB"] > 1.0

    def test_zero_scores_for_missing_positions(self, test_db: Session):
        """Test that positions with no players get score of 0.0"""
        team = Team(name="Test Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add only QB players
        player = Player(
            cfbd_athlete_id=12345,
            name="QB Only",
            team_id=team.id,
            position="QB",
            rating=95.0,
            recruiting_year=2024,
        )
        test_db.add(player)
        test_db.commit()

        scores = get_position_group_scores(team.id, test_db)

        # QB should have score
        assert scores["QB"] > 0

        # Other positions should be 0.0
        assert scores["OL"] == 0.0
        assert scores["DL"] == 0.0
        assert scores["RB"] == 0.0

    def test_team_with_no_players(self, test_db: Session):
        """Test team with no players returns all zeros"""
        team = Team(name="Empty Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        scores = get_position_group_scores(team.id, test_db)

        # All positions should be 0.0
        for position_group in POSITION_GROUPS.keys():
            assert scores[position_group] == 0.0


@pytest.mark.unit
class TestRosterBasedScoring:
    """EPIC-039: get_position_group_scores() with source='roster'"""

    def _team(self, test_db, name):
        team = Team(name=name, conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        return team

    def test_scores_from_roster_snapshot(self, test_db: Session):
        """source='roster' scores from roster_players, normalized 0–1 → 0–100"""
        team = self._team(test_db, "Roster U")
        for i, rating in enumerate([0.98, 0.96]):  # avg 0.97 → ~90
            test_db.add(
                RosterPlayer(
                    season=2025,
                    team_id=team.id,
                    athlete_id=900 + i,
                    name=f"QB {i}",
                    position="QB",
                    class_year=2,
                    rating=rating,
                    source="recruiting-join",
                )
            )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster"), season=2025
        )
        assert abs(scores["QB"] - 90.0) < 1.0

    def test_unrated_roster_players_excluded(self, test_db: Session):
        """Roster players without a resolved rating don't count"""
        team = self._team(test_db, "Mixed U")
        test_db.add(
            RosterPlayer(season=2025, team_id=team.id, athlete_id=1, name="Rated",
                         position="QB", rating=0.90, source="recruiting-join")
        )
        test_db.add(
            RosterPlayer(season=2025, team_id=team.id, athlete_id=2, name="Walk On",
                         position="QB", rating=None, source="unrated")
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster"), season=2025
        )
        # Only the 0.90 player counts: (0.90 - 0.70) / 0.30 * 100 = 66.7
        assert abs(scores["QB"] - 66.7) < 1.0

    def test_departed_player_excluded(self, test_db: Session):
        """A signee who left (not on the roster) does not inflate the score"""
        team = self._team(test_db, "Departure U")
        # Recruiting record: an elite QB who signed here but transferred away
        test_db.add(
            Player(cfbd_athlete_id=555, name="Gone QB", team_id=team.id,
                   position="QB", rating=0.97, recruiting_year=2023)
        )
        # Roster shows only a lower-rated QB actually on the team
        test_db.add(
            RosterPlayer(season=2025, team_id=team.id, athlete_id=777, name="Backup QB",
                         position="QB", rating=0.80, source="recruiting-join")
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster"), season=2025
        )
        # Reflects the 0.80 roster QB (~33), NOT the departed 0.97 recruit
        assert scores["QB"] < 50.0

    def test_transfer_in_counted(self, test_db: Session):
        """A transfer on the roster counts for the new team"""
        team = self._team(test_db, "Reload U")
        test_db.add(
            RosterPlayer(season=2025, team_id=team.id, athlete_id=555, name="Transfer QB",
                         position="QB", rating=0.96, source="recruiting-join")
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster"), season=2025
        )
        assert scores["QB"] > 80.0

    def test_falls_back_to_recruiting_without_snapshot(self, test_db: Session):
        """source='roster' but no snapshot → falls back to recruiting-class data"""
        team = self._team(test_db, "Fallback U")
        test_db.add(
            Player(cfbd_athlete_id=42, name="Recruit QB", team_id=team.id,
                   position="QB", rating=0.95, recruiting_year=2025)
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster"), season=2025
        )
        # No roster rows for this team → recruiting Player used → non-zero
        assert scores["QB"] > 0.0


@pytest.mark.unit
class TestBlendedScoring:
    """EPIC-040: get_position_group_scores() with blend enabled"""

    def _team(self, test_db, name):
        team = Team(name=name, conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        return team

    def test_blend_uses_blended_rating(self, test_db: Session):
        """With blend on, scoring uses blended_rating (0–100), not raw rating"""
        team = self._team(test_db, "Blend U")
        # Low recruiting rating but high blended (e.g. a 3-star who produced)
        test_db.add(
            RosterPlayer(
                season=2025, team_id=team.id, athlete_id=1, name="Riser QB",
                position="QB", rating=0.80, source="ppa",
                production_score=98.0, production_source="ppa", blended_rating=95.0,
            )
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster", blend=True), season=2025
        )
        # Uses blended_rating 95, not the 0.80 recruiting rating (~33)
        assert abs(scores["QB"] - 95.0) < 0.5

    def test_blend_off_uses_recruiting_rating(self, test_db: Session):
        """Same row, blend off → uses raw recruiting rating instead of blended"""
        team = self._team(test_db, "NoBlend U")
        test_db.add(
            RosterPlayer(
                season=2025, team_id=team.id, athlete_id=1, name="Riser QB",
                position="QB", rating=0.80, source="ppa",
                production_score=98.0, production_source="ppa", blended_rating=95.0,
            )
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster", blend=False), season=2025
        )
        # (0.80 - 0.70) / 0.30 * 100 = 33.3
        assert abs(scores["QB"] - 33.3) < 1.0

    def test_blend_excludes_null_blended_rating(self, test_db: Session):
        """Players without a blended_rating are excluded when blend is on"""
        team = self._team(test_db, "Partial U")
        test_db.add(
            RosterPlayer(
                season=2025, team_id=team.id, athlete_id=1, name="Scored QB",
                position="QB", rating=0.90, source="ppa", blended_rating=88.0,
            )
        )
        test_db.add(
            RosterPlayer(
                season=2025, team_id=team.id, athlete_id=2, name="Unscored QB",
                position="QB", rating=0.95, source="none", blended_rating=None,
            )
        )
        test_db.commit()

        scores = get_position_group_scores(
            team.id, test_db, _config_with_source("roster", blend=True), season=2025
        )
        # Only the player with blended_rating=88 counts
        assert abs(scores["QB"] - 88.0) < 0.5


@pytest.mark.unit
class TestAggregatePlayerRatings:
    """Tests for aggregate_player_ratings() function"""

    def test_aggregate_multiple_players(self, test_db: Session):
        """Test aggregating ratings for multiple players"""
        team = Team(name="Test Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Create players with ratings
        players = []
        for i, rating in enumerate([95.0, 90.0, 85.0]):
            player = Player(
                cfbd_athlete_id=10000 + i,
                name=f"Player {i}",
                team_id=team.id,
                position="QB",
                rating=rating,
                recruiting_year=2024,
            )
            test_db.add(player)
            players.append(player)
        test_db.commit()

        # Aggregate
        avg_rating = aggregate_player_ratings(players, "QB")

        # Should be (95 + 90 + 85) / 3 = 90.0
        assert abs(avg_rating - 90.0) < 0.01

    def test_aggregate_empty_list(self, test_db: Session):
        """Test aggregating empty player list returns 0.0"""
        avg_rating = aggregate_player_ratings([], "QB")
        assert avg_rating == 0.0

    def test_aggregate_players_with_none_ratings(self, test_db: Session):
        """Test aggregating players with None ratings"""
        team = Team(name="Test Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Create players, some with None ratings
        players = []
        player1 = Player(
            cfbd_athlete_id=11111,
            name="Player 1",
            team_id=team.id,
            position="QB",
            rating=90.0,
            recruiting_year=2024,
        )
        player2 = Player(
            cfbd_athlete_id=22222,
            name="Player 2",
            team_id=team.id,
            position="QB",
            rating=None,  # No rating
            recruiting_year=2024,
        )
        test_db.add(player1)
        test_db.add(player2)
        test_db.commit()

        players = [player1, player2]

        # Should only use player1's rating
        avg_rating = aggregate_player_ratings(players, "QB")
        assert abs(avg_rating - 90.0) < 0.01

    def test_aggregate_normalizes_to_100(self, test_db: Session):
        """Test that ratings over 100 are capped at 100"""
        team = Team(name="Test Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Create player with rating > 100
        player = Player(
            cfbd_athlete_id=33333,
            name="Super Player",
            team_id=team.id,
            position="QB",
            rating=105.0,  # Over 100
            recruiting_year=2024,
        )
        test_db.add(player)
        test_db.commit()

        avg_rating = aggregate_player_ratings([player], "QB")

        # Should be capped at 100.0
        assert avg_rating == 100.0


@pytest.mark.unit
class TestCalculatePositionStrength:
    """Tests for calculate_position_strength() function"""

    def test_calculate_with_valid_data(self, test_db: Session):
        """Test calculating position strength with valid player data"""
        # Create team
        team = Team(name="Alabama", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add diverse roster
        positions_ratings = [
            ("QB", 98.0),
            ("QB", 95.0),
            ("OL", 92.0),
            ("OL", 90.0),
            ("OL", 88.0),
            ("DL", 93.0),
            ("DL", 91.0),
            ("DB", 89.0),
            ("LB", 85.0),
        ]

        for i, (position, rating) in enumerate(positions_ratings):
            player = Player(
                cfbd_athlete_id=40000 + i,
                name=f"Player {position} {i}",
                team_id=team.id,
                position=position,
                rating=rating,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Define weights
        weights = {
            "QB": 0.30,
            "OL": 0.25,
            "DL": 0.20,
            "DB": 0.15,
            "LB": 0.05,
            "RB": 0.025,
            "WR": 0.025,
            "TE": 0.0,
            "ST": 0.0,
        }

        # Calculate
        bonus = calculate_position_strength(team.id, weights, test_db, max_bonus=150)

        # Should be > 0 since team has good players
        assert bonus > 0
        assert bonus <= 150  # Shouldn't exceed max_bonus

    def test_calculate_with_no_players_returns_zero(self, test_db: Session):
        """Test that team with no players gets 0.0 bonus"""
        team = Team(name="Empty Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        weights = {"QB": 0.5, "OL": 0.3, "DL": 0.2}

        bonus = calculate_position_strength(team.id, weights, test_db)

        assert bonus == 0.0

    def test_weights_must_sum_to_one(self, test_db: Session):
        """Test that weights not summing to 1.0 raises ValueError"""
        team = Team(name="Test Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Invalid weights (sum to 0.8)
        invalid_weights = {"QB": 0.5, "OL": 0.3}

        with pytest.raises(ValueError, match="must sum to 1.0"):
            calculate_position_strength(team.id, invalid_weights, test_db)

    def test_max_bonus_parameter(self, test_db: Session):
        """Test that max_bonus parameter controls maximum points"""
        team = Team(name="Elite Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add elite players across all positions (all 99.0 rating)
        for group_name, positions in POSITION_GROUPS.items():
            for pos in positions[:3]:  # Add 3 players per position
                player = Player(
                    cfbd_athlete_id=hash(f"{group_name}{pos}") % 1000000,
                    name=f"{pos} Elite",
                    team_id=team.id,
                    position=pos,
                    rating=99.0,
                    recruiting_year=2024,
                )
                test_db.add(player)
        test_db.commit()

        weights = {
            "QB": 0.30,
            "OL": 0.25,
            "DL": 0.20,
            "DB": 0.15,
            "LB": 0.05,
            "RB": 0.025,
            "WR": 0.025,
            "TE": 0.0,
            "ST": 0.0,
        }

        # Test with different max_bonus values
        bonus_150 = calculate_position_strength(team.id, weights, test_db, max_bonus=150)
        bonus_200 = calculate_position_strength(team.id, weights, test_db, max_bonus=200)

        # Bonus with higher max should be proportionally larger
        # Since team has nearly perfect scores, both should be close to their max
        assert bonus_150 <= 150
        assert bonus_200 <= 200
        assert bonus_200 > bonus_150

    def test_position_groups_enumeration(self):
        """Test that POSITION_GROUPS covers all expected positions"""
        expected_groups = ["QB", "OL", "RB", "WR", "TE", "DL", "LB", "DB", "ST"]

        assert all(group in POSITION_GROUPS for group in expected_groups)

        # Verify specific position mappings
        assert "QB" in POSITION_GROUPS["QB"]
        assert "OT" in POSITION_GROUPS["OL"]
        assert "OG" in POSITION_GROUPS["OL"]
        assert "C" in POSITION_GROUPS["OL"]
        assert "DT" in POSITION_GROUPS["DL"]
        assert "DE" in POSITION_GROUPS["DL"]
        assert "CB" in POSITION_GROUPS["DB"]
        assert "S" in POSITION_GROUPS["DB"]

    def test_partial_roster_calculation(self, test_db: Session):
        """Test calculating bonus with only some positions filled"""
        team = Team(name="Partial Team", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Add only QB and OL players
        for i in range(3):
            qb = Player(
                cfbd_athlete_id=50000 + i,
                name=f"QB {i}",
                team_id=team.id,
                position="QB",
                rating=95.0,
                recruiting_year=2024,
            )
            ol = Player(
                cfbd_athlete_id=51000 + i,
                name=f"OL {i}",
                team_id=team.id,
                position="OL",
                rating=90.0,
                recruiting_year=2024,
            )
            test_db.add(qb)
            test_db.add(ol)
        test_db.commit()

        weights = {
            "QB": 0.30,
            "OL": 0.25,
            "DL": 0.20,
            "DB": 0.15,
            "LB": 0.05,
            "RB": 0.025,
            "WR": 0.025,
            "TE": 0.0,
            "ST": 0.0,
        }

        bonus = calculate_position_strength(team.id, weights, test_db, max_bonus=150)

        # Should still calculate bonus based on positions with players
        # But will be lower than if all positions were filled
        assert bonus > 0
        assert bonus < 150  # Won't reach max with partial roster
