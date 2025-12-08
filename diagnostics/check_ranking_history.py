#!/usr/bin/env python3
"""
Check ranking_history table for season-specific data
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


from sqlalchemy import func

from src.models.database import SessionLocal
from src.models.models import RankingHistory, Team


def check_ranking_history():
    """Verify ranking_history has season-specific data"""

    db = SessionLocal()

    print("=" * 80)
    print("RANKING HISTORY DATA CHECK")
    print("=" * 80)
    print()

    # Check seasons available
    seasons = db.query(RankingHistory.season).distinct().order_by(RankingHistory.season).all()
    print(f"Seasons in ranking_history: {[s[0] for s in seasons]}")
    print()

    # Check data for each season
    for season_tuple in seasons:
        season = season_tuple[0]

        # Get max week for this season
        max_week = (
            db.query(func.max(RankingHistory.week)).filter(RankingHistory.season == season).scalar()
        )

        # Count entries
        count = db.query(RankingHistory).filter(RankingHistory.season == season).count()

        print(f"Season {season}:")
        print(f"  Max week: {max_week}")
        print(f"  Total entries: {count}")
        print()

    # Sample data for 2024 Week 15 (latest)
    print("Sample: Top 5 teams for 2024 Week 15:")
    print("-" * 80)

    rankings_2024 = (
        db.query(RankingHistory)
        .filter(RankingHistory.season == 2024, RankingHistory.week == 15)
        .order_by(RankingHistory.rank)
        .limit(5)
        .all()
    )

    if rankings_2024:
        for rh in rankings_2024:
            print(
                f"  {rh.rank}. {rh.team.name}: {rh.wins}-{rh.losses} "
                f"(ELO: {rh.elo_rating:.2f}, SOS: {rh.sos:.2f})"
            )
    else:
        print("  ⚠️  No data found for 2024 Week 15")

    print()

    # Check if Ohio State data looks correct
    print("Ohio State record by season:")
    print("-" * 80)

    ohio_state = db.query(Team).filter(Team.name == "Ohio State").first()
    if ohio_state:
        for season_tuple in seasons:
            season = season_tuple[0]

            # Get latest week for this season
            latest = (
                db.query(RankingHistory)
                .filter(RankingHistory.team_id == ohio_state.id, RankingHistory.season == season)
                .order_by(RankingHistory.week.desc())
                .first()
            )

            if latest:
                print(
                    f"  {season} Week {latest.week}: {latest.wins}-{latest.losses} "
                    f"(Rank #{latest.rank}, ELO: {latest.elo_rating:.2f})"
                )

    print()

    db.close()


if __name__ == "__main__":
    check_ranking_history()
