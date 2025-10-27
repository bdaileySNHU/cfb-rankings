# EPIC-015: Fix Remaining Test Failures

**Status:** Not Started
**Priority:** High
**Estimated Effort:** 2-4 hours
**Dependencies:** EPIC-014 (Complete)
**Related EPIC:** EPIC-014 (Test Fixture Refactoring)

## Overview

Fix the 5 remaining test failures from EPIC-014 refactoring to achieve 100% test pass rate in CI/CD. These tests are newly enabled (previously skipped) and require additional mocking setup.

## Problem Statement

After EPIC-014 refactoring, 50/55 tests now pass (91% success rate), but 5 tests still fail:
1. `test_usage_dashboard_returns_200`
2. `test_usage_dashboard_has_required_fields`
3. `test_usage_dashboard_current_month_fields`
4. `test_usage_dashboard_with_month_parameter`
5. `test_usage_dashboard_calculates_projections`

These failures prevent CI/CD from passing and need to be resolved for production readiness.

## Goals

1. **100% test pass rate** - All 55 refactored tests should pass in CI/CD
2. **No regressions** - Fix failures without breaking existing passing tests
3. **Proper mocking** - Ensure all external dependencies are mocked correctly
4. **CI/CD green** - GitHub Actions workflow completes successfully

## Non-Goals

- Adding new test coverage (separate effort)
- Refactoring test structure beyond what's needed to fix failures
- Modifying production code to accommodate tests

## Success Criteria

- [ ] All 5 failing tests now pass locally
- [ ] All 5 failing tests pass in CI/CD
- [ ] No regressions in previously passing tests
- [ ] GitHub Actions workflow shows green checkmark
- [ ] Total test count: 437 passing, 0 failing, 0 skipped

---

## Current Failure Analysis

### Failure Pattern

All 5 failures are in `tests/test_admin_endpoints.py` in the `TestUsageDashboardEndpoint` class.

**Error Pattern from CI:**
```
tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_returns_200 FAILED [ 0%]
tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_has_required_fields FAILED [ 0%]
tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_current_month_fields FAILED [ 0%]
tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_with_month_parameter FAILED [ 0%]
tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_calculates_projections FAILED [ 0%]
```

### Root Cause

The `/api/admin/usage-dashboard` endpoint likely:
1. Queries the `api_usage` table which doesn't exist in test database
2. Calls functions that need mocking (e.g., `get_monthly_usage()`)
3. Expects specific data that isn't seeded in test fixtures

---

## Stories

### Story 001: Investigate and Fix Usage Dashboard Test Failures

**Story Points:** 3
**Priority:** High

#### Description

Investigate why all 5 usage dashboard tests fail and implement the necessary mocking or test data setup to make them pass.

#### Acceptance Criteria

- [ ] Run failing tests locally with verbose output to see exact errors
- [ ] Identify what database tables/functions the endpoint depends on
- [ ] Add necessary test data fixtures or mocks
- [ ] All 5 tests pass locally
- [ ] Tests pass in CI/CD

#### Technical Investigation Steps

1. **Run tests with full output:**
```bash
pytest tests/test_admin_endpoints.py::TestUsageDashboardEndpoint -v --tb=long
```

2. **Check endpoint implementation:**
```bash
grep -A 50 "def usage_dashboard" main.py
```

3. **Identify dependencies:**
   - Does it query `api_usage` table?
   - Does it call `get_monthly_usage()`?
   - Does it need seeded data?

4. **Common solutions:**
   - Add `APIUsage` records to test database
   - Mock `get_monthly_usage()` function
   - Mock datetime for consistent test results
   - Add test fixture for API usage data

#### Implementation Approaches

**Option A: Seed Test Data**
```python
def test_usage_dashboard_returns_200(self, test_db, test_client):
    """Dashboard endpoint should return 200 OK"""
    # Seed API usage data
    usage = APIUsage(
        endpoint="/api/teams",
        timestamp=datetime.utcnow(),
        response_time=100
    )
    test_db.add(usage)
    test_db.commit()

    response = test_client.get("/api/admin/usage-dashboard")
    assert response.status_code == 200
```

**Option B: Mock Dependencies**
```python
@patch('main.get_monthly_usage')
def test_usage_dashboard_returns_200(self, mock_get_usage, test_client):
    """Dashboard endpoint should return 200 OK"""
    mock_get_usage.return_value = {
        'total_calls': 500,
        'monthly_limit': 1000,
        'percentage_used': 50.0
    }

    response = test_client.get("/api/admin/usage-dashboard")
    assert response.status_code == 200
```

**Option C: Hybrid Approach** (Recommended)
- Mock date/time functions for consistency
- Seed minimal test data
- Mock complex calculations

#### Testing Strategy

```bash
# Step 1: Run one test to see exact error
pytest tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_returns_200 -vv

# Step 2: Fix that test, verify it passes
pytest tests/test_admin_endpoints.py::TestUsageDashboardEndpoint::test_usage_dashboard_returns_200 -v

# Step 3: Apply same fix to other 4 tests
pytest tests/test_admin_endpoints.py::TestUsageDashboardEndpoint -v

# Step 4: Verify no regressions
pytest tests/test_admin_endpoints.py -v

# Step 5: Run full suite
pytest -v
```

---

### Story 002: Verify CI/CD Success

**Story Points:** 1
**Priority:** High

#### Description

Ensure the fixes work in CI/CD environment and update documentation.

#### Acceptance Criteria

- [ ] Push fixes to GitHub
- [ ] GitHub Actions workflow passes with all tests green
- [ ] Update EPIC-014 documentation with completion status
- [ ] Update EPIC-015 documentation as complete

#### Implementation Steps

1. **Commit and push:**
```bash
git add tests/test_admin_endpoints.py
git commit -m "Fix remaining 5 test failures (EPIC-015)

- Add proper mocking for usage dashboard tests
- Seed test data for api_usage table
- All 55 refactored tests now pass

EPIC-015 complete: 100% test pass rate achieved

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

2. **Monitor CI/CD:**
```bash
gh run watch --exit-status
```

3. **Verify results:**
   - All tests pass (437/437)
   - No skipped tests (0)
   - No failures (0)
   - Green checkmark in GitHub Actions

4. **Update documentation:**
   - Mark EPIC-015 as complete
   - Update NEW_PROJECT_DOCUMENTATION.md with new test counts
   - Update EPIC-014-TEST-FIXTURE-REFACTORING.md with final results

---

## Implementation Plan

### Phase 1: Investigation (30 minutes)
1. Run failing tests locally with verbose output
2. Check endpoint source code
3. Identify exact failure reasons
4. Document findings

### Phase 2: Fix Implementation (1-2 hours)
1. Implement fixes for first test
2. Verify fix works
3. Apply same pattern to other 4 tests
4. Run all tests locally to confirm no regressions

### Phase 3: CI/CD Verification (30 minutes)
1. Commit and push changes
2. Monitor GitHub Actions
3. Verify all tests pass
4. Update documentation

### Phase 4: Documentation (30 minutes)
1. Update EPIC-015 status to complete
2. Update project documentation with final test counts
3. Create completion summary if needed

---

## Expected Outcomes

### Before EPIC-015
- Total tests: 437
- Passing: 432
- Failing: 5
- Skipped: 0
- CI/CD: ❌ Failing

### After EPIC-015
- Total tests: 437
- Passing: 437
- Failing: 0
- Skipped: 0
- CI/CD: ✅ Passing

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Fixes break other tests | High | Low | Run full test suite locally before pushing |
| Mocking is too complex | Medium | Low | Use simpler test data seeding approach |
| Tests still fail in CI | High | Low | Test locally with same Python/dependency versions |
| Time estimate too low | Low | Medium | Break work into smaller increments, commit frequently |

---

## Related Documentation

- **EPIC-014:** `docs/EPIC-014-TEST-FIXTURE-REFACTORING.md`
- **Test Patterns:** `docs/TESTING.md`
- **CI/CD Pipeline:** `docs/CI-CD-PIPELINE.md`
- **Admin Endpoints:** Test implementation in `tests/test_admin_endpoints.py`

---

## Notes

- These tests were previously skipped, so failures are not regressions
- EPIC-014 was 91% successful (50/55 passing)
- This EPIC will bring success rate to 100%
- All test infrastructure from EPIC-014 is in place and working

---

**Created:** 2025-10-26
**Last Updated:** 2025-10-26
**Owner:** Development Team
**Status:** Ready to Start
