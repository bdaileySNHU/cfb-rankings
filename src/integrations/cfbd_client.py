"""CFBD API Client - CollegeFootballData.com Integration

This module provides a comprehensive client for the CollegeFootballData.com
(CFBD) API, enabling automated data imports for the ranking system.

The client handles:
    - Team data (FBS teams by season)
    - Game data (scores, schedules, line scores for quarter-weighted ELO)
    - Recruiting rankings (247Sports composite scores)
    - Transfer portal data (incoming transfers and rankings)
    - Returning production percentages
    - AP Poll rankings (for prediction comparison)
    - API usage tracking and quota monitoring

Key Features:
    - Automatic API usage tracking with threshold warnings (80%, 90%, 95%)
    - Request/response logging for debugging
    - Season and week detection utilities
    - Quarter-by-quarter line score fetching for garbage time detection

API Key:
    Required for most endpoints. Get a free key at:
    https://collegefootballdata.com/key

    Set via environment variable:
        export CFBD_API_KEY='your-key-here'

Example:
    Fetch teams and games:
        >>> client = CFBDClient()
        >>> teams = client.get_teams(2024)
        >>> games = client.get_games(2024, week=5)
        >>> print(f"Found {len(games)} games in Week 5")

    Check API usage:
        >>> usage = get_monthly_usage()
        >>> print(f"Used {usage['total_calls']}/{usage['monthly_limit']} calls")

Note:
    Default monthly limit is 1000 API calls. Configure via CFBD_MONTHLY_LIMIT
    environment variable. All API calls are automatically tracked in the
    api_usage table for monitoring.
"""

import functools
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Warning thresholds tracking (to prevent log spam)
_warning_thresholds_logged = {
    '80%': set(),   # Set of months where 80% warning was logged
    '90%': set(),   # Set of months where 90% warning was logged
    '95%': set()    # Set of months where 95% warning was logged
}


def track_api_usage(func):
    """
    Decorator to track CFBD API usage in database.

    Logs endpoint, timestamp, status code, and response time for each API call.
    Checks usage thresholds and logs warnings when approaching monthly limit.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        status_code = 200
        endpoint = "unknown"

        try:
            # Extract endpoint from args (assumes first arg after self is endpoint)
            if len(args) >= 2:
                endpoint = args[1]  # args[0] is self, args[1] is endpoint

            # Execute the actual API call
            response = func(*args, **kwargs)

            # Calculate response time
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Track usage in database
            try:
                from database import SessionLocal
                from models import APIUsage

                month = start_time.strftime("%Y-%m")

                db = SessionLocal()
                usage_record = APIUsage(
                    endpoint=endpoint,
                    timestamp=start_time,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    month=month
                )
                db.add(usage_record)
                db.commit()
                db.close()

                # Check warning thresholds
                check_usage_warnings(month)

            except Exception as tracking_error:
                logger.warning(f"Failed to track API usage: {tracking_error}")
                # Don't fail the API call due to tracking failure

            return response

        except Exception as e:
            # If API call fails, still try to track it
            status_code = getattr(e, 'status_code', 500)
            raise

    return wrapper


def get_monthly_usage(month: str = None, db: "Session" = None) -> dict:
    """
    Get API usage stats for specified month.

    Args:
        month: Month in YYYY-MM format (defaults to current month)
        db: Optional database session (creates new session if not provided)

    Returns:
        dict: Usage statistics including total calls, limit, percentage, etc.
    """
    from sqlalchemy import func

    from database import SessionLocal
    from models import APIUsage

    if not month:
        month = datetime.now().strftime("%Y-%m")

    # Use provided session or create new one
    db_provided = db is not None
    if not db_provided:
        db = SessionLocal()

    try:
        # Total calls for month
        total_calls = db.query(APIUsage).filter(APIUsage.month == month).count()

        # Monthly limit from environment
        monthly_limit = int(os.getenv("CFBD_MONTHLY_LIMIT", "1000"))

        # Calculate metrics
        percentage_used = (total_calls / monthly_limit) * 100 if monthly_limit > 0 else 0
        remaining_calls = max(0, monthly_limit - total_calls)

        # Average calls per day (based on days elapsed in month)
        year, month_num = map(int, month.split('-'))
        current_date = datetime.now()

        if year == current_date.year and month_num == current_date.month:
            days_elapsed = current_date.day
        else:
            # For past months, use full month
            import calendar
            days_elapsed = calendar.monthrange(year, month_num)[1]

        avg_per_day = total_calls / days_elapsed if days_elapsed > 0 else 0

        # Top endpoints
        top_endpoints = (
            db.query(APIUsage.endpoint, func.count(APIUsage.id).label('count'))
            .filter(APIUsage.month == month)
            .group_by(APIUsage.endpoint)
            .order_by(func.count(APIUsage.id).desc())
            .limit(5)
            .all()
        )

        # Determine warning level
        warning_level = None
        if percentage_used >= 95:
            warning_level = "95%"
        elif percentage_used >= 90:
            warning_level = "90%"
        elif percentage_used >= 80:
            warning_level = "80%"

        return {
            "month": month,
            "total_calls": total_calls,
            "monthly_limit": monthly_limit,
            "percentage_used": round(percentage_used, 2),
            "remaining_calls": remaining_calls,
            "average_calls_per_day": round(avg_per_day, 2),
            "warning_level": warning_level,
            "top_endpoints": [
                {"endpoint": ep, "count": cnt, "percentage": round((cnt / total_calls) * 100, 1) if total_calls > 0 else 0}
                for ep, cnt in top_endpoints
            ]
        }

    finally:
        # Only close session if we created it
        if not db_provided:
            db.close()


def check_usage_warnings(month: str):
    """
    Check API usage against thresholds and log warnings.

    Logs warning only once per threshold per month to prevent spam.

    Args:
        month: Month in YYYY-MM format
    """
    usage = get_monthly_usage(month)
    percentage = usage['percentage_used']
    total_calls = usage['total_calls']
    limit = usage['monthly_limit']

    # Check thresholds and log if not already logged for this month
    if percentage >= 95 and month not in _warning_thresholds_logged['95%']:
        logger.critical(f"CFBD API usage at 95% ({total_calls}/{limit} calls) - Month: {month}")
        _warning_thresholds_logged['95%'].add(month)
    elif percentage >= 90 and month not in _warning_thresholds_logged['90%']:
        logger.warning(f"CFBD API usage at 90% ({total_calls}/{limit} calls) - Month: {month}")
        _warning_thresholds_logged['90%'].add(month)
    elif percentage >= 80 and month not in _warning_thresholds_logged['80%']:
        logger.warning(f"CFBD API usage at 80% ({total_calls}/{limit} calls) - Month: {month}")
        _warning_thresholds_logged['80%'].add(month)


class CFBDClient:
    """Client for CollegeFootballData.com API with comprehensive data fetching.

    Provides methods to fetch all data types needed for the Modified ELO
    ranking system, including teams, games, recruiting data, transfer portal
    information, and AP Poll rankings.

    Features automatic API usage tracking via the @track_api_usage decorator,
    which logs every request to the api_usage table and checks threshold warnings.

    Attributes:
        BASE_URL: CFBD API base URL
        api_key: API key for authentication (from env or constructor)
        headers: HTTP headers including Bearer token authorization

    Example:
        >>> client = CFBDClient()
        >>> teams = client.get_teams(2024)
        >>> games = client.get_games(2024, week=5)
        >>> recruiting = client.get_recruiting_rankings(2024)
    """

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

    @track_api_usage
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
                # FIX: API uses camelCase field names
                home_points = game.get('homePoints')
                away_points = game.get('awayPoints')

                # Exclude future games (0-0 placeholder scores from EPIC-008)
                # College football games cannot end 0-0 due to overtime rules
                if (home_points is not None and away_points is not None and
                    not (home_points == 0 and away_points == 0)):
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
                  team: Optional[str] = None, season_type: str = 'regular',
                  classification: Optional[str] = None) -> List[Dict]:
        """
        Get games for a season

        Args:
            year: Season year
            week: Optional week number
            team: Optional team name filter
            season_type: 'regular' or 'postseason'
            classification: Optional division filter ('fbs', 'fcs', 'ii', 'iii')

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
        if classification:
            params['classification'] = classification

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

    def get_ap_poll(self, year: int, week: Optional[int] = None) -> List[Dict]:
        """
        Get AP Poll rankings for a specific week

        Part of EPIC-010: AP Poll Prediction Comparison

        Args:
            year: Season year
            week: Optional week number (if omitted, gets all weeks for the season)

        Returns:
            List of AP Poll ranking dictionaries, each containing:
            - season: int
            - seasonType: str (regular, postseason)
            - week: int
            - poll: str ("AP Top 25")
            - rank: int
            - school: str (team name)
            - conference: str
            - firstPlaceVotes: int
            - points: int

        Example:
            >>> client.get_ap_poll(2024, 5)
            [
                {
                    "season": 2024,
                    "week": 5,
                    "poll": "AP Top 25",
                    "rank": 1,
                    "school": "Georgia",
                    "conference": "SEC",
                    "firstPlaceVotes": 62,
                    "points": 1550
                },
                ...
            ]
        """
        params = {
            'year': year,
            'seasonType': 'regular'
        }
        if week:
            params['week'] = week

        rankings = self._get('/rankings', params=params)

        # Filter to only AP Poll rankings
        # CFBD API returns multiple polls (AP, Coaches, etc.)
        # We only want AP Top 25
        if not rankings:
            return []

        ap_rankings = []
        for poll_week in rankings:
            for poll in poll_week.get('polls', []):
                if poll.get('poll') == 'AP Top 25':
                    # Extract rankings with metadata
                    for team_ranking in poll.get('ranks', []):
                        ap_rankings.append({
                            'season': poll_week.get('season'),
                            'seasonType': poll_week.get('seasonType'),
                            'week': poll_week.get('week'),
                            'poll': poll.get('poll'),
                            'rank': team_ranking.get('rank'),
                            'school': team_ranking.get('school'),
                            'conference': team_ranking.get('conference'),
                            'firstPlaceVotes': team_ranking.get('firstPlaceVotes', 0),
                            'points': team_ranking.get('points', 0)
                        })

        return ap_rankings

    def get_game_line_scores(self, game_id: int, year: int, week: int,
                            home_team: str, away_team: str) -> Optional[Dict[str, List[int]]]:
        """
        Fetch quarter-by-quarter line scores for a game from CFBD API.

        Part of EPIC-021: Quarter-Weighted ELO

        Args:
            game_id: CFBD game ID (for logging/tracking)
            year: Season year
            week: Week number
            home_team: Home team name
            away_team: Away team name

        Returns:
            Dict with 'home' and 'away' keys, each containing list of 4 quarter scores
            Returns None if line scores unavailable

        Example:
            >>> client.get_game_line_scores(401525476, 2024, 5, "Georgia", "Alabama")
            {'home': [7, 14, 7, 10], 'away': [0, 7, 14, 3]}
        """
        try:
            # Fetch game data with team stats (includes line scores)
            params = {
                'year': year,
                'week': week,
                'team': home_team  # Filter to games involving home team
            }

            games = self._get('/games/teams', params=params)

            if not games:
                logger.debug(f"No game data for {home_team} vs {away_team}, Week {week}, {year}")
                return None

            # Find the specific game matching both teams
            for game_data in games:
                game_teams = game_data.get('teams', [])
                if len(game_teams) < 2:
                    continue

                team1 = game_teams[0]
                team2 = game_teams[1]

                # Check if this is the game we're looking for
                team1_name = team1.get('school', '')
                team2_name = team2.get('school', '')

                if (team1_name == home_team and team2_name == away_team) or \
                   (team1_name == away_team and team2_name == home_team):

                    # Determine which team is home
                    if team1.get('homeAway') == 'home':
                        home_data = team1
                        away_data = team2
                    else:
                        home_data = team2
                        away_data = team1

                    # Extract line scores
                    home_line = home_data.get('lineScores', [])
                    away_line = away_data.get('lineScores', [])

                    # Verify we have at least 4 quarters
                    if len(home_line) >= 4 and len(away_line) >= 4:
                        logger.debug(f"✓ Line scores found for {home_team} vs {away_team}")
                        return {
                            'home': home_line[:4],  # First 4 quarters only
                            'away': away_line[:4]
                        }
                    else:
                        logger.debug(f"Line scores incomplete for {home_team} vs {away_team}")
                        return None

            logger.debug(f"Game not found: {home_team} vs {away_team}, Week {week}, {year}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch line scores for game {game_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching line scores: {e}")
            return None


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
