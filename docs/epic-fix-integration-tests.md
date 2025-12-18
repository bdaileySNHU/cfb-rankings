# Epic: Fix Integration Test Suite - Brownfield Enhancement

**Epic ID:** EPIC-FIX-INT-TESTS
**Type:** Bug Fix / Test Infrastructure Enhancement
**Created:** 2025-12-17
**Status:** Ready for Planning
**Priority:** Critical
**Target:** 100% integration test pass rate in CI/CD

---

## Epic Goal

Restore the integration test suite to full working order by fixing the TestClient fixture initialization error and resolving game import test assertion failures, ensuring CI/CD pipeline validates all code changes reliably.

---

## Epic Description

### Existing System Context

**Current Relevant Functionality:**
- Integration test suite with 117 tests covering API endpoints, game imports, team management, predictions, and rankings
- pytest-based testing framework with shared fixtures (`test_client`, `test_db`, `mock_cfbd_client`)
- FastAPI application with Starlette TestClient for endpoint testing
- GitHub Actions CI/CD workflow running full test suite on every push

**Technology Stack:**
- Python 3.11
- pytest 7.4.3 with pytest-mock 3.12.0, pytest-asyncio
- FastAPI web framework
- Starlette TestClient for API testing
- SQLAlchemy ORM with SQLite test database
- GitHub Actions for CI/CD

**Integration Points:**
- `tests/conftest.py` - Central pytest fixtures for test client and database
- `tests/integration/` - Integration test modules
- `.github/workflows/tests.yml` - CI/CD test execution workflow
- Test fixtures shared across 100+ integration tests

### Enhancement Details

**What's Being Fixed:**

**Problem 1: TestClient Fixture Error (101 tests affected)**
- **Error:** `TypeError: Client.__init__() got an unexpected keyword argument 'app'`
- **Location:** `tests/conftest.py:101` in `test_client` fixture
- **Root Cause:** Starlette TestClient API incompatibility (likely version mismatch)
- **Impact:** All API endpoint tests fail during fixture setup (test_games_api, test_teams_api, test_rankings_seasons_api, test_admin_endpoints, test_predictions_api, test_fcs_games_api)
- **Current Status:** 101 ERROR results in test run

**Problem 2: Game Import Test Failures (5 tests affected)**
- **Error:** Test assertion failures in game import logic
- **Location:** `tests/integration/test_cfbd_import.py` - `TestGameImportWithMock` class
- **Affected Tests:**
  - `test_import_games_with_mock_data`
  - `test_import_games_updates_team_records`
  - `test_import_games_skips_fcs_opponents`
  - `test_import_games_handles_neutral_site`
  - `test_mock_client_with_missing_data_fields`
- **Impact:** Game import validation logic not properly tested
- **Current Status:** 5 FAILED results in test run

**How It Integrates:**
- Fix `test_client` fixture initialization in `conftest.py` to use correct TestClient API
- Update test assertions or game import logic to match expected behavior
- Ensure all fixes work both locally and in CI/CD environment
- Maintain backward compatibility with all existing tests

**Success Criteria:**
- ✅ All 117 integration tests pass locally: `pytest -m integration -v`
- ✅ All 117 integration tests pass in GitHub Actions CI/CD
- ✅ Test execution time remains under 5 minutes
- ✅ No new warnings or deprecations introduced
- ✅ Test coverage maintained or improved
- ✅ CI/CD pipeline returns to green status

---

## Stories

This epic consists of 2 focused stories:

### Story 1: Fix TestClient Fixture Initialization Error

**Goal:** Resolve the `TypeError: Client.__init__() got an unexpected keyword argument 'app'` error affecting 101 integration tests

**Scope:**
- Investigate Starlette TestClient API requirements and current usage
- Update `test_client` fixture in `tests/conftest.py` to use correct initialization pattern
- Verify fix works across all affected test modules
- Ensure compatibility with local development and CI/CD environments

**Acceptance Criteria:**
- All API endpoint tests using `test_client` fixture pass
- No ERROR results during test fixture setup
- Tests pass in both Python 3.11 local environment and GitHub Actions
- All 101 previously erroring tests now execute successfully

**Estimated Effort:** 2-4 hours

---

### Story 2: Fix Game Import Test Assertion Failures

**Goal:** Resolve assertion failures in 5 game import integration tests

**Scope:**
- Investigate root cause of assertion failures in `TestGameImportWithMock` tests
- Determine if issue is in test expectations or actual import logic
- Fix test assertions or game import logic as appropriate
- Verify game import functionality works correctly with real and mock data

**Acceptance Criteria:**
- All 5 game import tests pass with correct assertions
- Game import logic correctly handles:
  - Mock game data import
  - Team record updates
  - FCS opponent filtering
  - Neutral site games
  - Missing data fields
- No regression in game import functionality
- Tests accurately validate production behavior

**Estimated Effort:** 2-3 hours

---

## Compatibility Requirements

- ✅ **Existing APIs remain unchanged** - Test fixes only, no production code changes unless game import logic is genuinely broken
- ✅ **Database schema unchanged** - Test database setup remains the same
- ✅ **UI changes:** None - backend testing only
- ✅ **Performance impact:** Minimal - test execution time may improve slightly
- ✅ **Dependency compatibility:** Ensure Starlette/FastAPI versions are aligned

---

## Risk Mitigation

### Primary Risks

**Risk 1: TestClient API Breaking Change**
- **Description:** Starlette TestClient API may have changed between versions, requiring code updates beyond fixture initialization
- **Probability:** Medium
- **Impact:** High (could require test refactoring across multiple files)
- **Mitigation:**
  - Check Starlette/FastAPI version compatibility matrix
  - Review TestClient API documentation for correct usage
  - Test fixture fix thoroughly across all affected test modules
  - If needed, pin specific compatible versions in requirements.txt
- **Rollback Plan:** Revert fixture changes, investigate alternative TestClient initialization

**Risk 2: Game Import Logic Actually Broken**
- **Description:** Test failures may indicate real bugs in game import logic, not just test issues
- **Probability:** Medium
- **Impact:** Medium (would require production code fixes and more extensive testing)
- **Mitigation:**
  - Analyze test failures to distinguish test issues from logic bugs
  - Review game import implementation in `import_real_data.py` or similar
  - If logic bugs found, create additional stories for production fixes
  - Verify with real data import scenarios
- **Rollback Plan:** Separate test fixes from logic fixes; rollback independently if needed

**Risk 3: Environment Differences (Local vs CI)**
- **Description:** Fixes may pass locally but fail in CI due to environment differences
- **Probability:** Low
- **Impact:** Medium (would delay CI/CD restoration)
- **Mitigation:**
  - Test in both local and CI environments before considering story complete
  - Check for Python version differences, dependency versions
  - Review CI/CD workflow configuration
  - Consider adding environment-specific test skips if necessary
- **Rollback Plan:** Git revert individual commits if CI failures occur

### Overall Rollback Plan

```bash
# Rollback Story 1 (TestClient fixture)
git revert <story-1-commit-hash>

# Rollback Story 2 (Game import tests)
git revert <story-2-commit-hash>

# If needed, rollback entire epic
git revert <epic-start-hash>..HEAD
```

All changes are isolated to test code, making rollback safe and non-disruptive to production.

---

## Definition of Done

**Epic-Level Completion Criteria:**

- ✅ All 117 integration tests pass locally with zero errors
- ✅ All 117 integration tests pass in GitHub Actions CI/CD
- ✅ Both Story 1 and Story 2 completed with acceptance criteria met
- ✅ CI/CD pipeline returns to green status (all workflows passing)
- ✅ No new test warnings or errors introduced
- ✅ Test execution time remains acceptable (< 5 minutes)
- ✅ Documentation updated if test patterns changed
- ✅ Changes committed with clear messages and pushed to main branch
- ✅ GitHub issues created and closed for tracking

**Verification Commands:**

```bash
# Local verification
pytest -m integration -v --tb=short

# Full test suite
pytest -m "not e2e" -v

# Check CI/CD status
gh run list --limit 1
gh run view <run-id>
```

---

## Dependencies and Sequencing

**Story Dependencies:**
- Story 1 and Story 2 are **independent** and can be worked in parallel or sequentially
- Recommend completing Story 1 first (fixes 101 tests vs 5 tests)
- Both stories must complete before epic is considered done

**External Dependencies:**
- None - all changes are internal to test suite
- May require `requirements.txt` or `requirements-dev.txt` updates if version pinning needed

---

## Technical Notes

### Story 1 Investigation Starting Points

**Check TestClient initialization:**
```python
# Current pattern in tests/conftest.py:101
from fastapi.testclient import TestClient
client = TestClient(app)  # ← This is failing

# Possible correct pattern (depending on Starlette version):
client = TestClient(app=app)
# OR
from starlette.testclient import TestClient
client = TestClient(app)
```

**Review Starlette/FastAPI versions:**
```bash
pip show starlette fastapi
```

### Story 2 Investigation Starting Points

**Check failing test output:**
```bash
pytest tests/integration/test_cfbd_import.py::TestGameImportWithMock -v --tb=long
```

**Review game import implementation:**
- Check `scripts/import_teams()` and `import_games()` functions
- Compare mock data structure with real CFBD API responses
- Verify test expectations match actual import behavior

---

## Success Metrics

**Pre-Epic Status:**
- ❌ Integration test pass rate: 9.4% (11/117 passing)
- ❌ CI/CD status: Failing
- ❌ Test errors: 101 errors, 5 failures

**Post-Epic Target:**
- ✅ Integration test pass rate: 100% (117/117 passing)
- ✅ CI/CD status: Passing (green)
- ✅ Test errors: 0 errors, 0 failures

---

## Related Documentation

- Test file: `tests/conftest.py` (fixture definitions)
- Integration tests: `tests/integration/test_*.py`
- CI/CD workflow: `.github/workflows/tests.yml`
- Previous test fixes: STORY-CFBD-01, STORY-CFBD-02 (unit test mock fixes)
- Investigation results: `docs/stories/story-fix-integration-test-imports.md` (STORY-INT-01)

---

## Notes

- This epic focuses exclusively on test infrastructure fixes
- No production code changes expected (unless game import logic is genuinely broken in Story 2)
- High priority: CI/CD is currently non-functional for integration testing
- Quick wins: Story 1 fix will restore 86% of integration test suite
- This follows successful completion of unit test fixes (STORY-CFBD-02)
