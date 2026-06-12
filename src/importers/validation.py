"""Import validation and duplicate detection (EPIC-008 Story 003)."""

from src.integrations.cfbd_client import CFBDClient
from src.models.models import Game, Team


def validate_api_connection(cfbd: CFBDClient, year: int) -> bool:
    """
    Test CFBD API connectivity and authentication.

    Args:
        cfbd: CFBD client instance
        year: Year to test with

    Returns:
        bool: True if API accessible, False otherwise
    """
    try:
        print("Validating CFBD API connection...")
        teams = cfbd.get_teams(year)
        if teams and len(teams) > 0:
            print(f"✓ API Connection OK ({len(teams)} teams found)")
            return True
        else:
            print("✗ API Connection Failed: No teams returned")
            return False
    except Exception as e:
        print(f"✗ API Connection Failed: {e}")
        return False


def get_week_statistics(cfbd: CFBDClient, year: int, week: int) -> dict:
    """
    Get statistics about games available for a given week.

    Args:
        cfbd: CFBD client instance
        year: Season year
        week: Week number

    Returns:
        dict: Statistics including total games, completed games
    """
    games = cfbd.get_games(year, week=week)
    if not games:
        return {"total": 0, "completed": 0, "scheduled": 0}

    completed = sum(
        1 for g in games if g.get("homePoints") is not None and g.get("awayPoints") is not None
    )
    total = len(games)

    return {"total": total, "completed": completed, "scheduled": total - completed}


def check_for_duplicates(db) -> list:
    """
    Check for duplicate games in the database.

    A duplicate is defined as two games with the same:
    - home_team_id
    - away_team_id
    - week
    - season

    Args:
        db: Database session

    Returns:
        list: List of duplicate game groups with details
    """
    from sqlalchemy import func

    # Query for duplicate games
    duplicates = (
        db.query(
            Game.home_team_id,
            Game.away_team_id,
            Game.week,
            Game.season,
            func.count(Game.id).label("count"),
        )
        .group_by(Game.home_team_id, Game.away_team_id, Game.week, Game.season)
        .having(func.count(Game.id) > 1)
        .all()
    )

    if not duplicates:
        return []

    # Get details for each duplicate group
    duplicate_details = []
    for dup in duplicates:
        games = (
            db.query(Game)
            .filter(
                Game.home_team_id == dup.home_team_id,
                Game.away_team_id == dup.away_team_id,
                Game.week == dup.week,
                Game.season == dup.season,
            )
            .all()
        )

        home_team = db.query(Team).filter(Team.id == dup.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == dup.away_team_id).first()

        duplicate_details.append(
            {
                "home_team": home_team.name if home_team else "Unknown",
                "away_team": away_team.name if away_team else "Unknown",
                "week": dup.week,
                "season": dup.season,
                "count": dup.count,
                "game_ids": [g.id for g in games],
                "scores": [(g.home_score, g.away_score) for g in games],
            }
        )

    return duplicate_details


def print_duplicate_report(duplicates: list):
    """Print a formatted report of duplicate games."""
    if not duplicates:
        print("✓ No duplicate games found")
        return

    print("\n" + "=" * 80)
    print("⚠ WARNING: DUPLICATE GAMES DETECTED")
    print("=" * 80)

    for dup in duplicates:
        print(f"\n{dup['away_team']} @ {dup['home_team']} (Week {dup['week']}, {dup['season']})")
        print(f"  Found {dup['count']} duplicate records:")
        for game_id, scores in zip(dup["game_ids"], dup["scores"]):
            print(f"    - Game ID {game_id}: {scores[1]}-{scores[0]}")

    print("\nTo fix duplicates manually:")
    print("  sqlite3 cfb_rankings.db")
    print("  DELETE FROM games WHERE id IN (...);")
    print("=" * 80)


def validate_import_results(db, import_stats: dict, year: int):
    """
    Validate import results and print summary.

    Args:
        db: Database session
        import_stats: Dictionary with import counts
        year: Season year
    """
    print("\n" + "=" * 80)
    print("IMPORT VALIDATION")
    print("=" * 80)

    # Check for duplicates
    duplicates = check_for_duplicates(db)
    print_duplicate_report(duplicates)

    # Verify game counts
    total_games = db.query(Game).filter(Game.season == year).count()
    future_games = (
        db.query(Game)
        .filter(Game.season == year, Game.home_score == 0, Game.away_score == 0)
        .count()
    )
    completed_games = total_games - future_games

    print(f"\nDatabase Game Counts (Season {year}):")
    print(f"  Total Games: {total_games}")
    print(f"  Completed Games: {completed_games}")
    print(f"  Future Games: {future_games}")

    # Verify against import stats
    print(f"\nImport Stats:")
    print(f"  FBS Games Imported: {import_stats.get('imported', 0)}")
    print(f"  FCS Games Imported: {import_stats.get('fcs_imported', 0)}")
    print(f"  Future Games Imported: {import_stats.get('future_imported', 0)}")
    print(f"  Games Updated: {import_stats.get('games_updated', 0)}")
    print(f"  Games Skipped: {import_stats.get('skipped', 0)}")

    # Warnings for anomalies
    if duplicates:
        print("\n⚠ WARNING: Duplicates detected (see above)")

    if total_games == 0:
        print("\n⚠ WARNING: No games in database!")

    if future_games > 300:
        print(f"\n⚠ WARNING: Unusually high future game count ({future_games})")

    print("=" * 80)
