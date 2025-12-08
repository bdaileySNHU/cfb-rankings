"""
Unit tests for prediction accuracy evaluation (EPIC-009 Story 002)

Tests the evaluate_prediction_accuracy function and accuracy statistics.
"""

from datetime import datetime

import pytest

from src.models.models import ConferenceType, Game, Prediction, Team
from src.core.ranking_service import (
    evaluate_prediction_accuracy,
    get_overall_prediction_accuracy,
    get_team_prediction_accuracy,
)


@pytest.fixture
def test_game_with_prediction(test_db):
    """Create a test game with a prediction"""
    import random

    unique_id = random.randint(10000, 99999)

    # Create teams
    home_team = Team(
        name=f"Test Home Team {unique_id}",
        conference=ConferenceType.POWER_5,
        is_fcs=False,
        elo_rating=1650.0,
    )
    away_team = Team(
        name=f"Test Away Team {unique_id}",
        conference=ConferenceType.POWER_5,
        is_fcs=False,
        elo_rating=1550.0,
    )

    test_db.add(home_team)
    test_db.add(away_team)
    test_db.commit()
    test_db.refresh(home_team)
    test_db.refresh(away_team)

    # Create a completed game (home team wins 35-28)
    game = Game(
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_score=35,
        away_score=28,
        week=10,
        season=2024,
        is_processed=True,
        excluded_from_rankings=False,
    )
    test_db.add(game)
    test_db.commit()
    test_db.refresh(game)

    # Create a prediction (predicted home team to win)
    prediction = Prediction(
        game_id=game.id,
        predicted_winner_id=home_team.id,
        predicted_home_score=30,
        predicted_away_score=24,
        win_probability=0.65,
        home_elo_at_prediction=1650.0,
        away_elo_at_prediction=1550.0,
        was_correct=None,  # Not yet evaluated
    )
    test_db.add(prediction)
    test_db.commit()
    test_db.refresh(prediction)

    return game, prediction, home_team, away_team


@pytest.mark.unit
class TestPredictionAccuracyEvaluation:
    """Test prediction accuracy evaluation"""

    def test_evaluate_correct_prediction(self, test_db, test_game_with_prediction):
        """Test evaluating a correct prediction"""
        game, prediction, home_team, away_team = test_game_with_prediction

        # Verify prediction not yet evaluated
        assert prediction.was_correct is None

        # Evaluate prediction
        result = evaluate_prediction_accuracy(test_db, game)

        # Assertions
        assert result is not None
        assert result.id == prediction.id
        assert result.was_correct is True  # Home team was predicted and won

    def test_evaluate_incorrect_prediction(self, test_db):
        """Test evaluating an incorrect prediction"""
        import random

        unique_id = random.randint(10000, 99999)

        # Create teams
        home_team = Team(
            name=f"Test Home Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1550.0,
        )
        away_team = Team(
            name=f"Test Away Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1650.0,
        )
        test_db.add_all([home_team, away_team])
        test_db.commit()
        test_db.refresh(home_team)
        test_db.refresh(away_team)

        # Create a completed game (away team wins 35-21)
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=21,
            away_score=35,
            week=11,
            season=2024,
            is_processed=True,
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Create a prediction (incorrectly predicted home team to win)
        prediction = Prediction(
            game_id=game.id,
            predicted_winner_id=home_team.id,  # Wrong!
            predicted_home_score=28,
            predicted_away_score=24,
            win_probability=0.55,
            home_elo_at_prediction=1550.0,
            away_elo_at_prediction=1650.0,
            was_correct=None,
        )
        test_db.add(prediction)
        test_db.commit()

        # Evaluate prediction
        result = evaluate_prediction_accuracy(test_db, game)

        # Assertions
        assert result is not None
        assert result.was_correct is False  # Prediction was wrong

    def test_evaluate_no_prediction(self, test_db):
        """Test evaluating a game with no prediction"""
        import random

        unique_id = random.randint(10000, 99999)

        # Create teams
        home_team = Team(
            name=f"Test Home Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1600.0,
        )
        away_team = Team(
            name=f"Test Away Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1600.0,
        )
        test_db.add_all([home_team, away_team])
        test_db.commit()
        test_db.refresh(home_team)
        test_db.refresh(away_team)

        # Create a completed game with no prediction
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=24,
            away_score=21,
            week=12,
            season=2024,
            is_processed=True,
        )
        test_db.add(game)
        test_db.commit()

        # Evaluate prediction (should return None)
        result = evaluate_prediction_accuracy(test_db, game)

        assert result is None

    def test_evaluate_unprocessed_game(self, test_db):
        """Test evaluating an unprocessed game"""
        import random

        unique_id = random.randint(10000, 99999)

        # Create teams
        home_team = Team(
            name=f"Test Home Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1600.0,
        )
        away_team = Team(
            name=f"Test Away Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1600.0,
        )
        test_db.add_all([home_team, away_team])
        test_db.commit()
        test_db.refresh(home_team)
        test_db.refresh(away_team)

        # Create an unprocessed game
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=0,
            away_score=0,
            week=13,
            season=2024,
            is_processed=False,  # Not yet played
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Create a prediction
        prediction = Prediction(
            game_id=game.id,
            predicted_winner_id=home_team.id,
            predicted_home_score=28,
            predicted_away_score=24,
            win_probability=0.60,
            home_elo_at_prediction=1600.0,
            away_elo_at_prediction=1600.0,
            was_correct=None,
        )
        test_db.add(prediction)
        test_db.commit()

        # Try to evaluate (should return None for unprocessed game)
        result = evaluate_prediction_accuracy(test_db, game)

        assert result is None


@pytest.mark.unit
class TestPredictionAccuracyStats:
    """Test prediction accuracy statistics functions"""

    def test_overall_accuracy_calculation(self, test_db):
        """Test overall accuracy statistics calculation"""
        import random

        # Use a unique test season to avoid conflicts with existing data
        test_season = random.randint(2050, 2099)
        unique_id = random.randint(10000, 99999)

        # Create teams
        teams = []
        for i in range(4):
            team = Team(
                name=f"Test Team {unique_id}-{i}",
                conference=ConferenceType.POWER_5,
                is_fcs=False,
                elo_rating=1600.0,
            )
            teams.append(team)
            test_db.add(team)

        test_db.commit()
        for team in teams:
            test_db.refresh(team)

        # Create games with predictions (2 correct, 1 incorrect, 1 not evaluated)
        predictions_data = [
            # Correct predictions
            {
                "home_id": teams[0].id,
                "away_id": teams[1].id,
                "home_score": 35,
                "away_score": 28,
                "predicted_winner": teams[0].id,
                "processed": True,
                "week": 1,
            },
            {
                "home_id": teams[2].id,
                "away_id": teams[3].id,
                "home_score": 21,
                "away_score": 28,
                "predicted_winner": teams[3].id,
                "processed": True,
                "week": 2,
            },
            # Incorrect prediction
            {
                "home_id": teams[0].id,
                "away_id": teams[2].id,
                "home_score": 14,
                "away_score": 24,
                "predicted_winner": teams[0].id,
                "processed": True,
                "week": 3,
            },
            # Not yet evaluated
            {
                "home_id": teams[1].id,
                "away_id": teams[3].id,
                "home_score": 0,
                "away_score": 0,
                "predicted_winner": teams[1].id,
                "processed": False,
                "week": 4,
            },
        ]

        for pred_data in predictions_data:
            game = Game(
                home_team_id=pred_data["home_id"],
                away_team_id=pred_data["away_id"],
                home_score=pred_data["home_score"],
                away_score=pred_data["away_score"],
                week=pred_data["week"],
                season=test_season,  # Use unique test season
                is_processed=pred_data["processed"],
            )
            test_db.add(game)
            test_db.commit()
            test_db.refresh(game)

            prediction = Prediction(
                game_id=game.id,
                predicted_winner_id=pred_data["predicted_winner"],
                predicted_home_score=28,
                predicted_away_score=24,
                win_probability=0.60,
                home_elo_at_prediction=1600.0,
                away_elo_at_prediction=1600.0,
            )
            test_db.add(prediction)
            test_db.commit()  # Commit prediction

            if pred_data["processed"]:
                evaluate_prediction_accuracy(test_db, game)
                test_db.commit()  # Commit after each evaluation

        # Get overall accuracy for our test season
        stats = get_overall_prediction_accuracy(test_db, season=test_season)

        # Assertions
        assert stats["total_predictions"] == 4
        assert stats["evaluated_predictions"] == 3  # 3 processed games
        assert stats["correct_predictions"] == 2  # 2 correct predictions
        assert stats["accuracy_percentage"] == pytest.approx(66.67, rel=0.1)  # 2/3 = 66.67%

    def test_team_accuracy_calculation(self, test_db):
        """Test team-specific accuracy calculation"""
        import random

        # Use a unique test season to avoid conflicts with existing data
        test_season = random.randint(2050, 2099)
        unique_id = random.randint(10000, 99999)

        # Create target team and opponents
        target_team = Team(
            name=f"Target Team {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1650.0,
        )
        opponent1 = Team(
            name=f"Opponent 1 {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1550.0,
        )
        opponent2 = Team(
            name=f"Opponent 2 {unique_id}",
            conference=ConferenceType.POWER_5,
            is_fcs=False,
            elo_rating=1700.0,
        )
        test_db.add_all([target_team, opponent1, opponent2])
        test_db.commit()
        for team in [target_team, opponent1, opponent2]:
            test_db.refresh(team)

        # Create games involving target team
        # Game 1: Target team wins as favorite (correct prediction)
        game1 = Game(
            home_team_id=target_team.id,
            away_team_id=opponent1.id,
            home_score=35,
            away_score=28,
            week=1,
            season=test_season,  # Use unique test season
            is_processed=True,
        )
        test_db.add(game1)
        test_db.commit()
        test_db.refresh(game1)

        pred1 = Prediction(
            game_id=game1.id,
            predicted_winner_id=target_team.id,
            predicted_home_score=31,
            predicted_away_score=24,
            win_probability=0.70,
            home_elo_at_prediction=1650.0,
            away_elo_at_prediction=1550.0,
        )
        test_db.add(pred1)
        test_db.commit()  # Commit prediction
        evaluate_prediction_accuracy(test_db, game1)
        test_db.commit()  # Commit evaluation

        # Game 2: Target team loses as underdog (correct prediction)
        game2 = Game(
            home_team_id=opponent2.id,
            away_team_id=target_team.id,
            home_score=31,
            away_score=24,
            week=2,
            season=test_season,  # Use unique test season
            is_processed=True,
        )
        test_db.add(game2)
        test_db.commit()
        test_db.refresh(game2)

        pred2 = Prediction(
            game_id=game2.id,
            predicted_winner_id=opponent2.id,  # Predicted opponent to win
            predicted_home_score=28,
            predicted_away_score=21,
            win_probability=0.60,
            home_elo_at_prediction=1700.0,
            away_elo_at_prediction=1650.0,
        )
        test_db.add(pred2)
        test_db.commit()  # Commit prediction
        evaluate_prediction_accuracy(test_db, game2)
        test_db.commit()  # Commit evaluation

        # Get team accuracy
        stats = get_team_prediction_accuracy(test_db, target_team.id, season=test_season)

        # Assertions
        assert stats["team_id"] == target_team.id
        assert stats["team_name"] == target_team.name
        assert stats["total_predictions"] == 2
        assert stats["evaluated_predictions"] == 2
        assert stats["correct_predictions"] == 2  # Both predictions were correct
        assert stats["accuracy_percentage"] == 100.0
        assert stats["as_favorite_accuracy"] == 100.0  # 1/1 correct as favorite
        assert stats["as_underdog_accuracy"] == 100.0  # 1/1 correct as underdog
