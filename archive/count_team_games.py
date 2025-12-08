#!/usr/bin/env python3
"""
Count actual games played by a team in a season
"""

import sys

from src.models.database import SessionLocal
from src.models.models import Game, Team


def count_team_games(team_id, season):
    """Count processed games for a team in a season"""

    db = SessionLocal()

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        print(f"Team ID {team_id} not found")
        return 1

    print("="*80)
    print(f"GAME COUNT: {team.name} - {season}")
    print("="*80)
    print()

    # Count all games
    total_games = db.query(Game).filter(
        ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)),
        Game.season == season
    ).count()

    # Count processed games
    processed_games = db.query(Game).filter(
        ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)),
        Game.season == season,
        Game.is_processed == True
    ).all()

    # Count wins and losses
    wins = 0
    losses = 0

    for game in processed_games:
        is_home = game.home_team_id == team_id

        if is_home:
            if game.home_score > game.away_score:
                wins += 1
            else:
                losses += 1
        else:
            if game.away_score > game.home_score:
                wins += 1
            else:
                losses += 1

    print(f"Total games in schedule: {total_games}")
    print(f"Processed games: {len(processed_games)}")
    print(f"Actual record: {wins}-{losses}")
    print()

    # Compare to ranking_history
    from models import RankingHistory

    for week in [14, 15]:
        rank_history = db.query(RankingHistory).filter(
            RankingHistory.team_id == team_id,
            RankingHistory.season == season,
            RankingHistory.week == week
        ).first()

        if rank_history:
            total_in_history = rank_history.wins + rank_history.losses
            print(f"Week {week} ranking_history: {rank_history.wins}-{rank_history.losses} ({total_in_history} games)")
        else:
            print(f"Week {week} ranking_history: Not found")

    print()
    print("Analysis:")
    print(f"  Actual games through season: {len(processed_games)}")

    if len(processed_games) < 20:
        print(f"  ✓ Normal game count for college football season")
    else:
        print(f"  ⚠️  Abnormally high - ranking_history likely has cumulative data")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python count_team_games.py <team_id> <season>")
        print("Example: python count_team_games.py 87 2024  (Oregon)")
        sys.exit(1)

    team_id = int(sys.argv[1])
    season = int(sys.argv[2])

    sys.exit(count_team_games(team_id, season))
