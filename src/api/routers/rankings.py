"""Rankings & postseason API routes.

Auto-extracted from the former monolithic main.py during the EPIC-043
backend modularization. Route paths and handler logic are unchanged.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.ranking_service import RankingService
from src.models import schemas
from src.models.database import get_db
from src.models.models import Game, RankingHistory, Season, Team

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/rankings", response_model=schemas.RankingsResponse, tags=["Rankings"])
async def get_rankings(
    season: Optional[int] = None,
    limit: Optional[int] = Query(25, ge=1, le=200),
    week: Optional[int] = Query(None, ge=0, le=20, description="Specific week snapshot (defaults to current week)"),
    db: Session = Depends(get_db),
):
    """Get current team rankings sorted by ELO rating.

    Retrieves the current rankings for a specified season (or active season
    if not specified). Rankings include ELO rating, wins/losses, strength of
    schedule, and rank information for each team.

    Args:
        season: Season year (defaults to active season)
        limit: Maximum number of teams to return (default: 25, max: 200)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.RankingsResponse: Rankings data including:
            - week: Current week number
            - season: Season year
            - rankings: List of team ranking objects
            - total_teams: Count of teams in rankings

    Example:
        Get top 25 teams for 2024:
            GET /api/rankings?season=2024&limit=25
    """
    # Get current season if not specified
    if not season:
        active_season = db.query(Season).filter(Season.is_active == True).first()
        season = active_season.year if active_season else datetime.now().year

    # Get current week for this season
    active_season = db.query(Season).filter(Season.year == season).first()
    season_current_week = active_season.current_week if active_season else 0

    # EPIC-042: Use requested week or fall back to season's current week
    target_week = week if week is not None else season_current_week
    current_week = target_week

    # Get rankings
    ranking_service = RankingService(db)
    rankings = ranking_service.get_current_rankings(season, limit=limit, week=target_week)

    # EPIC-031 Story 31.2: Compute rank changes and ELO history in batch
    team_ids = [r["team_id"] for r in rankings]

    # --- Rank change: batch-query ALL teams at (week - 1) ---
    prior_rank_by_team_id: dict = {}
    if current_week > 0:
        prior_week = current_week - 1
        prior_records = (
            db.query(RankingHistory.team_id, RankingHistory.elo_rating)
            .filter(
                RankingHistory.season == season,
                RankingHistory.week == prior_week,
            )
            .all()
        )
        if prior_records:
            # Sort by ELO descending to derive prior-week ranks
            sorted_prior = sorted(prior_records, key=lambda r: r.elo_rating, reverse=True)
            for prior_rank, row in enumerate(sorted_prior, start=1):
                prior_rank_by_team_id[row.team_id] = prior_rank

    # --- ELO history: batch-query for all teams in the result set ---
    elo_history_by_team_id: dict = {}
    if team_ids:
        history_records = (
            db.query(RankingHistory.team_id, RankingHistory.week, RankingHistory.elo_rating)
            .filter(
                RankingHistory.season == season,
                RankingHistory.team_id.in_(team_ids),
                RankingHistory.week != 999,
            )
            .order_by(RankingHistory.team_id, RankingHistory.week.asc())
            .all()
        )
        # Group by team_id; take last 8 entries
        from collections import defaultdict
        history_map: dict = defaultdict(list)
        for row in history_records:
            history_map[row.team_id].append(row.elo_rating)
        for tid, elos in history_map.items():
            elo_history_by_team_id[tid] = elos[-10:]  # spec: history is int[10]

    # EPIC-037: Batch-fetch espn_ids for all ranked teams
    espn_id_by_team: dict = {}
    if team_ids:
        team_rows = db.query(Team.id, Team.espn_id).filter(Team.id.in_(team_ids)).all()
        for row in team_rows:
            espn_id_by_team[row.id] = row.espn_id

    # Ticker spec §10: per-team season points-for/-against per game (OFF/DEF heat cells).
    # One pass over the season's scored games for the ranked teams.
    off_by_team: dict = {}  # team_id -> (points_for_sum, games)
    def_by_team: dict = {}  # team_id -> points_against_sum
    if team_ids:
        games = (
            db.query(
                Game.home_team_id, Game.away_team_id, Game.home_score, Game.away_score
            )
            .filter(
                Game.season == season,
                Game.is_processed == True,
                Game.excluded_from_rankings == False,
                (Game.home_team_id.in_(team_ids)) | (Game.away_team_id.in_(team_ids)),
            )
            .all()
        )
        counts: dict = {}
        for g in games:
            for tid, pf, pa in (
                (g.home_team_id, g.home_score, g.away_score),
                (g.away_team_id, g.away_score, g.home_score),
            ):
                if tid not in team_ids:
                    continue
                off_by_team[tid] = off_by_team.get(tid, 0) + (pf or 0)
                def_by_team[tid] = def_by_team.get(tid, 0) + (pa or 0)
                counts[tid] = counts.get(tid, 0) + 1

    # Attach rank_change, elo_history, espn_id, off, def to each ranking entry
    for entry in rankings:
        tid = entry["team_id"]
        current_rank = entry["rank"]

        if current_week == 0 or tid not in prior_rank_by_team_id:
            entry["rank_change"] = None
        else:
            prior_rank = prior_rank_by_team_id[tid]
            entry["rank_change"] = prior_rank - current_rank  # positive = moved up

        entry["elo_history"] = elo_history_by_team_id.get(tid, [])
        entry["espn_id"] = espn_id_by_team.get(tid)

        n = counts.get(tid, 0) if team_ids else 0
        entry["off"] = round(off_by_team.get(tid, 0) / n, 1) if n else None
        entry["def"] = round(def_by_team.get(tid, 0) / n, 1) if n else None

    return {
        "week": current_week,
        "season": season,
        "rankings": rankings,
        "total_teams": len(rankings),
    }


@router.get("/api/rankings/history", response_model=List[schemas.RankingHistory], tags=["Rankings"])
async def get_ranking_history(team_id: int, season: int, db: Session = Depends(get_db)):
    """Get historical rankings for a specific team across a season.

    Retrieves week-by-week ranking snapshots for a team, showing how their
    ELO rating, rank, wins/losses, and strength of schedule evolved throughout
    the season. Useful for generating ranking charts and tracking team progress.

    Args:
        team_id: Unique team identifier
        season: Season year (e.g., 2024)
        db: Database session (injected by FastAPI)

    Returns:
        List[schemas.RankingHistory]: Ordered list of weekly ranking snapshots

    Example:
        GET /api/rankings/history?team_id=42&season=2024
    """
    history = (
        db.query(RankingHistory)
        .filter((RankingHistory.team_id == team_id) & (RankingHistory.season == season))
        .order_by(RankingHistory.week)
        .all()
    )

    return history


# ── EPIC-042: Week/postseason endpoints ───────────────────────────────────────

WEEK_LABELS = {
    15: "Week 15 (Conf. Championships)",
    16: "CFP Round 1",
    17: "CFP Quarterfinals",
    18: "CFP Semifinals",
    19: "CFP National Championship",
}


@router.get("/api/rankings/weeks", tags=["Rankings"])
async def get_ranking_weeks(season: int, db: Session = Depends(get_db)):
    """Return weeks that have ranking snapshots for a season, plus postseason weeks from games."""
    from sqlalchemy import text as sa_text2

    snapshot_weeks = (
        db.query(RankingHistory.week)
        .filter(RankingHistory.season == season, RankingHistory.week <= 19)
        .distinct()
        .order_by(RankingHistory.week)
        .all()
    )
    snapshot_set = {row.week for row in snapshot_weeks}

    # Also expose postseason weeks that have processed games (even if no snapshot yet)
    postseason_weeks = (
        db.query(Game.week)
        .filter(
            Game.season == season,
            Game.week >= 16,
            Game.week <= 19,
            Game.is_processed == True,
        )
        .distinct()
        .order_by(Game.week)
        .all()
    )
    all_weeks = sorted(snapshot_set | {row.week for row in postseason_weeks})

    result = []
    for w in all_weeks:
        label = WEEK_LABELS.get(w, f"Week {w}")
        result.append({"week": w, "label": label, "has_snapshot": w in snapshot_set})
    return result


@router.get("/api/postseason", tags=["Rankings"])
async def get_postseason(season: int, db: Session = Depends(get_db)):
    """Return bowl, playoff, and conference championship games for a season."""
    games_all = (
        db.query(Game)
        .filter(
            Game.season == season,
            Game.game_type.in_(["bowl", "playoff", "conference_championship"]),
            Game.home_score + Game.away_score > 0,  # only games with scores
        )
        .order_by(Game.week, Game.game_date)
        .all()
    )

    result = []
    for g in games_all:
        home = g.home_team
        away = g.away_team
        if not home or not away:
            continue
        home_won = g.home_score > g.away_score
        result.append({
            "game_id": g.id,
            "week": g.week,
            "game_type": g.game_type,
            "postseason_name": g.postseason_name,
            "home_team_id": g.home_team_id,
            "home_team_name": home.name,
            "away_team_id": g.away_team_id,
            "away_team_name": away.name,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "is_neutral_site": g.is_neutral_site,
            "game_date": g.game_date.isoformat() if g.game_date else None,
            "winner_team_id": g.home_team_id if home_won else g.away_team_id,
            "winner_name": home.name if home_won else away.name,
            "loser_name": away.name if home_won else home.name,
            "winner_score": g.home_score if home_won else g.away_score,
            "loser_score": g.away_score if home_won else g.home_score,
        })
    return result


@router.get(
    "/api/preseason/components",
    response_model=List[schemas.PreseasonComponent],
    tags=["Rankings"],
)
async def get_preseason_components(
    season: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get raw preseason rating components for all FBS teams (EPIC-032).

    Returns each team's individual bonus contributions so the preseason
    simulator can recalculate rankings client-side with custom weights
    without making a server request on every slider change.

    Args:
        season: Season year (defaults to active season). Used to look up
                previous season ELO from ranking_history.
        db: Database session (injected by FastAPI)

    Returns:
        List of PreseasonComponent objects sorted by current_rating desc,
        one per FBS team. Each item includes base rating, all bonus
        components, previous season ELO, and current official rating.

    Example:
        GET /api/preseason/components?season=2026
    """
    if not season:
        active_season = db.query(Season).filter(Season.is_active == True).first()
        season = active_season.year if active_season else datetime.now().year

    ranking_service = RankingService(db)
    return ranking_service.get_preseason_components(season)


@router.post("/api/rankings/save", response_model=schemas.SuccessResponse, tags=["Rankings"])
async def save_rankings(season: int, week: int, db: Session = Depends(get_db)):
    """Save current rankings to historical snapshots.

    Creates a snapshot of current rankings for all teams at a specific week,
    storing ELO ratings, ranks, wins/losses, and strength of schedule data
    in the ranking_history table for future reference and charting.

    Args:
        season: Season year (e.g., 2024)
        week: Week number to save (0-15)
        db: Database session (injected by FastAPI)

    Returns:
        schemas.SuccessResponse: Confirmation message with saved week info

    Example:
        POST /api/rankings/save?season=2024&week=5
    """
    ranking_service = RankingService(db)
    ranking_service.save_weekly_rankings(season, week)

    return {
        "message": f"Rankings saved for Week {week}, {season}",
        "data": {"season": season, "week": week},
    }


# ============================================================================
# SEASON ENDPOINTS
# ============================================================================


