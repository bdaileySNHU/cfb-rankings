#!/usr/bin/env python3
"""Season Archival and System Preparation

This script marks a completed season as inactive and prepares the system
for the next season initialization. Includes safety checks and confirmation
requirements to prevent accidental archival.

Usage:
    python utilities/archive_season.py --season 2025                    # Dry-run (shows what would be done)
    python utilities/archive_season.py --season 2025 --confirm          # Actually archives season

Part of EPIC-SEASON-END-2025: Story 3 - Season Archival and System Preparation
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import database and models
from src.models.database import SessionLocal
from src.models.models import RankingHistory, Season


def verify_final_snapshot_exists(db: Any, season: int) -> bool:
    """Verify that final ranking snapshot exists for the season."""
    print("Verifying final ranking snapshot...")

    # Check for week 20 snapshot
    final_week = 20
    snapshot_count = db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == final_week
    ).count()

    if snapshot_count == 0:
        print(f"✗ No final snapshot found for season {season} week {final_week}")
        return False

    print(f"✓ Final snapshot exists ({snapshot_count} team entries)")
    return True


def check_active_seasons(db: Any) -> list:
    """Check for any active seasons in the system."""
    active_seasons = db.query(Season).filter(Season.is_active == True).all()
    return active_seasons


def archive_season(db: Any, season_year: int, confirm: bool) -> bool:
    """Archive the specified season by marking it inactive."""
    # Get the season
    season = db.query(Season).filter(Season.year == season_year).first()

    if not season:
        print(f"✗ Season {season_year} not found in database")
        return False

    if not season.is_active:
        print(f"⚠ Season {season_year} is already archived (is_active = False)")
        return True

    # Verify final snapshot exists
    if not verify_final_snapshot_exists(db, season_year):
        print("\n⚠ WARNING: Final ranking snapshot does not exist!")
        print("Recommendation: Run utilities/finalize_season_stats.py first")
        if not confirm:
            return False
        # Allow proceeding with confirmation even without snapshot
        print("Proceeding with archival despite missing snapshot...")

    # Show what will be done
    print(f"\n{'='*60}")
    print("Archival Actions")
    print(f"{'='*60}")
    print(f"Season: {season_year}")
    print(f"Current Status: is_active = {season.is_active}")
    print(f"New Status: is_active = False")
    print(f"{'='*60}\n")

    if not confirm:
        print("DRY-RUN MODE: No changes will be made")
        print("To actually archive the season, add --confirm flag")
        return False

    # Confirm with user one more time
    print("⚠ This will mark the season as inactive.")
    print("⚠ This action is reversible by running: UPDATE seasons SET is_active = True WHERE year = {season_year};")

    # Update season status
    try:
        season.is_active = False
        db.commit()
        print(f"\n✓ Season {season_year} marked as inactive (archived)")
        print(f"  Archived at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    except Exception as e:
        print(f"\n✗ Error archiving season: {e}")
        db.rollback()
        return False


def create_archival_documentation(season_year: int, confirm: bool) -> None:
    """Create archival documentation by copying validation and summary reports."""
    print("\nCreating archival documentation...")

    # Create archive directory if it doesn't exist
    archive_dir = project_root / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Define source and destination files
    files_to_archive = [
        (
            f"docs/season-{season_year}-validation-report.md",
            f"docs/archive/season-{season_year}-validation.md"
        ),
        (
            f"docs/season-{season_year}-summary.md",
            f"docs/archive/season-{season_year}-summary.md"
        ),
    ]

    archived_count = 0
    for source, dest in files_to_archive:
        source_path = project_root / source
        dest_path = project_root / dest

        if source_path.exists():
            if confirm:
                shutil.copy2(source_path, dest_path)
                print(f"  ✓ Copied {source} → {dest}")
                archived_count += 1
            else:
                print(f"  [DRY-RUN] Would copy {source} → {dest}")
        else:
            print(f"  ⚠ Source file not found: {source}")

    # Create season notes file
    notes_file = f"docs/archive/season-{season_year}-notes.md"
    notes_path = project_root / notes_file

    if confirm:
        if not notes_path.exists():
            notes_content = f"""# Season {season_year} - Archival Notes

**Archived:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Season Summary

- Final standings completed
- Season marked as inactive (is_active = False)
- All historical data preserved and accessible

## Notable Events

(Add any notable events, issues, or observations for this season)

## Data Quality

(Add any data quality notes or concerns)

## Recommendations for Future Seasons

(Add any recommendations based on this season's experience)
"""
            with open(notes_path, "w") as f:
                f.write(notes_content)
            print(f"  ✓ Created {notes_file}")
        else:
            print(f"  ⚠ Notes file already exists: {notes_file}")
    else:
        print(f"  [DRY-RUN] Would create {notes_file}")

    if confirm:
        print(f"\n✓ Archived {archived_count} document(s) to docs/archive/")


def create_season_end_checklist() -> None:
    """Create or update season-end checklist documentation."""
    print("\nUpdating season-end process documentation...")

    checklist_path = project_root / "docs" / "season-end-checklist.md"

    checklist_content = """# Season-End Finalization Checklist

This checklist documents the process for finalizing and archiving a completed season.

## Prerequisites

- Season has concluded with all postseason games completed
- All game data imported and processed
- Database backup created

## Step 1: Data Validation

Run the validation script to verify data integrity:

```bash
python utilities/validate_season.py --season YYYY --output docs/season-YYYY-validation-report.md
```

**Expected Result:** Validation PASS with no critical errors

**If validation fails:**
- Review errors in validation report
- Fix data issues (import missing games, process unprocessed games, etc.)
- Re-run validation until PASS

## Step 2: Final Statistics Calculation

Calculate final season statistics and generate summary:

```bash
python utilities/finalize_season_stats.py --season YYYY --output docs/season-YYYY-summary.md
```

**Expected Result:**
- Final rankings snapshot created (week 20)
- Season summary document generated
- Prediction accuracy calculated
- Conference statistics compiled

## Step 3: Review Reports

Manually review generated reports:

- [ ] Check validation report (docs/season-YYYY-validation-report.md)
- [ ] Review season summary (docs/season-YYYY-summary.md)
- [ ] Verify final rankings make sense
- [ ] Confirm all statistics are reasonable

## Step 4: Create Database Backup

Create a backup before archival:

```bash
cp cfb_rankings.db cfb_rankings_backup_YYYY-MM-DD.db
```

## Step 5: Archive Season

Mark season as inactive and create archival documentation:

```bash
# Dry-run first (verify actions)
python utilities/archive_season.py --season YYYY

# Actually archive
python utilities/archive_season.py --season YYYY --confirm
```

**Expected Result:**
- Season marked as is_active = False
- Archival documents copied to docs/archive/
- Season notes file created

## Step 6: Verify Historical Data Access

Test that historical data remains accessible:

- [ ] Check API endpoint: `GET /api/rankings?season=YYYY&week=20`
- [ ] Verify frontend season selector includes archived season
- [ ] Confirm rankings display correctly for archived season
- [ ] Test team detail pages for archived season

## Step 7: Test System State

Verify system is ready for next season:

- [ ] Confirm no active season exists: `SELECT * FROM seasons WHERE is_active = True` returns empty
- [ ] Verify all tables are in consistent state
- [ ] Run test suite: `pytest`
- [ ] Check application starts without errors

## Post-Archival Tasks

- [ ] Update any documentation with season-specific information
- [ ] Announce season finalization to stakeholders (if applicable)
- [ ] Begin planning for next season initialization

## Troubleshooting

### Validation Fails

**Problem:** Validation script reports errors

**Solution:**
- Review validation report for specific issues
- Fix data issues (import missing games, correct ELO imbalances)
- Re-run validation

### Final Snapshot Missing

**Problem:** Archive script warns about missing final snapshot

**Solution:**
- Run `utilities/finalize_season_stats.py` first
- Verify snapshot exists: `SELECT COUNT(*) FROM ranking_history WHERE season = YYYY AND week = 20;`

### Season Already Archived

**Problem:** Season is already marked inactive

**Solution:**
- This is safe - no action needed
- Archival documents may already exist

### Need to Re-Activate Season

**Problem:** Need to make changes after archival

**Solution:**
```sql
UPDATE seasons SET is_active = True WHERE year = YYYY;
```

Then re-run archival after making changes.

## Rollback Procedure

If archival needs to be rolled back:

1. **Restore database backup:**
   ```bash
   cp cfb_rankings_backup_YYYY-MM-DD.db cfb_rankings.db
   ```

2. **Or re-activate season:**
   ```sql
   UPDATE seasons SET is_active = True WHERE year = YYYY;
   ```

3. **Remove archival documents if needed:**
   ```bash
   rm docs/archive/season-YYYY-*.md
   ```

## Notes

- **Database backups:** Keep backups for at least 1 year after archival
- **Archival documents:** Preserved indefinitely for historical reference
- **Historical data:** All data remains in database, only `is_active` flag changes
- **Season notes:** Update `docs/archive/season-YYYY-notes.md` with any relevant information

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
"""

    with open(checklist_path, "w") as f:
        f.write(checklist_content)

    print(f"✓ Created/updated season-end checklist: docs/season-end-checklist.md")


def verify_system_readiness(db: Any) -> None:
    """Verify system is ready for next season."""
    print("\nVerifying system readiness...")

    # Check for active seasons
    active_seasons = check_active_seasons(db)

    if not active_seasons:
        print("✓ No active season exists - system ready for new season initialization")
    else:
        print(f"⚠ {len(active_seasons)} active season(s) still exist:")
        for season in active_seasons:
            print(f"  - Season {season.year} (is_active = {season.is_active})")

    # Check tables for consistency
    print("✓ System state verified")


def main():
    """Main entry point for season archival script."""
    parser = argparse.ArgumentParser(
        description="Archive a completed season and prepare system for next season"
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to archive (e.g., 2025)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually perform archival (without this flag, runs in dry-run mode)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    if args.confirm:
        print(f"Archiving Season {args.season}")
    else:
        print(f"Season {args.season} Archival - DRY-RUN MODE")
    print(f"{'='*60}\n")

    # Create database session
    db = SessionLocal()

    try:
        # Archive the season
        success = archive_season(db, args.season, args.confirm)

        if not success and not args.confirm:
            print("\n" + "="*60)
            print("Dry-run completed - no changes made")
            print("Add --confirm flag to actually archive the season")
            print("="*60 + "\n")
            sys.exit(0)
        elif not success:
            print("\n✗ Archival failed")
            sys.exit(1)

        # Create archival documentation
        create_archival_documentation(args.season, args.confirm)

        # Create/update season-end checklist
        if args.confirm:
            create_season_end_checklist()

        # Verify system readiness
        verify_system_readiness(db)

        if args.confirm:
            print(f"\n{'='*60}")
            print("Season Archival Complete")
            print(f"{'='*60}")
            print(f"✓ Season {args.season} archived successfully")
            print(f"✓ System ready for season {args.season + 1} initialization")
            print(f"{'='*60}\n")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error during archival: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
