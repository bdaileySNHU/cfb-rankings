"""Position Strength Calculation Service

This module calculates position group strength scores for teams based on
individual player recruiting rankings. Used to enhance preseason rating
calculations by accounting for roster quality at key positions.

The position strength bonus provides a more granular assessment of team
strength than aggregate recruiting rankings alone, recognizing that certain
positions (QB, OL, DL) have outsized impact on team success.

Part of: Preseason Enhancement Epic - Story 1.3

Key Concepts:
    - Position Groups: Major position categories (QB, OL, RB, WR, TE, DL, LB, DB, ST)
    - Position Weights: Configurable weights reflecting positional importance
    - Position Strength Score: Aggregate quality metric for each position group
    - Overall Bonus: Weighted sum of position scores (0-max_bonus points)

Algorithm:
    1. For each position group, select top N players on team (configurable)
    2. Calculate average recruiting rating for top players
    3. Normalize to 0-100 score per position
    4. Apply position weight from configuration
    5. Sum weighted scores to get overall position strength bonus

Example:
    Calculate position strength for a team:
        >>> from src.models.database import SessionLocal
        >>> from src.core.position_service import calculate_position_strength, load_position_weights
        >>>
        >>> db = SessionLocal()
        >>> weights = load_position_weights()
        >>>
        >>> # Calculate for team_id=1
        >>> bonus = calculate_position_strength(team_id=1, weights=weights["weights"], db=db)
        >>> print(f"Position strength bonus: {bonus:.2f} points")
        Position strength bonus: 125.75 points

Configuration:
    Position weights and behavior controlled by src/core/position_weights.json
    See load_position_weights() for schema details.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.models import Player, RosterPlayer

# Configure logging
logger = logging.getLogger(__name__)

# Position group definitions - maps specific positions to major groups
# Used to aggregate player data at the position group level
POSITION_GROUPS = {
    "QB": ["QB"],
    "OL": ["OL", "OT", "OG", "C"],
    "RB": ["RB", "FB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "DL": ["DL", "DT", "DE"],
    "LB": ["LB", "OLB", "ILB"],
    "DB": ["DB", "CB", "S", "FS", "SS"],
    "ST": ["K", "P", "LS"],
}

# Default configuration path (relative to this file)
DEFAULT_CONFIG_PATH = Path(__file__).parent / "position_weights.json"

# CFBD recruit composite ratings fall on a ~0.70–1.00 scale (the 5★/elite band
# is ~0.98+, a low-end FBS roster averages ~0.80). Map that band onto a 0–100
# quality score so position group scores — and the preseason ELO bonus derived
# from them — have meaningful spread between elite and average rosters.
RATING_FLOOR = 0.70
RATING_CEIL = 1.00


def _normalize_rating(avg_rating: float) -> float:
    """Map an average recruit rating onto a 0–100 position quality score.

    CFBD composite ratings are on a 0–1 scale, so they are stretched from the
    realistic recruit band ([RATING_FLOOR, RATING_CEIL]) to 0–100. Values above
    1.0 are assumed to already be on a 0–100 scale (legacy/manual data) and are
    simply clamped, which keeps the function correct for either representation.

    Args:
        avg_rating: Average recruit rating for a position group

    Returns:
        float: Quality score clamped to 0.0–100.0
    """
    if avg_rating is None:
        return 0.0
    if avg_rating > 1.0:
        # Already on a 0–100 scale
        return min(avg_rating, 100.0)
    scaled = (avg_rating - RATING_FLOOR) / (RATING_CEIL - RATING_FLOOR) * 100.0
    return max(0.0, min(scaled, 100.0))


def load_position_weights(config_path: Optional[str] = None) -> Dict:
    """Load position weights configuration from JSON file.

    Reads the position weights configuration file which controls:
    - Whether position strength is enabled
    - Weight assigned to each position group (0.0-1.0)
    - Maximum bonus points contribution
    - Number of top players to consider per position

    Args:
        config_path: Path to position_weights.json file (optional)
                     Defaults to src/core/position_weights.json

    Returns:
        dict: Configuration dictionary with schema:
            {
                "version": "1.0",
                "enabled": bool,  # Feature flag
                "weights": {
                    "QB": float,   # 0.0-1.0, weights should sum to 1.0
                    "OL": float,
                    ...
                },
                "max_bonus": int,  # Maximum bonus points (e.g., 150)
                "top_players_per_position": {
                    "QB": int,  # Number of top players to consider
                    "OL": int,
                    ...
                }
            }

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
        ValueError: If configuration validation fails

    Example:
        >>> config = load_position_weights()
        >>> print(f"Feature enabled: {config['enabled']}")
        >>> print(f"QB weight: {config['weights']['QB']}")
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Position weights config not found: {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Validate configuration
    _validate_config(config)

    return config


def _validate_config(config: Dict) -> None:
    """Validate position weights configuration.

    Ensures configuration has required fields and valid values.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If configuration is invalid

    Note:
        Validation rules:
        - Must have 'enabled', 'weights', 'max_bonus', 'top_players_per_position' keys
        - Weights must sum to approximately 1.0 (within 0.01 tolerance)
        - All weights must be between 0.0 and 1.0
        - max_bonus must be positive
        - top_players_per_position values must be positive integers
    """
    required_keys = ["enabled", "weights", "max_bonus", "top_players_per_position"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Configuration missing required key: {key}")

    # Validate weights sum to 1.0
    weights_sum = sum(config["weights"].values())
    if abs(weights_sum - 1.0) > 0.01:
        raise ValueError(f"Position weights must sum to 1.0, got {weights_sum:.3f}")

    # Validate weight values
    for pos, weight in config["weights"].items():
        if not 0.0 <= weight <= 1.0:
            raise ValueError(f"Position weight for {pos} must be 0.0-1.0, got {weight}")

    # Validate max_bonus
    if config["max_bonus"] <= 0:
        raise ValueError(f"max_bonus must be positive, got {config['max_bonus']}")

    # Validate top_players_per_position
    for pos, count in config["top_players_per_position"].items():
        if not isinstance(count, int) or count <= 0:
            raise ValueError(
                f"top_players_per_position for {pos} must be positive integer, got {count}"
            )


def resolve_roster_season(db: Session, team_id: int, season: Optional[int]) -> Optional[int]:
    """Return the roster snapshot season to score from, or None if unavailable.

    If ``season`` is given and a snapshot exists for it, use it. Otherwise fall
    back to the most recent season present in ``roster_players`` for this team.
    Returns None when the team has no roster snapshot at all (caller then falls
    back to recruiting-class scoring).
    """
    if season is not None:
        exists = (
            db.query(RosterPlayer.id)
            .filter(RosterPlayer.season == season, RosterPlayer.team_id == team_id)
            .first()
        )
        if exists:
            return season

    latest = (
        db.query(RosterPlayer.season)
        .filter(RosterPlayer.team_id == team_id)
        .order_by(RosterPlayer.season.desc())
        .first()
    )
    return latest[0] if latest else None


def get_position_group_scores(
    team_id: int,
    db: Session,
    config: Optional[Dict] = None,
    season: Optional[int] = None,
) -> Dict[str, float]:
    """Calculate quality scores for each position group on a team.

    For each major position group (QB, OL, DL, etc.), calculates a quality score
    (0–100) from the top players at that position.

    The data source is controlled by ``config["source"]`` (EPIC-039):
        - "roster": score from the team's actual roster snapshot
          (``roster_players``) — reflects transfers in, departures out, and all
          class years. Falls back to recruiting per-team when no snapshot exists.
        - "recruiting" (default): score from recruiting-class signings
          (``players``).

    Args:
        team_id: Database ID of the team
        db: SQLAlchemy database session
        config: Optional configuration dict (loads default if not provided)
        season: Season to use for roster scoring (defaults to the team's most
            recent roster snapshot; ignored for the recruiting source)

    Returns:
        dict: Position group scores keyed by group name, 0.0 where no rated
        players exist for the group.

    Note:
        - Uses top N players per position (configured in top_players_per_position)
        - Average rating normalized to 0–100 via _normalize_rating()
    """
    if config is None:
        config = load_position_weights()

    source = config.get("source", "recruiting")
    roster_season = None
    if source == "roster":
        roster_season = resolve_roster_season(db, team_id, season)
        if roster_season is None:
            logger.debug(
                f"Team {team_id} has no roster snapshot; "
                f"falling back to recruiting-class scoring"
            )

    # EPIC-040: when blending is enabled on the roster source, score from the
    # pre-computed blended_rating (recruiting pedigree + on-field production,
    # already on a 0–100 scale) instead of the raw recruiting rating.
    use_blend = roster_season is not None and config.get("blend", False)

    scores = {}

    for group_name, positions in POSITION_GROUPS.items():
        top_n = config["top_players_per_position"].get(group_name, 3)

        if roster_season is not None:
            rating_col = RosterPlayer.blended_rating if use_blend else RosterPlayer.rating
            ratings = [
                r
                for (r,) in db.query(rating_col)
                .filter(
                    RosterPlayer.season == roster_season,
                    RosterPlayer.team_id == team_id,
                    RosterPlayer.position.in_(positions),
                    rating_col.isnot(None),
                )
                .order_by(rating_col.desc())
                .limit(top_n)
                .all()
            ]
        else:
            ratings = [
                p.rating
                for p in db.query(Player)
                .filter(
                    Player.team_id == team_id,
                    Player.position.in_(positions),
                    Player.rating.isnot(None),
                )
                .order_by(Player.rating.desc())
                .limit(top_n)
                .all()
            ]

        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            if use_blend:
                # blended_rating is already a 0–100 quality score
                score = max(0.0, min(avg_rating, 100.0))
            else:
                # Normalize CFBD 0–1 composite (or legacy 0–100) to a 0–100 score
                score = _normalize_rating(avg_rating)
        else:
            score = 0.0
            if config.get("enabled", False):
                logger.debug(f"Team {team_id} has no players in position group {group_name}")

        scores[group_name] = score

    return scores


def aggregate_player_ratings(players: List[Player], position_group: str) -> float:
    """Aggregate recruiting ratings for a list of players.

    Calculates the average recruiting rating for a group of players,
    used as a quality metric for the position group.

    Args:
        players: List of Player objects to aggregate
        position_group: Position group name (for logging only)

    Returns:
        float: Average recruiting rating (0-100), or 0.0 if no players

    Example:
        >>> players = [player1, player2, player3]  # Player objects
        >>> avg_rating = aggregate_player_ratings(players, "QB")
        >>> print(f"Average QB rating: {avg_rating:.2f}")

    Note:
        - Only considers players with non-None rating values
        - Returns 0.0 if no valid ratings found
        - Normalizes to max 100.0
    """
    # Filter to players with valid ratings
    valid_players = [p for p in players if p.rating is not None]

    if not valid_players:
        return 0.0

    # Calculate average
    avg_rating = sum(p.rating for p in valid_players) / len(valid_players)

    # Normalize CFBD 0–1 composite (or legacy 0–100) to a 0–100 score
    return _normalize_rating(avg_rating)


def calculate_position_strength(
    team_id: int,
    weights: Dict[str, float],
    db: Session,
    max_bonus: Optional[int] = None,
    season: Optional[int] = None,
) -> float:
    """Calculate position strength bonus for a team's preseason rating.

    Computes an overall position strength score by evaluating roster quality
    across all position groups, applying configurable weights to reflect
    the relative importance of each position.

    Algorithm:
        1. Get quality score (0-100) for each position group
        2. Apply position weight (0.0-1.0) to each score
        3. Sum weighted scores to get overall percentage (0-100)
        4. Scale to max_bonus range (e.g., 0-150 points)

    Args:
        team_id: Database ID of the team
        weights: Dictionary mapping position group to weight (0.0-1.0)
                 Example: {"QB": 0.30, "OL": 0.25, ...}
                 Must sum to 1.0
        db: SQLAlchemy database session
        max_bonus: Maximum bonus points (defaults to 150)

    Returns:
        float: Position strength bonus in rating points (0-max_bonus)
               Returns 0.0 if team has no player data

    Raises:
        ValueError: If weights don't sum to 1.0 (within 0.01 tolerance)

    Example:
        >>> weights = {"QB": 0.30, "OL": 0.25, "DL": 0.20, ...}
        >>> bonus = calculate_position_strength(
        ...     team_id=5,
        ...     weights=weights,
        ...     db=session,
        ...     max_bonus=150
        ... )
        >>> print(f"Position bonus: {bonus:.2f} points")
        Position bonus: 125.75 points

    Note:
        - If team has no players, returns 0.0 (graceful degradation)
        - Logs warnings when falling back due to missing data
        - Position scores are 0-100, weights sum to 1.0, so weighted
          sum is 0-100, which is then scaled to 0-max_bonus
    """
    if max_bonus is None:
        max_bonus = 150

    # Validate weights sum to 1.0
    weights_sum = sum(weights.values())
    if abs(weights_sum - 1.0) > 0.01:
        raise ValueError(f"Position weights must sum to 1.0, got {weights_sum:.3f}")

    # Get position group scores
    config = load_position_weights()
    scores = get_position_group_scores(team_id, db, config, season=season)

    # Check if team has any player data
    if all(score == 0.0 for score in scores.values()):
        logger.warning(f"Team {team_id} has no player data, position strength bonus = 0.0")
        return 0.0

    # Calculate weighted sum (0-100 scale)
    weighted_sum = 0.0
    for position_group, weight in weights.items():
        score = scores.get(position_group, 0.0)
        contribution = score * weight
        weighted_sum += contribution

        # Debug logging
        logger.debug(
            f"Team {team_id} - Position {position_group}: score={score:.2f}, "
            f"weight={weight:.2f}, contribution={contribution:.2f}"
        )

    # Scale to max_bonus range
    # weighted_sum is 0-100, scale to 0-max_bonus
    position_bonus = (weighted_sum / 100.0) * max_bonus

    logger.debug(
        f"Team {team_id} - Total weighted sum: {weighted_sum:.2f}, "
        f"Position strength bonus: {position_bonus:.2f}"
    )

    return position_bonus
