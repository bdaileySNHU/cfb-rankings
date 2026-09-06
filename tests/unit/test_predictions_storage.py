"""
Unit tests for prediction storage (EPIC-009 Story 001)

Tests the Prediction model and create_and_store_prediction function.
"""

from datetime import datetime

import pytest

from src.models.models import ConferenceType, Game, Prediction, Team
from src.core.ranking_service import create_and_store_prediction


@pytest.fixture
def test_teams(test_db):
    """Create test teams with ELO ratings"""
    import random

    unique_id = random.randint(10000, 99999)

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

    return home_team, away_team


@pytest.mark.unit
class TestPredictionStorage:
    """Test prediction storage functionality"""

    def test_create_prediction_for_future_game(self, test_db, test_teams):
        """Test creating a prediction for a future game"""
        home_team, away_team = test_teams

        # Create a future game (0-0 scores)
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=0,
            away_score=0,
            week=10,
            season=2024,
            is_processed=False,
            excluded_from_rankings=False,
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Create prediction
        prediction = create_and_store_prediction(test_db, game)

        # Assertions
        assert prediction is not None
        assert prediction.game_id == game.id
        assert prediction.predicted_winner_id in [home_team.id, away_team.id]
        assert 0 <= prediction.win_probability <= 1.0
        assert prediction.predicted_home_score >= 0
        assert prediction.predicted_away_score >= 0
        assert prediction.home_elo_at_prediction == home_team.elo_rating
        assert prediction.away_elo_at_prediction == away_team.elo_rating
        assert prediction.was_correct is None  # Not yet determined

    def test_no_duplicate_predictions(self, test_db, test_teams):
        """Test that duplicate predictions are not created"""
        home_team, away_team = test_teams

        # Create a future game
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=0,
            away_score=0,
            week=11,
            season=2024,
            is_processed=False,
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Create first prediction
        pred1 = create_and_store_prediction(test_db, game)
        assert pred1 is not None

        # Try to create second prediction for same game
        pred2 = create_and_store_prediction(test_db, game)

        # Should return existing prediction, not create new one
        assert pred2 is not None
        assert pred2.id == pred1.id

        # Verify only one prediction exists
        count = test_db.query(Prediction).filter(Prediction.game_id == game.id).count()
        assert count == 1

    def test_no_prediction_for_completed_game(self, test_db, test_teams):
        """Test that predictions are not created for completed games"""
        home_team, away_team = test_teams

        # Create a completed game
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=12,
            season=2024,
            is_processed=True,
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        # Try to create prediction
        prediction = create_and_store_prediction(test_db, game)

        # Should return None for completed games
        assert prediction is None

    def test_prediction_model_properties(self, test_db, test_teams):
        """Test Prediction model properties"""
        home_team, away_team = test_teams

        # Create prediction directly
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=0,
            away_score=0,
            week=13,
            season=2024,
            is_processed=False,
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)

        prediction = Prediction(
            game_id=game.id,
            predicted_winner_id=home_team.id,
            predicted_home_score=30,
            predicted_away_score=24,
            win_probability=0.65,
            home_elo_at_prediction=1650.0,
            away_elo_at_prediction=1550.0,
        )
        test_db.add(prediction)
        test_db.commit()
        test_db.refresh(prediction)

        # Test predicted_margin property
        assert prediction.predicted_margin == 6

        # Test __repr__
        repr_str = repr(prediction)
        assert "Test Home Team" in repr_str or "?" in repr_str


@pytest.mark.unit
class TestSlatePredictionStorage:
    """The step utilities/weekly_update.sh runs before each slate.

    Nothing stored predictions on a schedule, so the 2026 season reached week 1
    with an empty predictions table and an accuracy page reading 0%.
    """

    def _slate(self, test_db, home_team, away_team, season=2026):
        from src.models.models import Season

        test_db.add(Season(year=season, current_week=1, is_active=True))
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=0,
            away_score=0,
            week=2,
            season=season,
            game_date=datetime(season, 9, 12, 19, 0),
            is_processed=False,
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)
        return game

    def _store_slate(self, test_db, season=2026):
        """Mirror of the loop in weekly_update.sh step 3."""
        from src.core.ranking_service import generate_predictions

        slate = generate_predictions(test_db, season_year=season)
        stored = 0
        for entry in slate:
            game = test_db.get(Game, entry["game_id"])
            if game is not None and create_and_store_prediction(test_db, game):
                stored += 1
        return stored, len(slate)

    def test_stores_a_prediction_for_each_slate_game(self, test_db, test_teams):
        home_team, away_team = test_teams
        game = self._slate(test_db, home_team, away_team)

        stored, slate_size = self._store_slate(test_db)

        assert slate_size == 1
        assert stored == 1
        prediction = test_db.query(Prediction).filter(Prediction.game_id == game.id).first()
        assert prediction is not None
        assert prediction.home_elo_at_prediction == home_team.elo_rating
        assert prediction.was_correct is None

    def test_rerunning_does_not_double_store(self, test_db, test_teams):
        """The cron runs daily; a second pass must not re-price the slate."""
        home_team, away_team = test_teams
        self._slate(test_db, home_team, away_team)
        self._store_slate(test_db)
        first = test_db.query(Prediction).one()
        original_elo = first.home_elo_at_prediction

        home_team.elo_rating += 40.0
        test_db.commit()
        self._store_slate(test_db)

        assert test_db.query(Prediction).count() == 1
        test_db.refresh(first)
        assert first.home_elo_at_prediction == original_elo
