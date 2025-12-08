"""
Seed script to populate database with sample teams and games
"""

from datetime import datetime

from database import SessionLocal, init_db, reset_db
from models import ConferenceType, Game, Season, Team
from ranking_service import RankingService


def seed_database():
    """Populate database with sample data"""
    print("Resetting database...")
    reset_db()

    db = SessionLocal()
    ranking_service = RankingService(db)

    print("Creating 2024 season...")
    season = Season(year=2024, current_week=2, is_active=True)
    db.add(season)
    db.commit()

    print("Adding teams...")

    # Elite P5 Teams
    teams_data = [
        # Name, Conference, Recruiting, Transfer, Returning
        ("Georgia", ConferenceType.POWER_5, 3, 5, 0.70),
        ("Alabama", ConferenceType.POWER_5, 5, 8, 0.65),
        ("Ohio State", ConferenceType.POWER_5, 2, 3, 0.60),
        ("Texas", ConferenceType.POWER_5, 8, 12, 0.75),
        ("Oregon", ConferenceType.POWER_5, 12, 7, 0.68),
        ("Michigan", ConferenceType.POWER_5, 15, 10, 0.72),
        ("Penn State", ConferenceType.POWER_5, 18, 20, 0.65),
        ("Florida State", ConferenceType.POWER_5, 10, 15, 0.55),
        ("Notre Dame", ConferenceType.POWER_5, 7, 18, 0.62),
        ("USC", ConferenceType.POWER_5, 6, 6, 0.58),

        # Mid-tier P5
        ("Wisconsin", ConferenceType.POWER_5, 35, 40, 0.72),
        ("Iowa", ConferenceType.POWER_5, 45, 55, 0.80),
        ("Michigan State", ConferenceType.POWER_5, 50, 48, 0.55),
        ("Nebraska", ConferenceType.POWER_5, 38, 35, 0.60),
        ("Minnesota", ConferenceType.POWER_5, 42, 45, 0.68),
        ("Oklahoma", ConferenceType.POWER_5, 22, 25, 0.50),
        ("LSU", ConferenceType.POWER_5, 9, 14, 0.58),
        ("Clemson", ConferenceType.POWER_5, 11, 16, 0.65),
        ("Miami", ConferenceType.POWER_5, 14, 11, 0.60),
        ("Florida", ConferenceType.POWER_5, 16, 22, 0.52),

        # Strong G5
        ("Boise State", ConferenceType.GROUP_5, 85, 65, 0.82),
        ("Memphis", ConferenceType.GROUP_5, 90, 75, 0.68),
        ("UCF", ConferenceType.GROUP_5, 70, 60, 0.70),
        ("Cincinnati", ConferenceType.GROUP_5, 75, 70, 0.75),
        ("Houston", ConferenceType.GROUP_5, 65, 55, 0.65),

        # Average G5
        ("Toledo", ConferenceType.GROUP_5, 110, 95, 0.70),
        ("UTSA", ConferenceType.GROUP_5, 105, 88, 0.65),
        ("App State", ConferenceType.GROUP_5, 95, 85, 0.72),
        ("Louisiana", ConferenceType.GROUP_5, 100, 92, 0.68),
        ("Tulane", ConferenceType.GROUP_5, 88, 78, 0.73),

        # FCS
        ("North Dakota State", ConferenceType.FCS, 999, 999, 0.85),
        ("Montana", ConferenceType.FCS, 999, 999, 0.78),
        ("South Dakota State", ConferenceType.FCS, 999, 999, 0.80),
    ]

    team_objects = {}
    for name, conf, recruiting, transfer, returning in teams_data:
        team = Team(
            name=name,
            conference=conf,
            recruiting_rank=recruiting,
            transfer_rank=transfer,
            returning_production=returning
        )
        ranking_service.initialize_team_rating(team)
        db.add(team)
        team_objects[name] = team

    db.commit()
    print(f"Added {len(team_objects)} teams")

    # Refresh teams to get IDs
    for team in team_objects.values():
        db.refresh(team)

    print("Adding Week 1 games...")
    week1_games = [
        # Winner, Loser, Winner Score, Loser Score, Is Neutral
        ("Georgia", "Clemson", 34, 3, True),
        ("Ohio State", "Iowa", 35, 7, False),
        ("Alabama", "Wisconsin", 42, 10, True),
        ("Texas", "Michigan", 31, 12, False),
        ("Oregon", "Boise State", 37, 34, False),
        ("Notre Dame", "Nebraska", 23, 13, True),
        ("USC", "LSU", 27, 20, True),
        ("Penn State", "Minnesota", 34, 12, False),
        ("Florida State", "Oklahoma", 24, 21, True),
        ("Miami", "Florida", 41, 17, True),
        ("UCF", "Toledo", 49, 7, False),
        ("Memphis", "App State", 40, 14, False),
        ("Cincinnati", "UTSA", 28, 14, False),
    ]

    for winner_name, loser_name, winner_score, loser_score, is_neutral in week1_games:
        winner = team_objects[winner_name]
        loser = team_objects[loser_name]

        game = Game(
            home_team_id=winner.id,
            away_team_id=loser.id,
            home_score=winner_score,
            away_score=loser_score,
            week=1,
            season=2024,
            is_neutral_site=is_neutral,
            game_date=datetime(2024, 9, 1)
        )
        db.add(game)
        db.commit()
        db.refresh(game)

        # Process game
        result = ranking_service.process_game(game)
        print(f"  {result['winner_name']} defeats {result['loser_name']} {result['score']}")

    print("\nAdding Week 2 games...")
    week2_games = [
        # Big matchups
        ("Georgia", "Alabama", 27, 24, True),
        ("Ohio State", "Texas", 31, 28, False),
        ("Oregon", "Michigan", 38, 17, False),
        ("Notre Dame", "USC", 24, 20, False),

        # Mid-tier games
        ("Penn State", "Iowa", 31, 0, False),
        ("Wisconsin", "Michigan State", 24, 21, False),
        ("Miami", "Florida State", 36, 14, False),
        ("LSU", "Nebraska", 41, 14, False),

        # G5 action
        ("Memphis", "Louisiana", 35, 21, False),
        ("Boise State", "Tulane", 37, 34, False),
        ("UCF", "Houston", 45, 14, False),
        ("Cincinnati", "App State", 27, 16, False),
    ]

    for winner_name, loser_name, winner_score, loser_score, is_neutral in week2_games:
        winner = team_objects[winner_name]
        loser = team_objects[loser_name]

        game = Game(
            home_team_id=winner.id,
            away_team_id=loser.id,
            home_score=winner_score,
            away_score=loser_score,
            week=2,
            season=2024,
            is_neutral_site=is_neutral,
            game_date=datetime(2024, 9, 8)
        )
        db.add(game)
        db.commit()
        db.refresh(game)

        # Process game
        result = ranking_service.process_game(game)
        print(f"  {result['winner_name']} defeats {result['loser_name']} {result['score']}")

    # Save weekly rankings
    print("\nSaving rankings history...")
    ranking_service.save_weekly_rankings(2024, 1)
    ranking_service.save_weekly_rankings(2024, 2)

    # Print final rankings
    print("\n" + "="*80)
    print("FINAL RANKINGS AFTER WEEK 2")
    print("="*80)
    rankings = ranking_service.get_current_rankings(2024, limit=25)

    print(f"{'RANK':<6} {'TEAM':<25} {'RATING':<10} {'RECORD':<10} {'CONF':<6} {'SOS':<10}")
    print("-"*80)
    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        print(f"{r['rank']:<6} {r['team_name']:<25} {r['elo_rating']:<10.2f} {record:<10} "
              f"{r['conference'].value:<6} {r['sos']:<10.2f}")

    print("\nDatabase seeded successfully!")
    db.close()


if __name__ == "__main__":
    seed_database()
