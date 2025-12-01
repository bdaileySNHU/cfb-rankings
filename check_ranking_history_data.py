#!/usr/bin/env python3
"""
Check what data exists in ranking_history table
"""

from database import SessionLocal
from models import RankingHistory
from sqlalchemy import func


def check_ranking_history():
    """Check ranking_history data by season and week"""

    db = SessionLocal()

    print("="*80)
    print("RANKING_HISTORY DATA CHECK")
    print("="*80)
    print()

    # Get all season/week combinations
    season_week_data = db.query(
        RankingHistory.season,
        RankingHistory.week,
        func.count(RankingHistory.id).label('team_count'),
        func.avg(RankingHistory.wins + RankingHistory.losses).label('avg_games')
    ).group_by(
        RankingHistory.season,
        RankingHistory.week
    ).order_by(
        RankingHistory.season,
        RankingHistory.week
    ).all()

    current_season = None
    for row in season_week_data:
        if current_season != row.season:
            if current_season is not None:
                print()
            current_season = row.season
            print(f"Season {row.season}:")
            print(f"{'Week':<6} {'Teams':<8} {'Avg Games':<12}")
            print("-"*30)

        print(f"{row.week:<6} {row.team_count:<8} {row.avg_games:<12.1f}")

    print()
    print("="*80)
    print()

    # Check for data quality issues
    print("Data Quality Checks:")
    print()

    # Check for abnormally high game counts
    high_game_counts = db.query(
        RankingHistory.season,
        RankingHistory.week,
        RankingHistory.team_id,
        RankingHistory.wins,
        RankingHistory.losses
    ).filter(
        (RankingHistory.wins + RankingHistory.losses) > 15
    ).limit(10).all()

    if high_game_counts:
        print("⚠️  Teams with >15 games (likely cumulative data):")
        for r in high_game_counts:
            from models import Team
            team = db.query(Team).get(r.team_id)
            total = r.wins + r.losses
            print(f"  {r.season} Week {r.week}: {team.name if team else 'Unknown'} - {r.wins}-{r.losses} ({total} games)")
    else:
        print("✓ No teams with >15 games found")

    print()

    db.close()


if __name__ == "__main__":
    check_ranking_history()
