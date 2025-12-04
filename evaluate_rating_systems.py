"""
Evaluate different rating systems by backtesting against actual game results

Compares:
1. Current system (K=32, no decay)
2. Progressive K-factor (K=48→40→32)
3. Preseason decay (preseason influence fades over time)

Metrics:
- Prediction accuracy (% correct winners)
- Brier score (lower is better, measures probability calibration)
- Log loss (lower is better, penalizes confident wrong predictions)
- Mean prediction confidence (how confident were predictions)
"""

import sys
from database import SessionLocal
from models import Team, Game, Season, ConferenceType
from typing import Dict, List, Tuple
import math
from copy import deepcopy


class RatingSystem:
    """Base class for rating systems"""

    def __init__(self, name: str):
        self.name = name
        self.teams = {}  # team_id -> current_rating
        self.initial_ratings = {}  # team_id -> preseason_rating
        self.predictions = []  # List of (predicted_prob, actual_result)

    def initialize_teams(self, teams: List[Team]):
        """Set up initial ratings"""
        for team in teams:
            self.teams[team.id] = team.initial_rating
            self.initial_ratings[team.id] = team.initial_rating

    def get_rating(self, team_id: int, week: int) -> float:
        """Get effective rating for a team (may apply decay)"""
        return self.teams[team_id]

    def get_k_factor(self, week: int) -> float:
        """Get K-factor for this week (default: 32)"""
        return 32.0

    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score using ELO formula"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def predict_game(self, game: Game, week: int) -> Tuple[float, bool]:
        """
        Predict game outcome and record prediction

        Returns:
            (home_win_prob, home_won)
        """
        home_rating = self.get_rating(game.home_team_id, week)
        away_rating = self.get_rating(game.away_team_id, week)

        # Add home field advantage
        home_rating_adj = home_rating + 65

        # Calculate win probability
        home_win_prob = self.calculate_expected_score(home_rating_adj, away_rating)

        # Actual result
        home_won = game.home_score > game.away_score

        # Record prediction
        self.predictions.append((home_win_prob, 1.0 if home_won else 0.0))

        return home_win_prob, home_won

    def process_game(self, game: Game, week: int, home_conf: ConferenceType, away_conf: ConferenceType):
        """Process game and update ratings"""
        home_rating = self.get_rating(game.home_team_id, week)
        away_rating = self.get_rating(game.away_team_id, week)

        # Home field advantage
        home_rating_adj = home_rating + 65

        # Expected scores
        home_expected = self.calculate_expected_score(home_rating_adj, away_rating)
        away_expected = 1 - home_expected

        # Actual scores (1 or 0)
        home_actual = 1 if game.home_score > game.away_score else 0
        away_actual = 1 - home_actual

        # Margin of victory multiplier (simplified - not using quarter weights)
        score_diff = abs(game.home_score - game.away_score)
        mov_multiplier = math.log(max(score_diff, 1) + 1) / math.log(22)
        mov_multiplier = min(mov_multiplier, 2.0)

        # Conference multipliers
        home_mult, away_mult = self.get_conference_multipliers(
            home_conf, away_conf, home_actual == 1
        )

        # K-factor for this week
        k = self.get_k_factor(week)

        # Rating changes
        home_change = k * mov_multiplier * home_mult * (home_actual - home_expected)
        away_change = k * mov_multiplier * away_mult * (away_actual - away_expected)

        # Update ratings
        self.teams[game.home_team_id] += home_change
        self.teams[game.away_team_id] += away_change

    def get_conference_multipliers(self, home_conf: ConferenceType, away_conf: ConferenceType,
                                   home_won: bool) -> Tuple[float, float]:
        """Get conference multipliers"""
        home_p5 = home_conf == ConferenceType.POWER_5
        away_p5 = away_conf == ConferenceType.POWER_5

        if home_p5 and away_p5:
            return (1.0, 1.0)
        elif home_p5 and not away_p5:
            return (0.8, 1.2)
        elif not home_p5 and away_p5:
            if not home_won:  # G5 won
                return (1.5, 0.8)
            else:  # P5 won
                return (1.2, 0.8)
        else:  # Both G5
            return (1.0, 1.0)

    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate prediction accuracy metrics"""
        if not self.predictions:
            return {}

        n = len(self.predictions)
        correct = 0
        brier_sum = 0.0
        log_loss_sum = 0.0
        conf_sum = 0.0

        for pred_prob, actual in self.predictions:
            # Prediction accuracy (pick team with >50% probability)
            predicted_home_win = pred_prob > 0.5
            actual_home_win = actual == 1.0
            if predicted_home_win == actual_home_win:
                correct += 1

            # Brier score: (predicted_prob - actual)^2
            brier_sum += (pred_prob - actual) ** 2

            # Log loss: -log(correct_probability)
            # Clamp probabilities to avoid log(0)
            prob = max(0.001, min(0.999, pred_prob if actual == 1.0 else 1 - pred_prob))
            log_loss_sum += -math.log(prob)

            # Average confidence (distance from 50%)
            conf_sum += abs(pred_prob - 0.5)

        return {
            'accuracy': correct / n,
            'brier_score': brier_sum / n,
            'log_loss': log_loss_sum / n,
            'mean_confidence': conf_sum / n,
            'n_games': n
        }


class CurrentSystem(RatingSystem):
    """Current system: K=32, no decay"""

    def __init__(self):
        super().__init__("Current (K=32)")


class ProgressiveKSystem(RatingSystem):
    """Progressive K-factor: 48→40→32"""

    def __init__(self):
        super().__init__("Progressive K-factor")

    def get_k_factor(self, week: int) -> float:
        if week <= 4:
            return 48.0
        elif week <= 8:
            return 40.0
        else:
            return 32.0


class PreseasonDecaySystem(RatingSystem):
    """Preseason rating influence decays over season"""

    def __init__(self):
        super().__init__("Preseason Decay")
        self.rating_changes = {}  # team_id -> cumulative rating change

    def initialize_teams(self, teams: List[Team]):
        super().initialize_teams(teams)
        for team in teams:
            self.rating_changes[team.id] = 0.0

    def get_rating(self, team_id: int, week: int) -> float:
        """Apply decay to preseason rating advantage"""
        # Calculate decay factor (linear decay to 0 by week 15)
        decay_factor = max(0.0, 1.0 - (week / 15.0))

        # Preseason rating and performance rating
        initial = self.initial_ratings[team_id]
        performance = 1500 + self.rating_changes[team_id]

        # Blend based on decay factor
        effective_rating = (decay_factor * initial) + ((1 - decay_factor) * performance)

        return effective_rating

    def process_game(self, game: Game, week: int, home_conf: ConferenceType, away_conf: ConferenceType):
        """Process game and track rating changes separately"""
        # Get ratings before change
        home_rating_before = self.get_rating(game.home_team_id, week)
        away_rating_before = self.get_rating(game.away_team_id, week)

        # Calculate rating changes (same as parent)
        home_rating_adj = home_rating_before + 65
        home_expected = self.calculate_expected_score(home_rating_adj, away_rating_before)
        away_expected = 1 - home_expected

        home_actual = 1 if game.home_score > game.away_score else 0
        away_actual = 1 - home_actual

        score_diff = abs(game.home_score - game.away_score)
        mov_multiplier = math.log(max(score_diff, 1) + 1) / math.log(22)
        mov_multiplier = min(mov_multiplier, 2.0)

        home_mult, away_mult = self.get_conference_multipliers(
            home_conf, away_conf, home_actual == 1
        )

        k = self.get_k_factor(week)

        home_change = k * mov_multiplier * home_mult * (home_actual - home_expected)
        away_change = k * mov_multiplier * away_mult * (away_actual - away_expected)

        # Track cumulative changes from 1500 baseline
        self.rating_changes[game.home_team_id] += home_change
        self.rating_changes[game.away_team_id] += away_change

        # Update actual ratings (for display purposes)
        self.teams[game.home_team_id] = self.get_rating(game.home_team_id, week + 1)
        self.teams[game.away_team_id] = self.get_rating(game.away_team_id, week + 1)


def evaluate_systems(season_year: int = 2025):
    """Evaluate all rating systems against actual game results"""

    db = SessionLocal()

    try:
        print("=" * 80)
        print(f"RATING SYSTEM EVALUATION - {season_year} Season")
        print("=" * 80)
        print()

        # Get all teams
        teams = db.query(Team).all()
        print(f"Loaded {len(teams)} teams")

        # Get all processed games in chronological order
        games = db.query(Game).filter(
            Game.season == season_year,
            Game.is_processed == True
        ).order_by(Game.week, Game.id).all()
        print(f"Loaded {len(games)} processed games")
        print()

        # Create team lookup for conference info
        team_lookup = {t.id: t for t in teams}

        # Initialize all systems
        systems = [
            CurrentSystem(),
            ProgressiveKSystem(),
            PreseasonDecaySystem()
        ]

        for system in systems:
            system.initialize_teams(teams)

        # Process each game with all systems
        print("Processing games...")
        for i, game in enumerate(games):
            week = game.week

            # Get conference info
            home_team = team_lookup[game.home_team_id]
            away_team = team_lookup[game.away_team_id]

            for system in systems:
                # Predict game
                system.predict_game(game, week)

                # Update ratings
                system.process_game(game, week, home_team.conference, away_team.conference)

            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(games)} games...")

        print(f"✓ Processed all {len(games)} games")
        print()

        # Calculate and display metrics
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()

        results = []
        for system in systems:
            metrics = system.calculate_metrics()
            results.append((system.name, metrics))

            print(f"{system.name}")
            print("-" * 40)
            print(f"  Prediction Accuracy: {metrics['accuracy']:.1%}")
            print(f"  Brier Score:         {metrics['brier_score']:.4f} (lower is better)")
            print(f"  Log Loss:            {metrics['log_loss']:.4f} (lower is better)")
            print(f"  Mean Confidence:     {metrics['mean_confidence']:.1%}")
            print(f"  Games Evaluated:     {metrics['n_games']}")
            print()

        # Determine winner
        print("=" * 80)
        print("WINNER")
        print("=" * 80)
        print()

        best_accuracy = max(results, key=lambda x: x[1]['accuracy'])
        best_brier = min(results, key=lambda x: x[1]['brier_score'])
        best_log_loss = min(results, key=lambda x: x[1]['log_loss'])

        print(f"Best Accuracy:    {best_accuracy[0]} ({best_accuracy[1]['accuracy']:.2%})")
        print(f"Best Brier Score: {best_brier[0]} ({best_brier[1]['brier_score']:.4f})")
        print(f"Best Log Loss:    {best_log_loss[0]} ({best_log_loss[1]['log_loss']:.4f})")
        print()

        # Overall recommendation
        scores = {}
        for name, metrics in results:
            # Simple scoring: 3 points for best in category, 2 for second, 1 for third
            scores[name] = 0

        for metric in ['accuracy', 'brier_score', 'log_loss']:
            if metric == 'accuracy':
                sorted_systems = sorted(results, key=lambda x: x[1][metric], reverse=True)
            else:
                sorted_systems = sorted(results, key=lambda x: x[1][metric])

            for i, (name, _) in enumerate(sorted_systems):
                scores[name] += (3 - i)

        best_overall = max(scores.items(), key=lambda x: x[1])
        print(f"Overall Best System: {best_overall[0]} ({best_overall[1]} points)")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate rating systems")
    parser.add_argument("--season", type=int, default=2025, help="Season year to evaluate")

    args = parser.parse_args()

    evaluate_systems(args.season)
