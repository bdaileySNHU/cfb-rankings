# EPIC-016: Fix Additional Test Failures

**Status:** Not Started
**Priority:** High
**Estimated Effort:** 2-3 hours
**Dependencies:** EPIC-015 (Complete)
**Related EPIC:** EPIC-015 (Fix Remaining Test Failures)

## Overview

Apply the same database session fix pattern from EPIC-015 to remaining failing tests in CI/CD. After EPIC-015, we discovered that other tests have the same root cause: functions creating their own database sessions instead of using dependency injection.

## Problem Statement

After EPIC-015 fixed the 5 usage dashboard tests, CI/CD still shows failures in:

**TestTriggerUpdateEndpoint (4 tests):**
1. `test_trigger_update_fails_with_no_week`
2. `test_trigger_update_fails_at_90_percent_usage`
3. `test_trigger_update_succeeds_with_valid_conditions`
4. `test_trigger_update_creates_task_record`

**TestAPIIntegration (1 test):**
5. `test_trigger_and_check_status_workflow`

**TestMainFunction in test_weekly_update.py (3 tests):**
6. `test_off_season_exits_gracefully`
7. `test_no_current_week_exits_with_error`
8. `test_api_usage_exceeded_exits_with_error`

**Error Messages:**
- `sqlite3.OperationalError: no such table: update_tasks`
- `sqlite3.OperationalError: no such table: api_usage`

## Goals

1. **100% CI/CD pass rate** - All tests pass in unit, integration, AND coverage steps
2. **Apply EPIC-015 solution** - Use the same fix pattern for consistency
3. **No regressions** - Maintain backward compatibility
4. **CI/CD green** - GitHub Actions workflow shows green checkmark

## Non-Goals

- Adding new test coverage
- Refactoring test structure
- Modifying production code beyond necessary fixes

## Success Criteria

- [ ] All 8 additional failing tests pass locally
- [ ] All 8 additional failing tests pass in CI/CD
- [ ] Unit tests: PASS
- [ ] Integration tests: PASS
- [ ] Coverage tests: PASS
- [ ] GitHub Actions workflow shows green checkmark
- [ ] No regressions in previously passing tests

---

## Root Cause Analysis

### Known Pattern from EPIC-015
Functions that create their own database sessions (using `SessionLocal()`) bypass the dependency injection overrides in tests. This causes tests to query the production database instead of the test database.

### Affected Functions

Based on error messages and test failures, these functions likely have the same issue:

1. **Functions called by `/api/admin/trigger-update` endpoint:**
   - Possibly `check_api_usage()` in weekly_update.py
   - Possibly other functions in the trigger-update flow

2. **Functions in weekly_update.py:**
   - `check_api_usage()` - likely creates own session to query api_usage table
   - `main()` function - likely creates session for update_tasks table
   - Any other helper functions called during update workflow

### Solution Pattern (from EPIC-015)

```python
def function_name(param1, db: "Session" = None):
    """
    Description.

    Args:
        param1: Description
        db: Optional database session (creates new session if not provided)
    """
    from database import SessionLocal

    # Use provided session or create new one
    db_provided = db is not None
    if not db_provided:
        db = SessionLocal()

    try:
        # ... use db ...
        result = db.query(...).all()
        return result
    finally:
        # Only close session if we created it
        if not db_provided:
            db.close()
```

---

## Stories

### Story 001: Identify All Functions Creating Database Sessions

**Story Points:** 1
**Priority:** High

#### Description

Search the codebase for functions that create their own database sessions and are called by the failing tests.

#### Acceptance Criteria

- [ ] List all functions that call `SessionLocal()`
- [ ] Identify which ones are called by failing tests
- [ ] Document function locations and line numbers
- [ ] Prioritize functions by impact (how many tests they affect)

#### Investigation Steps

1. **Search for SessionLocal usage:**
```bash
grep -rn "SessionLocal()" --include="*.py" .
```

2. **Check weekly_update.py:**
```bash
grep -A 20 "def check_api_usage" scripts/weekly_update.py
grep -A 30 "def main" scripts/weekly_update.py
```

3. **Check main.py trigger-update endpoint:**
```bash
grep -B5 -A 50 "@app.post(\"/api/admin/trigger-update\"" main.py
```

4. **Analyze test failures:**
   - Run failing tests locally with verbose output
   - Trace which functions are called
   - Identify session creation points

---

### Story 002: Apply Database Session Fix Pattern

**Story Points:** 2
**Priority:** High

#### Description

Apply the EPIC-015 fix pattern to all identified functions. Modify function signatures to accept optional `db` parameter and update all callers.

#### Acceptance Criteria

- [ ] All identified functions modified to accept optional `db` parameter
- [ ] All API endpoints updated to pass `db` session
- [ ] All functions maintain backward compatibility
- [ ] All tests pass locally
- [ ] Code follows the established pattern from EPIC-015

#### Implementation Tasks

For each function:
1. Add optional `db` parameter to signature
2. Add `db_provided = db is not None` check
3. Create `SessionLocal()` only if `db` not provided
4. Update `finally` block to close only if we created session
5. Update all callers to pass `db` where available
6. Test locally

---

### Story 003: Verify CI/CD Success

**Story Points:** 1
**Priority:** High

#### Description

Ensure all fixes work in CI/CD environment and all tests pass.

#### Acceptance Criteria

- [ ] Push fixes to GitHub
- [ ] Unit tests: PASS in CI
- [ ] Integration tests: PASS in CI
- [ ] Coverage tests: PASS in CI
- [ ] GitHub Actions workflow shows green checkmark
- [ ] No regressions in other tests
- [ ] Update documentation

#### Verification Steps

1. **Commit and push:**
```bash
git add <modified files>
git commit -m "Apply database session fix pattern to remaining tests (EPIC-016)"
git push origin main
```

2. **Monitor CI/CD:**
```bash
gh run watch --exit-status
```

3. **Verify results:**
   - Check all test steps pass
   - Review test counts
   - Confirm no new failures

4. **Update documentation:**
   - Mark EPIC-016 as complete
   - Update NEW_PROJECT_DOCUMENTATION.md
   - Note final test counts

---

## Expected Outcomes

### Before EPIC-016
- Total tests: 538
- Passing: 530 (98.5%)
- Failing: 8
- CI/CD: ❌ Failing

### After EPIC-016
- Total tests: 538
- Passing: 538 (100%)
- Failing: 0
- CI/CD: ✅ Passing

---

## Implementation Plan

### Phase 1: Investigation (30 minutes)
1. Search codebase for `SessionLocal()` usage
2. Identify all affected functions
3. Map functions to failing tests
4. Document findings

### Phase 2: Apply Fixes (1-1.5 hours)
1. Fix `check_api_usage()` in weekly_update.py
2. Fix any other functions in weekly_update.py
3. Fix trigger-update endpoint dependencies
4. Update all callers
5. Test locally

### Phase 3: CI/CD Verification (30 minutes)
1. Commit and push changes
2. Monitor GitHub Actions
3. Verify all tests pass
4. Confirm no regressions

### Phase 4: Documentation (30 minutes)
1. Mark EPIC-016 as complete
2. Update project documentation
3. Create completion summary

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| More functions affected than expected | Medium | Medium | Systematic search and test all failures |
| Backward compatibility breaks | High | Low | Maintain optional parameter pattern |
| New test failures introduced | Medium | Low | Run full test suite locally first |
| CI environment differences | Low | Very Low | Pattern proven in EPIC-015 |

---

## Related Documentation

- **EPIC-015:** `docs/EPIC-015-FIX-REMAINING-TEST-FAILURES.md` (Solution pattern)
- **Test Patterns:** `docs/TESTING.md`
- **CI/CD Pipeline:** `.github/workflows/tests.yml`

---

## Notes

- This EPIC applies the proven solution pattern from EPIC-015
- The fix is well-understood and low-risk
- Estimated effort is lower than EPIC-015 because pattern is established
- Primary challenge is finding all affected functions

---

**Created:** 2025-10-27
**Last Updated:** 2025-10-27
**Owner:** Development Team
**Status:** Ready to Start
