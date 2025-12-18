---
name: "Story 2: Fix Test Mocks to Match CFBD API Schema"
about: Update test mocks to use correct CFBD API field names and restore CI/CD to green
title: '[STORY-CFBD-02] Fix Test Mocks to Match Actual CFBD API Response Schema'
labels: 'bug, tests, priority-high, epic-cfbd-test-failures'
assignees: ''
---

## 📋 Story Overview

**Epic**: Fix CFBD Client Test Failures
**Story ID**: STORY-CFBD-02
**Estimated Effort**: 2-4 hours
**Priority**: High
**Status**: ⚠️ Blocked by STORY-CFBD-01

---

## 🎯 User Story

**As a** developer maintaining the CFBD client test suite
**I want** test mocks to accurately reflect the real CFBD API response schema
**So that** our unit tests validate actual production behavior and the CI/CD pipeline returns to green status

---

## 📝 Context

### Problem
Six tests are failing in `test_cfbd_client.py` because test mocks use incorrect field names that don't match the real CFBD API schema (as determined in STORY-CFBD-01).

### Failing Tests

| # | Test Name | Expected | Actual | Line |
|---|-----------|----------|--------|------|
| 1 | `test_get_current_week_with_completed_games` | week 8 | None | 66 |
| 2 | `test_get_current_week_week_1_only` | week 1 | None | 106 |
| 3 | `test_get_current_week_ignores_missing_week_field` | week 5 | None | 118 |
| 4 | `test_get_current_week_excludes_future_games_with_zero_scores` | week 5 | None | 132 |
| 5 | `test_get_current_week_epic_008_scenario` | week 9 | None | 148 |
| 6 | `test_get_current_week_with_mixed_data` | week 3 | None | 166 |

### Goal
Update test mocks (and possibly implementation) to use correct API field names, making all tests pass and restoring CI/CD to green.

### Integration Points
- Test suite: `tests/unit/test_cfbd_client.py`
- Implementation: `src/integrations/cfbd_client.py` (lines 317-364)
- CI/CD: `.github/workflows/tests.yml`

---

## ✅ Acceptance Criteria

### Functional Requirements

- [ ] **Update all test mock data** to use correct field names (from STORY-CFBD-01):
  - [ ] Fix `test_get_current_week_with_completed_games` (line 66)
  - [ ] Fix `test_get_current_week_week_1_only` (line 106)
  - [ ] Fix `test_get_current_week_ignores_missing_week_field` (line 118)
  - [ ] Fix `test_get_current_week_excludes_future_games_with_zero_scores` (line 132)
  - [ ] Fix `test_get_current_week_epic_008_scenario` (line 148)
  - [ ] Fix `test_get_current_week_with_mixed_data` (line 166)

- [ ] **All 6 failing tests now pass**:
  - [ ] `test_get_current_week_with_completed_games` → returns 8
  - [ ] `test_get_current_week_week_1_only` → returns 1
  - [ ] `test_get_current_week_ignores_missing_week_field` → returns 5
  - [ ] `test_get_current_week_excludes_future_games_with_zero_scores` → returns 5
  - [ ] `test_get_current_week_epic_008_scenario` → returns 9
  - [ ] `test_get_current_week_with_mixed_data` → returns 3

- [ ] **Update implementation if needed** (only if STORY-CFBD-01 reveals implementation is incorrect):
  - [ ] Fix field access in `get_current_week()` method
  - [ ] Update field names in lines 346-347, 356 of `cfbd_client.py`
  - [ ] Maintain compatibility with existing API integration

### Integration Requirements

- [ ] **No regression in existing tests**:
  - [ ] All `TestSeasonDetection` tests still pass
  - [ ] All `TestWeekEstimation` tests still pass
  - [ ] All other `test_cfbd_client.py` tests still pass

- [ ] **Follow existing test patterns**:
  - [ ] Mock structure matches existing format
  - [ ] Test documentation follows conventions
  - [ ] No changes to test organization

- [ ] **CI/CD pipeline returns to green**:
  - [ ] Unit tests pass: `pytest -m unit -v --tb=short`
  - [ ] Integration tests pass: `pytest -m integration -v --tb=short`
  - [ ] Full test suite passes: `pytest -m "not e2e"`
  - [ ] GitHub Actions workflow completes successfully

### Quality Requirements

- [ ] **Add documentation** explaining API schema:
  - [ ] Module-level comment or docstring in test file
  - [ ] Document field naming convention
  - [ ] Reference STORY-CFBD-01 findings
  - [ ] Include API documentation link

- [ ] **Verify locally before pushing**:
  - [ ] Run failing tests individually
  - [ ] Run full CFBD client test suite
  - [ ] Check for warnings or deprecations

- [ ] **No unrelated changes**:
  - [ ] Changes limited to test mocks (and possibly implementation)
  - [ ] No refactoring or cleanup
  - [ ] No structural changes to tests

---

## 🔧 Implementation Guide

### Step 1: Review STORY-CFBD-01 Findings

- [ ] Read investigation results from STORY-CFBD-01
- [ ] Confirm correct field naming convention
- [ ] Note any special cases (postseason, missing fields)

### Step 2: Update Test Mocks

**Example transformation** (if API uses camelCase):

**Before (INCORRECT):**
```python
mock_games = [
    {"week": 1, "home_points": 35, "away_points": 28},  # snake_case ❌
    {"week": 2, "home_points": 21, "away_points": 24},
]
```

**After (CORRECT):**
```python
mock_games = [
    {"week": 1, "homePoints": 35, "awayPoints": 28},  # camelCase ✅
    {"week": 2, "homePoints": 21, "awayPoints": 24},
]
```

### Step 3: Update Implementation (if needed)

**Only if STORY-CFBD-01 reveals implementation is wrong:**

```python
# Current (lines 346-347):
home_points = game.get("homePoints")
away_points = game.get("awayPoints")

# Update to (example if snake_case is correct):
home_points = game.get("home_points")
away_points = game.get("away_points")
```

### Step 4: Add Documentation

```python
"""
CFBD API Response Schema (verified 2025-12-16, STORY-CFBD-01):
- Score fields use camelCase: homePoints, awayPoints
- Week field uses lowercase: week
- Reference: https://api.collegefootballdata.com/api/docs/
- See: docs/stories/story-cfbd-01-investigate-api-schema.md
"""
```

### Step 5: Run Tests

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

---

## ✅ Test Execution Checklist

### Individual Test Verification

- [ ] `test_get_current_week_with_completed_games` passes
- [ ] `test_get_current_week_week_1_only` passes
- [ ] `test_get_current_week_ignores_missing_week_field` passes
- [ ] `test_get_current_week_excludes_future_games_with_zero_scores` passes
- [ ] `test_get_current_week_epic_008_scenario` passes
- [ ] `test_get_current_week_with_mixed_data` passes

### Suite Verification

- [ ] All `TestWeekDetection` tests pass
- [ ] All `TestEdgeCases` tests pass
- [ ] All `test_cfbd_client.py` tests pass
- [ ] `pytest -m unit` passes (no regressions)
- [ ] `pytest -m integration` passes
- [ ] No new warnings in pytest output

### CI/CD Verification

- [ ] Changes committed with clear message
- [ ] GitHub Actions workflow triggered
- [ ] CI/CD pipeline shows green status
- [ ] All workflow steps complete successfully

---

## 📊 Definition of Done

- [ ] STORY-CFBD-01 investigation results reviewed
- [ ] All 6 test mocks updated with correct field names
- [ ] Implementation field access updated (if needed)
- [ ] All 6 previously failing tests now pass
- [ ] Full CFBD client test suite passes (no regressions)
- [ ] Unit test suite passes: `pytest -m unit -v`
- [ ] Integration test suite passes: `pytest -m integration -v`
- [ ] API schema documented in test file comments
- [ ] Changes committed with message referencing epic
- [ ] CI/CD pipeline shows green on GitHub Actions
- [ ] No new warnings or errors introduced

---

## 🚨 Pre-Implementation Checklist

**Before starting this story, verify:**

- [ ] STORY-CFBD-01 is complete with documented findings
- [ ] Correct API field naming is confirmed
- [ ] Decision made: update tests only, or tests + implementation
- [ ] Sample API response available for reference
- [ ] Local development environment set up with pytest

---

## ⚠️ Risk Mitigation

### Primary Risk
Changing field names incorrectly could cause tests to pass while production fails with real API.

### Mitigation
- [ ] STORY-CFBD-01 verified actual API schema before changes
- [ ] Cross-referenced with official API documentation
- [ ] Reviewed production logs to verify current behavior
- [ ] Running full test suite, not just the 6 failing tests

### Rollback Plan
```bash
# Simple git revert if issues arise
git revert <commit-hash>

# Or manual revert
git checkout HEAD~1 -- tests/unit/test_cfbd_client.py
```

---

## 🔗 Related Links

- **Epic**: Fix CFBD Client Test Failures ([docs/epic-fix-cfbd-test-failures.md](../../docs/epic-fix-cfbd-test-failures.md))
- **Story Doc**: [story-cfbd-02-fix-test-mocks.md](../../docs/stories/story-cfbd-02-fix-test-mocks.md)
- **Depends On**: STORY-CFBD-01 (Investigation)
- **Test File**: `tests/unit/test_cfbd_client.py`
- **Implementation**: `src/integrations/cfbd_client.py` (lines 317-364)
- **CI Workflow**: `.github/workflows/tests.yml`
- **API Docs**: https://api.collegefootballdata.com/api/docs/
- **GitHub Actions**: https://github.com/bdaileySNHU/cfb-rankings/actions

---

## 💡 Notes

### Files to Modify

**Primary:**
- `tests/unit/test_cfbd_client.py` (test mocks)

**Possibly:**
- `src/integrations/cfbd_client.py` (if implementation is wrong)

### Commit Message Template

```
Fix CFBD client test failures by correcting API field names

- Update test mocks to use correct CFBD API schema (camelCase/snake_case)
- Fix field access in get_current_week() if needed
- Add API schema documentation to test file
- All 6 failing tests now pass
- CI/CD pipeline restored to green status

Fixes: STORY-CFBD-02
Epic: Fix CFBD Client Test Failures
Related: STORY-CFBD-01
```

### Success Metrics

- ✅ 6 tests changed from FAILED → PASSED
- ✅ 0 regressions (all other tests still pass)
- ✅ CI/CD status: ❌ → ✅
- ✅ Test execution time: no significant change
