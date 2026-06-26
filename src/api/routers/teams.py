"""Team API routes.

Auto-extracted from the former monolithic main.py during the EPIC-043
backend modularization. Route paths and handler logic are unchanged.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.core.ranking_service import RankingService
from src.models import schemas
from src.models.database import get_db
from src.models.models import ConferenceType, Game, RankingHistory, Season, Team

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/teams", response_model=List[schemas.Team], tags=["Teams"])
async def get_teams(
    conference: Optional[ConferenceType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all teams with optional filtering by conference.

    Retrieves a paginated list of college football teams. Supports filtering
    by conference type (P5, G5, FCS) and pagination for large result sets.

    Args:
        conference: Optional conference filter (P5, G5, or FCS)
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100, max: 500)
        db: Database session (injected by FastAPI)

    Returns:
        List[schemas.Team]: List of team objects with basic information

    Example:
        Get all Power 5 teams:
            GET /api/teams?conference=P5

        Get teams with pagination:
            GET /api/teams?skip=0&limit=50
    """
    query = db.query(Team)

    if conference:
        query = query.filter(Team.conference == conference)

    teams = query.offset(skip).limit(limit).all()
    return teams


@router.get("/api/teams/{team_id}", response_model=schemas.TeamDetail, tags=["Teams"])
async def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get a specific team by ID with detailed season statistics.

    Retrieves comprehensive team information including current ELO rating,
    season-specific wins/losses, and strength of schedule data from the
    current active season.

    Args:
        team_id: Unique team identifier
        db: Database session (injected by FastAPI)

    Returns:
        schemas.TeamDetail: Detailed team object with:
            - Basic info (name, conference, recruiting/transfer data)
            - Season-specific stats (wins, losses, current ELO)
            - Ranking data (rank, SOS, SOS rank)

    Raises:
        HTTPException: 404 if team not found

    Example:
        GET /api/teams/42
    """
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get current season
    season = db.query(Season).filter(Season.is_active == True).first()
    season_year = season.year if season else datetime.now().year

    # EPIC-024: Get season-specific data from rankings
    ranking_service = RankingService(db)
    rankings = ranking_service.get_current_rankings(season_year)

    # Find this team's ranking data (includes season-specific wins/losses)
    team_ranking = next((r for r in rankings if r["team_id"] == team_id), None)

    # Convert to TeamDetail schema
    team_dict = {
        "id": team.id,
        "name": team.name,
        "conference": team.conference,
        "conference_name": team.conference_name,  # EPIC-012: Include conference name
        "recruiting_rank": team.recruiting_rank,
        "returning_production": team.returning_production,
        "transfer_portal_points": team.transfer_portal_points,  # EPIC-026: Transfer portal points
        "transfer_portal_rank": team.transfer_portal_rank,  # EPIC-026: Transfer portal rank
        "transfer_count": team.transfer_count,  # EPIC-026: Transfer count
        "elo_rating": (
            team_ranking["elo_rating"] if team_ranking else team.elo_rating
        ),  # EPIC-024: Season-specific ELO
        "initial_rating": team.initial_rating,
        "wins": team_ranking["wins"] if team_ranking else 0,  # EPIC-024: Season-specific wins
        "losses": team_ranking["losses"] if team_ranking else 0,  # EPIC-024: Season-specific losses
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "sos": team_ranking["sos"] if team_ranking else None,  # EPIC-024: From ranking_history
        "rank": team_ranking["rank"] if team_ranking else None,  # EPIC-024: From ranking_history
        "sos_rank": (
            team_ranking["sos_rank"] if team_ranking else None
        ),  # EPIC-024: From ranking_history
    }

    return team_dict


@router.post("/api/teams", response_model=schemas.Team, status_code=201, tags=["Teams"])
async def create_team(team: schemas.TeamCreate, db: Session = Depends(get_db)):
    """Create a new team with initialized ELO rating.

    Creates a team record and automatically calculates its initial ELO rating
    based on conference type, recruiting rank, transfer portal data, and
    returning production using the Modified ELO algorithm.

    Args:
        team: Team creation data (name, conference, recruiting metrics)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.Team: Created team object with initialized ELO rating

    Raises:
        HTTPException: 400 if team name already exists

    Example:
        POST /api/teams
        {
            "name": "Georgia",
            "conference": "P5",
            "recruiting_rank": 3,
            "returning_production": 85.2
        }
    """
    # Check if team already exists
    existing = db.query(Team).filter(Team.name == team.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team already exists")

    # Create team
    db_team = Team(**team.model_dump())

    # Initialize rating
    ranking_service = RankingService(db)
    ranking_service.initialize_team_rating(db_team)

    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    return db_team


@router.put("/api/teams/{team_id}", response_model=schemas.Team, tags=["Teams"])
async def update_team(team_id: int, team_update: schemas.TeamUpdate, db: Session = Depends(get_db)):
    """Update team information and recalculate rating if needed.

    Updates team fields with provided data. If preseason factors (recruiting,
    transfer portal, or returning production) are modified, automatically
    recalculates the team's ELO rating using the Modified ELO algorithm.

    Args:
        team_id: Unique team identifier
        team_update: Fields to update (only provided fields are updated)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.Team: Updated team object with potentially recalculated rating

    Raises:
        HTTPException: 404 if team not found

    Note:
        Updating recruiting_rank, returning_production, transfer_portal_rank,
        transfer_portal_points, or transfer_count will trigger automatic ELO
        rating recalculation.

    Example:
        PUT /api/teams/42
        {
            "recruiting_rank": 5,
            "returning_production": 82.5
        }
    """
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Update fields
    update_data = team_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    # Recalculate rating if preseason factors changed
    # EPIC-026: Added transfer portal fields to trigger recalculation
    if any(
        field in update_data
        for field in [
            "recruiting_rank",
            "returning_production",
            "transfer_portal_rank",
            "transfer_portal_points",
            "transfer_count",
        ]
    ):
        ranking_service = RankingService(db)
        team.elo_rating = ranking_service.calculate_preseason_rating(team)
        team.initial_rating = team.elo_rating

    db.commit()
    db.refresh(team)

    return team


@router.get("/api/teams/{team_id}/schedule", response_model=schemas.TeamSchedule, tags=["Teams"])
async def get_team_schedule(team_id: int, season: int, db: Session = Depends(get_db)):
    """Get a team's complete schedule for a specific season.

    Retrieves all games (home and away) for a team in a given season,
    including completed games with scores and upcoming games. Supports
    FCS opponents, neutral site games, and postseason games.

    Args:
        team_id: Unique team identifier
        season: Season year (e.g., 2024)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.TeamSchedule: Schedule object containing:
            - team_id, team_name, season
            - games: List of schedule games with opponent info and results

    Raises:
        HTTPException: 404 if team not found

    Example:
        GET /api/teams/42/schedule?season=2024
    """
    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get all games for this team (including FCS games)
    # Sort by: week ascending (chronological schedule)
    #          → game_date ascending (earliest date first within week)
    # Note: nulls_last() ensures games without dates appear after games with dates
    games = (
        db.query(Game)
        .filter(
            ((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
            & (Game.season == season)
        )
        .order_by(Game.week.asc(), Game.game_date.asc().nulls_last())
        .all()
    )

    # Fetch all ranking histories for this season to map team + week to their rank
    ranks = (
        db.query(RankingHistory.team_id, RankingHistory.week, RankingHistory.rank)
        .filter(RankingHistory.season == season)
        .all()
    )
    # Build a lookup map: (team_id, week) -> rank
    rank_lookup = {(r.team_id, r.week): r.rank for r in ranks}

    schedule_games = []
    for game in games:
        is_home = game.home_team_id == team_id
        opponent = game.away_team if is_home else game.home_team

        score_str = None
        if game.is_processed:
            if is_home:
                result = "W" if game.home_score > game.away_score else "L"
                score_str = f"{result} {game.home_score}-{game.away_score}"
            else:
                result = "W" if game.away_score > game.home_score else "L"
                score_str = f"{result} {game.away_score}-{game.home_score}"

        opponent_rank = rank_lookup.get((opponent.id, game.week))

        schedule_games.append(
            {
                "game_id": game.id,
                "week": game.week,
                "game_date": game.game_date.isoformat() if game.game_date else None,  # EPIC-GAME-DATE-SORTING: Include game date
                "opponent_id": opponent.id,
                "opponent_name": opponent.name,
                "opponent_conference": opponent.conference.value if opponent.conference else None,
                "is_home": is_home,
                "is_neutral_site": game.is_neutral_site,
                "score": score_str,
                "is_played": game.is_processed,
                "excluded_from_rankings": game.excluded_from_rankings,
                "is_fcs": opponent.is_fcs,
                "game_type": game.game_type,  # EPIC-022: Include game type for frontend badge display
                "postseason_name": game.postseason_name,  # EPIC-023: Include bowl/playoff name
                "home_score": game.home_score,
                "away_score": game.away_score,
                "home_team_id": game.home_team_id,
                "opponent_rank": opponent_rank,
            }
        )

    return {"team_id": team_id, "team_name": team.name, "season": season, "games": schedule_games}



@router.get("/api/teams/{team_id}/players", response_model=schemas.TeamPlayersResponse, tags=["Teams"])
async def get_team_players(
    team_id: int,
    recruiting_year: Optional[int] = None,
    position: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get player recruiting data for a specific team.

    Retrieves a paginated list of players on a team's roster, with optional
    filtering by recruiting year and position. Used to display team rosters
    and analyze position group strength.

    Part of: Preseason Enhancement Epic - Story 1.5

    Args:
        team_id: Unique team identifier
        recruiting_year: Optional filter by recruiting class year (e.g., 2024)
        position: Optional filter by position (e.g., "QB", "OL")
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100, max: 500)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.TeamPlayersResponse: Team player data including:
            - team_id: Team identifier
            - team_name: Team name
            - total: Total count of matching players
            - players: List of player objects with recruiting data

    Raises:
        HTTPException: 404 if team not found

    Example:
        Get all players for Georgia:
            GET /api/teams/42/players

        Get 2024 recruiting class:
            GET /api/teams/42/players?recruiting_year=2024

        Get all quarterbacks:
            GET /api/teams/42/players?position=QB

        Get 2024 offensive linemen:
            GET /api/teams/42/players?recruiting_year=2024&position=OL
    """
    from src.models.models import Player

    # Verify team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Build query
    query = db.query(Player).filter(Player.team_id == team_id)

    if recruiting_year:
        query = query.filter(Player.recruiting_year == recruiting_year)

    if position:
        query = query.filter(Player.position == position)

    # Get total count for pagination metadata
    total = query.count()

    # Get paginated results, ordered by rating (best first)
    players = query.order_by(Player.rating.desc().nulls_last()).offset(skip).limit(limit).all()

    return {
        "team_id": team_id,
        "team_name": team.name,
        "total": total,
        "players": players,
    }


@router.get("/api/teams/{team_id}/position-strength", tags=["Teams"])
async def get_team_position_strength(
    team_id: int,
    recruiting_year: Optional[int] = None,
    season: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Calculate position group strength for a team.

    Computes position-weighted strength scores based on player recruiting
    rankings. Returns both individual position group scores and the overall
    position strength bonus that would be applied to preseason ratings.

    Part of: Preseason Enhancement Epic - Story 1.5

    Args:
        team_id: Unique team identifier
        recruiting_year: Optional recruiting year to filter players (defaults to most recent)
        db: Database session (injected by FastAPI)

    Returns:
        dict: Position strength analysis including:
            - team_id: Team identifier
            - team_name: Team name
            - enabled: Whether position strength feature is enabled
            - position_scores: Score (0-100) for each position group
            - position_bonus: Overall bonus points (0-max_bonus)
            - max_bonus: Maximum possible bonus from configuration
            - weights: Position weights from configuration
            - recruiting_year: Year used for player data

    Raises:
        HTTPException: 404 if team not found
        HTTPException: 500 if position strength calculation fails

    Example:
        GET /api/teams/42/position-strength
        GET /api/teams/42/position-strength?recruiting_year=2024

    Response:
        {
            "team_id": 42,
            "team_name": "Georgia",
            "enabled": true,
            "position_scores": {
                "QB": 95.5,
                "OL": 92.3,
                "DL": 89.7,
                "DB": 88.2,
                ...
            },
            "position_bonus": 137.85,
            "max_bonus": 150,
            "weights": {
                "QB": 0.30,
                "OL": 0.25,
                ...
            },
            "recruiting_year": 2024
        }

    Note:
        - Returns 0.0 bonus if team has no player data
        - Respects enabled flag in position_weights.json
        - Uses most recent recruiting year if not specified
    """
    from src.core.position_service import (
        calculate_position_strength,
        get_position_group_scores,
        load_position_weights,
        resolve_roster_season,
    )
    from src.models.models import Player, Season

    # Verify team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Load configuration
    try:
        config = load_position_weights()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load position weights configuration: {str(e)}"
        )

    # Decide the data source (EPIC-039). "roster" scores from the actual roster
    # snapshot for the season; falls back to recruiting-class data per-team when
    # no snapshot exists.
    configured_source = config.get("source", "recruiting")
    source_used = "recruiting"
    roster_season = None

    if configured_source == "roster":
        target_season = season
        if target_season is None:
            active = db.query(Season).filter(Season.is_active == True).first()  # noqa: E712
            target_season = active.year if active else None
        roster_season = resolve_roster_season(db, team_id, target_season)
        if roster_season is not None:
            source_used = "roster"

    # Recruiting path needs a recruiting year (used for the response + no-data check)
    if source_used == "recruiting":
        if not recruiting_year:
            most_recent = (
                db.query(Player.recruiting_year)
                .filter(Player.team_id == team_id)
                .order_by(Player.recruiting_year.desc())
                .first()
            )
            recruiting_year = most_recent[0] if most_recent else None

        # No recruiting data and no roster snapshot → team has no player data
        if not recruiting_year:
            return {
                "team_id": team_id,
                "team_name": team.name,
                "enabled": config["enabled"],
                "source": "recruiting",
                "season": None,
                "position_scores": {group: 0.0 for group in config["weights"].keys()},
                "position_bonus": 0.0,
                "max_bonus": config["max_bonus"],
                "weights": config["weights"],
                "recruiting_year": None,
                "message": "No player data available for this team",
            }

    scoring_season = roster_season if source_used == "roster" else None

    # Calculate position scores
    try:
        position_scores = get_position_group_scores(
            team_id, db, config, season=scoring_season
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate position scores: {str(e)}"
        )

    # Calculate overall position bonus
    try:
        position_bonus = calculate_position_strength(
            team_id,
            config["weights"],
            db,
            config["max_bonus"],
            season=scoring_season,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate position strength: {str(e)}"
        )

    return {
        "team_id": team_id,
        "team_name": team.name,
        "enabled": config["enabled"],
        "source": source_used,
        "season": roster_season if source_used == "roster" else None,
        # EPIC-040: whether on-field production was blended into the scores
        "blend": source_used == "roster" and config.get("blend", False),
        "position_scores": position_scores,
        "position_bonus": position_bonus,
        "max_bonus": config["max_bonus"],
        "weights": config["weights"],
        "recruiting_year": recruiting_year if source_used == "recruiting" else None,
    }


@router.get("/api/teams/{team_id}/elo-history", tags=["Teams"])
def get_team_elo_history(team_id: int, season: int = None, db: Session = Depends(get_db)):
    """Get week-by-week ELO history for a team in a given season.

    Returns ELO rating snapshots ordered by week, excluding the synthetic
    week-999 final-snapshot entries. Week 0 is the preseason rating.

    Args:
        team_id: Unique team identifier
        season: Season year (defaults to active season)
        db: Database session (injected by FastAPI)

    Returns:
        List of {week, elo_rating} dicts ordered by week ascending.
    """
    if season is None:
        active = db.query(Season).filter(Season.is_active == True).first()
        season = active.year if active else 2025

    rows = (
        db.query(RankingHistory)
        .filter(
            RankingHistory.team_id == team_id,
            RankingHistory.season == season,
            RankingHistory.week != 999,
        )
        .order_by(RankingHistory.week.asc())
        .all()
    )

    return [{"week": r.week, "elo_rating": round(r.elo_rating, 2)} for r in rows]


@router.get("/api/teams/{team_id}/games", tags=["Teams"])
def get_team_games(team_id: int, season: int = None, db: Session = Depends(get_db)):
    """Get game log with ELO deltas for a team in a given season.

    Returns all processed games for a team, enriched with ELO before/after
    and the delta for each game. Games are ordered by week ascending.

    Args:
        team_id: Unique team identifier
        season: Season year (defaults to active season)
        db: Database session (injected by FastAPI)

    Returns:
        List of game objects with opponent info, scores, result, and ELO data.
    """
    if season is None:
        active = db.query(Season).filter(Season.is_active == True).first()
        season = active.year if active else 2025

    games = (
        db.query(Game)
        .filter(
            Game.season == season,
            Game.is_processed == True,
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
        )
        .order_by(Game.week.asc())
        .all()
    )

    result = []
    for g in games:
        is_home = g.home_team_id == team_id
        opp_id = g.away_team_id if is_home else g.home_team_id
        opp = db.query(Team).filter(Team.id == opp_id).first()

        team_score = g.home_score if is_home else g.away_score
        opp_score = g.away_score if is_home else g.home_score
        won = (
            team_score > opp_score
            if (team_score is not None and opp_score is not None)
            else None
        )

        # ELO after this week from ranking_history
        elo_after_row = (
            db.query(RankingHistory)
            .filter(
                RankingHistory.team_id == team_id,
                RankingHistory.season == season,
                RankingHistory.week == g.week,
            )
            .first()
        )
        # ELO before this week (prior week snapshot)
        elo_before_row = (
            db.query(RankingHistory)
            .filter(
                RankingHistory.team_id == team_id,
                RankingHistory.season == season,
                RankingHistory.week == g.week - 1,
            )
            .first()
        )

        elo_after = round(elo_after_row.elo_rating, 2) if elo_after_row else None
        elo_before = round(elo_before_row.elo_rating, 2) if elo_before_row else None
        elo_delta = (
            round(elo_after - elo_before, 2)
            if (elo_after is not None and elo_before is not None)
            else None
        )

        location = "Home" if is_home else ("Neutral" if g.is_neutral_site else "Away")

        result.append(
            {
                "week": g.week,
                "opponent": opp.name if opp else "Unknown",
                "opponent_id": opp_id,
                "location": location,
                "team_score": team_score,
                "opponent_score": opp_score,
                "result": ("W" if won else ("L" if won is False else None)),
                "elo_before": elo_before,
                "elo_after": elo_after,
                "elo_delta": elo_delta,
                "is_fcs": getattr(opp, "is_fcs", False) if opp else False,
            }
        )

    return result


@router.get("/api/teams/{team_id}/preseason", tags=["Teams"])
def get_team_preseason(team_id: int, season: int = None, db: Session = Depends(get_db)):
    """Get preseason ELO rating for a team (week 0 snapshot).

    Args:
        team_id: Unique team identifier
        season: Season year (defaults to active season)
        db: Database session (injected by FastAPI)

    Returns:
        dict with preseason_elo value (or None if no week-0 snapshot exists).
    """
    if season is None:
        active = db.query(Season).filter(Season.is_active == True).first()
        season = active.year if active else 2025

    row = (
        db.query(RankingHistory)
        .filter(
            RankingHistory.team_id == team_id,
            RankingHistory.season == season,
            RankingHistory.week == 0,
        )
        .first()
    )

    return {"preseason_elo": round(row.elo_rating, 2) if row else None}


@router.get("/api/matchup", tags=["Teams"])
def get_matchup(
    teamA: int,
    teamB: int,
    season: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Head-to-head team comparison: stats, ELO history, and win probabilities.

    Returns side-by-side data for two teams in a given season, including their
    current ELO ratings, records, ELO history, historical matchups between them,
    and win probability estimates for neutral, home-A, and home-B scenarios.

    Args:
        teamA: Team A's unique identifier
        teamB: Team B's unique identifier
        season: Season year (defaults to active season)
        db: Database session (injected by FastAPI)

    Returns:
        dict with team_a, team_b, elo_history_a, elo_history_b,
        head_to_head (historical results), and win probabilities.
    """
    if season is None:
        active = db.query(Season).filter(Season.is_active == True).first()
        season = active.year if active else 2025

    team_a = db.query(Team).filter(Team.id == teamA).first()
    team_b = db.query(Team).filter(Team.id == teamB).first()
    if not team_a or not team_b:
        raise HTTPException(status_code=404, detail="One or both teams not found")

    # Get current rankings for season-specific ELO/record/rank
    ranking_service = RankingService(db)
    rankings = ranking_service.get_current_rankings(season)
    ra = next((r for r in rankings if r["team_id"] == teamA), None)
    rb = next((r for r in rankings if r["team_id"] == teamB), None)

    HOME_FIELD = 65.0
    SCALE = 400.0

    def get_off_def_ppg(team_id):
        games = (
            db.query(Game)
            .filter(
                Game.season == season,
                Game.is_processed == True,
                Game.excluded_from_rankings == False,
                (Game.home_team_id == team_id) | (Game.away_team_id == team_id),
            )
            .all()
        )
        if not games:
            return None, None
        
        pf_sum = 0
        pa_sum = 0
        n = len(games)
        for g in games:
            if g.home_team_id == team_id:
                pf_sum += g.home_score if g.home_score is not None else 0
                pa_sum += g.away_score if g.away_score is not None else 0
            else:
                pf_sum += g.away_score if g.away_score is not None else 0
                pa_sum += g.home_score if g.home_score is not None else 0
        
        return round(pf_sum / n, 1), round(pa_sum / n, 1)

    def team_payload(team, ranking):
        elo = ranking["elo_rating"] if ranking else team.elo_rating
        # preseason week-0 snapshot
        pre_row = (
            db.query(RankingHistory)
            .filter(
                RankingHistory.team_id == team.id,
                RankingHistory.season == season,
                RankingHistory.week == 0,
            )
            .first()
        )
        off_ppg, def_ppg = get_off_def_ppg(team.id)
        wins = ranking["wins"] if ranking else 0
        losses = ranking["losses"] if ranking else 0
        win_pct = round((wins / (wins + losses) * 100), 1) if (wins + losses) > 0 else 0.0

        return {
            "id": team.id,
            "name": team.name,
            "conference": team.conference,
            "conference_name": team.conference_name,
            "elo_rating": round(elo, 1) if elo else None,
            "preseason_elo": round(pre_row.elo_rating, 1) if pre_row else None,
            "wins": wins,
            "losses": losses,
            "win_pct": win_pct,
            "rank": ranking["rank"] if ranking else None,
            "sos": round(ranking["sos"], 1) if ranking and ranking.get("sos") else None,
            "sos_rank": ranking["sos_rank"] if ranking else None,
            "off": off_ppg,
            "def": def_ppg,
        }

    # ELO history for both teams this season
    def elo_history(team_id):
        rows = (
            db.query(RankingHistory)
            .filter(
                RankingHistory.team_id == team_id,
                RankingHistory.season == season,
                RankingHistory.week != 999,
            )
            .order_by(RankingHistory.week.asc())
            .all()
        )
        return [{"week": r.week, "elo_rating": round(r.elo_rating, 2)} for r in rows]

    # Historical head-to-head games (all seasons, processed only)
    h2h_games = (
        db.query(Game)
        .filter(
            Game.is_processed == True,
            or_(
                and_(Game.home_team_id == teamA, Game.away_team_id == teamB),
                and_(Game.home_team_id == teamB, Game.away_team_id == teamA),
            ),
        )
        .order_by(Game.season.desc(), Game.week.asc())
        .limit(10)
        .all()
    )

    head_to_head = []
    wins_a = 0
    wins_b = 0
    for g in h2h_games:
        a_is_home = g.home_team_id == teamA
        a_score = g.home_score if a_is_home else g.away_score
        b_score = g.away_score if a_is_home else g.home_score
        winner_id = None
        if a_score is not None and b_score is not None:
            winner_id = teamA if a_score > b_score else teamB
            if winner_id == teamA:
                wins_a += 1
            else:
                wins_b += 1
        head_to_head.append({
            "season": g.season,
            "week": g.week,
            "score_a": a_score,
            "score_b": b_score,
            "winner_id": winner_id,
            "neutral_site": g.is_neutral_site,
        })

    # Win probabilities
    elo_a = (ra["elo_rating"] if ra else team_a.elo_rating) or 1500.0
    elo_b = (rb["elo_rating"] if rb else team_b.elo_rating) or 1500.0

    def win_prob(rating_a, rating_b):
        return round(1.0 / (1.0 + 10 ** ((rating_b - rating_a) / SCALE)), 4)

    win_prob_neutral = win_prob(elo_a, elo_b)
    win_prob_a_home = win_prob(elo_a + HOME_FIELD, elo_b)
    win_prob_b_home = win_prob(elo_a, elo_b + HOME_FIELD)

    return {
        "season": season,
        "team_a": team_payload(team_a, ra),
        "team_b": team_payload(team_b, rb),
        "elo_history_a": elo_history(teamA),
        "elo_history_b": elo_history(teamB),
        "head_to_head": head_to_head,
        "series_wins_a": wins_a,
        "series_wins_b": wins_b,
        "win_prob_neutral": win_prob_neutral,
        "win_prob_a_home": win_prob_a_home,
        "win_prob_b_home": win_prob_b_home,
    }


# ============================================================================
# GAME ENDPOINTS
# ============================================================================


