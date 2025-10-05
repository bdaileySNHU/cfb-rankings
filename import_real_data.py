"""
Import Real College Football Data
Fetches data from CollegeFootballData API and populates the database
"""

from database import SessionLocal, reset_db
from models import Team, Game, Season, ConferenceType
from ranking_service import RankingService
from cfbd_client import CFBDClient
from datetime import datetime
import sys


# Conference mapping from CFBD to our system
CONFERENCE_MAP = {
    'SEC': ConferenceType.POWER_5,
    'Big Ten': ConferenceType.POWER_5,
    'ACC': ConferenceType.POWER_5,
    'Big 12': ConferenceType.POWER_5,
    'Pac-12': ConferenceType.POWER_5,
    'American Athletic': ConferenceType.GROUP_5,
    'Mountain West': ConferenceType.GROUP_5,
    'Conference USA': ConferenceType.GROUP_5,
    'Mid-American': ConferenceType.GROUP_5,
    'Sun Belt': ConferenceType.GROUP_5,
    'FBS Independents': ConferenceType.GROUP_5,
}


def import_teams(cfbd: CFBDClient, db, year: int = 2025):
    """Import all FBS teams"""
    print(f"\nImporting FBS teams for {year}...")

    # Fetch teams from CFBD
    teams_data = cfbd.get_teams(year)
    if not teams_data:
        print("✗ Failed to fetch teams from CFBD API")
        return {}

    # Fetch recruiting data
    print("Fetching recruiting rankings...")
    recruiting_data = cfbd.get_recruiting_rankings(year) or []
    recruiting_map = {r['team']: r['rank'] for r in recruiting_data if 'team' in r and 'rank' in r}

    # Fetch talent ratings
    print("Fetching talent composite...")
    talent_data = cfbd.get_team_talent(year) or []
    talent_map = {t['school']: t['talent'] for t in talent_data if 'school' in t and 'talent' in t}

    # Fetch returning production
    print("Fetching returning production...")
    returning_data = cfbd.get_returning_production(year) or []
    returning_map = {}
    for r in returning_data:
        if 'team' in r and 'returningProduction' in r:
            team = r['team']
            prod = r['returningProduction']
            # Average the returning production percentage
            if isinstance(prod, dict):
                values = [v for v in prod.values() if isinstance(v, (int, float))]
                returning_map[team] = sum(values) / len(values) / 100 if values else 0.5
            elif isinstance(prod, (int, float)):
                returning_map[team] = prod / 100

    team_objects = {}
    ranking_service = RankingService(db)

    for team_data in teams_data:
        team_name = team_data['school']
        conference_name = team_data.get('conference', 'FBS Independents')

        # Map conference
        conference = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)

        # Get preseason data
        recruiting_rank = recruiting_map.get(team_name, 999)
        transfer_rank = 999  # CFBD doesn't have transfer portal rankings easily accessible
        returning_prod = returning_map.get(team_name, 0.5)

        # Create team
        team = Team(
            name=team_name,
            conference=conference,
            recruiting_rank=recruiting_rank,
            transfer_rank=transfer_rank,
            returning_production=returning_prod
        )

        ranking_service.initialize_team_rating(team)
        db.add(team)
        team_objects[team_name] = team

        print(f"  Added: {team_name} ({conference.value}) - Recruiting: #{recruiting_rank}, Returning: {returning_prod*100:.0f}%")

    db.commit()
    print(f"\n✓ Imported {len(team_objects)} teams")
    return team_objects


def import_games(cfbd: CFBDClient, db, team_objects: dict, year: int = 2025, max_week: int = None):
    """Import games for the season"""
    print(f"\nImporting games for {year}...")

    ranking_service = RankingService(db)

    # Determine which weeks to import
    weeks = range(1, (max_week or 15) + 1)

    total_imported = 0

    for week in weeks:
        print(f"\nWeek {week}...")
        games_data = cfbd.get_games(year, week=week)

        if not games_data:
            print(f"  No games found for week {week}")
            continue

        week_count = 0

        for game_data in games_data:
            # API uses camelCase
            home_team_name = game_data.get('homeTeam')
            away_team_name = game_data.get('awayTeam')
            home_score = game_data.get('homePoints')
            away_score = game_data.get('awayPoints')

            # Skip if game not completed
            if home_score is None or away_score is None:
                continue

            # Skip if teams not in our database (filters out FCS games)
            if home_team_name not in team_objects or away_team_name not in team_objects:
                continue

            home_team = team_objects[home_team_name]
            away_team = team_objects[away_team_name]

            # Check if game already exists
            existing = db.query(Game).filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.week == week,
                Game.season == year
            ).first()

            if existing:
                continue

            # Create game
            is_neutral = game_data.get('neutralSite', False)

            game = Game(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=home_score,
                away_score=away_score,
                week=week,
                season=year,
                is_neutral_site=is_neutral,
                game_date=datetime.now()  # CFBD has date but in different format
            )

            db.add(game)
            db.commit()
            db.refresh(game)

            # Process game to update rankings
            result = ranking_service.process_game(game)

            winner = result['winner_name']
            loser = result['loser_name']
            score = result['score']

            print(f"    {winner} defeats {loser} {score}")
            week_count += 1
            total_imported += 1

        print(f"  Imported {week_count} games for week {week}")

    print(f"\n✓ Imported {total_imported} total games")
    return total_imported


def main():
    """Main import function"""
    print("="*80)
    print("COLLEGE FOOTBALL DATA IMPORT")
    print("="*80)
    print()
    print("This script imports real college football data from CollegeFootballData.com")
    print()

    # Check for API key
    import os
    api_key = os.getenv('CFBD_API_KEY')

    if not api_key:
        print("ERROR: No API key found!")
        print()
        print("To get real data:")
        print("1. Visit: https://collegefootballdata.com/key")
        print("2. Sign up for a free API key")
        print("3. Set environment variable:")
        print("   export CFBD_API_KEY='your-key-here'")
        print()
        print("Then run this script again.")
        sys.exit(1)

    # Initialize
    cfbd = CFBDClient(api_key)
    db = SessionLocal()

    # Confirm reset
    print("WARNING: This will reset your database and replace all data!")
    response = input("Continue? (yes/no): ")

    if response.lower() != 'yes':
        print("Cancelled.")
        return

    # Reset database
    print("\nResetting database...")
    reset_db()

    # Create season
    print("Creating 2025 season...")
    season = Season(year=2025, current_week=0, is_active=True)
    db.add(season)
    db.commit()

    # Import teams
    team_objects = import_teams(cfbd, db, year=2025)

    if not team_objects:
        print("\nFailed to import teams. Check your API key.")
        return

    # Import games
    print("\nHow many weeks of games would you like to import?")
    print("(The 2025 season is currently through Week 6)")
    try:
        max_week = int(input("Enter max week (1-6): "))
        max_week = min(max(max_week, 1), 6)
    except:
        print("Invalid input, using Week 1 only")
        max_week = 1

    total_games = import_games(cfbd, db, team_objects, year=2025, max_week=max_week)

    # Update season current week
    season.current_week = max_week
    db.commit()

    # Save rankings
    print("\nSaving final rankings...")
    ranking_service = RankingService(db)
    for week in range(1, max_week + 1):
        ranking_service.save_weekly_rankings(2025, week)

    # Show final rankings
    print("\n" + "="*80)
    print("FINAL RANKINGS")
    print("="*80)

    rankings = ranking_service.get_current_rankings(2025, limit=25)
    print(f"\n{'RANK':<6} {'TEAM':<30} {'RATING':<10} {'RECORD':<10} {'SOS':<10}")
    print("-"*80)

    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        print(f"{r['rank']:<6} {r['team_name']:<30} {r['elo_rating']:<10.2f} {record:<10} {r['sos']:<10.2f}")

    print()
    print("="*80)
    print(f"✓ Import Complete!")
    print(f"  - {len(team_objects)} teams imported")
    print(f"  - {total_games} games processed")
    print(f"  - Rankings calculated through Week {max_week}")
    print("="*80)

    db.close()


if __name__ == "__main__":
    main()
