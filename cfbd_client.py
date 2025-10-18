"""
CollegeFootballData.com API Client
Fetches real college football data for the ranking system
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class CFBDClient:
    """Client for CollegeFootballData.com API"""

    BASE_URL = "https://api.collegefootballdata.com"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CFBD client

        Args:
            api_key: API key from collegefootballdata.com
                     If not provided, will look for CFBD_API_KEY env variable
        """
        self.api_key = api_key or os.getenv('CFBD_API_KEY')
        self.headers = {}
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to CFBD API"""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return None

    def get_current_season(self) -> int:
        """
        Determine the current college football season year based on calendar date.

        Season year logic:
        - August 1 through December 31: Current calendar year
        - January 1 through July 31: Current calendar year

        Examples:
            July 31, 2025 → 2025 season
            August 1, 2025 → 2025 season (new season starts)
            December 31, 2025 → 2025 season
            January 15, 2026 → 2026 season (next year's planning)

        Returns:
            int: The current season year (e.g., 2025)
        """
        now = datetime.now()
        # Season year is always the current calendar year
        # The college football season runs from August of year N to January of year N+1
        # But we consider January-July of year N+1 as planning for year N+1 season
        return now.year

    def get_current_week(self, season: int) -> Optional[int]:
        """
        Get the current week of the season from CFBD API.

        Queries the /games endpoint to find the highest week number
        that has completed games (games with non-null scores).

        Args:
            season: The season year to check

        Returns:
            int: Highest completed week number (1-15), or None if no games played

        Example:
            >>> client.get_current_week(2025)
            8  # Week 8 is the latest with completed games
        """
        try:
            # Query all regular season games for the year
            games = self.get_games(season, season_type='regular')

            if not games:
                return None

            # Find max week with completed games (non-null scores)
            max_week = 0
            for game in games:
                # Check if game has been played (has scores)
                home_points = game.get('home_points')
                away_points = game.get('away_points')

                if home_points is not None and away_points is not None:
                    week = game.get('week', 0)
                    if week > max_week:
                        max_week = week

            return max_week if max_week > 0 else None

        except Exception as e:
            print(f"Error detecting current week: {e}")
            return None

    def estimate_current_week(self, season: int) -> int:
        """
        Estimate current week based on calendar (fallback when API unavailable).

        Calculates weeks elapsed since the season start (first Saturday after Labor Day).

        Args:
            season: The season year

        Returns:
            int: Estimated week number (0-15)
                0 = pre-season
                1-15 = regular season weeks

        Note:
            This is a fallback estimate only. Use get_current_week() for accurate data.
        """
        now = datetime.now()

        # Find Labor Day (first Monday of September)
        labor_day = self._find_labor_day(season)

        # Season starts on first Saturday after Labor Day
        season_start = self._find_season_start(labor_day)

        # If we're before the season start, return 0 (pre-season)
        if now < season_start:
            return 0

        # Calculate weeks since season start
        days_since_start = (now - season_start).days
        weeks_elapsed = (days_since_start // 7) + 1

        # Cap at 15 weeks (regular season maximum)
        return min(weeks_elapsed, 15)

    def _find_labor_day(self, year: int) -> datetime:
        """
        Find Labor Day (first Monday of September).

        Args:
            year: The year to find Labor Day for

        Returns:
            datetime: Labor Day date
        """
        # Start with September 1st
        september_first = datetime(year, 9, 1)

        # Find first Monday (weekday 0 = Monday)
        days_until_monday = (7 - september_first.weekday()) % 7

        # If September 1st is already a Monday, that's Labor Day
        if september_first.weekday() == 0:
            return september_first

        # Otherwise, add days to get to first Monday
        return september_first + timedelta(days=days_until_monday)

    def _find_season_start(self, labor_day: datetime) -> datetime:
        """
        Find season start (first Saturday after Labor Day).

        Args:
            labor_day: Labor Day date

        Returns:
            datetime: Season start date (first Saturday after Labor Day)
        """
        # Saturday = weekday 5
        days_until_saturday = (5 - labor_day.weekday()) % 7

        # If days_until_saturday is 0, Labor Day is already a Saturday
        # In that case, we want the NEXT Saturday (7 days later)
        if days_until_saturday == 0:
            days_until_saturday = 7

        return labor_day + timedelta(days=days_until_saturday)

    def get_teams(self, year: int = 2024) -> List[Dict]:
        """
        Get all FBS teams for a given year

        Args:
            year: Season year

        Returns:
            List of team dictionaries
        """
        return self._get('/teams/fbs', params={'year': year})

    def get_games(self, year: int, week: Optional[int] = None,
                  team: Optional[str] = None, season_type: str = 'regular') -> List[Dict]:
        """
        Get games for a season

        Args:
            year: Season year
            week: Optional week number
            team: Optional team name filter
            season_type: 'regular' or 'postseason'

        Returns:
            List of game dictionaries
        """
        params = {
            'year': year,
            'seasonType': season_type
        }
        if week:
            params['week'] = week
        if team:
            params['team'] = team

        return self._get('/games', params=params)

    def get_recruiting_rankings(self, year: int) -> List[Dict]:
        """
        Get recruiting rankings for a class year

        Args:
            year: Recruiting class year

        Returns:
            List of team recruiting rankings
        """
        return self._get('/recruiting/teams', params={'year': year})

    def get_team_talent(self, year: int) -> List[Dict]:
        """
        Get team talent composite scores

        Args:
            year: Season year

        Returns:
            List of team talent rankings
        """
        return self._get('/talent', params={'year': year})

    def get_returning_production(self, year: int, team: Optional[str] = None) -> List[Dict]:
        """
        Get returning production percentages

        Args:
            year: Season year
            team: Optional team filter

        Returns:
            List of returning production data
        """
        params = {'year': year}
        if team:
            params['team'] = team

        return self._get('/player/returning', params=params)

    def get_transfer_portal(self, year: int) -> List[Dict]:
        """
        Get transfer portal data

        Args:
            year: Season year

        Returns:
            List of transfer portal rankings
        """
        return self._get('/player/portal', params={'year': year})


def test_api():
    """Test CFBD API connection"""
    print("Testing CollegeFootballData API...")
    print("Note: You'll need an API key from https://collegefootballdata.com/key")
    print()

    client = CFBDClient()

    # Test teams endpoint (works without API key)
    print("Fetching FBS teams for 2024...")
    teams = client.get_teams(2024)
    if teams:
        print(f"✓ Found {len(teams)} teams")
        print(f"  Example: {teams[0]['school']} ({teams[0]['conference']})")
    else:
        print("✗ Failed to fetch teams (may need API key)")

    print()

    # Test games endpoint
    print("Fetching Week 1 games...")
    games = client.get_games(2024, week=1)
    if games:
        print(f"✓ Found {len(games)} games")
        if games:
            game = games[0]
            print(f"  Example: {game.get('home_team')} vs {game.get('away_team')}")
    else:
        print("✗ Failed to fetch games (may need API key)")

    print()
    print("To use this API:")
    print("1. Get free API key: https://collegefootballdata.com/key")
    print("2. Set environment variable: export CFBD_API_KEY='your-key-here'")
    print("3. Run import scripts")


if __name__ == "__main__":
    test_api()
