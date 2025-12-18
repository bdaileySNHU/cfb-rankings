# Story: Fix CFBD Client get_current_week Detection Logic - Brownfield Bug Fix

**Story ID**: STORY-FIX-CFBD-WEEK-DETECTION
**Epic**: EPIC-FIX-CI-TESTS (Fix CI Test Failures)
**Type**: Bug Fix
**Created**: 2025-12-18
**Status**: Ready for Development
**Estimated Effort**: 1-2 hours
**Priority**: High
**Complexity**: Low-Medium

---

## User Story

As a **weekly update automation script**,
I want **get_current_week() to correctly identify the current week from game data**,
So that **I can schedule data imports for the right week and exclude placeholder games**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `src/integrations/cfbd_client.py` - CFBD API client with `get_current_week()` function
- `scripts/weekly_update.py` - Weekly automation script that calls get_current_week()
- CollegeFootballData.com API - External data source for game information
- `tests/test_cfbd_client.py` - CFBD client unit tests

**Technology:**
- Python 3.11
- CFBD API (CollegeFootballData.com)
- Game data with completion status and scores
- Week-based scheduling system (weeks 0-15, postseason)

**Follows pattern:**
- Detect current week by finding highest week with completed games
- Exclude placeholder games (0-0 scores indicate future/unplayed games)
- Return week number for scheduling imports
- Handle edge cases: off-season, no games, all future games

**Touch points:**
- `src/integrations/cfbd_client.py` - get_current_week() implementation
- `tests/test_cfbd_client.py` - TestCurrentWeekDetection class (2 tests)
- `scripts/weekly_update.py` - Depends on accurate week detection

---

## Problem Statement

### Current Issue

2 unit tests in `TestCurrentWeekDetection` fail because get_current_week() returns `None` instead of expected week number:

```python
FAILED test_get_current_week_with_completed_games
- assert None == 2  (Expected week 2, got None)

FAILED test_get_current_week_excludes_zero_zero_games
- assert None == 1  (Expected week 1, got None)
```

**Failing Tests:**
1. `test_get_current_week_with_completed_games` - Should return week 2 (latest week with completed games)
2. `test_get_current_week_excludes_zero_zero_games` - Should return week 1 (ignoring week 2 with 0-0 placeholder)

**Error Location:** get_current_week() function in `src/integrations/cfbd_client.py`

**Impact:**
- Weekly automation cannot determine current week
- May import wrong week's data or skip imports
- Placeholder games (0-0 scores) not filtered properly
- Week detection logic broken for scheduling
- 2 of 511 unit tests failing (blocking CI/CD)

### Root Cause

**Likely Issues:**

1. **Completed game detection broken:**
   - Logic not correctly identifying which games are completed vs future
   - May be checking wrong field or using incorrect condition
   - Completed games not being recognized

2. **0-0 score filtering broken:**
   - Placeholder games (0-0 scores) not being excluded
   - Week with only placeholders counted as "current"
   - Filter condition missing or incorrect

3. **Week selection logic broken:**
   - Not returning highest week number with completed games
   - Returning None instead of week number
   - Logic short-circuits before finding valid week

**Expected Logic Pattern:**
```python
def get_current_week(season: int, season_type: str = "regular") -> Optional[int]:
    """
    Detect current week by finding highest week with completed games.
    Exclude 0-0 placeholder games.
    """
    games = fetch_games(season, season_type)

    # Filter to completed games only
    completed_games = [
        g for g in games
        if g.completed  # Must be marked complete
        and not (g.home_points == 0 and g.away_points == 0)  # Exclude 0-0 placeholders
    ]

    if not completed_games:
        return None  # No completed games yet

    # Return highest week number
    return max(g.week for g in completed_games)
```

**Test Scenario 1: Completed Games**
```python
# Test data includes:
# Week 1: Game with score 24-17 (completed=True)
# Week 2: Game with score 31-14 (completed=True)
# Expected: 2 (highest week with completed game)
# Actual: None (not finding completed games)
```

**Test Scenario 2: Exclude 0-0 Games**
```python
# Test data includes:
# Week 1: Game with score 21-10 (completed=True)
# Week 2: Game with score 0-0 (completed=True but placeholder)
# Expected: 1 (week 2 excluded due to 0-0 score)
# Actual: None (filter not working or logic broken)
```

---

## Acceptance Criteria

### Functional Requirements

1. **Correctly identify completed games**
   - Use appropriate field to check game completion (completed=True, or similar)
   - Handle various completion status representations
   - Don't count future/scheduled games as completed

2. **Exclude 0-0 placeholder games**
   - Filter out games where home_points == 0 AND away_points == 0
   - Even if marked as "completed", 0-0 means placeholder
   - Allow games with legitimate 0-0 scores if that's possible (rare in CFB)

3. **Return highest week with valid completed games**
   - Find maximum week number among filtered completed games
   - Return integer week number (0-15 for regular season)
   - Return None only if no valid completed games exist

4. **test_get_current_week_with_completed_games passes**
   - Returns 2 when weeks 1 and 2 both have completed games
   - Correctly identifies highest completed week
   - No assertion errors

5. **test_get_current_week_excludes_zero_zero_games passes**
   - Returns 1 when week 1 has real game, week 2 has 0-0 placeholder
   - Successfully filters 0-0 games from consideration
   - No assertion errors

### Integration Requirements

6. **Handle edge cases gracefully**
   - No games: return None
   - All future games: return None
   - Mixed completed/future: return highest completed week
   - Off-season: return None

7. **Maintain existing function signature**
   - Parameters unchanged (season, season_type)
   - Return type unchanged (Optional[int])
   - No breaking changes to callers (weekly_update.py)

### Quality Requirements

8. **No regression in other tests**
   - 509 currently passing unit tests continue to pass (511 total - 2 failing)
   - Other CFBD client tests unaffected
   - Weekly update tests that depend on get_current_week() still work

9. **Clear logic and comments**
   - Document why 0-0 games are excluded
   - Explain completion detection logic
   - Handle edge cases with clear comments

---

## Technical Notes

### Investigation Approach

**Step 1: Read get_current_week() implementation**
```bash
# Find function in cfbd_client.py
grep -n "def get_current_week" src/integrations/cfbd_client.py

# Read function implementation
```

**Step 2: Examine test expectations**
```bash
# Read failing tests to understand expected behavior
grep -A 20 "def test_get_current_week_with_completed_games" tests/test_cfbd_client.py
grep -A 20 "def test_get_current_week_excludes_zero_zero_games" tests/test_cfbd_client.py
```

**Step 3: Check game data structure**
```bash
# Understand what fields are available on game objects
# Look for: completed, home_points, away_points, week, etc.
grep -A 30 "def get_current_week" src/integrations/cfbd_client.py
```

**Step 4: Identify the broken logic**
- Is completed check correct?
- Is 0-0 filter present?
- Is max(week) calculation correct?
- Does function return None prematurely?

### Implementation Approach

**Likely Current (Broken) Implementation:**
```python
def get_current_week(season: int, season_type: str = "regular") -> Optional[int]:
    """Get current week based on game completion."""
    games = self._fetch_games(season, season_type)

    # ❌ Missing or incorrect completion check
    completed_games = [g for g in games if g.some_wrong_field]

    # ❌ Not filtering 0-0 games
    # ❌ Not returning max week
    return None  # Always returns None
```

**Fixed Implementation:**
```python
def get_current_week(season: int, season_type: str = "regular") -> Optional[int]:
    """
    Get current week based on game completion.

    Returns the highest week number that has completed games,
    excluding placeholder games (0-0 scores).

    Returns None if no completed games exist.
    """
    games = self._fetch_games(season, season_type)

    if not games:
        return None

    # Filter to completed games, excluding 0-0 placeholders
    completed_games = [
        g for g in games
        if g.completed  # ✅ Check actual completion field
        and not (g.home_points == 0 and g.away_points == 0)  # ✅ Exclude 0-0
    ]

    if not completed_games:
        return None  # No valid completed games

    # ✅ Return highest week number
    return max(g.week for g in completed_games)
```

**Key Changes:**
1. Check `g.completed` field (or correct completion indicator)
2. Add 0-0 score filter: `not (home_points == 0 and away_points == 0)`
3. Return `max(g.week for g in completed_games)` instead of None
4. Handle empty game lists gracefully

### Testing the Fix

```bash
# Run single failing test
pytest tests/test_cfbd_client.py::TestCurrentWeekDetection::test_get_current_week_with_completed_games -xvs

# Expected: PASSED (assert 2 == 2)

# Run both current week detection tests
pytest tests/test_cfbd_client.py::TestCurrentWeekDetection -v

# Expected: 2 passed

# Run full unit suite to verify no regressions
pytest --tb=short

# Expected: 511 passed, 0 failed (assuming Story 1 and 3 also complete)
```

### Key Constraints

- **No API changes** - function signature unchanged
- **No breaking changes** - callers (weekly_update.py) unaffected
- **No external API changes** - CFBD API calls unchanged
- **Logic fix only** - correct the detection algorithm
- **Maintain edge case handling** - None return for no games

---

## Definition of Done

- [ ] get_current_week() correctly identifies completed games
- [ ] 0-0 score games excluded from week detection
- [ ] Returns highest week number with valid completed games
- [ ] Returns None when no valid completed games exist
- [ ] test_get_current_week_with_completed_games passes (returns 2)
- [ ] test_get_current_week_excludes_zero_zero_games passes (returns 1)
- [ ] No regression in other tests (509 currently passing continue to pass)
- [ ] Changes committed with clear message: "Fix get_current_week logic to detect completed games and exclude 0-0 placeholders"
- [ ] Function documented with clear comments

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:**
Changing week detection logic might affect weekly_update.py behavior in production, potentially importing wrong weeks.

**Mitigation:**
1. Run all weekly_update tests to verify integration
2. Check if any other code depends on get_current_week()
3. Test edge cases (no games, off-season, future games)
4. Verify fix matches test expectations exactly

```bash
# Find all usages of get_current_week
grep -r "get_current_week" --include="*.py" .

# Run weekly_update tests
pytest tests/test_weekly_update.py -v
```

**Rollback:**
```bash
# Simple revert if issues arise
git revert <commit-hash>

# Or manual rollback
git checkout HEAD~1 -- src/integrations/cfbd_client.py
```

### Compatibility Verification

- [x] No breaking changes to function signature
- [x] No changes to external API calls
- [x] No database changes
- [x] No configuration changes
- [x] Callers (weekly_update.py) continue working
- [x] Return type unchanged (Optional[int])

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one session (1-2 hours)
- [x] Fix approach is straightforward (correct filtering logic)
- [x] Follows existing patterns (list comprehension, max())
- [x] No design or architecture work required

### Clarity Check

- [x] Story requirements are clear (fix completion detection and 0-0 filtering)
- [x] Integration points are specified (get_current_week in cfbd_client.py)
- [x] Success criteria are testable (2 tests pass with correct values)
- [x] Rollback approach is simple (git revert)

---

## Implementation Guidance

### Step-by-Step Workflow

1. **Read the get_current_week() function**
   ```bash
   # Read src/integrations/cfbd_client.py
   # Focus on get_current_week() implementation
   ```

2. **Read the failing tests**
   ```bash
   # Understand test data and expectations
   # Check what game data structure looks like in tests
   ```

3. **Identify the bug**
   - Find how completed games are currently detected (or not)
   - Check if 0-0 filtering exists
   - See why None is returned instead of week number

4. **Apply fix - Correct completion check**
   ```python
   # Ensure using correct field to check completion
   # Might be: g.completed, g.status == "completed", etc.
   ```

5. **Apply fix - Add 0-0 filter**
   ```python
   # Add condition to exclude placeholder games
   and not (g.home_points == 0 and g.away_points == 0)
   ```

6. **Apply fix - Return max week**
   ```python
   # Return highest week number from filtered games
   return max(g.week for g in completed_games)
   ```

7. **Test immediately**
   ```bash
   # Run one test to verify fix works
   pytest tests/test_cfbd_client.py::TestCurrentWeekDetection::test_get_current_week_with_completed_games -xvs

   # Should see: PASSED (assert 2 == 2)
   ```

8. **Run all affected tests**
   ```bash
   # Run both week detection tests
   pytest tests/test_cfbd_client.py::TestCurrentWeekDetection -v

   # Should see: 2 passed
   ```

9. **Verify weekly_update integration**
   ```bash
   # Ensure weekly_update tests still pass
   pytest tests/test_weekly_update.py -v

   # Note: Story 3 addresses exit handling failures in these tests
   ```

10. **Verify no regression**
    ```bash
    # Run full unit suite
    pytest --tb=short

    # Should see: 509 passed (or 511 if all stories complete)
    ```

11. **Commit changes**
    ```bash
    git add src/integrations/cfbd_client.py
    git commit -m "Fix get_current_week logic to detect completed games and exclude 0-0 placeholders

Fixes 2 failing tests in TestCurrentWeekDetection:
- Correct completed game detection using proper field check
- Filter out 0-0 placeholder games from week calculation
- Return max week number instead of None

Tests now passing:
- test_get_current_week_with_completed_games (returns 2)
- test_get_current_week_excludes_zero_zero_games (returns 1)

Part of EPIC-FIX-CI-TESTS Story 2."
    ```

### Commands Reference

```bash
# Investigation
grep -n "def get_current_week" src/integrations/cfbd_client.py
grep -A 30 "def get_current_week" src/integrations/cfbd_client.py

# Testing
pytest tests/test_cfbd_client.py::TestCurrentWeekDetection -v
pytest tests/test_cfbd_client.py::TestCurrentWeekDetection::test_get_current_week_with_completed_games -xvs
pytest tests/test_weekly_update.py -v
pytest --tb=short

# Verification
git diff src/integrations/cfbd_client.py
grep -r "get_current_week" --include="*.py" .
```

---

## Notes

- **Related Work**:
  - Part of EPIC-FIX-CI-TESTS
  - Integrates with Story 3 (weekly_update exit handling)
  - Used by scripts/weekly_update.py for scheduling
- **Common Bug Pattern**: Incorrect field checks, missing filters, premature None returns
- **CI Impact**: Fixes 2 of 9 failing unit tests (22% of failures)
- **Effort**: Low-Medium - requires understanding game data structure
- **Risk**: Low - isolated function, comprehensive tests, easy rollback
- **Priority**: High - blocking CI/CD, affects weekly automation reliability
- **Business Impact**: Incorrect week detection could cause wrong data imports in production

---

## Expected Changes

**File: src/integrations/cfbd_client.py**

**Change: Fix get_current_week() logic**

```python
def get_current_week(season: int, season_type: str = "regular") -> Optional[int]:
    """
    Get current week based on game completion.

    Returns the highest week number that has completed games,
    excluding placeholder games (0-0 scores).

+   Args:
+       season: Season year
+       season_type: "regular" or "postseason"
+
+   Returns:
+       Highest week number with completed games, or None if no completed games
    """
    games = self._fetch_games(season, season_type)

    if not games:
        return None

    # Filter to completed games, excluding 0-0 placeholders
    completed_games = [
        g for g in games
-       if g.some_wrong_field  # ❌ Current (broken)
+       if g.completed  # ✅ Fix: Use correct completion field
+       and not (g.home_points == 0 and g.away_points == 0)  # ✅ Fix: Exclude 0-0
    ]

    if not completed_games:
        return None

-   return None  # ❌ Current (always returns None)
+   return max(g.week for g in completed_games)  # ✅ Fix: Return max week
```

**Total Changes:** ~5-10 lines modified in 1 function (logic corrections + documentation)
