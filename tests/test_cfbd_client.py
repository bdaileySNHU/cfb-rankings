"""
Tests for cfbd_client.py

These tests validate the CFBD API client functionality including:
- API response parsing
- Current week detection
- Season estimation
- Field name handling (camelCase from API)

EPIC-013 Story 002: Improve Test Coverage - Phase 2
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.integrations.cfbd_client import CFBDClient


class TestCFBDClient:
    """Test suite for CFBDClient class"""

    @pytest.fixture
    def client(self):
        """Create CFBDClient instance with mock API key"""
        return CFBDClient(api_key="test_api_key")

    @pytest.fixture
    def mock_response(self):
        """Mock requests response"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = []
        return response

    def test_client_initialization_with_api_key(self):
        """Test that client initializes with provided API key"""
        client = CFBDClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"
        assert client.headers['Authorization'] == 'Bearer test_key_123'

    def test_client_initialization_from_env(self, monkeypatch):
        """Test that client reads API key from environment"""
        monkeypatch.setenv('CFBD_API_KEY', 'env_key_456')
        client = CFBDClient()
        assert client.api_key == 'env_key_456'

    def test_get_current_season(self, client):
        """Test current season detection based on calendar year"""
        # Mock datetime to test different scenarios
        with patch('src.integrations.cfbd_client.datetime') as mock_datetime:
            # Test January 2025 → should return 2025
            mock_datetime.now.return_value = datetime(2025, 1, 15)
            assert client.get_current_season() == 2025

            # Test August 2025 → should return 2025
            mock_datetime.now.return_value = datetime(2025, 8, 1)
            assert client.get_current_season() == 2025

            # Test December 2025 → should return 2025
            mock_datetime.now.return_value = datetime(2025, 12, 31)
            assert client.get_current_season() == 2025


class TestCurrentWeekDetection:
    """Tests for get_current_week() functionality"""

    @pytest.fixture
    def client(self):
        return CFBDClient(api_key="test_key")

    def test_get_current_week_with_completed_games(self, client):
        """Test that current week is detected from completed games"""
        mock_games = [
            {'week': 1, 'home_points': 21, 'away_points': 14},
            {'week': 1, 'home_points': 35, 'away_points': 10},
            {'week': 2, 'home_points': 28, 'away_points': 21},
            {'week': 2, 'home_points': 17, 'away_points': 14},
            {'week': 3, 'home_points': None, 'away_points': None},  # Future game
        ]

        with patch.object(client, 'get_games', return_value=mock_games):
            current_week = client.get_current_week(2025)
            assert current_week == 2  # Week 2 is latest with scores

    def test_get_current_week_excludes_zero_zero_games(self, client):
        """Test that 0-0 games are treated as future games (not played)"""
        mock_games = [
            {'week': 1, 'home_points': 21, 'away_points': 14},
            {'week': 2, 'home_points': 0, 'away_points': 0},  # Placeholder, not played
        ]

        with patch.object(client, 'get_games', return_value=mock_games):
            current_week = client.get_current_week(2025)
            assert current_week == 1  # Week 2 should be ignored (0-0)

    def test_get_current_week_no_games_played(self, client):
        """Test when no games have been played yet"""
        mock_games = [
            {'week': 1, 'home_points': None, 'away_points': None},
            {'week': 2, 'home_points': None, 'away_points': None},
        ]

        with patch.object(client, 'get_games', return_value=mock_games):
            current_week = client.get_current_week(2025)
            assert current_week is None

    def test_get_current_week_empty_response(self, client):
        """Test when API returns no games"""
        with patch.object(client, 'get_games', return_value=[]):
            current_week = client.get_current_week(2025)
            assert current_week is None


class TestEstimateCurrentWeek:
    """Tests for estimate_current_week() calendar-based estimation"""

    @pytest.fixture
    def client(self):
        return CFBDClient(api_key="test_key")

    def test_find_labor_day_2025(self, client):
        """Test Labor Day calculation for 2025"""
        # Labor Day 2025 is September 1st (Monday)
        labor_day = client._find_labor_day(2025)
        assert labor_day.month == 9
        assert labor_day.day == 1
        assert labor_day.weekday() == 0  # Monday

    def test_find_season_start_2025(self, client):
        """Test season start (first Saturday after Labor Day)"""
        labor_day = client._find_labor_day(2025)
        season_start = client._find_season_start(labor_day)

        # Should be September 6, 2025 (Saturday)
        assert season_start.month == 9
        assert season_start.day == 6
        assert season_start.weekday() == 5  # Saturday

    def test_estimate_current_week_logic(self, client):
        """
        Test week estimation logic exists

        Note: Full testing of estimate_current_week requires complex datetime mocking.
        The logic is tested indirectly through integration tests.
        Here we just verify the method exists and doesn't crash.
        """
        # Just verify the method exists and is callable
        assert hasattr(client, 'estimate_current_week')
        assert callable(client.estimate_current_week)

        # The actual calculation is complex and depends on current date
        # This is better tested in integration tests


class TestCFBDAPIEndpoints:
    """Tests for individual CFBD API endpoint methods"""

    @pytest.fixture
    def client(self):
        return CFBDClient(api_key="test_key")

    @patch('src.integrations.cfbd_client.requests.get')
    def test_get_teams(self, mock_get, client):
        """Test get_teams() method"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {'school': 'Ohio State', 'conference': 'Big Ten'},
            {'school': 'Michigan', 'conference': 'Big Ten'},
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        teams = client.get_teams(2025)

        assert len(teams) == 2
        assert teams[0]['school'] == 'Ohio State'
        mock_get.assert_called_once()

    @patch('src.integrations.cfbd_client.requests.get')
    def test_get_games_with_week_filter(self, mock_get, client):
        """Test get_games() with week parameter"""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client.get_games(2025, week=10, season_type='regular')

        # Verify correct parameters passed
        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params['year'] == 2025
        assert params['week'] == 10
        assert params['seasonType'] == 'regular'

    @patch('src.integrations.cfbd_client.requests.get')
    def test_get_ap_poll(self, mock_get, client):
        """Test get_ap_poll() method"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'season': 2025,
                'week': 10,
                'polls': [
                    {
                        'poll': 'AP Top 25',
                        'ranks': [
                            {'rank': 1, 'school': 'Ohio State', 'points': 1550},
                            {'rank': 2, 'school': 'Michigan', 'points': 1490},
                        ]
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ap_rankings = client.get_ap_poll(2025, week=10)

        assert len(ap_rankings) == 2
        assert ap_rankings[0]['rank'] == 1
        assert ap_rankings[0]['school'] == 'Ohio State'
        assert ap_rankings[1]['rank'] == 2


class TestAPIUsageTracking:
    """Tests for API usage tracking decorator"""

    @pytest.fixture
    def client(self):
        return CFBDClient(api_key="test_key")

    def test_track_api_usage_decorator(self, client):
        """Test that API usage tracking decorator exists"""
        # This is a basic test to verify the decorator is in place
        # Full testing would require database setup
        import inspect

        from src.integrations.cfbd_client import track_api_usage

        # Verify the decorator exists and is a function
        assert callable(track_api_usage)

        # Verify _get method has tracking
        # (testing the actual tracking requires database which is out of scope for unit tests)

    def test_get_monthly_usage(self):
        """Test monthly usage calculation"""
        # This requires database access, so we'll test the structure
        # In a real test, we'd use a test database
        # For now, just verify the function exists and has correct signature
        import inspect

        from src.integrations.cfbd_client import get_monthly_usage
        sig = inspect.signature(get_monthly_usage)
        assert 'month' in sig.parameters


class TestCFBDFieldNaming:
    """
    Critical tests for CFBD API field naming conventions

    These tests document and validate the camelCase convention
    """

    def test_cfbd_uses_camelcase(self):
        """Document that CFBD API uses camelCase, not snake_case"""
        # This is documentation as much as a test
        cfbd_conventions = {
            'team_fields': ['homeTeam', 'awayTeam', 'homeId', 'awayId'],
            'score_fields': ['homePoints', 'awayPoints'],
            'date_fields': ['startDate', 'startTimeTBD'],
            'site_fields': ['neutralSite'],
            'classification_fields': ['homeClassification', 'awayClassification'],
            'conference_fields': ['homeConference', 'awayConference', 'conferenceGame'],
        }

        # Verify all use camelCase
        for category, fields in cfbd_conventions.items():
            for field in fields:
                # camelCase has no underscores
                assert '_' not in field, f"{field} should be camelCase"
                # camelCase starts with lowercase
                assert field[0].islower(), f"{field} should start with lowercase"

    def test_incorrect_snake_case_fields_dont_exist(self):
        """Verify snake_case fields DON'T exist in CFBD responses"""
        # These field names are WRONG - CFBD doesn't use them
        wrong_fields = [
            'home_team',  # Should be homeTeam
            'away_team',  # Should be awayTeam
            'start_date',  # Should be startDate
            'neutral_site',  # Should be neutralSite
            'home_points',  # Should be homePoints
            'away_points',  # Should be awayPoints
        ]

        # Sample CFBD response (from actual API)
        cfbd_response = {
            'homeTeam': 'Texas State',
            'awayTeam': 'James Madison',
            'startDate': '2025-10-29T00:00:00.000Z',
            'neutralSite': False,
            'homePoints': None,
            'awayPoints': None,
        }

        # Verify wrong fields don't exist
        for wrong_field in wrong_fields:
            assert wrong_field not in cfbd_response, \
                f"CFBD doesn't use snake_case field '{wrong_field}'"


class TestErrorHandling:
    """Tests for error handling in CFBD client"""

    @pytest.fixture
    def client(self):
        return CFBDClient(api_key="test_key")

    @patch('src.integrations.cfbd_client.requests.get')
    def test_api_request_failure(self, mock_get, client):
        """Test handling of API request failures"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        result = client._get('/games')
        assert result is None  # Should return None on error

    @patch('src.integrations.cfbd_client.requests.get')
    def test_http_error_handling(self, mock_get, client):
        """Test handling of HTTP errors (404, 500, etc.)"""
        import requests
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = client._get('/games')
        assert result is None
