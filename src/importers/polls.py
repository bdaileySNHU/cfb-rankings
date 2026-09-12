"""Poll and rating imports from the CFBD API (EPIC-010, SP+ comparison)."""

from src.integrations.cfbd_client import CFBDClient
from src.models.models import APPollRanking, SPPlusRating


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
                # Without this the row is matched on team/week alone, so a second
                # poll stored in this table would overwrite the AP row instead of
                # sitting beside it. get_ap_poll() filters to AP today, which is
                # the only reason that has never bitten.
                APPollRanking.poll_type == "AP Top 25",
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


def import_sp_plus_ratings(cfbd: CFBDClient, db, team_objects: dict, year: int, week: int) -> int:
    """
    Snapshot SP+ ratings for a week.

    SP+ rates every FBS team where the AP Top 25 reaches 25, so it can grade
    predictions on the unranked-vs-unranked games that are most of the schedule.

    Write-once per week, deliberately. CFBD's /ratings/sp has no week dimension:
    it serves one season-level rating revised in place as results come in. If
    this upserted, every run would restamp week 1 with today's SP+ -- a rating
    that has already seen week 1's results -- and the comparison would flatter
    SP+ with hindsight it did not have. So the first snapshot of a week is the
    one that stands, and past weeks cannot be backfilled at all.

    Args:
        cfbd: CFBD client instance
        db: Database session
        team_objects: Dictionary mapping team names to Team objects
        year: Season year
        week: Week number to snapshot under

    Returns:
        int: Number of ratings stored (0 if this week is already snapshotted)
    """
    # Checking first also spares the API call on weeks already recorded.
    already_snapshotted = (
        db.query(SPPlusRating)
        .filter(SPPlusRating.season == year, SPPlusRating.week == week)
        .first()
    )
    if already_snapshotted:
        return 0

    ratings = cfbd.get_sp_ratings(year)
    if not ratings:
        return 0

    stored = 0
    for entry in ratings:
        team = team_objects.get(entry.get("team"))
        if not team:
            # SP+ carries a few non-FBS and renamed entries; skip quietly rather
            # than print ~10 warnings a week.
            continue

        ranking = entry.get("ranking")
        rating = entry.get("rating")
        if ranking is None or rating is None:
            continue

        db.add(
            SPPlusRating(
                season=year,
                week=week,
                team_id=team.id,
                ranking=ranking,
                rating=float(rating),
            )
        )
        stored += 1

    db.commit()
    return stored
