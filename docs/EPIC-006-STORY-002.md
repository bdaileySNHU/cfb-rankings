# EPIC-006 Story 002: Implement Automatic Current Week Detection from CFBD API

## Story Title

Implement Automatic Current Week Detection - Brownfield Enhancement

## User Story

**As a** user viewing the rankings page,
**I want** the current week number to automatically update and stay accurate,
**So that** I always see up-to-date information about what week of the season we're in.

## Story Context

### Existing System Integration

- **Integrates with:**
  - Season model (`models.py:147` - `current_week` field already exists)
  - Weekly update script (`scripts/weekly_update.py` from EPIC-004)
  - Stats API endpoint (`main.py:417-433` - `/api/stats`)
  - Frontend (`frontend/js/app.js:26-39` - `loadStats()` function)

- **Technology:** FastAPI, SQLAlchemy ORM, SQLite, CFBD API client
- **Follows pattern:** Weekly automated update job pattern from EPIC-004
- **Touch points:**
  - Database: `seasons.current_week` column (write)
  - Backend: `/api/stats` endpoint (read, no changes needed)
  - Frontend: No changes needed (already displays the value)
  - CFBD API: Source of game data

### Current Problem

The `Season.current_week` field in the database shows 7, but the actual current week is 8. Based on Story 001 investigation, we need to:
1. Immediately fix the database value to 8
2. Add logic to automatically update this field during weekly data refresh
3. Provide manual override capability for emergency corrections

## Acceptance Criteria

### Functional Requirements

1. **Immediate database fix applied**
   - Given admin access to production database
   - When executing manual UPDATE statement
   - Then `seasons.current_week` for 2025 is set to 8
   - And frontend immediately displays "Current Week: 8" after hard refresh

2. **Automatic week detection implemented**
   - Given the weekly update script runs (via cron or manual trigger)
   - When processing games for the current season
   - Then `Season.current_week` is automatically updated to match the latest processed week
   - And the update is logged in the UpdateTask record

3. **Manual override endpoint created**
   - Given an admin needs to correct the current week
   - When calling `POST /api/admin/update-current-week` with `{year: 2025, week: 8}`
   - Then the database is updated immediately
   - And the response confirms the new week number
   - And the change is logged

### Integration Requirements

4. **Existing `/api/stats` endpoint unchanged**
   - Given the stats endpoint exists and returns current_week
   - When the database value is updated
   - Then the endpoint automatically returns the new value
   - And no API contract changes are needed

5. **Weekly update integration seamless**
   - Given the weekly update script already updates games and rankings
   - When adding current week update logic
   - Then it executes as part of the normal workflow
   - And doesn't interfere with existing update steps
   - And failures are logged but don't block other updates

6. **Frontend requires no changes**
   - Given the frontend already reads and displays current_week from `/api/stats`
   - When the database value changes
   - Then the frontend automatically shows the new week
   - And no JavaScript or HTML modifications are needed

### Quality Requirements

7. **Week detection logic is reliable**
   - Uses max week from successfully processed games as the source of truth
   - Falls back gracefully if no games are processed
   - Validates week number is within reasonable bounds (0-15)

8. **Changes are tested**
   - Manual database update tested locally and verified
   - Automatic update logic tested with mock data
   - Admin endpoint tested with valid and invalid inputs
   - Existing tests still pass

9. **Documentation updated**
   - Manual correction procedure documented
   - Weekly update behavior documented
   - API endpoint documented in main.py docstring

## Technical Implementation

### Part 1: Immediate Database Fix

**File:** Manual SQL execution (local and production)

```sql
-- Verify current state
SELECT year, current_week, is_active FROM seasons WHERE year = 2025;

-- Update to correct week
UPDATE seasons SET current_week = 8 WHERE year = 2025;

-- Verify update
SELECT year, current_week, is_active FROM seasons WHERE year = 2025;
```

**Execution:**
1. Local: `sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"`
2. Production: SSH to VPS, run same command
3. Verify frontend shows Week 8 immediately

### Part 2: Automatic Week Detection

**File:** `scripts/weekly_update.py`

**Add new function:**
```python
def update_current_week(db: Session, season_year: int, logger) -> int:
    """
    Update the current week for a season based on the latest processed games.

    Args:
        db: Database session
        season_year: Year of the season to update
        logger: Logger instance

    Returns:
        int: The updated current week number
    """
    from sqlalchemy import func
    from models import Season, Game

    # Get max week from processed games this season
    max_week = db.query(func.max(Game.week)).filter(
        Game.season == season_year,
        Game.is_processed == True
    ).scalar()

    # Default to 0 if no games processed
    max_week = max_week or 0

    # Validate week is reasonable
    if not (0 <= max_week <= 15):
        logger.warning(f"Detected week {max_week} is out of bounds, skipping update")
        return 0

    # Get season record
    season = db.query(Season).filter(Season.year == season_year).first()
    if not season:
        logger.error(f"Season {season_year} not found")
        return 0

    # Update if changed
    if season.current_week != max_week:
        old_week = season.current_week
        season.current_week = max_week
        db.commit()
        logger.info(f"Updated current week from {old_week} to {max_week} for season {season_year}")
    else:
        logger.debug(f"Current week already {max_week}, no update needed")

    return max_week
```

**Integration into main update function:**
```python
def run_weekly_update(api_key: str, season: int):
    """Main weekly update orchestration"""
    # ... existing setup ...

    try:
        # ... existing game import and ranking calculation ...

        # NEW: Update current week
        current_week = update_current_week(db, season, logger)
        logger.info(f"Current week for season {season}: {current_week}")

        # ... existing UpdateTask record creation ...
        task.metadata = {
            # ... existing metadata ...
            "current_week": current_week  # Add to metadata
        }

    except Exception as e:
        # ... existing error handling ...
```

### Part 3: Manual Override Endpoint

**File:** `main.py`

**Add new admin endpoint:**
```python
@app.post("/api/admin/update-current-week", tags=["Admin"])
async def update_current_week_manual(
    year: int,
    week: int,
    db: Session = Depends(get_db)
):
    """
    Manually update the current week for a season.

    Use this endpoint to correct the current week if automatic detection fails
    or if an immediate update is needed before the weekly update runs.

    Args:
        year: Season year (e.g., 2025)
        week: Week number to set (0-15)

    Returns:
        Success message with updated week number
    """
    # Validate week
    if not (0 <= week <= 15):
        raise HTTPException(
            status_code=400,
            detail=f"Week must be between 0 and 15, got {week}"
        )

    # Get season
    season = db.query(Season).filter(Season.year == year).first()
    if not season:
        raise HTTPException(
            status_code=404,
            detail=f"Season {year} not found"
        )

    # Update
    old_week = season.current_week
    season.current_week = week
    db.commit()

    logger.info(f"Manual current week update: {old_week} → {week} for season {year}")

    return {
        "success": True,
        "season": year,
        "old_week": old_week,
        "new_week": week,
        "message": f"Current week updated from {old_week} to {week}"
    }
```

## Definition of Done

- [ ] Database manually updated to Week 8 (local and production)
- [ ] Frontend verified to display "Current Week: 8"
- [ ] `update_current_week()` function implemented in `scripts/weekly_update.py`
- [ ] Function integrated into main weekly update workflow
- [ ] Admin endpoint `/api/admin/update-current-week` implemented
- [ ] Week validation logic added (0-15 range)
- [ ] Update logic tested locally with mock data
- [ ] Admin endpoint tested with valid and invalid inputs
- [ ] Existing tests still pass
- [ ] Code committed to git with descriptive message
- [ ] Changes deployed to production
- [ ] Documentation updated (manual correction procedure)

## Risk and Compatibility

### Minimal Risk Assessment

- **Primary Risk:** Automatic week detection could set incorrect week if game data is corrupted
- **Mitigation:**
  - Validate week is 0-15 range before updating
  - Log all week changes for audit trail
  - Manual override endpoint allows immediate correction
  - Week detection based on processed games (reliable source)
- **Rollback:**
  ```sql
  UPDATE seasons SET current_week = 8 WHERE year = 2025;
  ```
  Or use admin endpoint: `POST /api/admin/update-current-week {year: 2025, week: 8}`

### Compatibility Verification

- [x] No breaking changes to existing APIs (`/api/stats` unchanged)
- [x] Database changes are data-only (no schema changes)
- [x] UI changes: None (frontend already handles this)
- [x] Performance impact: Minimal (one additional query + update during weekly job)

## Files Modified

- `scripts/weekly_update.py` (~40 lines added for `update_current_week()` function and integration)
- `main.py` (~30 lines for admin endpoint)
- Database: Manual UPDATE for immediate fix
- `docs/EPIC-006-WEEK-MANAGEMENT.md` (new documentation file, created in Story 003)

## Estimated Effort

**3-4 hours**

- Database manual update and verification: 30 minutes
- Implement `update_current_week()` function: 1 hour
- Integrate into weekly_update.py: 30 minutes
- Implement admin endpoint: 1 hour
- Testing (local): 45 minutes
- Deployment to production: 15 minutes

## Priority

**High** - Users need to see correct week ASAP

## Dependencies

- Story 001 (Investigation) should be completed first to confirm root cause and approach

## Success Metrics

- Frontend displays "Current Week: 8" immediately after database fix
- Next weekly update run successfully updates current_week if new games are processed
- Admin endpoint works for manual corrections
- Zero user-reported issues about incorrect week display

---

**Story Created:** 2025-10-20
**Story Owner:** Development Team
**Story Status:** Ready for Development (after Story 001)
**Epic:** EPIC-006 Current Week Display Accuracy

## Testing Checklist

### Local Testing

- [ ] Database update: Verify `current_week` changes from 7 to 8
- [ ] Frontend refresh: Confirm "Current Week: 8" displays
- [ ] Weekly update: Run script locally, verify week detection works
- [ ] Admin endpoint: Test with valid input (year=2025, week=9)
- [ ] Admin endpoint: Test with invalid input (week=20, week=-1)
- [ ] Admin endpoint: Test with nonexistent season (year=2030)
- [ ] Validation: Verify week must be 0-15
- [ ] Logging: Check all updates are logged correctly

### Production Deployment

- [ ] SSH to VPS
- [ ] Pull latest code from GitHub
- [ ] Run database UPDATE statement
- [ ] Restart Gunicorn
- [ ] Verify frontend shows Week 8
- [ ] Monitor logs for any errors
- [ ] Test admin endpoint on production (set to 8, verify it stays 8)

## Quick Reference Commands

```bash
# Local database update
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"

# Production database update
ssh user@vps
cd /var/www/cfb-rankings
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"
sudo systemctl restart gunicorn

# Test admin endpoint (local)
curl -X POST http://localhost:8000/api/admin/update-current-week \
  -H "Content-Type: application/json" \
  -d '{"year": 2025, "week": 8}'

# Verify stats endpoint
curl http://localhost:8000/api/stats | jq .current_week
```
