"""Unit Tests for Player Model

Tests the Player database model including:
- Player creation with required and optional fields
- Relationship with Team model
- Unique constraints on cfbd_athlete_id
- Database indexes for efficient queries
- Default values and field validation

Part of Preseason Enhancement Epic - Story 1.1
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Player, Team


@pytest.mark.unit
class TestPlayerModel:
    """Tests for Player model and relationships"""

    def test_create_player_with_all_fields(self, test_db: Session):
        """Test creating player with all fields populated"""
        # Arrange - Create a team first
        team = Team(name="Georgia", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Act - Create player
        player = Player(
            cfbd_athlete_id=12345,
            name="John Smith",
            team_id=team.id,
            position="QB",
            stars=5,
            rating=98.5,
            ranking=3,
            recruiting_year=2024,
        )
        test_db.add(player)
        test_db.commit()
        test_db.refresh(player)

        # Assert
        assert player.id is not None
        assert player.cfbd_athlete_id == 12345
        assert player.name == "John Smith"
        assert player.team_id == team.id
        assert player.position == "QB"
        assert player.stars == 5
        assert player.rating == 98.5
        assert player.ranking == 3
        assert player.recruiting_year == 2024
        assert player.created_at is not None
        assert isinstance(player.created_at, datetime)

    def test_create_player_with_minimal_fields(self, test_db: Session):
        """Test creating player with only required fields (nullable ratings)"""
        # Arrange - Create a team first
        team = Team(name="Alabama", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Act - Create player without star rating and ranking
        player = Player(
            cfbd_athlete_id=67890,
            name="Jane Doe",
            team_id=team.id,
            position="OL",
            recruiting_year=2024,
        )
        test_db.add(player)
        test_db.commit()
        test_db.refresh(player)

        # Assert
        assert player.id is not None
        assert player.cfbd_athlete_id == 67890
        assert player.name == "Jane Doe"
        assert player.team_id == team.id
        assert player.position == "OL"
        assert player.stars is None
        assert player.rating is None
        assert player.ranking is None
        assert player.recruiting_year == 2024

    def test_player_team_relationship(self, test_db: Session):
        """Test that player has relationship with team"""
        # Arrange
        team = Team(name="Ohio State", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        player = Player(
            cfbd_athlete_id=11111,
            name="Mike Johnson",
            team_id=team.id,
            position="RB",
            stars=4,
            recruiting_year=2024,
        )
        test_db.add(player)
        test_db.commit()
        test_db.refresh(player)

        # Act & Assert - Test relationship
        assert player.team is not None
        assert player.team.name == "Ohio State"
        assert player.team.id == team.id

    def test_team_players_relationship(self, test_db: Session):
        """Test that team has collection of players"""
        # Arrange
        team = Team(name="Clemson", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)

        # Add multiple players
        players = [
            Player(
                cfbd_athlete_id=22222,
                name="Player One",
                team_id=team.id,
                position="QB",
                stars=5,
                recruiting_year=2024,
            ),
            Player(
                cfbd_athlete_id=33333,
                name="Player Two",
                team_id=team.id,
                position="WR",
                stars=4,
                recruiting_year=2024,
            ),
            Player(
                cfbd_athlete_id=44444,
                name="Player Three",
                team_id=team.id,
                position="DL",
                stars=5,
                recruiting_year=2024,
            ),
        ]
        for player in players:
            test_db.add(player)
        test_db.commit()
        test_db.refresh(team)

        # Act & Assert - Check team's players collection
        assert len(team.players) == 3
        assert all(p.team_id == team.id for p in team.players)
        positions = {p.position for p in team.players}
        assert positions == {"QB", "WR", "DL"}

    def test_cfbd_athlete_id_must_be_unique(self, test_db: Session):
        """Test that cfbd_athlete_id must be unique across all players"""
        # Arrange - Create team
        team = Team(name="Michigan", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Create first player
        player1 = Player(
            cfbd_athlete_id=55555,
            name="First Player",
            team_id=team.id,
            position="QB",
            recruiting_year=2024,
        )
        test_db.add(player1)
        test_db.commit()

        # Act & Assert - Try to create duplicate cfbd_athlete_id
        player2 = Player(
            cfbd_athlete_id=55555,  # Same ID
            name="Second Player",
            team_id=team.id,
            position="RB",
            recruiting_year=2024,
        )
        test_db.add(player2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_multiple_players_same_team(self, test_db: Session):
        """Test that multiple players can belong to same team"""
        # Arrange
        team = Team(name="Texas", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Act - Add 5 players to same team
        for i in range(5):
            player = Player(
                cfbd_athlete_id=60000 + i,
                name=f"Player {i}",
                team_id=team.id,
                position="OL",
                stars=3 + (i % 3),
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Assert
        players = test_db.query(Player).filter(Player.team_id == team.id).all()
        assert len(players) == 5
        assert all(p.team_id == team.id for p in players)

    def test_player_position_field(self, test_db: Session):
        """Test various position abbreviations"""
        # Arrange
        team = Team(name="LSU", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        positions = ["QB", "RB", "WR", "TE", "OL", "OT", "OG", "C", "DL", "DE", "DT", "LB", "DB", "CB", "S", "K", "P"]

        # Act - Create players with different positions
        for i, pos in enumerate(positions):
            player = Player(
                cfbd_athlete_id=70000 + i,
                name=f"Player {pos}",
                team_id=team.id,
                position=pos,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Assert
        all_players = test_db.query(Player).filter(Player.team_id == team.id).all()
        assert len(all_players) == len(positions)
        stored_positions = {p.position for p in all_players}
        assert stored_positions == set(positions)

    def test_player_recruiting_year_field(self, test_db: Session):
        """Test recruiting_year field for different years"""
        # Arrange
        team = Team(name="Florida", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Act - Create players from different recruiting years
        years = [2020, 2021, 2022, 2023, 2024]
        for i, year in enumerate(years):
            player = Player(
                cfbd_athlete_id=80000 + i,
                name=f"Player {year}",
                team_id=team.id,
                position="QB",
                recruiting_year=year,
            )
            test_db.add(player)
        test_db.commit()

        # Assert - Query by recruiting year
        for year in years:
            players = test_db.query(Player).filter(Player.recruiting_year == year).all()
            assert len(players) == 1
            assert players[0].recruiting_year == year

    def test_player_star_rating_range(self, test_db: Session):
        """Test star ratings from 1-5"""
        # Arrange
        team = Team(name="Penn State", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        # Act - Create players with different star ratings
        for stars in range(1, 6):  # 1 through 5
            player = Player(
                cfbd_athlete_id=90000 + stars,
                name=f"{stars} Star Player",
                team_id=team.id,
                position="RB",
                stars=stars,
                recruiting_year=2024,
            )
            test_db.add(player)
        test_db.commit()

        # Assert
        for stars in range(1, 6):
            players = test_db.query(Player).filter(Player.stars == stars).all()
            assert len(players) >= 1
            assert all(p.stars == stars for p in players)

    def test_player_repr(self, test_db: Session):
        """Test player string representation"""
        # Arrange
        team = Team(name="Notre Dame", conference=ConferenceType.POWER_5)
        test_db.add(team)
        test_db.commit()

        player = Player(
            cfbd_athlete_id=99999,
            name="Test Player",
            team_id=team.id,
            position="QB",
            stars=5,
            recruiting_year=2024,
        )
        test_db.add(player)
        test_db.commit()
        test_db.refresh(player)

        # Act
        repr_string = repr(player)

        # Assert
        assert "Test Player" in repr_string
        assert "QB" in repr_string
        assert "5" in repr_string
        assert "Notre Dame" in repr_string

    def test_query_players_by_position_and_team(self, test_db: Session):
        """Test querying players by position and team (tests index usage)"""
        # Arrange - Create two teams
        team1 = Team(name="Oklahoma", conference=ConferenceType.POWER_5)
        team2 = Team(name="USC", conference=ConferenceType.POWER_5)
        test_db.add(team1)
        test_db.add(team2)
        test_db.commit()

        # Add QBs to both teams
        for i in range(3):
            test_db.add(
                Player(
                    cfbd_athlete_id=100000 + i,
                    name=f"Oklahoma QB {i}",
                    team_id=team1.id,
                    position="QB",
                    stars=4 + (i % 2),
                    recruiting_year=2024,
                )
            )
            test_db.add(
                Player(
                    cfbd_athlete_id=110000 + i,
                    name=f"USC QB {i}",
                    team_id=team2.id,
                    position="QB",
                    stars=4,
                    recruiting_year=2024,
                )
            )
        test_db.commit()

        # Act - Query QBs for team1 only (this query should use idx_players_team_position)
        team1_qbs = (
            test_db.query(Player)
            .filter(Player.team_id == team1.id, Player.position == "QB")
            .all()
        )

        # Assert
        assert len(team1_qbs) == 3
        assert all(p.team_id == team1.id for p in team1_qbs)
        assert all(p.position == "QB" for p in team1_qbs)
        assert all("Oklahoma" in p.name for p in team1_qbs)
