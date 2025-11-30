#!/usr/bin/env python3
"""
Fix 2025 team records - Story 24.1

Problem: Teams table has cumulative records across seasons
Solution: Recalculate wins/losses from 2025 games only
"""

from database import SessionLocal
from models import Team, Game
import sys


def fix_2025_records():
    """Recalculate team records for 2025 season"""

    db = SessionLocal()
    season = 2025

    print("="*80)
    print("FIX 2025 TEAM RECORDS - Story 24.1")
    print("="*80)
    print()
    print("⚠️  WARNING: This will update all team win/loss records")
    print()

    # Get all teams
    teams = db.query(Team).all()

    print(f"Processing {len(teams)} teams...")
    print()

    updated_count = 0
    changes = []

    for team in teams:
        # Get all 2025 games for this team
        games = db.query(Game).filter(
            ((Game.home_team_id == team.id) | (Game.away_team_id == team.id)),
            Game.season == season,
            Game.is_processed == True
        ).all()

        wins = 0
        losses = 0

        for game in games:
            # Determine if team won or lost
            is_home = game.home_team_id == team.id

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

        # Check if record changed
        old_record = f"{team.wins}-{team.losses}"
        new_record = f"{wins}-{losses}"

        if team.wins != wins or team.losses != losses:
            changes.append({
                'team': team.name,
                'old': old_record,
                'new': new_record,
                'games': len(games)
            })
            team.wins = wins
            team.losses = losses
            updated_count += 1

    # Show changes before committing
    if changes:
        print("Changes to be made:")
        print()
        for change in changes:
            print(f"  {change['team']:30} {change['old']:8} → {change['new']:8} ({change['games']} games)")

        print()
        print(f"Total teams to update: {updated_count}")
        print()

    # Commit changes
    db.commit()

    print()
    print("="*80)
    print(f"✓ Updated {updated_count} teams")
    print("="*80)
    print()

    # Verification
    print("VERIFICATION:")
    print()

    # Check for impossible records
    max_week_game = db.query(Game).filter(
        Game.season == season,
        Game.is_processed == True
    ).order_by(Game.week.desc()).first()

    if max_week_game:
        max_week = max_week_game.week
        print(f"Max week with games: {max_week}")
        print()

        teams_with_issues = db.query(Team).filter(
            (Team.wins + Team.losses) > max_week
        ).all()

        if teams_with_issues:
            print("⚠️  WARNING: Teams with impossible records:")
            for team in teams_with_issues:
                print(f"  - {team.name}: {team.wins}-{team.losses} (>{max_week} games)")
        else:
            print("✓ All teams have valid records (<= max week)")
    else:
        print("No processed games found for season", season)

    print()

    # Show top 10
    print("Top 10 teams by wins:")
    top_teams = db.query(Team).order_by(Team.wins.desc()).limit(10).all()
    for i, team in enumerate(top_teams, 1):
        total_games = team.wins + team.losses
        print(f"  {i:2}. {team.name:30} {team.wins:2}-{team.losses:2} ({total_games} games)")

    print()

    db.close()

    return 0


if __name__ == "__main__":
    print()
    response = input("Continue with fixing 2025 records? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted")
        sys.exit(1)

    print()
    sys.exit(fix_2025_records())
