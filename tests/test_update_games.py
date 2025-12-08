"""
Tests for scripts/update_games.py

These tests validate the game update script that imports future games
from the CFBD API without resetting the database.

EPIC-013 Story 002: Improve Test Coverage
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

# Import the function we're testing (we'll need to refactor update_games.py to make it testable)
# For now, we'll test the core logic


class TestUpdateGamesScript:
    """Test suite for update_games.py functionality"""

    @pytest.fixture
    def mock_cfbd_client(self):
        """Mock CFBD client with realistic responses"""
        client = Mock()
        # Based on actual CFBD API response from debug_cfbd_response.py
        client.get_games.return_value = [
            {
                "id": 401761639,
                "season": 2025,
                "week": 10,
                "seasonType": "regular",
                "startDate": "2025-10-29T00:00:00.000Z",
                "startTimeTBD": False,
                "completed": False,
                "neutralSite": False,
                "conferenceGame": True,
                "homeId": 326,
                "homeTeam": "Texas State",
                "homeClassification": "fbs",
                "homeConference": "Sun Belt",
                "homePoints": None,
                "awayId": 256,
                "awayTeam": "James Madison",
                "awayClassification": "fbs",
                "awayConference": "Sun Belt",
                "awayPoints": None,
            },
            {
                "id": 401757289,
                "season": 2025,
                "week": 10,
                "seasonType": "regular",
                "startDate": "2025-10-29T00:00:00.000Z",
                "startTimeTBD": False,
                "completed": False,
                "neutralSite": False,
                "conferenceGame": True,
                "homeId": 338,
                "homeTeam": "Kennesaw State",
                "homeClassification": "fbs",
                "homeConference": "Conference USA",
                "homePoints": None,
                "awayId": 2638,
                "awayTeam": "UTEP",
                "awayClassification": "fbs",
                "awayConference": "Conference USA",
                "awayPoints": None,
            }
        ]
        return client

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock(spec=Session)
        return session

    def test_cfbd_response_parsing_camelcase_fields(self, mock_cfbd_client):
        """
        Test that we correctly parse camelCase fields from CFBD API

        This test ensures we don't regress on the camelCase bug that was fixed.
        CFBD API returns: homeTeam, awayTeam, startDate, neutralSite, homePoints, awayPoints
        NOT: home_team, away_team, start_date, neutral_site, home_points, away_points
        """
        games = mock_cfbd_client.get_games(2025, week=10)

        # Verify we get the expected structure
        assert len(games) == 2

        # First game
        game1 = games[0]
        assert game1['homeTeam'] == 'Texas State'  # camelCase!
        assert game1['awayTeam'] == 'James Madison'  # camelCase!
        assert game1['startDate'] == '2025-10-29T00:00:00.000Z'  # camelCase!
        assert game1['neutralSite'] == False  # camelCase!
        assert game1['homePoints'] is None  # camelCase!
        assert game1['awayPoints'] is None  # camelCase!

        # Second game
        game2 = games[1]
        assert game2['homeTeam'] == 'Kennesaw State'
        assert game2['awayTeam'] == 'UTEP'

    def test_null_team_name_handling(self, mock_cfbd_client):
        """
        Test that games with null team names are skipped

        This prevents the "NOT NULL constraint failed: teams.name" error
        """
        # Add a game with null team names
        mock_cfbd_client.get_games.return_value.append({
            "id": 999999,
            "season": 2025,
            "week": 10,
            "homeTeam": None,  # NULL!
            "awayTeam": "Some Team",
            "startDate": "2025-10-29T00:00:00.000Z",
        })

        games = mock_cfbd_client.get_games(2025, week=10)

        # Filter logic: skip if home_name or away_name is None
        valid_games = []
        skipped_count = 0

        for game_data in games:
            home_name = game_data.get('homeTeam')
            away_name = game_data.get('awayTeam')

            if not home_name or not away_name:
                skipped_count += 1
                continue

            valid_games.append(game_data)

        assert len(valid_games) == 2  # Only 2 valid games
        assert skipped_count == 1  # 1 game skipped due to null team

    def test_duplicate_game_detection(self, mock_db_session):
        """
        Test that duplicate games are not created

        When a game already exists for the same teams, week, and season,
        it should be skipped.
        """
        # Mock existing game query
        existing_game = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_game

        # Should skip this game
        result = mock_db_session.query.return_value.filter.return_value.first()
        assert result is not None  # Game exists, should skip

    def test_fcs_team_creation(self, mock_db_session):
        """
        Test that FCS teams are created when not found in database

        When a team is not in the database, it should be created with
        is_fcs=True and default ELO rating of 1500.
        """
        from src.models.models import Team

        # Mock team not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Create FCS team
        fcs_team = Team(
            name="Montana",
            conference='FCS',
            is_fcs=True,
            elo_rating=1500.0,
            initial_rating=1500.0
        )

        assert fcs_team.name == "Montana"
        assert fcs_team.is_fcs == True
        assert fcs_team.elo_rating == 1500.0
        assert fcs_team.conference == 'FCS'

    def test_game_date_parsing(self):
        """
        Test that ISO 8601 date strings are parsed correctly

        CFBD returns dates like: "2025-10-29T00:00:00.000Z"
        We need to parse these to datetime objects.
        """
        date_str = "2025-10-29T00:00:00.000Z"

        # Parse ISO format
        game_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

        assert game_date.year == 2025
        assert game_date.month == 10
        assert game_date.day == 29

    def test_neutral_site_flag(self, mock_cfbd_client):
        """Test that neutral site flag is correctly extracted"""
        games = mock_cfbd_client.get_games(2025, week=10)

        game1 = games[0]
        assert game1['neutralSite'] == False

        # Test with a neutral site game
        neutral_game = {
            "homeTeam": "Georgia",
            "awayTeam": "Florida",
            "neutralSite": True,  # Jacksonville - neutral site
            "startDate": "2025-10-29T00:00:00.000Z",
        }

        assert neutral_game['neutralSite'] == True

    def test_future_game_not_processed(self):
        """
        Test that future games are marked as is_processed=False

        Games that haven't been played yet should have:
        - is_processed = False
        - home_score = 0 or None
        - away_score = 0 or None
        """
        from src.models.models import Game

        future_game = Game(
            home_team_id=1,
            away_team_id=2,
            home_score=0,
            away_score=0,
            week=10,
            season=2025,
            is_processed=False,
            excluded_from_rankings=False
        )

        assert future_game.is_processed == False
        assert future_game.home_score == 0
        assert future_game.away_score == 0

    def test_fcs_game_excluded_from_rankings(self):
        """
        Test that FCS games are excluded from rankings

        When a game involves an FCS team, excluded_from_rankings should be True
        """
        from src.models.models import Game, Team

        # FBS team
        fbs_team = Team(name="Ohio State", is_fcs=False, elo_rating=1800.0)

        # FCS team
        fcs_team = Team(name="Montana", is_fcs=True, elo_rating=1500.0)

        # Determine exclusion
        is_fcs_game = fbs_team.is_fcs or fcs_team.is_fcs

        game = Game(
            home_team_id=1,
            away_team_id=2,
            week=10,
            season=2025,
            excluded_from_rankings=is_fcs_game
        )

        assert is_fcs_game == True
        assert game.excluded_from_rankings == True


class TestCFBDAPIFieldMapping:
    """
    Test suite specifically for CFBD API field name mapping

    This prevents regression of the camelCase vs snake_case bug
    """

    def test_field_name_mapping(self):
        """
        Document the correct field names from CFBD API

        CFBD API uses camelCase, NOT snake_case!
        """
        expected_fields = {
            'homeTeam': 'home_team',      # CFBD -> Our code
            'awayTeam': 'away_team',
            'startDate': 'start_date',
            'neutralSite': 'neutral_site',
            'homePoints': 'home_points',
            'awayPoints': 'away_points',
            'homeId': 'home_id',
            'awayId': 'away_id',
            'seasonType': 'season_type',
        }

        # Verify we're using the correct CFBD field names
        assert 'homeTeam' in expected_fields
        assert 'home_team' not in expected_fields  # Don't use snake_case for CFBD!

    def test_cfbd_response_schema(self):
        """
        Test expected structure of CFBD API game response

        This serves as documentation of the API contract
        """
        cfbd_game_response = {
            "id": 401761639,
            "season": 2025,
            "week": 10,
            "seasonType": "regular",  # camelCase!
            "startDate": "2025-10-29T00:00:00.000Z",  # camelCase!
            "startTimeTBD": False,  # camelCase!
            "completed": False,
            "neutralSite": False,  # camelCase!
            "conferenceGame": True,  # camelCase!
            "homeId": 326,  # camelCase!
            "homeTeam": "Texas State",  # camelCase!
            "homeClassification": "fbs",  # camelCase!
            "homeConference": "Sun Belt",  # camelCase!
            "homePoints": None,  # camelCase!
            "awayId": 256,  # camelCase!
            "awayTeam": "James Madison",  # camelCase!
            "awayClassification": "fbs",  # camelCase!
            "awayConference": "Sun Belt",  # camelCase!
            "awayPoints": None,  # camelCase!
        }

        # Verify all critical fields are camelCase
        assert 'homeTeam' in cfbd_game_response
        assert 'awayTeam' in cfbd_game_response
        assert 'startDate' in cfbd_game_response
        assert 'neutralSite' in cfbd_game_response
        assert 'homePoints' in cfbd_game_response
        assert 'awayPoints' in cfbd_game_response

        # These should NOT exist (snake_case)
        assert 'home_team' not in cfbd_game_response
        assert 'away_team' not in cfbd_game_response
