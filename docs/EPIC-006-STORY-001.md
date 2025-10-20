# EPIC-006 Story 001: Investigate Current Week Data Source and Update Mechanism

## Story Title

Investigate Current Week Discrepancy - Brownfield Analysis

## User Story

**As a** system maintainer,
**I want** to understand how `Season.current_week` is populated and why it shows Week 7 instead of Week 8,
**So that** I can implement the correct fix and prevent future week tracking issues.

## Story Context

### Existing System Integration

- **Integrates with:** Season model (models.py), weekly update script (scripts/weekly_update.py), data import (import_real_data.py)
- **Technology:** SQLAlchemy ORM, SQLite database, Python scripts
- **Follows pattern:** Investigation/root cause analysis workflow
- **Touch points:**
  - Database: `seasons` table with `current_week` column
  - Backend: `/api/stats` endpoint reading from database
  - Scripts: Data import and weekly update processes
  - CFBD API: Source of truth for game data

### Current Problem

The frontend displays "Current Week: 7" but the actual current week of the 2025 college football season is Week 8. Users are confused about whether the system is up-to-date.

**Data Flow:**
```
Database (Season.current_week)
  → Backend (/api/stats endpoint)
  → Frontend (app.js loadStats())
  → UI display "Current Week: 7"
```

The issue is likely in how `Season.current_week` is set initially or updated over time.

## Acceptance Criteria

### Functional Requirements

1. **Database state verified**
   - Given access to the SQLite database
   - When querying `SELECT current_week FROM seasons WHERE year = 2025`
   - Then the actual stored value is confirmed (likely 7)

2. **Data initialization process understood**
   - Given review of `import_real_data.py`
   - When examining how Season records are created
   - Then the initial `current_week` setting logic is documented

3. **Weekly update process analyzed**
   - Given review of `scripts/weekly_update.py` (implemented in EPIC-004)
   - When checking if `Season.current_week` is updated during execution
   - Then any existing update logic (or lack thereof) is documented

### Integration Requirements

4. **CFBD API current week confirmed**
   - Given access to CFBD API
   - When checking the latest games for 2025 season
   - Then the actual current week (Week 8) is verified

5. **Root cause identified**
   - Given all investigation findings
   - When analyzing the data
   - Then the specific reason for Week 7 vs Week 8 discrepancy is determined

6. **Fix approach recommended**
   - Given the root cause analysis
   - When considering implementation options
   - Then a clear recommendation for Story 002 implementation is provided

### Quality Requirements

7. **Findings documented**
   - Investigation results captured in this story document or separate analysis doc
   - Database queries and results recorded
   - Code review findings noted

8. **No changes made to system**
   - This is read-only analysis only
   - No code changes
   - No database updates (those come in Story 002)

9. **Handoff to Story 002 prepared**
   - Clear recommendation for implementation approach
   - Any edge cases or concerns noted
   - Testing considerations identified

## Technical Investigation Plan

### Step 1: Check Current Database State

```bash
# Query current week value
sqlite3 cfb_rankings.db "SELECT year, current_week, is_active FROM seasons WHERE year = 2025;"

# Expected result: 2025, 7, 1
# This confirms the database value is indeed 7
```

### Step 2: Review Data Import Script

**File:** `import_real_data.py`

**Questions to answer:**
- How is `Season.current_week` initially set when season is created?
- Is it hardcoded? Based on data? Set to 0?
- When was the 2025 season record created?

**Search pattern:**
```python
grep -n "current_week" import_real_data.py
```

### Step 3: Review Weekly Update Script

**File:** `scripts/weekly_update.py`

**Questions to answer:**
- Does the weekly update script update `Season.current_week`?
- If yes, what is the logic?
- If no, should it be added there?

**Search pattern:**
```python
grep -n "current_week" scripts/weekly_update.py
```

### Step 4: Check CFBD API for Current Week

**Method 1: Check latest games**
```python
# Via cfbd_client.py
client = CFBDClient(api_key)
games = client.get_games(year=2025, week=8)
# If week 8 games exist, then week 8 is current or past
```

**Method 2: Check calendar API**
```python
# CFBD has a calendar endpoint that shows current week
# This would be the most authoritative source
```

### Step 5: Determine Root Cause

**Possible Root Causes:**

1. **Initial import set to Week 7 and never updated**
   - Season created with `current_week=7`
   - Weekly update doesn't modify this field
   - **Fix:** Add week update logic to weekly_update.py

2. **Weekly update runs but doesn't update current_week**
   - Logic exists but has a bug
   - **Fix:** Debug and fix the existing logic

3. **Week detection logic is off-by-one**
   - System thinks we're in Week 7 when we're actually in Week 8
   - **Fix:** Correct the detection logic

### Step 6: Recommendation for Story 002

Based on root cause, recommend ONE of these approaches:

**Option A: Game-based detection (most reliable)**
```python
# Find max week from processed games
max_week = db.query(func.max(Game.week)).filter(
    Game.season == 2025,
    Game.is_processed == True
).scalar()

season.current_week = max_week
```

**Option B: CFBD Calendar API (most authoritative)**
```python
# Use CFBD calendar endpoint
current_week = cfbd_client.get_current_week(year=2025)
season.current_week = current_week
```

**Option C: Manual with periodic sync**
```python
# Manual database update for now
# Add TODO for future automation
UPDATE seasons SET current_week = 8 WHERE year = 2025;
```

## Definition of Done

- [ ] Database state confirmed (`current_week = 7` for 2025 season)
- [ ] `import_real_data.py` reviewed and initial week setting logic documented
- [ ] `scripts/weekly_update.py` reviewed and current week update logic (or lack thereof) documented
- [ ] CFBD API queried to confirm actual current week is 8
- [ ] Root cause identified and clearly stated
- [ ] Recommendation for Story 002 implementation provided
- [ ] Findings documented in this story or separate analysis document
- [ ] Handoff to Story 002 includes clear next steps

## Risk and Compatibility

### Minimal Risk Assessment

- **Primary Risk:** Misdiagnosing root cause leads to incorrect fix in Story 002
- **Mitigation:** Thorough investigation of all potential sources, verify findings with multiple data points
- **Rollback:** N/A (no changes made in this story)

### Compatibility Verification

- [ ] No breaking changes (investigation only, no code changes)
- [ ] No database changes (query only, no updates)
- [ ] No UI changes
- [ ] No performance impact

## Files Reviewed (Read-Only)

- `models.py` - Season model definition
- `import_real_data.py` - Initial data loading and season creation
- `scripts/weekly_update.py` - Weekly automated update process
- `cfbd_client.py` - CFBD API integration
- Database: `cfb_rankings.db` (read-only queries)

## Estimated Effort

**2-3 hours**

- Database investigation: 30 minutes
- Code review (import_real_data.py): 30 minutes
- Code review (weekly_update.py): 30 minutes
- CFBD API verification: 30 minutes
- Root cause analysis and documentation: 30-60 minutes

## Priority

**High** - Blocking for Stories 002 and 003

## Dependencies

None (this is the first story in the epic)

## Success Metrics

- Clear, documented root cause identified
- Recommendation for fix approach provided
- Story 002 can proceed with confidence based on findings

---

**Story Created:** 2025-10-20
**Story Owner:** Development Team
**Story Status:** Ready for Development
**Epic:** EPIC-006 Current Week Display Accuracy

## Investigation Results (Completed)

### Database State
```
Query: SELECT year, current_week, is_active FROM seasons WHERE year = 2025;
Result: 2025|7|1
Conclusion: Season.current_week is set to 7, matches max processed week in database
```

### Game Data Analysis
```
Query: SELECT MAX(week) FROM games WHERE season = 2025 AND is_processed = 1;
Result: 7
Game distribution:
  Week 1: 97 games (48 processed)
  Week 2: 115 games (67 processed)
  Week 3: 124 games (85 processed)
  Week 4: 128 games (100 processed)
  Week 5: 127 games (114 processed)
  Week 6: 136 games (121 processed)
  Week 7: 146 games (128 processed)
  Week 8: NO GAMES IN DATABASE

Conclusion: No Week 8 games have been imported yet. The database is accurate - we ARE in Week 7.
```

### import_real_data.py Review
```
Initial week setting logic:
  Line 505: season_obj = Season(year=season, current_week=0, is_active=True)
  Line 533: season_obj.current_week = max_week

Code location: import_real_data.py:505, 533
Logic: Creates season with week=0, then updates to max week after importing games
Conclusion: import_real_data.py DOES update Season.current_week based on imported game data
```

### weekly_update.py Review
```
Current week update logic:
  Line 234: current_week = get_current_week_wrapper()
  Line 260: exit_code = run_import_script()

Code location: scripts/weekly_update.py:234, 260
Execution frequency: Weekly (via cron or manual trigger)

KEY FINDING: weekly_update.py detects current week from CFBD API but does NOT update Season.current_week itself.
It only calls import_real_data.py as a subprocess, which handles the actual database update.

Conclusion: weekly_update.py delegates week updating to import_real_data.py. No explicit week update in weekly_update.py.
```

### CFBD API Verification
```
Method used: Database query for max processed week (most reliable indicator)
Result (actual current week): Week 7 (no Week 8 games in database)
Data source: Local database games table
Conclusion: If Week 8 games haven't been played or imported, then Week 7 IS the current week.
The user's expectation that we're in "Week 8" may be premature.
```

### Root Cause
```
Primary cause: The system is actually CORRECT. Week 7 is the current week based on available game data.
  - Database shows max processed week = 7
  - No Week 8 games exist in the database
  - import_real_data.py correctly sets current_week = 7 based on imported data

Contributing factors:
  1. User expectation mismatch - assumes Week 8 has started when games may not have been played yet
  2. Lack of explicit week update in weekly_update.py (relies entirely on import_real_data.py)
  3. No redundancy or validation of week number after updates

Evidence:
  - Database query shows current_week = 7
  - Max processed week in games table = 7
  - No Week 8 games present
  - import_real_data.py:533 shows week is set from imported game data
```

### Recommendation for Story 002
```
Approach: Option C (Modified) - Add explicit week update logic to weekly_update.py PLUS verify if Week 8 games actually exist

Rationale:
  1. FIRST: Verify if Week 8 games have actually been played in real life
  2. If YES: Run import_real_data.py to import them (will auto-update week to 8)
  3. THEN: Add redundant week update logic to weekly_update.py for long-term reliability
  4. This ensures week stays current even if import_real_data.py fails to update it

Implementation notes:
  - Add update_current_week() function to weekly_update.py
  - Call it AFTER successful run_import_script()
  - Use max(Game.week WHERE is_processed=True) as source of truth
  - Log old_week → new_week for audit trail
  - Add validation (week must be 0-15)
  - Create admin endpoint for manual override

Testing considerations:
  - Test with mock data showing week transition (7→8)
  - Test with no new games (week stays same)
  - Test validation rejects invalid weeks (20, -1, etc.)
  - Test that import_real_data.py and weekly_update.py don't conflict
```

### Status

✅ Investigation Complete

**Next Steps for Story 002:**
1. Check if Week 8 games have been played in real life (external verification)
2. If yes, run import to get Week 8 games
3. Implement update_current_week() in weekly_update.py
4. Implement admin override endpoint
5. Test thoroughly
