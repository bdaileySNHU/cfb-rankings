"""
Unit tests for AP Poll comparison logic (EPIC-010 Story 002)

Tests cover:
- get_team_ap_rank() helper function
- get_ap_prediction_for_game() prediction logic
- calculate_comparison_stats() statistics calculation
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.ap_poll_service import (
    calculate_comparison_stats,
    get_ap_prediction_for_game,
    get_team_ap_rank,
)
from src.models.models import APPollRanking, ConferenceType, Game, Prediction, Season, Team


@pytest.mark.unit
class TestGetTeamAPRank:
    """Tests for get_team_ap_rank() function"""

    def test_get_team_ap_rank_success(self):
        """Test fetching AP rank for a ranked team"""
        # Mock database and ranking
        db = Mock()
        mock_ranking = Mock()
        mock_ranking.rank = 5

        db.query.return_value.filter.return_value.first.return_value = mock_ranking

        rank = get_team_ap_rank(db, team_id=1, season=2024, week=5)

        assert rank == 5

    def test_get_team_ap_rank_unranked(self):
        """Test fetching AP rank for unranked team"""
        # Mock database with no ranking found
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        rank = get_team_ap_rank(db, team_id=999, season=2024, week=5)

        assert rank is None


@pytest.mark.unit
class TestAPPredictionLogic:
    """Tests for get_ap_prediction_for_game() function"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        return Mock()

    @pytest.fixture
    def sample_game(self):
        """Create sample game"""
        game = Mock(spec=Game)
        game.id = 1
        game.home_team_id = 10
        game.away_team_id = 20
        game.season = 2024
        game.week = 5
        game.home_score = 35
        game.away_score = 28
        return game

    def test_both_ranked_higher_rank_home_wins(self, mock_db, sample_game):
        """Test AP prediction when both teams ranked, home team ranked higher"""

        def mock_ap_rank(db, team_id, season, week):
            if team_id == 10:  # Home team
                return 5
            elif team_id == 20:  # Away team
                return 12
            return None

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Home team is #5, away team is #12, so AP predicts home team wins
            assert predicted_winner_id == 10

    def test_both_ranked_higher_rank_away_wins(self, mock_db, sample_game):
        """Test AP prediction when both teams ranked, away team ranked higher"""

        def mock_ap_rank(db, team_id, season, week):
            if team_id == 10:  # Home team
                return 15
            elif team_id == 20:  # Away team
                return 3
            return None

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Away team is #3, home team is #15, so AP predicts away team wins
            assert predicted_winner_id == 20

    def test_only_home_ranked(self, mock_db, sample_game):
        """Test AP prediction when only home team is ranked"""

        def mock_ap_rank(db, team_id, season, week):
            if team_id == 10:  # Home team
                return 8
            return None  # Away team unranked

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Only home team ranked, so AP predicts home team wins
            assert predicted_winner_id == 10

    def test_only_away_ranked(self, mock_db, sample_game):
        """Test AP prediction when only away team is ranked"""

        def mock_ap_rank(db, team_id, season, week):
            if team_id == 20:  # Away team
                return 10
            return None  # Home team unranked

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Only away team ranked, so AP predicts away team wins
            assert predicted_winner_id == 20

    def test_both_unranked(self, mock_db, sample_game):
        """Test AP prediction when neither team is ranked"""

        def mock_ap_rank(db, team_id, season, week):
            return None  # Both unranked

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Both unranked, no AP prediction possible
            assert predicted_winner_id is None

    def test_equal_ranks(self, mock_db, sample_game):
        """Test AP prediction when teams have equal ranks (edge case)"""

        def mock_ap_rank(db, team_id, season, week):
            return 10  # Both ranked #10 (very rare)

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Equal ranks, no clear prediction
            assert predicted_winner_id is None


@pytest.mark.unit
class TestComparisonStatistics:
    """Tests for calculate_comparison_stats() function"""

    @pytest.fixture
    def mock_db_with_data(self):
        """Create mock database with sample comparison data"""
        db = Mock()

        # Mock game 1: ELO correct, AP correct (both ranked, both right)
        game1 = Mock(spec=Game)
        game1.id = 1
        game1.season = 2024
        game1.week = 5
        game1.home_team_id = 10
        game1.away_team_id = 20
        game1.home_score = 35
        game1.away_score = 28
        game1.is_processed = True
        game1.excluded_from_rankings = False

        # Mock game 2: ELO correct, AP wrong (upset)
        game2 = Mock(spec=Game)
        game2.id = 2
        game2.season = 2024
        game2.week = 5
        game2.home_team_id = 30
        game2.away_team_id = 40
        game2.home_score = 31
        game2.away_score = 28
        game2.is_processed = True
        game2.excluded_from_rankings = False

        # Mock game 3: ELO wrong, AP correct
        game3 = Mock(spec=Game)
        game3.id = 3
        game3.season = 2024
        game3.week = 6
        game3.home_team_id = 50
        game3.away_team_id = 60
        game3.home_score = 21
        game3.away_score = 24
        game3.is_processed = True
        game3.excluded_from_rankings = False

        games = [game1, game2, game3]
        db.query.return_value.filter.return_value.all.return_value = games

        # Mock predictions
        def mock_prediction_query(model):
            if model == Prediction:
                mock_pred_query = Mock()

                def filter_pred(game_id_filter):
                    # Return appropriate prediction based on game_id
                    if hasattr(game_id_filter, "right") and hasattr(game_id_filter.right, "value"):
                        game_id = game_id_filter.right.value
                    else:
                        return mock_pred_query

                    if game_id == 1:
                        pred1 = Mock()
                        pred1.game_id = 1
                        pred1.predicted_winner_id = 10  # Correct
                        mock_pred_query.first.return_value = pred1
                    elif game_id == 2:
                        pred2 = Mock()
                        pred2.game_id = 2
                        pred2.predicted_winner_id = 30  # Correct
                        mock_pred_query.first.return_value = pred2
                    elif game_id == 3:
                        pred3 = Mock()
                        pred3.game_id = 3
                        pred3.predicted_winner_id = 50  # Wrong
                        mock_pred_query.first.return_value = pred3

                    return mock_pred_query

                mock_pred_query.filter = filter_pred
                return mock_pred_query
            elif model == Team:
                mock_team = Mock()
                mock_team.name = "Team"
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_team))))
            return Mock()

        db.query = mock_prediction_query

        return db

    def test_calculate_comparison_stats_no_data(self):
        """Test comparison stats with no games (empty state)"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        assert stats["season"] == 2024
        assert stats["total_games_compared"] == 0
        assert stats["elo_accuracy"] == 0.0
        assert stats["ap_accuracy"] == 0.0
        assert len(stats["by_week"]) == 0
        assert len(stats["disagreements"]) == 0
        # Check for new empty state fields
        assert stats["overall_elo_accuracy"] == 0.0
        assert stats["overall_elo_total"] == 0
        assert stats["overall_elo_correct"] == 0
        assert "message" in stats
        assert "available once" in stats["message"].lower()

    def test_calculate_comparison_stats_structure(self):
        """Test that comparison stats returns correct structure"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        # Verify all required fields present
        assert "season" in stats
        assert "elo_accuracy" in stats
        assert "ap_accuracy" in stats
        assert "elo_advantage" in stats
        assert "total_games_compared" in stats
        assert "elo_correct" in stats
        assert "ap_correct" in stats
        assert "both_correct" in stats
        assert "elo_only_correct" in stats
        assert "ap_only_correct" in stats
        assert "both_wrong" in stats
        assert "by_week" in stats
        assert "disagreements" in stats
        # Check for overall ELO stats and message field
        assert "overall_elo_accuracy" in stats
        assert "overall_elo_total" in stats
        assert "overall_elo_correct" in stats
        assert "message" in stats

    def test_elo_advantage_calculation(self):
        """Test ELO advantage calculation"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        # With no data, advantage should be 0
        assert stats["elo_advantage"] == stats["elo_accuracy"] - stats["ap_accuracy"]

    def test_postseason_fields_in_empty_state(self):
        """Test that postseason fields are included in empty state response"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        # EPIC-COMPARISON-BOWL-PLAYOFF: Verify postseason fields present
        assert "regular_season_elo_accuracy" in stats
        assert "regular_season_ap_accuracy" in stats
        assert "postseason_elo_accuracy" in stats
        assert "postseason_ap_accuracy" in stats
        # All should be 0.0 in empty state
        assert stats["regular_season_elo_accuracy"] == 0.0
        assert stats["regular_season_ap_accuracy"] == 0.0
        assert stats["postseason_elo_accuracy"] == 0.0
        assert stats["postseason_ap_accuracy"] == 0.0

    def test_postseason_game_included_in_calculations(self):
        """Test that postseason games (weeks 16-20) are included in comparison"""
        db = Mock()

        # Create a postseason game (week 17 - CFP Quarterfinal)
        postseason_game = Mock(spec=Game)
        postseason_game.id = 100
        postseason_game.season = 2024
        postseason_game.week = 17  # Postseason
        postseason_game.home_team_id = 10
        postseason_game.away_team_id = 20
        postseason_game.home_score = 35
        postseason_game.away_score = 31
        postseason_game.is_processed = True
        postseason_game.excluded_from_rankings = False
        postseason_game.game_type = "playoff"
        postseason_game.postseason_name = "CFP Quarterfinal"

        games = [postseason_game]

        # Setup mock query chain for games
        mock_game_query = Mock()
        mock_game_query.all.return_value = games

        # Create prediction for postseason game
        postseason_pred = Mock()
        postseason_pred.game_id = 100
        postseason_pred.predicted_winner_id = 10  # Predicted home team (correct)
        postseason_pred.was_correct = True

        # Mock AP rank function
        def mock_ap_rank(db_arg, team_id, season, week):
            if team_id == 10:  # Home team
                return 3  # Ranked #3
            elif team_id == 20:  # Away team
                return 7  # Ranked #7
            return None

        # Mock Team query
        mock_team = Mock()
        mock_team.name = "Team"

        def mock_query(model):
            if model == Game:
                return Mock(filter=Mock(return_value=mock_game_query))
            elif model == Prediction:
                mock_pred_query = Mock()

                def filter_pred(game_id_filter):
                    mock_pred_query.first.return_value = postseason_pred
                    return mock_pred_query

                mock_pred_query.filter = filter_pred
                # For overall ELO accuracy query
                mock_pred_query.join.return_value.filter.return_value.all.return_value = [postseason_pred]
                return mock_pred_query
            elif model == Team:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_team))))
            return Mock()

        db.query = mock_query

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            stats = calculate_comparison_stats(db, 2024)

        # EPIC-COMPARISON-BOWL-PLAYOFF: Verify postseason game was included
        assert stats["total_games_compared"] == 1
        assert stats["postseason_elo_accuracy"] == 1.0  # 100% accurate (1/1 correct)
        assert stats["postseason_ap_accuracy"] == 1.0  # AP also correct (lower rank wins)
        assert stats["regular_season_elo_accuracy"] == 0.0  # No regular season games
        assert stats["regular_season_ap_accuracy"] == 0.0

    def test_game_type_and_postseason_name_in_by_week(self):
        """Test that game_type and postseason_name are included in by_week breakdown"""
        db = Mock()

        # Create postseason game with game_type and postseason_name
        playoff_game = Mock(spec=Game)
        playoff_game.id = 200
        playoff_game.season = 2024
        playoff_game.week = 18  # CFP Semifinal week
        playoff_game.home_team_id = 10
        playoff_game.away_team_id = 20
        playoff_game.home_score = 42
        playoff_game.away_score = 35
        playoff_game.is_processed = True
        playoff_game.excluded_from_rankings = False
        playoff_game.game_type = "playoff"
        playoff_game.postseason_name = "CFP Semifinal - Rose Bowl"

        games = [playoff_game]

        # Setup mocks
        mock_game_query = Mock()
        mock_game_query.all.return_value = games

        playoff_pred = Mock()
        playoff_pred.game_id = 200
        playoff_pred.predicted_winner_id = 10  # Correct
        playoff_pred.was_correct = True

        def mock_ap_rank(db_arg, team_id, season, week):
            if team_id == 10:
                return 2
            elif team_id == 20:
                return 5
            return None

        mock_team = Mock()
        mock_team.name = "Team"

        def mock_query(model):
            if model == Game:
                return Mock(filter=Mock(return_value=mock_game_query))
            elif model == Prediction:
                mock_pred_query = Mock()
                mock_pred_query.filter = Mock(return_value=Mock(first=Mock(return_value=playoff_pred)))
                mock_pred_query.join.return_value.filter.return_value.all.return_value = [playoff_pred]
                return mock_pred_query
            elif model == Team:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_team))))
            return Mock()

        db.query = mock_query

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            stats = calculate_comparison_stats(db, 2024)

        # EPIC-COMPARISON-BOWL-PLAYOFF: Verify game_type and postseason_name in by_week
        assert len(stats["by_week"]) == 1
        week_18_stats = stats["by_week"][0]
        assert week_18_stats["week"] == 18
        assert week_18_stats["game_type"] == "playoff"
        assert week_18_stats["postseason_name"] == "CFP Semifinal - Rose Bowl"
        assert week_18_stats["elo_accuracy"] == 1.0
        assert week_18_stats["ap_accuracy"] == 1.0
        assert week_18_stats["games"] == 1

    def test_mixed_regular_and_postseason_games(self):
        """Test comparison with both regular season and postseason games"""
        db = Mock()

        # Regular season game (week 10)
        regular_game = Mock(spec=Game)
        regular_game.id = 1
        regular_game.season = 2024
        regular_game.week = 10
        regular_game.home_team_id = 10
        regular_game.away_team_id = 20
        regular_game.home_score = 28
        regular_game.away_score = 24
        regular_game.is_processed = True
        regular_game.excluded_from_rankings = False
        regular_game.game_type = None
        regular_game.postseason_name = None

        # Postseason game (week 16 - Bowl game)
        bowl_game = Mock(spec=Game)
        bowl_game.id = 2
        bowl_game.season = 2024
        bowl_game.week = 16
        bowl_game.home_team_id = 30
        bowl_game.away_team_id = 40
        bowl_game.home_score = 35
        bowl_game.away_score = 31
        bowl_game.is_processed = True
        bowl_game.excluded_from_rankings = False
        bowl_game.game_type = "bowl"
        bowl_game.postseason_name = "Fiesta Bowl"

        games = [regular_game, bowl_game]

        mock_game_query = Mock()
        mock_game_query.all.return_value = games

        # Predictions: regular season correct, bowl game wrong
        regular_pred = Mock()
        regular_pred.game_id = 1
        regular_pred.predicted_winner_id = 10  # Correct
        regular_pred.was_correct = True

        bowl_pred = Mock()
        bowl_pred.game_id = 2
        bowl_pred.predicted_winner_id = 40  # Wrong (predicted away, but home won)
        bowl_pred.was_correct = False

        def mock_ap_rank(db_arg, team_id, season, week):
            if week == 10:
                if team_id == 10:
                    return 8
                elif team_id == 20:
                    return 15
            elif week == 16:
                if team_id == 30:
                    return 12
                elif team_id == 40:
                    return 10  # AP predicts away team (wrong)
            return None

        mock_team = Mock()
        mock_team.name = "Team"

        def mock_query(model):
            if model == Game:
                return Mock(filter=Mock(return_value=mock_game_query))
            elif model == Prediction:
                mock_pred_query = Mock()

                def filter_pred(game_id_filter):
                    if hasattr(game_id_filter, "right") and hasattr(game_id_filter.right, "value"):
                        game_id = game_id_filter.right.value
                        if game_id == 1:
                            mock_pred_query.first.return_value = regular_pred
                        elif game_id == 2:
                            mock_pred_query.first.return_value = bowl_pred
                    return mock_pred_query

                mock_pred_query.filter = filter_pred
                mock_pred_query.join.return_value.filter.return_value.all.return_value = [
                    regular_pred,
                    bowl_pred,
                ]
                return mock_pred_query
            elif model == Team:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_team))))
            return Mock()

        db.query = mock_query

        with patch("src.core.ap_poll_service.get_team_ap_rank", side_effect=mock_ap_rank):
            stats = calculate_comparison_stats(db, 2024)

        # EPIC-COMPARISON-BOWL-PLAYOFF: Verify separate tracking
        assert stats["total_games_compared"] == 2
        # Regular season: 1 game, 1 correct (100%)
        assert stats["regular_season_elo_accuracy"] == 1.0
        assert stats["regular_season_ap_accuracy"] == 1.0
        # Postseason: 1 game, 0 correct (0%)
        assert stats["postseason_elo_accuracy"] == 0.0
        assert stats["postseason_ap_accuracy"] == 0.0
        # Overall: 2 games, 1 ELO correct, 1 AP correct
        assert stats["elo_correct"] == 1
        assert stats["ap_correct"] == 1
