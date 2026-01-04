"""
AP Poll Comparison Service

Handles AP Poll prediction logic and comparison with ELO predictions.
Part of EPIC-010: AP Poll Prediction Comparison.
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.models import APPollRanking, Game, Prediction, Team


def get_team_ap_rank(db: Session, team_id: int, season: int, week: int) -> Optional[int]:
    """
    Get team's AP Poll rank for a specific week.

    Args:
        db: Database session
        team_id: Team ID
        season: Season year
        week: Week number

    Returns:
        int: Team's AP rank (1-25), or None if unranked

    Example:
        >>> rank = get_team_ap_rank(db, 82, 2024, 5)
        >>> print(rank)  # 1 (if Ohio State is ranked #1 in week 5)
    """
    ranking = (
        db.query(APPollRanking)
        .filter(
            APPollRanking.team_id == team_id,
            APPollRanking.season == season,
            APPollRanking.week == week,
        )
        .first()
    )

    return ranking.rank if ranking else None


def get_ap_prediction_for_game(db: Session, game: Game) -> Optional[int]:
    """
    Determine AP-implied prediction for a game.

    AP Poll prediction logic:
    - Higher ranked team (lower rank number) is predicted to win
    - Ranked team beats unranked team
    - Both unranked = no prediction
    - Equal ranks = no prediction (very rare)

    Args:
        db: Database session
        game: Game object

    Returns:
        int: team_id of predicted winner, or None if no AP prediction possible

    Example:
        >>> # Georgia (#5) vs Tennessee (#12)
        >>> winner_id = get_ap_prediction_for_game(db, game)
        >>> # Returns Georgia's team_id (higher ranked = predicted winner)
    """
    # Get AP ranks for both teams
    home_rank = get_team_ap_rank(db, game.home_team_id, game.season, game.week)
    away_rank = get_team_ap_rank(db, game.away_team_id, game.season, game.week)

    # Both unranked - no prediction
    if home_rank is None and away_rank is None:
        return None

    # One team unranked - predict ranked team
    if home_rank is None:
        return game.away_team_id
    if away_rank is None:
        return game.home_team_id

    # Both ranked - lower number = higher rank = predicted winner
    if home_rank < away_rank:
        return game.home_team_id
    elif away_rank < home_rank:
        return game.away_team_id
    else:
        # Equal rankings (very rare) - no prediction
        return None


def calculate_comparison_stats(db: Session, season: int) -> Dict:
    """
    Calculate comparison statistics between ELO and AP Poll predictions.

    Compares:
    - Overall accuracy for each system
    - Accuracy by week
    - Accuracy by conference
    - Games where systems disagreed
    - Breakdown of correct/incorrect predictions

    Args:
        db: Database session
        season: Season year

    Returns:
        dict: Comprehensive comparison statistics

    Example response:
        {
            "season": 2024,
            "elo_accuracy": 0.73,
            "ap_accuracy": 0.68,
            "elo_advantage": 0.05,
            "total_games_compared": 127,
            "elo_correct": 93,
            "ap_correct": 86,
            "both_correct": 79,
            "elo_only_correct": 14,
            "ap_only_correct": 7,
            "both_wrong": 27,
            "by_week": [...],
            "disagreements": [...]
        }
    """
    # Get all completed games with ELO predictions for this season
    games = (
        db.query(Game)
        .filter(
            Game.season == season,
            Game.is_processed == True,
            Game.excluded_from_rankings == False,  # Only FBS vs FBS games
        )
        .all()
    )

    if not games:
        return {
            "season": season,
            "elo_accuracy": 0.0,
            "ap_accuracy": 0.0,
            "elo_advantage": 0.0,
            "total_games_compared": 0,
            "elo_correct": 0,
            "ap_correct": 0,
            "both_correct": 0,
            "elo_only_correct": 0,
            "ap_only_correct": 0,
            "both_wrong": 0,
            "by_week": [],
            "disagreements": [],
            "overall_elo_accuracy": 0.0,
            "overall_elo_total": 0,
            "overall_elo_correct": 0,
            "message": "Comparison data will be available once AP Poll rankings are imported for this season.",
        }

    # Track statistics
    total_games_compared = 0
    elo_correct_count = 0
    ap_correct_count = 0
    both_correct_count = 0
    elo_only_correct_count = 0
    ap_only_correct_count = 0
    both_wrong_count = 0

    by_week_stats = {}
    disagreements = []

    for game in games:
        # Get ELO prediction
        elo_prediction = db.query(Prediction).filter(Prediction.game_id == game.id).first()

        # Skip if no ELO prediction
        if not elo_prediction:
            continue

        # Get AP-implied prediction
        ap_predicted_winner_id = get_ap_prediction_for_game(db, game)

        # Skip if no AP prediction (both teams unranked)
        if ap_predicted_winner_id is None:
            continue

        # Now we have both predictions - include in comparison
        total_games_compared += 1

        # Determine actual winner
        actual_winner_id = (
            game.home_team_id if game.home_score > game.away_score else game.away_team_id
        )

        # Check if each system was correct
        elo_correct = elo_prediction.predicted_winner_id == actual_winner_id
        ap_correct = ap_predicted_winner_id == actual_winner_id

        # Update counts
        if elo_correct:
            elo_correct_count += 1
        if ap_correct:
            ap_correct_count += 1

        if elo_correct and ap_correct:
            both_correct_count += 1
        elif elo_correct and not ap_correct:
            elo_only_correct_count += 1
        elif ap_correct and not elo_correct:
            ap_only_correct_count += 1
        else:
            both_wrong_count += 1

        # Track by week
        week = game.week
        if week not in by_week_stats:
            by_week_stats[week] = {"week": week, "games": 0, "elo_correct": 0, "ap_correct": 0}
        by_week_stats[week]["games"] += 1
        if elo_correct:
            by_week_stats[week]["elo_correct"] += 1
        if ap_correct:
            by_week_stats[week]["ap_correct"] += 1

        # Track disagreements (where systems predicted different winners)
        if elo_prediction.predicted_winner_id != ap_predicted_winner_id:
            home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
            away_team = db.query(Team).filter(Team.id == game.away_team_id).first()
            elo_predicted_team = (
                db.query(Team).filter(Team.id == elo_prediction.predicted_winner_id).first()
            )
            ap_predicted_team = db.query(Team).filter(Team.id == ap_predicted_winner_id).first()

            disagreements.append(
                {
                    "game_id": game.id,
                    "week": week,
                    "matchup": f"{away_team.name} @ {home_team.name}",
                    "elo_predicted": elo_predicted_team.name if elo_predicted_team else "Unknown",
                    "ap_predicted": ap_predicted_team.name if ap_predicted_team else "Unknown",
                    "actual_winner": (
                        home_team.name if actual_winner_id == game.home_team_id else away_team.name
                    ),
                    "elo_correct": elo_correct,
                    "ap_correct": ap_correct,
                }
            )

    # Calculate accuracies
    elo_accuracy = elo_correct_count / total_games_compared if total_games_compared > 0 else 0.0
    ap_accuracy = ap_correct_count / total_games_compared if total_games_compared > 0 else 0.0
    elo_advantage = elo_accuracy - ap_accuracy

    # Calculate by-week accuracies
    by_week = []
    for week_num in sorted(by_week_stats.keys()):
        stats = by_week_stats[week_num]
        games_count = stats["games"]
        by_week.append(
            {
                "week": week_num,
                "elo_accuracy": stats["elo_correct"] / games_count if games_count > 0 else 0.0,
                "ap_accuracy": stats["ap_correct"] / games_count if games_count > 0 else 0.0,
                "games": games_count,
            }
        )

    # Calculate OVERALL ELO accuracy (all predictions, not just compared ones)
    all_predictions = (
        db.query(Prediction)
        .join(Game)
        .filter(Game.season == season, Prediction.was_correct.isnot(None))
        .all()
    )

    overall_elo_total = len(all_predictions)
    overall_elo_correct = sum(1 for p in all_predictions if p.was_correct)
    overall_elo_accuracy = overall_elo_correct / overall_elo_total if overall_elo_total > 0 else 0.0

    return {
        "season": season,
        "elo_accuracy": round(elo_accuracy, 4),  # Accuracy when compared to AP Poll
        "ap_accuracy": round(ap_accuracy, 4),
        "elo_advantage": round(elo_advantage, 4),
        "total_games_compared": total_games_compared,
        "elo_correct": elo_correct_count,
        "ap_correct": ap_correct_count,
        "both_correct": both_correct_count,
        "elo_only_correct": elo_only_correct_count,
        "ap_only_correct": ap_only_correct_count,
        "both_wrong": both_wrong_count,
        "by_week": by_week,
        "disagreements": disagreements,
        # New fields for overall ELO accuracy
        "overall_elo_accuracy": round(overall_elo_accuracy, 4),
        "overall_elo_total": overall_elo_total,
        "overall_elo_correct": overall_elo_correct,
    }
