"""
Unit tests for AP Poll functionality (EPIC-010 Story 001)

Tests cover:
- AP Poll fetching from CFBD API (get_ap_poll)
- AP Poll ranking import and storage
- Duplicate prevention
- Team lookup and matching
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from cfbd_client import CFBDClient
from models import Team, APPollRanking, ConferenceType
from import_real_data import import_ap_poll_rankings


@pytest.mark.unit
class TestAPPollFetching:
    """Tests for CFBDClient.get_ap_poll() method"""

    def test_get_ap_poll_success(self):
        """Test successful AP Poll fetch for a specific week"""
        client = CFBDClient()

        # Mock CFBD API response
        mock_response = [
            {
                "season": 2024,
                "seasonType": "regular",
                "week": 5,
                "polls": [
                    {
                        "poll": "AP Top 25",
                        "ranks": [
                            {
                                "rank": 1,
                                "school": "Georgia",
                                "conference": "SEC",
                                "firstPlaceVotes": 62,
                                "points": 1550
                            },
                            {
                                "rank": 2,
                                "school": "Alabama",
                                "conference": "SEC",
                                "firstPlaceVotes": 0,
                                "points": 1488
                            }
                        ]
                    }
                ]
            }
        ]

        with patch.object(client, '_get', return_value=mock_response):
            rankings = client.get_ap_poll(2024, 5)

            assert len(rankings) == 2
            assert rankings[0]['rank'] == 1
            assert rankings[0]['school'] == 'Georgia'
            assert rankings[0]['week'] == 5
            assert rankings[0]['season'] == 2024
            assert rankings[1]['rank'] == 2
            assert rankings[1]['school'] == 'Alabama'

    def test_get_ap_poll_filters_coaches_poll(self):
        """Test that get_ap_poll filters out non-AP polls"""
        client = CFBDClient()

        # Mock response with both AP and Coaches polls
        mock_response = [
            {
                "season": 2024,
                "seasonType": "regular",
                "week": 5,
                "polls": [
                    {
                        "poll": "AP Top 25",
                        "ranks": [
                            {"rank": 1, "school": "Georgia", "conference": "SEC"}
                        ]
                    },
                    {
                        "poll": "Coaches Poll",
                        "ranks": [
                            {"rank": 1, "school": "Alabama", "conference": "SEC"}
                        ]
                    }
                ]
            }
        ]

        with patch.object(client, '_get', return_value=mock_response):
            rankings = client.get_ap_poll(2024, 5)

            # Should only include AP Poll, not Coaches Poll
            assert len(rankings) == 1
            assert rankings[0]['school'] == 'Georgia'
            assert rankings[0]['poll'] == 'AP Top 25'

    def test_get_ap_poll_no_data(self):
        """Test AP Poll fetch when no poll data available"""
        client = CFBDClient()

        with patch.object(client, '_get', return_value=None):
            rankings = client.get_ap_poll(2024, 1)
            assert rankings == []

    def test_get_ap_poll_empty_response(self):
        """Test AP Poll fetch with empty response"""
        client = CFBDClient()

        with patch.object(client, '_get', return_value=[]):
            rankings = client.get_ap_poll(2024, 5)
            assert rankings == []

    def test_get_ap_poll_all_weeks(self):
        """Test fetching AP Poll for entire season (no week specified)"""
        client = CFBDClient()

        mock_response = [
            {
                "season": 2024,
                "week": 1,
                "polls": [
                    {"poll": "AP Top 25", "ranks": [{"rank": 1, "school": "Georgia"}]}
                ]
            },
            {
                "season": 2024,
                "week": 2,
                "polls": [
                    {"poll": "AP Top 25", "ranks": [{"rank": 1, "school": "Alabama"}]}
                ]
            }
        ]

        with patch.object(client, '_get', return_value=mock_response):
            rankings = client.get_ap_poll(2024)  # No week specified

            # Should include both weeks
            assert len(rankings) == 2
            assert rankings[0]['week'] == 1
            assert rankings[1]['week'] == 2


@pytest.mark.unit
class TestAPPollImport:
    """Tests for import_ap_poll_rankings function"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    @pytest.fixture
    def sample_teams(self):
        """Create sample team objects"""
        return {
            "Georgia": Team(
                id=1,
                name="Georgia",
                conference=ConferenceType.POWER_5,
                elo_rating=1500
            ),
            "Alabama": Team(
                id=2,
                name="Alabama",
                conference=ConferenceType.POWER_5,
                elo_rating=1495
            )
        }

    def test_import_ap_poll_success(self, mock_db, sample_teams):
        """Test successful AP Poll import"""
        client = CFBDClient()

        # Mock AP Poll data
        mock_poll_data = [
            {
                'season': 2024,
                'week': 5,
                'poll': 'AP Top 25',
                'rank': 1,
                'school': 'Georgia',
                'conference': 'SEC',
                'firstPlaceVotes': 62,
                'points': 1550
            },
            {
                'season': 2024,
                'week': 5,
                'poll': 'AP Top 25',
                'rank': 2,
                'school': 'Alabama',
                'conference': 'SEC',
                'firstPlaceVotes': 0,
                'points': 1488
            }
        ]

        with patch.object(client, 'get_ap_poll', return_value=mock_poll_data):
            count = import_ap_poll_rankings(client, mock_db, sample_teams, 2024, 5)

            assert count == 2
            assert mock_db.add.call_count == 2
            assert mock_db.commit.called

    def test_import_ap_poll_no_data(self, mock_db, sample_teams):
        """Test AP Poll import when no poll data available"""
        client = CFBDClient()

        with patch.object(client, 'get_ap_poll', return_value=[]):
            count = import_ap_poll_rankings(client, mock_db, sample_teams, 2024, 1)

            assert count == 0
            assert not mock_db.add.called
            assert not mock_db.commit.called

    def test_import_ap_poll_team_not_found(self, mock_db, sample_teams):
        """Test AP Poll import when team not in database"""
        client = CFBDClient()

        mock_poll_data = [
            {
                'season': 2024,
                'week': 5,
                'poll': 'AP Top 25',
                'rank': 1,
                'school': 'Unknown Team',  # Not in sample_teams
                'conference': 'SEC',
                'firstPlaceVotes': 62,
                'points': 1550
            }
        ]

        with patch.object(client, 'get_ap_poll', return_value=mock_poll_data):
            count = import_ap_poll_rankings(client, mock_db, sample_teams, 2024, 5)

            # Should skip unknown team
            assert count == 0
            assert not mock_db.add.called

    def test_import_ap_poll_prevents_duplicates(self, mock_db, sample_teams):
        """Test that duplicate rankings are updated, not duplicated"""
        client = CFBDClient()

        # Mock existing ranking
        existing_ranking = Mock(spec=APPollRanking)
        existing_ranking.rank = 3  # Old rank
        existing_ranking.first_place_votes = 0
        existing_ranking.points = 1200
        existing_ranking.poll_type = 'AP Top 25'

        mock_db.query.return_value.filter.return_value.first.return_value = existing_ranking

        mock_poll_data = [
            {
                'season': 2024,
                'week': 5,
                'poll': 'AP Top 25',
                'rank': 1,  # Updated rank
                'school': 'Georgia',
                'conference': 'SEC',
                'firstPlaceVotes': 62,
                'points': 1550
            }
        ]

        with patch.object(client, 'get_ap_poll', return_value=mock_poll_data):
            count = import_ap_poll_rankings(client, mock_db, sample_teams, 2024, 5)

            # Should update existing, not create new
            assert count == 0  # No new rankings added
            assert existing_ranking.rank == 1  # Updated
            assert existing_ranking.first_place_votes == 62
            assert existing_ranking.points == 1550
            assert mock_db.commit.called


@pytest.mark.unit
class TestAPPollModel:
    """Tests for APPollRanking model"""

    def test_ap_poll_ranking_creation(self):
        """Test APPollRanking model creation"""
        ranking = APPollRanking(
            season=2024,
            week=5,
            poll_type='AP Top 25',
            rank=1,
            team_id=1,
            first_place_votes=62,
            points=1550
        )

        assert ranking.season == 2024
        assert ranking.week == 5
        assert ranking.rank == 1
        assert ranking.team_id == 1
        assert ranking.first_place_votes == 62
        assert ranking.points == 1550
