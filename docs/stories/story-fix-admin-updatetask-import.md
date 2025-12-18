# Story: Fix Admin Endpoint UpdateTask Import Error - Brownfield Bug Fix

**Story ID**: STORY-FIX-ADMIN-UPDATETASK
**Epic**: EPIC-FIX-CI-TESTS (Fix CI Test Failures)
**Type**: Bug Fix
**Created**: 2025-12-18
**Status**: Ready for Development
**Estimated Effort**: 1-2 hours
**Priority**: High
**Complexity**: Low

---

## User Story

As a **developer running unit tests**,
I want **admin trigger_update endpoint tests to pass without import errors**,
So that **I can verify the manual data import functionality works correctly and CI/CD pipeline is reliable**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `src/api/main.py` - Admin endpoint definitions, specifically `trigger_update` endpoint
- `src/models/models.py` - UpdateTask model for tracking update operations
- `tests/test_admin_endpoints.py` - Admin endpoint unit tests
- FastAPI dependency injection and error handling system

**Technology:**
- Python 3.11
- FastAPI 0.125.0
- SQLAlchemy ORM
- pytest 7.4.3 with FastAPI TestClient

**Follows pattern:**
- FastAPI application structure with endpoint modules
- SQLAlchemy model imports from src.models.models
- FastAPI HTTPException for error responses (400, 500 status codes)
- Database session management with dependency injection

**Touch points:**
- `src/api/main.py` - trigger_update endpoint function (imports UpdateTask)
- `src/models/models.py` - UpdateTask model definition
- `tests/test_admin_endpoints.py` - TestTriggerUpdateEndpoint class (4 tests)

---

## Problem Statement

### Current Issue

4 unit tests in `TestTriggerUpdateEndpoint` fail with `UnboundLocalError`:

```python
UnboundLocalError: cannot access local variable 'UpdateTask' where it is not associated with a value
```

**Failing Tests:**
1. `test_trigger_update_fails_with_no_week` - Returns 500 instead of expected 400
2. `test_trigger_update_succeeds_with_valid_conditions` - UnboundLocalError on UpdateTask access
3. `test_trigger_update_creates_task_record` - UnboundLocalError on UpdateTask access
4. `test_trigger_and_check_status_workflow` - UnboundLocalError on UpdateTask access

**Error Location:** trigger_update endpoint in `src/api/main.py`

**Impact:**
- Manual data import endpoint completely untested
- Status code validation failing (500 instead of 400)
- UpdateTask database record creation untested
- Integration workflow between trigger and status endpoints untested
- 4 of 511 unit tests failing (blocking CI/CD)

### Root Cause

**Likely Cause:**
UpdateTask import statement is placed inside a conditional block or try/except statement, making the variable inaccessible in certain code paths.

**Common Python Scoping Error Pattern:**
```python
# ❌ INCORRECT - Import inside conditional
@app.post("/api/admin/trigger-update")
async def trigger_update(request: Request):
    if some_condition:
        from src.models.models import UpdateTask  # Only bound if condition True

    # UnboundLocalError if condition was False
    task = UpdateTask(...)  # ❌ UpdateTask not in scope
```

**Expected Pattern:**
```python
# ✅ CORRECT - Import at function/module top level
from src.models.models import UpdateTask

@app.post("/api/admin/trigger-update")
async def trigger_update(request: Request):
    # UpdateTask available in all code paths
    task = UpdateTask(...)  # ✅ Works correctly
```

**Secondary Issue:**
Error handling likely returns 500 (server error) instead of 400 (bad request) when week parameter is missing, indicating validation logic error.

---

## Acceptance Criteria

### Functional Requirements

1. **UpdateTask import accessible in all code paths**
   - Import statement at function or module top level
   - Not inside conditional blocks or try/except
   - Available before any code path that uses UpdateTask

2. **Missing week parameter returns 400 status**
   - `test_trigger_update_fails_with_no_week` expects 400 Bad Request
   - Error message clear: "Week parameter required" or similar
   - Not 500 Internal Server Error

3. **Valid trigger_update request succeeds**
   - `test_trigger_update_succeeds_with_valid_conditions` passes
   - Returns appropriate success response
   - No UnboundLocalError

4. **UpdateTask record created in database**
   - `test_trigger_update_creates_task_record` passes
   - Task record has correct attributes (week, status, timestamp)
   - Database transaction commits successfully

5. **Trigger and status workflow works end-to-end**
   - `test_trigger_and_check_status_workflow` passes
   - Can trigger update and retrieve status
   - Status reflects task state correctly

### Integration Requirements

6. **Existing endpoint functionality preserved**
   - Only fix import placement and error handling
   - No changes to endpoint logic or behavior
   - API contracts remain unchanged
   - Database operations unchanged

7. **Follow project import conventions**
   - Use full package paths: `from src.models.models import UpdateTask`
   - Consistent with other imports in main.py
   - Place imports at top of function or module

### Quality Requirements

8. **No regression in other tests**
   - 507 currently passing unit tests continue to pass (511 total - 4 failing)
   - Other admin endpoint tests unaffected
   - Full unit suite: 511 passing, 0 failing

9. **Clean error handling**
   - Appropriate HTTP status codes (400 vs 500)
   - Clear error messages for API consumers
   - No stack traces in API responses for user errors

---

## Technical Notes

### Investigation Approach

**Step 1: Locate trigger_update endpoint**
```bash
# Find trigger_update function in main.py
grep -n "def trigger_update" src/api/main.py
```

**Step 2: Identify UpdateTask import location**
```bash
# Search for UpdateTask imports in endpoint
grep -A 20 -B 5 "def trigger_update" src/api/main.py | grep "UpdateTask"
```

**Step 3: Check import placement**
- Is import inside if/else block?
- Is import inside try/except?
- Is import at function top level?

**Step 4: Verify UpdateTask model exists**
```bash
# Confirm UpdateTask is defined in models
grep "class UpdateTask" src/models/models.py
```

### Implementation Approach

**Fix 1: Move UpdateTask Import to Top**

```python
# BEFORE (likely causing UnboundLocalError)
@app.post("/api/admin/trigger-update")
async def trigger_update(
    request: Request,
    week: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if not week:
        raise HTTPException(status_code=500, detail="Week required")  # Wrong code

    try:
        from src.models.models import UpdateTask  # ❌ Inside try block
        task = UpdateTask(week=week, status="pending")
        db.add(task)
        db.commit()
    except Exception as e:
        # If exception before import, UpdateTask not bound
        task = UpdateTask(...)  # ❌ UnboundLocalError here
```

```python
# AFTER (fixed)
from src.models.models import UpdateTask  # ✅ At function top

@app.post("/api/admin/trigger-update")
async def trigger_update(
    request: Request,
    week: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if not week:
        raise HTTPException(status_code=400, detail="Week required")  # ✅ Correct code

    try:
        task = UpdateTask(week=week, status="pending")  # ✅ Works in all paths
        db.add(task)
        db.commit()
        return {"status": "success", "task_id": task.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

**Fix 2: Correct Error Status Code**

Change validation error from 500 → 400:
```python
# BEFORE
if not week:
    raise HTTPException(status_code=500, detail="Week required")  # ❌

# AFTER
if not week:
    raise HTTPException(status_code=400, detail="Week required")  # ✅
```

### Testing the Fix

```bash
# Run single failing test
pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_fails_with_no_week -xvs

# Expected: PASSED (assert 400 == 400)

# Run all 4 trigger_update tests
pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint -v

# Expected: 4 passed

# Run full unit suite to verify no regressions
pytest --tb=short

# Expected: 511 passed, 0 failed
```

### Key Constraints

- **No logic changes** - only fix import placement and error code
- **No API changes** - endpoint behavior unchanged
- **No database changes** - UpdateTask model unchanged
- **No test changes** - tests are correct, only fix production code
- **Follow conventions** - use full package paths (src.models.models)

---

## Definition of Done

- [ ] UpdateTask import moved to function/module top level in src/api/main.py
- [ ] Import uses full package path: `from src.models.models import UpdateTask`
- [ ] Missing week parameter returns 400 status (not 500)
- [ ] All 4 trigger_update tests pass: `pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint -v`
- [ ] No UnboundLocalError in test output
- [ ] No regression in other tests (507 currently passing continue to pass)
- [ ] Changes committed with clear message: "Fix UpdateTask import scoping and error code in trigger_update endpoint"
- [ ] Full unit suite: 511 passed, 0 failed

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:**
Moving import might reveal other scoping issues or dependencies not visible in current broken state.

**Mitigation:**
1. Read entire trigger_update function before making changes
2. Understand all code paths that use UpdateTask
3. Run tests immediately after fix to verify
4. Check for other endpoints with similar pattern

**Rollback:**
```bash
# Simple revert if issues arise
git revert <commit-hash>

# Or manual rollback
git checkout HEAD~1 -- src/api/main.py
```

### Compatibility Verification

- [x] No breaking changes to API contracts
- [x] No database schema changes
- [x] No changes to UpdateTask model
- [x] No configuration changes
- [x] No external dependencies affected
- [x] Production code behavior unchanged (only fix scoping bug)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one session (1-2 hours)
- [x] Fix approach is straightforward (move import, fix status code)
- [x] Follows existing patterns (top-level imports)
- [x] No design or architecture work required

### Clarity Check

- [x] Story requirements are clear (fix import scoping and error code)
- [x] Integration points are specified (trigger_update endpoint in main.py)
- [x] Success criteria are testable (4 tests pass, correct status codes)
- [x] Rollback approach is simple (git revert)

---

## Implementation Guidance

### Step-by-Step Workflow

1. **Read the trigger_update endpoint**
   ```bash
   # Read src/api/main.py focusing on trigger_update function
   # Identify line numbers for the function
   ```

2. **Locate UpdateTask import**
   ```bash
   # Find where UpdateTask is imported within the function
   grep -n "UpdateTask" src/api/main.py
   ```

3. **Identify the scoping issue**
   - Is import inside if/else?
   - Is import inside try/except?
   - What code paths fail to bind UpdateTask?

4. **Apply fix - Move import to top**
   - Place import at beginning of function (or module level if appropriate)
   - Use full package path: `from src.models.models import UpdateTask`

5. **Apply fix - Correct error status code**
   - Find validation for missing week parameter
   - Change HTTPException status_code from 500 → 400

6. **Test immediately**
   ```bash
   # Run one test to verify fix works
   pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_fails_with_no_week -xvs

   # Should see: PASSED (and assert 400 == 400)
   ```

7. **Run all affected tests**
   ```bash
   # Run all 4 trigger_update tests
   pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint -v

   # Should see: 4 passed
   ```

8. **Verify no regression**
   ```bash
   # Run full unit suite
   pytest --tb=short

   # Should see: 511 passed, 0 failed
   ```

9. **Commit changes**
   ```bash
   git add src/api/main.py
   git commit -m "Fix UpdateTask import scoping and error code in trigger_update endpoint

Fixes 4 failing tests in TestTriggerUpdateEndpoint:
- Move UpdateTask import to function top level (was inside conditional/try block)
- Fix missing week validation to return 400 instead of 500

Tests now passing:
- test_trigger_update_fails_with_no_week (400 status code)
- test_trigger_update_succeeds_with_valid_conditions
- test_trigger_update_creates_task_record
- test_trigger_and_check_status_workflow

Part of EPIC-FIX-CI-TESTS Story 1."
   ```

### Commands Reference

```bash
# Investigation
grep -n "def trigger_update" src/api/main.py
grep -B 10 -A 30 "def trigger_update" src/api/main.py

# Testing
pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint -v
pytest tests/test_admin_endpoints.py::TestTriggerUpdateEndpoint::test_trigger_update_fails_with_no_week -xvs
pytest --tb=short

# Verification
git diff src/api/main.py
```

---

## Notes

- **Related Work**:
  - Part of EPIC-FIX-CI-TESTS
  - Follows pattern from EPIC-FIX-REMAINING-TESTS (import path fixes)
  - Complements Story 2 (CFBD week detection) and Story 3 (exit handling)
- **Common Python Gotcha**: Variable scope when imports inside conditional/try blocks
- **CI Impact**: Fixes 4 of 9 failing unit tests (44% of failures)
- **Effort**: Low - straightforward scoping fix + status code change
- **Risk**: Very low - isolated fix, easy rollback, comprehensive tests
- **Priority**: High - blocking CI/CD, prevents confident deployments

---

## Expected Changes

**File: src/api/main.py**

**Change 1: Move UpdateTask import to top of function**
```python
# Location: trigger_update function (around line 1336 based on story-fix-admin-endpoint-imports.md)

# Add at top of function:
+ from src.models.models import UpdateTask

# Remove from inside conditional/try block:
- from src.models.models import UpdateTask  # (wherever it currently is)
```

**Change 2: Fix validation error status code**
```python
# Change validation logic:
- raise HTTPException(status_code=500, detail="Week parameter required")
+ raise HTTPException(status_code=400, detail="Week parameter required")
```

**Total Changes:** ~2 lines modified in 1 file (1 import move + 1 status code change)
