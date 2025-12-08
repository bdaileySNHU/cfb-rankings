"""
Integration tests for CFBD data import functionality

Tests cover:
- Mocking the CFBD API client
- Team import from CFBD data
- Game import from CFBD data
- Preseason data integration (recruiting, talent, returning production)
"""

import sys
from unittest.mock import Mock, patch

import pytest
from factories import configure_factories
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import ConferenceType, Game, Season, Team


@pytest.mark.integration
class TestCFBDClientMocking:
    """Tests for CFBD API client mocking"""

    def test_mock_cfbd_client_fixture(self, mock_cfbd_client):
        """Test that mock CFBD client fixture provides realistic data"""
        # Act - Call all mocked methods
        teams = mock_cfbd_client.get_teams(2025)
        games = mock_cfbd_client.get_games(2025, week=1)
        recruiting = mock_cfbd_client.get_recruiting_rankings(2025)
        talent = mock_cfbd_client.get_team_talent(2025)
        returning = mock_cfbd_client.get_returning_production(2025)
        transfers = mock_cfbd_client.get_transfer_portal(2025)

        # Assert - Verify mock returns expected data structures
        assert isinstance(teams, list)
        assert len(teams) == 5
        assert teams[0]['school'] == 'Alabama'
        assert teams[0]['conference'] == 'SEC'

        assert isinstance(games, list)
        assert len(games) == 2
        assert 'homeTeam' in games[0]
        assert 'awayTeam' in games[0]
        assert 'homePoints' in games[0]

        assert isinstance(recruiting, list)
        assert recruiting[0]['team'] == 'Alabama'
        assert recruiting[0]['rank'] == 1

        assert isinstance(talent, list)
        assert talent[0]['school'] == 'Alabama'
        assert talent[0]['talent'] == 95.5

        assert isinstance(returning, list)
        assert returning[0]['team'] == 'Alabama'

        assert isinstance(transfers, list)
        assert transfers[0]['team'] == 'Alabama'

    def test_mock_client_is_deterministic(self, mock_cfbd_client):
        """Test that mock client returns same data on repeated calls"""
        # Act - Call same method twice
        teams1 = mock_cfbd_client.get_teams(2025)
        teams2 = mock_cfbd_client.get_teams(2025)

        # Assert - Should be identical
        assert teams1 == teams2
        assert len(teams1) == len(teams2)


@pytest.mark.integration
class TestTeamImportWithMock:
    """Tests for team import functionality using mocked CFBD client"""

    def test_import_teams_with_mock_data(self, test_db: Session, mock_cfbd_client):
        """Test importing teams using mocked CFBD data"""
        # Arrange
        configure_factories(test_db)
        from import_real_data import import_teams

        # Act - Import teams using mock client
        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Assert - Verify teams were created
        assert len(team_objects) == 5
        assert 'Alabama' in team_objects
        assert 'Georgia' in team_objects
        assert 'Ohio State' in team_objects

        # Verify teams in database
        teams_in_db = test_db.query(Team).all()
        assert len(teams_in_db) == 5

        # Verify Alabama has correct data
        alabama = team_objects['Alabama']
        assert alabama.name == 'Alabama'
        assert alabama.conference == ConferenceType.POWER_5
        assert alabama.recruiting_rank == 1  # From mock recruiting data
        assert alabama.returning_production > 0  # From mock returning production

    def test_import_teams_with_conference_mapping(self, test_db: Session, mock_cfbd_client):
        """Test that conference mapping works correctly"""
        # Arrange
        from import_real_data import import_teams

        # Act
        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Assert - Verify conference types
        alabama = team_objects['Alabama']
        boise = team_objects['Boise State']

        assert alabama.conference == ConferenceType.POWER_5  # SEC -> P5
        assert boise.conference == ConferenceType.GROUP_5  # Mountain West -> G5

    def test_import_teams_calculates_preseason_ratings(self, test_db: Session, mock_cfbd_client):
        """Test that preseason ratings are calculated during import"""
        # Arrange
        from import_real_data import import_teams

        # Act
        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Assert - Teams should have initial ELO ratings calculated
        alabama = team_objects['Alabama']
        georgia = team_objects['Georgia']

        # Alabama has better recruiting (#1 vs #2), so should have higher initial rating
        assert alabama.elo_rating > 1500  # Base FBS rating
        assert alabama.elo_rating > georgia.elo_rating or \
               abs(alabama.elo_rating - georgia.elo_rating) < 50  # Close due to similar recruiting

        # Verify initial_rating is set
        assert alabama.initial_rating == alabama.elo_rating


@pytest.mark.integration
class TestGameImportWithMock:
    """Tests for game import functionality using mocked CFBD client"""

    def test_import_games_with_mock_data(self, test_db: Session, mock_cfbd_client):
        """Test importing games using mocked CFBD data"""
        # Arrange
        from import_real_data import import_games, import_teams

        # First import teams
        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Act - Import games using mock client
        import_stats = import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=1)

        # Assert - Verify games were created and processed
        assert import_stats['imported'] == 2  # Mock data has 2 games

        games_in_db = test_db.query(Game).all()
        assert len(games_in_db) == 2

        # Verify game was processed (ratings updated)
        game = games_in_db[0]
        assert game.is_processed is True
        assert game.home_rating_change != 0.0 or game.away_rating_change != 0.0

    def test_import_games_updates_team_records(self, test_db: Session, mock_cfbd_client):
        """Test that game import updates team win/loss records"""
        # Arrange
        from import_real_data import import_games, import_teams

        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Act
        import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=1)

        # Assert - Teams should have updated records
        alabama = test_db.query(Team).filter(Team.name == 'Alabama').first()
        georgia = test_db.query(Team).filter(Team.name == 'Georgia').first()

        # Alabama beat Georgia 27-24 in mock data
        assert alabama.wins == 1
        assert alabama.losses == 0
        assert georgia.wins == 0
        assert georgia.losses == 1

    def test_import_games_skips_incomplete_games(self, test_db: Session, mock_cfbd_client):
        """Test that import handles games without scores as future games"""
        # Arrange
        from import_real_data import import_games, import_teams

        # Modify mock to include incomplete game
        mock_cfbd_client.get_games.return_value = [
            {
                'homeTeam': 'Alabama',
                'awayTeam': 'Georgia',
                'homePoints': None,  # Future/incomplete game
                'awayPoints': None,
                'week': 1,
                'neutralSite': False
            }
        ]

        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Act
        import_stats = import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=1)

        # Assert - Games without scores are treated as future games
        assert import_stats['imported'] == 0
        assert import_stats['future_imported'] == 1

    def test_import_games_skips_fcs_opponents(self, test_db: Session, mock_cfbd_client):
        """Test that import creates FCS games with excluded_from_rankings flag"""
        # Arrange
        from import_real_data import import_games, import_teams
        from models import Game

        # Modify mock to include FCS opponent
        mock_cfbd_client.get_games.return_value = [
            {
                'homeTeam': 'Alabama',
                'awayTeam': 'Some FCS Team',  # Not in our team list
                'homePoints': 56,
                'awayPoints': 7,
                'week': 1,
                'neutralSite': False
            }
        ]

        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Act
        import_stats = import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=1)

        # Assert - FCS game should be imported but not processed for rankings
        assert import_stats['imported'] == 0, "No FBS games should be imported"
        assert import_stats['fcs_imported'] == 1, "One FCS game should be imported"

        # Verify the game was created with excluded_from_rankings=True
        fcs_game = test_db.query(Game).first()
        assert fcs_game is not None
        assert fcs_game.excluded_from_rankings is True
        assert fcs_game.is_processed is False

    def test_import_games_handles_neutral_site(self, test_db: Session, mock_cfbd_client):
        """Test that neutral site flag is properly imported"""
        # Arrange
        from import_real_data import import_games, import_teams

        # Modify mock to include neutral site game
        mock_cfbd_client.get_games.return_value = [
            {
                'homeTeam': 'Alabama',
                'awayTeam': 'Georgia',
                'homePoints': 27,
                'awayPoints': 24,
                'week': 1,
                'neutralSite': True  # Neutral site game
            }
        ]

        team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

        # Act
        import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=1)

        # Assert - Game should be marked as neutral site
        game = test_db.query(Game).first()
        assert game.is_neutral_site is True


@pytest.mark.integration
class TestMockClientErrorHandling:
    """Tests for mock client error scenarios"""

    def test_mock_client_handles_api_failures(self, test_db: Session):
        """Test handling when CFBD API returns None (failure)"""
        # Arrange
        from unittest.mock import Mock

        from import_real_data import import_teams

        mock_client = Mock()
        mock_client.get_teams.return_value = None  # Simulate API failure

        # Act
        team_objects = import_teams(mock_client, test_db, year=2025)

        # Assert - Should return empty dict on failure
        assert team_objects == {}

    def test_mock_client_with_missing_data_fields(self, test_db: Session):
        """Test robustness when API returns incomplete data"""
        # Arrange
        from unittest.mock import Mock

        from import_real_data import import_teams

        mock_client = Mock()
        mock_client.get_teams.return_value = [
            {'school': 'Alabama', 'conference': 'SEC'}
        ]
        # Missing recruiting, talent, returning production data
        mock_client.get_recruiting_rankings.return_value = []
        mock_client.get_team_talent.return_value = []
        mock_client.get_returning_production.return_value = []

        # Act
        team_objects = import_teams(mock_client, test_db, year=2025)

        # Assert - Should still create team with defaults
        assert len(team_objects) == 1
        alabama = team_objects['Alabama']
        assert alabama.recruiting_rank == 999  # Default for unranked
        assert alabama.returning_production == 0.5  # Default
