"""
Ranking service that integrates ELO calculations with database
"""

import math
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import Team, Game, RankingHistory, Season, ConferenceType, Prediction
from datetime import datetime


class RankingService:
    """Service for calculating and managing ELO rankings"""

    # ELO Constants
    K_FACTOR = 32
    RATING_SCALE = 400
    HOME_FIELD_ADVANTAGE = 65
    MAX_MOV_MULTIPLIER = 2.5

    # EPIC-021: Garbage Time Configuration
    GARBAGE_TIME_THRESHOLD = 21  # Point differential entering Q4 that triggers reduced weighting
    GARBAGE_TIME_Q4_WEIGHT = 0.25  # Weight applied to Q4 in garbage time (25% of normal)

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

    def calculate_quarter_weighted_mov(self, game: Game, winner_is_home: bool) -> float:
        """
        Calculate margin of victory multiplier using quarter-by-quarter scores
        with garbage time adjustment (EPIC-021)

        Processes each quarter separately and applies reduced weight to 4th quarter
        scoring when the game enters garbage time (large differential after Q3).

        Args:
            game: Game object with quarter scores populated
            winner_is_home: True if home team won, False if away team won

        Returns:
            Weighted MOV multiplier (float, capped at MAX_MOV_MULTIPLIER)

        Algorithm:
            1. Calculate cumulative score differential after each quarter
            2. Detect garbage time: |differential after Q3| > GARBAGE_TIME_THRESHOLD
            3. Weight each quarter's contribution:
               - Q1, Q2, Q3: Full weight (1.0)
               - Q4: Full weight (1.0) in close games, reduced weight (0.25) in garbage time
            4. Combine quarters into overall MOV multiplier
        """
        # Ensure quarter data exists
        if any(q is None for q in [game.q1_home, game.q1_away, game.q2_home, game.q2_away,
                                     game.q3_home, game.q3_away, game.q4_home, game.q4_away]):
            # Fall back to legacy MOV if any quarter missing
            point_diff = abs(game.home_score - game.away_score)
            return self.calculate_mov_multiplier(point_diff)

        # Extract quarter scores (winner perspective)
        if winner_is_home:
            winner_quarters = [game.q1_home, game.q2_home, game.q3_home, game.q4_home]
            loser_quarters = [game.q1_away, game.q2_away, game.q3_away, game.q4_away]
        else:
            winner_quarters = [game.q1_away, game.q2_away, game.q3_away, game.q4_away]
            loser_quarters = [game.q1_home, game.q2_home, game.q3_home, game.q4_home]

        # Calculate cumulative differential after Q3 (before Q4)
        differential_after_q3 = sum(winner_quarters[:3]) - sum(loser_quarters[:3])

        # Detect garbage time
        is_garbage_time = abs(differential_after_q3) > self.GARBAGE_TIME_THRESHOLD

        # Calculate quarter-by-quarter MOV contributions
        quarter_movs = []
        for i in range(4):
            # Calculate differential for this quarter
            quarter_diff = winner_quarters[i] - loser_quarters[i]

            # Apply weight: reduced for Q4 in garbage time, full otherwise
            if i == 3 and is_garbage_time:
                weight = self.GARBAGE_TIME_Q4_WEIGHT
            else:
                weight = 1.0

            # Calculate MOV for this quarter (using log function like legacy)
            if quarter_diff > 0:
                quarter_mov = math.log(abs(quarter_diff) + 1) * weight
            else:
                # Quarter was even or loser outscored winner
                quarter_mov = 0.0

            quarter_movs.append(quarter_mov)

        # Combine quarters: average (treats each quarter equally)
        combined_mov = sum(quarter_movs) / 4.0

        # Cap at maximum
        return min(combined_mov, self.MAX_MOV_MULTIPLIER)

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

        Raises:
            ValueError: If game is invalid (no scores, already processed, excluded, etc.)
        """
        # EPIC-008 Story 003: Comprehensive validation

        # Validation: Ensure game has scores (not a future game)
        if game.home_score == 0 and game.away_score == 0:
            raise ValueError(
                f"Cannot process game {game.id} ({game.home_team.name if game.home_team else 'Unknown'} vs "
                f"{game.away_team.name if game.away_team else 'Unknown'}) - no scores available. "
                f"This is likely a future/scheduled game."
            )

        # Get teams
        home_team = game.home_team
        away_team = game.away_team

        # Validation: Ensure both teams exist
        if not home_team or not away_team:
            raise ValueError(
                f"Game {game.id} has invalid teams. "
                f"Home: {game.home_team_id}, Away: {game.away_team_id}"
            )

        # Validation: Ensure valid week and season
        if not (0 <= game.week <= 15):
            raise ValueError(f"Game {game.id} has invalid week: {game.week}")

        if not (2020 <= game.season <= 2030):
            raise ValueError(f"Game {game.id} has invalid season: {game.season}")

        # CRITICAL: Only process games included in rankings
        if game.excluded_from_rankings:
            raise ValueError("Cannot process excluded game for rankings")

        if game.is_processed:
            return {"error": "Game already processed"}

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
        # EPIC-021: Use quarter-weighted calculation if quarter data available
        if all([game.q1_home is not None, game.q1_away is not None,
                game.q2_home is not None, game.q2_away is not None,
                game.q3_home is not None, game.q3_away is not None,
                game.q4_home is not None, game.q4_away is not None]):
            # Quarter data available - use new algorithm
            mov_multiplier = self.calculate_quarter_weighted_mov(game, is_home_win)
        else:
            # No quarter data - use legacy algorithm
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

        # EPIC-009: Evaluate prediction accuracy if prediction exists
        evaluate_prediction_accuracy(self.db, game)

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

    def get_season_record(self, team_id: int, season: int) -> tuple[int, int]:
        """
        Calculate season-specific wins and losses for a team

        EPIC-024: Query games table for accurate season-specific records instead
        of using cumulative wins/losses from teams table.

        Args:
            team_id: Team ID
            season: Season year

        Returns:
            Tuple of (wins, losses) for the season
        """
        from models import Game

        # Count wins (games where team won and game is completed)
        wins = self.db.query(Game).filter(
            Game.season == season,
            Game.completed == True,
            ((Game.home_team_id == team_id) & (Game.home_score > Game.away_score)) |
            ((Game.away_team_id == team_id) & (Game.away_score > Game.home_score))
        ).count()

        # Count losses (games where team lost and game is completed)
        losses = self.db.query(Game).filter(
            Game.season == season,
            Game.completed == True,
            ((Game.home_team_id == team_id) & (Game.home_score < Game.away_score)) |
            ((Game.away_team_id == team_id) & (Game.away_score < Game.home_score))
        ).count()

        return wins, losses

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
        # CRITICAL: Only include games that count toward rankings
        games = self.db.query(Game).filter(
            ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)) &
            (Game.season == season) &
            (Game.is_processed == True) &
            (Game.excluded_from_rankings == False)
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

        EPIC-024: Now uses ranking_history for season-specific data instead of
        cumulative team records. This ensures each season's rankings are independent
        and historical seasons can be browsed accurately.

        Args:
            season: Season year
            limit: Optional limit on number of teams to return

        Returns:
            List of ranking dictionaries
        """
        # EPIC-024: Get current week for this season
        season_obj = self.db.query(Season).filter(Season.year == season).first()
        if not season_obj:
            # No season found - return empty rankings
            return []

        current_week = season_obj.current_week

        # EPIC-024: Query ranking_history instead of teams table for season-specific data
        query = self.db.query(RankingHistory).filter(
            RankingHistory.season == season,
            RankingHistory.week == current_week
        ).order_by(RankingHistory.elo_rating.desc())

        if limit:
            query = query.limit(limit)

        ranking_records = query.all()

        rankings = []
        for rank, record in enumerate(ranking_records, start=1):
            # Get team info (name, conference) from Team table
            team = record.team

            rankings.append({
                'rank': rank,
                'team_id': record.team_id,
                'team_name': team.name,
                'conference': team.conference,
                'conference_name': team.conference_name,  # EPIC-012: Add actual conference name
                'elo_rating': round(record.elo_rating, 2),  # EPIC-024: From ranking_history
                'wins': record.wins,  # EPIC-024: Season-specific wins from ranking_history
                'losses': record.losses,  # EPIC-024: Season-specific losses from ranking_history
                'sos': round(record.sos, 2),  # EPIC-024: Use saved SOS from ranking_history
                'sos_rank': record.sos_rank  # EPIC-024: Use saved SOS rank
            })

        return rankings

    def save_weekly_rankings(self, season: int, week: int) -> None:
        """
        Save current rankings to history

        EPIC-024 FIX: After refactoring get_current_rankings() to read from ranking_history,
        this method needs to build rankings from the teams table (current ELO state) instead
        of calling get_current_rankings() which would create circular logic.

        Args:
            season: Season year
            week: Week number
        """
        # Delete existing entries for this season/week to prevent duplicates
        # (handles case where weekly update runs multiple times)
        self.db.query(RankingHistory).filter(
            RankingHistory.season == season,
            RankingHistory.week == week
        ).delete()

        # Build rankings from current teams table state (not from ranking_history)
        teams = self.db.query(Team).order_by(Team.elo_rating.desc()).all()

        for rank, team in enumerate(teams, start=1):
            # Calculate season-specific wins/losses
            wins, losses = self.get_season_record(team.id, season)

            # Calculate SOS for this team
            sos = self.calculate_sos(team.id, season)

            history = RankingHistory(
                team_id=team.id,
                week=week,
                season=season,
                rank=rank,
                elo_rating=team.elo_rating,
                wins=wins,  # Season-specific wins
                losses=losses,  # Season-specific losses
                sos=sos,
                sos_rank=None  # Will be calculated after all teams are saved
            )
            self.db.add(history)

        self.db.commit()

        # Calculate and save SOS ranks
        rankings = self.db.query(RankingHistory).filter(
            RankingHistory.season == season,
            RankingHistory.week == week
        ).order_by(RankingHistory.sos.desc()).all()

        for sos_rank, ranking in enumerate(rankings, start=1):
            ranking.sos_rank = sos_rank

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


# Prediction Functions (standalone, not part of RankingService class)

def generate_predictions(
    db: Session,
    week: Optional[int] = None,
    team_id: Optional[int] = None,
    next_week: bool = True,
    season_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Generate predictions for upcoming (unprocessed) games.

    Args:
        db: Database session
        week: Optional specific week filter
        team_id: Optional team filter
        next_week: If True, only predict games in next week (default: True)
        season_year: Optional season year (defaults to current season)

    Returns:
        List of prediction dictionaries with winner, scores, and probabilities
    """
    # Determine season year
    if not season_year:
        season_year = datetime.now().year

    # Build query for unprocessed games
    query = db.query(Game).filter(
        Game.is_processed == False,
        Game.season == season_year
    )

    # Apply week filter
    if next_week:
        # Get current week from Season model
        current_week = db.query(Season.current_week).filter(
            Season.year == season_year
        ).scalar()

        if current_week is None:
            return []  # No active season

        query = query.filter(Game.week == current_week + 1)
    elif week is not None:
        query = query.filter(Game.week == week)

    # Apply team filter
    if team_id is not None:
        query = query.filter(
            or_(
                Game.home_team_id == team_id,
                Game.away_team_id == team_id
            )
        )

    # Execute query
    games = query.all()
    predictions = []

    for game in games:
        # Get team data
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

        # Validate teams exist and have valid ratings
        if not _validate_prediction_teams(home_team, away_team):
            continue

        # Generate prediction
        prediction = _calculate_game_prediction(game, home_team, away_team)
        predictions.append(prediction)

    return predictions


# Validation constants
MIN_VALID_RATING = 1  # Minimum valid ELO rating
MAX_PREDICTED_SCORE = 150  # Maximum reasonable score
MIN_PREDICTED_SCORE = 0  # Minimum score
MIN_WEEK = 0  # Preseason
MAX_WEEK = 15  # Postseason


def validate_week(week: int) -> bool:
    """
    Validate week number is within valid range.

    Args:
        week: Week number to validate

    Returns:
        True if valid, False otherwise
    """
    return MIN_WEEK <= week <= MAX_WEEK


def validate_team_for_prediction(team: Optional[Team]) -> bool:
    """
    Validate team exists and has valid rating for prediction.

    Args:
        team: Team object to validate

    Returns:
        True if valid, False otherwise
    """
    if team is None:
        return False

    if team.elo_rating < MIN_VALID_RATING:
        return False

    return True


def validate_predicted_score(score: int) -> int:
    """
    Ensure predicted score is within reasonable bounds.

    Args:
        score: Predicted score

    Returns:
        Clamped score within valid range [0, 150]
    """
    return max(MIN_PREDICTED_SCORE, min(score, MAX_PREDICTED_SCORE))


def validate_game_for_prediction(game: Game) -> bool:
    """
    Validate game can be predicted.

    Args:
        game: Game object to validate

    Returns:
        True if game is valid for prediction, False otherwise
    """
    # Only predict unprocessed games
    if game.is_processed:
        return False

    # Week must be valid
    if not validate_week(game.week):
        return False

    return True


def _validate_prediction_teams(home_team: Team, away_team: Team) -> bool:
    """Validate both teams exist and have valid ELO ratings."""
    if not home_team or not away_team:
        return False
    if home_team.elo_rating <= 0 or away_team.elo_rating <= 0:
        return False
    return True


def _calculate_game_prediction(game: Game, home_team: Team, away_team: Team) -> Dict[str, Any]:
    """
    Calculate prediction for a single game.

    Uses standard ELO formula for win probability and estimates scores
    based on rating difference.
    """
    # Apply home field advantage (unless neutral site)
    home_rating = home_team.elo_rating + (0 if game.is_neutral_site else 65)
    away_rating = away_team.elo_rating

    # Calculate win probability (standard ELO formula)
    rating_diff = home_rating - away_rating
    home_win_prob = 1 / (1 + 10 ** ((away_rating - home_rating) / 400))
    away_win_prob = 1 - home_win_prob

    # Estimate scores based on ELO difference
    # Base score: historical average (~30 points per team)
    base_score = 30

    # Adjust based on rating difference
    # Every 100 rating points ≈ 7 point margin, so 3.5 points per team
    score_adjustment = (rating_diff / 100) * 3.5

    predicted_home_score = round(base_score + score_adjustment)
    predicted_away_score = round(base_score - score_adjustment)

    # Ensure scores are reasonable (0-150 range)
    predicted_home_score = max(0, min(predicted_home_score, 150))
    predicted_away_score = max(0, min(predicted_away_score, 150))

    # Determine confidence level based on win probability margin
    prob_margin = abs(home_win_prob - 0.5)
    if prob_margin > 0.3:
        confidence = "High"
    elif prob_margin > 0.15:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "game_id": game.id,
        "home_team_id": home_team.id,
        "home_team": home_team.name,
        "away_team_id": away_team.id,
        "away_team": away_team.name,
        "week": game.week,
        "season": game.season,
        "game_date": game.game_date.isoformat() if game.game_date else None,
        "is_neutral_site": game.is_neutral_site,
        "predicted_winner": home_team.name if home_win_prob > 0.5 else away_team.name,
        "predicted_winner_id": home_team.id if home_win_prob > 0.5 else away_team.id,
        "predicted_home_score": predicted_home_score,
        "predicted_away_score": predicted_away_score,
        "home_win_probability": round(home_win_prob * 100, 1),
        "away_win_probability": round(away_win_prob * 100, 1),
        "confidence": confidence,
        "home_team_rating": home_team.elo_rating,
        "away_team_rating": away_team.elo_rating
    }


def create_and_store_prediction(db: Session, game: Game) -> Optional[Prediction]:
    """
    Create and store a prediction for a future game.

    Part of EPIC-009: Prediction Accuracy Tracking.
    This function generates a prediction using the current ELO ratings
    and stores it in the database for later accuracy evaluation.

    Args:
        db: Database session
        game: Game object to predict (must be unprocessed/future game)

    Returns:
        Prediction object if successful, None if prediction cannot be created

    Example:
        >>> prediction = create_and_store_prediction(db, future_game)
        >>> print(f"Predicted {prediction.predicted_winner.name} to win")
    """
    # Validate game is future/unprocessed
    if game.is_processed:
        return None

    # Check if prediction already exists
    existing = db.query(Prediction).filter(Prediction.game_id == game.id).first()
    if existing:
        return existing  # Don't create duplicate

    # Get teams
    home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
    away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

    # Validate teams
    if not _validate_prediction_teams(home_team, away_team):
        return None

    # Generate prediction data
    prediction_data = _calculate_game_prediction(game, home_team, away_team)

    # Create Prediction object
    prediction = Prediction(
        game_id=game.id,
        predicted_winner_id=prediction_data['predicted_winner_id'],
        predicted_home_score=prediction_data['predicted_home_score'],
        predicted_away_score=prediction_data['predicted_away_score'],
        win_probability=prediction_data['home_win_probability'] / 100.0 if prediction_data['predicted_winner_id'] == home_team.id else prediction_data['away_win_probability'] / 100.0,
        home_elo_at_prediction=home_team.elo_rating,
        away_elo_at_prediction=away_team.elo_rating,
        was_correct=None  # Will be set when game completes
    )

    # Store in database
    try:
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction
    except Exception as e:
        db.rollback()
        print(f"Error storing prediction for game {game.id}: {e}")
        return None


def evaluate_prediction_accuracy(db: Session, game: Game) -> Optional[Prediction]:
    """
    Evaluate prediction accuracy for a completed game.

    Part of EPIC-009: Prediction Accuracy Tracking.
    This function checks if a prediction exists for the completed game
    and updates the was_correct flag based on actual game outcome.

    Args:
        db: Database session
        game: Completed game object

    Returns:
        Updated Prediction object if exists, None otherwise

    Example:
        >>> evaluate_prediction_accuracy(db, completed_game)
        >>> prediction.was_correct  # True or False
    """
    # Check if prediction exists for this game
    prediction = db.query(Prediction).filter(Prediction.game_id == game.id).first()

    if not prediction:
        return None  # No prediction to evaluate

    # Validate game is completed
    if not game.is_processed:
        return None  # Game not yet complete

    # Determine actual winner
    actual_winner_id = game.winner_id

    # Compare predicted winner to actual winner
    prediction.was_correct = (prediction.predicted_winner_id == actual_winner_id)

    # No need to commit here - will be committed by caller (process_game)
    return prediction


def get_overall_prediction_accuracy(db: Session, season: Optional[int] = None) -> Dict[str, Any]:
    """
    Get overall prediction accuracy statistics.

    Part of EPIC-009: Prediction Accuracy Tracking.

    Args:
        db: Database session
        season: Optional season filter

    Returns:
        Dictionary with accuracy statistics

    Example:
        >>> stats = get_overall_prediction_accuracy(db, season=2024)
        >>> print(f"Accuracy: {stats['accuracy_percentage']:.1f}%")
    """
    from sqlalchemy import func

    # Build base query
    query = db.query(Prediction)

    # Filter by season if provided
    if season:
        query = query.join(Game).filter(Game.season == season)

    # Total predictions
    total_predictions = query.count()

    # Evaluated predictions (where was_correct is not None)
    evaluated_predictions = query.filter(Prediction.was_correct.isnot(None)).count()

    # Correct predictions
    correct_predictions = query.filter(Prediction.was_correct == True).count()

    # Calculate accuracy
    accuracy_percentage = (correct_predictions / evaluated_predictions * 100) if evaluated_predictions > 0 else 0.0

    return {
        "total_predictions": total_predictions,
        "evaluated_predictions": evaluated_predictions,
        "correct_predictions": correct_predictions,
        "accuracy_percentage": round(accuracy_percentage, 2),
        "high_confidence_accuracy": None,  # TODO: Implement confidence-based accuracy
        "medium_confidence_accuracy": None,
        "low_confidence_accuracy": None
    }


def get_team_prediction_accuracy(db: Session, team_id: int, season: Optional[int] = None) -> Dict[str, Any]:
    """
    Get prediction accuracy for a specific team.

    Part of EPIC-009: Prediction Accuracy Tracking.

    Args:
        db: Database session
        team_id: Team ID
        season: Optional season filter

    Returns:
        Dictionary with team-specific accuracy statistics

    Example:
        >>> stats = get_team_prediction_accuracy(db, team_id=15, season=2024)
        >>> print(f"Team accuracy: {stats['accuracy_percentage']:.1f}%")
    """
    from sqlalchemy import or_

    # Get team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {
            "team_id": team_id,
            "team_name": "Unknown",
            "total_predictions": 0,
            "evaluated_predictions": 0,
            "correct_predictions": 0,
            "accuracy_percentage": 0.0,
            "as_favorite_accuracy": None,
            "as_underdog_accuracy": None
        }

    # Build query for predictions involving this team
    query = db.query(Prediction).join(Game).filter(
        or_(
            Game.home_team_id == team_id,
            Game.away_team_id == team_id
        )
    )

    # Filter by season if provided
    if season:
        query = query.filter(Game.season == season)

    # Get all predictions
    predictions = query.all()

    total_predictions = len(predictions)
    evaluated_predictions = sum(1 for p in predictions if p.was_correct is not None)
    correct_predictions = sum(1 for p in predictions if p.was_correct is True)

    # Calculate accuracy
    accuracy_percentage = (correct_predictions / evaluated_predictions * 100) if evaluated_predictions > 0 else 0.0

    # Calculate as favorite/underdog accuracy
    as_favorite = [p for p in predictions if p.predicted_winner_id == team_id and p.was_correct is not None]
    as_underdog = [p for p in predictions if p.predicted_winner_id != team_id and p.was_correct is not None]

    as_favorite_correct = sum(1 for p in as_favorite if p.was_correct is True)
    # For underdogs: was_correct = True means prediction was correct (team lost as predicted)
    as_underdog_correct = sum(1 for p in as_underdog if p.was_correct is True)

    as_favorite_accuracy = (as_favorite_correct / len(as_favorite) * 100) if as_favorite else None
    as_underdog_accuracy = (as_underdog_correct / len(as_underdog) * 100) if as_underdog else None

    return {
        "team_id": team_id,
        "team_name": team.name,
        "total_predictions": total_predictions,
        "evaluated_predictions": evaluated_predictions,
        "correct_predictions": correct_predictions,
        "accuracy_percentage": round(accuracy_percentage, 2),
        "as_favorite_accuracy": round(as_favorite_accuracy, 2) if as_favorite_accuracy is not None else None,
        "as_underdog_accuracy": round(as_underdog_accuracy, 2) if as_underdog_accuracy is not None else None
    }
