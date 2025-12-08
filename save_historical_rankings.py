#!/usr/bin/env python3
"""
Save historical rankings by replaying games up to a specific week

Unlike save_weekly_rankings(), this doesn't read from teams table.
Instead, it replays all games chronologically and captures the state
at the specified week.
"""

import sys

from src.models.database import SessionLocal
from src.models.models import Game, RankingHistory, Team
from src.core.ranking_service import RankingService


def save_historical_rankings(season, week):
    """
    Replay season up to specified week and save ranking snapshot
    """

    db = SessionLocal()

    print("="*80)
    print(f"SAVE HISTORICAL RANKINGS: {season} Week {week}")
    print("="*80)
    print()

    # Step 1: Create temporary team state dictionary
    print("Step 1: Loading team preseason ratings...")
    teams = db.query(Team).all()

    # Store team state (ELO, wins, losses)
    team_state = {}
    for team in teams:
        team_state[team.id] = {
            'name': team.name,
            'conference': team.conference,
            'elo_rating': team.initial_rating,  # Start with preseason rating
            'wins': 0,
            'losses': 0
        }

    print(f"  Loaded {len(team_state)} teams")
    print()

    # Step 2: Replay all games through the specified week
    print(f"Step 2: Replaying games through Week {week}...")

    games = db.query(Game).filter(
        Game.season == season,
        Game.week <= week,
        Game.is_processed == True
    ).order_by(Game.week, Game.id).all()

    print(f"  Found {len(games)} processed games to replay")
    print()

    ranking_service = RankingService(db)

    for game in games:
        home_id = game.home_team_id
        away_id = game.away_team_id

        # Get current state
        home_state = team_state[home_id]
        away_state = team_state[away_id]

        # Determine winner
        if game.home_score > game.away_score:
            home_state['wins'] += 1
            away_state['losses'] += 1
        else:
            away_state['wins'] += 1
            home_state['losses'] += 1

        # Apply ELO changes (these are stored on the game)
        home_state['elo_rating'] += game.home_rating_change
        away_state['elo_rating'] += game.away_rating_change

    print(f"  ✓ Replayed {len(games)} games")
    print()

    # Step 3: Calculate SOS for each team
    print("Step 3: Calculating strength of schedule...")

    for team_id, state in team_state.items():
        # Calculate SOS from all games in season
        # Note: This uses full season SOS, not week-specific
        sos = ranking_service.calculate_sos(team_id, season)
        state['sos'] = sos

    print("  ✓ SOS calculated for all teams")
    print()

    # Step 4: Rank teams by ELO
    print("Step 4: Ranking teams...")

    ranked_teams = sorted(
        team_state.items(),
        key=lambda x: x[1]['elo_rating'],
        reverse=True
    )

    for rank, (team_id, state) in enumerate(ranked_teams, start=1):
        state['rank'] = rank

    print(f"  ✓ {len(ranked_teams)} teams ranked")
    print()

    # Step 5: Calculate SOS ranks
    print("Step 5: Calculating SOS ranks...")

    sos_sorted = sorted(
        team_state.items(),
        key=lambda x: x[1]['sos'],
        reverse=True
    )

    for sos_rank, (team_id, state) in enumerate(sos_sorted, start=1):
        team_state[team_id]['sos_rank'] = sos_rank

    print("  ✓ SOS ranks calculated")
    print()

    # Step 6: Check if rankings already exist
    existing = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == week
    ).count()

    if existing > 0:
        print(f"⚠️  Week {week} rankings already exist ({existing} teams)")
        response = input("Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            db.close()
            return 1

        # Delete existing
        db.query(RankingHistory).filter(
            RankingHistory.season == season,
            RankingHistory.week == week
        ).delete()
        db.commit()
        print("  Deleted existing rankings")
        print()

    # Step 7: Save to ranking_history
    print(f"Step 6: Saving rankings to database...")

    for team_id, state in team_state.items():
        history = RankingHistory(
            team_id=team_id,
            week=week,
            season=season,
            rank=state['rank'],
            elo_rating=state['elo_rating'],
            wins=state['wins'],
            losses=state['losses'],
            sos=state['sos'],
            sos_rank=state['sos_rank']
        )
        db.add(history)

    db.commit()
    print(f"  ✓ Saved rankings for {len(team_state)} teams")
    print()

    # Verification
    print("="*80)
    print("VERIFICATION")
    print("="*80)
    print()

    saved_count = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == week
    ).count()

    print(f"✓ {saved_count} team rankings saved for {season} Week {week}")
    print()

    # Show top 10
    print("Top 10 teams:")
    top_10 = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == week
    ).order_by(RankingHistory.rank).limit(10).all()

    for r in top_10:
        print(f"  {r.rank:2}. {r.team.name:30} {r.wins:2}-{r.losses}  ELO: {r.elo_rating:.2f}")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python save_historical_rankings.py <season> <week>")
        print()
        print("Examples:")
        print("  python save_historical_rankings.py 2024 15")
        print("  python save_historical_rankings.py 2024 14")
        sys.exit(1)

    season = int(sys.argv[1])
    week = int(sys.argv[2])

    sys.exit(save_historical_rankings(season, week))
