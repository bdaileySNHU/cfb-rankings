"""
College Football ELO Ranking System Prototype
Modified ELO with recruiting, transfers, and returning production
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


class Conference(Enum):
    """Conference classifications for multiplier calculations"""
    POWER_5 = "P5"
    GROUP_5 = "G5"
    FCS = "FCS"


@dataclass
class Team:
    """Represents a college football team"""
    name: str
    conference: Conference
    recruiting_rank: int = 999  # 247Sports composite rank
    transfer_rank: int = 999    # 247Sports transfer portal rank
    returning_production: float = 0.5  # Percentage (0.0 to 1.0)
    elo_rating: float = 1500.0
    wins: int = 0
    losses: int = 0
    games_played: List[str] = None  # List of opponent names

    def __post_init__(self):
        if self.games_played is None:
            self.games_played = []
        # Calculate initial preseason rating
        self.elo_rating = self._calculate_preseason_rating()

    def _calculate_preseason_rating(self) -> float:
        """Calculate preseason ELO rating based on recruiting, transfers, and returning production"""
        # Base rating
        if self.conference == Conference.FCS:
            base = 1300.0
        else:
            base = 1500.0

        # Recruiting bonus
        recruiting_bonus = 0.0
        if self.recruiting_rank <= 5:
            recruiting_bonus = 200.0
        elif self.recruiting_rank <= 10:
            recruiting_bonus = 150.0
        elif self.recruiting_rank <= 25:
            recruiting_bonus = 100.0
        elif self.recruiting_rank <= 50:
            recruiting_bonus = 50.0
        elif self.recruiting_rank <= 75:
            recruiting_bonus = 25.0

        # Transfer portal bonus (half weight of recruiting)
        transfer_bonus = 0.0
        if self.transfer_rank <= 5:
            transfer_bonus = 100.0
        elif self.transfer_rank <= 10:
            transfer_bonus = 75.0
        elif self.transfer_rank <= 25:
            transfer_bonus = 50.0
        elif self.transfer_rank <= 50:
            transfer_bonus = 25.0

        # Returning production bonus
        returning_bonus = 0.0
        if self.returning_production >= 0.80:
            returning_bonus = 40.0
        elif self.returning_production >= 0.60:
            returning_bonus = 25.0
        elif self.returning_production >= 0.40:
            returning_bonus = 10.0

        return base + recruiting_bonus + transfer_bonus + returning_bonus

    def get_record(self) -> str:
        """Return win-loss record as string"""
        return f"{self.wins}-{self.losses}"


class ELORankingSystem:
    """Modified ELO ranking system for college football"""

    # Constants
    K_FACTOR = 32
    RATING_SCALE = 400
    HOME_FIELD_ADVANTAGE = 65
    MAX_MOV_MULTIPLIER = 2.5

    def __init__(self):
        self.teams: Dict[str, Team] = {}

    def add_team(self, team: Team) -> None:
        """Add a team to the ranking system"""
        self.teams[team.name] = team

    def calculate_expected_score(self, team_a_rating: float, team_b_rating: float) -> float:
        """
        Calculate expected win probability for team A

        Args:
            team_a_rating: ELO rating of team A
            team_b_rating: ELO rating of team B

        Returns:
            Expected probability (0.0 to 1.0) that team A wins
        """
        exponent = (team_b_rating - team_a_rating) / self.RATING_SCALE
        return 1.0 / (1.0 + math.pow(10, exponent))

    def calculate_mov_multiplier(self, point_differential: int) -> float:
        """
        Calculate margin of victory multiplier

        Args:
            point_differential: Absolute point difference

        Returns:
            Multiplier capped at MAX_MOV_MULTIPLIER
        """
        if point_differential <= 0:
            return 1.0

        multiplier = math.log(abs(point_differential) + 1)
        return min(multiplier, self.MAX_MOV_MULTIPLIER)

    def get_conference_multiplier(self, winner_conf: Conference, loser_conf: Conference) -> Tuple[float, float]:
        """
        Get rating change multipliers based on conference matchup

        Args:
            winner_conf: Conference of winning team
            loser_conf: Conference of losing team

        Returns:
            Tuple of (winner_multiplier, loser_multiplier)
        """
        # FBS vs FCS
        if winner_conf != Conference.FCS and loser_conf == Conference.FCS:
            return (0.5, 2.0)  # FBS gains half, FCS loses double
        elif winner_conf == Conference.FCS and loser_conf != Conference.FCS:
            return (2.0, 0.5)  # FCS gains double, FBS loses half

        # P5 vs G5
        if winner_conf == Conference.POWER_5 and loser_conf == Conference.GROUP_5:
            return (0.9, 1.1)  # P5 gains 10% less
        elif winner_conf == Conference.GROUP_5 and loser_conf == Conference.POWER_5:
            return (1.1, 0.9)  # G5 gains 10% more for upset

        # Same tier matchups
        return (1.0, 1.0)

    def process_game(self,
                     winner_name: str,
                     loser_name: str,
                     winner_score: int,
                     loser_score: int,
                     is_home_game_for_winner: bool = False,
                     is_neutral_site: bool = False) -> Dict[str, float]:
        """
        Process a game result and update ELO ratings

        Args:
            winner_name: Name of winning team
            loser_name: Name of losing team
            winner_score: Points scored by winner
            loser_score: Points scored by loser
            is_home_game_for_winner: True if winner played at home
            is_neutral_site: True if neutral site game

        Returns:
            Dictionary with rating changes and details
        """
        winner = self.teams[winner_name]
        loser = self.teams[loser_name]

        # Apply home field advantage to ratings for calculation
        winner_rating = winner.elo_rating
        loser_rating = loser.elo_rating

        if not is_neutral_site:
            if is_home_game_for_winner:
                winner_rating += self.HOME_FIELD_ADVANTAGE
            else:
                loser_rating += self.HOME_FIELD_ADVANTAGE

        # Calculate expected outcomes
        winner_expected = self.calculate_expected_score(winner_rating, loser_rating)
        loser_expected = 1.0 - winner_expected

        # Calculate margin of victory multiplier
        point_diff = abs(winner_score - loser_score)
        mov_multiplier = self.calculate_mov_multiplier(point_diff)

        # Get conference multipliers
        winner_conf_mult, loser_conf_mult = self.get_conference_multiplier(
            winner.conference, loser.conference
        )

        # Calculate rating changes
        winner_change = self.K_FACTOR * (1.0 - winner_expected) * mov_multiplier * winner_conf_mult
        loser_change = self.K_FACTOR * (0.0 - loser_expected) * mov_multiplier * loser_conf_mult

        # Update ratings
        winner.elo_rating += winner_change
        loser.elo_rating += loser_change

        # Update records
        winner.wins += 1
        loser.losses += 1

        # Track opponents for SOS calculation
        winner.games_played.append(loser_name)
        loser.games_played.append(winner_name)

        return {
            'winner': winner_name,
            'loser': loser_name,
            'score': f"{winner_score}-{loser_score}",
            'winner_rating_change': round(winner_change, 2),
            'loser_rating_change': round(loser_change, 2),
            'winner_new_rating': round(winner.elo_rating, 2),
            'loser_new_rating': round(loser.elo_rating, 2),
            'winner_expected': round(winner_expected, 3),
            'mov_multiplier': round(mov_multiplier, 2)
        }

    def calculate_sos(self, team_name: str) -> float:
        """
        Calculate strength of schedule as average opponent ELO rating

        Args:
            team_name: Name of team

        Returns:
            Average ELO rating of opponents
        """
        team = self.teams[team_name]

        if not team.games_played:
            return 0.0

        total_rating = sum(self.teams[opp].elo_rating for opp in team.games_played)
        return total_rating / len(team.games_played)

    def get_rankings(self) -> List[Tuple[int, Team, float]]:
        """
        Get current rankings sorted by ELO rating

        Returns:
            List of tuples (rank, Team, SOS)
        """
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: t.elo_rating,
            reverse=True
        )

        rankings = []
        for rank, team in enumerate(sorted_teams, start=1):
            sos = self.calculate_sos(team.name)
            rankings.append((rank, team, sos))

        return rankings

    def print_rankings(self, top_n: int = 25) -> None:
        """Print top N rankings in formatted table"""
        rankings = self.get_rankings()

        print("\n" + "="*100)
        print(f"{'RANK':<6} {'TEAM':<25} {'RATING':<10} {'RECORD':<10} {'CONF':<6} {'SOS':<10}")
        print("="*100)

        for rank, team, sos in rankings[:top_n]:
            print(f"{rank:<6} {team.name:<25} {team.elo_rating:<10.2f} {team.get_record():<10} "
                  f"{team.conference.value:<6} {sos:<10.2f}")

        print("="*100 + "\n")
