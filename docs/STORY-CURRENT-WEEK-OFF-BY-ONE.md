# Fix Current Week Display Off-by-One Bug - Brownfield Addition

## User Story

As a **user viewing the rankings page**,
I want **the current week to display accurately (week 9, not week 10)**,
So that **I can see the correct week number for the current point in the season**.

## Story Context

**Existing System Integration:**
- Integrates with: `CFBDClient.get_current_week()` method in `cfbd_client.py`
- Technology: Python, CFBD API
- Follows pattern: Week detection based on completed games
- Touch points:
  - `cfbd_client.py:245-285` - `get_current_week()` method
  - `scripts/weekly_update.py:106-136` - `get_current_week_wrapper()`
  - `main.py:358` - Stats endpoint using `active_season.current_week`
  - `frontend/js/app.js:32` - Frontend display

**Root Cause Analysis:**

After implementing EPIC-008 (Future Game Imports), we now store future games with 0-0 placeholder scores. The `get_current_week()` method checks:

```python
if home_points is not None and away_points is not None:
```

This condition is **True** for 0-0 future games, causing them to be incorrectly counted as "completed games". When finding the max week with completed games, it returns week 10 (which has future 0-0 games) instead of week 9 (the actual current week).

**Location:** `cfbd_client.py:273-279`

## Acceptance Criteria

**Functional Requirements:**
1. `get_current_week()` must exclude games with 0-0 scores when finding the highest completed week
2. Current week display on frontend must show week 9 (actual current week) instead of week 10
3. Method must still return the correct week number for actual completed games

**Integration Requirements:**
4. Existing `get_current_week_wrapper()` in `weekly_update.py` continues to work unchanged
5. Stats API endpoint behavior remains the same (returns correct current week)
6. Integration with admin override functionality maintains current behavior

**Quality Requirements:**
7. Change is covered by unit tests (test 0-0 game exclusion)
8. Existing tests for `get_current_week()` continue to pass
9. No regression in week detection for completed games

## Technical Notes

**Integration Approach:**
Modify the condition in `cfbd_client.py:276` to check for non-zero scores:

```python
# OLD (line 276):
if home_points is not None and away_points is not None:

# NEW:
if (home_points is not None and away_points is not None and
    not (home_points == 0 and away_points == 0)):
```

**Existing Pattern Reference:**
- Similar 0-0 check exists in `ranking_service.py:160-164` for validation
- Follows pattern established in EPIC-008 for future game detection

**Key Constraints:**
- Must maintain backward compatibility with existing week detection logic
- Must not affect database current_week values that are already correct
- Must work with both CFBD API responses (None for future) and DB storage (0 for future)

## Definition of Done

- [ ] `cfbd_client.py:get_current_week()` updated to exclude 0-0 games
- [ ] Unit test added for 0-0 game exclusion scenario
- [ ] Existing unit tests pass
- [ ] Frontend verified to show correct week (9 instead of 10)
- [ ] Documentation updated (inline comments added)

## Risk and Compatibility Check

**Primary Risk:**
Breaking existing week detection if the fix is too broad (e.g., excluding legitimate 0-0 ties)

**Mitigation:**
- College football games cannot end 0-0 (overtime rules prevent ties)
- 0-0 is exclusively used as placeholder for future games (EPIC-008 design)
- Change is isolated to single method in `cfbd_client.py`

**Rollback:**
Simple git revert of single-line change in `cfbd_client.py`

**Compatibility Verification:**
- [x] No breaking changes to existing APIs
- [x] Database changes: None (read-only fix)
- [x] UI changes: None (displays corrected data)
- [x] Performance impact: Negligible (adds one boolean check per game)

## Validation Checklist

**Scope Validation:**
- [x] Story can be completed in one development session (~30 minutes)
- [x] Integration approach is straightforward (single-line change)
- [x] Follows existing patterns (0-0 detection from EPIC-008)
- [x] No design or architecture work required

**Clarity Check:**
- [x] Story requirements are unambiguous
- [x] Integration points are clearly specified (`cfbd_client.py:276`)
- [x] Success criteria are testable (week 9 vs week 10 display)
- [x] Rollback approach is simple (git revert)

## Related Work

**Introduced By:**
- EPIC-008: Future Game Imports (Story 001)
  - Added 0-0 placeholder scores for future games
  - Did not account for impact on current week detection

**Related Documentation:**
- `docs/EPIC-008-STORY-001.md` - Future game import implementation
- `docs/EPIC-006-CURRENT-WEEK-ACCURACY.md` - Current week display system

---

## Deployment Record

**Deployed:** 2025-01-23

**Changes Deployed:**
1. `cfbd_client.py:278-279` - Modified to exclude 0-0 games from current week detection
2. `tests/unit/test_cfbd_client.py` - Added 2 new tests for 0-0 game exclusion
3. Database update: Set current_week from 10 → 9 for 2024 season

**Deployment Steps:**
```bash
cd /var/www/cfb-rankings
git pull
sudo systemctl restart cfb-rankings
curl -X POST "http://localhost:8000/api/admin/update-current-week?year=2024&week=9"
```

**Verification:**
- ✅ Frontend displays "Current Week: 9" (was showing 10)
- ✅ All unit tests pass (9/9)
- ✅ No regressions in week detection logic

**Impact:**
- Fixed immediate bug: Current week now displays correctly
- Future-proofed: Automatic week detection will now exclude 0-0 future games
- No breaking changes to existing functionality
