"""AP Poll ranking import from the CFBD API (EPIC-010)."""

from src.integrations.cfbd_client import CFBDClient
from src.models.models import APPollRanking


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
