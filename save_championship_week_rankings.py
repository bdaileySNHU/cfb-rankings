#!/usr/bin/env python3
"""
Save championship week (Week 15) rankings to ranking_history

After fixing import script to include championship week, we need to
backfill Week 15 rankings for seasons that already imported championships
but didn't save the ranking history.
"""

from database import SessionLocal
from ranking_service import RankingService
from models import Game
import sys


def save_championship_week_rankings(season=2024):
    """Save Week 15 rankings if championship games exist"""

    db = SessionLocal()
    ranking_service = RankingService(db)

    print("="*80)
    print(f"SAVE CHAMPIONSHIP WEEK RANKINGS - {season}")
    print("="*80)
    print()

    # Check if there are any Week 15 games
    week_15_games = db.query(Game).filter(
        Game.season == season,
        Game.week == 15
    ).all()

    if not week_15_games:
        print(f"⚠️  No Week 15 games found for {season}")
        print()
        db.close()
        return 1

    print(f"Found {len(week_15_games)} games in Week 15")

    # Check how many are processed
    processed_count = sum(1 for g in week_15_games if g.is_processed)
    print(f"  Processed: {processed_count}")
    print(f"  Unprocessed: {len(week_15_games) - processed_count}")
    print()

    if processed_count == 0:
        print("⚠️  No processed games in Week 15 - nothing to save")
        print()
        db.close()
        return 1

    # Check if Week 15 rankings already exist
    from models import RankingHistory
    existing_rankings = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).count()

    if existing_rankings > 0:
        print(f"⚠️  Week 15 rankings already exist ({existing_rankings} teams)")
        print()
        response = input("Overwrite existing rankings? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            db.close()
            return 1

        # Delete existing Week 15 rankings
        db.query(RankingHistory).filter(
            RankingHistory.season == season,
            RankingHistory.week == 15
        ).delete()
        db.commit()
        print("  Deleted existing Week 15 rankings")
        print()

    # Save Week 15 rankings
    print(f"Saving Week 15 rankings for {season}...")
    ranking_service.save_weekly_rankings(season, 15)
    print("  ✓ Week 15 rankings saved")
    print()

    # Verify saved rankings
    saved_rankings = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).count()

    print("="*80)
    print("VERIFICATION")
    print("="*80)
    print()
    print(f"✓ Week 15 rankings saved for {saved_rankings} teams")
    print()

    # Show top 10
    print("Top 10 teams in Week 15:")
    top_rankings = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == 15
    ).order_by(RankingHistory.rank).limit(10).all()

    for r in top_rankings:
        print(f"  {r.rank:2}. {r.team.name:30} {r.wins:2}-{r.losses}  ELO: {r.elo_rating:.2f}")

    print()

    db.close()
    return 0


if __name__ == "__main__":
    season = 2024
    if len(sys.argv) > 1:
        season = int(sys.argv[1])

    sys.exit(save_championship_week_rankings(season))
