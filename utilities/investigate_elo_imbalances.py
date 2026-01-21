#!/usr/bin/env python3
"""Investigate ELO Imbalances

This script analyzes games with ELO rating imbalances to understand
the nature and severity of the imbalances.

Usage:
    python utilities/investigate_elo_imbalances.py --season 2025

Part of Season-End Finalization Utilities
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import SessionLocal
from src.models.models import Game, Team


def analyze_imbalances(db, season: int):
    """Analyze ELO imbalances in detail."""
    print(f"\nAnalyzing ELO imbalances for season {season}...\n")

    # Find games with ELO imbalances
    games = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True,
        Game.excluded_from_rankings == False
    ).all()

    imbalances = []
    for game in games:
        rating_sum = game.home_rating_change + game.away_rating_change
        if abs(rating_sum) > 0.01:
            imbalances.append((game, rating_sum))

    if not imbalances:
        print("✓ No ELO imbalances found")
        return

    print(f"Found {len(imbalances)} games with ELO imbalances")
    print(f"Total games analyzed: {len(games)}")
    print(f"Imbalance rate: {len(imbalances)/len(games)*100:.1f}%\n")

    # Analyze by week
    print("Imbalances by week:")
    weeks = {}
    for game, imbalance in imbalances:
        week = game.week
        if week not in weeks:
            weeks[week] = []
        weeks[week].append(abs(imbalance))

    for week in sorted(weeks.keys()):
        imbs = weeks[week]
        avg = sum(imbs) / len(imbs)
        max_imb = max(imbs)
        print(f"  Week {week:2d}: {len(imbs):3d} games, avg={avg:.4f}, max={max_imb:.4f}")

    # Analyze severity
    print("\nImbalance severity distribution:")
    severity_ranges = [
        (0.01, 0.1, "Tiny (0.01-0.1)"),
        (0.1, 1.0, "Small (0.1-1.0)"),
        (1.0, 5.0, "Medium (1.0-5.0)"),
        (5.0, 10.0, "Large (5.0-10.0)"),
        (10.0, float('inf'), "Very Large (>10.0)")
    ]

    for min_val, max_val, label in severity_ranges:
        count = sum(1 for _, imb in imbalances if min_val <= abs(imb) < max_val)
        if count > 0:
            print(f"  {label}: {count} games")

    # Show worst cases
    print("\nWorst 10 imbalances:")
    worst = sorted(imbalances, key=lambda x: abs(x[1]), reverse=True)[:10]
    for i, (game, imbalance) in enumerate(worst, 1):
        home = db.query(Team).filter(Team.id == game.home_team_id).first()
        away = db.query(Team).filter(Team.id == game.away_team_id).first()
        print(f"  {i}. Week {game.week}: {home.name if home else 'Unknown'} vs {away.name if away else 'Unknown'}")
        print(f"     Imbalance: {imbalance:.6f} (home: {game.home_rating_change:+.2f}, away: {game.away_rating_change:+.2f})")
        print(f"     Score: {game.home_score}-{game.away_score}, Neutral: {game.is_neutral_site}")

    # Check if imbalances are systemic or random
    total_imbalance = sum(imb for _, imb in imbalances)
    avg_imbalance = total_imbalance / len(imbalances)

    print(f"\nStatistics:")
    print(f"  Total imbalance: {total_imbalance:.6f}")
    print(f"  Average imbalance: {avg_imbalance:.6f}")
    print(f"  Max imbalance: {max(abs(imb) for _, imb in imbalances):.6f}")
    print(f"  Min imbalance: {min(abs(imb) for _, imb in imbalances):.6f}")

    # Determine if acceptable
    max_imbalance = max(abs(imb) for _, imb in imbalances)
    avg_abs_imbalance = sum(abs(imb) for _, imb in imbalances) / len(imbalances)

    print("\nAssessment:")
    if max_imbalance < 0.1:
        print("  ✓ All imbalances are tiny (< 0.1) - likely floating-point precision")
        print("  ✓ Safe to proceed with finalization")
    elif max_imbalance < 1.0 and avg_abs_imbalance < 0.5:
        print("  ⚠ Imbalances are small but noticeable")
        print("  ⚠ Consider investigating but likely safe to proceed")
    else:
        print("  ✗ Significant imbalances detected")
        print("  ✗ Should investigate root cause before finalizing")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Investigate ELO imbalances in season data"
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to investigate (e.g., 2025)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Investigate ELO Imbalances - Season {args.season}")
    print(f"{'='*60}")

    db = SessionLocal()

    try:
        analyze_imbalances(db, args.season)
        print(f"\n{'='*60}\n")
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
