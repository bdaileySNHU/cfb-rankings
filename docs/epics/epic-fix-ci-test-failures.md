# Epic: Fix CI Test Failures - Brownfield Enhancement

**Epic ID**: EPIC-FIX-CI-TESTS
**Type**: Brownfield - Bug Fix
**Status**: Draft
**Created**: 2025-12-18
**Target Completion**: 1-2 development sessions (3-5 hours)
**Priority**: High
**Complexity**: Low-Medium

---

## Epic Goal

Fix 9 failing unit tests in CI/CD pipeline to achieve 100% test pass rate and ensure deployment readiness. These failures were revealed after integrating recent fixes and represent edge cases in admin endpoints, CFBD client week detection, and weekly update exit handling.

---

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Admin trigger_update endpoint handles manual data imports with pre-flight checks
- CFBD client detects current week from game data for scheduling
- Weekly update script orchestrates data imports with proper error handling and exit codes

**Technology stack:**
- Python 3.11
- FastAPI web framework
- pytest unit testing framework
- CFBD API integration (CollegeFootballData.com)

**Integration points:**
- Admin API endpoint `/api/admin/trigger-update`
- CFBD client `get_current_week()` function
- Weekly update main orchestration script
- Database models (UpdateTask)

### Enhancement Details

**What's being added/changed:**
Fixing 9 unit test failures identified in CI/CD pipeline:

**Group 1: Admin Endpoints (4 failures) - trigger_update functionality**
- `test_trigger_update_fails_with_no_week` - Returns 500 instead of expected 400
- `test_trigger_update_succeeds_with_valid_conditions` - UnboundLocalError: UpdateTask variable not accessible
- `test_trigger_update_creates_task_record` - UnboundLocalError: UpdateTask variable not accessible
- `test_trigger_and_check_status_workflow` - UnboundLocalError: UpdateTask variable not accessible

**Root Cause (Group 1):** Import statement for UpdateTask likely inside conditional block or try/except, making it inaccessible in certain code paths.

**Group 2: CFBD Client (2 failures) - get_current_week detection**
- `test_get_current_week_with_completed_games` - Returns None instead of 2
- `test_get_current_week_excludes_zero_zero_games` - Returns None instead of 1

**Root Cause (Group 2):** Logic for detecting current week from game data not correctly identifying completed vs future games, or filtering logic broken.

**Group 3: Weekly Update (3 failures) - exit handling**
- `test_off_season_exits_gracefully` - sys.exit called 3 times instead of 1
- `test_no_current_week_exits_with_error` - sys.exit called 2 times instead of 1
- `test_api_usage_exceeded_exits_with_error` - sys.exit called 2 times instead of 1

**Root Cause (Group 3):** Multiple sys.exit calls in error handling paths, likely due to nested function calls or error propagation issues.

**How it integrates:**
- Fixes maintain existing API contracts and behavior
- No database schema changes required
- No UI changes needed
- Only internal logic corrections

**Success criteria:**
- All 9 tests pass in local and CI environments
- No regressions in 502 currently passing tests
- Test suite achieves 511/511 passing (100% pass rate)
- CI/CD pipeline fully green

---

## Stories

### Story 1: Fix Admin Endpoint UpdateTask Import Error

**Description:** Fix UnboundLocalError in trigger_update endpoint by ensuring UpdateTask is imported at module level, not inside conditional blocks.

**Scope:**
- Fix import statement placement in `src/api/main.py` trigger_update endpoint
- Ensure UpdateTask is accessible in all code paths
- Fix error handling to return 400 instead of 500 for missing week
- Verify all 4 trigger_update tests pass

**Acceptance Criteria:**
- UpdateTask import at module/function top level
- test_trigger_update_fails_with_no_week returns 400 status
- test_trigger_update_succeeds_with_valid_conditions passes
- test_trigger_update_creates_task_record passes
- test_trigger_and_check_status_workflow passes

---

### Story 2: Fix CFBD Client get_current_week Detection Logic

**Description:** Fix get_current_week() logic to correctly identify current week from completed game data and properly exclude placeholder games (0-0 scores).

**Scope:**
- Review and fix week detection logic in `src/integrations/cfbd_client.py`
- Ensure completed games are identified correctly
- Ensure 0-0 score games are filtered out
- Verify both current week detection tests pass

**Acceptance Criteria:**
- test_get_current_week_with_completed_games returns correct week number
- test_get_current_week_excludes_zero_zero_games returns correct week number
- Logic handles edge cases (no games, all future games, mixed completed/future)

---

### Story 3: Fix Weekly Update Multiple Exit Calls

**Description:** Fix weekly_update.py to call sys.exit() only once per error scenario by consolidating exit logic and removing redundant exit calls in error propagation paths.

**Scope:**
- Review exit call locations in `scripts/weekly_update.py`
- Consolidate error handling to single exit point
- Ensure error messages are clear and exit codes are correct
- Verify all 3 exit handling tests pass

**Acceptance Criteria:**
- test_off_season_exits_gracefully: sys.exit called exactly once
- test_no_current_week_exits_with_error: sys.exit called exactly once
- test_api_usage_exceeded_exits_with_error: sys.exit called exactly once
- Error messages remain clear and informative
- Exit codes remain appropriate (0 for graceful, 1 for error)

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (fixing internal logic only)
- [x] Database schema changes are backward compatible (no schema changes)
- [x] UI changes follow existing patterns (no UI changes)
- [x] Performance impact is minimal (logic fixes only)
- [x] No breaking changes to contracts or interfaces
- [x] Error messages remain clear for operators

---

## Risk Mitigation

**Primary Risk:**
Fixing error handling might mask real errors or change expected behavior in production.

**Mitigation:**
1. Test fixes locally before CI
2. Run full test suite to verify no regressions (502 passing tests remain passing)
3. Review error messages to ensure clarity maintained
4. Verify exit codes match expected values
5. Test actual weekly_update script execution in development environment

**Rollback Plan:**
```bash
# Simple revert if issues arise
git revert <commit-hash>

# Or rollback specific files
git checkout HEAD~1 -- src/api/main.py
git checkout HEAD~1 -- src/integrations/cfbd_client.py
git checkout HEAD~1 -- scripts/weekly_update.py
```

---

## Definition of Done

- [x] All 9 failing tests pass in local environment
- [x] All 9 failing tests pass in CI/CD environment
- [x] No regression in 502 currently passing tests
- [x] Full test suite: 511 passed, 0 failed (100% pass rate)
- [x] CI/CD pipeline fully green
- [x] Error handling maintains clarity and appropriate exit codes
- [x] Code changes reviewed for maintainability
- [x] Documentation updated if error handling changed significantly
- [x] Changes committed with clear messages per story
- [x] Epic documented in GitHub issues (optional)

---

## Validation Checklist

### Scope Validation

- [x] Epic can be completed in 3 stories maximum
- [x] No architectural documentation required (bug fixes only)
- [x] Enhancement follows existing patterns (fixing logic, not adding features)
- [x] Integration complexity is manageable (isolated fixes)

### Risk Assessment

- [x] Risk to existing system is low (unit test fixes)
- [x] Rollback plan is feasible (git revert)
- [x] Testing approach covers existing functionality (502 passing tests)
- [x] Team has sufficient knowledge of integration points

### Completeness Check

- [x] Epic goal is clear and achievable (fix 9 tests → 100% pass rate)
- [x] Stories are properly scoped (3 logical groupings)
- [x] Success criteria are measurable (test pass/fail counts)
- [x] Dependencies are identified (none - stories can be done in parallel)

---

## Technical Notes

### Current Test Results (CI)

```
========== 9 failed, 502 passed, 46 deselected, 58 warnings in 15.41s ==========

FAILED tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_fails_with_no_week
- assert 500 == 400

FAILED tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_succeeds_with_valid_conditions
- UnboundLocalError: cannot access local variable 'UpdateTask' where it is not associated with a value

FAILED tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_creates_task_record
- UnboundLocalError: cannot access local variable 'UpdateTask' where it is not associated with a value

FAILED tests/test_admin_endpoints.py::TestAPIIntegration::test_trigger_and_check_status_workflow
- UnboundLocalError: cannot access local variable 'UpdateTask' where it is not associated with a value

FAILED tests/test_cfbd_client.py::TestCurrentWeekDetection::test_get_current_week_with_completed_games
- assert None == 2

FAILED tests/test_cfbd_client.py::TestCurrentWeekDetection::test_get_current_week_excludes_zero_zero_games
- assert None == 1

FAILED tests/test_weekly_update.py::TestMainFunction::test_off_season_exits_gracefully
- AssertionError: Expected 'exit' to be called once. Called 3 times.

FAILED tests/test_weekly_update.py::TestMainFunction::test_no_current_week_exits_with_error
- AssertionError: Expected 'exit' to be called once. Called 2 times.

FAILED tests/test_weekly_update.py::TestMainFunction::test_api_usage_exceeded_exits_with_error
- AssertionError: Expected 'exit' to be called once. Called 2 times.
```

### Investigation Commands

```bash
# Run failing tests locally
pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint -v
pytest tests/test_cfbd_client.py::TestCurrentWeekDetection -v
pytest tests/test_weekly_update.py::TestMainFunction -v

# Run full test suite to verify no regressions
pytest --tb=short

# Check specific error details
pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_fails_with_no_week -xvs
```

### Files Likely to Modify

- `src/api/main.py` - trigger_update endpoint (Story 1)
- `src/integrations/cfbd_client.py` - get_current_week() function (Story 2)
- `scripts/weekly_update.py` - main() and error handling (Story 3)

---

## Dependencies

**No blocking dependencies:**
- All 3 stories are independent and can be worked in parallel
- No external API changes required
- No database migrations needed
- No infrastructure changes required

**Builds on:**
- EPIC-FIX-INT-TESTS (previously completed - 117/117 integration tests passing)
- EPIC-FIX-REMAINING-TESTS (previously completed - 100% integration test pass rate)

**Enables:**
- Fully green CI/CD pipeline (100% unit + integration test coverage)
- Confident deployment to production
- Foundation for additional feature development

---

## Success Metrics

### Before Epic
- **Unit Tests:** 502 passing, 9 failing (98.2% pass rate)
- **Integration Tests:** 117 passing, 0 failing (100% pass rate)
- **Overall:** 619 passing, 9 failing (98.6% pass rate)
- **CI Status:** Red (failing)

### After Epic (Target)
- **Unit Tests:** 511 passing, 0 failing (100% pass rate)
- **Integration Tests:** 117 passing, 0 failing (100% pass rate)
- **Overall:** 628 passing, 0 failing (100% pass rate)
- **CI Status:** Green (passing)

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is bug fixing for an existing FastAPI application running Python 3.11
- Integration points:
  - Admin API endpoint `/api/admin/trigger-update`
  - CFBD client week detection logic
  - Weekly update orchestration script
- Existing patterns to follow:
  - Import statements at module/function top level
  - Single exit point per error scenario
  - Clear error messages with appropriate exit codes
- Critical compatibility requirements:
  - No changes to API contracts
  - No changes to database schema
  - Maintain existing error message clarity
  - No performance degradation
- Each story must verify that 502 currently passing tests remain passing

The epic should achieve 100% test pass rate (628/628) while maintaining system integrity and clear error handling."

---

## Notes

- **Related Work:**
  - EPIC-FIX-INT-TESTS (Complete) - Fixed integration test fixtures
  - EPIC-FIX-REMAINING-TESTS (Complete) - Fixed integration test data setup
- **Impact:** Final epic to achieve 100% test coverage (unit + integration)
- **Effort:** Low-Medium - focused bug fixes, no architectural changes
- **Risk:** Very low - isolated logic fixes with comprehensive test coverage
- **Priority:** High - blocking deployment, prevents confident releases
- **CI Run:** GitHub Actions run #52603794906 on 2025-12-18

---

## Acceptance Testing

**Manual Verification Steps:**

After all stories complete:

1. **Run full test suite locally:**
   ```bash
   pytest --tb=short
   # Expected: 511 unit tests passed, 117 integration tests passed (628 total)
   ```

2. **Verify CI/CD pipeline:**
   ```bash
   git push
   gh run watch
   # Expected: All checks pass, green status
   ```

3. **Test weekly_update script manually (optional):**
   ```bash
   python scripts/weekly_update.py --dry-run
   # Expected: Proper error messages, single exit per error scenario
   ```

4. **Test trigger_update endpoint manually (optional):**
   ```bash
   curl -X POST http://localhost:8000/api/admin/trigger-update
   # Expected: Proper error codes and messages
   ```

---

## Conclusion

This epic completes the test suite stabilization work by fixing the final 9 unit test failures. Combined with the previous integration test fixes (EPIC-FIX-INT-TESTS, EPIC-FIX-REMAINING-TESTS), this achieves 100% test coverage across both unit and integration tests (628/628 passing). The fixes are low-risk, focused logic corrections that maintain existing system behavior while ensuring test reliability.

**Timeline:**
- Story 1: 1-2 hours (admin endpoint import fix)
- Story 2: 1-2 hours (week detection logic)
- Story 3: 1-2 hours (exit handling consolidation)
- **Total: 3-5 hours (1-2 development sessions)**

**Impact:**
- 9 additional passing tests
- 100% unit test coverage (511/511)
- 100% integration test coverage (117/117)
- Fully green CI/CD pipeline
- Production deployment readiness
