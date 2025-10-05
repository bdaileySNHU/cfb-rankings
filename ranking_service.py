"""
Ranking service that integrates ELO calculations with database
"""

import math
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from models import Team, Game, RankingHistory, Season, ConferenceType


class RankingService:
    """Service for calculating and managing ELO rankings"""

    # ELO Constants
    K_FACTOR = 32
    RATING_SCALE = 400
    HOME_FIELD_ADVANTAGE = 65
    MAX_MOV_MULTIPLIER = 2.5

    def __init__(self, db: Session):
        self.db = db

    def calculate_preseason_rating(self, team: Team) -> float:
        """
        Calculate preseason ELO rating based on recruiting, transfers, and returning production

        Args:
            team: Team object with preseason data

        Returns:
            Calculated preseason rating
        """
        # Base rating
        if team.conference == ConferenceType.FCS:
            base = 1300.0
        else:
            base = 1500.0

        # Recruiting bonus
        recruiting_bonus = 0.0
        if team.recruiting_rank <= 5:
            recruiting_bonus = 200.0
        elif team.recruiting_rank <= 10:
            recruiting_bonus = 150.0
        elif team.recruiting_rank <= 25:
            recruiting_bonus = 100.0
        elif team.recruiting_rank <= 50:
            recruiting_bonus = 50.0
        elif team.recruiting_rank <= 75:
            recruiting_bonus = 25.0

        # Transfer portal bonus (half weight of recruiting)
        transfer_bonus = 0.0
        if team.transfer_rank <= 5:
            transfer_bonus = 100.0
        elif team.transfer_rank <= 10:
            transfer_bonus = 75.0
        elif team.transfer_rank <= 25:
            transfer_bonus = 50.0
        elif team.transfer_rank <= 50:
            transfer_bonus = 25.0

        # Returning production bonus
        returning_bonus = 0.0
        if team.returning_production >= 0.80:
            returning_bonus = 40.0
        elif team.returning_production >= 0.60:
            returning_bonus = 25.0
        elif team.returning_production >= 0.40:
            returning_bonus = 10.0

        return base + recruiting_bonus + transfer_bonus + returning_bonus

    def initialize_team_rating(self, team: Team) -> None:
        """
        Initialize a team's ELO rating based on preseason factors

        Args:
            team: Team to initialize
        """
        rating = self.calculate_preseason_rating(team)
        team.elo_rating = rating
        team.initial_rating = rating
        self.db.commit()

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

    def get_conference_multiplier(self, winner_conf: ConferenceType,
                                  loser_conf: ConferenceType) -> Tuple[float, float]:
        """
        Get rating change multipliers based on conference matchup

        Args:
            winner_conf: Conference of winning team
            loser_conf: Conference of losing team

        Returns:
            Tuple of (winner_multiplier, loser_multiplier)
        """
        # FBS vs FCS
        if winner_conf != ConferenceType.FCS and loser_conf == ConferenceType.FCS:
            return (0.5, 2.0)  # FBS gains half, FCS loses double
        elif winner_conf == ConferenceType.FCS and loser_conf != ConferenceType.FCS:
            return (2.0, 0.5)  # FCS gains double, FBS loses half

        # P5 vs G5
        if winner_conf == ConferenceType.POWER_5 and loser_conf == ConferenceType.GROUP_5:
            return (0.9, 1.1)  # P5 gains 10% less
        elif winner_conf == ConferenceType.GROUP_5 and loser_conf == ConferenceType.POWER_5:
            return (1.1, 0.9)  # G5 gains 10% more for upset

        # Same tier matchups
        return (1.0, 1.0)

    def process_game(self, game: Game) -> dict:
        """
        Process a game and update team ELO ratings

        Args:
            game: Game object to process

        Returns:
            Dictionary with game result details
        """
        if game.is_processed:
            return {"error": "Game already processed"}

        # Get teams
        home_team = game.home_team
        away_team = game.away_team

        # Determine winner and loser
        if game.home_score > game.away_score:
            winner = home_team
            loser = away_team
            winner_score = game.home_score
            loser_score = game.away_score
            is_home_win = True
        else:
            winner = away_team
            loser = home_team
            winner_score = game.away_score
            loser_score = game.home_score
            is_home_win = False

        # Apply home field advantage for calculation
        home_rating = home_team.elo_rating
        away_rating = away_team.elo_rating

        if not game.is_neutral_site:
            home_rating += self.HOME_FIELD_ADVANTAGE

        # Calculate expected outcomes (from winner's perspective)
        if is_home_win:
            winner_expected = self.calculate_expected_score(home_rating, away_rating)
        else:
            winner_expected = self.calculate_expected_score(away_rating, home_rating)

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

        # Store rating changes in game
        if is_home_win:
            game.home_rating_change = winner_change
            game.away_rating_change = loser_change
        else:
            game.home_rating_change = loser_change
            game.away_rating_change = winner_change

        # Mark game as processed
        game.is_processed = True

        # Commit changes
        self.db.commit()

        return {
            'game_id': game.id,
            'winner_name': winner.name,
            'loser_name': loser.name,
            'score': f"{winner_score}-{loser_score}",
            'winner_rating_change': round(winner_change, 2),
            'loser_rating_change': round(loser_change, 2),
            'winner_new_rating': round(winner.elo_rating, 2),
            'loser_new_rating': round(loser.elo_rating, 2),
            'winner_expected_probability': round(winner_expected, 3),
            'mov_multiplier': round(mov_multiplier, 2)
        }

    def calculate_sos(self, team_id: int, season: int) -> float:
        """
        Calculate strength of schedule as average opponent ELO rating

        Args:
            team_id: ID of team
            season: Season year

        Returns:
            Average ELO rating of opponents
        """
        # Get all games for this team in this season
        games = self.db.query(Game).filter(
            ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)) &
            (Game.season == season) &
            (Game.is_processed == True)
        ).all()

        if not games:
            return 0.0

        total_rating = 0.0
        count = 0

        for game in games:
            # Get opponent
            if game.home_team_id == team_id:
                opponent = game.away_team
            else:
                opponent = game.home_team

            total_rating += opponent.elo_rating
            count += 1

        return total_rating / count if count > 0 else 0.0

    def get_current_rankings(self, season: int, limit: Optional[int] = None) -> List[dict]:
        """
        Get current rankings sorted by ELO rating

        Args:
            season: Season year
            limit: Optional limit on number of teams to return

        Returns:
            List of ranking dictionaries
        """
        # Get all teams sorted by ELO rating
        query = self.db.query(Team).order_by(Team.elo_rating.desc())

        if limit:
            query = query.limit(limit)

        teams = query.all()

        rankings = []
        for rank, team in enumerate(teams, start=1):
            sos = self.calculate_sos(team.id, season)

            rankings.append({
                'rank': rank,
                'team_id': team.id,
                'team_name': team.name,
                'conference': team.conference,
                'elo_rating': round(team.elo_rating, 2),
                'wins': team.wins,
                'losses': team.losses,
                'sos': round(sos, 2),
                'sos_rank': None  # Will calculate after all SOS values are known
            })

        # Calculate SOS ranks
        sos_sorted = sorted(rankings, key=lambda x: x['sos'], reverse=True)
        for sos_rank, entry in enumerate(sos_sorted, start=1):
            # Find the entry in original rankings and update SOS rank
            for ranking in rankings:
                if ranking['team_id'] == entry['team_id']:
                    ranking['sos_rank'] = sos_rank
                    break

        return rankings

    def save_weekly_rankings(self, season: int, week: int) -> None:
        """
        Save current rankings to history

        Args:
            season: Season year
            week: Week number
        """
        rankings = self.get_current_rankings(season)

        for ranking in rankings:
            history = RankingHistory(
                team_id=ranking['team_id'],
                week=week,
                season=season,
                rank=ranking['rank'],
                elo_rating=ranking['elo_rating'],
                wins=ranking['wins'],
                losses=ranking['losses'],
                sos=ranking['sos'],
                sos_rank=ranking['sos_rank']
            )
            self.db.add(history)

        self.db.commit()

    def reset_season(self, season_year: int) -> None:
        """
        Reset all teams for a new season

        Args:
            season_year: Year of the season to reset
        """
        teams = self.db.query(Team).all()

        for team in teams:
            # Recalculate preseason rating
            team.elo_rating = self.calculate_preseason_rating(team)
            team.initial_rating = team.elo_rating
            team.wins = 0
            team.losses = 0

        self.db.commit()
