#!/usr/bin/env python3
"""
Fix playoff game week numbers for proper schedule ordering

Updates existing playoff games in database to use correct week numbers
based on their playoff round.
"""

from src.models.database import SessionLocal
from src.models.models import Game


def fix_playoff_weeks(season=2024):
    """Update playoff game weeks based on round"""

    db = SessionLocal()

    print("="*80)
    print(f"FIX PLAYOFF GAME WEEKS - {season}")
    print("="*80)
    print()

    # Get all playoff games
    playoff_games = db.query(Game).filter(
        Game.season == season,
        Game.game_type == 'playoff'
    ).all()

    if not playoff_games:
        print("No playoff games found")
        db.close()
        return

    print(f"Found {len(playoff_games)} playoff games")
    print()

    updated = 0

    for game in playoff_games:
        if not game.postseason_name:
            print(f"⚠️  Skipping game {game.id}: No postseason_name")
            continue

        name_lower = game.postseason_name.lower()
        old_week = game.week
        new_week = old_week

        # Assign week based on playoff round
        if 'national championship' in name_lower or 'championship' in name_lower:
            new_week = 19 if season >= 2024 else 18
        elif 'semifinal' in name_lower:
            new_week = 18 if season >= 2024 else 17
        elif 'quarterfinal' in name_lower:
            new_week = 17
        elif 'first round' in name_lower:
            new_week = 16

        if new_week != old_week:
            game.week = new_week
            updated += 1
            print(f"✓ {game.postseason_name}")
            print(f"  {game.away_team.name} vs {game.home_team.name}")
            print(f"  Week {old_week} → Week {new_week}")
            print()

    if updated > 0:
        db.commit()
        print()
        print(f"✅ Updated {updated} playoff games")
    else:
        print("✓ All playoff games already have correct week numbers")

    print()

    # Show final distribution
    print("Playoff games by week:")
    weeks = {}
    for game in playoff_games:
        weeks[game.week] = weeks.get(game.week, 0) + 1

    for week in sorted(weeks.keys()):
        print(f"  Week {week}: {weeks[week]} games")

    print()

    db.close()


if __name__ == "__main__":
    import sys
    season = 2024
    if len(sys.argv) > 1:
        season = int(sys.argv[1])

    fix_playoff_weeks(season)
