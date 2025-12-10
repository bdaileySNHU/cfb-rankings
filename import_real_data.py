"""
Import Real College Football Data
Fetches data from CollegeFootballData API and populates the database
"""

from dotenv import load_dotenv

# Load environment variables from .env file (if accessible)
try:
    load_dotenv()
except (PermissionError, FileNotFoundError):
    # .env file not accessible or doesn't exist
    # Will fall back to system environment variables
    pass

import argparse
import sys
from datetime import datetime

from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal, reset_db
from src.models.models import APPollRanking, ConferenceType, Game, Season, Team
from src.core.ranking_service import RankingService, create_and_store_prediction

# Conference mapping from CFBD to our system
CONFERENCE_MAP = {
    "SEC": ConferenceType.POWER_5,
    "Big Ten": ConferenceType.POWER_5,
    "ACC": ConferenceType.POWER_5,
    "Big 12": ConferenceType.POWER_5,
    "Pac-12": ConferenceType.POWER_5,
    "American Athletic": ConferenceType.GROUP_5,
    "Mountain West": ConferenceType.GROUP_5,
    "Conference USA": ConferenceType.GROUP_5,
    "Mid-American": ConferenceType.GROUP_5,
    "Sun Belt": ConferenceType.GROUP_5,
    "FBS Independents": ConferenceType.GROUP_5,
}


def parse_game_date(game_data: dict) -> datetime:
    """
    Parse game date from CFBD API response.

    EPIC-008: CFBD provides dates in ISO 8601 format:
    "start_date": "2025-09-06T19:00:00.000Z"

    Args:
        game_data: Game data dictionary from CFBD API

    Returns:
        datetime: Parsed game date, or None if not available

    Note:
        Returns None instead of datetime.now() when date is unavailable.
        This prevents showing incorrect import timestamps as game dates.
        Frontend will display "TBD" for games without scheduled dates.
    """
    date_str = game_data.get("start_date")
    if date_str:
        try:
            # CFBD uses ISO 8601 format with Z suffix (UTC)
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass
    # Return None for unscheduled games instead of showing wrong date
    return None


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


def import_teams(cfbd: CFBDClient, db, year: int):
    """Import all FBS teams (or reuse existing teams in incremental mode)"""
    print(f"\nImporting FBS teams for {year}...")

    # Fetch teams from CFBD
    teams_data = cfbd.get_teams(year)
    if not teams_data:
        print("✗ Failed to fetch teams from CFBD API")
        return {}

    # Fetch recruiting data
    print("Fetching recruiting rankings...")
    recruiting_data = cfbd.get_recruiting_rankings(year) or []
    recruiting_map = {r["team"]: r["rank"] for r in recruiting_data if "team" in r and "rank" in r}

    # Fetch talent ratings
    print("Fetching talent composite...")
    talent_data = cfbd.get_team_talent(year) or []
    talent_map = {t["school"]: t["talent"] for t in talent_data if "school" in t and "talent" in t}

    # Fetch returning production (EPIC-025)
    # API returns percentPPA (decimal 0.0-1.0) for overall returning production
    print("Fetching returning production...")
    returning_data = cfbd.get_returning_production(year) or []
    returning_map = {}
    for r in returning_data:
        if "team" in r and "percentPPA" in r:
            team = r["team"]
            prod = r["percentPPA"]
            # Validate and store (API returns decimal, no conversion needed)
            if isinstance(prod, (int, float)) and 0.0 <= prod <= 1.0:
                returning_map[team] = prod
            else:
                print(f"  Warning: Invalid returning production for {team}: {prod}")

    print(f"  Loaded returning production for {len(returning_map)} teams")

    # EPIC-026: Fetch and calculate transfer portal rankings
    print("Fetching transfer portal data...")
    transfer_data = cfbd.get_transfer_portal(year) or []
    print(f"  Retrieved {len(transfer_data)} transfers")

    print("Calculating transfer portal rankings...")
    from transfer_portal_service import TransferPortalService

    tp_service = TransferPortalService()
    team_scores, team_ranks = tp_service.get_team_stats(transfer_data)
    print(f"  Calculated rankings for {len(team_ranks)} teams")

    team_objects = {}
    ranking_service = RankingService(db)
    teams_created = 0
    teams_reused = 0

    for team_data in teams_data:
        team_name = team_data["school"]
        conference_name = team_data.get("conference", "FBS Independents")

        # Check if team already exists (incremental mode)
        existing_team = db.query(Team).filter(Team.name == team_name).first()

        if existing_team:
            # Reuse existing team, but update preseason data
            recruiting_rank = recruiting_map.get(team_name, 999)
            returning_prod = returning_map.get(team_name, 0.5)

            # EPIC-026: Get transfer portal data
            transfer_portal_rank = team_ranks.get(team_name, 999)
            transfer_portal_points = team_scores.get(team_name, {}).get("points", 0)
            transfer_portal_count = team_scores.get(team_name, {}).get("count", 0)

            # Update preseason factors
            existing_team.recruiting_rank = recruiting_rank
            existing_team.returning_production = returning_prod
            existing_team.transfer_portal_rank = transfer_portal_rank
            existing_team.transfer_portal_points = transfer_portal_points
            existing_team.transfer_count = transfer_portal_count

            team_objects[team_name] = existing_team
            teams_reused += 1
        else:
            # Create new team
            # Map conference to tier (P5/G5/FCS)
            conference_tier = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)

            # Special case: Notre Dame is P5 Independent
            if team_name == "Notre Dame":
                conference_tier = ConferenceType.POWER_5

            # Get preseason data
            recruiting_rank = recruiting_map.get(team_name, 999)
            transfer_rank = 999  # DEPRECATED: Use transfer_portal_rank instead
            returning_prod = returning_map.get(team_name, 0.5)

            # EPIC-026: Get transfer portal data
            transfer_portal_rank = team_ranks.get(team_name, 999)
            transfer_portal_points = team_scores.get(team_name, {}).get("points", 0)
            transfer_portal_count = team_scores.get(team_name, {}).get("count", 0)

            # EPIC-012: Create team with BOTH conference tier and name
            team = Team(
                name=team_name,
                conference=conference_tier,  # P5/G5/FCS (for logic)
                conference_name=conference_name,  # "Big Ten", "SEC", etc. (for display)
                recruiting_rank=recruiting_rank,
                transfer_rank=transfer_rank,
                returning_production=returning_prod,
                transfer_portal_rank=transfer_portal_rank,
                transfer_portal_points=transfer_portal_points,
                transfer_count=transfer_portal_count,
            )

            ranking_service.initialize_team_rating(team)
            db.add(team)
            team_objects[team_name] = team
            teams_created += 1

            print(
                f"  Added: {team_name} - {conference_name} ({conference_tier.value}) - Recruiting: #{recruiting_rank}, Returning: {returning_prod*100:.0f}%, Portal: #{transfer_portal_rank}"
            )

    db.commit()

    if teams_reused > 0:
        print(f"\n✓ Reused {teams_reused} existing teams, created {teams_created} new teams")
    else:
        print(f"\n✓ Imported {len(team_objects)} teams")

    return team_objects


def get_or_create_fcs_team(db, team_name: str, team_objects: dict) -> Team:
    """
    Get or create FCS team placeholder.

    Args:
        db: Database session
        team_name: Name of FCS team
        team_objects: Dictionary to update with new team

    Returns:
        Team object for FCS team
    """
    # Check if already in our cache
    if team_name in team_objects:
        return team_objects[team_name]

    # Check if exists in database
    team = db.query(Team).filter(Team.name == team_name).first()

    if not team:
        # Create new FCS team placeholder
        team = Team(
            name=team_name,
            conference=ConferenceType.FCS,
            is_fcs=True,
            elo_rating=0,  # Not used for FCS
            initial_rating=0,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=0.5,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    # Add to cache
    team_objects[team_name] = team
    return team


# EPIC-008 Story 003: Validation and duplicate detection functions


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


def import_ap_poll_rankings(cfbd: CFBDClient, db, team_objects: dict, year: int, week: int) -> int:
    """
    Import AP Poll rankings for a specific week.

    Part of EPIC-010: AP Poll Prediction Comparison

    Args:
        cfbd: CFBD client instance
        db: Database session
        team_objects: Dictionary mapping team names to Team objects
        year: Season year
        week: Week number

    Returns:
        int: Number of rankings imported
    """
    # Fetch AP Poll data for this week
    ap_poll_data = cfbd.get_ap_poll(year, week)

    if not ap_poll_data:
        # No AP Poll available for this week (common for early weeks, late season)
        return 0

    rankings_imported = 0

    for ranking in ap_poll_data:
        school_name = ranking.get("school")
        rank = ranking.get("rank")

        # Find team in our database
        team = team_objects.get(school_name)
        if not team:
            # Team not in our FBS list (shouldn't happen for AP Top 25)
            print(f"      Warning: AP Poll team '{school_name}' not found in database")
            continue

        # Check if ranking already exists (prevent duplicates)
        existing = (
            db.query(APPollRanking)
            .filter(
                APPollRanking.season == year,
                APPollRanking.week == week,
                APPollRanking.team_id == team.id,
            )
            .first()
        )

        if existing:
            # Update existing ranking
            existing.rank = rank
            existing.first_place_votes = ranking.get("firstPlaceVotes", 0)
            existing.points = ranking.get("points", 0)
            existing.poll_type = ranking.get("poll", "AP Top 25")
        else:
            # Create new ranking
            ap_ranking = APPollRanking(
                season=year,
                week=week,
                poll_type=ranking.get("poll", "AP Top 25"),
                rank=rank,
                team_id=team.id,
                first_place_votes=ranking.get("firstPlaceVotes", 0),
                points=ranking.get("points", 0),
            )
            db.add(ap_ranking)
            rankings_imported += 1

    db.commit()
    return rankings_imported


def import_conference_championships(
    cfbd: CFBDClient, db, team_objects: dict, year: int, ranking_service
):
    """
    Import conference championship games from CFBD API.

    EPIC-022: Fetches regular season weeks 14-15 and filters for conference championships.
    Conference championships are played in week 14 (and sometimes 15) and have "Championship"
    in the game notes, but are not bowl games or playoff games.

    Args:
        cfbd: CFBD API client
        db: Database session
        team_objects: Dictionary of team objects by name
        year: Season year
        ranking_service: Ranking service instance for processing games

    Returns:
        int: Number of conference championship games imported
    """
    print(f"\nImporting conference championship games for {year}...")
    print("=" * 80)

    # Fetch regular season weeks 14-15 (championship weeks)
    # Conference championships are part of regular season, not postseason
    # Filter for FBS-only to exclude FCS/Division II/III championships
    conf_championships = []

    for week in [14, 15]:
        week_games = cfbd.get_games(year, week=week, season_type="regular", classification="fbs")

        if not week_games:
            continue

        # Filter for conference championships in this week
        for game in week_games:
            notes = game.get("notes", "") or ""  # Handle None

            # Conference championships have "Championship" in notes
            # Exclude: CFP (College Football Playoff) games
            is_championship = "Championship" in notes or "championship" in notes
            is_cfp = "playoff" in notes.lower() or "semifinal" in notes.lower()

            # Accept conference championships, exclude CFP
            if is_championship and not is_cfp:
                conf_championships.append(game)

    if not conf_championships:
        print("No conference championship games found")
        return 0

    print(f"Found {len(conf_championships)} conference championship games")

    if len(conf_championships) == 0:
        print("✓ No conference championships to import")
        return 0

    # Import each conference championship
    imported = 0
    skipped = 0
    processed = 0

    for game_data in conf_championships:
        home_team_name = game_data.get("homeTeam")
        away_team_name = game_data.get("awayTeam")
        week = game_data.get("week", 14)
        notes = game_data.get("notes", "")

        # Skip if teams not found
        if home_team_name not in team_objects or away_team_name not in team_objects:
            print(f"  ⚠️  Skipping {notes}: Teams not found in database")
            skipped += 1
            continue

        home_team = team_objects[home_team_name]
        away_team = team_objects[away_team_name]

        # Check for duplicate (prevent importing same game twice)
        existing_game = (
            db.query(Game)
            .filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.season == year,
                Game.week == week,
            )
            .first()
        )

        if existing_game:
            print(f"  ⚠️  {notes}: Already exists (Week {week})")
            skipped += 1
            continue

        # Get scores
        home_score = game_data.get("homePoints", 0) or 0
        away_score = game_data.get("awayPoints", 0) or 0

        # Check if game is completed (has actual scores)
        is_future_game = home_score == 0 and away_score == 0

        # EPIC-021: Fetch quarter scores if game is completed
        line_scores = None
        if not is_future_game:
            line_scores = cfbd.get_game_line_scores(
                game_id=game_data.get("id", 0),
                year=year,
                week=week,
                home_team=home_team_name,
                away_team=away_team_name,
            )

        # Create game with game_type='conference_championship'
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=home_score,
            away_score=away_score,
            week=week,
            season=year,
            is_neutral_site=game_data.get(
                "neutralSite", True
            ),  # Championships usually at neutral site
            game_type="conference_championship",  # EPIC-022: Mark as conference championship
            game_date=parse_game_date(game_data),
            # EPIC-021: Quarter scores (if available)
            q1_home=line_scores["home"][0] if line_scores else None,
            q1_away=line_scores["away"][0] if line_scores else None,
            q2_home=line_scores["home"][1] if line_scores else None,
            q2_away=line_scores["away"][1] if line_scores else None,
            q3_home=line_scores["home"][2] if line_scores else None,
            q3_away=line_scores["away"][2] if line_scores else None,
            q4_home=line_scores["home"][3] if line_scores else None,
            q4_away=line_scores["away"][3] if line_scores else None,
        )

        # EPIC-021: Validate quarter scores if present
        try:
            game.validate_quarter_scores()
        except ValueError as e:
            print(f"    ⚠️  Quarter score validation failed: {e}")
            game.q1_home = game.q1_away = game.q2_home = game.q2_away = None
            game.q3_home = game.q3_away = game.q4_home = game.q4_away = None

        db.add(game)
        db.commit()
        db.refresh(game)

        imported += 1

        # Process game for rankings if completed
        if not is_future_game:
            result = ranking_service.process_game(game)
            winner = result["winner_name"]
            loser = result["loser_name"]
            score = result["score"]
            print(f"  ✓ {notes}: {winner} defeats {loser} {score}")
            processed += 1
        else:
            print(f"  ✓ {notes}: {home_team_name} vs {away_team_name} (scheduled)")

            # EPIC-009: Store prediction for future championship game
            from ranking_service import create_and_store_prediction

            prediction = create_and_store_prediction(db, game)
            if prediction:
                print(f"      → Prediction stored ({prediction.predicted_winner.name} favored)")

    # Summary
    print()
    print("=" * 80)
    print("CONFERENCE CHAMPIONSHIP IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total Identified: {len(conf_championships)}")
    print(f"Imported: {imported}")
    print(f"Processed for Rankings: {processed}")
    if skipped > 0:
        print(f"Skipped: {skipped}")
    print("=" * 80)
    print()

    return imported


def import_bowl_games(cfbd: CFBDClient, db, team_objects: dict, year: int, ranking_service):
    """
    Import bowl games from CFBD API.

    EPIC-023: Fetches postseason games and filters for bowl games (excluding conference championships and playoffs).
    Bowl games are typically played in December-January after the regular season.

    Args:
        cfbd: CFBD API client
        db: Database session
        team_objects: Dictionary of team objects by name
        year: Season year
        ranking_service: Ranking service instance for processing games

    Returns:
        int: Number of bowl games imported
    """
    print(f"\nImporting bowl games for {year}...")
    print("=" * 80)

    # Fetch postseason games from CFBD API
    postseason_games = cfbd.get_games(year, season_type="postseason", classification="fbs")

    if not postseason_games:
        print("No postseason games found")
        return 0

    # Filter for bowl games only (exclude conference championships and playoffs)
    bowl_games = []

    for game in postseason_games:
        notes = game.get("notes", "") or ""

        # Skip conference championships (already imported in EPIC-022)
        if "Championship" in notes or "championship" in notes:
            # Check if it's a CONFERENCE championship (not bowl championship)
            # Conference championships have "ACC Championship", "Big Ten Championship", etc.
            conference_keywords = [
                "ACC",
                "Big Ten",
                "Big 12",
                "SEC",
                "Pac-12",
                "American",
                "Conference USA",
                "MAC",
                "Mountain West",
                "Sun Belt",
            ]
            is_conf_champ = any(conf in notes for conf in conference_keywords)

            if is_conf_champ:
                continue  # Skip conference championships

        # Skip playoff games (will be handled in Story 23.2)
        is_playoff = any(
            keyword in notes.lower()
            for keyword in ["playoff", "semifinal", "national championship"]
        )

        if is_playoff:
            continue  # Skip playoff games for now

        # This is a bowl game!
        bowl_games.append(game)

    if not bowl_games:
        print("No bowl games found")
        return 0

    print(f"Found {len(bowl_games)} bowl games")

    # Import each bowl game
    imported = 0
    skipped = 0
    processed = 0

    for game_data in bowl_games:
        home_team_name = game_data.get("homeTeam")
        away_team_name = game_data.get("awayTeam")
        week = game_data.get("week", 16)  # Bowl games typically week 16+

        # BUGFIX: CFBD sometimes returns week=1 for unscheduled bowl games
        # Bowl games should be weeks 15-17, so override invalid values
        if week < 15:
            week = 16  # Default to week 16 for bowl games

        notes = game_data.get("notes", "") or "Bowl Game"

        # Extract bowl name from notes (e.g., "Rose Bowl Game", "Sugar Bowl")
        bowl_name = notes if notes else "Bowl Game"

        # Skip if teams not found
        if home_team_name not in team_objects or away_team_name not in team_objects:
            print(
                f"  ⚠️  Skipping {bowl_name}: Teams not found ({home_team_name} vs {away_team_name})"
            )
            skipped += 1
            continue

        home_team = team_objects[home_team_name]
        away_team = team_objects[away_team_name]

        # Check for duplicate
        existing_game = (
            db.query(Game)
            .filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.season == year,
                Game.week == week,
            )
            .first()
        )

        if existing_game:
            # Update game_type and postseason_name if not set
            if not existing_game.game_type or not existing_game.postseason_name:
                existing_game.game_type = "bowl"
                existing_game.postseason_name = bowl_name
                db.commit()
                print(f"  ✓ Updated: {bowl_name} (Week {week})")
                imported += 1
            else:
                print(f"  ⚠️  {bowl_name}: Already exists (Week {week})")
                skipped += 1
            continue

        # Get scores
        home_score = game_data.get("homePoints", 0) or 0
        away_score = game_data.get("awayPoints", 0) or 0

        # Check if game is completed
        is_future_game = home_score == 0 and away_score == 0

        # EPIC-021: Fetch quarter scores if game is completed
        line_scores = None
        if not is_future_game:
            line_scores = cfbd.get_game_line_scores(
                game_id=game_data.get("id", 0),
                year=year,
                week=week,
                home_team=home_team_name,
                away_team=away_team_name,
            )

        # Create game with game_type='bowl' and postseason_name
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=home_score,
            away_score=away_score,
            week=week,
            season=year,
            is_neutral_site=game_data.get("neutralSite", True),  # Bowl games usually neutral
            game_type="bowl",  # EPIC-023: Mark as bowl game
            postseason_name=bowl_name,  # EPIC-023: Store bowl name
            game_date=parse_game_date(game_data),
            # EPIC-021: Quarter scores (if available)
            q1_home=line_scores["home"][0] if line_scores else None,
            q1_away=line_scores["away"][0] if line_scores else None,
            q2_home=line_scores["home"][1] if line_scores else None,
            q2_away=line_scores["away"][1] if line_scores else None,
            q3_home=line_scores["home"][2] if line_scores else None,
            q3_away=line_scores["away"][2] if line_scores else None,
            q4_home=line_scores["home"][3] if line_scores else None,
            q4_away=line_scores["away"][3] if line_scores else None,
        )
        db.add(game)
        db.commit()

        # Process game if completed
        if not is_future_game:
            try:
                ranking_service.process_game(game)
                processed += 1
                print(
                    f"  ✓ Imported & processed: {bowl_name} - {away_team_name} vs {home_team_name} ({away_score}-{home_score})"
                )
            except Exception as e:
                print(f"  ⚠️  Imported but not processed: {bowl_name} - {str(e)}")
        else:
            print(f"  ✓ Imported (scheduled): {bowl_name} - {away_team_name} @ {home_team_name}")

        imported += 1

    print()
    print(f"Imported: {imported}")
    print(f"Processed: {processed}")
    if skipped > 0:
        print(f"Skipped: {skipped}")
    print("=" * 80)
    print()

    return imported


def import_playoff_games(cfbd: CFBDClient, db, team_objects: dict, year: int, ranking_service):
    """
    Import College Football Playoff games from CFBD API.

    EPIC-023 Story 23.2: Fetches postseason games and filters for playoff games.
    Handles both 4-team playoff format (2014-2023) and 12-team format (2024+).

    Args:
        cfbd: CFBD API client
        db: Database session
        team_objects: Dictionary of team objects by name
        year: Season year
        ranking_service: Ranking service instance for processing games

    Returns:
        int: Number of playoff games imported
    """
    print(f"\nImporting CFP playoff games for {year}...")
    print("=" * 80)

    # Fetch postseason games from CFBD API
    postseason_games = cfbd.get_games(year, season_type="postseason", classification="fbs")

    if not postseason_games:
        print("No postseason games found")
        return 0

    # Filter for playoff games only
    playoff_games = []

    for game in postseason_games:
        notes = game.get("notes", "") or ""

        # Identify playoff games by keywords
        playoff_keywords = [
            "playoff",
            "semifinal",
            "quarterfinal",
            "national championship",
            "first round",
            "cfp",
        ]

        is_playoff = any(keyword in notes.lower() for keyword in playoff_keywords)

        # Also check if it's explicitly marked as championship but is CFP
        if "championship" in notes.lower() and "cfp" in notes.lower():
            is_playoff = True

        if is_playoff:
            playoff_games.append(game)

    if not playoff_games:
        print("No playoff games found")
        return 0

    print(f"Found {len(playoff_games)} playoff games")

    # Import each playoff game
    imported = 0
    skipped = 0
    processed = 0

    for game_data in playoff_games:
        home_team_name = game_data.get("homeTeam")
        away_team_name = game_data.get("awayTeam")
        notes = game_data.get("notes", "") or "CFP Game"

        # Determine playoff round from notes
        playoff_round = "CFP Game"  # Default
        notes_lower = notes.lower()

        # Assign week numbers based on playoff round
        # 12-team format (2024+): First Round (16), Quarterfinals (17), Semifinals (18), Championship (19)
        # 4-team format (2014-2023): Semifinals (17), Championship (18)
        if "national championship" in notes_lower:
            playoff_round = "CFP National Championship"
            week = 19 if year >= 2024 else 18
        elif "semifinal" in notes_lower:
            # Extract bowl name if present (e.g., "CFP Semifinal - Rose Bowl")
            playoff_round = "CFP Semifinal"
            week = 18 if year >= 2024 else 17
            if "rose" in notes_lower:
                playoff_round = "CFP Semifinal - Rose Bowl"
            elif "sugar" in notes_lower:
                playoff_round = "CFP Semifinal - Sugar Bowl"
            elif "orange" in notes_lower:
                playoff_round = "CFP Semifinal - Orange Bowl"
            elif "cotton" in notes_lower:
                playoff_round = "CFP Semifinal - Cotton Bowl"
            elif "peach" in notes_lower:
                playoff_round = "CFP Semifinal - Peach Bowl"
            elif "fiesta" in notes_lower:
                playoff_round = "CFP Semifinal - Fiesta Bowl"
        elif "quarterfinal" in notes_lower:
            # 12-team format has quarterfinals
            playoff_round = "CFP Quarterfinal"
            week = 17
        elif "first round" in notes_lower:
            # 12-team format has first round
            playoff_round = "CFP First Round"
            week = 16
        else:
            # Fallback - use API week or default
            week = game_data.get("week", 17)
            # BUGFIX: Validate week number for playoff games
            if week < 15:
                week = 17  # Default to week 17 for unidentified playoff games

        # Skip if teams not found
        if home_team_name not in team_objects or away_team_name not in team_objects:
            print(
                f"  ⚠️  Skipping {playoff_round}: Teams not found ({home_team_name} vs {away_team_name})"
            )
            skipped += 1
            continue

        home_team = team_objects[home_team_name]
        away_team = team_objects[away_team_name]

        # Check for duplicate
        existing_game = (
            db.query(Game)
            .filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.season == year,
                Game.week == week,
            )
            .first()
        )

        if existing_game:
            # Update game_type and postseason_name if not set
            if not existing_game.game_type or existing_game.game_type != "playoff":
                existing_game.game_type = "playoff"
                existing_game.postseason_name = playoff_round
                db.commit()
                print(f"  ✓ Updated: {playoff_round} (Week {week})")
                imported += 1
            else:
                print(f"  ⚠️  {playoff_round}: Already exists (Week {week})")
                skipped += 1
            continue

        # Get scores
        home_score = game_data.get("homePoints", 0) or 0
        away_score = game_data.get("awayPoints", 0) or 0

        # Check if game is completed
        is_future_game = home_score == 0 and away_score == 0

        # EPIC-021: Fetch quarter scores if game is completed
        line_scores = None
        if not is_future_game:
            line_scores = cfbd.get_game_line_scores(
                game_id=game_data.get("id", 0),
                year=year,
                week=week,
                home_team=home_team_name,
                away_team=away_team_name,
            )

        # Create game with game_type='playoff' and postseason_name
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=home_score,
            away_score=away_score,
            week=week,
            season=year,
            is_neutral_site=game_data.get("neutralSite", True),  # Playoff games usually neutral
            game_type="playoff",  # EPIC-023: Mark as playoff game
            postseason_name=playoff_round,  # EPIC-023: Store playoff round
            game_date=parse_game_date(game_data),
            # EPIC-021: Quarter scores (if available)
            q1_home=line_scores["home"][0] if line_scores else None,
            q1_away=line_scores["away"][0] if line_scores else None,
            q2_home=line_scores["home"][1] if line_scores else None,
            q2_away=line_scores["away"][1] if line_scores else None,
            q3_home=line_scores["home"][2] if line_scores else None,
            q3_away=line_scores["away"][2] if line_scores else None,
            q4_home=line_scores["home"][3] if line_scores else None,
            q4_away=line_scores["away"][3] if line_scores else None,
        )
        db.add(game)
        db.commit()

        # Process game if completed
        if not is_future_game:
            try:
                ranking_service.process_game(game)
                processed += 1
                print(
                    f"  ✓ Imported & processed: {playoff_round} - {away_team_name} vs {home_team_name} ({away_score}-{home_score})"
                )
            except Exception as e:
                print(f"  ⚠️  Imported but not processed: {playoff_round} - {str(e)}")
        else:
            print(
                f"  ✓ Imported (scheduled): {playoff_round} - {away_team_name} @ {home_team_name}"
            )

        imported += 1

    print()
    print(f"Imported: {imported}")
    print(f"Processed: {processed}")
    if skipped > 0:
        print(f"Skipped: {skipped}")
    print("=" * 80)
    print()

    return imported


def import_games(
    cfbd: CFBDClient,
    db,
    team_objects: dict,
    year: int,
    max_week: int = None,
    validate_only: bool = False,
    strict: bool = False,
):
    """
    Import games for the season with validation and completeness reporting.

    Args:
        cfbd: CFBD client instance
        db: Database session
        team_objects: Dictionary mapping team names to Team objects
        year: Season year
        max_week: Maximum week to import
        validate_only: If True, don't actually import (dry-run)
        strict: If True, fail on validation warnings

    Returns:
        dict: Import statistics including total imported, skipped, etc.
    """
    print(f"\nImporting games for {year}...")
    if validate_only:
        print("**VALIDATION MODE** - No changes will be made to database\n")

    ranking_service = RankingService(db)

    # Determine which weeks to import
    weeks = range(1, (max_week or 15) + 1)

    # Track statistics
    total_imported = 0
    fcs_games_imported = 0  # NEW: Track FCS games separately
    future_games_imported = 0  # EPIC-008: Track future games
    predictions_stored = 0  # EPIC-009: Track stored predictions
    ap_poll_rankings_imported = 0  # EPIC-010: Track AP Poll rankings
    total_updated = 0  # EPIC-008 Story 002: Track updated games
    total_skipped = 0
    skipped_fcs = 0
    skipped_not_found = 0
    skipped_incomplete = 0
    skipped_details = []  # List of (week, reason, game_description) tuples

    for week in weeks:
        print(f"\nWeek {week}...")
        games_data = cfbd.get_games(year, week=week)

        if not games_data:
            print(f"  No games found for week {week}")
            continue

        # Get week statistics for validation
        week_stats = get_week_statistics(cfbd, year, week)
        week_imported = 0
        week_skipped = 0
        week_updated = 0  # EPIC-008 Story 002: Track updated games per week

        for game_data in games_data:
            # API uses camelCase
            home_team_name = game_data.get("homeTeam")
            away_team_name = game_data.get("awayTeam")
            home_score = game_data.get("homePoints")
            away_score = game_data.get("awayPoints")

            game_desc = f"{away_team_name} @ {home_team_name}"

            # EPIC-008: Detect future games (no scores yet) and import them
            is_future_game = home_score is None or away_score is None

            if is_future_game:
                # Future game - use placeholder scores and don't process for ELO
                home_score = 0
                away_score = 0
                print(f"    Found future game: {game_desc}")

            # Determine if FBS vs FBS, FBS vs FCS, or both FCS
            # BUGFIX: Check is_fcs flag instead of just presence in team_objects
            # (FCS teams get added to team_objects when we create them)
            home_team_obj = team_objects.get(home_team_name)
            away_team_obj = team_objects.get(away_team_name)

            home_is_fbs = home_team_obj is not None and not home_team_obj.is_fcs
            away_is_fbs = away_team_obj is not None and not away_team_obj.is_fcs

            # Case 1: Both FCS (skip entirely)
            if not home_is_fbs and not away_is_fbs:
                week_skipped += 1
                total_skipped += 1
                skipped_fcs += 1
                skipped_details.append((week, "Both teams FCS", game_desc))
                continue

            # Case 2: FBS vs FCS game - import with excluded flag
            is_fcs_game = not (home_is_fbs and away_is_fbs)

            # Get team objects (create FCS team if needed)
            if home_team_obj and not home_team_obj.is_fcs:
                home_team = home_team_obj
            else:
                home_team = get_or_create_fcs_team(db, home_team_name, team_objects)

            if away_team_obj and not away_team_obj.is_fcs:
                away_team = away_team_obj
            else:
                away_team = get_or_create_fcs_team(db, away_team_name, team_objects)

            # EPIC-008 Story 002: Check if game already exists (upsert logic)
            existing_game = (
                db.query(Game)
                .filter(
                    Game.home_team_id == home_team.id,
                    Game.away_team_id == away_team.id,
                    Game.week == week,
                    Game.season == year,
                )
                .first()
            )

            if existing_game:
                # Game exists - decide whether to update, skip, or process
                if is_future_game:
                    # Still a future game (no scores yet) - skip
                    # This can happen if we re-import the same future week
                    continue

                # Game now has scores - check if we should update
                if existing_game.home_score == 0 and existing_game.away_score == 0:
                    # Future game that now has scores - UPDATE IT
                    print(f"    Updating game: {game_desc} -> {home_score}-{away_score}")

                    existing_game.home_score = home_score
                    existing_game.away_score = away_score
                    existing_game.is_neutral_site = game_data.get("neutralSite", False)
                    existing_game.excluded_from_rankings = (
                        is_fcs_game  # Update based on actual FCS status
                    )
                    existing_game.game_date = parse_game_date(game_data)

                    # EPIC-021: Fetch and update quarter scores
                    line_scores = cfbd.get_game_line_scores(
                        game_id=game_data.get("id", 0),
                        year=year,
                        week=week,
                        home_team=home_team_name,
                        away_team=away_team_name,
                    )
                    if line_scores:
                        existing_game.q1_home = line_scores["home"][0]
                        existing_game.q1_away = line_scores["away"][0]
                        existing_game.q2_home = line_scores["home"][1]
                        existing_game.q2_away = line_scores["away"][1]
                        existing_game.q3_home = line_scores["home"][2]
                        existing_game.q3_away = line_scores["away"][2]
                        existing_game.q4_home = line_scores["home"][3]
                        existing_game.q4_away = line_scores["away"][3]

                        # Validate quarter scores
                        try:
                            existing_game.validate_quarter_scores()
                        except ValueError as e:
                            print(f"    ⚠️  Quarter validation failed: {e}")
                            existing_game.q1_home = existing_game.q1_away = None
                            existing_game.q2_home = existing_game.q2_away = None
                            existing_game.q3_home = existing_game.q3_away = None
                            existing_game.q4_home = existing_game.q4_away = None

                    # Mark as unprocessed so ELO calculation runs
                    existing_game.is_processed = False

                    db.commit()
                    db.refresh(existing_game)

                    # Now process the game for ELO ratings (if FBS vs FBS)
                    if not is_fcs_game:
                        result = ranking_service.process_game(existing_game)
                        winner = result["winner_name"]
                        loser = result["loser_name"]
                        score = result["score"]
                        print(f"      Processed: {winner} defeats {loser} {score}")
                        week_imported += 1
                        total_imported += 1

                    week_updated += 1
                    total_updated += 1
                    continue

                elif existing_game.is_processed:
                    # Already processed - skip
                    continue
                else:
                    # Has scores but not processed yet - process it
                    # But first check if it's actually a future game (0-0)
                    if existing_game.home_score == 0 and existing_game.away_score == 0:
                        # This is a future game that still has no scores - skip
                        continue

                    if not is_fcs_game:
                        result = ranking_service.process_game(existing_game)
                        week_imported += 1
                        total_imported += 1
                    continue

            # EPIC-008 Story 002: Game doesn't exist - INSERT NEW GAME

            # In validate-only mode, just count
            if validate_only:
                week_imported += 1
                total_imported += 1
                if is_future_game:
                    future_games_imported += 1
                continue

            # Create game
            is_neutral = game_data.get("neutralSite", False)

            # EPIC-008: Future games are excluded from rankings for safety
            excluded_from_rankings = is_fcs_game or is_future_game

            # EPIC-021: Fetch quarter scores if game is completed
            line_scores = None
            if not is_future_game:
                line_scores = cfbd.get_game_line_scores(
                    game_id=game_data.get("id", 0),
                    year=year,
                    week=week,
                    home_team=home_team_name,
                    away_team=away_team_name,
                )

            game = Game(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=home_score,  # 0 for future games, real score for completed
                away_score=away_score,  # 0 for future games, real score for completed
                week=week,
                season=year,
                is_neutral_site=is_neutral,
                excluded_from_rankings=excluded_from_rankings,
                game_date=parse_game_date(game_data),  # EPIC-008: Parse actual date from CFBD
                # EPIC-021: Quarter scores (if available)
                q1_home=line_scores["home"][0] if line_scores else None,
                q1_away=line_scores["away"][0] if line_scores else None,
                q2_home=line_scores["home"][1] if line_scores else None,
                q2_away=line_scores["away"][1] if line_scores else None,
                q3_home=line_scores["home"][2] if line_scores else None,
                q3_away=line_scores["away"][2] if line_scores else None,
                q4_home=line_scores["home"][3] if line_scores else None,
                q4_away=line_scores["away"][3] if line_scores else None,
            )

            # EPIC-021: Validate quarter scores if present
            try:
                game.validate_quarter_scores()
            except ValueError as e:
                print(f"    ⚠️  Quarter score validation failed: {e}")
                # Set quarters to None if validation fails
                game.q1_home = game.q1_away = game.q2_home = game.q2_away = None
                game.q3_home = game.q3_away = game.q4_home = game.q4_away = None

            db.add(game)
            db.commit()
            db.refresh(game)

            # EPIC-008: Process game to update rankings (ONLY for completed FBS vs FBS games)
            if is_future_game:
                # Future game - don't process for rankings
                print(f"    {game_desc} (scheduled - not ranked)")
                future_games_imported += 1
                week_imported += 1

                # EPIC-009: Store prediction for future game (FBS vs FBS only)
                if not is_fcs_game:
                    prediction = create_and_store_prediction(db, game)
                    if prediction:
                        predictions_stored += 1
            elif not is_fcs_game:
                # Completed FBS vs FBS game - process for rankings
                result = ranking_service.process_game(game)

                winner = result["winner_name"]
                loser = result["loser_name"]
                score = result["score"]

                print(f"    {winner} defeats {loser} {score}")
                week_imported += 1
                total_imported += 1
            else:
                # FCS game - don't process for rankings, just track
                fcs_opponent = away_team if home_is_fbs else home_team
                fbs_team_obj = home_team if home_is_fbs else away_team
                print(f"    {fbs_team_obj.name} vs {fcs_opponent.name} (FCS - not ranked)")
                fcs_games_imported += 1

        # Print week summary
        total_week_games = week_stats["completed"]
        if total_week_games > 0:
            completion_rate = (week_imported / total_week_games) * 100
            status = "✓" if completion_rate >= 95 else "⚠"
            print(f"\n  {status} Week {week} Summary:")
            print(f"    Expected: {total_week_games} games")
            print(f"    Imported: {week_imported} games ({completion_rate:.0f}%)")
            if week_updated > 0:  # EPIC-008 Story 002
                print(f"    Updated: {week_updated} games")
            if week_skipped > 0:
                print(f"    Skipped: {week_skipped} games")

        # EPIC-010: Import AP Poll rankings for this week (if not validate-only)
        if not validate_only:
            ap_rankings_count = import_ap_poll_rankings(cfbd, db, team_objects, year, week)
            if ap_rankings_count > 0:
                print(f"    AP Poll: {ap_rankings_count} rankings imported")
                ap_poll_rankings_imported += ap_rankings_count

    # Print final import summary
    print("\n" + "=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total FBS Games Imported: {total_imported}")
    print(f"Total FCS Games Imported: {fcs_games_imported}")
    print(f"Total Future Games Imported: {future_games_imported}")  # EPIC-008
    print(f"Total Predictions Stored: {predictions_stored}")  # EPIC-009
    print(f"Total AP Poll Rankings Imported: {ap_poll_rankings_imported}")  # EPIC-010
    print(f"Total Games Updated: {total_updated}")  # EPIC-008 Story 002
    print(f"Total Games Skipped: {total_skipped}")
    if skipped_fcs > 0:
        print(f"  - FCS Opponents: {skipped_fcs}")
    if skipped_not_found > 0:
        print(f"  - Team Not Found: {skipped_not_found}")
    if skipped_incomplete > 0:
        print(f"  - Incomplete Games (now imported as future): {skipped_incomplete}")

    # Show details of skipped games (limit to first 10)
    if skipped_details and not validate_only:
        print(f"\nSkipped Game Details (showing first 10 of {len(skipped_details)}):")
        for week, reason, game in skipped_details[:10]:
            print(f"  Week {week}: {game} - {reason}")

    # Check for strict mode failures
    if strict and total_skipped > 0:
        print("\n✗ STRICT MODE: Import failed due to skipped games")
        sys.exit(1)

    print("=" * 80)

    return {
        "imported": total_imported,
        "fcs_imported": fcs_games_imported,
        "future_imported": future_games_imported,  # EPIC-008
        "predictions_stored": predictions_stored,  # EPIC-009
        "ap_poll_rankings_imported": ap_poll_rankings_imported,  # EPIC-010
        "games_updated": total_updated,  # EPIC-008 Story 002
        "skipped": total_skipped,
        "skipped_fcs": skipped_fcs,
        "skipped_not_found": skipped_not_found,
        "skipped_incomplete": skipped_incomplete,
    }


def main():
    """Main import function"""
    print("=" * 80)
    print("COLLEGE FOOTBALL DATA IMPORT")
    print("=" * 80)
    print()
    print("This script imports real college football data from CollegeFootballData.com")
    print()

    # Parse command-line arguments
    import os

    api_key = os.getenv("CFBD_API_KEY")

    # Initialize CFBD client first (needed for auto-detection)
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

    cfbd = CFBDClient(api_key)

    # Auto-detect current season and week
    current_season = cfbd.get_current_season()
    max_week_available = cfbd.get_current_week(current_season)

    # If API doesn't have week data yet, estimate from calendar
    if max_week_available is None:
        max_week_available = cfbd.estimate_current_week(current_season)
        if max_week_available == 0:
            max_week_available = 1  # Default to week 1 if pre-season

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Import college football data from CFBD API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Incremental update (default) - import new data without resetting database
  python3 import_real_data.py

  # Full reset - wipe database and reimport everything
  python3 import_real_data.py --reset

  # Override season year
  python3 import_real_data.py --season 2024

  # Override max week to import
  python3 import_real_data.py --max-week 10

  # Specify both season and week
  python3 import_real_data.py --season 2024 --max-week 12
        """,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before import (WARNING: destroys all existing data)",
    )
    parser.add_argument(
        "--season", type=int, help=f"Season year (default: auto-detect, currently {current_season})"
    )
    parser.add_argument(
        "--max-week",
        type=int,
        help=f"Maximum week to import (default: all available, currently {max_week_available})",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate import without making changes (dry-run mode)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on validation warnings (exit with error if games skipped)",
    )

    args = parser.parse_args()

    # Use overrides or detected values
    season = args.season or current_season
    max_week = args.max_week or max_week_available

    # Validate API connection
    if not validate_api_connection(cfbd, season):
        print("\n✗ Cannot proceed without valid API connection")
        sys.exit(1)

    print(f"✓ Detected current season: {current_season}")
    print(f"✓ Latest completed week: {max_week_available}")
    if args.season:
        print(f"  → Using season override: {season}")
    if args.max_week:
        print(f"  → Using max week override: {max_week}")
    if args.validate_only:
        print(f"  → VALIDATE-ONLY MODE: No database changes will be made")
    if args.strict:
        print(f"  → STRICT MODE: Will fail on validation warnings")
    if args.reset:
        print(f"  → RESET MODE: Database will be wiped and rebuilt")
    else:
        print(f"  → INCREMENTAL MODE: New data will be added to existing database")
    print()

    # Initialize database
    db = SessionLocal()

    # Conditional reset based on --reset flag
    if args.reset:
        # Confirm reset
        print("WARNING: This will reset your database and replace all data!")
        response = input("Continue? (yes/no): ")

        if response.lower() != "yes":
            print("Cancelled.")
            return

        # Reset database
        print("\nResetting database...")
        reset_db()

        # Create season
        print(f"Creating {season} season...")
        season_obj = Season(year=season, current_week=0, is_active=True)
        db.add(season_obj)
        db.commit()
    else:
        # Incremental mode - get or create season
        print(f"Incremental mode: Getting or creating {season} season...")
        season_obj = db.query(Season).filter(Season.year == season).first()
        if not season_obj:
            print(f"  Season {season} not found, creating new season...")
            season_obj = Season(year=season, current_week=0, is_active=True)
            db.add(season_obj)
            db.commit()
        else:
            print(f"  Found existing season {season} (current week: {season_obj.current_week})")

    # Import teams
    team_objects = import_teams(cfbd, db, year=season)

    if not team_objects:
        print("\nFailed to import teams. Check your API key.")
        return

    # Import games (using detected/overridden max_week)
    print(f"\nImporting games through Week {max_week}...")
    import_stats = import_games(
        cfbd,
        db,
        team_objects,
        year=season,
        max_week=max_week,
        validate_only=args.validate_only,
        strict=args.strict,
    )

    # EPIC-022: Import conference championship games
    # EPIC-023: Import bowl games
    if not args.validate_only:
        ranking_service = RankingService(db)

        # Import conference championships
        conf_champ_count = import_conference_championships(
            cfbd, db, team_objects, season, ranking_service
        )
        import_stats["conf_championships_imported"] = conf_champ_count

        # Import bowl games
        bowl_count = import_bowl_games(cfbd, db, team_objects, season, ranking_service)
        import_stats["bowl_games_imported"] = bowl_count

        # Import playoff games
        playoff_count = import_playoff_games(cfbd, db, team_objects, season, ranking_service)
        import_stats["playoff_games_imported"] = playoff_count

    # Skip remaining steps if validate-only mode
    if args.validate_only:
        print("\n✓ Validation complete - no changes made to database")
        db.close()
        return

    # EPIC-008 Story 003: Validate import results
    validate_import_results(db, import_stats, season)

    # EPIC-022: Determine actual max week including championship games
    # Conference championships may be in Week 15, even if max_week was 14
    actual_max_week = (
        db.query(Game)
        .filter(Game.season == season, Game.is_processed == True)
        .order_by(Game.week.desc())
        .first()
    )

    if actual_max_week:
        final_week = actual_max_week.week
    else:
        final_week = max_week

    # Update season current week to actual max
    season_obj.current_week = final_week
    db.commit()

    # Save rankings through actual max week (including championship week if present)
    print(f"\nSaving final rankings through Week {final_week}...")
    # ranking_service already created above for conference championships
    for week in range(1, final_week + 1):
        ranking_service.save_weekly_rankings(season, week)

    # Show final rankings
    print("\n" + "=" * 80)
    print("FINAL RANKINGS")
    print("=" * 80)

    rankings = ranking_service.get_current_rankings(season, limit=25)
    print(f"\n{'RANK':<6} {'TEAM':<30} {'RATING':<10} {'RECORD':<10} {'SOS':<10}")
    print("-" * 80)

    for r in rankings:
        record = f"{r['wins']}-{r['losses']}"
        print(
            f"{r['rank']:<6} {r['team_name']:<30} {r['elo_rating']:<10.2f} {record:<10} {r['sos']:<10.2f}"
        )

    print()
    print("=" * 80)
    print(f"✓ Import Complete!")
    print(f"  - {len(team_objects)} teams imported")
    print(f"  - {import_stats['imported']} FBS games imported")
    if import_stats.get("fcs_imported", 0) > 0:
        print(f"  - {import_stats['fcs_imported']} FCS games imported (not ranked)")
    if import_stats.get("conf_championships_imported", 0) > 0:
        print(
            f"  - {import_stats['conf_championships_imported']} conference championships imported"
        )
    if import_stats.get("bowl_games_imported", 0) > 0:
        print(f"  - {import_stats['bowl_games_imported']} bowl games imported")
    if import_stats.get("playoff_games_imported", 0) > 0:
        print(f"  - {import_stats['playoff_games_imported']} playoff games imported")
    if import_stats["skipped"] > 0:
        print(f"  - {import_stats['skipped']} games skipped")
    print(f"  - Rankings calculated through Week {final_week}")
    print("=" * 80)

    db.close()


if __name__ == "__main__":
    main()
