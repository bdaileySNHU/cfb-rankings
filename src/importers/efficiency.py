"""Team efficiency import from the CFBD API (EPIC-045).

Pulls opponent-adjusted team PPA — the CORE-style efficiency signal — and stores
it on the teams table. One API call per run; the rating blend in
``src.core.ranking_service`` reads it from there.
"""

from src.integrations.cfbd_client import CFBDClient
from src.models.models import Team


def import_team_efficiency(cfbd: CFBDClient, db, year: int) -> int:
    """Refresh offense_ppa / defense_ppa for every team from CFBD.

    Values are season-to-date, so running this weekly keeps the blend current
    without any lookahead. Teams missing from the response (FCS, or not yet
    covered this season) keep whatever they had; the blend falls back to pure
    ELO when the columns are NULL.

    Args:
        cfbd: Authenticated CFBD client
        db: SQLAlchemy session
        year: Season year

    Returns:
        Number of teams updated
    """
    print(f"\nImporting team efficiency (adjusted PPA) for {year}...")

    ppa_data = cfbd.get_team_ppa_season(year)
    if not ppa_data:
        print("⚠️  No team PPA available — leaving existing efficiency values in place")
        return 0

    teams_by_name = {t.name: t for t in db.query(Team).all()}
    updated = 0

    for row in ppa_data:
        team = teams_by_name.get(row.get("team"))
        if team is None:
            continue

        offense = (row.get("offense") or {}).get("overall")
        defense = (row.get("defense") or {}).get("overall")
        if offense is None or defense is None:
            continue

        team.offense_ppa = offense
        team.defense_ppa = defense
        updated += 1

    db.commit()
    print(f"✓ Updated efficiency for {updated} teams")
    return updated
