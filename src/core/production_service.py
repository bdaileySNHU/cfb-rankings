"""Production Service — on-field production signals for position strength.

EPIC-040 blends on-field production into the EPIC-039 roster quality score so
position strength reflects what players have actually done, not just recruiting
pedigree. This module holds the pure, testable pieces:

    - ``compute_percentiles``: map a population of production values (e.g. PPA)
      onto 0–100 percentile scores.
    - ``blend_quality``: combine a recruiting score and a production score.

Production data is sparse and offense-skill-heavy (PPA covers QB/RB/WR/TE).
Players without a production signal fall back to their recruiting score, so the
blend is "production where it exists, recruiting everywhere else".

Part of: EPIC-040 (Production-Blended Position Strength)
"""

from typing import Dict, List, Optional

# Position groups that have a per-player production signal in the skill-first
# phase (PPA covers offensive skill positions). OL and most defenders have no
# per-player PPA and stay on recruiting pedigree.
PRODUCTION_GROUPS = {"QB", "RB", "WR", "TE"}


def compute_percentiles(values: List[float]) -> List[float]:
    """Map a population of production values onto 0–100 percentile scores.

    Uses a rank-based percentile so the result is robust to PPA's arbitrary
    scale: for each value, percentile = (count strictly below + half the ties)
    / N * 100. A larger value always scores at least as high as a smaller one.

    Args:
        values: Production values for the population (same metric, e.g. avg PPA)

    Returns:
        List of 0–100 scores, one per input value, in the same order.
        Empty input returns an empty list; a single value returns [50.0].
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [50.0]

    scores = []
    for v in values:
        below = sum(1 for o in values if o < v)
        equal = sum(1 for o in values if o == v)
        pct = (below + 0.5 * equal) / n * 100.0
        scores.append(round(pct, 4))
    return scores


def blend_quality(
    recruiting_score: float,
    production_score: Optional[float],
    weight: float,
) -> float:
    """Blend a recruiting score with a production score (both 0–100).

    Args:
        recruiting_score: Recruiting-pedigree quality (0–100)
        production_score: On-field production quality (0–100), or None when the
            player has no production signal (e.g. OL, freshmen, no prior snaps)
        weight: Production weight ``w_prod`` in [0, 1]. The recruiting score gets
            ``1 - weight``. Ignored when production_score is None.

    Returns:
        Blended quality (0–100). Equals recruiting_score when production_score
        is None.
    """
    if production_score is None:
        return recruiting_score
    w = max(0.0, min(1.0, weight))
    return w * production_score + (1.0 - w) * recruiting_score
