#!/usr/bin/env python3
"""Rebuild a past season's week-by-week ranking_history from a point-in-time replay.

Why: an old full rebuild called save_weekly_rankings() in a loop, which stamps the
teams table's CURRENT ratings under every week. Prod 2025 weeks 1-15 all hold
end-of-regular-season ratings (Indiana 15-0 at week 1), so every prediction
backfilled from them graded ELO with hindsight.

How: replay the seasons chronologically on a throwaway copy of the database,
reusing the efficiency-blend backtest's replay pieces. Week 0 is the preseason
snapshot; week N is the snapshot after week N's games, efficiency blended from
PPA through week N only -- the same semantics the weekly cron writes. Then only
those seasons' weeks 0-20 are copied back into the real database. Nothing else
in it is touched: not teams, not games, not the week=999 final snapshots that
seed the next season's preseason.

Then re-price the predictions from the rebuilt snapshots:
    python scripts/backfill_historical_predictions.py --season 2025 --refresh

Known limits (same as the backtest): preseason inputs -- recruiting, portal,
returning production, conference tiers -- are today's values on the teams table,
and the first season in --seasons has no prior season to regress toward. So
list one season before the one you care about, and treat it as warm-up only.

Usage:
    python scripts/rebuild_season_history.py --seasons 2024 2025
    python scripts/rebuild_season_history.py --seasons 2024 2025 --db data/backtest_history.db
"""

import argparse
import logging
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backtest_efficiency_blend import build_weekly_efficiency, load_ppa_games  # noqa: E402
from src.core.ranking_service import RankingService  # noqa: E402
from src.models.models import Game, RankingHistory, Team  # noqa: E402

MAX_SNAPSHOT_WEEK = 20  # 999 is the final-season sentinel; never copied back


def replay(work_db: Path, season: int, weekly_eff: dict) -> None:
    """Replay one season in work_db, writing a snapshot after every week."""
    session = sessionmaker(bind=create_engine(f"sqlite:///{work_db}"))()
    service = RankingService(session)

    def set_efficiency(through_week: int) -> None:
        # weekly_eff[w] = PPA from games strictly before w. Postseason PPA uses
        # its own week numbering, so efficiency freezes at the regular season's.
        eff = weekly_eff.get(min(through_week + 1, max(weekly_eff)), {})
        for team in session.query(Team).all():
            team.offense_ppa, team.defense_ppa = eff.get(team.name, (None, None))
        session.commit()

    service.reset_season(season)
    session.query(Game).filter(Game.season == season).update({Game.is_processed: False})
    session.commit()
    set_efficiency(0)
    service.save_weekly_rankings(season, 0)

    weeks = sorted(w for (w,) in session.query(Game.week).filter(Game.season == season).distinct())
    for week in weeks:
        for game in session.query(Game).filter(
            Game.season == season,
            Game.week == week,
            Game.excluded_from_rankings == False,  # noqa: E712
        ):
            if game.home_score == 0 and game.away_score == 0:
                continue  # unplayed
            try:
                service.process_game(game)
            except ValueError:
                continue  # invalid for ranking purposes; skipped like production
        set_efficiency(week)
        service.save_weekly_rankings(season, week)

    # Seed the next replayed season's preseason regression.
    service.save_final_season_snapshot(season)
    session.close()


def copy_back(work_db: Path, target_db: Path, seasons: list) -> int:
    """Replace the seasons' weeks 0-MAX_SNAPSHOT_WEEK in target with work_db's."""
    placeholders = ",".join("?" * len(seasons))
    where = f"season IN ({placeholders}) AND week <= {MAX_SNAPSHOT_WEEK}"
    conn = sqlite3.connect(target_db)
    try:
        conn.execute("ATTACH DATABASE ? AS work", (str(work_db),))
        cols = ", ".join(r[1] for r in conn.execute("PRAGMA table_info(ranking_history)") if r[1] != "id")
        with conn:  # one transaction: all or nothing
            conn.execute(f"DELETE FROM ranking_history WHERE {where}", seasons)
            cur = conn.execute(
                f"INSERT INTO ranking_history ({cols}) SELECT {cols} FROM work.ranking_history WHERE {where}",
                seasons,
            )
        return cur.rowcount
    finally:
        conn.close()


def main():
    logging.getLogger("src").setLevel(logging.ERROR)  # reset_season logs per team

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seasons", type=int, nargs="+", required=True,
                        help="Chronological chain; the first is warm-up only")
    parser.add_argument("--db", default=str(project_root / "cfb_rankings.db"))
    parser.add_argument("--dry-run", action="store_true", help="Replay but do not write back")
    args = parser.parse_args()

    target_db = Path(args.db)
    if not target_db.exists():
        sys.exit(f"ERROR: database not found: {target_db}")
    seasons = sorted(args.seasons)

    tmpdir = Path(tempfile.mkdtemp(prefix="rebuild-history-"))
    try:
        work_db = tmpdir / "work.db"
        shutil.copy(target_db, work_db)
        # Start the chain clean so it reads its own snapshots, not the leaked ones.
        conn = sqlite3.connect(work_db)
        with conn:
            conn.execute(
                f"DELETE FROM ranking_history WHERE season IN ({','.join('?' * len(seasons))})",
                seasons,
            )
        conn.close()

        for season in seasons:
            print(f"Replaying {season}...")
            replay(work_db, season, build_weekly_efficiency(load_ppa_games(season, project_root / "data")))

        if args.dry_run:
            print("Dry run: target database untouched.")
            return

        backup = target_db.with_suffix(target_db.suffix + ".pre-rebuild")
        shutil.copy(target_db, backup)
        print(f"Backed up {target_db.name} -> {backup.name}")
        rows = copy_back(work_db, target_db, seasons)
        print(f"Wrote {rows} ranking_history rows for {seasons}")
        print("Next: python scripts/backfill_historical_predictions.py --season <year> --refresh")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
