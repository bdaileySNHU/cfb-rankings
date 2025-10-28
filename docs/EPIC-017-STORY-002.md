# EPIC-017 Story 002: Add Data Validation and Safety Checks

**Epic:** EPIC-017 - Retrospective Prediction Generation
**Story Points:** 3
**Priority:** High
**Status:** ✅ Complete
**Completion Date:** 2025-10-27
**Dependencies:** EPIC-017 Story 001 (Complete)

---

## User Story

As a **system administrator**,
I want **comprehensive safety checks and validation in the backfill script**,
So that **I can preview changes before committing them, prevent data corruption, and easily rollback if predictions are incorrect**.

---

## Story Context

### Existing System Integration

- **Integrates with:**
  - `scripts/backfill_historical_predictions.py` (from Story 001)
  - `models.py`: Prediction model
  - `database.py`: SQLAlchemy session management
  - Python `argparse` module for command-line flags

- **Technology:** Python 3, SQLAlchemy ORM, SQLite

- **Follows pattern:**
  - Command-line argument handling from `scripts/weekly_update.py`
  - Dry-run pattern from common CLI tools
  - Logging and validation patterns from existing scripts

- **Touch points:**
  - `predictions` table for duplicate checking
  - `ranking_history` table for data completeness validation
  - `games` table for querying games to process

---

## Acceptance Criteria

### Functional Requirements

1. **Script supports `--dry-run` flag for preview mode**
   - Usage: `python3 scripts/backfill_historical_predictions.py --dry-run`
   - Performs all queries and calculations
   - Shows exactly what would be written to database
   - Does NOT commit any changes
   - Outputs summary: "DRY RUN - No changes written to database"

2. **Script prevents duplicate predictions**
   - Before creating prediction, checks: `SELECT COUNT(*) FROM predictions WHERE game_id = ?`
   - If count > 0, skips game and logs: "Skipping game {game_id} - prediction already exists"
   - Increments "skipped" counter in summary
   - Does not raise error (skip and continue)

3. **Script validates historical data completeness before processing**
   - For each game, verifies both home and away team have historical ratings
   - Query: `SELECT COUNT(*) FROM ranking_history WHERE team_id IN (?, ?) AND season = ? AND week = ?`
   - If any ratings missing, logs warning with team names
   - Option: `--require-complete-data` flag to abort if any data missing
   - Default: use 1500 for missing ratings and continue

4. **Script logs warnings for data anomalies**
   - Win probability outside 5-95% range: "Unusual prediction: {home_team} vs {away_team} - {win_prob}% confidence"
   - Rating outside 1000-2500 range: "Unusual rating: {team_name} has rating {rating} in week {week}"
   - Large rating difference (>500): "Large rating gap: {home_rating} vs {away_rating}"
   - All warnings logged but do not prevent processing

5. **Script provides `--delete-backfilled` flag for rollback**
   - Usage: `python3 scripts/backfill_historical_predictions.py --delete-backfilled --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"`
   - Requires both `--start-time` and `--end-time` parameters
   - Performs: `DELETE FROM predictions WHERE created_at BETWEEN ? AND ?`
   - Shows count of predictions to delete and requires confirmation: "Delete {count} predictions? (yes/no)"
   - Logs each deletion: "Deleted {count} predictions from backfill run"

6. **Script generates comprehensive summary report**
   - Total games found
   - Predictions created
   - Predictions skipped (already existed)
   - Warnings (missing data, anomalies)
   - Errors encountered
   - Duration (seconds)
   - Average time per prediction

### Quality Requirements

7. **Validation logic is covered by unit tests**
   - Test duplicate detection logic
   - Test data completeness validation
   - Test anomaly detection (win probability, ratings)
   - Test rollback query construction

8. **Command-line flags are documented**
   - `--help` shows all available flags
   - README or script docstring includes usage examples
   - Error messages guide user to correct usage

9. **Rollback procedure is tested and safe**
   - Integration test verifies rollback deletes correct predictions
   - Test confirms rollback doesn't delete other predictions
   - Requires explicit confirmation (no accidental deletions)

---

## Technical Notes

### Command-Line Interface

**Script Signature:**
```bash
python3 scripts/backfill_historical_predictions.py [OPTIONS]

Options:
  --dry-run                  Preview changes without writing to database
  --require-complete-data    Abort if any historical ratings are missing
  --delete-backfilled        Delete predictions from previous backfill run
  --start-time DATETIME      Start time for rollback (required with --delete-backfilled)
  --end-time DATETIME        End time for rollback (required with --delete-backfilled)
  --season YEAR              Process only specific season (default: all seasons)
  --week WEEK                Process only specific week (default: all weeks)
  --help                     Show this help message
```

### Implementation Pattern

**Argparse Setup:**
```python
import argparse

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Backfill historical predictions using historical ELO ratings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be created (no changes)
  python3 scripts/backfill_historical_predictions.py --dry-run

  # Backfill all historical predictions
  python3 scripts/backfill_historical_predictions.py

  # Backfill only 2025 season, Week 5
  python3 scripts/backfill_historical_predictions.py --season 2025 --week 5

  # Rollback predictions created between specific times
  python3 scripts/backfill_historical_predictions.py --delete-backfilled \\
    --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to database')
    parser.add_argument('--require-complete-data', action='store_true',
                        help='Abort if any historical ratings are missing')
    parser.add_argument('--delete-backfilled', action='store_true',
                        help='Delete predictions from previous backfill run')
    parser.add_argument('--start-time', type=str,
                        help='Start time for rollback (format: "YYYY-MM-DD HH:MM:SS")')
    parser.add_argument('--end-time', type=str,
                        help='End time for rollback (format: "YYYY-MM-DD HH:MM:SS")')
    parser.add_argument('--season', type=int,
                        help='Process only specific season')
    parser.add_argument('--week', type=int,
                        help='Process only specific week')

    args = parser.parse_args()

    # Validate rollback arguments
    if args.delete_backfilled:
        if not args.start_time or not args.end_time:
            parser.error('--delete-backfilled requires both --start-time and --end-time')

    return args
```

**Duplicate Check:**
```python
def prediction_exists(db, game_id: int) -> bool:
    """
    Check if a prediction already exists for a game.

    Args:
        db: Database session
        game_id: ID of the game to check

    Returns:
        bool: True if prediction exists, False otherwise
    """
    from models import Prediction

    count = db.query(Prediction).filter(Prediction.game_id == game_id).count()
    return count > 0
```

**Data Completeness Validation:**
```python
def validate_historical_data(db, season: int, week: int, team_ids: list) -> dict:
    """
    Validate that historical ratings exist for all teams.

    Args:
        db: Database session
        season: Season year
        week: Week number
        team_ids: List of team IDs to check

    Returns:
        dict: {
            'complete': bool,
            'missing_teams': list of team_ids without ratings
        }
    """
    from models import RankingHistory, Team

    found_teams = db.query(RankingHistory.team_id).filter(
        RankingHistory.team_id.in_(team_ids),
        RankingHistory.season == season,
        RankingHistory.week == week
    ).all()

    found_team_ids = {t[0] for t in found_teams}
    missing_team_ids = [tid for tid in team_ids if tid not in found_team_ids]

    if missing_team_ids:
        # Get team names for logging
        teams = db.query(Team).filter(Team.id.in_(missing_team_ids)).all()
        team_names = {t.id: t.school for t in teams}

        return {
            'complete': False,
            'missing_teams': missing_team_ids,
            'missing_team_names': [team_names.get(tid, f"Team {tid}") for tid in missing_team_ids]
        }

    return {'complete': True, 'missing_teams': []}
```

**Anomaly Detection:**
```python
def detect_anomalies(prediction_data: dict, home_team: str, away_team: str,
                     home_rating: float, away_rating: float) -> list:
    """
    Detect unusual predictions or ratings.

    Args:
        prediction_data: Dictionary with prediction results
        home_team: Home team name
        away_team: Away team name
        home_rating: Home team ELO rating
        away_rating: Away team ELO rating

    Returns:
        list: List of warning messages
    """
    warnings = []

    # Check win probability range
    win_prob = prediction_data['home_win_probability']
    if win_prob < 5 or win_prob > 95:
        warnings.append(
            f"Unusual prediction: {home_team} vs {away_team} - {win_prob}% confidence"
        )

    # Check rating ranges
    if home_rating < 1000 or home_rating > 2500:
        warnings.append(f"Unusual rating: {home_team} has rating {home_rating}")

    if away_rating < 1000 or away_rating > 2500:
        warnings.append(f"Unusual rating: {away_team} has rating {away_rating}")

    # Check large rating gap
    rating_diff = abs(home_rating - away_rating)
    if rating_diff > 500:
        warnings.append(
            f"Large rating gap: {home_team} ({home_rating}) vs "
            f"{away_team} ({away_rating}) - difference: {rating_diff}"
        )

    return warnings
```

**Rollback Function:**
```python
def rollback_predictions(db, start_time: str, end_time: str, dry_run: bool = False) -> int:
    """
    Delete predictions created within a time range.

    Args:
        db: Database session
        start_time: Start timestamp (format: "YYYY-MM-DD HH:MM:SS")
        end_time: End timestamp (format: "YYYY-MM-DD HH:MM:SS")
        dry_run: If True, only count predictions without deleting

    Returns:
        int: Number of predictions deleted (or would be deleted in dry-run)
    """
    from datetime import datetime
    from models import Prediction

    # Parse timestamps
    try:
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {e}")
        logger.error('Expected format: "YYYY-MM-DD HH:MM:SS"')
        return 0

    # Query predictions in range
    predictions = db.query(Prediction).filter(
        Prediction.created_at >= start_dt,
        Prediction.created_at <= end_dt
    ).all()

    count = len(predictions)

    if count == 0:
        logger.info(f"No predictions found between {start_time} and {end_time}")
        return 0

    # Confirm deletion
    logger.warning(f"Found {count} predictions to delete")
    if not dry_run:
        confirmation = input(f"Delete {count} predictions? (yes/no): ")
        if confirmation.lower() != 'yes':
            logger.info("Deletion cancelled")
            return 0

        # Delete predictions
        for pred in predictions:
            db.delete(pred)

        db.commit()
        logger.info(f"✓ Deleted {count} predictions from backfill run")
    else:
        logger.info(f"DRY RUN - Would delete {count} predictions")

    return count
```

**Enhanced Summary Report:**
```python
def print_summary(stats: dict, duration: float):
    """
    Print comprehensive summary report.

    Args:
        stats: Dictionary with statistics
        duration: Script duration in seconds
    """
    logger.info("=" * 80)
    logger.info("Summary:")
    logger.info(f"  Total games processed: {stats['total_games']}")
    logger.info(f"  Predictions created: {stats['created']}")
    logger.info(f"  Predictions skipped: {stats['skipped']} (already existed)")
    logger.info(f"  Warnings: {stats['warnings']} (missing data or anomalies)")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"  Duration: {duration:.1f} seconds")

    if stats['created'] > 0:
        avg_time = duration / stats['created']
        logger.info(f"  Average time per prediction: {avg_time:.3f} seconds")

    if stats.get('dry_run'):
        logger.info("")
        logger.info("DRY RUN - No changes written to database")
        logger.info("Run without --dry-run to commit changes")

    logger.info("=" * 80)
```

---

## Definition of Done

- [ ] Script accepts `--dry-run` flag and performs preview without committing
- [ ] Script checks for duplicate predictions before creating
- [ ] Script validates historical data completeness
- [ ] Script detects and logs data anomalies (win probability, ratings, gaps)
- [ ] Script supports `--delete-backfilled` flag with time range for rollback
- [ ] Script requires confirmation before deleting predictions
- [ ] Script generates comprehensive summary report with all statistics
- [ ] All command-line flags documented in `--help`
- [ ] Unit tests created for validation logic
- [ ] Integration test verifies rollback works correctly
- [ ] README updated with safety check examples

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Accidental deletion of production predictions during rollback

**Mitigation:**
- Require explicit `--delete-backfilled` flag
- Require both `--start-time` and `--end-time` parameters
- Show count of predictions to delete before executing
- Require "yes" confirmation (not just Enter key)
- Log all deletions with timestamps
- Dry-run mode allows testing rollback query first

**Rollback for Rollback:**
Database backups should be created before running backfill script:
```bash
# Backup database before backfill
cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d_%H%M%S).db

# Run backfill
python3 scripts/backfill_historical_predictions.py

# If needed, restore backup
cp cfb_rankings_backup_YYYYMMDD_HHMMSS.db cfb_rankings.db
```

### Compatibility Verification

- ✅ **No breaking changes to existing APIs:** Script is standalone, no API changes
- ✅ **Database changes are additive only:** Only adds predictions, deletions are explicit
- ✅ **UI changes follow existing design patterns:** No UI changes
- ✅ **Performance impact is negligible:** Validation adds minimal overhead

---

## Validation Checklist

### Scope Validation

- ✅ **Story can be completed in one development session:** Adding flags and validation to existing script, 2-3 hours work
- ✅ **Integration approach is straightforward:** Standard argparse and validation patterns
- ✅ **Follows existing patterns exactly:** Command-line flag handling matches weekly_update.py
- ✅ **No design or architecture work required:** All patterns established

### Clarity Check

- ✅ **Story requirements are unambiguous:** Each flag has clear behavior specification
- ✅ **Integration points are clearly specified:** Extends Story 001 script
- ✅ **Success criteria are testable:** All criteria have objective pass/fail conditions
- ✅ **Rollback approach is simple:** Standard SQL DELETE with timestamp range

---

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_backfill_validation.py`

```python
def test_prediction_exists_returns_true_when_prediction_found():
    """Verify duplicate detection returns True when prediction exists"""
    # Setup: create game and prediction
    # Test: call prediction_exists(game_id)
    # Assert: returns True

def test_prediction_exists_returns_false_when_no_prediction():
    """Verify duplicate detection returns False when no prediction exists"""
    # Setup: create game without prediction
    # Test: call prediction_exists(game_id)
    # Assert: returns False

def test_validate_historical_data_complete():
    """Verify data completeness validation succeeds when all ratings exist"""
    # Setup: create RankingHistory records for all teams
    # Test: call validate_historical_data()
    # Assert: returns {'complete': True, 'missing_teams': []}

def test_validate_historical_data_missing_teams():
    """Verify data completeness validation identifies missing teams"""
    # Setup: create RankingHistory for only 1 of 2 teams
    # Test: call validate_historical_data()
    # Assert: returns {'complete': False, 'missing_teams': [team_id]}

def test_detect_anomalies_unusual_win_probability():
    """Verify anomaly detection flags extreme win probabilities"""
    # Test: prediction with 98% win probability
    # Assert: returns warning about unusual prediction

def test_detect_anomalies_unusual_rating():
    """Verify anomaly detection flags ratings outside normal range"""
    # Test: team with rating 800 (very low)
    # Assert: returns warning about unusual rating

def test_detect_anomalies_large_rating_gap():
    """Verify anomaly detection flags large rating differences"""
    # Test: home rating 2200, away rating 1400 (800 point gap)
    # Assert: returns warning about large gap

def test_rollback_query_construction():
    """Verify rollback builds correct DELETE query"""
    # Test: build rollback query with time range
    # Assert: query includes correct WHERE clause with BETWEEN
```

### Integration Tests

**File:** `tests/integration/test_backfill_safety.py`

```python
def test_dry_run_mode_does_not_commit(test_db):
    """Verify --dry-run flag prevents database writes"""
    # Setup: create games without predictions
    # Run: backfill script with --dry-run
    # Assert: prediction count in database is still 0
    # Assert: script logged "DRY RUN - No changes written"

def test_duplicate_detection_skips_existing_predictions(test_db):
    """Verify script skips games that already have predictions"""
    # Setup: create 3 games, 1 already has prediction
    # Run: backfill script
    # Assert: only 2 new predictions created
    # Assert: script logged "Skipping game X - prediction already exists"

def test_rollback_deletes_correct_predictions(test_db):
    """Verify --delete-backfilled removes only predictions in time range"""
    # Setup: create predictions with timestamps: 09:55, 10:02, 10:08, 10:15
    # Run: rollback with start=10:00, end=10:10
    # Assert: only predictions at 10:02 and 10:08 deleted
    # Assert: predictions at 09:55 and 10:15 still exist

def test_require_complete_data_aborts_on_missing_ratings(test_db):
    """Verify --require-complete-data flag stops processing when data missing"""
    # Setup: create games with some missing historical ratings
    # Run: backfill with --require-complete-data flag
    # Assert: script exits with error
    # Assert: no predictions created
    # Assert: script logged which teams/weeks are missing
```

### Manual Test Scenarios

1. **Dry Run Preview:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --dry-run
   # Verify: Shows what would be created, no database changes
   ```

2. **Duplicate Prevention:**
   ```bash
   # Run twice
   python3 scripts/backfill_historical_predictions.py
   python3 scripts/backfill_historical_predictions.py
   # Verify: Second run skips all games (already have predictions)
   ```

3. **Rollback:**
   ```bash
   # Backfill and note start/end times
   python3 scripts/backfill_historical_predictions.py

   # Rollback
   python3 scripts/backfill_historical_predictions.py --delete-backfilled \
     --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
   # Verify: Requires "yes" confirmation, deletes correct predictions
   ```

---

## Example Output

### Dry Run Mode
```
================================================================================
Retrospective Prediction Backfill - DRY RUN MODE
================================================================================
Season: 2025
Found 350 processed games without predictions

Week 1: Processing 48 games...
  [DRY RUN] Would create 48 predictions
  Sample prediction: Alabama vs Florida State - Alabama 65% win probability

Week 2: Processing 50 games...
  [DRY RUN] Would create 50 predictions

...

--------------------------------------------------------------------------------
Summary:
  Total games processed: 350
  Predictions created: 0 (dry run mode)
  Predictions that would be created: 350
  Warnings: 1 (unusual predictions)
  Errors: 0
  Duration: 6.2 seconds

DRY RUN - No changes written to database
Run without --dry-run to commit changes
================================================================================
```

### With Duplicate Detection
```
================================================================================
Retrospective Prediction Backfill
================================================================================
Season: 2025
Found 350 processed games, checking for existing predictions...
Found 100 games already have predictions - will skip these

Week 1: Processing 48 games...
  ⊘ Skipped 15 games (predictions already exist)
  ✓ Generated 33 predictions

Week 2: Processing 50 games...
  ⊘ Skipped 20 games (predictions already exist)
  ✓ Generated 30 predictions

...

--------------------------------------------------------------------------------
Summary:
  Total games processed: 350
  Predictions created: 250
  Predictions skipped: 100 (already existed)
  Warnings: 1 (missing historical ratings)
  Errors: 0
  Duration: 8.1 seconds

✅ Backfill completed successfully
================================================================================
```

### Rollback Mode
```
================================================================================
Retrospective Prediction Rollback
================================================================================
Querying predictions between 2025-10-27 10:00:00 and 2025-10-27 10:05:00...

⚠ Found 350 predictions to delete

Delete 350 predictions? (yes/no): yes

Deleting predictions...
✓ Deleted 350 predictions from backfill run

Summary:
  Predictions deleted: 350
  Time range: 2025-10-27 10:00:00 to 2025-10-27 10:05:00
  Duration: 1.2 seconds

✅ Rollback completed successfully
================================================================================
```

---

**Created:** 2025-10-27
**Last Updated:** 2025-10-27
**Assigned To:** Development Team
