"""
Unit tests for CFBD Client

Tests cover:
- Season detection (get_current_season)
- Current week detection from API (get_current_week)
- Calendar-based week estimation (estimate_current_week)
- Labor Day calculation (_find_labor_day)
- Season start calculation (_find_season_start)
- Edge cases: off-season, week boundaries, API failures
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from freezegun import freeze_time

from src.integrations.cfbd_client import CFBDClient


@pytest.mark.unit
class TestSeasonDetection:
    """Tests for get_current_season() method"""

    @freeze_time("2025-08-01")
    def test_get_current_season_august(self):
        """Test season detection on August 1 (new season starts)"""
        client = CFBDClient()
        assert client.get_current_season() == 2025

    @freeze_time("2026-01-15")
    def test_get_current_season_january(self):
        """Test season detection in January (next year planning)"""
        client = CFBDClient()
        assert client.get_current_season() == 2026

    @freeze_time("2025-07-31")
    def test_get_current_season_july(self):
        """Test season detection on July 31 (current year)"""
        client = CFBDClient()
        assert client.get_current_season() == 2025

    @freeze_time("2025-12-31")
    def test_get_current_season_december(self):
        """Test season detection on December 31 (current year)"""
        client = CFBDClient()
        assert client.get_current_season() == 2025

    @freeze_time("2025-09-15")
    def test_get_current_season_midseason(self):
        """Test season detection during the season (September)"""
        client = CFBDClient()
        assert client.get_current_season() == 2025

    @freeze_time("2025-02-01")
    def test_get_current_season_february(self):
        """Test season detection in off-season (February)"""
        client = CFBDClient()
        assert client.get_current_season() == 2025


@pytest.mark.unit
class TestWeekDetection:
    """Tests for get_current_week() method"""

    def test_get_current_week_with_completed_games(self):
        """Test week detection when games have been played"""
        client = CFBDClient()

        # Mock the get_games method to return sample games
        mock_games = [
            {"week": 1, "home_points": 35, "away_points": 28},
            {"week": 2, "home_points": 21, "away_points": 24},
            {"week": 8, "home_points": 42, "away_points": 17},
            {"week": 8, "home_points": 14, "away_points": 31},
            {"week": 9, "home_points": None, "away_points": None},  # Future game
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            assert week == 8

    def test_get_current_week_no_games(self):
        """Test week detection when no games played yet (pre-season)"""
        client = CFBDClient()

        with patch.object(client, "get_games", return_value=[]):
            week = client.get_current_week(2025)
            assert week is None

    def test_get_current_week_only_future_games(self):
        """Test week detection when all games are scheduled but not played"""
        client = CFBDClient()

        mock_games = [
            {"week": 1, "home_points": None, "away_points": None},
            {"week": 2, "home_points": None, "away_points": None},
            {"week": 3, "home_points": None, "away_points": None},
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            assert week is None

    def test_get_current_week_api_failure(self):
        """Test week detection when API call fails"""
        client = CFBDClient()

        with patch.object(client, "get_games", return_value=None):
            week = client.get_current_week(2025)
            assert week is None

    def test_get_current_week_api_exception(self):
        """Test week detection when API raises exception"""
        client = CFBDClient()

        with patch.object(client, "get_games", side_effect=Exception("API Error")):
            week = client.get_current_week(2025)
            assert week is None

    def test_get_current_week_week_1_only(self):
        """Test week detection when only week 1 has been played"""
        client = CFBDClient()

        mock_games = [
            {"week": 1, "home_points": 28, "away_points": 14},
            {"week": 1, "home_points": 35, "away_points": 21},
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            assert week == 1

    def test_get_current_week_ignores_missing_week_field(self):
        """Test week detection handles games missing week field"""
        client = CFBDClient()

        mock_games = [
            {"week": 5, "home_points": 28, "away_points": 14},
            {"home_points": 35, "away_points": 21},  # Missing week
            {"week": 3, "home_points": 42, "away_points": 7},
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            assert week == 5


@pytest.mark.unit
class TestWeekEstimation:
    """Tests for estimate_current_week() method"""

    @freeze_time("2025-09-06")
    def test_estimate_current_week_week1(self):
        """Test week estimation during Week 1"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Week 1 starts first Saturday after Labor Day (Sept 1 is Mon, Labor Day is Sept 1)
        assert week == 1

    @freeze_time("2025-08-15")
    def test_estimate_current_week_preseason(self):
        """Test week estimation before season starts"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        assert week == 0

    @freeze_time("2025-10-25")
    def test_estimate_current_week_midseason(self):
        """Test week estimation mid-season"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Around late October, should be week 7-9
        assert 7 <= week <= 9

    @freeze_time("2025-12-01")
    def test_estimate_current_week_late_season(self):
        """Test week estimation late in season (around week 13)"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Around early December, should be week 12-14
        assert 12 <= week <= 14

    @freeze_time("2025-12-31")
    def test_estimate_current_week_caps_at_15(self):
        """Test week estimation caps at 15 weeks maximum"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Should cap at 15 weeks
        assert week == 15

    @freeze_time("2026-01-15")
    def test_estimate_current_week_postseason(self):
        """Test week estimation after season ends"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Well after season, should return 15 (max)
        assert week == 15


@pytest.mark.unit
class TestLaborDayCalculation:
    """Tests for _find_labor_day() helper method"""

    def test_labor_day_2025(self):
        """Test Labor Day calculation for 2025"""
        client = CFBDClient()
        labor_day = client._find_labor_day(2025)
        # Labor Day 2025 is September 1 (first Monday of September)
        assert labor_day.year == 2025
        assert labor_day.month == 9
        assert labor_day.day == 1
        assert labor_day.weekday() == 0  # Monday

    def test_labor_day_2024(self):
        """Test Labor Day calculation for 2024"""
        client = CFBDClient()
        labor_day = client._find_labor_day(2024)
        # Labor Day 2024 is September 2
        assert labor_day.year == 2024
        assert labor_day.month == 9
        assert labor_day.day == 2
        assert labor_day.weekday() == 0  # Monday

    def test_labor_day_2026(self):
        """Test Labor Day calculation for 2026"""
        client = CFBDClient()
        labor_day = client._find_labor_day(2026)
        # Labor Day 2026 is September 7
        assert labor_day.year == 2026
        assert labor_day.month == 9
        assert labor_day.day == 7
        assert labor_day.weekday() == 0  # Monday

    def test_labor_day_always_monday(self):
        """Test Labor Day is always a Monday for multiple years"""
        client = CFBDClient()
        for year in range(2020, 2030):
            labor_day = client._find_labor_day(year)
            assert labor_day.weekday() == 0, f"Labor Day {year} is not a Monday"
            assert labor_day.month == 9, f"Labor Day {year} is not in September"


@pytest.mark.unit
class TestSeasonStartCalculation:
    """Tests for _find_season_start() helper method"""

    def test_season_start_after_labor_day(self):
        """Test season start is Saturday after Labor Day"""
        client = CFBDClient()
        labor_day = datetime(2025, 9, 1)  # Monday
        season_start = client._find_season_start(labor_day)

        # First Saturday after Labor Day is September 6, 2025
        assert season_start.year == 2025
        assert season_start.month == 9
        assert season_start.day == 6
        assert season_start.weekday() == 5  # Saturday

    def test_season_start_always_saturday(self):
        """Test season start is always a Saturday"""
        client = CFBDClient()
        for year in range(2020, 2030):
            labor_day = client._find_labor_day(year)
            season_start = client._find_season_start(labor_day)
            assert season_start.weekday() == 5, f"Season start {year} is not a Saturday"

    def test_season_start_after_labor_day_multiple_years(self):
        """Test season start is always after Labor Day"""
        client = CFBDClient()
        for year in range(2020, 2030):
            labor_day = client._find_labor_day(year)
            season_start = client._find_season_start(labor_day)
            assert season_start > labor_day, f"Season start {year} is not after Labor Day"


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_get_current_week_excludes_future_games_with_zero_scores(self):
        """Test week detection excludes 0-0 games (future game placeholders from EPIC-008)"""
        client = CFBDClient()

        mock_games = [
            {"week": 5, "home_points": 28, "away_points": 14},  # Completed game
            {"week": 6, "home_points": 0, "away_points": 0},  # Future game (0-0 placeholder)
            {"week": 7, "home_points": None, "away_points": None},  # Future game (None)
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            # Should return week 5, not week 6 (0-0 games are future games)
            # College football games cannot end 0-0 due to overtime rules
            assert week == 5

    def test_get_current_week_epic_008_scenario(self):
        """Test exact EPIC-008 bug scenario: week 9 complete, week 10 has 0-0 future games"""
        client = CFBDClient()

        mock_games = [
            # Weeks 1-9 have completed games
            {"week": 1, "home_points": 35, "away_points": 28},
            {"week": 2, "home_points": 21, "away_points": 14},
            {"week": 3, "home_points": 28, "away_points": 24},
            {"week": 4, "home_points": 42, "away_points": 17},
            {"week": 5, "home_points": 31, "away_points": 28},
            {"week": 6, "home_points": 24, "away_points": 21},
            {"week": 7, "home_points": 35, "away_points": 14},
            {"week": 8, "home_points": 28, "away_points": 27},
            {"week": 9, "home_points": 42, "away_points": 38},
            # Week 10 has future games with 0-0 placeholder scores
            {"week": 10, "home_points": 0, "away_points": 0},
            {"week": 10, "home_points": 0, "away_points": 0},
            {"week": 10, "home_points": 0, "away_points": 0},
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            # Should return week 9 (last completed week), NOT week 10
            assert week == 9

    def test_get_current_week_with_mixed_data(self):
        """Test week detection with mixed completed and future games"""
        client = CFBDClient()

        mock_games = [
            {"week": 1, "home_points": 35, "away_points": 28},
            {"week": 3, "home_points": 21, "away_points": 24},
            {"week": 5, "home_points": None, "away_points": None},
            {"week": 2, "home_points": 42, "away_points": 17},
            {"week": 4, "home_points": None, "away_points": None},
        ]

        with patch.object(client, "get_games", return_value=mock_games):
            week = client.get_current_week(2025)
            # Should find week 3 as the highest completed week
            assert week == 3

    @freeze_time("2025-09-01")  # Labor Day
    def test_estimate_current_week_on_labor_day(self):
        """Test week estimation on Labor Day itself"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Season hasn't started yet (starts following Saturday)
        assert week == 0

    @freeze_time("2025-09-06")  # First Saturday after Labor Day
    def test_estimate_current_week_on_season_start(self):
        """Test week estimation on exact season start date"""
        client = CFBDClient()
        week = client.estimate_current_week(2025)
        # Week 1 just started
        assert week == 1
