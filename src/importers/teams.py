"""Team import from the CFBD API."""

from src.core.ranking_service import RankingService
from src.importers.common import CONFERENCE_MAP
from src.integrations.cfbd_client import CFBDClient
from src.models.models import ConferenceType, Team


def import_teams(cfbd: CFBDClient, db, year: int):
    """Import all FBS teams (or reuse existing teams in incremental mode)"""
    print(f"\nImporting FBS teams for {year}...")

    # Fetch teams from CFBD
    teams_data = cfbd.get_teams(year)
    if not teams_data:
        print("✗ Failed to fetch teams from CFBD API")
        return {}

    # Fetch recruiting data
    print("Fetching recruiting rankings...")
    recruiting_data = cfbd.get_recruiting_rankings(year) or []
    recruiting_map = {r["team"]: r["rank"] for r in recruiting_data if "team" in r and "rank" in r}

    # Fetch talent ratings
    print("Fetching talent composite...")
    talent_data = cfbd.get_team_talent(year) or []
    talent_map = {t["school"]: t["talent"] for t in talent_data if "school" in t and "talent" in t}

    # Fetch returning production (EPIC-025)
    # API returns percentPPA (decimal 0.0-1.0) for overall returning production
    print("Fetching returning production...")
    returning_data = cfbd.get_returning_production(year) or []
    returning_map = {}
    for r in returning_data:
        if "team" in r and "percentPPA" in r:
            team = r["team"]
            prod = r["percentPPA"]
            # Validate and store (API returns decimal, no conversion needed)
            if isinstance(prod, (int, float)) and 0.0 <= prod <= 1.0:
                returning_map[team] = prod
            else:
                print(f"  Warning: Invalid returning production for {team}: {prod}")

    print(f"  Loaded returning production for {len(returning_map)} teams")

    # EPIC-026: Fetch and calculate transfer portal rankings
    print("Fetching transfer portal data...")
    transfer_data = cfbd.get_transfer_portal(year) or []
    print(f"  Retrieved {len(transfer_data)} transfers")

    print("Calculating transfer portal rankings...")
    from src.core.transfer_portal_service import TransferPortalService

    tp_service = TransferPortalService()
    team_scores, team_ranks = tp_service.get_team_stats(transfer_data)
    print(f"  Calculated rankings for {len(team_ranks)} teams")

    team_objects = {}
    ranking_service = RankingService(db)
    teams_created = 0
    teams_reused = 0

    for team_data in teams_data:
        team_name = team_data["school"]
        conference_name = team_data.get("conference", "FBS Independents")

        # Check if team already exists (incremental mode)
        existing_team = db.query(Team).filter(Team.name == team_name).first()

        if existing_team:
            # Reuse existing team, but update preseason data
            recruiting_rank = recruiting_map.get(team_name, 999)
            returning_prod = returning_map.get(team_name, 0.5)

            # EPIC-026: Get transfer portal data
            transfer_portal_rank = team_ranks.get(team_name, 999)
            transfer_portal_points = team_scores.get(team_name, {}).get("points", 0)
            transfer_portal_count = team_scores.get(team_name, {}).get("count", 0)

            # Update preseason factors
            existing_team.recruiting_rank = recruiting_rank
            existing_team.returning_production = returning_prod
            existing_team.transfer_portal_rank = transfer_portal_rank
            existing_team.transfer_portal_points = transfer_portal_points
            existing_team.transfer_count = transfer_portal_count

            team_objects[team_name] = existing_team
            teams_reused += 1
        else:
            # Create new team
            # Map conference to tier (P5/G5/FCS)
            conference_tier = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)

            # Special case: Notre Dame is P5 Independent
            if team_name == "Notre Dame":
                conference_tier = ConferenceType.POWER_5

            # Get preseason data
            recruiting_rank = recruiting_map.get(team_name, 999)
            transfer_rank = 999  # DEPRECATED: Use transfer_portal_rank instead
            returning_prod = returning_map.get(team_name, 0.5)

            # EPIC-026: Get transfer portal data
            transfer_portal_rank = team_ranks.get(team_name, 999)
            transfer_portal_points = team_scores.get(team_name, {}).get("points", 0)
            transfer_portal_count = team_scores.get(team_name, {}).get("count", 0)

            # EPIC-012: Create team with BOTH conference tier and name
            team = Team(
                name=team_name,
                conference=conference_tier,  # P5/G5/FCS (for logic)
                conference_name=conference_name,  # "Big Ten", "SEC", etc. (for display)
                recruiting_rank=recruiting_rank,
                transfer_rank=transfer_rank,
                returning_production=returning_prod,
                transfer_portal_rank=transfer_portal_rank,
                transfer_portal_points=transfer_portal_points,
                transfer_count=transfer_portal_count,
            )

            ranking_service.initialize_team_rating(team)
            db.add(team)
            team_objects[team_name] = team
            teams_created += 1

            print(
                f"  Added: {team_name} - {conference_name} ({conference_tier.value}) - Recruiting: #{recruiting_rank}, Returning: {returning_prod*100:.0f}%, Portal: #{transfer_portal_rank}"
            )

    db.commit()

    if teams_reused > 0:
        print(f"\n✓ Reused {teams_reused} existing teams, created {teams_created} new teams")
    else:
        print(f"\n✓ Imported {len(team_objects)} teams")

    return team_objects
