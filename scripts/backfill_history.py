#!/usr/bin/env python3
"""Import past seasons' games so the backtest has more than two seasons to work with.

``scripts/backtest_efficiency_blend.py`` replays seasons out of our own games
table, so its sample is capped by whatever that table holds. This adds older
seasons to it, one API call per week rather than one per game.

Defaults to writing a copy of the database rather than the live one: older
seasons are only wanted for backtesting, and adding them to production would put
seasons on the site that nothing else (rankings, snapshots, predictions) has
been built for. Point ``--db`` at the real file if you do want them there.

Usage:
    python3 scripts/backfill_history.py --seasons 2021 2022 2023
    python3 scripts/backfill_history.py --seasons 2021 --db cfb_rankings.db

Caveat worth knowing before trusting the numbers: teams carry today's conference
and today's preseason inputs, so a replayed 2021 starts every team from its
2026-informed preseason rating and applies 2026 conference tiers to 2021 games.
Absolute accuracy on older seasons is therefore understated. Comparisons between
two settings over the same seasons are still fair — both sides eat the same
handicap.
"""

import argparse
import shutil
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import os  # noqa: E402

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.importers.common import (  # noqa: E402
    apply_quarter_scores,
    find_existing_game,
    get_or_create_fcs_team,
    line_scores_from_game,
    parse_game_date,
)
from src.integrations.cfbd_client import CFBDClient  # noqa: E402
from src.models.models import Game, Team  # noqa: E402

MAX_WEEK = 15


def import_season(db, cfbd: CFBDClient, season: int) -> dict:
    """Import one season's regular-season games. Returns counts."""
    team_cache = {}
    imported = skipped = 0

    for week in range(1, MAX_WEEK + 1):
        # classification="fbs" keeps the D2/D3 slate out. Without it CFBD returns
        # every division, and each of those teams would land in our table as an
        # FCS placeholder — roughly a thousand junk games per season.
        games_data = (
            cfbd.get_games(season, week=week, season_type="regular", classification="fbs")
            or []
        )

        for game_data in games_data:
            home_name = game_data.get("homeTeam")
            away_name = game_data.get("awayTeam")
            if not home_name or not away_name:
                skipped += 1
                continue

            home_team = db.query(Team).filter(Team.name == home_name).first()
            if not home_team:
                home_team = get_or_create_fcs_team(db, home_name, team_cache)
            away_team = db.query(Team).filter(Team.name == away_name).first()
            if not away_team:
                away_team = get_or_create_fcs_team(db, away_name, team_cache)

            if home_team.is_fcs and away_team.is_fcs:
                skipped += 1  # FCS vs FCS tells us nothing; the main import skips these too
                continue

            if find_existing_game(db, home_team.id, away_team.id, week, season):
                skipped += 1
                continue

            game = Game(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=game_data.get("homePoints") or 0,
                away_score=game_data.get("awayPoints") or 0,
                week=week,
                season=season,
                is_neutral_site=game_data.get("neutralSite", False),
                game_date=parse_game_date(game_data),
                is_processed=False,
                excluded_from_rankings=home_team.is_fcs or away_team.is_fcs,
            )
            apply_quarter_scores(game, line_scores_from_game(game_data))
            db.add(game)
            imported += 1

        db.commit()
        print(f"  week {week:>2}: {imported} imported / {skipped} skipped (running)")

    return {"imported": imported, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument(
        "--db",
        default=str(project_root / "data" / "backtest_history.db"),
        help="database to write (default: data/backtest_history.db, a copy)",
    )
    parser.add_argument(
        "--from-db",
        default=str(project_root / "cfb_rankings.db"),
        help="database to copy when --db does not exist yet",
    )
    args = parser.parse_args()

    target = Path(args.db)
    if not target.exists():
        source = Path(args.from_db)
        if not source.exists():
            sys.exit(f"ERROR: no database to copy from: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
        print(f"Copied {source.name} -> {target}")

    api_key = os.getenv("CFBD_API_KEY")
    if not api_key:
        sys.exit("ERROR: CFBD_API_KEY not set")

    cfbd = CFBDClient(api_key)
    db = sessionmaker(bind=create_engine(f"sqlite:///{target}"))()

    try:
        for season in args.seasons:
            print(f"\nSeason {season} ({MAX_WEEK} API calls)")
            stats = import_season(db, cfbd, season)
            print(f"  done: {stats['imported']} imported, {stats['skipped']} skipped")
    finally:
        db.close()

    print(f"\n✓ Written to {target}")
    print(f"  Backtest it with: --db {target}")


if __name__ == "__main__":
    main()
