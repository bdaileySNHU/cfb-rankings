"""Postseason game imports: conference championships, bowls, and CFP playoffs.

Each importer picks its games out of the CFBD feed and works out the stored
week and label; _import_games does the shared team lookup, upsert, and
rating processing.
"""

from src.core.ranking_service import create_and_store_prediction
from src.importers.common import (
    apply_quarter_scores,
    find_existing_game,
    parse_game_date,
)
from src.integrations.cfbd_client import CFBDClient
from src.models.models import Game

CONFERENCE_KEYWORDS = [
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

PLAYOFF_KEYWORDS = [
    "playoff",
    "semifinal",
    "quarterfinal",
    "national championship",
    "first round",
    "cfp",
]

SEMIFINAL_BOWLS = ["Rose", "Sugar", "Orange", "Cotton", "Peach", "Fiesta"]


def _scores(game_data):
    """Return (home, away, is_future) from a CFBD game; missing points count as 0."""
    home_score = game_data.get("homePoints", 0) or 0
    away_score = game_data.get("awayPoints", 0) or 0
    is_future = (home_score == 0 and away_score == 0) or game_data.get("completed") is False
    return home_score, away_score, is_future


def _line_scores(cfbd, game_data, year, week):
    return cfbd.get_game_line_scores(
        game_id=game_data.get("id", 0),
        year=year,
        week=week,
        home_team=game_data.get("homeTeam"),
        away_team=game_data.get("awayTeam"),
    )


def _process(ranking_service, game, label):
    """Run a game through the ratings; a failure is logged, not raised."""
    try:
        result = ranking_service.process_game(game)
        print(f"    ✓ {label}: {result['winner_name']} defeats {result['loser_name']} {result['score']}")
        return True
    except Exception as e:
        print(f"    ⚠️  {label}: processing failed: {e}")
        return False


def _import_games(
    cfbd, db, team_objects, year, ranking_service, entries, game_type, needs_retag,
    title, predict_future=False,
):
    """Upsert postseason games and process the completed ones.

    Args:
        entries: (game_data, week, label) per feed game. label is stored as
            postseason_name, except for conference championships, which store none.
        game_type: game_type for new rows (and re-tagged existing rows).
        needs_retag: predicate on an existing Game — True means overwrite its
            game_type and postseason_name.
        predict_future: store a prediction for each newly created scheduled game.

    Returns:
        int: games inserted plus existing games that just got their final score.
    """
    if not entries:
        print(f"No {title.lower()} games found")
        return 0
    print(f"Found {len(entries)} {title.lower()} games")

    # Conference championships carry no postseason_name; their label is the raw notes.
    store_name = game_type != "conference_championship"
    imported = skipped = processed = 0

    for game_data, week, label in entries:
        home_name = game_data.get("homeTeam")
        away_name = game_data.get("awayTeam")
        name = label if store_name else None

        if home_name not in team_objects or away_name not in team_objects:
            print(f"  ⚠️  Skipping {label}: Teams not found ({home_name} vs {away_name})")
            skipped += 1
            continue

        home_team = team_objects[home_name]
        away_team = team_objects[away_name]
        home_score, away_score, is_future = _scores(game_data)
        existing = find_existing_game(db, home_team.id, away_team.id, week, year)

        if existing:
            if needs_retag(existing):
                existing.game_type = game_type
                if store_name:
                    existing.postseason_name = name

            new_game_date = parse_game_date(game_data)
            if new_game_date and existing.game_date != new_game_date:
                existing.game_date = new_game_date

            if existing.home_score == 0 and existing.away_score == 0 and not is_future:
                print(
                    f"  ✓ Updating scores for {label}: {away_name} vs {home_name} "
                    f"({away_score}-{home_score})"
                )
                existing.home_score = home_score
                existing.away_score = away_score
                existing.is_neutral_site = game_data.get("neutralSite", True)
                existing.is_processed = False  # Mark for reprocessing
                apply_quarter_scores(existing, _line_scores(cfbd, game_data, year, week))
                db.commit()
                db.refresh(existing)
                processed += _process(ranking_service, existing, label)
                imported += 1
            else:
                db.commit()  # metadata updates only
                state = "Already processed" if not is_future and existing.is_processed else "Updated metadata"
                print(f"  ✓ {label}: {state} (Week {week})")
                skipped += 1
            continue

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=home_score,
            away_score=away_score,
            week=week,
            season=year,
            is_neutral_site=game_data.get("neutralSite", True),  # postseason is mostly neutral
            game_type=game_type,
            postseason_name=name,
            game_date=parse_game_date(game_data),
        )
        if not is_future:
            apply_quarter_scores(game, _line_scores(cfbd, game_data, year, week))
        db.add(game)
        db.commit()
        db.refresh(game)
        imported += 1

        if not is_future:
            processed += _process(ranking_service, game, label)
        else:
            print(f"  ✓ Imported (scheduled): {label} - {away_name} @ {home_name}")
            if predict_future:
                prediction = create_and_store_prediction(db, game)
                if prediction:
                    print(f"      → Prediction stored ({prediction.predicted_winner.name} favored)")

    print()
    print("=" * 80)
    print(f"{title.upper()} IMPORT SUMMARY")
    print(f"Imported: {imported}")
    print(f"Processed for Rankings: {processed}")
    if skipped:
        print(f"Skipped: {skipped}")
    print("=" * 80)
    print()
    return imported


def import_conference_championships(
    cfbd: CFBDClient, db, team_objects: dict, year: int, ranking_service
):
    """
    Import conference championship games from CFBD API.

    EPIC-022: Conference championships are regular-season games in weeks 14-15
    with "Championship" in the notes, excluding CFP games. FBS only.

    Returns:
        int: Number of conference championship games imported
    """
    print(f"\nImporting conference championship games for {year}...")
    print("=" * 80)

    entries = []
    for week in [14, 15]:
        for game in cfbd.get_games(year, week=week, season_type="regular", classification="fbs") or []:
            notes = game.get("notes", "") or ""
            is_championship = "Championship" in notes or "championship" in notes
            is_cfp = "playoff" in notes.lower() or "semifinal" in notes.lower()
            if is_championship and not is_cfp:
                entries.append((game, game.get("week", 14), notes))

    return _import_games(
        cfbd, db, team_objects, year, ranking_service, entries,
        game_type="conference_championship",
        needs_retag=lambda g: not g.game_type,
        title="Conference championship",
        predict_future=True,
    )


def import_bowl_games(cfbd: CFBDClient, db, team_objects: dict, year: int, ranking_service):
    """
    Import bowl games from CFBD API.

    EPIC-023: Postseason games that are neither conference championships nor
    playoff games. CFBD sometimes reports week=1 for unscheduled bowls, so any
    week below 15 is stored as 16.

    Returns:
        int: Number of bowl games imported
    """
    print(f"\nImporting bowl games for {year}...")
    print("=" * 80)

    entries = []
    for game in cfbd.get_games(year, season_type="postseason", classification="fbs") or []:
        notes = game.get("notes", "") or ""
        is_championship = "Championship" in notes or "championship" in notes
        if is_championship and any(c in notes for c in CONFERENCE_KEYWORDS):
            continue
        if any(k in notes.lower() for k in ["playoff", "semifinal", "national championship"]):
            continue
        week = game.get("week", 16)
        entries.append((game, 16 if week < 15 else week, notes or "Bowl Game"))

    return _import_games(
        cfbd, db, team_objects, year, ranking_service, entries,
        game_type="bowl",
        needs_retag=lambda g: not g.game_type or not g.postseason_name,
        title="Bowl",
    )


def _playoff_round(notes: str, year: int, api_week: int) -> tuple[int, str]:
    """Map CFP notes to (stored week, round label).

    12-team format (2024+): First Round 16, Quarterfinals 17, Semifinals 18, Championship 19.
    4-team format (2014-2023): Semifinals 17, Championship 18.
    """
    n = notes.lower()
    if "national championship" in n:
        return (19 if year >= 2024 else 18), "CFP National Championship"
    if "semifinal" in n:
        bowl = next((b for b in SEMIFINAL_BOWLS if b.lower() in n), None)
        return (18 if year >= 2024 else 17), f"CFP Semifinal - {bowl} Bowl" if bowl else "CFP Semifinal"
    if "quarterfinal" in n:
        return 17, "CFP Quarterfinal"
    if "first round" in n:
        return 16, "CFP First Round"
    return (17 if api_week < 15 else api_week), "CFP Game"


def import_playoff_games(cfbd: CFBDClient, db, team_objects: dict, year: int, ranking_service):
    """
    Import College Football Playoff games from CFBD API.

    EPIC-023 Story 23.2: Handles both the 4-team (2014-2023) and 12-team (2024+)
    formats; see _playoff_round for the week mapping.

    Returns:
        int: Number of playoff games imported
    """
    print(f"\nImporting CFP playoff games for {year}...")
    print("=" * 80)

    entries = []
    for game in cfbd.get_games(year, season_type="postseason", classification="fbs") or []:
        notes = game.get("notes", "") or ""
        if any(k in notes.lower() for k in PLAYOFF_KEYWORDS):
            week, label = _playoff_round(notes, year, game.get("week", 17))
            entries.append((game, week, label))

    return _import_games(
        cfbd, db, team_objects, year, ranking_service, entries,
        game_type="playoff",
        needs_retag=lambda g: g.game_type != "playoff",
        title="CFP playoff",
    )
