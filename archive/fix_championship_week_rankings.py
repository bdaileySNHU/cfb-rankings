#!/usr/bin/env python3
"""
Fix Week 15 rankings by applying championship game changes to Week 14 data

Simpler approach: Copy Week 14 rankings to Week 15, then update teams
that played in championship games by applying the game rating changes.
"""

import sys

from src.models.database import SessionLocal
from src.models.models import Game, RankingHistory, Team


def fix_championship_week_rankings(season=2024):
    """Fix Week 15 rankings using Week 14 + championship game changes"""

    db = SessionLocal()

    print("="*80)
    print(f"FIX CHAMPIONSHIP WEEK RANKINGS - {season}")
    print("="*80)
    print()

    # Step 1: Get all Week 14 rankings
    print("Step 1: Loading Week 14 rankings...")
    week_14_rankings = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 14
    ).all()

    if not week_14_rankings:
        print(f"⚠️  No Week 14 rankings found for {season}")
        db.close()
        return 1

    print(f"  Found {len(week_14_rankings)} teams in Week 14")
    print()

    # Step 2: Get all championship games
    print("Step 2: Finding championship games...")
    championship_games = db.query(Game).filter(
        Game.season == season,
        Game.week == 15,
        Game.game_type == 'conference_championship',
        Game.is_processed == True
    ).all()

    print(f"  Found {len(championship_games)} processed championship games")
    print()

    # Step 3: Delete existing Week 15 rankings
    existing = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).count()

    if existing > 0:
        print(f"Step 3: Deleting {existing} existing Week 15 rankings...")
        db.query(RankingHistory).filter(
            RankingHistory.season == season,
            RankingHistory.week == 15
        ).delete()
        db.commit()
        print("  ✓ Deleted")
        print()

    # Step 4: Create Week 15 rankings from Week 14
    print("Step 4: Copying Week 14 rankings to Week 15...")

    week_15_data = {}
    for w14_rank in week_14_rankings:
        week_15_data[w14_rank.team_id] = {
            'elo_rating': w14_rank.elo_rating,
            'wins': w14_rank.wins,
            'losses': w14_rank.losses,
            'sos': w14_rank.sos,
            'sos_rank': w14_rank.sos_rank
        }

    print(f"  ✓ Copied {len(week_15_data)} teams")
    print()

    # Step 5: Apply championship game changes
    print("Step 5: Applying championship game results...")

    for game in championship_games:
        home_id = game.home_team_id
        away_id = game.away_team_id

        # Update home team
        if home_id in week_15_data:
            week_15_data[home_id]['elo_rating'] += game.home_rating_change

            if game.home_score > game.away_score:
                week_15_data[home_id]['wins'] += 1
            else:
                week_15_data[home_id]['losses'] += 1

        # Update away team
        if away_id in week_15_data:
            week_15_data[away_id]['elo_rating'] += game.away_rating_change

            if game.away_score > game.home_score:
                week_15_data[away_id]['wins'] += 1
            else:
                week_15_data[away_id]['losses'] += 1

        home_team = db.query(Team).get(home_id)
        away_team = db.query(Team).get(away_id)
        score = f"{game.away_score}-{game.home_score}"

        print(f"  Applied: {away_team.name} @ {home_team.name} ({score})")

    print()

    # Step 6: Re-rank teams by ELO
    print("Step 6: Re-ranking teams...")

    ranked_teams = sorted(
        week_15_data.items(),
        key=lambda x: x[1]['elo_rating'],
        reverse=True
    )

    print(f"  ✓ {len(ranked_teams)} teams ranked")
    print()

    # Step 7: Save Week 15 rankings
    print("Step 7: Saving Week 15 rankings...")

    for rank, (team_id, data) in enumerate(ranked_teams, start=1):
        history = RankingHistory(
            team_id=team_id,
            week=15,
            season=season,
            rank=rank,
            elo_rating=data['elo_rating'],
            wins=data['wins'],
            losses=data['losses'],
            sos=data['sos'],
            sos_rank=data['sos_rank']
        )
        db.add(history)

    db.commit()
    print(f"  ✓ Saved {len(ranked_teams)} teams")
    print()

    # Verification
    print("="*80)
    print("VERIFICATION")
    print("="*80)
    print()

    saved = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).count()

    print(f"✓ {saved} teams saved for Week 15")
    print()

    # Show top 10
    print("Top 10 teams:")
    top_10 = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).order_by(RankingHistory.rank).limit(10).all()

    for r in top_10:
        print(f"  {r.rank:2}. {r.team.name:30} {r.wins:2}-{r.losses}  ELO: {r.elo_rating:.2f}")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    season = 2024
    if len(sys.argv) > 1:
        season = int(sys.argv[1])

    sys.exit(fix_championship_week_rankings(season))
