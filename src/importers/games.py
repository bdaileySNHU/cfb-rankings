"""Regular-season game import from the CFBD API."""

import sys

from src.core.ranking_service import RankingService, create_and_store_prediction
from src.importers.common import (
    apply_quarter_scores,
    fetch_line_scores,
    find_existing_game,
    get_or_create_fcs_team,
    parse_game_date,
)
from src.importers.polls import import_ap_poll_rankings
from src.importers.validation import get_week_statistics
from src.integrations.cfbd_client import CFBDClient
from src.models.models import Game


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
            existing_game = find_existing_game(db, home_team.id, away_team.id, week, year)

            if existing_game:
                # Game exists - decide whether to update, skip, or process
                if is_future_game:
                    # Still a future game (no scores yet)
                    # But update game_date if available and not already set
                    new_game_date = parse_game_date(game_data)
                    if new_game_date and existing_game.game_date != new_game_date:
                        print(
                            f"    Updating game date: {game_desc} -> {new_game_date.strftime('%Y-%m-%d')}"
                        )
                        existing_game.game_date = new_game_date
                        db.commit()
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
                    line_scores = fetch_line_scores(
                        cfbd, game_data, year, week, home_team_name, away_team_name
                    )
                    apply_quarter_scores(existing_game, line_scores)

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
                    # Already processed - but check if we need to update game_date
                    new_game_date = parse_game_date(game_data)
                    if new_game_date and existing_game.game_date != new_game_date:
                        print(
                            f"    Updating game date: {game_desc} -> {new_game_date.strftime('%Y-%m-%d')}"
                        )
                        existing_game.game_date = new_game_date
                        db.commit()
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
                line_scores = fetch_line_scores(
                    cfbd, game_data, year, week, home_team_name, away_team_name
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
            )

            # EPIC-021: Apply and validate quarter scores if present
            apply_quarter_scores(game, line_scores)

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
