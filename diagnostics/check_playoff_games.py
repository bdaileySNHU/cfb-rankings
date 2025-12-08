#!/usr/bin/env python3
"""
Check playoff games imported in database
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


from src.models.database import SessionLocal
from src.models.models import Game


def check_playoff_games(season=2024):
    """Check all playoff games for a season"""

    db = SessionLocal()

    print("=" * 80)
    print(f"CFP PLAYOFF GAMES - {season}")
    print("=" * 80)
    print()

    # Get all playoff games
    playoff_games = (
        db.query(Game)
        .filter(Game.season == season, Game.game_type == "playoff")
        .order_by(Game.week, Game.postseason_name)
        .all()
    )

    print(f"Total playoff games: {len(playoff_games)}")
    print()

    if not playoff_games:
        print("⚠️  No playoff games found")
        db.close()
        return 1

    # Display each playoff game
    print(f"{'Week':<6} {'Round':<45} {'Matchup':<50} {'Score':<12} {'Processed':<10}")
    print("-" * 125)

    for game in playoff_games:
        matchup = f"{game.away_team.name} vs {game.home_team.name}"

        if game.is_processed:
            score = f"{game.away_score}-{game.home_score}"
            processed = "Yes"
            # Determine winner
            if game.away_score > game.home_score:
                winner_mark = "✓"
                matchup = f"{game.away_team.name} {winner_mark} vs {game.home_team.name}"
            else:
                winner_mark = "✓"
                matchup = f"{game.away_team.name} vs {game.home_team.name} {winner_mark}"
        else:
            score = "TBD"
            processed = "No"

        playoff_round = game.postseason_name or "Unknown Round"

        print(f"{game.week:<6} {playoff_round:<45} {matchup:<50} {score:<12} {processed:<10}")

    print()

    # Summary statistics
    processed_count = sum(1 for g in playoff_games if g.is_processed)
    unprocessed_count = len(playoff_games) - processed_count

    with_names = sum(1 for g in playoff_games if g.postseason_name)
    without_names = len(playoff_games) - with_names

    print("Summary:")
    print(f"  Processed: {processed_count}")
    print(f"  Unprocessed: {unprocessed_count}")
    print(f"  With round info: {with_names}")
    print(f"  Without round info: {without_names}")
    print(f"  Total: {len(playoff_games)}")
    print()

    # Show unique playoff rounds
    playoff_rounds = {}
    for g in playoff_games:
        if g.postseason_name:
            round_type = g.postseason_name.split(" - ")[
                0
            ]  # e.g., "CFP Semifinal" from "CFP Semifinal - Orange Bowl"
            playoff_rounds[round_type] = playoff_rounds.get(round_type, 0) + 1

    print(f"Games by Round:")
    for round_name in sorted(playoff_rounds.keys()):
        print(f"  {round_name}: {playoff_rounds[round_name]} games")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    import sys

    season = 2024
    if len(sys.argv) > 1:
        season = int(sys.argv[1])

    sys.exit(check_playoff_games(season))
