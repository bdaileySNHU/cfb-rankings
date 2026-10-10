"""Poll, rating and betting-line imports from the CFBD API (EPIC-010, SP+/spread comparison)."""

from statistics import median

from src.integrations.cfbd_client import CFBDClient
from src.models.models import APPollRanking, BettingLine, Game, SPPlusRating


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


def _median_of(lines: list, key: str):
    """Median of one field across providers, or None if nobody posted it."""
    values = [l[key] for l in lines if l.get(key) is not None]
    return median(values) if values else None


def import_betting_lines(cfbd: CFBDClient, db, team_objects: dict, year: int) -> int:
    """
    Store the consensus (median across providers) closing spread for each game,
    plus over/under and moneylines when providers post them.

    Upserts: a line keeps moving until kickoff, and re-running after the game
    settles it on the closing number. Safe to run for past seasons.

    Lines are matched to games on (home, away) team. CFBD numbers postseason
    weeks from 1 while ours run 16+, so week is only a tie-breaker for the rare
    pairing that meets twice in a season (e.g. a conference title rematch).

    Returns:
        int: Number of games with a line stored or updated
    """
    entries = cfbd.get_betting_lines(year)
    if not entries:
        return 0

    by_matchup = {}
    for entry in entries:
        home = team_objects.get(entry.get("homeTeam"))
        away = team_objects.get(entry.get("awayTeam"))
        lines = entry.get("lines") or []
        consensus = {
            field: _median_of(lines, key)
            for field, key in (("spread", "spread"), ("over_under", "overUnder"),
                               ("home_moneyline", "homeMoneyline"), ("away_moneyline", "awayMoneyline"))
        }
        if home and away and consensus["spread"] is not None:
            by_matchup.setdefault((home.id, away.id), []).append((entry, consensus))

    existing = {
        bl.game_id: bl
        for bl in db.query(BettingLine).join(Game).filter(Game.season == year).all()
    }

    stored = 0
    for game in db.query(Game).filter(Game.season == year).all():
        candidates = by_matchup.get((game.home_team_id, game.away_team_id))
        if not candidates:
            continue
        # ponytail: same-week regular-season match, else the latest meeting.
        # Breaks only if a pairing meets twice in the postseason.
        same_week = [
            c for c in candidates
            if c[0].get("seasonType") == "regular" and c[0].get("week") == game.week
        ]
        _, consensus = same_week[0] if same_week else max(candidates, key=lambda c: c[0].get("startDate") or "")
        for ml in ("home_moneyline", "away_moneyline"):
            if consensus[ml] is not None:
                consensus[ml] = round(consensus[ml])

        line = existing.get(game.id)
        if line is None:
            db.add(BettingLine(game_id=game.id, **consensus))
        elif any(getattr(line, k) != v for k, v in consensus.items()):
            for k, v in consensus.items():
                setattr(line, k, v)
        else:
            continue
        stored += 1

    db.commit()
    return stored
