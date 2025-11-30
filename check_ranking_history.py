#!/usr/bin/env python3
"""
Check if ranking history exists for a team/season
"""

from database import SessionLocal
from models import RankingHistory, Team
import sys


def check_ranking_history(team_id, season):
    """Check ranking history for a specific team and season"""
    try:
        db = SessionLocal()

        # Get team
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            print(f"Team ID {team_id} not found")
            return 1

        print("=" * 80)
        print(f"RANKING HISTORY CHECK: {team.name} - {season}")
        print("=" * 80)
        print()

        # Check current team record
        print(f"Current Team Record (from teams table):")
        print(f"  Wins: {team.wins}")
        print(f"  Losses: {team.losses}")
        print(f"  ELO Rating: {team.elo_rating:.2f}")
        print()

        # Check ranking history
        history = db.query(RankingHistory).filter(
            RankingHistory.team_id == team_id,
            RankingHistory.season == season
        ).order_by(RankingHistory.week).all()

        if not history:
            print(f"❌ NO RANKING HISTORY FOUND for {team.name} in {season}")
            print()
            print("This means:")
            print("  1. Rankings were never saved for this season")
            print("  2. Or the season hasn't been processed yet")
            print()
            print("To fix: Run ranking calculation and save for this season")
            return 1

        print(f"✓ Found {len(history)} weeks of ranking history")
        print()

        # Show last 3 weeks
        print("Last 3 weeks:")
        for week_data in history[-3:]:
            print(f"  Week {week_data.week}: Rank #{week_data.rank}, "
                  f"Record: {week_data.wins}-{week_data.losses}, "
                  f"ELO: {week_data.elo_rating:.2f}")

        print()
        print("=" * 80)
        print("CONCLUSION")
        print("=" * 80)

        last_week = history[-1]
        print(f"End of {season} season stats for {team.name}:")
        print(f"  Final Record: {last_week.wins}-{last_week.losses}")
        print(f"  Final ELO: {last_week.elo_rating:.2f}")
        print(f"  Final Rank: #{last_week.rank}")
        print()

        db.close()
        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_ranking_history.py <team_id> <season>")
        print("Example: python check_ranking_history.py 107 2024")
        sys.exit(1)

    team_id = int(sys.argv[1])
    season = int(sys.argv[2])

    sys.exit(check_ranking_history(team_id, season))
