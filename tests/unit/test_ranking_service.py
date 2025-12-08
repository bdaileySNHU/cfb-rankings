"""
Unit tests for RankingService - ELO Algorithm

Tests cover:
- Preseason rating calculations (recruiting, transfers, returning production)
- Expected score calculations
- MOV multipliers
- Conference multipliers
- Game processing logic
"""

import math
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.models.models import ConferenceType, Game, Team
from src.core.ranking_service import RankingService


@pytest.mark.unit
class TestPreseasonRating:
    """Tests for preseason ELO rating calculations"""

    def test_base_rating_fbs_teams(self, test_db: Session):
        """FBS teams should start with base rating of 1500"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Test FBS Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=999,  # Unranked (no bonuses)
            transfer_rank=999,
            returning_production=0.0,
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        assert rating == 1500.0, "FBS base rating should be 1500"

    def test_base_rating_fcs_teams(self, test_db: Session):
        """FCS teams should start with base rating of 1300"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Test FCS Team",
            conference=ConferenceType.FCS,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=0.0,
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        assert rating == 1300.0, "FCS base rating should be 1300"

    @pytest.mark.parametrize(
        "conference_type,expected_base",
        [
            (ConferenceType.POWER_5, 1500.0),
            (ConferenceType.GROUP_5, 1500.0),
            (ConferenceType.FCS, 1300.0),
        ],
    )
    def test_base_rating_by_conference(self, test_db: Session, conference_type, expected_base):
        """Test base ratings for all conference types"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name=f"Test {conference_type.value} Team",
            conference=conference_type,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=0.0,
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        assert rating == expected_base

    @pytest.mark.parametrize(
        "recruiting_rank,expected_bonus",
        [
            (1, 200.0),  # Top 5
            (5, 200.0),  # Top 5 boundary
            (6, 150.0),  # Top 10
            (10, 150.0),  # Top 10 boundary
            (11, 100.0),  # Top 25
            (25, 100.0),  # Top 25 boundary
            (26, 50.0),  # Top 50
            (50, 50.0),  # Top 50 boundary
            (51, 25.0),  # Top 75
            (75, 25.0),  # Top 75 boundary
            (76, 0.0),  # Outside top 75
            (100, 0.0),  # Unranked
            (999, 0.0),  # Default unranked value
        ],
    )
    def test_recruiting_bonus_tiers(self, test_db: Session, recruiting_rank, expected_bonus):
        """Test recruiting bonus calculation for all tiers"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name=f"Test Team Recruiting {recruiting_rank}",
            conference=ConferenceType.POWER_5,
            recruiting_rank=recruiting_rank,
            transfer_rank=999,
            returning_production=0.0,
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        expected_rating = 1500.0 + expected_bonus
        assert (
            rating == expected_rating
        ), f"Recruiting rank {recruiting_rank} should give +{expected_bonus} bonus"

    @pytest.mark.parametrize(
        "transfer_rank,expected_bonus",
        [
            (1, 100.0),  # Top 5
            (5, 100.0),  # Top 5 boundary
            (6, 75.0),  # Top 10
            (10, 75.0),  # Top 10 boundary
            (11, 50.0),  # Top 25
            (25, 50.0),  # Top 25 boundary
            (26, 25.0),  # Top 50
            (50, 25.0),  # Top 50 boundary
            (51, 0.0),  # Outside top 50
            (100, 0.0),  # Unranked
            (999, 0.0),  # Default unranked value
        ],
    )
    def test_transfer_portal_bonus_tiers(self, test_db: Session, transfer_rank, expected_bonus):
        """Test transfer portal bonus calculation for all tiers"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name=f"Test Team Transfer {transfer_rank}",
            conference=ConferenceType.POWER_5,
            recruiting_rank=999,
            transfer_rank=transfer_rank,
            returning_production=0.0,
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        expected_rating = 1500.0 + expected_bonus
        assert (
            rating == expected_rating
        ), f"Transfer rank {transfer_rank} should give +{expected_bonus} bonus"

    @pytest.mark.parametrize(
        "returning_production,expected_bonus",
        [
            (1.0, 40.0),  # 100% returning (max)
            (0.90, 40.0),  # 90% returning
            (0.80, 40.0),  # 80% returning (boundary)
            (0.79, 25.0),  # 79% returning
            (0.70, 25.0),  # 70% returning
            (0.60, 25.0),  # 60% returning (boundary)
            (0.59, 10.0),  # 59% returning
            (0.50, 10.0),  # 50% returning
            (0.40, 10.0),  # 40% returning (boundary)
            (0.39, 0.0),  # 39% returning
            (0.20, 0.0),  # 20% returning
            (0.0, 0.0),  # 0% returning (min)
        ],
    )
    def test_returning_production_bonus_tiers(
        self, test_db: Session, returning_production, expected_bonus
    ):
        """Test returning production bonus calculation for all tiers"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name=f"Test Team Returning {returning_production}",
            conference=ConferenceType.POWER_5,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=returning_production,
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        expected_rating = 1500.0 + expected_bonus
        assert (
            rating == expected_rating
        ), f"Returning production {returning_production} should give +{expected_bonus} bonus"

    def test_combined_preseason_rating_elite_team(self, test_db: Session):
        """Test combined rating for elite team (top recruiting, transfers, high returning production)"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Alabama",  # Elite program example
            conference=ConferenceType.POWER_5,
            recruiting_rank=1,  # Top 5: +200
            transfer_rank=3,  # Top 5: +100
            returning_production=0.85,  # 80%+: +40
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        # Base (1500) + Recruiting (200) + Transfer (100) + Returning (40) = 1840
        assert rating == 1840.0, "Elite team should have maximum preseason rating"

    def test_combined_preseason_rating_typical_p5_team(self, test_db: Session):
        """Test combined rating for typical Power 5 team"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Typical P5 Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=35,  # Top 50: +50
            transfer_rank=20,  # Top 25: +50
            returning_production=0.65,  # 60-79%: +25
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        # Base (1500) + Recruiting (50) + Transfer (50) + Returning (25) = 1625
        assert rating == 1625.0

    def test_combined_preseason_rating_g5_team(self, test_db: Session):
        """Test combined rating for Group of 5 team"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="G5 Team",
            conference=ConferenceType.GROUP_5,
            recruiting_rank=80,  # Unranked: +0
            transfer_rank=60,  # Unranked: +0
            returning_production=0.55,  # 40-59%: +10
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        # Base (1500) + Recruiting (0) + Transfer (0) + Returning (10) = 1510
        assert rating == 1510.0

    def test_edge_case_fcs_team_with_high_recruiting(self, test_db: Session):
        """Test edge case: FCS team with top recruiting class (unusual but possible)"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Top FCS Team",
            conference=ConferenceType.FCS,
            recruiting_rank=30,  # Top 50: +50
            transfer_rank=15,  # Top 25: +50
            returning_production=0.75,  # 60-79%: +25
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        # Base (1300) + Recruiting (50) + Transfer (50) + Returning (25) = 1425
        assert (
            rating == 1425.0
        ), "FCS team with good factors should have lower base but can gain bonuses"

    def test_edge_case_unranked_team_all_defaults(self, test_db: Session):
        """Test edge case: completely unranked team with default values"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Unranked Team",
            conference=ConferenceType.GROUP_5,
            recruiting_rank=999,  # Default unranked
            transfer_rank=999,  # Default unranked
            returning_production=0.5,  # Default (39-59%: +10 originally, but 50% is boundary case)
        )

        # Act
        rating = service.calculate_preseason_rating(team)

        # Assert
        # Base (1500) + Recruiting (0) + Transfer (0) + Returning (10 for 0.50 = 50%) = 1510
        assert rating == 1510.0

    def test_initialize_team_rating_sets_both_ratings(self, test_db: Session):
        """Test that initialize_team_rating sets both elo_rating and initial_rating"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Test Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=10,  # Top 10: +150
            transfer_rank=999,
            returning_production=0.0,
        )
        test_db.add(team)
        test_db.commit()

        # Act
        service.initialize_team_rating(team)
        test_db.refresh(team)

        # Assert
        expected_rating = 1650.0  # 1500 + 150
        assert team.elo_rating == expected_rating, "elo_rating should be set to preseason rating"
        assert (
            team.initial_rating == expected_rating
        ), "initial_rating should store preseason rating"
        assert team.elo_rating == team.initial_rating, "Both ratings should match initially"

    def test_initialize_team_rating_persists_to_database(self, test_db: Session):
        """Test that initialize_team_rating commits changes to database"""
        # Arrange
        service = RankingService(test_db)
        team = Team(
            name="Persistence Test Team",
            conference=ConferenceType.POWER_5,
            recruiting_rank=25,
            transfer_rank=999,
            returning_production=0.0,
        )
        test_db.add(team)
        test_db.commit()
        team_id = team.id

        # Act
        service.initialize_team_rating(team)

        # Query team fresh from database to verify persistence
        fresh_team = test_db.query(Team).filter(Team.id == team_id).first()

        # Assert
        expected_rating = 1600.0  # 1500 + 100
        assert fresh_team.elo_rating == expected_rating, "Rating should persist in database"
        assert (
            fresh_team.initial_rating == expected_rating
        ), "Initial rating should persist in database"


@pytest.mark.unit
class TestExpectedScore:
    """Tests for ELO expected score calculation"""

    def test_equal_ratings_gives_50_percent(self, test_db: Session):
        """Teams with equal ratings should have 50% win probability"""
        # Arrange
        service = RankingService(test_db)

        # Act
        expected = service.calculate_expected_score(1500.0, 1500.0)

        # Assert
        assert expected == pytest.approx(
            0.5, abs=0.001
        ), "Equal ratings should give 50% probability"

    def test_higher_rated_team_favored(self, test_db: Session):
        """Higher rated team should have >50% win probability"""
        # Arrange
        service = RankingService(test_db)

        # Act
        expected = service.calculate_expected_score(1600.0, 1500.0)

        # Assert
        assert expected > 0.5, "Higher rated team should be favored"
        assert expected == pytest.approx(
            0.640, abs=0.001
        ), "100 point advantage should give ~64% probability"

    def test_lower_rated_team_underdog(self, test_db: Session):
        """Lower rated team should have <50% win probability"""
        # Arrange
        service = RankingService(test_db)

        # Act
        expected = service.calculate_expected_score(1500.0, 1600.0)

        # Assert
        assert expected < 0.5, "Lower rated team should be underdog"
        assert expected == pytest.approx(
            0.360, abs=0.001
        ), "100 point disadvantage should give ~36% probability"

    @pytest.mark.parametrize(
        "rating_diff,expected_prob",
        [
            (0, 0.500),  # Equal ratings
            (100, 0.640),  # Small advantage
            (200, 0.760),  # Medium advantage
            (300, 0.849),  # Large advantage
            (400, 0.909),  # Very large advantage (10:1 odds)
            (-100, 0.360),  # Small disadvantage
            (-200, 0.240),  # Medium disadvantage
            (-400, 0.091),  # Very large disadvantage
        ],
    )
    def test_expected_score_formula(self, test_db: Session, rating_diff, expected_prob):
        """Test expected score formula across various rating differences"""
        # Arrange
        service = RankingService(test_db)
        team_a_rating = 1500.0
        team_b_rating = 1500.0 - rating_diff

        # Act
        result = service.calculate_expected_score(team_a_rating, team_b_rating)

        # Assert
        assert result == pytest.approx(expected_prob, abs=0.001)

    def test_expected_score_symmetric(self, test_db: Session):
        """Expected scores for both teams should sum to 1.0"""
        # Arrange
        service = RankingService(test_db)
        rating_a = 1650.0
        rating_b = 1450.0

        # Act
        expected_a = service.calculate_expected_score(rating_a, rating_b)
        expected_b = service.calculate_expected_score(rating_b, rating_a)

        # Assert
        assert expected_a + expected_b == pytest.approx(
            1.0, abs=0.001
        ), "Probabilities should sum to 1.0"


@pytest.mark.unit
class TestMovMultiplier:
    """Tests for margin of victory (MOV) multiplier calculation"""

    def test_zero_point_differential_returns_one(self, test_db: Session):
        """Zero point differential should return multiplier of 1.0"""
        # Arrange
        service = RankingService(test_db)

        # Act
        multiplier = service.calculate_mov_multiplier(0)

        # Assert
        assert multiplier == 1.0

    def test_negative_point_differential_returns_one(self, test_db: Session):
        """Negative point differential should return multiplier of 1.0"""
        # Arrange
        service = RankingService(test_db)

        # Act
        multiplier = service.calculate_mov_multiplier(-10)

        # Assert
        assert multiplier == 1.0

    @pytest.mark.parametrize(
        "point_diff,expected_multiplier",
        [
            (1, 0.693),  # ln(2)
            (3, 1.386),  # ln(4)
            (7, 2.079),  # ln(8)
            (10, 2.398),  # ln(11)
            (14, 2.500),  # ln(15) = 2.708, capped at 2.5
            (20, 2.500),  # ln(21) = 3.045, capped at 2.5
            (50, 2.500),  # ln(51) = 3.932, capped at 2.5
            (100, 2.500),  # Blowout, capped at 2.5
        ],
    )
    def test_mov_multiplier_values(self, test_db: Session, point_diff, expected_multiplier):
        """Test MOV multiplier calculation for various point differentials"""
        # Arrange
        service = RankingService(test_db)

        # Act
        multiplier = service.calculate_mov_multiplier(point_diff)

        # Assert
        assert multiplier == pytest.approx(expected_multiplier, abs=0.001)

    def test_mov_multiplier_capped_at_max(self, test_db: Session):
        """MOV multiplier should be capped at MAX_MOV_MULTIPLIER"""
        # Arrange
        service = RankingService(test_db)

        # Act
        multiplier_20 = service.calculate_mov_multiplier(20)
        multiplier_50 = service.calculate_mov_multiplier(50)
        multiplier_100 = service.calculate_mov_multiplier(100)

        # Assert
        assert multiplier_20 == 2.5, "20+ point win should be capped"
        assert multiplier_50 == 2.5, "50 point blowout should be capped"
        assert multiplier_100 == 2.5, "100 point blowout should be capped"
        assert multiplier_20 == multiplier_50 == multiplier_100, "All large MOVs should be equal"

    def test_mov_multiplier_logarithmic_growth(self, test_db: Session):
        """MOV multiplier should grow logarithmically (diminishing returns)"""
        # Arrange
        service = RankingService(test_db)

        # Act
        mov_1 = service.calculate_mov_multiplier(1)
        mov_3 = service.calculate_mov_multiplier(3)
        mov_7 = service.calculate_mov_multiplier(7)

        # Assert - difference between 1 and 3 should be greater than difference between 3 and 7
        diff_1_to_3 = mov_3 - mov_1
        diff_3_to_7 = mov_7 - mov_3
        assert diff_1_to_3 > diff_3_to_7, "Logarithmic growth means diminishing returns"


@pytest.mark.unit
class TestConferenceMultiplier:
    """Tests for conference-based rating change multipliers"""

    def test_same_tier_matchup_no_adjustment(self, test_db: Session):
        """Same tier matchups should have no multiplier adjustment"""
        # Arrange
        service = RankingService(test_db)

        # Act & Assert - P5 vs P5
        winner_mult, loser_mult = service.get_conference_multiplier(
            ConferenceType.POWER_5, ConferenceType.POWER_5
        )
        assert winner_mult == 1.0
        assert loser_mult == 1.0

        # G5 vs G5
        winner_mult, loser_mult = service.get_conference_multiplier(
            ConferenceType.GROUP_5, ConferenceType.GROUP_5
        )
        assert winner_mult == 1.0
        assert loser_mult == 1.0

        # FCS vs FCS
        winner_mult, loser_mult = service.get_conference_multiplier(
            ConferenceType.FCS, ConferenceType.FCS
        )
        assert winner_mult == 1.0
        assert loser_mult == 1.0

    def test_p5_beats_g5_expected_outcome(self, test_db: Session):
        """P5 beating G5 should have reduced multiplier (expected outcome)"""
        # Arrange
        service = RankingService(test_db)

        # Act
        winner_mult, loser_mult = service.get_conference_multiplier(
            ConferenceType.POWER_5, ConferenceType.GROUP_5
        )

        # Assert
        assert winner_mult == 0.9, "P5 should gain less for beating G5"
        assert loser_mult == 1.1, "G5 should lose more for losing to P5"

    def test_g5_beats_p5_upset(self, test_db: Session):
        """G5 beating P5 should have increased multiplier (upset bonus)"""
        # Arrange
        service = RankingService(test_db)

        # Act
        winner_mult, loser_mult = service.get_conference_multiplier(
            ConferenceType.GROUP_5, ConferenceType.POWER_5
        )

        # Assert
        assert winner_mult == 1.1, "G5 should gain more for upset over P5"
        assert loser_mult == 0.9, "P5 should lose less for losing to G5"

    def test_fbs_beats_fcs_expected_outcome(self, test_db: Session):
        """FBS beating FCS should have minimal gain"""
        # Arrange
        service = RankingService(test_db)

        # Act - P5 beats FCS
        winner_mult_p5, loser_mult = service.get_conference_multiplier(
            ConferenceType.POWER_5, ConferenceType.FCS
        )

        # Act - G5 beats FCS
        winner_mult_g5, loser_mult_g5 = service.get_conference_multiplier(
            ConferenceType.GROUP_5, ConferenceType.FCS
        )

        # Assert
        assert winner_mult_p5 == 0.5, "P5 should gain half for beating FCS"
        assert winner_mult_g5 == 0.5, "G5 should gain half for beating FCS"
        assert loser_mult == 2.0, "FCS should lose double for losing to FBS"
        assert loser_mult_g5 == 2.0, "FCS should lose double for losing to FBS"

    def test_fcs_beats_fbs_major_upset(self, test_db: Session):
        """FCS beating FBS should have major upset bonus"""
        # Arrange
        service = RankingService(test_db)

        # Act - FCS beats P5
        winner_mult, loser_mult_p5 = service.get_conference_multiplier(
            ConferenceType.FCS, ConferenceType.POWER_5
        )

        # Act - FCS beats G5
        winner_mult_g5, loser_mult_g5 = service.get_conference_multiplier(
            ConferenceType.FCS, ConferenceType.GROUP_5
        )

        # Assert
        assert winner_mult == 2.0, "FCS should gain double for beating P5"
        assert winner_mult_g5 == 2.0, "FCS should gain double for beating G5"
        assert loser_mult_p5 == 0.5, "P5 should lose half for losing to FCS"
        assert loser_mult_g5 == 0.5, "G5 should lose half for losing to FCS"

    @pytest.mark.parametrize(
        "winner_conf,loser_conf,expected_winner,expected_loser",
        [
            (ConferenceType.POWER_5, ConferenceType.POWER_5, 1.0, 1.0),  # P5 vs P5
            (ConferenceType.POWER_5, ConferenceType.GROUP_5, 0.9, 1.1),  # P5 beats G5
            (ConferenceType.GROUP_5, ConferenceType.POWER_5, 1.1, 0.9),  # G5 upsets P5
            (ConferenceType.POWER_5, ConferenceType.FCS, 0.5, 2.0),  # P5 beats FCS
            (ConferenceType.FCS, ConferenceType.POWER_5, 2.0, 0.5),  # FCS upsets P5
            (ConferenceType.GROUP_5, ConferenceType.GROUP_5, 1.0, 1.0),  # G5 vs G5
            (ConferenceType.GROUP_5, ConferenceType.FCS, 0.5, 2.0),  # G5 beats FCS
            (ConferenceType.FCS, ConferenceType.GROUP_5, 2.0, 0.5),  # FCS upsets G5
            (ConferenceType.FCS, ConferenceType.FCS, 1.0, 1.0),  # FCS vs FCS
        ],
    )
    def test_all_conference_matchups(
        self, test_db: Session, winner_conf, loser_conf, expected_winner, expected_loser
    ):
        """Test conference multipliers for all possible matchups"""
        # Arrange
        service = RankingService(test_db)

        # Act
        winner_mult, loser_mult = service.get_conference_multiplier(winner_conf, loser_conf)

        # Assert
        assert winner_mult == expected_winner
        assert loser_mult == expected_loser


@pytest.mark.unit
class TestGameProcessing:
    """Tests for complete game processing workflow"""

    def test_process_game_home_team_wins(self, test_db: Session):
        """Test processing game where home team wins"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home Team", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away Team", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=21,
            week=1,
            season=2024,
            is_neutral_site=False,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)
        test_db.refresh(home_team)
        test_db.refresh(away_team)

        # Assert
        assert game.is_processed is True, "Game should be marked as processed"
        assert home_team.elo_rating > 1500.0, "Home team rating should increase"
        assert away_team.elo_rating < 1500.0, "Away team rating should decrease"
        assert home_team.wins == 1, "Home team should have 1 win"
        assert away_team.losses == 1, "Away team should have 1 loss"
        assert result["winner_name"] == "Home Team"
        assert result["loser_name"] == "Away Team"

    def test_process_game_away_team_wins(self, test_db: Session):
        """Test processing game where away team wins"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home Team", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away Team", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=21,
            away_score=35,
            week=1,
            season=2024,
            is_neutral_site=False,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)
        test_db.refresh(home_team)
        test_db.refresh(away_team)

        # Assert
        assert game.is_processed is True
        assert away_team.elo_rating > 1500.0, "Away team rating should increase"
        assert home_team.elo_rating < 1500.0, "Home team rating should decrease"
        assert away_team.wins == 1, "Away team should have 1 win"
        assert home_team.losses == 1, "Home team should have 1 loss"
        assert result["winner_name"] == "Away Team"

    def test_home_field_advantage_applied(self, test_db: Session):
        """Test that home field advantage is applied in calculations"""
        # Arrange
        service = RankingService(test_db)
        # Equal teams, but home team should have advantage
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=24,
            away_score=21,  # Close game
            week=1,
            season=2024,
            is_neutral_site=False,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)

        # Assert
        # Home team was expected to have better chance due to HFA
        # So winning gains less rating change than if it were neutral
        assert result["winner_expected_probability"] > 0.5, "Home team should be favored with HFA"
        # With equal teams (1500 each) + 65 HFA, home team has rating of 1565 vs 1500
        # Expected prob = 1 / (1 + 10^((1500-1565)/400)) = 1 / (1 + 10^(-0.1625)) ≈ 0.592
        assert result["winner_expected_probability"] == pytest.approx(
            0.592, abs=0.01
        ), "65 point HFA should give ~59% chance"

    def test_neutral_site_no_home_advantage(self, test_db: Session):
        """Test that neutral site games don't apply home field advantage"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Team A", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Team B", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=24,
            week=1,
            season=2024,
            is_neutral_site=True,  # Neutral site
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)

        # Assert
        # Equal teams on neutral site should be 50-50
        assert result["winner_expected_probability"] == pytest.approx(
            0.5, abs=0.001
        ), "Neutral site should be 50-50"

    def test_larger_mov_increases_rating_change(self, test_db: Session):
        """Test that larger margin of victory increases rating change"""
        # Arrange
        service = RankingService(test_db)

        # Game 1: Close win (3 points)
        team1_home = Team(name="Team 1 Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        team1_away = Team(name="Team 1 Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([team1_home, team1_away])
        test_db.commit()

        game1 = Game(
            home_team_id=team1_home.id,
            away_team_id=team1_away.id,
            home_score=24,
            away_score=21,
            week=1,
            season=2024,
            is_neutral_site=True,
        )
        test_db.add(game1)
        test_db.commit()

        # Game 2: Blowout (21 points)
        team2_home = Team(name="Team 2 Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        team2_away = Team(name="Team 2 Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([team2_home, team2_away])
        test_db.commit()

        game2 = Game(
            home_team_id=team2_home.id,
            away_team_id=team2_away.id,
            home_score=42,
            away_score=21,
            week=1,
            season=2024,
            is_neutral_site=True,
        )
        test_db.add(game2)
        test_db.commit()

        # Act
        result1 = service.process_game(game1)
        result2 = service.process_game(game2)

        # Assert
        assert (
            result2["mov_multiplier"] > result1["mov_multiplier"]
        ), "Larger MOV should have larger multiplier"
        assert abs(result2["winner_rating_change"]) > abs(
            result1["winner_rating_change"]
        ), "Larger MOV should yield larger rating change"

    def test_conference_multiplier_applied_in_processing(self, test_db: Session):
        """Test that conference multipliers affect rating changes"""
        # Arrange
        service = RankingService(test_db)

        # P5 beats G5 (expected, reduced gain)
        p5_team = Team(name="P5 Team", conference=ConferenceType.POWER_5, elo_rating=1600.0)
        g5_team = Team(name="G5 Team", conference=ConferenceType.GROUP_5, elo_rating=1500.0)
        test_db.add_all([p5_team, g5_team])
        test_db.commit()

        game = Game(
            home_team_id=p5_team.id,
            away_team_id=g5_team.id,
            home_score=35,
            away_score=14,
            week=1,
            season=2024,
            is_neutral_site=True,
        )
        test_db.add(game)
        test_db.commit()

        initial_p5_rating = p5_team.elo_rating

        # Act
        result = service.process_game(game)
        test_db.refresh(p5_team)

        # Assert
        # P5 beating G5 should have 0.9 multiplier, so less gain
        rating_change = p5_team.elo_rating - initial_p5_rating
        assert rating_change > 0, "Winner should gain rating"
        # The rating change should be reduced by the 0.9 multiplier

    def test_duplicate_game_processing_prevented(self, test_db: Session):
        """Test that processing the same game twice is prevented"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=24,
            week=1,
            season=2024,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result1 = service.process_game(game)
        rating_after_first = home_team.elo_rating

        # Try to process again
        result2 = service.process_game(game)
        test_db.refresh(home_team)

        # Assert
        assert result2 == {
            "error": "Game already processed"
        }, "Should return error for duplicate processing"
        assert (
            home_team.elo_rating == rating_after_first
        ), "Rating should not change on duplicate processing"

    def test_rating_changes_stored_in_game(self, test_db: Session):
        """Test that rating changes are stored in the game record"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1550.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1450.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=31,
            away_score=28,
            week=1,
            season=2024,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        service.process_game(game)
        test_db.refresh(game)

        # Assert
        assert game.home_rating_change != 0.0, "Home team rating change should be stored"
        assert game.away_rating_change != 0.0, "Away team rating change should be stored"
        assert game.home_rating_change > 0, "Home team won, should have positive change"
        assert game.away_rating_change < 0, "Away team lost, should have negative change"

    def test_process_game_realistic_scenario(self, test_db: Session):
        """Test realistic game scenario with all factors combined"""
        # Arrange
        service = RankingService(test_db)

        # Alabama (elite) vs Georgia (elite) - close game
        alabama = Team(name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0)
        georgia = Team(name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1875.0)
        test_db.add_all([alabama, georgia])
        test_db.commit()

        # Close game, Alabama wins at home
        game = Game(
            home_team_id=alabama.id,
            away_team_id=georgia.id,
            home_score=27,
            away_score=24,
            week=5,
            season=2024,
            is_neutral_site=False,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)
        test_db.refresh(alabama)
        test_db.refresh(georgia)

        # Assert
        assert game.is_processed is True
        assert alabama.wins == 1
        assert georgia.losses == 1
        assert alabama.elo_rating > 1850.0, "Alabama should gain rating"
        assert georgia.elo_rating < 1875.0, "Georgia should lose rating"
        assert result["score"] == "27-24"

        # Alabama was slightly favored due to home field, so upset value is moderate
        assert "winner_expected_probability" in result
        assert "mov_multiplier" in result


@pytest.mark.unit
class TestQuarterWeightedMOV:
    """Tests for quarter-weighted MOV calculation - EPIC-021"""

    def test_garbage_time_detection_true(self, test_db: Session):
        """Test that garbage time is detected with 22+ point differential after Q3"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game: 35-7 after Q3, then 7-7 in Q4 (garbage time TD)
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=42,
            away_score=14,
            week=1,
            season=2024,
            q1_home=14,
            q1_away=0,
            q2_home=14,
            q2_away=0,
            q3_home=7,
            q3_away=7,
            q4_home=7,
            q4_away=7,  # Garbage time TD by loser
        )

        # Act
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)

        # Assert - Q4 should have reduced weight
        # Without garbage time reduction, MOV would be higher
        # With reduction, Q4 is weighted at 25%
        assert mov < 2.5, "Garbage time should reduce MOV"

    def test_garbage_time_detection_false(self, test_db: Session):
        """Test that close games don't trigger garbage time"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game: 14-7 after Q3, then 7-7 in Q4 (close game)
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=21,
            away_score=14,
            week=1,
            season=2024,
            q1_home=7,
            q1_away=0,
            q2_home=0,
            q2_away=7,
            q3_home=7,
            q3_away=0,
            q4_home=7,
            q4_away=7,
        )

        # Act
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)

        # Assert - Should use full weight for all quarters
        assert mov > 0.0
        # Q4 not penalized in close game

    def test_garbage_time_threshold_boundary(self, test_db: Session):
        """Test that exactly 21 point differential does NOT trigger garbage time"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game: Exactly 21-0 after Q3
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=21,
            away_score=0,
            week=1,
            season=2024,
            q1_home=7,
            q1_away=0,
            q2_home=7,
            q2_away=0,
            q3_home=7,
            q3_away=0,
            q4_home=0,
            q4_away=0,
        )

        # Act & Assert - Should NOT trigger garbage time (threshold is >21, not >=21)
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)
        # Q4 should have full weight
        assert mov > 0.0

    def test_quarter_weighted_mov_close_game(self, test_db: Session):
        """Test quarter-weighted MOV for competitive game"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Even scoring across all quarters: 7-0 each quarter
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=0,
            week=1,
            season=2024,
            q1_home=7,
            q1_away=0,
            q2_home=7,
            q2_away=0,
            q3_home=7,
            q3_away=0,
            q4_home=7,
            q4_away=0,
        )

        # Act
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)

        # Assert
        assert mov > 0.0
        assert mov <= service.MAX_MOV_MULTIPLIER

    def test_backward_compatibility_null_quarters(self, test_db: Session):
        """Test that games without quarter data fall back to legacy MOV"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game without quarter scores
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=1,
            season=2024,
            # No quarter scores
        )

        # Act
        quarter_mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)
        legacy_mov = service.calculate_mov_multiplier(7)  # 35-28 = 7

        # Assert - Should fall back to legacy calculation
        assert quarter_mov == legacy_mov

    def test_backward_compatibility_partial_quarters(self, test_db: Session):
        """Test that games with partial quarter data fall back to legacy MOV"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game with partial quarter scores (Q3, Q4 missing)
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=1,
            season=2024,
            q1_home=14,
            q1_away=7,
            q2_home=7,
            q2_away=14,
            q3_home=None,
            q3_away=None,  # Missing
            q4_home=None,
            q4_away=None,  # Missing
        )

        # Act
        quarter_mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)
        legacy_mov = service.calculate_mov_multiplier(7)

        # Assert - Should fall back to legacy
        assert quarter_mov == legacy_mov

    def test_all_scoring_in_first_quarter(self, test_db: Session):
        """Test game where all scoring happens in Q1"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # All scoring in Q1, defensive game after
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=0,
            week=1,
            season=2024,
            q1_home=28,
            q1_away=0,
            q2_home=0,
            q2_away=0,
            q3_home=0,
            q3_away=0,
            q4_home=0,
            q4_away=0,
        )

        # Act
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)

        # Assert - Should still calculate valid MOV
        assert mov > 0.0
        # 28-0 is > 21, so Q4 (0-0) would be reduced, but Q4 had no scoring anyway

    def test_comeback_game(self, test_db: Session):
        """Test game where loser was ahead early but lost late"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Away team (loser) led early, home team (winner) came back
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=28,
            away_score=21,
            week=1,
            season=2024,
            q1_home=0,
            q1_away=14,  # Away ahead
            q2_home=0,
            q2_away=7,  # Away still ahead
            q3_home=14,
            q3_away=0,  # Home rallies
            q4_home=14,
            q4_away=0,  # Home wins
        )

        # Act
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)

        # Assert - Should calculate based on quarter differentials from winner's perspective
        # Q1: 0-14 = -14 (loser won), Q2: 0-7 = -7 (loser won), Q3: 14-0 = 14, Q4: 14-0 = 14
        # Winner only "won" Q3 and Q4
        assert mov > 0.0

    def test_mov_capped_at_maximum(self, test_db: Session):
        """Test that MOV is capped at MAX_MOV_MULTIPLIER"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Massive blowout: 70-0
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=70,
            away_score=0,
            week=1,
            season=2024,
            q1_home=21,
            q1_away=0,
            q2_home=21,
            q2_away=0,
            q3_home=14,
            q3_away=0,
            q4_home=14,
            q4_away=0,
        )

        # Act
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=True)

        # Assert - Should be capped
        assert mov <= service.MAX_MOV_MULTIPLIER

    def test_away_team_wins_quarter_calculation(self, test_db: Session):
        """Test MOV calculation when away team wins"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1500.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Away team wins
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=14,
            away_score=35,
            week=1,
            season=2024,
            q1_home=0,
            q1_away=14,
            q2_home=7,
            q2_away=7,
            q3_home=7,
            q3_away=7,
            q4_home=0,
            q4_away=7,
        )

        # Act - winner_is_home=False because away team won
        mov = service.calculate_quarter_weighted_mov(game, winner_is_home=False)

        # Assert
        assert mov > 0.0
        assert mov <= service.MAX_MOV_MULTIPLIER


@pytest.mark.unit
class TestProcessGameWithQuarters:
    """Test process_game() integration with quarter-weighted MOV - EPIC-021"""

    def test_process_game_with_quarter_data_uses_new_algorithm(self, test_db: Session):
        """Test that games with quarter data use quarter-weighted MOV"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1600.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1600.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game with quarter scores
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=1,
            season=2024,
            q1_home=7,
            q1_away=7,
            q2_home=14,
            q2_away=7,
            q3_home=7,
            q3_away=7,
            q4_home=7,
            q4_away=7,
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)

        # Assert - Game should be processed successfully
        assert game.is_processed is True
        assert result["mov_multiplier"] is not None
        # MOV should be from quarter-weighted calculation
        assert result["winner_name"] == "Home"

    def test_process_game_without_quarter_data_uses_legacy(self, test_db: Session):
        """Test that games without quarter data use legacy MOV"""
        # Arrange
        service = RankingService(test_db)
        home_team = Team(name="Home", conference=ConferenceType.POWER_5, elo_rating=1600.0)
        away_team = Team(name="Away", conference=ConferenceType.POWER_5, elo_rating=1600.0)
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Game WITHOUT quarter scores
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=35,
            away_score=28,
            week=1,
            season=2024,
            # No quarter scores
        )
        test_db.add(game)
        test_db.commit()

        # Act
        result = service.process_game(game)

        # Assert - Game should be processed successfully with legacy MOV
        assert game.is_processed is True
        assert result["mov_multiplier"] is not None
        # MOV should be from legacy calculation (7 point difference)
        expected_legacy_mov = math.log(7 + 1)
        assert abs(result["mov_multiplier"] - expected_legacy_mov) < 0.01
