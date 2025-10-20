# EPIC-006 Story 003: Add Current Week Validation and Monitoring

## Story Title

Add Current Week Validation and Monitoring - Brownfield Enhancement

## User Story

**As a** system administrator,
**I want** validation and monitoring for current week updates,
**So that** I can catch and fix any week tracking issues quickly and have confidence in the system's accuracy.

## Story Context

### Existing System Integration

- **Integrates with:**
  - Week update logic from Story 002 (`scripts/weekly_update.py`)
  - UpdateTask model (`models.py:158-186` for logging)
  - Admin endpoints (`main.py`)
  - Testing infrastructure (`tests/test_weekly_update.py`)

- **Technology:** Python validation logic, SQLAlchemy, pytest
- **Follows pattern:** Validation and monitoring pattern from EPIC-004
- **Touch points:**
  - Weekly update script: Add validation before updates
  - UpdateTask records: Log week changes for audit trail
  - Test suite: Add coverage for week detection logic
  - Documentation: Document week management procedures

### Current Problem

After implementing automatic week detection in Story 002, we need safeguards to ensure:
1. Week numbers are always valid and reasonable
2. Week changes are logged for troubleshooting
3. Tests verify the week detection logic works correctly
4. Team knows how to manually correct week issues if they occur

## Acceptance Criteria

### Functional Requirements

1. **Week validation prevents invalid values**
   - Given a week number is about to be set
   - When the week is < 0 or > 15
   - Then the update is rejected with a clear error message
   - And the database retains the previous valid value
   - And the error is logged for monitoring

2. **Week changes are logged in UpdateTask**
   - Given the weekly update runs and changes the current week
   - When `update_current_week()` modifies `Season.current_week`
   - Then the UpdateTask metadata includes the week change
   - And the log message clearly states old_week → new_week
   - And audit trail is available for troubleshooting

3. **Admin endpoint includes current week in response**
   - Given calling `/api/stats` or an admin status endpoint
   - When the response is returned
   - Then it includes the current week number
   - And the information is easily accessible for monitoring

### Integration Requirements

4. **Validation integrates seamlessly with Story 002 logic**
   - Given `update_current_week()` function exists from Story 002
   - When adding validation logic
   - Then it executes before the database update
   - And doesn't interfere with normal operation
   - And gracefully handles edge cases

5. **UpdateTask metadata schema extended**
   - Given UpdateTask already tracks update operations (EPIC-004)
   - When extending metadata to include week changes
   - Then existing metadata fields are preserved
   - And new `week_change` field is added
   - And backward compatibility is maintained

6. **Tests verify week detection works correctly**
   - Given the test suite has coverage for weekly updates
   - When running tests for week detection
   - Then various scenarios are covered:
     - No games processed (week = 0)
     - Single week of games (week = that week)
     - Multiple weeks (week = max week)
     - Invalid week values rejected

### Quality Requirements

7. **Comprehensive test coverage**
   - Unit tests for `update_current_week()` function
   - Unit tests for week validation
   - Integration test for weekly update workflow
   - Edge case tests (empty database, invalid data)

8. **Documentation is complete**
   - Manual week correction procedure documented
   - Week validation rules explained
   - Troubleshooting guide for week tracking issues
   - Admin endpoint usage examples

9. **Code quality maintained**
   - Type hints added for validation functions
   - Error messages are clear and actionable
   - Logging is consistent with existing patterns
   - No code duplication

## Technical Implementation

### Part 1: Week Validation Function

**File:** `scripts/weekly_update.py`

**Add validation function:**
```python
def validate_week_number(week: int, season_year: int, logger) -> bool:
    """
    Validate that a week number is reasonable for college football.

    Args:
        week: Week number to validate
        season_year: Year of the season
        logger: Logger instance

    Returns:
        bool: True if valid, False otherwise
    """
    MIN_WEEK = 0  # Preseason
    MAX_WEEK = 15  # Includes bowl season

    if not isinstance(week, int):
        logger.error(f"Week must be an integer, got {type(week)}: {week}")
        return False

    if week < MIN_WEEK:
        logger.error(f"Week {week} is below minimum {MIN_WEEK} for season {season_year}")
        return False

    if week > MAX_WEEK:
        logger.error(f"Week {week} exceeds maximum {MAX_WEEK} for season {season_year}")
        return False

    logger.debug(f"Week {week} validated successfully for season {season_year}")
    return True
```

**Update `update_current_week()` to use validation:**
```python
def update_current_week(db: Session, season_year: int, logger) -> int:
    """Update current week with validation"""
    # ... existing logic to get max_week ...

    # ADDED: Validate before updating
    if not validate_week_number(max_week, season_year, logger):
        logger.warning(f"Week validation failed for {max_week}, keeping current value")
        return season.current_week  # Return existing value

    # ... rest of existing logic ...
```

### Part 2: Enhanced Logging in UpdateTask

**File:** `scripts/weekly_update.py`

**Update main update function to log week changes:**
```python
def run_weekly_update(api_key: str, season: int):
    """Main weekly update orchestration"""
    # ... existing setup ...

    try:
        # Get old week before update
        season_record = db.query(Season).filter(Season.year == season).first()
        old_week = season_record.current_week if season_record else 0

        # ... existing game import and ranking calculation ...

        # Update current week
        new_week = update_current_week(db, season, logger)

        # Log week change
        if old_week != new_week:
            logger.info(f"Week changed: {old_week} → {new_week} for season {season}")
        else:
            logger.debug(f"Week unchanged: {new_week}")

        # ... existing UpdateTask record creation ...
        task.metadata = {
            # ... existing metadata ...
            "week_change": {
                "old_week": old_week,
                "new_week": new_week,
                "changed": old_week != new_week
            }
        }

    except Exception as e:
        # ... existing error handling ...
```

### Part 3: Test Coverage

**File:** `tests/test_weekly_update.py`

**Add new test cases:**
```python
import pytest
from scripts.weekly_update import update_current_week, validate_week_number


class TestWeekValidation:
    """Test week number validation"""

    def test_validate_week_valid_range(self, logger):
        """Valid weeks 0-15 should pass"""
        for week in range(0, 16):
            assert validate_week_number(week, 2025, logger) is True

    def test_validate_week_negative(self, logger):
        """Negative weeks should fail"""
        assert validate_week_number(-1, 2025, logger) is False

    def test_validate_week_too_high(self, logger):
        """Weeks > 15 should fail"""
        assert validate_week_number(20, 2025, logger) is False
        assert validate_week_number(100, 2025, logger) is False

    def test_validate_week_non_integer(self, logger):
        """Non-integer weeks should fail"""
        assert validate_week_number("5", 2025, logger) is False
        assert validate_week_number(5.5, 2025, logger) is False
        assert validate_week_number(None, 2025, logger) is False


class TestCurrentWeekUpdate:
    """Test current week detection and update"""

    def test_update_current_week_no_games(self, db_session, logger):
        """Week should be 0 when no games processed"""
        # Setup: Season with no games
        season = SeasonFactory(year=2025, current_week=0)
        db_session.add(season)
        db_session.commit()

        # Execute
        result = update_current_week(db_session, 2025, logger)

        # Assert
        assert result == 0
        assert season.current_week == 0

    def test_update_current_week_single_week(self, db_session, logger):
        """Week should match the single processed week"""
        # Setup: Season with week 5 games
        season = SeasonFactory(year=2025, current_week=0)
        team1 = TeamFactory()
        team2 = TeamFactory()
        game = GameFactory(
            season=2025,
            week=5,
            home_team_id=team1.id,
            away_team_id=team2.id,
            is_processed=True
        )
        db_session.add_all([season, team1, team2, game])
        db_session.commit()

        # Execute
        result = update_current_week(db_session, 2025, logger)

        # Assert
        assert result == 5
        assert season.current_week == 5

    def test_update_current_week_multiple_weeks(self, db_session, logger):
        """Week should be max of all processed weeks"""
        # Setup: Season with weeks 3, 5, 8 games
        season = SeasonFactory(year=2025, current_week=0)
        team1 = TeamFactory()
        team2 = TeamFactory()

        for week in [3, 5, 8]:
            game = GameFactory(
                season=2025,
                week=week,
                home_team_id=team1.id,
                away_team_id=team2.id,
                is_processed=True
            )
            db_session.add(game)

        db_session.add_all([season, team1, team2])
        db_session.commit()

        # Execute
        result = update_current_week(db_session, 2025, logger)

        # Assert
        assert result == 8  # Max week
        assert season.current_week == 8

    def test_update_current_week_ignores_unprocessed(self, db_session, logger):
        """Unprocessed games should not affect week detection"""
        # Setup: Processed week 5, unprocessed week 10
        season = SeasonFactory(year=2025, current_week=0)
        team1 = TeamFactory()
        team2 = TeamFactory()

        processed_game = GameFactory(
            season=2025,
            week=5,
            home_team_id=team1.id,
            away_team_id=team2.id,
            is_processed=True
        )
        unprocessed_game = GameFactory(
            season=2025,
            week=10,
            home_team_id=team1.id,
            away_team_id=team2.id,
            is_processed=False
        )

        db_session.add_all([season, team1, team2, processed_game, unprocessed_game])
        db_session.commit()

        # Execute
        result = update_current_week(db_session, 2025, logger)

        # Assert
        assert result == 5  # Only processed game's week
        assert season.current_week == 5

    def test_update_current_week_invalid_week_rejected(self, db_session, logger, monkeypatch):
        """Invalid detected week should not update database"""
        # Setup: Season exists
        season = SeasonFactory(year=2025, current_week=7)
        db_session.add(season)
        db_session.commit()

        # Mock: Force invalid week detection
        def mock_max_week(*args, **kwargs):
            return 20  # Invalid week

        # This test would require mocking the query, or creating invalid data
        # For now, test the validation function separately
        assert validate_week_number(20, 2025, logger) is False
```

### Part 4: Documentation

**File:** `docs/EPIC-006-WEEK-MANAGEMENT.md` (new file)

**Content:**
```markdown
# Week Management Guide

## Overview

The current week for each season is tracked in the `seasons.current_week` field and displayed on the frontend.

## Automatic Updates

The weekly update script (`scripts/weekly_update.py`) automatically updates `current_week`:
- Detects max week from processed games
- Validates week is in range 0-15
- Updates database if changed
- Logs all changes

## Manual Correction

If the current week is incorrect:

### Option 1: Admin Endpoint (Preferred)
```bash
curl -X POST http://your-domain.com/api/admin/update-current-week \
  -H "Content-Type: application/json" \
  -d '{"year": 2025, "week": 8}'
```

### Option 2: Direct Database Update
```bash
ssh user@vps
cd /var/www/cfb-rankings
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"
sudo systemctl restart gunicorn
```

## Validation Rules

- Week must be an integer
- Week must be >= 0 (preseason)
- Week must be <= 15 (includes bowl season)

## Troubleshooting

**Week not updating automatically:**
1. Check weekly update logs: `tail -f /var/log/cfb-rankings/weekly-update.log`
2. Verify processed games exist: `SELECT MAX(week) FROM games WHERE season=2025 AND is_processed=1;`
3. Check UpdateTask records: `SELECT metadata FROM update_tasks ORDER BY created_at DESC LIMIT 1;`

**Week shows incorrect value:**
1. Use admin endpoint to correct immediately
2. Investigate why automatic detection failed
3. Check logs for validation errors

## Monitoring

Check current week:
```bash
curl http://your-domain.com/api/stats | jq .current_week
```

Check recent week changes:
```bash
SELECT created_at, metadata->>'week_change' as week_change
FROM update_tasks
WHERE metadata->>'week_change' IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```
```

## Definition of Done

- [ ] `validate_week_number()` function implemented
- [ ] Validation integrated into `update_current_week()`
- [ ] UpdateTask metadata includes week change tracking
- [ ] All test cases implemented and passing
- [ ] Documentation file `EPIC-006-WEEK-MANAGEMENT.md` created
- [ ] Manual correction procedure tested
- [ ] Edge cases handled (no games, invalid data, etc.)
- [ ] Code committed to git with descriptive message
- [ ] Changes deployed to production
- [ ] Team trained on manual correction procedure

## Risk and Compatibility

### Minimal Risk Assessment

- **Primary Risk:** Overly strict validation could reject legitimate week values
- **Mitigation:** Use wide validation range (0-15), log all rejections, provide manual override
- **Rollback:** Remove validation logic, revert to Story 002 implementation

### Compatibility Verification

- [x] No breaking changes to existing APIs
- [x] Database schema unchanged (metadata is JSON, flexible)
- [x] UI changes: None
- [x] Performance impact: Negligible (one additional validation check)

## Files Modified

- `scripts/weekly_update.py` (~30 lines for validation and enhanced logging)
- `tests/test_weekly_update.py` (~100 lines for comprehensive test coverage)
- `docs/EPIC-006-WEEK-MANAGEMENT.md` (new documentation file)

## Estimated Effort

**2-3 hours**

- Validation function: 30 minutes
- Integration: 30 minutes
- Test cases: 1 hour
- Documentation: 30 minutes
- Testing and verification: 30 minutes

## Priority

**Medium** - Important for long-term reliability, but not blocking

## Dependencies

- Story 002 (Implementation) must be completed first

## Success Metrics

- All tests pass (including new week validation tests)
- Invalid week numbers are rejected and logged
- Week changes are tracked in UpdateTask metadata
- Documentation is clear and actionable
- Team can manually correct week issues confidently

---

**Story Created:** 2025-10-20
**Story Owner:** Development Team
**Story Status:** Ready for Development (after Story 002)
**Epic:** EPIC-006 Current Week Display Accuracy
