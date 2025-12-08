"""
Diagnose missing games for specific teams
"""
from dotenv import load_dotenv

load_dotenv()

import os

from cfbd_client import CFBDClient


def check_team_games(team_name: str, year: int = 2025, max_week: int = 6):
    """Check what games are available for a specific team"""
    api_key = os.getenv('CFBD_API_KEY')
    if not api_key:
        print("ERROR: No CFBD_API_KEY found in environment")
        return

    cfbd = CFBDClient(api_key)

    print(f"\n{'='*80}")
    print(f"GAMES FOR {team_name} - {year} Season")
    print(f"{'='*80}\n")

    all_team_games = []

    for week in range(1, max_week + 1):
        games = cfbd.get_games(year, week=week)
        if not games:
            continue

        # Find games involving this team
        team_games = [
            g for g in games
            if g.get('homeTeam') == team_name or g.get('awayTeam') == team_name
        ]

        for game in team_games:
            home = game.get('homeTeam')
            away = game.get('awayTeam')
            home_score = game.get('homePoints')
            away_score = game.get('awayPoints')

            opponent = away if home == team_name else home
            location = "vs" if home == team_name else "@"

            if home_score is None or away_score is None:
                status = "SCHEDULED (No score)"
            else:
                status = f"FINAL: {home} {home_score}, {away} {away_score}"

            all_team_games.append({
                'week': week,
                'opponent': opponent,
                'location': location,
                'status': status,
                'completed': home_score is not None and away_score is not None
            })

            print(f"Week {week}: {location} {opponent}")
            print(f"  Status: {status}")
            print()

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total games found: {len(all_team_games)}")
    print(f"Completed games: {sum(1 for g in all_team_games if g['completed'])}")
    print(f"Scheduled games: {sum(1 for g in all_team_games if not g['completed'])}")

    # Check for FCS opponents
    print(f"\nNOTE: If a week is missing, the opponent might be FCS (not FBS)")
    print(f"FCS games are intentionally excluded from the rankings system")


if __name__ == "__main__":
    # Check teams that are missing games
    teams_to_check = [
        'Ohio State',
        'Georgia',
        'Alabama',
        'Oregon',
        'Texas'
    ]

    for team in teams_to_check:
        check_team_games(team, year=2025, max_week=6)
        print("\n" * 2)
