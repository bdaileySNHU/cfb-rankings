# Story: Fix Weekly Update Multiple Exit Calls - Brownfield Bug Fix

**Story ID**: STORY-FIX-WEEKLY-UPDATE-EXITS
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
I want **to call sys.exit() only once per error scenario**,
So that **tests can verify proper error handling and exit codes without redundant exit calls**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `scripts/weekly_update.py` - Main orchestration script for weekly data imports
- `src/integrations/cfbd_client.py` - CFBD client (get_current_week, API usage checking)
- `tests/test_weekly_update.py` - Unit tests for main() function
- pytest mocking framework - Tests mock sys.exit to verify behavior

**Technology:**
- Python 3.11
- sys.exit() for script termination with exit codes
- pytest with unittest.mock for sys.exit mocking
- Error handling patterns for CLI scripts

**Follows pattern:**
- CLI scripts call sys.exit(0) for graceful completion
- CLI scripts call sys.exit(1) for errors
- Single exit point per error scenario
- Clear error messages before exit
- Tests verify exit called exactly once with correct code

**Touch points:**
- `scripts/weekly_update.py` - main() function and error handling
- `tests/test_weekly_update.py` - TestMainFunction class (3 failing tests)
- Error propagation from helper functions to main()

---

## Problem Statement

### Current Issue

3 unit tests in `TestMainFunction` fail because sys.exit() is called multiple times instead of once:

```python
FAILED test_off_season_exits_gracefully
- AssertionError: Expected 'exit' to be called once. Called 3 times.

FAILED test_no_current_week_exits_with_error
- AssertionError: Expected 'exit' to be called once. Called 2 times.

FAILED test_api_usage_exceeded_exits_with_error
- AssertionError: Expected 'exit' to be called once. Called 2 times.
```

**Failing Tests:**
1. `test_off_season_exits_gracefully` - Should call sys.exit(0) once, calls 3 times
2. `test_no_current_week_exits_with_error` - Should call sys.exit(1) once, calls 2 times
3. `test_api_usage_exceeded_exits_with_error` - Should call sys.exit(1) once, calls 2 times

**Error Location:** main() function and helper functions in `scripts/weekly_update.py`

**Impact:**
- Exit handling tests cannot verify proper error codes
- Redundant exit calls indicate poor error propagation design
- Production script may have confusing error output
- 3 of 511 unit tests failing (blocking CI/CD)
- Masks actual error handling logic issues

### Root Cause

**Likely Cause:**
Helper functions call sys.exit() when detecting errors, then calling code also calls sys.exit(), resulting in multiple exit attempts.

**Common Pattern - Multiple Exit Calls:**
```python
def check_current_week(season):
    """Helper function that exits on error."""
    week = get_current_week(season)
    if week is None:
        print("ERROR: Could not detect current week")
        sys.exit(1)  # ❌ Helper calls exit
    return week

def main():
    """Main function."""
    season = 2024

    # Check if off-season
    if is_off_season(season):
        print("Off-season, exiting")
        sys.exit(0)  # ❌ Main calls exit
        return  # Never reached

    # Check current week
    week = check_current_week(season)  # ❌ Helper also calls exit
    if week is None:  # This check is redundant now
        print("No current week")
        sys.exit(1)  # ❌ THIRD exit call (never reached in real execution)
```

**Result:** When tests mock sys.exit, they see multiple calls:
- Off-season: 3 calls (helper + main + redundant check)
- No current week: 2 calls (helper + main)
- API exceeded: 2 calls (helper + main)

**Expected Pattern - Single Exit Point:**
```python
def check_current_week(season):
    """Helper function that returns status, doesn't exit."""
    week = get_current_week(season)
    return week  # ✅ Return value, let caller decide to exit

def main():
    """Main function with single exit point per scenario."""
    season = 2024

    # Check if off-season
    if is_off_season(season):
        print("Off-season, exiting gracefully")
        sys.exit(0)  # ✅ ONLY exit call for this scenario
        return

    # Check current week
    week = check_current_week(season)
    if week is None:
        print("ERROR: Could not detect current week")
        sys.exit(1)  # ✅ ONLY exit call for this scenario
        return

    # Check API usage
    usage = check_api_usage()
    if usage.exceeded:
        print("ERROR: API usage limit exceeded")
        sys.exit(1)  # ✅ ONLY exit call for this scenario
        return

    # Continue with normal processing...
```

---

## Acceptance Criteria

### Functional Requirements

1. **Off-season scenario exits exactly once**
   - test_off_season_exits_gracefully passes
   - sys.exit(0) called exactly 1 time (not 3)
   - Graceful exit with appropriate message

2. **No current week scenario exits exactly once**
   - test_no_current_week_exits_with_error passes
   - sys.exit(1) called exactly 1 time (not 2)
   - Error exit with clear message

3. **API usage exceeded scenario exits exactly once**
   - test_api_usage_exceeded_exits_with_error passes
   - sys.exit(1) called exactly 1 time (not 2)
   - Error exit with clear message

4. **Helper functions don't call sys.exit()**
   - Helper functions return status/values
   - Only main() calls sys.exit()
   - Clear separation of concerns

5. **Error messages remain clear**
   - Each exit scenario has descriptive message
   - Error output helps operators understand issue
   - No degradation in error message quality

### Integration Requirements

6. **Exit codes remain appropriate**
   - 0 for graceful/expected exit (off-season)
   - 1 for error conditions (no week, API exceeded)
   - Consistent with CLI conventions

7. **Maintain existing error detection logic**
   - Off-season detection unchanged
   - Current week detection unchanged (uses Story 2 fix)
   - API usage checking unchanged
   - Only exit call placement modified

### Quality Requirements

8. **No regression in other tests**
   - 508 currently passing unit tests continue to pass (511 total - 3 failing)
   - Other weekly_update tests unaffected
   - Full unit suite: 511 passing, 0 failing

9. **Clean error propagation pattern**
   - Helper functions return values/status
   - main() makes exit decisions
   - No nested exit calls
   - Clear control flow

---

## Technical Notes

### Investigation Approach

**Step 1: Read main() function**
```bash
# Find main function in weekly_update.py
grep -n "def main" scripts/weekly_update.py

# Read main() implementation
```

**Step 2: Find all sys.exit() calls**
```bash
# Locate all exit calls in the file
grep -n "sys.exit" scripts/weekly_update.py

# Expected: Multiple calls (some in helpers, some in main)
```

**Step 3: Read failing tests**
```bash
# Understand test expectations
grep -A 20 "def test_off_season_exits_gracefully" tests/test_weekly_update.py
grep -A 20 "def test_no_current_week_exits_with_error" tests/test_weekly_update.py
grep -A 20 "def test_api_usage_exceeded_exits_with_error" tests/test_weekly_update.py
```

**Step 4: Identify redundant exit calls**
- Which helper functions call sys.exit()?
- Where does main() call sys.exit()?
- Which calls are redundant/unreachable?

### Implementation Approach

**Pattern 1: Remove sys.exit() from Helper Functions**

```python
# BEFORE (helper calls exit)
def check_current_week(season):
    week = get_current_week(season)
    if week is None:
        print("ERROR: No current week")
        sys.exit(1)  # ❌ Remove this
    return week

# AFTER (helper returns value)
def check_current_week(season):
    """Get current week, returning None if unavailable."""
    week = get_current_week(season)
    return week  # ✅ Just return, let caller handle None
```

**Pattern 2: Consolidate Exit Calls in main()**

```python
# BEFORE (multiple potential exit calls)
def main():
    if is_off_season():
        sys.exit(0)  # Call 1

    week = check_current_week()  # check_current_week also calls exit (Call 2)
    if week is None:
        sys.exit(1)  # Call 3 (never reached if helper exits)

# AFTER (single exit per scenario)
def main():
    if is_off_season():
        print("Off-season detected, exiting gracefully")
        sys.exit(0)  # ✅ Only exit for off-season scenario
        return

    week = check_current_week()  # Now just returns None
    if week is None:
        print("ERROR: Could not detect current week")
        sys.exit(1)  # ✅ Only exit for no-week scenario
        return

    usage = check_api_usage()  # Returns usage info
    if usage and usage.exceeded:
        print(f"ERROR: API usage exceeded ({usage.used}/{usage.limit})")
        sys.exit(1)  # ✅ Only exit for API exceeded scenario
        return

    # Continue with normal processing...
```

**Pattern 3: Early Return After Exit**

```python
# Good practice: return after sys.exit() for clarity
if error_condition:
    print("ERROR: Something went wrong")
    sys.exit(1)
    return  # Makes intent clear, even though exit prevents execution
```

### Testing the Fix

```bash
# Run single failing test
pytest tests/test_weekly_update.py::TestMainFunction::test_off_season_exits_gracefully -xvs

# Expected: PASSED (exit called once with code 0)

# Run all 3 exit handling tests
pytest tests/test_weekly_update.py::TestMainFunction -k "exit" -v

# Expected: 3 passed

# Run full weekly_update test suite
pytest tests/test_weekly_update.py -v

# Expected: All tests pass

# Run full unit suite to verify no regressions
pytest --tb=short

# Expected: 511 passed, 0 failed (assuming Stories 1 and 2 complete)
```

### Key Constraints

- **No logic changes** - only exit call placement modified
- **No error detection changes** - same conditions trigger errors
- **Exit codes unchanged** - 0 for graceful, 1 for errors
- **Error messages maintained** - keep clear operator messages
- **Single responsibility** - helpers return values, main() handles exits

---

## Definition of Done

- [ ] Helper functions don't call sys.exit() (return values/status instead)
- [ ] main() function has single exit point per error scenario
- [ ] test_off_season_exits_gracefully passes (exit called once with code 0)
- [ ] test_no_current_week_exits_with_error passes (exit called once with code 1)
- [ ] test_api_usage_exceeded_exits_with_error passes (exit called once with code 1)
- [ ] Error messages remain clear and informative
- [ ] Exit codes remain appropriate (0 vs 1)
- [ ] No regression in other tests (508 currently passing continue to pass)
- [ ] Changes committed with clear message: "Consolidate weekly_update exit handling to single exit per scenario"
- [ ] Full unit suite: 511 passed, 0 failed

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:**
Changing exit handling might mask real errors or alter production script behavior in unexpected ways.

**Mitigation:**
1. Preserve exact error detection logic (only move exit calls)
2. Keep same error messages (don't change operator experience)
3. Maintain same exit codes (0 vs 1)
4. Run all weekly_update tests to verify behavior
5. Manually test script execution in development environment

```bash
# Manual testing (optional but recommended)
python scripts/weekly_update.py --dry-run

# Should see proper error messages and single exit per scenario
```

**Rollback:**
```bash
# Simple revert if issues arise
git revert <commit-hash>

# Or manual rollback
git checkout HEAD~1 -- scripts/weekly_update.py
```

### Compatibility Verification

- [x] No changes to error detection logic
- [x] No changes to exit codes (0 for graceful, 1 for error)
- [x] No changes to error messages
- [x] No changes to script command-line interface
- [x] No database changes
- [x] No configuration changes
- [x] Production behavior unchanged (only exit call organization)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one session (1-2 hours)
- [x] Fix approach is straightforward (move exit calls to main())
- [x] Follows existing patterns (single exit point per scenario)
- [x] No design or architecture work required

### Clarity Check

- [x] Story requirements are clear (consolidate exit calls)
- [x] Integration points are specified (main() and helpers in weekly_update.py)
- [x] Success criteria are testable (3 tests pass, exit called once per scenario)
- [x] Rollback approach is simple (git revert)

---

## Implementation Guidance

### Step-by-Step Workflow

1. **Read the weekly_update.py script**
   ```bash
   # Read scripts/weekly_update.py
   # Focus on main() and helper functions
   ```

2. **Map all sys.exit() calls**
   ```bash
   # Find every exit call
   grep -n "sys.exit" scripts/weekly_update.py

   # Identify which are in helpers vs main()
   ```

3. **Read the failing tests**
   ```bash
   # Understand test mocking and expectations
   # See how they mock sys.exit and count calls
   ```

4. **Identify redundant exit calls**
   - Off-season: Why 3 calls? Where are they?
   - No current week: Why 2 calls? Where are they?
   - API exceeded: Why 2 calls? Where are they?

5. **Remove exit calls from helpers**
   - Helper functions should return values/status
   - Remove sys.exit() calls from helper functions
   - Keep helper logic otherwise unchanged

6. **Ensure main() has single exit per scenario**
   - Check return value from helpers
   - Call sys.exit() once if condition met
   - Add return statement after exit for clarity

7. **Test immediately**
   ```bash
   # Run one test to verify fix works
   pytest tests/test_weekly_update.py::TestMainFunction::test_off_season_exits_gracefully -xvs

   # Should see: PASSED (exit called 1 time with code 0)
   ```

8. **Run all exit handling tests**
   ```bash
   # Run all 3 exit tests
   pytest tests/test_weekly_update.py::TestMainFunction -k "exit" -v

   # Should see: 3 passed
   ```

9. **Run full weekly_update suite**
   ```bash
   # Ensure no regressions in other weekly_update tests
   pytest tests/test_weekly_update.py -v

   # Should see: All tests pass
   ```

10. **Verify no regression**
    ```bash
    # Run full unit suite
    pytest --tb=short

    # Should see: 511 passed, 0 failed (with Stories 1 and 2)
    ```

11. **Manual testing (optional)**
    ```bash
    # Test actual script execution
    python scripts/weekly_update.py --dry-run

    # Verify error messages clear and single exit per error
    ```

12. **Commit changes**
    ```bash
    git add scripts/weekly_update.py
    git commit -m "Consolidate weekly_update exit handling to single exit per scenario

Fixes 3 failing tests in TestMainFunction by removing redundant sys.exit() calls:
- Move exit calls from helper functions to main()
- Single exit point per error scenario (off-season, no week, API exceeded)
- Helper functions now return values/status instead of calling exit

Tests now passing:
- test_off_season_exits_gracefully (1 exit call with code 0)
- test_no_current_week_exits_with_error (1 exit call with code 1)
- test_api_usage_exceeded_exits_with_error (1 exit call with code 1)

Error messages and exit codes unchanged.

Part of EPIC-FIX-CI-TESTS Story 3."
    ```

### Commands Reference

```bash
# Investigation
grep -n "def main" scripts/weekly_update.py
grep -n "sys.exit" scripts/weekly_update.py
grep -A 30 "def main" scripts/weekly_update.py

# Testing
pytest tests/test_weekly_update.py::TestMainFunction -k "exit" -v
pytest tests/test_weekly_update.py::TestMainFunction::test_off_season_exits_gracefully -xvs
pytest tests/test_weekly_update.py -v
pytest --tb=short

# Manual testing
python scripts/weekly_update.py --dry-run

# Verification
git diff scripts/weekly_update.py
```

---

## Notes

- **Related Work**:
  - Part of EPIC-FIX-CI-TESTS
  - Depends on Story 2 (get_current_week fix) for proper week detection
  - Complements Story 1 (admin endpoint imports)
- **Common CLI Pattern**: Single exit point per error scenario, helpers return status
- **CI Impact**: Fixes 3 of 9 failing unit tests (33% of failures)
- **Effort**: Low-Medium - requires understanding control flow and error propagation
- **Risk**: Low - preserves behavior, only reorganizes exit calls
- **Priority**: High - blocking CI/CD, affects script reliability testing
- **Testing**: Tests use mock to count sys.exit calls, very precise verification

---

## Expected Changes

**File: scripts/weekly_update.py**

**Change 1: Remove exit from helper functions**

```python
# Example helper (exact code may vary)
def check_season_status(season):
    """Check if season is active."""
-   if is_off_season(season):
-       print("Off-season, exiting")
-       sys.exit(0)  # ❌ Remove exit from helper
    return is_off_season(season)  # ✅ Return status

def get_week_for_import(season):
    """Get current week for import."""
    week = get_current_week(season)
-   if week is None:
-       print("ERROR: No current week")
-       sys.exit(1)  # ❌ Remove exit from helper
    return week  # ✅ Return value (may be None)

def validate_api_usage():
    """Check API usage limits."""
    usage = get_api_usage()
-   if usage.exceeded:
-       print("ERROR: API limit exceeded")
-       sys.exit(1)  # ❌ Remove exit from helper
    return usage  # ✅ Return usage info
```

**Change 2: Consolidate exits in main()**

```python
def main():
    """Main entry point for weekly update script."""
    season = get_current_season()

    # Check if off-season
-   check_season_status(season)  # Old: helper calls exit
+   if is_off_season(season):  # ✅ Check in main
+       print("Off-season detected, exiting gracefully")
+       sys.exit(0)  # ✅ Single exit for this scenario
+       return

    # Get current week
-   week = get_week_for_import(season)  # Old: helper calls exit
+   week = get_current_week(season)  # ✅ Get value
+   if week is None:  # ✅ Check in main
+       print("ERROR: Could not detect current week")
+       sys.exit(1)  # ✅ Single exit for this scenario
+       return

    # Check API usage
-   validate_api_usage()  # Old: helper calls exit
+   usage = get_api_usage()  # ✅ Get usage info
+   if usage and usage.exceeded:  # ✅ Check in main
+       print(f"ERROR: API usage limit exceeded ({usage.used}/{usage.limit})")
+       sys.exit(1)  # ✅ Single exit for this scenario
+       return

    # Continue with normal import process...
    print(f"Importing week {week} for season {season}")
    # ... rest of logic
```

**Total Changes:** 10-20 lines modified across multiple functions (exit call reorganization)

**Key Principle:** Helper functions return information, main() makes decisions about exiting.
