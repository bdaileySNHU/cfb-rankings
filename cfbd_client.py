"""
CollegeFootballData.com API Client
Fetches real college football data for the ranking system
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime


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
