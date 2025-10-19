"""
Unit tests for weekly_update.py script

Tests the pre-flight check functions:
  - is_active_season()
  - check_api_usage()
  - get_current_week_wrapper()
"""

import sys
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add scripts directory to Python path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import weekly_update


class TestIsActiveSeason:
    """Tests for is_active_season() function"""

    def test_august_is_active_season(self):
        """August should be active season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 8, 15)
            assert weekly_update.is_active_season() is True

    def test_september_is_active_season(self):
        """September should be active season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 9, 20)
            assert weekly_update.is_active_season() is True

    def test_october_is_active_season(self):
        """October should be active season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19)
            assert weekly_update.is_active_season() is True

    def test_november_is_active_season(self):
        """November should be active season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 11, 25)
            assert weekly_update.is_active_season() is True

    def test_december_is_active_season(self):
        """December should be active season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 20)
            assert weekly_update.is_active_season() is True

    def test_january_is_active_season(self):
        """January should be active season (bowl games)"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 10)
            assert weekly_update.is_active_season() is True

    def test_february_is_off_season(self):
        """February should be off-season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 15)
            assert weekly_update.is_active_season() is False

    def test_march_is_off_season(self):
        """March should be off-season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 3, 10)
            assert weekly_update.is_active_season() is False

    def test_april_is_off_season(self):
        """April should be off-season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 5)
            assert weekly_update.is_active_season() is False

    def test_may_is_off_season(self):
        """May should be off-season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 5, 1)
            assert weekly_update.is_active_season() is False

    def test_june_is_off_season(self):
        """June should be off-season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 6, 15)
            assert weekly_update.is_active_season() is False

    def test_july_is_off_season(self):
        """July should be off-season"""
        with patch('weekly_update.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 7, 25)
            assert weekly_update.is_active_season() is False


class TestCheckApiUsage:
    """Tests for check_api_usage() function"""

    @patch('weekly_update.get_monthly_usage')
    def test_usage_below_90_percent_passes(self, mock_get_usage):
        """API usage below 90% should pass check"""
        mock_get_usage.return_value = {
            'percentage_used': 75.0,
            'remaining_calls': 250,
            'total_calls': 750,
            'monthly_limit': 1000
        }
        assert weekly_update.check_api_usage() is True

    @patch('weekly_update.get_monthly_usage')
    def test_usage_at_90_percent_fails(self, mock_get_usage):
        """API usage at exactly 90% should fail check"""
        mock_get_usage.return_value = {
            'percentage_used': 90.0,
            'remaining_calls': 100,
            'total_calls': 900,
            'monthly_limit': 1000
        }
        assert weekly_update.check_api_usage() is False

    @patch('weekly_update.get_monthly_usage')
    def test_usage_above_90_percent_fails(self, mock_get_usage):
        """API usage above 90% should fail check"""
        mock_get_usage.return_value = {
            'percentage_used': 95.5,
            'remaining_calls': 45,
            'total_calls': 955,
            'monthly_limit': 1000
        }
        assert weekly_update.check_api_usage() is False

    @patch('weekly_update.get_monthly_usage')
    def test_usage_at_100_percent_fails(self, mock_get_usage):
        """API usage at 100% should fail check"""
        mock_get_usage.return_value = {
            'percentage_used': 100.0,
            'remaining_calls': 0,
            'total_calls': 1000,
            'monthly_limit': 1000
        }
        assert weekly_update.check_api_usage() is False

    @patch('weekly_update.get_monthly_usage')
    def test_usage_check_exception_proceeds_with_caution(self, mock_get_usage):
        """If usage check fails, should proceed anyway (with warning)"""
        mock_get_usage.side_effect = Exception("Database connection failed")
        # Should return True (proceed) but log warning
        assert weekly_update.check_api_usage() is True


class TestGetCurrentWeekWrapper:
    """Tests for get_current_week_wrapper() function"""

    @patch('weekly_update.CFBDClient')
    def test_current_week_detected_successfully(self, mock_client_class):
        """Successfully detect current week from CFBD API"""
        mock_client = MagicMock()
        mock_client.get_current_season.return_value = 2025
        mock_client.get_current_week.return_value = 8
        mock_client_class.return_value = mock_client

        week = weekly_update.get_current_week_wrapper()
        assert week == 8

    @patch('weekly_update.CFBDClient')
    def test_no_current_week_returns_none(self, mock_client_class):
        """No current week (off-season) returns None"""
        mock_client = MagicMock()
        mock_client.get_current_season.return_value = 2025
        mock_client.get_current_week.return_value = None
        mock_client_class.return_value = mock_client

        week = weekly_update.get_current_week_wrapper()
        assert week is None

    @patch('weekly_update.CFBDClient')
    def test_cfbd_api_error_raises_exception(self, mock_client_class):
        """CFBD API error should raise exception"""
        mock_client = MagicMock()
        mock_client.get_current_season.side_effect = Exception("API unavailable")
        mock_client_class.return_value = mock_client

        with pytest.raises(Exception, match="API unavailable"):
            weekly_update.get_current_week_wrapper()


class TestMainFunction:
    """Integration tests for main() function"""

    @patch('weekly_update.is_active_season')
    @patch('weekly_update.sys.exit')
    def test_off_season_exits_gracefully(self, mock_exit, mock_is_active):
        """Off-season should exit gracefully with code 0"""
        mock_is_active.return_value = False

        weekly_update.main()

        mock_exit.assert_called_once_with(0)

    @patch('weekly_update.is_active_season')
    @patch('weekly_update.get_current_week_wrapper')
    @patch('weekly_update.sys.exit')
    def test_no_current_week_exits_with_error(self, mock_exit, mock_get_week, mock_is_active):
        """No current week should exit with error code 1"""
        mock_is_active.return_value = True
        mock_get_week.return_value = None

        weekly_update.main()

        mock_exit.assert_called_once_with(1)

    @patch('weekly_update.is_active_season')
    @patch('weekly_update.get_current_week_wrapper')
    @patch('weekly_update.check_api_usage')
    @patch('weekly_update.sys.exit')
    def test_api_usage_exceeded_exits_with_error(self, mock_exit, mock_check_usage,
                                                   mock_get_week, mock_is_active):
        """API usage >= 90% should exit with error code 1"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = False

        weekly_update.main()

        mock_exit.assert_called_once_with(1)

    @patch('weekly_update.is_active_season')
    @patch('weekly_update.get_current_week_wrapper')
    @patch('weekly_update.check_api_usage')
    @patch('weekly_update.run_import_script')
    @patch('weekly_update.sys.exit')
    def test_all_checks_pass_runs_import(self, mock_exit, mock_run_import, mock_check_usage,
                                          mock_get_week, mock_is_active):
        """All checks passing should run import script"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = True
        mock_run_import.return_value = 0  # Success

        weekly_update.main()

        mock_run_import.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('weekly_update.is_active_season')
    @patch('weekly_update.get_current_week_wrapper')
    @patch('weekly_update.check_api_usage')
    @patch('weekly_update.run_import_script')
    @patch('weekly_update.sys.exit')
    def test_import_failure_exits_with_error(self, mock_exit, mock_run_import, mock_check_usage,
                                              mock_get_week, mock_is_active):
        """Import script failure should exit with error code 1"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = True
        mock_run_import.return_value = 1  # Failure

        weekly_update.main()

        mock_run_import.assert_called_once()
        mock_exit.assert_called_once_with(1)
