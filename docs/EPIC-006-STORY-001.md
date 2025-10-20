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

## Investigation Template

Use this template to record findings:

### Database State
```
Query: SELECT year, current_week, is_active FROM seasons WHERE year = 2025;
Result:
Conclusion:
```

### import_real_data.py Review
```
Initial week setting logic:
Code location:
When created:
Conclusion:
```

### weekly_update.py Review
```
Current week update logic:
Code location:
Execution frequency:
Conclusion:
```

### CFBD API Verification
```
Method used:
Result (actual current week):
Data source:
Conclusion:
```

### Root Cause
```
Primary cause:
Contributing factors:
Evidence:
```

### Recommendation for Story 002
```
Approach: [Option A/B/C from above]
Rationale:
Implementation notes:
Testing considerations:
```
