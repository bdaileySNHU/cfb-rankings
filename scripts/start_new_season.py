#!/usr/bin/env python3
"""
EPIC-024 Story 24.3: Season Initialization Script

This script prepares the database for a new season:
- Creates new season record
- Resets team ELO ratings to preseason values
- Archives previous season
- Validates data integrity

Usage:
    python scripts/start_new_season.py --season 2025
    python scripts/start_new_season.py --season 2025 --dry-run
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import SessionLocal
from src.models.models import Game, RankingHistory, Season, Team
from src.core.ranking_service import RankingService


def validate_new_season(db, season_year: int):
    """
    Validate that we can safely start a new season

    Args:
        db: Database session
        season_year: Year of new season to start

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if season already exists
    existing_season = db.query(Season).filter(Season.year == season_year).first()
    if existing_season:
        return False, f"Season {season_year} already exists"

    # Check if previous season exists
    previous_season = db.query(Season).filter(Season.year == season_year - 1).first()
    if not previous_season:
        print(f"⚠️  Warning: No previous season ({season_year - 1}) found")

    return True, None


def archive_previous_season(db, season_year: int, dry_run: bool = True):
    """
    Archive the previous season

    Args:
        db: Database session
        season_year: Year of new season (previous will be year - 1)
        dry_run: If True, don't commit changes
    """
    previous_year = season_year - 1
    previous_season = db.query(Season).filter(Season.year == previous_year).first()

    if not previous_season:
        print(f"⚠️  No previous season to archive")
        return

    print(f"\nArchiving {previous_year} season:")
    print(f"  - Current week: {previous_season.current_week}")
    print(f"  - Active: {previous_season.is_active}")

    if not dry_run:
        previous_season.is_active = False
        db.commit()
        print(f"  ✅ Archived (set is_active=False)")
    else:
        print(f"  [DRY RUN] Would archive season {previous_year} (set is_active=False)")


def create_new_season(db, season_year: int, dry_run: bool = True):
    """
    Create a new season record

    Args:
        db: Database session
        season_year: Year of new season
        dry_run: If True, don't commit changes

    Returns:
        Season object (or None in dry run)
    """
    print(f"\nCreating {season_year} season:")
    print(f"  - Starting week: 1")
    print(f"  - Active: True")

    if not dry_run:
        new_season = Season(
            year=season_year,
            current_week=1,
            is_active=True
        )
        db.add(new_season)
        db.commit()
        print(f"  ✅ Created season {season_year}")
        return new_season
    else:
        print(f"  [DRY RUN] Would create season {season_year}")
        return None


def reset_team_ratings(db, season_year: int, dry_run: bool = True):
    """
    Reset all team ELO ratings to preseason values

    Args:
        db: Database session
        season_year: Year of new season
        dry_run: If True, don't commit changes
    """
    ranking_service = RankingService(db)
    teams = db.query(Team).all()

    print(f"\nResetting team ratings for {season_year}:")
    print(f"  - Teams to reset: {len(teams)}")

    if not dry_run:
        for team in teams:
            # Recalculate preseason rating
            preseason_rating = ranking_service.calculate_preseason_rating(team)
            team.elo_rating = preseason_rating
            team.initial_rating = preseason_rating

        db.commit()
        print(f"  ✅ Reset {len(teams)} team ratings")
    else:
        print(f"  [DRY RUN] Would reset {len(teams)} team ratings to preseason values")


def save_preseason_rankings(db, season_year: int, dry_run: bool = True):
    """
    Save preseason rankings (Week 0) to ranking_history

    Args:
        db: Database session
        season_year: Year of new season
        dry_run: If True, don't commit changes
    """
    if dry_run:
        print(f"\n[DRY RUN] Would save preseason rankings for {season_year} (Week 0)")
        return

    ranking_service = RankingService(db)

    print(f"\nSaving preseason rankings for {season_year} (Week 0):")

    # Get all teams sorted by preseason ELO
    teams = db.query(Team).order_by(Team.elo_rating.desc()).all()

    for rank, team in enumerate(teams, start=1):
        history = RankingHistory(
            team_id=team.id,
            week=0,  # Week 0 = Preseason
            season=season_year,
            rank=rank,
            elo_rating=team.elo_rating,
            wins=0,
            losses=0,
            sos=0.0,
            sos_rank=None
        )
        db.add(history)

    db.commit()
    print(f"  ✅ Saved preseason rankings for {len(teams)} teams")


def validate_season_data(db, season_year: int):
    """
    Validate that season data is correct

    Args:
        db: Database session
        season_year: Year to validate

    Returns:
        Tuple of (is_valid, issues_list)
    """
    issues = []

    # Check season exists
    season = db.query(Season).filter(Season.year == season_year).first()
    if not season:
        issues.append(f"Season {season_year} not found")
        return False, issues

    # Check no games exist for this season yet
    game_count = db.query(Game).filter(Game.season == season_year).count()
    if game_count > 0:
        issues.append(f"Warning: {game_count} games already exist for {season_year}")

    # Check preseason rankings saved
    preseason_rankings = db.query(RankingHistory).filter(
        RankingHistory.season == season_year,
        RankingHistory.week == 0
    ).count()

    if preseason_rankings == 0:
        issues.append(f"No preseason rankings found for {season_year}")

    return len(issues) == 0, issues


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Initialize a new season')
    parser.add_argument('--season', type=int, required=True,
                       help='Year of new season to start (e.g., 2025)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    args = parser.parse_args()

    db = SessionLocal()

    print("="*80)
    print(f"EPIC-024: Season Initialization - {args.season}")
    print("="*80)
    print()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    try:
        # Step 1: Validate
        print("Step 1: Validation")
        print("-" * 80)
        is_valid, error = validate_new_season(db, args.season)
        if not is_valid:
            print(f"❌ Validation failed: {error}")
            sys.exit(1)
        print("✅ Validation passed")

        # Step 2: Archive previous season
        print()
        print("Step 2: Archive Previous Season")
        print("-" * 80)
        archive_previous_season(db, args.season, dry_run=args.dry_run)

        # Step 3: Create new season
        print()
        print("Step 3: Create New Season")
        print("-" * 80)
        create_new_season(db, args.season, dry_run=args.dry_run)

        # Step 4: Reset team ratings
        print()
        print("Step 4: Reset Team Ratings")
        print("-" * 80)
        reset_team_ratings(db, args.season, dry_run=args.dry_run)

        # Step 5: Save preseason rankings
        print()
        print("Step 5: Save Preseason Rankings")
        print("-" * 80)
        save_preseason_rankings(db, args.season, dry_run=args.dry_run)

        # Step 6: Validate results
        if not args.dry_run:
            print()
            print("Step 6: Validation")
            print("-" * 80)
            is_valid, issues = validate_season_data(db, args.season)
            if issues:
                for issue in issues:
                    print(f"  ⚠️  {issue}")
            if is_valid:
                print("  ✅ All checks passed")

        print()
        print("="*80)
        if args.dry_run:
            print(f"[DRY RUN] To actually initialize {args.season}, run:")
            print(f"  python scripts/start_new_season.py --season {args.season}")
        else:
            print(f"✅ Season {args.season} initialized successfully!")
            print()
            print("Next steps:")
            print(f"  1. Import games for {args.season}")
            print(f"  2. Process weekly results")
            print(f"  3. Run weekly updates")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
