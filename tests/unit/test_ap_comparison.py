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

from src.core.ap_poll_service import calculate_comparison_stats, get_ap_prediction_for_game, get_team_ap_rank
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

        with patch('src.core.ap_poll_service.get_team_ap_rank', side_effect=mock_ap_rank):
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

        with patch('src.core.ap_poll_service.get_team_ap_rank', side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Away team is #3, home team is #15, so AP predicts away team wins
            assert predicted_winner_id == 20

    def test_only_home_ranked(self, mock_db, sample_game):
        """Test AP prediction when only home team is ranked"""
        def mock_ap_rank(db, team_id, season, week):
            if team_id == 10:  # Home team
                return 8
            return None  # Away team unranked

        with patch('src.core.ap_poll_service.get_team_ap_rank', side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Only home team ranked, so AP predicts home team wins
            assert predicted_winner_id == 10

    def test_only_away_ranked(self, mock_db, sample_game):
        """Test AP prediction when only away team is ranked"""
        def mock_ap_rank(db, team_id, season, week):
            if team_id == 20:  # Away team
                return 10
            return None  # Home team unranked

        with patch('src.core.ap_poll_service.get_team_ap_rank', side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Only away team ranked, so AP predicts away team wins
            assert predicted_winner_id == 20

    def test_both_unranked(self, mock_db, sample_game):
        """Test AP prediction when neither team is ranked"""
        def mock_ap_rank(db, team_id, season, week):
            return None  # Both unranked

        with patch('src.core.ap_poll_service.get_team_ap_rank', side_effect=mock_ap_rank):
            predicted_winner_id = get_ap_prediction_for_game(mock_db, sample_game)
            # Both unranked, no AP prediction possible
            assert predicted_winner_id is None

    def test_equal_ranks(self, mock_db, sample_game):
        """Test AP prediction when teams have equal ranks (edge case)"""
        def mock_ap_rank(db, team_id, season, week):
            return 10  # Both ranked #10 (very rare)

        with patch('src.core.ap_poll_service.get_team_ap_rank', side_effect=mock_ap_rank):
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
                    if hasattr(game_id_filter, 'right') and hasattr(game_id_filter.right, 'value'):
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
        """Test comparison stats with no games"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        assert stats['season'] == 2024
        assert stats['total_games_compared'] == 0
        assert stats['elo_accuracy'] == 0.0
        assert stats['ap_accuracy'] == 0.0
        assert len(stats['by_week']) == 0
        assert len(stats['disagreements']) == 0

    def test_calculate_comparison_stats_structure(self):
        """Test that comparison stats returns correct structure"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        # Verify all required fields present
        assert 'season' in stats
        assert 'elo_accuracy' in stats
        assert 'ap_accuracy' in stats
        assert 'elo_advantage' in stats
        assert 'total_games_compared' in stats
        assert 'elo_correct' in stats
        assert 'ap_correct' in stats
        assert 'both_correct' in stats
        assert 'elo_only_correct' in stats
        assert 'ap_only_correct' in stats
        assert 'both_wrong' in stats
        assert 'by_week' in stats
        assert 'disagreements' in stats

    def test_elo_advantage_calculation(self):
        """Test ELO advantage calculation"""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        stats = calculate_comparison_stats(db, 2024)

        # With no data, advantage should be 0
        assert stats['elo_advantage'] == stats['elo_accuracy'] - stats['ap_accuracy']
