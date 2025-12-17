# Story: Fix Test Mocks to Match Actual CFBD API Response Schema - Brownfield Fix

**Story ID**: STORY-CFBD-02
**Epic**: Fix CFBD Client Test Failures
**Created**: 2025-12-16
**Status**: Ready for Review
**Estimated Effort**: 2-4 hours (Completed in ~30 mins)
**Priority**: High

---

## User Story

As a **developer maintaining the CFBD client test suite**,
I want **test mocks to accurately reflect the real CFBD API response schema**,
So that **our unit tests validate actual production behavior and the CI/CD pipeline returns to green status**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- Test suite in `tests/unit/test_cfbd_client.py`
- `CFBDClient.get_current_week()` method in `src/integrations/cfbd_client.py`
- GitHub Actions CI/CD pipeline (`.github/workflows/tests.yml`)

**Technology:**
- Python 3.11
- pytest 7.4.3 with pytest-mock 3.12.0
- unittest.mock for patching

**Follows pattern:**
- Existing test mocking patterns in `test_cfbd_client.py`
- pytest unit test structure with class-based organization
- Mock object patterns using `@patch.object()`

**Touch points:**
- 6 failing tests in `TestWeekDetection` and `TestEdgeCases` classes
- Mock objects created with `@patch.object(client, "get_games")`
- CI/CD test execution workflow

---

## Acceptance Criteria

### Functional Requirements

1. **Update all test mock data** to use correct field names (determined in STORY-CFBD-01):
   - Fix `TestWeekDetection.test_get_current_week_with_completed_games` (line 66)
   - Fix `TestWeekDetection.test_get_current_week_week_1_only` (line 106)
   - Fix `TestWeekDetection.test_get_current_week_ignores_missing_week_field` (line 118)
   - Fix `TestEdgeCases.test_get_current_week_excludes_future_games_with_zero_scores` (line 132)
   - Fix `TestEdgeCases.test_get_current_week_epic_008_scenario` (line 148)
   - Fix `TestEdgeCases.test_get_current_week_with_mixed_data` (line 166)

2. **All 6 failing tests pass** after mock updates:
   - `test_get_current_week_with_completed_games` returns week 8 (not None)
   - `test_get_current_week_week_1_only` returns week 1 (not None)
   - `test_get_current_week_ignores_missing_week_field` returns week 5 (not None)
   - `test_get_current_week_excludes_future_games_with_zero_scores` returns week 5 (not None)
   - `test_get_current_week_epic_008_scenario` returns week 9 (not None)
   - `test_get_current_week_with_mixed_data` returns week 3 (not None)

3. **Update implementation if needed** (only if STORY-CFBD-01 reveals implementation is incorrect):
   - Fix field access in `get_current_week()` method
   - Update field names in lines 346-347 and 356 of `cfbd_client.py`
   - Maintain backward compatibility with existing API integration

### Integration Requirements

4. **Existing CFBD client functionality continues to work**:
   - All other tests in `test_cfbd_client.py` still pass
   - No regression in `TestSeasonDetection` tests
   - No regression in `TestWeekEstimation` tests
   - Production API calls continue to work correctly

5. **Follow existing test patterns**:
   - Mock structure matches existing test format
   - Test documentation follows existing conventions
   - No changes to test organization or class structure

6. **CI/CD pipeline returns to green**:
   - All unit tests pass: `pytest -m unit -v --tb=short`
   - All integration tests pass: `pytest -m integration -v --tb=short`
   - Full test suite passes: `pytest -m "not e2e"`
   - GitHub Actions workflow completes successfully

### Quality Requirements

7. **Add documentation explaining API schema**:
   - Add module-level docstring or comment in test file
   - Document field naming convention from CFBD API
   - Reference STORY-CFBD-01 investigation findings
   - Example:
     ```python
     """
     CFBD API Response Schema (verified 2025-12-16):
     - Score fields use camelCase: homePoints, awayPoints
     - Week field uses lowercase: week
     - See: https://api.collegefootballdata.com/api/docs/
     """
     ```

8. **Verify changes with pytest locally before pushing**:
   - Run failing tests individually: `pytest tests/unit/test_cfbd_client.py::TestWeekDetection -v`
   - Run full test suite: `pytest tests/unit/test_cfbd_client.py -v`
   - Check for any new warnings or deprecations

9. **No unrelated code changes**:
   - Changes limited to test mocks and (possibly) implementation field access
   - No refactoring or cleanup in this story
   - No changes to test structure or organization

---

## Technical Notes

### Implementation Approach

**Step 1: Review STORY-CFBD-01 Findings**
- Read investigation results from previous story
- Confirm correct field naming: camelCase vs snake_case
- Note any special cases (postseason, missing fields, etc.)

**Step 2: Update Test Mocks**

**Current mock format (INCORRECT - example):**
```python
mock_games = [
    {"week": 1, "home_points": 35, "away_points": 28},  # snake_case
    {"week": 2, "home_points": 21, "away_points": 24},
]
```

**Updated mock format (if API uses camelCase):**
```python
mock_games = [
    {"week": 1, "homePoints": 35, "awayPoints": 28},  # camelCase
    {"week": 2, "homePoints": 21, "awayPoints": 24},
]
```

**Step 3: Update All 6 Failing Tests**

| Test Method | Line | Mock Data to Update |
|------------|------|---------------------|
| `test_get_current_week_with_completed_games` | 71-77 | 5 game objects |
| `test_get_current_week_week_1_only` | 106-110 | 2 game objects |
| `test_get_current_week_ignores_missing_week_field` | 118-124 | 3 game objects |
| `test_get_current_week_excludes_future_games_with_zero_scores` | 132-138 | 4 game objects |
| `test_get_current_week_epic_008_scenario` | 148-156 | 7 game objects |
| `test_get_current_week_with_mixed_data` | 166-172 | 5 game objects |

**Step 4: Update Implementation (if needed)**

If STORY-CFBD-01 reveals implementation is wrong:
```python
# Current (lines 346-347):
home_points = game.get("homePoints")  # If this is wrong
away_points = game.get("awayPoints")

# Update to (example if snake_case is correct):
home_points = game.get("home_points")
away_points = game.get("away_points")
```

**Step 5: Add Documentation**
- Add API schema comment block at top of test class or module
- Reference official API docs
- Note verification date

**Step 6: Run Tests**
```bash
# Run failing tests specifically
pytest tests/unit/test_cfbd_client.py::TestWeekDetection::test_get_current_week_with_completed_games -v

# Run all week detection tests
pytest tests/unit/test_cfbd_client.py::TestWeekDetection -v
pytest tests/unit/test_cfbd_client.py::TestEdgeCases -v

# Run full CFBD client test suite
pytest tests/unit/test_cfbd_client.py -v

# Run full unit test suite
pytest -m unit -v
```

### Existing Pattern Reference

**Current test mock pattern:**
```python
def test_get_current_week_with_completed_games(self):
    """Test week detection when games have been played"""
    client = CFBDClient()

    mock_games = [
        {"week": 1, "home_points": 35, "away_points": 28},  # Update these dicts
    ]

    with patch.object(client, "get_games", return_value=mock_games):
        week = client.get_current_week(2025)
        assert week == 8
```

**Follow this pattern** - only update the dictionary field names.

### Key Constraints

- **Do not change test logic** - only update mock data field names
- **Do not change assertions** - expected values should remain the same
- **Maintain test isolation** - each test should still be independently runnable
- **Preserve test coverage** - all edge cases must remain tested
- **If implementation needs fixing**, ensure production compatibility

---

## Definition of Done

- [x] STORY-CFBD-01 investigation results reviewed
- [x] All 6 test mocks updated with correct field names
- [x] Implementation field access updated (if needed based on investigation)
- [x] All 6 previously failing tests now pass
- [x] Full CFBD client test suite passes (no regressions)
- [x] Unit test suite passes: `pytest -m unit -v`
- [x] Integration test suite passes: `pytest -m integration -v`
- [x] API schema documented in test file comments
- [x] Changes committed with clear message referencing epic
- [x] CI/CD pipeline shows green status on GitHub Actions
- [x] No new warnings or errors introduced

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:**
Changing field names incorrectly could cause tests to pass while production code fails with real API.

**Mitigation:**
- STORY-CFBD-01 provides verified API schema before any changes
- Cross-reference with actual API documentation
- If possible, test with real API call in development environment
- Review production logs to verify current behavior is working
- Run full test suite, not just the 6 failing tests

**Rollback:**
```bash
# Simple git revert if issues arise
git revert <commit-hash>

# Or manual revert of test mocks
git checkout HEAD~1 -- tests/unit/test_cfbd_client.py
```

### Compatibility Verification

- [x] No breaking changes to public APIs (test-only changes expected)
- [x] No database changes
- [x] No UI changes
- [x] No performance impact (test execution only)

**If implementation needs updating:**
- [ ] Verify production API calls still work
- [ ] Check for any cached responses or middleware transformations
- [ ] Ensure backward compatibility with any data processing pipelines

---

## Pre-Implementation Checklist

Before starting this story:

- [ ] STORY-CFBD-01 is complete with documented findings
- [ ] Correct API field naming is confirmed (camelCase vs snake_case)
- [ ] Decision made: update tests only, or tests + implementation
- [ ] Sample API response available for reference
- [ ] Local development environment set up with pytest

---

## Test Execution Checklist

After making changes:

- [ ] Individual test execution: All 6 tests pass independently
- [ ] Class test execution: `TestWeekDetection` all pass
- [ ] Class test execution: `TestEdgeCases` all pass
- [ ] File test execution: All `test_cfbd_client.py` tests pass
- [ ] Unit test execution: `pytest -m unit` passes
- [ ] Integration test execution: `pytest -m integration` passes
- [ ] No new warnings in pytest output
- [ ] CI/CD pipeline triggered and passes

---

## Notes

### Failing Tests Summary

| # | Test Name | Expected | Actual | Line |
|---|-----------|----------|--------|------|
| 1 | `test_get_current_week_with_completed_games` | week 8 | None | 66 |
| 2 | `test_get_current_week_week_1_only` | week 1 | None | 106 |
| 3 | `test_get_current_week_ignores_missing_week_field` | week 5 | None | 118 |
| 4 | `test_get_current_week_excludes_future_games_with_zero_scores` | week 5 | None | 132 |
| 5 | `test_get_current_week_epic_008_scenario` | week 9 | None | 148 |
| 6 | `test_get_current_week_with_mixed_data` | week 3 | None | 166 |

### Reference Links

- **Test File**: `tests/unit/test_cfbd_client.py`
- **Implementation**: `src/integrations/cfbd_client.py` lines 317-364
- **CI Workflow**: `.github/workflows/tests.yml`
- **API Docs**: https://api.collegefootballdata.com/api/docs/
- **GitHub Actions**: https://github.com/bdaileySNHU/cfb-rankings/actions

### Dependencies

- **Blocks**: CI/CD deployment, future CFBD client enhancements
- **Blocked by**: STORY-CFBD-01 (investigation must complete first)
- **Related**: Epic "Fix CFBD Client Test Failures"
