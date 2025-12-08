#!/usr/bin/env python3
"""
Recalculate 2025 season ELO ratings - Story 24.1 Follow-up

After fixing win/loss records, we need to recalculate ELO ratings
by replaying all 2025 games in chronological order.
"""

import sys

from src.models.database import SessionLocal
from src.models.models import Game, Team
from src.core.ranking_service import RankingService


def recalculate_2025_rankings():
    """Recalculate ELO ratings for 2025 season"""

    db = SessionLocal()
    season = 2025

    print("="*80)
    print("RECALCULATE 2025 ELO RATINGS")
    print("="*80)
    print()

    # Get ranking service
    ranking_service = RankingService(db)

    # Step 1: Reset all teams to preseason ratings
    print("Step 1: Resetting teams to preseason ratings...")
    teams = db.query(Team).all()
    for team in teams:
        team.elo_rating = team.initial_rating
        team.wins = 0
        team.losses = 0
    db.commit()
    print(f"  ✓ Reset {len(teams)} teams to preseason state")
    print()

    # Step 2: Mark all 2025 games as unprocessed
    print("Step 2: Marking 2025 games as unprocessed...")
    games_2025 = db.query(Game).filter(Game.season == season).all()
    for game in games_2025:
        game.is_processed = False
        game.home_rating_change = 0.0
        game.away_rating_change = 0.0
    db.commit()
    print(f"  ✓ Marked {len(games_2025)} games as unprocessed")
    print()

    # Step 3: Process all completed games in chronological order
    print("Step 3: Processing games in chronological order...")

    # Get all games that have scores (completed)
    # Note: A game is completed if EITHER team scored, or if both are 0 but marked as played
    # We use home_score + away_score > 0 to catch shutouts (like Wisconsin 0, OSU 34)
    completed_games = db.query(Game).filter(
        Game.season == season,
        (Game.home_score + Game.away_score) > 0  # At least one team scored
    ).order_by(Game.week, Game.id).all()

    print(f"  Found {len(completed_games)} completed games to process")
    print()

    processed_count = 0
    for game in completed_games:
        # Process the game through ranking service
        try:
            result = ranking_service.process_game(game)
            processed_count += 1

            if processed_count % 100 == 0:
                print(f"    Processed {processed_count}/{len(completed_games)} games...")

        except Exception as e:
            print(f"    Error processing game {game.id}: {e}")
            continue

    print(f"  ✓ Processed {processed_count} games")
    print()

    # Step 4: Save rankings
    print("Step 4: Saving final rankings...")

    # Get current week
    max_week = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True
    ).order_by(Game.week.desc()).first()

    if max_week:
        current_week = max_week.week
        ranking_service.save_weekly_rankings(season, current_week)
        print(f"  ✓ Saved rankings for Week {current_week}")

    print()

    # Verification
    print("="*80)
    print("VERIFICATION")
    print("="*80)
    print()

    # Show top 10
    print("Top 10 teams by ELO rating:")
    top_teams = db.query(Team).order_by(Team.elo_rating.desc()).limit(10).all()
    for i, team in enumerate(top_teams, 1):
        print(f"  {i:2}. {team.name:30} {team.wins:2}-{team.losses:2}  ELO: {team.elo_rating:.2f}")

    print()

    db.close()

    return 0


if __name__ == "__main__":
    print()
    print("⚠️  WARNING: This will reset and recalculate all 2025 ELO ratings")
    print()
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted")
        sys.exit(1)

    print()
    sys.exit(recalculate_2025_rankings())
