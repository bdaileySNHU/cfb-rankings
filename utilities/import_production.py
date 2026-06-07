#!/usr/bin/env python3
"""Import on-field production and compute blended roster ratings (EPIC-040).

For a roster season, pulls per-player PPA for the production year (default: the
prior season), normalizes it to 0–100 percentiles within each skill position
group across FBS, and snapshots onto roster_players:

    production_score   0–100 percentile (skill positions with PPA), else NULL
    production_source  'ppa' | 'recruiting' | 'none'
    blended_rating     w_prod * production + (1-w_prod) * recruiting  (0–100)

Players without a production signal (OL, freshmen, no prior snaps) keep their
recruiting-based score. Run AFTER import_roster.py for the roster season.

Usage:
    python utilities/import_production.py --roster-season 2025
    python utilities/import_production.py --roster-season 2025 --production-year 2024
    python utilities/import_production.py --roster-season 2025 --blend-weight 0.5
    python utilities/import_production.py --roster-season 2025 --dry-run

Part of: EPIC-040 (Production-Blended Position Strength) - Story 40.3
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.position_service import POSITION_GROUPS, _normalize_rating, load_position_weights
from src.core.production_service import (
    DEFENSE_GROUPS,
    PRODUCTION_GROUPS,
    blend_quality,
    compute_percentiles,
    defensive_impact,
)
from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal
from src.models.models import RosterPlayer

# Reverse map: specific position -> major group (e.g. "FB" -> "RB")
_POS_TO_GROUP = {pos: group for group, positions in POSITION_GROUPS.items() for pos in positions}


def build_production_percentiles(client: CFBDClient, production_year: int) -> dict:
    """Return {athlete_id: percentile_0_100} for skill players across FBS.

    Percentiles are computed within each production group (QB/RB/WR/TE) so a
    QB is ranked against QBs, a WR against WRs, etc.
    """
    ppa_rows = client.get_player_ppa_season(year=production_year)
    print(f"Fetched {len(ppa_rows)} player-PPA rows for {production_year}")

    # Collect (athlete_id, ppa) per group
    by_group = defaultdict(list)
    for row in ppa_rows:
        group = _POS_TO_GROUP.get(row.get("position"))
        if group not in PRODUCTION_GROUPS:
            continue
        avg = (row.get("averagePPA") or {}).get("all")
        athlete = row.get("id")
        if avg is None or athlete is None:
            continue
        try:
            by_group[group].append((int(athlete), float(avg)))
        except (TypeError, ValueError):
            continue

    percentile_map = {}
    for group, pairs in by_group.items():
        values = [v for _, v in pairs]
        scores = compute_percentiles(values)
        for (athlete_id, _), score in zip(pairs, scores):
            percentile_map[athlete_id] = score
    return percentile_map


def build_defensive_percentiles(client: CFBDClient, production_year: int) -> dict:
    """Return {athlete_id: percentile_0_100} for defenders across FBS.

    Builds a weighted defensive-impact composite per player from box-score stats,
    then percentiles within each defensive group (DL/LB/DB).
    """
    rows = client.get_player_season_stats(year=production_year, category="defensive")
    print(f"Fetched {len(rows)} defensive stat rows for {production_year}")

    # Collapse rows (one per statType) into {athlete_id: {position, stats{}}}
    players = defaultdict(lambda: {"position": None, "stats": {}})
    for row in rows:
        athlete = row.get("playerId")
        if athlete is None:
            continue
        try:
            athlete_id = int(athlete)
        except (TypeError, ValueError):
            continue
        players[athlete_id]["position"] = row.get("position")
        players[athlete_id]["stats"][row.get("statType")] = row.get("stat")

    # Composite impact, grouped by defensive position group
    by_group = defaultdict(list)
    for athlete_id, info in players.items():
        group = _POS_TO_GROUP.get(info["position"])
        if group not in DEFENSE_GROUPS:
            continue
        by_group[group].append((athlete_id, defensive_impact(info["stats"])))

    percentile_map = {}
    for group, pairs in by_group.items():
        scores = compute_percentiles([v for _, v in pairs])
        for (athlete_id, _), score in zip(pairs, scores):
            percentile_map[athlete_id] = score
    return percentile_map


def blend_roster(db, roster_season, percentile_map, source_map, weight, dry_run=False) -> dict:
    """Compute production_score/source/blended_rating for the season's roster."""
    rows = db.query(RosterPlayer).filter(RosterPlayer.season == roster_season).all()
    stats = {"total": 0, "with_production": 0, "recruiting_only": 0, "no_signal": 0}

    for rp in rows:
        stats["total"] += 1
        rec_score = _normalize_rating(rp.rating) if rp.rating is not None else None
        prod_score = percentile_map.get(rp.athlete_id)
        prod_label = source_map.get(rp.athlete_id, "production")

        if prod_score is not None and rec_score is not None:
            blended = blend_quality(rec_score, prod_score, weight)
            source = prod_label
            stats["with_production"] += 1
        elif prod_score is not None:
            blended = prod_score  # produced but unrated recruit
            source = prod_label
            stats["with_production"] += 1
        elif rec_score is not None:
            blended = rec_score
            source = "recruiting"
            stats["recruiting_only"] += 1
        else:
            blended = None
            source = "none"
            stats["no_signal"] += 1

        if not dry_run:
            rp.production_score = prod_score
            rp.production_source = source
            rp.blended_rating = blended

    if not dry_run:
        db.commit()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import production + compute blended roster ratings")
    parser.add_argument("--roster-season", type=int, required=True, help="Roster season to update")
    parser.add_argument("--production-year", type=int, help="Production stats year (default: roster-season - 1)")
    parser.add_argument("--blend-weight", type=float, help="w_prod in [0,1] (default: config blend_weight or 0.5)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    args = parser.parse_args()

    production_year = args.production_year or (args.roster_season - 1)
    config = load_position_weights()
    weight = args.blend_weight if args.blend_weight is not None else config.get("blend_weight", 0.5)

    print("=" * 60)
    print(f"Production blend — roster {args.roster_season}, production {production_year}, w_prod={weight}")
    if args.dry_run:
        print("DRY-RUN MODE - No changes will be made")
    print("=" * 60)

    client = CFBDClient()
    db = SessionLocal()
    try:
        skill_map = build_production_percentiles(client, production_year)
        print(f"Skill players with a production percentile: {len(skill_map)}")
        defense_map = build_defensive_percentiles(client, production_year)
        print(f"Defenders with a production percentile: {len(defense_map)}")
        # Skill and defensive athletes are disjoint by position
        percentile_map = {**skill_map, **defense_map}
        source_map = {**{a: "ppa" for a in skill_map}, **{a: "defense" for a in defense_map}}
        print(f"Total players with a production percentile: {len(percentile_map)}\n")

        stats = blend_roster(
            db, args.roster_season, percentile_map, source_map, weight, args.dry_run
        )

        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Roster rows:            {stats['total']}")
        print(f"  blended w/ production: {stats['with_production']}")
        print(f"  recruiting only:      {stats['recruiting_only']}")
        print(f"  no signal:            {stats['no_signal']}")
        print("\n✓ Production blend completed successfully!")
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ Error during production blend: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
