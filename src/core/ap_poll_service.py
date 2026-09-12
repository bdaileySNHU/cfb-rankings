"""
AP Poll Comparison Service

Handles AP Poll prediction logic and comparison with ELO predictions.
Part of EPIC-010: AP Poll Prediction Comparison.
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.models import APPollRanking, Game, Prediction, SPPlusRating, Team


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
            # The table has a poll_type column and no poll_type in its unique
            # constraint, so it can hold more than one poll per team-week.
            # Without this filter .first() would return an arbitrary source.
            APPollRanking.poll_type == "AP Top 25",
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
    return _pick_by_rank(game, home_rank, away_rank)


def _pick_by_rank(game: Game, home_rank: Optional[int], away_rank: Optional[int]) -> Optional[int]:
    """
    Winner implied by two ranks, where a lower number is the better team.

    Shared by the AP and SP+ predictions: they differ in where the ranks come
    from, not in how a matchup is called.
    """
    if home_rank is None and away_rank is None:
        return None
    if home_rank is None:
        return game.away_team_id
    if away_rank is None:
        return game.home_team_id
    if home_rank < away_rank:
        return game.home_team_id
    if away_rank < home_rank:
        return game.away_team_id
    # Equal ranks (very rare) - no prediction
    return None


def get_team_sp_rank(db: Session, team_id: int, season: int, week: int) -> Optional[int]:
    """
    Get a team's SP+ rank for a week, from the snapshot taken that week.

    Returns None when the week was never snapshotted -- which is every week
    before SP+ import was switched on, since CFBD cannot serve a past week's
    ratings and those snapshots can never be recovered.

    Args:
        db: Database session
        team_id: Team ID
        season: Season year
        week: Week number

    Returns:
        int: Team's SP+ rank (1 = best), or None if not snapshotted
    """
    rating = (
        db.query(SPPlusRating)
        .filter(
            SPPlusRating.team_id == team_id,
            SPPlusRating.season == season,
            SPPlusRating.week == week,
        )
        .first()
    )

    return rating.ranking if rating else None


def get_sp_prediction_for_game(db: Session, game: Game) -> Optional[int]:
    """
    Determine the SP+ implied prediction for a game.

    Same rule as the AP prediction -- better rank wins -- but SP+ rates every
    FBS team, so this returns a pick for essentially any FBS-vs-FBS game in a
    snapshotted week, where the AP version is silent whenever both teams are
    outside the top 25.

    Args:
        db: Database session
        game: Game object

    Returns:
        int: team_id of predicted winner, or None if no SP+ prediction possible
    """
    home_rank = get_team_sp_rank(db, game.home_team_id, game.season, game.week)
    away_rank = get_team_sp_rank(db, game.away_team_id, game.season, game.week)

    return _pick_by_rank(game, home_rank, away_rank)


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
            # EPIC-COMPARISON-BOWL-PLAYOFF: Include postseason fields in empty state
            "regular_season_elo_accuracy": 0.0,
            "regular_season_ap_accuracy": 0.0,
            "postseason_elo_accuracy": 0.0,
            "postseason_ap_accuracy": 0.0,
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

    # EPIC-COMPARISON-BOWL-PLAYOFF: Track regular season vs postseason separately
    regular_season_games = 0
    regular_season_elo_correct = 0
    regular_season_ap_correct = 0
    postseason_games = 0
    postseason_elo_correct = 0
    postseason_ap_correct = 0

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

        # EPIC-COMPARISON-BOWL-PLAYOFF: Track regular season (weeks 1-15) vs postseason (weeks 16-20)
        if game.week <= 15:
            regular_season_games += 1
            if elo_correct:
                regular_season_elo_correct += 1
            if ap_correct:
                regular_season_ap_correct += 1
        else:
            postseason_games += 1
            if elo_correct:
                postseason_elo_correct += 1
            if ap_correct:
                postseason_ap_correct += 1

        # Track by week
        week = game.week
        if week not in by_week_stats:
            # EPIC-COMPARISON-BOWL-PLAYOFF: Include game_type and postseason_name for frontend labeling
            by_week_stats[week] = {
                "week": week,
                "games": 0,
                "elo_correct": 0,
                "ap_correct": 0,
                "game_type": game.game_type,  # 'bowl', 'playoff', 'conference_championship', or None
                "postseason_name": game.postseason_name,  # Bowl/playoff name
            }
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

            # EPIC-COMPARISON-BOWL-PLAYOFF: Include game_type and postseason_name for frontend labeling
            disagreements.append(
                {
                    "game_id": game.id,
                    "week": week,
                    "game_type": game.game_type,
                    "postseason_name": game.postseason_name,
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
        # EPIC-COMPARISON-BOWL-PLAYOFF: Include game_type and postseason_name in output
        by_week.append(
            {
                "week": week_num,
                "elo_accuracy": stats["elo_correct"] / games_count if games_count > 0 else 0.0,
                "ap_accuracy": stats["ap_correct"] / games_count if games_count > 0 else 0.0,
                "games": games_count,
                "game_type": stats.get("game_type"),
                "postseason_name": stats.get("postseason_name"),
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

    # EPIC-COMPARISON-BOWL-PLAYOFF: Calculate postseason-specific accuracies
    regular_season_elo_accuracy = (
        regular_season_elo_correct / regular_season_games if regular_season_games > 0 else 0.0
    )
    regular_season_ap_accuracy = (
        regular_season_ap_correct / regular_season_games if regular_season_games > 0 else 0.0
    )
    postseason_elo_accuracy = (
        postseason_elo_correct / postseason_games if postseason_games > 0 else 0.0
    )
    postseason_ap_accuracy = postseason_ap_correct / postseason_games if postseason_games > 0 else 0.0

    # SP+ comparison, computed as its own pass. SP+ reaches games the AP Top 25
    # is silent on, so it has a different (much larger) denominator and cannot
    # share the counters above. elo_*_vs_sp re-measures ELO over exactly the SP+
    # subset, which is the only fair way to read the two against each other.
    sp_games_compared = 0
    sp_correct_count = 0
    elo_correct_vs_sp = 0

    for game in games:
        elo_prediction = db.query(Prediction).filter(Prediction.game_id == game.id).first()
        if not elo_prediction:
            continue

        sp_predicted_winner_id = get_sp_prediction_for_game(db, game)
        if sp_predicted_winner_id is None:
            continue

        actual_winner_id = (
            game.home_team_id if game.home_score > game.away_score else game.away_team_id
        )

        sp_games_compared += 1
        if sp_predicted_winner_id == actual_winner_id:
            sp_correct_count += 1
        if elo_prediction.predicted_winner_id == actual_winner_id:
            elo_correct_vs_sp += 1

    sp_accuracy = sp_correct_count / sp_games_compared if sp_games_compared > 0 else 0.0
    elo_accuracy_vs_sp = elo_correct_vs_sp / sp_games_compared if sp_games_compared > 0 else 0.0

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
        # EPIC-COMPARISON-BOWL-PLAYOFF: Postseason-specific statistics
        "regular_season_elo_accuracy": round(regular_season_elo_accuracy, 4),
        "regular_season_ap_accuracy": round(regular_season_ap_accuracy, 4),
        "postseason_elo_accuracy": round(postseason_elo_accuracy, 4),
        "postseason_ap_accuracy": round(postseason_ap_accuracy, 4),
        # SP+ comparison (own denominator -- see the pass above)
        "sp_games_compared": sp_games_compared,
        "sp_correct": sp_correct_count,
        "sp_accuracy": round(sp_accuracy, 4),
        "elo_correct_vs_sp": elo_correct_vs_sp,
        "elo_accuracy_vs_sp": round(elo_accuracy_vs_sp, 4),
        "elo_advantage_vs_sp": round(elo_accuracy_vs_sp - sp_accuracy, 4),
    }
