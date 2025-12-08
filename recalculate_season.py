"""
Recalculate season ratings by replaying all games
Used when fundamental changes affect game calculations (like conference reclassification)
"""

import sys

from src.models.database import SessionLocal
from src.models.models import Game, RankingHistory, Season, Team
from src.core.ranking_service import RankingService


def recalculate_season(season_year: int, dry_run: bool = False):
    """
    Reset and replay entire season with corrected data

    Args:
        season_year: Year to recalculate
        dry_run: If True, show what would happen without making changes
    """
    db = SessionLocal()

    try:
        print("=" * 80)
        print(f"Season {season_year} Recalculation")
        print("=" * 80)
        print()

        # Get season
        season = db.query(Season).filter(Season.year == season_year).first()
        if not season:
            print(f"❌ Season {season_year} not found")
            return

        print(f"📅 Season: {season_year}")
        print(f"📊 Current week: {season.current_week}")
        print()

        # Get all games for this season (including processed ones)
        all_games = db.query(Game).filter(
            Game.season == season_year
        ).order_by(Game.week, Game.id).all()

        processed_games = [g for g in all_games if g.is_processed]
        unprocessed_games = [g for g in all_games if not g.is_processed]

        print(f"🏈 Total games: {len(all_games)}")
        print(f"   ✓ Processed: {len(processed_games)}")
        print(f"   ⏳ Unprocessed: {len(unprocessed_games)}")
        print()

        if len(processed_games) == 0:
            print("ℹ️  No processed games to recalculate")
            return

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print()
            print("Would reset:")
            teams = db.query(Team).all()
            for team in teams[:5]:  # Show first 5
                print(f"  • {team.name}: {team.elo_rating:.1f} → {team.initial_rating:.1f} (preseason)")
            print(f"  ... and {len(teams) - 5} more teams")
            print()
            print(f"Would replay {len(processed_games)} games in chronological order")
            print()
            return

        # Step 1: Reset all teams to preseason
        print("Step 1: Resetting teams to preseason ratings...")
        teams = db.query(Team).all()
        for team in teams:
            team.elo_rating = team.initial_rating
            team.wins = 0
            team.losses = 0
        db.commit()
        print(f"✓ Reset {len(teams)} teams to preseason")
        print()

        # Step 2: Mark all games as unprocessed
        print("Step 2: Marking games as unprocessed...")
        for game in processed_games:
            game.is_processed = False
            game.home_rating_change = 0.0
            game.away_rating_change = 0.0
        db.commit()
        print(f"✓ Marked {len(processed_games)} games as unprocessed")
        print()

        # Step 3: Clear ranking history
        print("Step 3: Clearing ranking history...")
        deleted = db.query(RankingHistory).filter(
            RankingHistory.season == season_year
        ).delete()
        db.commit()
        print(f"✓ Cleared {deleted} ranking history records")
        print()

        # Step 4: Replay all games in order
        print("Step 4: Replaying games in chronological order...")
        print()

        ranking_service = RankingService(db)
        successful = 0
        failed = 0
        excluded = 0

        for i, game in enumerate(processed_games, 1):
            try:
                result = ranking_service.process_game(game)
                successful += 1

                # Show progress every 10 games
                if i % 10 == 0 or i == len(processed_games):
                    print(f"  Processed {i}/{len(processed_games)} games...")

            except ValueError as e:
                # Game excluded (like FCS)
                if "excluded from rankings" in str(e):
                    excluded += 1
                else:
                    print(f"  ⚠️  Week {game.week}: {e}")
                    failed += 1
            except Exception as e:
                print(f"  ❌ Week {game.week}: {e}")
                failed += 1

        db.commit()
        print()
        print(f"✓ Replay complete:")
        print(f"   • Successful: {successful}")
        print(f"   • Excluded (FCS): {excluded}")
        print(f"   • Failed: {failed}")
        print()

        # Step 5: Save final rankings
        print("Step 5: Saving final rankings...")
        ranking_service.save_weekly_rankings(season_year, season.current_week)
        print(f"✓ Saved rankings for week {season.current_week}")
        print()

        # Show top 10
        print("=" * 80)
        print("TOP 10 TEAMS (After Recalculation)")
        print("=" * 80)
        rankings = ranking_service.get_current_rankings(season_year, limit=10)
        for rank in rankings:
            print(f"  {rank['rank']:2d}. {rank['team_name']:25s} {rank['elo_rating']:.2f}  ({rank['wins']}-{rank['losses']})")
        print()

        print("=" * 80)
        print("✅ RECALCULATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recalculate season ratings")
    parser.add_argument("--season", type=int, default=2024, help="Season year to recalculate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.yes and not args.dry_run:
        print()
        print("⚠️  WARNING: This will reset all ratings and replay all games!")
        print(f"   Season: {args.season}")
        print()
        response = input("Continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            sys.exit(0)
        print()

    recalculate_season(args.season, dry_run=args.dry_run)
