"""Postseason game imports: conference championships, bowls, and CFP playoffs."""

from src.core.ranking_service import create_and_store_prediction
from src.importers.common import (
    apply_quarter_scores,
    find_existing_game,
    parse_game_date,
)
from src.integrations.cfbd_client import CFBDClient
from src.models.models import Game


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
        existing_game = find_existing_game(db, home_team.id, away_team.id, week, year)

        if existing_game:
            # Get scores to check if game has been played
            home_score = game_data.get("homePoints", 0) or 0
            away_score = game_data.get("awayPoints", 0) or 0
            is_future_game = home_score == 0 and away_score == 0

            # Update game_type if not set
            if not existing_game.game_type:
                existing_game.game_type = "conference_championship"

            # Update game_date if available
            new_game_date = parse_game_date(game_data)
            if new_game_date and existing_game.game_date != new_game_date:
                existing_game.game_date = new_game_date

            # Check if we need to update scores (future game that now has scores)
            if (
                existing_game.home_score == 0
                and existing_game.away_score == 0
                and not is_future_game
            ):
                print(
                    f"  ✓ Updating scores for {notes}: {away_team_name} vs {home_team_name} ({away_score}-{home_score})"
                )
                existing_game.home_score = home_score
                existing_game.away_score = away_score
                existing_game.is_neutral_site = game_data.get("neutralSite", True)
                existing_game.is_processed = False  # Mark for reprocessing

                # Fetch and update quarter scores
                line_scores = cfbd.get_game_line_scores(
                    game_id=game_data.get("id", 0),
                    year=year,
                    week=week,
                    home_team=home_team_name,
                    away_team=away_team_name,
                )
                apply_quarter_scores(existing_game, line_scores)

                db.commit()
                db.refresh(existing_game)

                # Process game for rankings
                result = ranking_service.process_game(existing_game)
                winner = result["winner_name"]
                loser = result["loser_name"]
                score = result["score"]
                print(f"    ✓ Processed: {winner} defeats {loser} {score}")
                processed += 1
                imported += 1
            else:
                # Just commit metadata updates
                db.commit()
                if not is_future_game and existing_game.is_processed:
                    print(f"  ✓ {notes}: Already processed (Week {week})")
                else:
                    print(f"  ✓ {notes}: Updated metadata (Week {week})")
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
        )

        # EPIC-021: Apply and validate quarter scores if present
        apply_quarter_scores(game, line_scores)

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
        existing_game = find_existing_game(db, home_team.id, away_team.id, week, year)

        if existing_game:
            # Get scores to check if game has been played
            home_score = game_data.get("homePoints", 0) or 0
            away_score = game_data.get("awayPoints", 0) or 0
            is_future_game = home_score == 0 and away_score == 0

            # Update game_type and postseason_name if not set
            if not existing_game.game_type or not existing_game.postseason_name:
                existing_game.game_type = "bowl"
                existing_game.postseason_name = bowl_name

            # Update game_date if available
            new_game_date = parse_game_date(game_data)
            if new_game_date and existing_game.game_date != new_game_date:
                existing_game.game_date = new_game_date

            # Check if we need to update scores (future game that now has scores)
            if (
                existing_game.home_score == 0
                and existing_game.away_score == 0
                and not is_future_game
            ):
                print(
                    f"  ✓ Updating scores for {bowl_name}: {away_team_name} vs {home_team_name} ({away_score}-{home_score})"
                )
                existing_game.home_score = home_score
                existing_game.away_score = away_score
                existing_game.is_neutral_site = game_data.get("neutralSite", True)
                existing_game.is_processed = False  # Mark for reprocessing

                # Fetch and update quarter scores
                line_scores = cfbd.get_game_line_scores(
                    game_id=game_data.get("id", 0),
                    year=year,
                    week=week,
                    home_team=home_team_name,
                    away_team=away_team_name,
                )
                apply_quarter_scores(existing_game, line_scores)

                db.commit()
                db.refresh(existing_game)

                # Process game for rankings
                try:
                    ranking_service.process_game(existing_game)
                    processed += 1
                    print(f"    ✓ Processed for rankings")
                except Exception as e:
                    print(f"    ⚠️  Processing failed: {str(e)}")

                imported += 1
            else:
                # Just commit metadata updates
                db.commit()
                if not is_future_game and existing_game.is_processed:
                    print(f"  ✓ {bowl_name}: Already processed")
                else:
                    print(f"  ✓ {bowl_name}: Updated metadata")
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
        )
        # EPIC-021: Apply and validate quarter scores if present
        apply_quarter_scores(game, line_scores)

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
        existing_game = find_existing_game(db, home_team.id, away_team.id, week, year)

        if existing_game:
            # Get scores to check if game has been played
            home_score = game_data.get("homePoints", 0) or 0
            away_score = game_data.get("awayPoints", 0) or 0
            is_future_game = home_score == 0 and away_score == 0

            # Update game_type and postseason_name if not set
            if not existing_game.game_type or existing_game.game_type != "playoff":
                existing_game.game_type = "playoff"
                existing_game.postseason_name = playoff_round

            # Update game_date if available
            new_game_date = parse_game_date(game_data)
            if new_game_date and existing_game.game_date != new_game_date:
                existing_game.game_date = new_game_date

            # Check if we need to update scores (future game that now has scores)
            if (
                existing_game.home_score == 0
                and existing_game.away_score == 0
                and not is_future_game
            ):
                print(
                    f"  ✓ Updating scores for {playoff_round}: {away_team_name} vs {home_team_name} ({away_score}-{home_score})"
                )
                existing_game.home_score = home_score
                existing_game.away_score = away_score
                existing_game.is_neutral_site = game_data.get("neutralSite", True)
                existing_game.is_processed = False  # Mark for reprocessing

                # Fetch and update quarter scores
                line_scores = cfbd.get_game_line_scores(
                    game_id=game_data.get("id", 0),
                    year=year,
                    week=week,
                    home_team=home_team_name,
                    away_team=away_team_name,
                )
                apply_quarter_scores(existing_game, line_scores)

                db.commit()
                db.refresh(existing_game)

                # Process game for rankings
                try:
                    ranking_service.process_game(existing_game)
                    processed += 1
                    print(f"    ✓ Processed for rankings")
                except Exception as e:
                    print(f"    ⚠️  Processing failed: {str(e)}")

                imported += 1
            else:
                # Just commit metadata updates
                db.commit()
                if not is_future_game and existing_game.is_processed:
                    print(f"  ✓ {playoff_round}: Already processed")
                else:
                    print(f"  ✓ {playoff_round}: Updated metadata")
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
        )
        # EPIC-021: Apply and validate quarter scores if present
        apply_quarter_scores(game, line_scores)

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
