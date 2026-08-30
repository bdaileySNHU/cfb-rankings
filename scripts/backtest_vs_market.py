#!/usr/bin/env python3
"""Score our predictions against the closing betting line.

The market is the strongest cheap benchmark available: a closing spread is a
consensus forecast with real money behind it, so "how far off the market are we"
is a more honest question than "how often are we right", which schedule strength
alone can flatter.

Lines are a yardstick here, never a model input. Feeding the spread back into
the ratings would just teach the model to copy Vegas.

Three things come out of it:

  Margin MAE   Our predicted margin against the market's, both against what
               actually happened. The market should win; the gap is the number
               to watch shrink.
  Straight up  Who each side picked to win, and who was right more often.
  ATS          Whether our disagreements with the line are worth anything. This
               is the demanding one: beating a closing spread reliably is not
               something a rating system is expected to do, and anything near
               50% means we are simply reading the same game the market is.

Reuses the same point-in-time replay as the blend backtest, so ratings are
whatever was knowable before kickoff.

Usage:
    python3 scripts/backtest_vs_market.py --db data/backtest_history.db
    python3 scripts/backtest_vs_market.py --seasons 2025 --weight 0.4
"""

import argparse
import json
import logging
import os
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for backtest_efficiency_blend

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.core.ranking_service import (  # noqa: E402
    EFFICIENCY_MIN_WEEK,
    EFFICIENCY_WEIGHT,
    blend_rating,
)
from src.integrations.cfbd_client import CFBDClient  # noqa: E402

from backtest_efficiency_blend import (  # noqa: E402
    HOME_FIELD_ADVANTAGE,
    POINTS_PER_100_ELO,
    build_weekly_efficiency,
    load_ppa_games,
    replay_seasons,
)


def load_lines(year: int, cache_dir: Path) -> dict:
    """{(week, home, away): median closing spread}, cached to avoid refetching.

    CFBD quotes spreads from the home team's perspective, so a home favorite
    carries a negative number. Providers disagree by a half point or so; the
    median keeps one book's outlier from deciding a game.
    """
    cache = cache_dir / f"lines_{year}.json"
    if cache.exists():
        rows = json.loads(cache.read_text())
    else:
        api_key = os.getenv("CFBD_API_KEY")
        if not api_key:
            sys.exit("ERROR: CFBD_API_KEY not set and no cached lines available")
        print(f"  fetching /lines for {year} (1 API call)...")
        rows = CFBDClient(api_key).get_lines(year)
        if not rows:
            sys.exit(f"ERROR: no lines returned for {year}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows))

    spreads = {}
    for game in rows:
        quoted = [
            line["spread"]
            for line in (game.get("lines") or [])
            if line.get("spread") is not None
        ]
        if not quoted:
            continue
        key = (game.get("week"), game.get("homeTeam"), game.get("awayTeam"))
        spreads[key] = statistics.median(quoted)
    return spreads


def predicted_margin(record: dict, weight: float, min_week: int) -> float:
    """Our margin for one game, from ratings knowable before kickoff."""
    home = blend_rating(
        record["home_elo"], record["home_eff"], weight, record["week"], min_week
    )
    away = blend_rating(
        record["away_elo"], record["away_eff"], weight, record["week"], min_week
    )
    diff = (home + (0 if record["neutral"] else HOME_FIELD_ADVANTAGE)) - away
    return (diff / 100) * POINTS_PER_100_ELO


def main():
    logging.getLogger("src").setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2021, 2022, 2023, 2024, 2025])
    parser.add_argument("--weight", type=float, default=EFFICIENCY_WEIGHT)
    parser.add_argument("--min-week", type=int, default=EFFICIENCY_MIN_WEEK)
    parser.add_argument("--db", default=str(project_root / "data" / "backtest_history.db"))
    args = parser.parse_args()

    source_db = Path(args.db)
    if not source_db.exists():
        sys.exit(f"ERROR: database not found: {source_db}")

    seasons = sorted(args.seasons)
    weekly_eff = {}
    spreads_by_season = {}
    for season in seasons:
        print(f"\nSeason {season}")
        weekly_eff[season] = build_weekly_efficiency(
            load_ppa_games(season, project_root / "data", exclude_garbage_time=True)
        )
        spreads_by_season[season] = load_lines(season, project_root / "data")

    tmpdir = Path(tempfile.mkdtemp(prefix="market-backtest-"))
    try:
        replayed = replay_seasons(source_db, seasons, weekly_eff, tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    rows = []
    for season, records in replayed:
        spreads = spreads_by_season[season]
        matched = 0
        for record in records:
            spread = spreads.get((record["week"], record["home"], record["away"]))
            if spread is None:
                continue
            actual = record["home_score"] - record["away_score"]
            if actual == 0:
                continue
            matched += 1
            rows.append(
                {
                    "season": season,
                    "ours": predicted_margin(record, args.weight, args.min_week),
                    "market": -spread,  # spread is what the home team gets
                    "actual": actual,
                }
            )
        print(f"  {season}: {len(records)} games replayed, {matched} matched to a closing line")

    if not rows:
        sys.exit("ERROR: no games matched a betting line")

    for label in [str(s) for s in args.seasons] + ["ALL"]:
        subset = rows if label == "ALL" else [r for r in rows if str(r["season"]) == label]
        if not subset or (len(args.seasons) == 1 and label == "ALL"):
            continue

        our_mae = statistics.fmean(abs(r["ours"] - r["actual"]) for r in subset)
        mkt_mae = statistics.fmean(abs(r["market"] - r["actual"]) for r in subset)
        our_su = sum((r["ours"] > 0) == (r["actual"] > 0) for r in subset) / len(subset)
        mkt_su = sum((r["market"] > 0) == (r["actual"] > 0) for r in subset) / len(subset)

        # Against the spread: we take a side only where we disagree with the
        # line, and we are right when the actual margin lands on our side of it.
        ats_wins = ats_played = 0
        for r in subset:
            if r["ours"] == r["market"] or r["actual"] == r["market"]:
                continue  # no opinion, or a push
            ats_played += 1
            ats_wins += (r["ours"] > r["market"]) == (r["actual"] > r["market"])

        print(f"\n{'=' * 62}\n{label}: n={len(subset)}\n{'=' * 62}")
        print(f"  margin MAE     ours {our_mae:6.2f}   market {mkt_mae:6.2f}   gap {our_mae - mkt_mae:+.2f}")
        print(f"  straight up    ours {our_su:6.4f}   market {mkt_su:6.4f}   gap {our_su - mkt_su:+.4f}")
        if ats_played:
            print(f"  against spread {ats_wins}/{ats_played} = {ats_wins / ats_played:.4f}")


if __name__ == "__main__":
    main()
