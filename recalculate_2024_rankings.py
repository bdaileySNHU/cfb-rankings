#!/usr/bin/env python3
"""
Recalculate 2024 season ELO ratings and ranking history

The 2024 ranking_history contains cumulative records from 2023+2024.
This script recalculates the entire 2024 season from scratch.
"""

from database import SessionLocal
from models import Team, Game, RankingHistory
from ranking_service import RankingService
import sys


def recalculate_2024_rankings():
    """Recalculate ELO ratings and ranking history for 2024 season"""

    db = SessionLocal()
    season = 2024

    print("="*80)
    print("RECALCULATE 2024 ELO RATINGS AND RANKING HISTORY")
    print("="*80)
    print()
    print("⚠️  WARNING: This will:")
    print("   - Delete all 2024 ranking_history")
    print("   - Replay all 2024 games from scratch")
    print("   - Regenerate ranking history for all weeks")
    print()

    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted")
        return 1

    print()

    # Get ranking service
    ranking_service = RankingService(db)

    # Step 1: Delete all 2024 ranking_history (it's corrupted)
    print("Step 1: Deleting corrupted 2024 ranking_history...")
    deleted_count = db.query(RankingHistory).filter(
        RankingHistory.season == season
    ).delete()
    db.commit()
    print(f"  ✓ Deleted {deleted_count} corrupted ranking records")
    print()

    # Step 2: Save current team state (2025 data)
    print("Step 2: Saving current team state...")
    team_state_backup = {}
    teams = db.query(Team).all()
    for team in teams:
        team_state_backup[team.id] = {
            'elo_rating': team.elo_rating,
            'wins': team.wins,
            'losses': team.losses
        }
    print(f"  ✓ Saved state for {len(teams)} teams")
    print()

    # Step 3: Reset all teams to 2024 preseason ratings
    print("Step 3: Resetting teams to 2024 preseason state...")
    for team in teams:
        team.elo_rating = team.initial_rating
        team.wins = 0
        team.losses = 0
    db.commit()
    print(f"  ✓ Reset {len(teams)} teams to preseason state")
    print()

    # Step 4: Mark all 2024 games as unprocessed
    print("Step 4: Marking 2024 games as unprocessed...")
    games_2024 = db.query(Game).filter(Game.season == season).all()
    for game in games_2024:
        game.is_processed = False
        game.home_rating_change = 0.0
        game.away_rating_change = 0.0
    db.commit()
    print(f"  ✓ Marked {len(games_2024)} games as unprocessed")
    print()

    # Step 5: Process all 2024 games in chronological order
    print("Step 5: Processing 2024 games in chronological order...")

    # Get all completed games (including shutouts)
    completed_games = db.query(Game).filter(
        Game.season == season,
        (Game.home_score + Game.away_score) > 0
    ).order_by(Game.week, Game.id).all()

    print(f"  Found {len(completed_games)} completed games to process")
    print()

    processed_count = 0
    max_week = 0

    for game in completed_games:
        try:
            result = ranking_service.process_game(game)
            processed_count += 1
            max_week = max(max_week, game.week)

            if processed_count % 100 == 0:
                print(f"    Processed {processed_count}/{len(completed_games)} games...")

        except Exception as e:
            print(f"    Error processing game {game.id}: {e}")
            continue

    print(f"  ✓ Processed {processed_count} games through Week {max_week}")
    print()

    # Step 6: Save ranking history for all weeks
    print(f"Step 6: Saving ranking history for Weeks 1-{max_week}...")

    for week in range(1, max_week + 1):
        ranking_service.save_weekly_rankings(season, week)
        if week % 5 == 0:
            print(f"    Saved Week {week}...")

    print(f"  ✓ Saved ranking history for {max_week} weeks")
    print()

    # Step 7: Restore 2025 team state
    print("Step 7: Restoring current (2025) team state...")
    for team in teams:
        if team.id in team_state_backup:
            backup = team_state_backup[team.id]
            team.elo_rating = backup['elo_rating']
            team.wins = backup['wins']
            team.losses = backup['losses']
    db.commit()
    print(f"  ✓ Restored 2025 state for {len(teams)} teams")
    print()

    # Verification
    print("="*80)
    print("VERIFICATION")
    print("="*80)
    print()

    # Check ranking_history count
    history_count = db.query(RankingHistory).filter(
        RankingHistory.season == season
    ).count()

    print(f"✓ {history_count} ranking records saved for 2024")
    print()

    # Show Oregon's correct 2024 record
    from models import RankingHistory
    oregon_week_15 = db.query(RankingHistory).filter(
        RankingHistory.team_id == 87,  # Oregon
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).first()

    if oregon_week_15:
        print(f"Oregon 2024 Week 15 (example):")
        print(f"  Record: {oregon_week_15.wins}-{oregon_week_15.losses}")
        print(f"  ELO: {oregon_week_15.elo_rating:.2f}")
        print(f"  Rank: {oregon_week_15.rank}")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(recalculate_2024_rankings())
