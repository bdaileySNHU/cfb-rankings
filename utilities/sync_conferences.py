#!/usr/bin/env python3
"""Sync team conference membership with CFBD for a season.

Realignment moves teams between conferences and promotes FCS schools into FBS.
The full team import (``import_real_data.py``) does the same thing, but it also
rewrites every preseason factor and is not something you want to run once the
season is underway. This does the membership half only.

Usage:
    python utilities/sync_conferences.py --season 2026            # dry run
    python utilities/sync_conferences.py --season 2026 --apply

Promoted teams (FCS in our table, FBS in CFBD's list) get a fresh preseason
rating, since an FCS rating is not on the same scale as an FBS one.
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.ranking_service import RankingService
from src.importers.teams import conference_tier
from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal
from src.models.models import Team


def sync(db, season: int, apply: bool) -> int:
    teams_data = CFBDClient().get_teams(season)
    if not teams_data:
        print("✗ CFBD returned no teams")
        return 1

    ranking_service = RankingService(db)
    moved, promoted, unknown = [], [], []

    for team_data in teams_data:
        name = team_data["school"]
        conference_name = team_data.get("conference", "FBS Independents")
        tier = conference_tier(name, conference_name)

        team = db.query(Team).filter(Team.name == name).first()
        if team is None:
            unknown.append(f"{name} ({conference_name})")
            continue

        if team.is_fcs:
            promoted.append(f"{name}: FCS -> {conference_name}")
            team.is_fcs = False
        elif team.conference_name != conference_name or team.conference != tier:
            moved.append(f"{name}: {team.conference_name} -> {conference_name} ({tier.value})")

        team.conference_name = conference_name
        team.conference = tier

    for label, rows in (("Realigned", moved), ("Promoted to FBS", promoted)):
        print(f"\n{label}: {len(rows)}")
        for row in rows:
            print(f"  {row}")
    if unknown:
        print(f"\nNot in our teams table ({len(unknown)}) -- run the full import to add them:")
        for row in unknown:
            print(f"  {row}")

    if not apply:
        db.rollback()
        print("\nDry run, nothing written. Re-run with --apply.")
        return 0

    # Promoted teams keep their FCS-scale rating until it is recomputed. `season`
    # is deliberately not passed: the previous-season blend would drag an FCS
    # rating (where ~1060 is a *good* team) onto the FBS scale and land them
    # hundreds of points below the weakest real FBS team. The formula alone errs
    # the other way -- no recruiting or portal data means a default-ish 1500, a
    # median FBS team -- so cap a newcomer at the weakest established FBS team.
    # ponytail: one flat floor, so a perennial FCS champion starts level with a
    # first-timer. Results move them apart inside a month; revisit only if the
    # early-season predictions for these teams are visibly bad.
    promoted_names = [row.split(":")[0] for row in promoted]
    floor = min(
        elo for elo, in db.query(Team.elo_rating)
        .filter(Team.is_fcs == False, Team.name.notin_(promoted_names))  # noqa: E712
        .all()
    )
    for name in promoted_names:
        team = db.query(Team).filter(Team.name == name).one()
        before = team.elo_rating
        ranking_service.initialize_team_rating(team)
        if team.elo_rating > floor:
            team.elo_rating = team.initial_rating = floor
        print(f"  Rated {team.name}: {before:.0f} -> {team.elo_rating:.0f} (FBS floor {floor:.0f})")

    db.commit()
    print(f"\n✓ Wrote {len(moved)} realignments and {len(promoted)} promotions for {season}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        return sync(db, args.season, args.apply)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
