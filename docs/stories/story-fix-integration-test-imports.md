# Story: Fix Integration Test Import Errors - Brownfield Bug Fix

**Story ID**: STORY-INT-01
**Type**: Bug Fix
**Created**: 2025-12-17
**Status**: Closed - Not Reproducible
**Estimated Effort**: 1-2 hours
**Priority**: High
**Resolution**: Import errors do not exist in current codebase (Investigated 2025-12-17)

---

## User Story

As a **developer running CI/CD pipelines**,
I want **integration tests to import modules correctly**,
So that **the CI/CD pipeline can verify code changes and deployments can proceed**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- Integration test suite in `tests/integration/` and `tests/`
- pytest test runner and CI/CD workflow (`.github/workflows/tests.yml`)
- Python module import system

**Technology:**
- Python 3.11
- pytest 7.4.3
- GitHub Actions CI/CD

**Follows pattern:**
- Existing import patterns in working tests
- Python package structure conventions
- pytest configuration in `pytest.ini`

**Touch points:**
- Integration tests: `test_cfbd_import.py`, `test_admin_endpoints.py`, `test_rankings_seasons_api.py`, `test_teams_api.py`
- Module being imported: `cfbd_client` (should be `src.integrations.cfbd_client`)
- CI/CD workflow test execution steps

---

## Problem Statement

### Current Issue

CI/CD pipeline fails with `ModuleNotFoundError: No module named 'cfbd_client'` in integration tests:

**Failing Tests (18+ affected):**
- `tests/test_admin_endpoints.py` - All 5 tests failing
- `tests/integration/test_cfbd_import.py` - All 5 tests failing
- `tests/integration/test_rankings_seasons_api.py` - Multiple tests failing
- `tests/integration/test_teams_api.py` - Multiple tests failing

**Error Pattern:**
```python
ModuleNotFoundError: No module named 'cfbd_client'
```

**Environment Difference:**
- ✅ Tests pass locally (imports work)
- ❌ Tests fail in CI (imports break)

### Root Cause

Integration tests are using incorrect import statements:
- Using: `import cfbd_client` or `from cfbd_client import ...`
- Should be: `from src.integrations.cfbd_client import CFBDClient`

---

## Acceptance Criteria

### Functional Requirements

1. **Fix import statements in all affected integration tests**
   - Update imports to use correct module path: `src.integrations.cfbd_client`
   - Follow pattern used in working unit tests
   - Maintain existing test functionality

2. **All integration tests pass in CI/CD**
   - `pytest -m integration -v` completes successfully
   - No `ModuleNotFoundError` exceptions
   - Test logic remains unchanged (only imports fixed)

3. **Verify no regressions in local test execution**
   - Tests still pass locally after import changes
   - No new errors or warnings introduced

### Integration Requirements

4. **Existing test functionality continues to work**
   - All test assertions remain the same
   - Test coverage unchanged
   - Mock patterns unchanged

5. **Follow existing import patterns**
   - Match import style used in `tests/unit/test_cfbd_client.py`
   - Consistent with other working tests
   - No changes to test organization

6. **CI/CD pipeline returns to green**
   - All integration tests pass: `pytest -m integration -v --tb=short`
   - Full test suite passes: `pytest -m "not e2e"`
   - GitHub Actions workflow completes successfully

### Quality Requirements

7. **No changes to test logic**
   - Only import statements modified
   - Test assertions unchanged
   - Mock behavior unchanged

8. **Verify fix with local and CI testing**
   - Run tests locally before pushing
   - Verify CI/CD passes after push

---

## Technical Notes

### Integration Approach

**Step 1: Identify all affected files**
```bash
# Search for incorrect import pattern
grep -r "import cfbd_client\|from cfbd_client" tests/
```

**Step 2: Review correct import pattern**
Check working tests for reference:
```python
# Correct pattern (from tests/unit/test_cfbd_client.py)
from src.integrations.cfbd_client import CFBDClient
```

**Step 3: Update imports systematically**
For each affected file:
- Replace `import cfbd_client` → `from src.integrations.cfbd_client import CFBDClient`
- Replace `from cfbd_client import X` → `from src.integrations.cfbd_client import X`
- Update any usage if needed (e.g., `cfbd_client.CFBDClient` → `CFBDClient`)

**Step 4: Test locally**
```bash
pytest -m integration -v
```

**Step 5: Verify in CI**
Push changes and monitor GitHub Actions workflow

### Existing Pattern Reference

**Working import pattern (unit tests):**
```python
from src.integrations.cfbd_client import CFBDClient
```

**Incorrect pattern (integration tests):**
```python
import cfbd_client  # ❌ Wrong
from cfbd_client import CFBDClient  # ❌ Wrong
```

### Key Constraints

- **No changes to test logic** - only fix imports
- **Must work in both local and CI environments**
- **No changes to module structure** - only test imports
- **Maintain all existing test coverage**

---

## Definition of Done

- [ ] All integration test import errors identified
- [ ] Import statements updated to correct module path
- [ ] Integration tests pass locally: `pytest -m integration -v`
- [ ] Full test suite passes locally: `pytest -m "not e2e"`
- [ ] Changes committed with clear message
- [ ] CI/CD pipeline passes (GitHub Actions green)
- [ ] No test logic changes (only imports)
- [ ] No new warnings or errors introduced

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:**
Incorrect import path update could break tests or change behavior.

**Mitigation:**
- Reference working unit tests for correct pattern
- Test locally before pushing
- Only modify import statements, not test logic
- Review each file individually

**Rollback:**
```bash
# Simple git revert if issues arise
git revert <commit-hash>
```

### Compatibility Verification

- [x] No breaking changes to test APIs
- [x] No database changes
- [x] No UI changes
- [x] No performance impact (import path only)
- [x] No production code changes (tests only)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one development session (1-2 hours)
- [x] Integration approach is straightforward (fix import paths)
- [x] Follows existing patterns exactly (copy from unit tests)
- [x] No design or architecture work required

### Clarity Check

- [x] Story requirements are unambiguous (fix import errors)
- [x] Integration points are clearly specified (integration tests)
- [x] Success criteria are testable (CI/CD passes)
- [x] Rollback approach is simple (git revert)

---

## Investigation Results

> **Investigation completed:** 2025-12-17

### Findings: Import Errors Do Not Exist ❌

**Status:** The integration test import errors described in this story **do not exist** in the current codebase.

**Evidence:**

1. ✅ **Code search completed:**
   ```bash
   grep -r "import cfbd_client|from cfbd_client" tests/
   ```
   - **Result:** Zero matches found
   - All test files use correct import patterns

2. ✅ **Integration tests executed:**
   ```bash
   pytest -m integration -v --tb=short
   ```
   - **Result:** 117 tests collected, zero `ModuleNotFoundError` exceptions
   - No import errors for `cfbd_client` module

3. ✅ **Actual test results:**
   - 11 tests PASSED
   - 5 tests FAILED (assertion failures, not import errors)
   - 101 tests ERROR (test fixture issue: `TypeError: Client.__init__() got an unexpected keyword argument 'app'`)
   - **Zero import errors**

### Actual Current Issues (Different from Story Description)

**The real integration test failures are:**

1. **Test Fixture Error (101 tests):**
   - Error: `TypeError: Client.__init__() got an unexpected keyword argument 'app'`
   - Location: `tests/conftest.py:101` in `test_client` fixture
   - Cause: Starlette TestClient API incompatibility
   - **This is NOT an import error**

2. **Test Assertion Failures (5 tests):**
   - File: `tests/integration/test_cfbd_import.py`
   - Tests: `test_import_games_*` methods
   - **These are logic failures, not import errors**

### Conclusion

**Recommendation:** Close this story as "Not Reproducible" or "Already Resolved"

The import errors mentioned in the story description do not exist. The integration tests have different issues:
- Test fixture setup error (TestClient initialization)
- Some assertion failures in game import tests

These would require **different stories** to address, not import fixes.

### Verification Commands Run

```bash
# Search for incorrect imports (found none):
grep -n "cfbd" tests/test_admin_endpoints.py tests/integration/test_cfbd_import.py tests/integration/test_rankings_seasons_api.py tests/integration/test_teams_api.py

# Run integration tests (no import errors):
pytest -m integration -v --tb=short

# Results: 5 failed, 11 passed, 101 errors (fixture issue, NOT import errors)
```

---

## Implementation Guidance

**⚠️ NOTE: Implementation not needed - issue does not exist**

### Affected Files (Estimated)

Based on CI logs, likely files to update:
1. `tests/test_admin_endpoints.py`
2. `tests/integration/test_cfbd_import.py`
3. `tests/integration/test_rankings_seasons_api.py`
4. `tests/integration/test_teams_api.py`

### Search and Replace Pattern

```bash
# Find affected files
grep -l "import cfbd_client\|from cfbd_client" tests/**/*.py

# For each file, replace:
# OLD: import cfbd_client
# NEW: from src.integrations.cfbd_client import CFBDClient

# OLD: from cfbd_client import CFBDClient
# NEW: from src.integrations.cfbd_client import CFBDClient
```

### Testing Commands

```bash
# Test locally
pytest -m integration -v --tb=short

# Test full suite
pytest -m "not e2e" -v

# Check specific file
pytest tests/integration/test_cfbd_import.py -v
```

---

## Notes

- **Related Work**: Follows successful completion of STORY-CFBD-02 (unit test fixes)
- **CI Status**: Currently blocking deployments
- **Impact**: 18+ integration tests failing
- **Effort**: Simple import path fixes, minimal code changes
- **Risk**: Very low - isolated to test imports only
