# EPIC-006: Current Week Display Accuracy - Brownfield Enhancement

## Epic Goal

Ensure the displayed "Current Week" on the rankings page accurately reflects the actual current week of the college football season (Week 8, not Week 7) and automatically stays synchronized with the CFBD API data.

## Epic Overview

**Priority:** High
**Estimated Total Effort:** 6-10 hours
**Status:** Ready for Development
**Type:** Bug Fix + Enhancement

---

## Problem Statement

The rankings page currently displays "Week 7" in the stats header, but the actual current week of the 2025 college football season is Week 8. This creates confusion for users and makes the system appear out-of-date.

**Root Cause:** The `Season.current_week` field in the database is likely set to 7 and is not being automatically updated when new games are processed during the weekly update job.

---

## Epic Description

### Existing System Context

**Current functionality:**
- Frontend displays "Current Week" from the `/api/stats` endpoint
- Backend reads `Season.current_week` from the database (models.py:147)
- Value is returned via `/api/stats` endpoint (main.py:417-433)
- Frontend displays the value in `loadStats()` function (app.js:26-39)

**Technology stack:**
- Backend: FastAPI with SQLAlchemy ORM
- Database: SQLite with `Season` model
- Frontend: Vanilla JavaScript
- Data source: CFBD API

**Integration points:**
- Database: `Season` model with `current_week` field
- Backend API: `/api/stats` endpoint
- Frontend: app.js `loadStats()` function
- Weekly job: `scripts/weekly_update.py`
- CFBD API: Source of truth for game data and current week

### Enhancement Details

**What's being added/changed:**
- Automatic current week detection from CFBD API
- Automatic `Season.current_week` update during weekly data refresh
- Manual admin endpoint for emergency week corrections
- Validation to prevent invalid week numbers
- Immediate fix: Update database to Week 8

**How it integrates:**
- Backend weekly update script will detect current week from latest games processed
- `Season.current_week` field will be updated automatically
- Existing `/api/stats` endpoint continues to work unchanged (no breaking changes)
- Frontend requires no modifications (already displays the value correctly)

**Success criteria:**
- Current week displays as "8" (or whatever the actual current week is)
- Week number automatically updates when weekly job runs
- System remains synchronized with CFBD API data
- Manual override available if automatic detection fails

---

## Stories

### Story 001: Investigate Current Week Data Source and Update Mechanism

**Goal:** Understand how `Season.current_week` is currently populated and identify why it's showing Week 7 instead of Week 8

**Estimated Effort:** 2-3 hours

**Key Tasks:**
- Check database to see current value of `Season.current_week` for 2025 season
- Review `import_real_data.py` to understand initial week setting
- Review `scripts/weekly_update.py` (EPIC-004) to see if current_week is updated
- Check CFBD API to confirm actual current week
- Identify the root cause of the discrepancy
- Document findings and recommendation

**Deliverables:**
- Root cause analysis document
- Database query results showing current state
- Recommendation for fix approach

---

### Story 002: Implement Automatic Current Week Detection from CFBD API

**Goal:** Add logic to automatically detect and update the current week from CFBD API

**Estimated Effort:** 3-4 hours

**Key Tasks:**
- Implement current week detection logic (find max week from processed games)
- Update `scripts/weekly_update.py` to set `Season.current_week` automatically
- Add manual update endpoint `/api/admin/update-current-week` for immediate correction
- Manually update database: `UPDATE seasons SET current_week = 8 WHERE year = 2025`
- Test that frontend displays correct week after changes

**Deliverables:**
- Updated weekly_update.py with automatic week detection
- New admin endpoint for manual week override
- Database updated to Week 8
- Frontend displaying correct week

---

### Story 003: Add Current Week Validation and Monitoring

**Goal:** Ensure week number stays accurate and provide visibility into week tracking

**Estimated Effort:** 2-3 hours

**Key Tasks:**
- Add validation: week must be 0-15 (college football season range)
- Log current week updates in `UpdateTask` records for audit trail
- Add current week to admin endpoint responses
- Add test coverage for week detection and validation logic
- Document week management process for future maintenance

**Deliverables:**
- Week validation logic with reasonable bounds checking
- Update task logs recording week changes
- Unit tests for week detection
- Documentation for manual week correction process

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (`/api/stats` still returns `current_week`)
- [x] Database schema changes are backward compatible (no schema changes, just data updates)
- [x] UI changes follow existing patterns (no UI changes required)
- [x] Performance impact is minimal (one additional field update during weekly job)

---

## Risk Assessment

### Primary Risks

1. **Incorrect week detection could show wrong week number to users**
   - **Mitigation:** Add validation (1-15 range), manual override endpoint, logging
   - **Rollback:** Manual database update: `UPDATE seasons SET current_week = X WHERE year = 2025;`

2. **Weekly update job might fail to update week**
   - **Mitigation:** Explicit error handling, logging, alerts in UpdateTask
   - **Rollback:** Use manual admin endpoint to correct

3. **Edge case: Mid-week vs end-of-week timing**
   - **Mitigation:** Detect week from latest games processed (most reliable)
   - **Fallback:** Manual correction endpoint available

### Rollback Plan

```sql
-- Emergency rollback: Manually set correct week
UPDATE seasons SET current_week = 8 WHERE year = 2025;
-- Then restart API server
```

---

## Definition of Done

- [ ] Story 001: Root cause identified and documented
- [ ] Story 002: Automatic week detection implemented and working
- [ ] Story 003: Validation and monitoring in place
- [ ] Frontend displays correct current week (Week 8 or actual current week)
- [ ] `Season.current_week` automatically updates during weekly data refresh
- [ ] Manual correction endpoint available and tested
- [ ] No regression in existing features (stats endpoint still works)
- [ ] Tests added for week detection and validation logic
- [ ] Documentation updated with week management process

---

## Technical Approach

### Immediate Fix (Story 002)
```python
# Direct database update
UPDATE seasons SET current_week = 8 WHERE year = 2025;
```

### Long-term Solution (Story 002)
```python
# In scripts/weekly_update.py
def update_current_week(db: Session, season_year: int):
    # Get max week from processed games
    max_week = db.query(func.max(Game.week)).filter(
        Game.season == season_year,
        Game.is_processed == True
    ).scalar() or 0

    # Update season
    season = db.query(Season).filter(Season.year == season_year).first()
    if season and season.current_week != max_week:
        season.current_week = max_week
        db.commit()
        logger.info(f"Updated current week to {max_week}")
```

### Validation (Story 003)
```python
# Week validation
def validate_week(week: int) -> bool:
    return 0 <= week <= 15  # College football season range
```

---

## Files Modified

**Story 001 (Investigation):**
- None (read-only analysis)

**Story 002 (Implementation):**
- `scripts/weekly_update.py` (~20 lines added for week detection)
- `main.py` (~15 lines for admin endpoint)
- Database: Manual UPDATE to set current week to 8

**Story 003 (Validation & Monitoring):**
- `scripts/weekly_update.py` (~10 lines for validation)
- `tests/test_weekly_update.py` (~30 lines for tests)
- `docs/WEEK_MANAGEMENT.md` (new documentation file)

---

## Success Metrics

### Quantitative
- Current week displays correctly (Week 8) after Story 002
- Weekly update job successfully updates week on next run
- Zero manual interventions needed after initial fix
- All tests pass

### Qualitative
- Users no longer confused about current week
- System appears up-to-date and accurate
- Team has confidence in automatic week tracking

---

## Deployment Plan

### Story 002 Deployment Steps

```bash
# 1. SSH to VPS
ssh user@vps

# 2. Navigate to app directory
cd /var/www/cfb-rankings

# 3. Pull latest code
git pull origin main

# 4. Manually update database
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"

# 5. Restart Gunicorn
sudo systemctl restart gunicorn

# 6. Verify frontend shows Week 8
curl http://your-domain.com/api/stats | jq .current_week
```

---

## Future Enhancements (Out of Scope)

- Automatic week detection from CFBD calendar API (more robust than game-based detection)
- Week number countdown to postseason
- Historical week tracking and timeline
- Week-based navigation in UI

---

**Epic Created:** 2025-10-20
**Epic Owner:** Product Manager (John)
**Ready for Development:** ✅

---

## Story Documents

- **Epic:** `docs/EPIC-006-CURRENT-WEEK-ACCURACY.md` (this document)
- **Story 001:** `docs/EPIC-006-STORY-001.md`
- **Story 002:** `docs/EPIC-006-STORY-002.md`
- **Story 003:** `docs/EPIC-006-STORY-003.md`
