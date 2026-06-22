"""Shared helpers for the CFBD import pipeline."""

from datetime import datetime

from src.integrations.cfbd_client import CFBDClient
from src.models.models import ConferenceType, Game, Team

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
    "startDate": "2025-09-06T19:00:00.000Z"

    Args:
        game_data: Game data dictionary from CFBD API

    Returns:
        datetime: Parsed game date, or None if not available

    Note:
        Returns None instead of datetime.now() when date is unavailable.
        This prevents showing incorrect import timestamps as game dates.
        Frontend will display "TBD" for games without scheduled dates.
    """
    # BUGFIX: CFBD API uses camelCase "startDate", not snake_case "start_date"
    date_str = game_data.get("startDate")
    if date_str:
        try:
            # CFBD uses ISO 8601 format with Z suffix (UTC)
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass
    # Return None for unscheduled games instead of showing wrong date
    return None


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
            returning_production=0.5,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    # Add to cache
    team_objects[team_name] = team
    return team


def find_existing_game(db, home_team_id: int, away_team_id: int, week: int, season: int) -> Game:
    """
    Look up an existing game by its identifying fields.

    Args:
        db: Database session
        home_team_id: Home team ID
        away_team_id: Away team ID
        week: Week number
        season: Season year

    Returns:
        Game or None
    """
    return (
        db.query(Game)
        .filter(
            Game.home_team_id == home_team_id,
            Game.away_team_id == away_team_id,
            Game.week == week,
            Game.season == season,
        )
        .first()
    )


def apply_quarter_scores(game: Game, line_scores) -> None:
    """
    Apply fetched quarter scores to a game and validate them (EPIC-021).

    No-op when line_scores is falsy. On validation failure the quarter
    fields are cleared rather than persisting inconsistent data.

    Args:
        game: Game ORM object (new or existing)
        line_scores: dict with "home"/"away" lists of 4 quarter scores, or None
    """
    if not line_scores:
        return

    game.q1_home = line_scores["home"][0]
    game.q1_away = line_scores["away"][0]
    game.q2_home = line_scores["home"][1]
    game.q2_away = line_scores["away"][1]
    game.q3_home = line_scores["home"][2]
    game.q3_away = line_scores["away"][2]
    game.q4_home = line_scores["home"][3]
    game.q4_away = line_scores["away"][3]

    try:
        game.validate_quarter_scores()
    except ValueError as e:
        print(f"    ⚠️  Quarter score validation failed: {e}")
        game.q1_home = game.q1_away = game.q2_home = game.q2_away = None
        game.q3_home = game.q3_away = game.q4_home = game.q4_away = None
