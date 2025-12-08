"""
Unit tests for prediction functions
"""

import pytest

from src.models.models import ConferenceType, Game, Team
from src.core.ranking_service import (
    _calculate_game_prediction,
    _validate_prediction_teams,
    validate_game_for_prediction,
    validate_predicted_score,
    validate_team_for_prediction,
    validate_week,
)


class TestWinProbabilityCalculation:
    """Test ELO-based win probability calculation"""

    def test_equal_ratings_neutral_site(self):
        """Test that equal ratings on neutral site result in 50% probability"""
        home_team = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Team B",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        assert prediction["home_win_probability"] == 50.0
        assert prediction["away_win_probability"] == 50.0

    def test_home_field_advantage(self):
        """Test home field advantage applied correctly"""
        home_team = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Team B",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=False,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Home team should have > 50% win probability due to HFA
        assert prediction["home_win_probability"] > 50.0
        assert prediction["away_win_probability"] < 50.0
        # Should be approximately 59.6% for +65 rating advantage
        assert 59.0 < prediction["home_win_probability"] < 61.0

    def test_rating_difference_affects_probability(self):
        """Test that higher rating leads to higher win probability"""
        home_team = Team(
            id=1,
            name="Strong Team",
            elo_rating=1700,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Weak Team",
            elo_rating=1400,
            conference=ConferenceType.GROUP_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Stronger team should have much higher win probability
        assert prediction["home_win_probability"] > 80.0
        assert prediction["away_win_probability"] < 20.0


class TestScoreEstimation:
    """Test score estimation logic"""

    def test_score_estimation_basic(self):
        """Test basic score estimation"""
        home_team = Team(
            id=1,
            name="Strong Team",
            elo_rating=1700,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Weak Team",
            elo_rating=1400,
            conference=ConferenceType.GROUP_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Stronger team should have higher predicted score
        assert prediction["predicted_home_score"] > prediction["predicted_away_score"]
        # Scores should be reasonable
        assert 0 <= prediction["predicted_home_score"] <= 150
        assert 0 <= prediction["predicted_away_score"] <= 150
        # Check specific values (300 point difference = 10.5 point adjustment each way)
        # Base 30 + 10.5 = 40.5, Base 30 - 10.5 = 19.5
        assert 40 <= prediction["predicted_home_score"] <= 41
        assert 19 <= prediction["predicted_away_score"] <= 20

    def test_score_clamping_at_bounds(self):
        """Test that scores are clamped within 0-150 range"""
        # Extreme case: massive rating difference
        home_team = Team(
            id=1, name="Elite", elo_rating=2200, conference=ConferenceType.POWER_5, wins=0, losses=0
        )
        away_team = Team(
            id=2, name="Very Weak", elo_rating=1000, conference=ConferenceType.FCS, wins=0, losses=0
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Scores must be within valid range
        assert 0 <= prediction["predicted_home_score"] <= 150
        assert 0 <= prediction["predicted_away_score"] <= 150

    def test_equal_ratings_equal_scores(self):
        """Test that equal ratings produce equal predicted scores"""
        home_team = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Team B",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Equal ratings should produce equal scores (base score = 30)
        assert prediction["predicted_home_score"] == 30
        assert prediction["predicted_away_score"] == 30


class TestConfidenceLevels:
    """Test confidence level assignment"""

    def test_high_confidence(self):
        """Test high confidence for large rating difference"""
        home_team = Team(
            id=1, name="Elite", elo_rating=1800, conference=ConferenceType.POWER_5, wins=0, losses=0
        )
        away_team = Team(
            id=2, name="Weak", elo_rating=1200, conference=ConferenceType.FCS, wins=0, losses=0
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        assert prediction["confidence"] == "High"

    def test_medium_confidence(self):
        """Test medium confidence for moderate rating difference"""
        home_team = Team(
            id=1,
            name="Better Team",
            elo_rating=1600,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Decent Team",
            elo_rating=1450,
            conference=ConferenceType.GROUP_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        assert prediction["confidence"] == "Medium"

    def test_low_confidence(self):
        """Test low confidence for close matchup"""
        home_team = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Team B",
            elo_rating=1490,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        assert prediction["confidence"] == "Low"


class TestValidation:
    """Test team validation logic"""

    def test_validation_valid_teams(self):
        """Test validation passes for valid teams"""
        valid_team_1 = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        valid_team_2 = Team(
            id=2,
            name="Team B",
            elo_rating=1600,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )

        assert _validate_prediction_teams(valid_team_1, valid_team_2) == True

    def test_validation_invalid_rating(self):
        """Test validation fails for teams with invalid ratings"""
        valid_team = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        invalid_team = Team(
            id=2, name="Team B", elo_rating=0, conference=ConferenceType.POWER_5, wins=0, losses=0
        )

        assert _validate_prediction_teams(valid_team, invalid_team) == False
        assert _validate_prediction_teams(invalid_team, valid_team) == False

    def test_validation_none_team(self):
        """Test validation fails for None teams"""
        valid_team = Team(
            id=1,
            name="Team A",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )

        assert _validate_prediction_teams(None, valid_team) == False
        assert _validate_prediction_teams(valid_team, None) == False
        assert _validate_prediction_teams(None, None) == False


class TestPredictionOutput:
    """Test prediction output structure"""

    def test_prediction_contains_all_fields(self):
        """Test that prediction dict contains all required fields"""
        home_team = Team(
            id=1,
            name="Home Team",
            elo_rating=1600,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Away Team",
            elo_rating=1500,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=42,
            week=5,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=False,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Check all required fields exist
        required_fields = [
            "game_id",
            "home_team_id",
            "home_team",
            "away_team_id",
            "away_team",
            "week",
            "season",
            "game_date",
            "is_neutral_site",
            "predicted_winner",
            "predicted_winner_id",
            "predicted_home_score",
            "predicted_away_score",
            "home_win_probability",
            "away_win_probability",
            "confidence",
            "home_team_rating",
            "away_team_rating",
        ]

        for field in required_fields:
            assert field in prediction

        # Check specific values
        assert prediction["game_id"] == 42
        assert prediction["home_team"] == "Home Team"
        assert prediction["away_team"] == "Away Team"
        assert prediction["week"] == 5
        assert prediction["season"] == 2025

    def test_predicted_winner_correct(self):
        """Test that predicted winner is correctly identified"""
        home_team = Team(
            id=1,
            name="Strong Home",
            elo_rating=1700,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Weak Away",
            elo_rating=1400,
            conference=ConferenceType.GROUP_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Stronger team should be predicted winner
        assert prediction["predicted_winner"] == "Strong Home"
        assert prediction["predicted_winner_id"] == 1

    def test_probabilities_sum_to_100(self):
        """Test that win probabilities sum to 100%"""
        home_team = Team(
            id=1,
            name="Team A",
            elo_rating=1550,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        away_team = Team(
            id=2,
            name="Team B",
            elo_rating=1450,
            conference=ConferenceType.POWER_5,
            wins=0,
            losses=0,
        )
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_neutral_site=True,
            is_processed=False,
        )

        prediction = _calculate_game_prediction(game, home_team, away_team)

        # Probabilities should sum to 100 (allowing for rounding)
        total = prediction["home_win_probability"] + prediction["away_win_probability"]
        assert 99.9 <= total <= 100.1


class TestValidationFunctions:
    """Test standalone validation functions added in Story 003"""

    def test_validate_week_valid(self):
        """Test valid week numbers"""
        assert validate_week(0) == True  # Preseason
        assert validate_week(1) == True
        assert validate_week(8) == True
        assert validate_week(15) == True  # Postseason

    def test_validate_week_invalid(self):
        """Test invalid week numbers"""
        assert validate_week(-1) == False
        assert validate_week(16) == False
        assert validate_week(100) == False

    def test_validate_team_for_prediction_valid(self):
        """Test valid team for prediction"""
        team = Team(id=1, name="Valid Team", elo_rating=1500, conference=ConferenceType.POWER_5)
        assert validate_team_for_prediction(team) == True

    def test_validate_team_for_prediction_invalid_rating(self):
        """Test team with invalid rating"""
        team = Team(id=1, name="Invalid Team", elo_rating=0, conference=ConferenceType.POWER_5)
        assert validate_team_for_prediction(team) == False

        team.elo_rating = -100
        assert validate_team_for_prediction(team) == False

    def test_validate_team_for_prediction_none(self):
        """Test None team"""
        assert validate_team_for_prediction(None) == False

    def test_validate_predicted_score_clamping(self):
        """Test score clamping to valid range"""
        assert validate_predicted_score(30) == 30  # Valid
        assert validate_predicted_score(0) == 0  # Min
        assert validate_predicted_score(150) == 150  # Max
        assert validate_predicted_score(-10) == 0  # Below min
        assert validate_predicted_score(200) == 150  # Above max

    def test_validate_game_for_prediction_unprocessed(self):
        """Test unprocessed game is valid"""
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_processed=False,
        )
        assert validate_game_for_prediction(game) == True

    def test_validate_game_for_prediction_processed(self):
        """Test processed game is invalid"""
        game = Game(
            id=1,
            week=1,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=35,
            away_score=28,
            is_processed=True,
        )
        assert validate_game_for_prediction(game) == False

    def test_validate_game_for_prediction_invalid_week(self):
        """Test game with invalid week"""
        game = Game(
            id=1,
            week=99,
            season=2025,
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            is_processed=False,
        )
        assert validate_game_for_prediction(game) == False
