"""
Compare our transfer portal rankings with 247Sports rankings
EPIC-026 Story 26.8: Validation
"""

import sqlite3
from typing import Dict, List, Tuple

# 247Sports Top 25 (from web scraping)
SPORTS_247_RANKINGS = {
    "Ole Miss": 1,
    "Oregon": 2,
    "Alabama": 3,
    "Texas A&M": 4,
    "Texas": 5,
    "Florida": 6,
    "Florida State": 7,
    "Ohio State": 8,
    "Colorado": 9,
    "Miami": 10,
    "Washington": 11,
    "Michigan State": 12,
    "Georgia": 13,
    "Missouri": 14,
    "Louisville": 15,
    "South Carolina": 16,
    "California": 17,
    "NC State": 18,
    "USC": 19,
    "Oklahoma": 20,
    "Kentucky": 21,
    "UCF": 22,
    "Wisconsin": 23,
    "Syracuse": 24,
    "TCU": 25,
}


def get_our_rankings(db_path: str = "cfb_rankings.db") -> Dict[str, int]:
    """Get our transfer portal rankings from database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name, transfer_portal_rank, transfer_portal_points, transfer_count
        FROM teams
        WHERE transfer_portal_rank IS NOT NULL
        ORDER BY transfer_portal_rank
    """
    )

    rankings = {}
    for row in cursor.fetchall():
        name, rank, points, count = row
        rankings[name] = {"rank": rank, "points": points, "count": count}

    conn.close()
    return rankings


def normalize_team_name(name: str) -> str:
    """Normalize team names for comparison"""
    # Handle common variations
    normalizations = {
        "Miami": "Miami",
        "Miami (FL)": "Miami",
        "USC": "USC",
        "Southern California": "USC",
        "NC State": "NC State",
        "North Carolina State": "NC State",
        "Texas A&M": "Texas A&M",
        "TCU": "TCU",
    }
    return normalizations.get(name, name)


def find_overlaps(
    sports247: Dict[str, int], ours: Dict[str, dict]
) -> Tuple[List[str], List[str], List[str]]:
    """Find teams in both rankings, and unique to each"""
    sports247_names = set(normalize_team_name(name) for name in sports247.keys())
    our_names = set(normalize_team_name(name) for name in ours.keys())

    in_both = sports247_names & our_names
    only_247 = sports247_names - our_names
    only_ours = our_names - sports247_names

    return sorted(in_both), sorted(only_247), sorted(only_ours)


def calculate_correlation(sports247: Dict[str, int], ours: Dict[str, dict]) -> float:
    """Calculate Spearman rank correlation for overlapping teams"""
    # Get teams in both rankings
    common_teams = []
    sports247_ranks = []
    our_ranks = []

    for team_247, rank_247 in sports247.items():
        team_norm = normalize_team_name(team_247)

        # Find matching team in our rankings
        for team_ours, data in ours.items():
            if normalize_team_name(team_ours) == team_norm:
                common_teams.append(team_norm)
                sports247_ranks.append(rank_247)
                our_ranks.append(data["rank"])
                break

    if len(common_teams) < 2:
        return 0.0

    # Manual Spearman correlation calculation
    n = len(sports247_ranks)
    d_squared_sum = sum((r1 - r2) ** 2 for r1, r2 in zip(sports247_ranks, our_ranks))
    correlation = 1 - (6 * d_squared_sum) / (n * (n**2 - 1))

    return correlation


def main():
    print("=" * 80)
    print("EPIC-026 Story 26.8: Transfer Portal Rankings Validation")
    print("Comparing our rankings vs 247Sports")
    print("=" * 80)
    print()

    # Get rankings
    sports247 = SPORTS_247_RANKINGS
    ours = get_our_rankings()

    print(f"247Sports Top 25: {len(sports247)} teams")
    print(f"Our rankings: {len(ours)} teams total")
    print()

    # Find overlaps
    in_both, only_247, only_ours = find_overlaps(sports247, ours)

    print(f"✓ Teams in both top 25: {len(in_both)}")
    print(f"  Only in 247Sports: {len(only_247)}")
    print(
        f"  Only in our top 25: {len([t for t in ours.keys() if ours[t]['rank'] <= 25]) - len(in_both)}"
    )
    print()

    # Calculate correlation
    correlation = calculate_correlation(sports247, ours)
    print(f"Spearman Rank Correlation: {correlation:.3f}")
    print()

    if correlation > 0.7:
        print("✅ Strong correlation (> 0.70)")
    elif correlation > 0.5:
        print("⚠️  Moderate correlation (0.50-0.70)")
    else:
        print("❌ Weak correlation (< 0.50)")
    print()

    # Detailed comparison
    print("=" * 80)
    print("DETAILED COMPARISON (Top 25)")
    print("=" * 80)
    print()
    print(f"{'Team':<25} {'247Sports':<12} {'Our Rank':<12} {'Diff':<10} {'Pts/Transfer'}")
    print("-" * 80)

    comparisons = []
    for team_247, rank_247 in sorted(sports247.items(), key=lambda x: x[1]):
        team_norm = normalize_team_name(team_247)

        # Find in our rankings
        our_rank = None
        our_points = None
        our_count = None
        for team_ours, data in ours.items():
            if normalize_team_name(team_ours) == team_norm:
                our_rank = data["rank"]
                our_points = data["points"]
                our_count = data["count"]
                break

        if our_rank:
            diff = our_rank - rank_247
            pts_per_transfer = our_points / our_count if our_count > 0 else 0
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            print(
                f"{team_247:<25} {rank_247:<12} {our_rank:<12} {diff_str:<10} {pts_per_transfer:.1f}"
            )
            comparisons.append((team_247, rank_247, our_rank, diff, pts_per_transfer))
        else:
            print(f"{team_247:<25} {rank_247:<12} {'N/A':<12} {'N/A':<10} -")

    print()

    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    # Calculate average difference
    diffs = [abs(c[3]) for c in comparisons if c[3] is not None]
    avg_diff = sum(diffs) / len(diffs) if diffs else 0

    print(f"Average rank difference: {avg_diff:.1f} positions")
    print()

    # Find biggest disagreements
    print("Biggest disagreements:")
    sorted_by_diff = sorted(comparisons, key=lambda x: abs(x[3]), reverse=True)[:5]
    for team, rank_247, our_rank, diff, pts_per in sorted_by_diff:
        if diff > 0:
            print(
                f"  • {team}: 247Sports #{rank_247}, Ours #{our_rank} ({pts_per:.1f} pts/transfer)"
            )
            print(f"    → We rank them {diff} spots LOWER (quantity-focused)")
        else:
            print(
                f"  • {team}: 247Sports #{rank_247}, Ours #{our_rank} ({pts_per:.1f} pts/transfer)"
            )
            print(f"    → We rank them {abs(diff)} spots HIGHER (quantity-focused)")

    print()

    # Quality vs Quantity analysis
    print("Quality vs Quantity Analysis:")
    print()

    high_quality = [c for c in comparisons if c[4] >= 68]  # High pts/transfer
    high_quantity = [c for c in comparisons if c[1] < c[2]]  # 247 ranks higher than us

    print(f"  High-quality transfers (≥68 pts/transfer): {len(high_quality)} teams")
    print(f"  247Sports ranks higher than us: {len(high_quantity)} teams")
    print()
    print("  → Our algorithm favors QUANTITY (more transfers)")
    print("  → 247Sports favors QUALITY (better recruits, fewer transfers)")
    print()

    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    if correlation < 0.5:
        print("❌ Low correlation suggests algorithmic differences")
        print()
        print("Options:")
        print("  1. Keep current approach (quantity-focused, simpler)")
        print("     • Rewards teams active in portal")
        print("     • Easier to explain and calculate")
        print()
        print("  2. Adjust algorithm to match 247Sports (quality-weighted)")
        print("     • Add quality multiplier (favor 4/5-star)")
        print("     • Use Gaussian distribution weighting")
        print("     • More complex, closer to expert rankings")
        print()
    else:
        print("✅ Acceptable correlation - algorithm is reasonable")
        print()

    print("=" * 80)


if __name__ == "__main__":
    main()
