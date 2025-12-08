#!/usr/bin/env python3
"""
Check bowl games imported in database
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


from database import SessionLocal
from models import Game


def check_bowl_games(season=2024):
    """Check all bowl games for a season"""

    db = SessionLocal()

    print("="*80)
    print(f"BOWL GAMES - {season}")
    print("="*80)
    print()

    # Get all bowl games
    bowl_games = db.query(Game).filter(
        Game.season == season,
        Game.game_type == 'bowl'
    ).order_by(Game.week, Game.postseason_name).all()

    print(f"Total bowl games: {len(bowl_games)}")
    print()

    if not bowl_games:
        print("⚠️  No bowl games found")
        db.close()
        return 1

    # Display each bowl game
    print(f"{'Week':<6} {'Bowl Name':<40} {'Matchup':<50} {'Score':<12} {'Processed':<10}")
    print("-"*120)

    for game in bowl_games:
        matchup = f"{game.away_team.name} @ {game.home_team.name}"

        if game.is_processed:
            score = f"{game.away_score}-{game.home_score}"
            processed = "Yes"
        else:
            score = "TBD"
            processed = "No"

        bowl_name = game.postseason_name or "Unknown Bowl"

        print(f"{game.week:<6} {bowl_name:<40} {matchup:<50} {score:<12} {processed:<10}")

    print()

    # Summary statistics
    processed_count = sum(1 for g in bowl_games if g.is_processed)
    unprocessed_count = len(bowl_games) - processed_count

    with_names = sum(1 for g in bowl_games if g.postseason_name)
    without_names = len(bowl_games) - with_names

    print("Summary:")
    print(f"  Processed: {processed_count}")
    print(f"  Unprocessed: {unprocessed_count}")
    print(f"  With bowl names: {with_names}")
    print(f"  Without names: {without_names}")
    print(f"  Total: {len(bowl_games)}")
    print()

    # Show unique bowl names
    bowl_names = set(g.postseason_name for g in bowl_games if g.postseason_name)
    print(f"Unique bowl names ({len(bowl_names)}):")
    for name in sorted(bowl_names):
        print(f"  - {name}")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    import sys
    season = 2024
    if len(sys.argv) > 1:
        season = int(sys.argv[1])

    sys.exit(check_bowl_games(season))
