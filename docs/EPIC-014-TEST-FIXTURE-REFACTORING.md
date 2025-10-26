# EPIC-014: Test Fixture Refactoring

**Status**: Not Started
**Priority**: Medium
**Estimated Effort**: 2-3 days
**Dependencies**: None
**Related EPIC**: EPIC-013 (CI/CD Improvements)

## Overview

Refactor admin endpoint and weekly update tests to use proper test fixtures instead of accessing the production database. This will enable these tests to run in CI/CD and improve test isolation and reliability.

## Problem Statement

Currently, 55 tests in `test_admin_endpoints.py` and `test_weekly_update.py` are skipped in CI because they:
- Use `SessionLocal()` to create production database connections
- Access tables (api_usage, update_task) that don't exist in CI environment
- Create their own test client without overriding database dependencies
- Make the test suite incomplete and reduce confidence in deployments

## Goals

1. **Enable all tests to run in CI** - 100% of tests should run in automated pipelines
2. **Improve test isolation** - Each test should use in-memory database with clean state
3. **Maintain test coverage** - Ensure refactored tests still validate original behavior
4. **Document patterns** - Create reusable patterns for future test development

## Non-Goals

- Rewriting test logic or changing what's being tested
- Adding new test coverage (separate effort)
- Modifying production code behavior

## Success Criteria

- [ ] All 55 skipped tests now run successfully in CI
- [ ] Tests use `test_db` and `test_client` fixtures from conftest.py
- [ ] No tests use `SessionLocal()` or create production database connections
- [ ] All tests pass locally and in CI
- [ ] Test execution time remains under 5 minutes for full suite
- [ ] Documentation updated with test fixture usage patterns

---

## Stories

### Story 001: Refactor Admin Endpoint Tests (test_admin_endpoints.py)

**Story Points**: 5
**Priority**: High

#### Description
Refactor all 17 admin endpoint tests to use proper test fixtures instead of `SessionLocal()`.

#### Acceptance Criteria
- [ ] Replace `client = TestClient(app)` with `test_client` fixture parameter
- [ ] Replace all `SessionLocal()` calls with `test_db` fixture parameter
- [ ] Remove `pytestmark = pytest.mark.skip()` line
- [ ] All 17 tests pass with test fixtures
- [ ] Tests validate same behavior as original tests

#### Technical Details

**Tests to refactor** (17 total):
1. TestUsageDashboardEndpoint (5 tests)
   - test_usage_dashboard_returns_200
   - test_usage_dashboard_has_required_fields
   - test_usage_dashboard_current_month_fields
   - test_usage_dashboard_with_month_parameter
   - test_usage_dashboard_calculates_projections

2. TestConfigEndpoints (5 tests)
   - test_get_config_returns_200
   - test_get_config_has_all_fields
   - test_get_config_default_values
   - test_put_config_updates_limit
   - test_put_config_returns_updated_config

3. TestTriggerUpdateEndpoint (5 tests)
   - test_trigger_update_fails_in_off_season
   - test_trigger_update_fails_with_no_week
   - test_trigger_update_fails_at_90_percent_usage
   - test_trigger_update_succeeds_with_valid_conditions
   - test_trigger_update_creates_task_record

4. TestUpdateStatusEndpoint (3 tests)
   - test_update_status_404_for_unknown_task
   - test_update_status_returns_task_info
   - test_update_status_handles_null_result

5. TestUpdateTaskModel (2 tests)
   - test_create_update_task
   - test_update_task_status

6. TestAPIIntegration (2 tests)
   - test_full_dashboard_workflow
   - test_trigger_and_check_status_workflow

**Refactoring pattern**:
```python
# Before
class TestUsageDashboardEndpoint:
    def test_usage_dashboard_returns_200(self):
        response = client.get("/api/admin/usage-dashboard")
        assert response.status_code == 200

# After
class TestUsageDashboardEndpoint:
    def test_usage_dashboard_returns_200(self, test_client):
        response = test_client.get("/api/admin/usage-dashboard")
        assert response.status_code == 200
```

**Database access pattern**:
```python
# Before
def test_update_status_returns_task_info(self):
    db = SessionLocal()
    task = UpdateTask(...)
    db.add(task)
    db.commit()
    db.close()

# After
def test_update_status_returns_task_info(self, test_db, test_client):
    task = UpdateTask(...)
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)
```

#### Implementation Steps
1. Remove module-level `client = TestClient(app)` and imports
2. Update each test method signature to accept `test_client` parameter
3. Find tests with database access and add `test_db` parameter
4. Replace `db = SessionLocal()` with `test_db` usage
5. Remove `db.close()` calls (test fixture handles cleanup)
6. Remove `try/finally` blocks around database operations
7. Run tests locally to verify: `pytest tests/test_admin_endpoints.py -v`
8. Remove skip marker once all tests pass

#### Testing
```bash
# Run just admin endpoint tests
pytest tests/test_admin_endpoints.py -v

# Verify no SessionLocal usage
grep -n "SessionLocal" tests/test_admin_endpoints.py

# Run in CI simulation (clean environment)
docker run -v $(pwd):/app python:3.11 sh -c "cd /app && pip install -r requirements.txt && pytest tests/test_admin_endpoints.py"
```

---

### Story 002: Refactor Weekly Update Tests (test_weekly_update.py)

**Story Points**: 8
**Priority**: High

#### Description
Refactor weekly update script tests to mock database access instead of calling production database functions.

#### Acceptance Criteria
- [ ] Database calls in `weekly_update.py` functions are mocked
- [ ] Tests validate function behavior without requiring database
- [ ] Remove `pytestmark = pytest.mark.skip()` line
- [ ] All tests pass with mocked dependencies
- [ ] Test coverage remains at same level

#### Technical Details

**Tests to refactor** (38 total in file):
- TestIsActiveSeason (6 tests) - ✅ Already work, no database
- TestValidateWeekNumber (3 tests) - ✅ Already work, no database
- TestCheckAPIUsage (5 tests) - ⚠️ Need database mocking
- TestGetCurrentWeekWrapper (3 tests) - ⚠️ Need database mocking
- TestMainFunction (5 tests) - ⚠️ Need comprehensive mocking

**Challenge**: These tests call functions in `weekly_update.py` that internally create database sessions:

```python
# weekly_update.py - current implementation
def check_api_usage() -> bool:
    """Check if API usage is below 90%"""
    db = SessionLocal()  # ❌ Creates production connection
    try:
        # Query api_usage table
        count = db.query(APIUsage).filter(...).count()
        return usage_percent < 90.0
    finally:
        db.close()
```

**Solution approaches**:

**Option A: Mock database at module level** (Recommended)
```python
# In test file
@patch('weekly_update.SessionLocal')
def test_check_api_usage_below_threshold(self, mock_session):
    # Create mock database session
    mock_db = MagicMock()
    mock_session.return_value = mock_db

    # Mock query results
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 500
    mock_db.query.return_value = mock_query

    # Test function
    result = weekly_update.check_api_usage()
    assert result is True
```

**Option B: Refactor weekly_update.py to accept db parameter** (Better long-term)
```python
# weekly_update.py - refactored
def check_api_usage(db: Session = None) -> bool:
    """Check if API usage is below 90%"""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False

    try:
        count = db.query(APIUsage).filter(...).count()
        return usage_percent < 90.0
    finally:
        if close_db:
            db.close()

# In test
def test_check_api_usage_below_threshold(self, test_db):
    # Seed test data
    test_db.add(APIUsage(...))
    test_db.commit()

    # Test with test database
    result = weekly_update.check_api_usage(test_db)
    assert result is True
```

#### Implementation Steps

**Phase 1: Tests that don't need database** (already working)
1. Verify TestIsActiveSeason tests run without issues
2. Verify TestValidateWeekNumber tests run without issues

**Phase 2: Mock database access**
1. For each test calling `check_api_usage()`:
   - Add `@patch('weekly_update.SessionLocal')` decorator
   - Mock database query chain
   - Verify function logic with mocked data

2. For each test calling `get_current_week_wrapper()`:
   - Add `@patch('weekly_update.SessionLocal')` decorator
   - Mock Season table query
   - Verify week calculation logic

3. For TestMainFunction tests:
   - Mock all database-dependent functions
   - Mock subprocess calls to import_real_data.py
   - Verify orchestration logic

**Phase 3: Remove skip marker**
1. Run all tests: `pytest tests/test_weekly_update.py -v`
2. Verify 38/38 tests pass
3. Remove `pytestmark = pytest.mark.skip()` line
4. Run again to confirm

#### Testing
```bash
# Run weekly update tests
pytest tests/test_weekly_update.py -v

# Verify no production database access
pytest tests/test_weekly_update.py -v --tb=short 2>&1 | grep -i "OperationalError"

# Should return no results when working correctly
```

---

### Story 003: Create Test Fixture Documentation

**Story Points**: 2
**Priority**: Medium

#### Description
Document test fixture patterns and best practices for future test development.

#### Acceptance Criteria
- [ ] Documentation added to docs/TESTING.md
- [ ] Examples show how to use test_db and test_client fixtures
- [ ] Anti-patterns documented (what NOT to do)
- [ ] Checklist for test review included

#### Content Outline

**Add to docs/TESTING.md**:

```markdown
## Test Fixture Best Practices

### Using Test Database (test_db)

The `test_db` fixture provides an in-memory SQLite database that is:
- Created fresh for each test function
- Automatically cleaned up after test
- Isolated from production database
- Fast (in-memory, no disk I/O)

**Example**:
```python
def test_create_team(test_db):
    """Example of using test_db fixture"""
    team = Team(name="Test Team", elo_rating=1500.0)
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    assert team.id is not None
    assert team.name == "Test Team"
```

**❌ Don't do this**:
```python
# WRONG - uses production database
def test_create_team():
    db = SessionLocal()  # ❌ Production database
    team = Team(...)
    db.add(team)
    db.commit()
    db.close()
```

### Using Test Client (test_client)

The `test_client` fixture provides a FastAPI TestClient that:
- Uses test_db instead of production database
- Doesn't require running server
- Makes actual HTTP requests to endpoints
- Automatically handles request/response serialization

**Example**:
```python
def test_get_rankings(test_client, test_db):
    """Example of using test_client fixture"""
    # Seed test data
    team = Team(name="Alabama", elo_rating=1800.0)
    test_db.add(team)
    test_db.commit()

    # Make request
    response = test_client.get("/api/rankings")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alabama"
```

**❌ Don't do this**:
```python
# WRONG - creates own client without database override
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)  # ❌ Uses production database

def test_get_rankings():
    response = client.get("/api/rankings")  # ❌ Queries production DB
```

### Test Review Checklist

Before merging test code, verify:

- [ ] No imports of `SessionLocal` from database module
- [ ] No `TestClient(app)` without database override
- [ ] All test functions use `test_db` and/or `test_client` fixtures
- [ ] No hardcoded file paths (use Path or fixtures)
- [ ] Tests are isolated (don't depend on order)
- [ ] Mocks are used for external services (CFBD API, etc)
- [ ] Tests clean up after themselves (fixtures handle this)
```

---

### Story 004: Update CI/CD Pipeline Documentation

**Story Points**: 1
**Priority**: Low

#### Description
Update CI/CD documentation to reflect that all tests now run in pipeline.

#### Acceptance Criteria
- [ ] docs/CI-CD-PIPELINE.md updated with correct test counts
- [ ] README.md test badge updated
- [ ] Known issues section removed (if all tests pass)

#### Changes Needed

**docs/CI-CD-PIPELINE.md**:
```markdown
## Test Execution

The CI/CD pipeline runs the complete test suite:

- **538 total tests** (was 483 with 55 skipped)
- **Unit tests**: ~220 tests
- **Integration tests**: ~200 tests
- **E2E tests**: ~118 tests

All tests use proper test fixtures and in-memory databases.
No tests require production database access.
```

**README.md**:
```markdown
## Testing

![Tests](https://github.com/bdaileySNHU/cfb-rankings/actions/workflows/tests.yml/badge.svg)

### Comprehensive Test Suite

**538 tests** covering all functionality with automated CI/CD testing:

- ✅ **220 unit tests** - Fast, isolated component tests
- ✅ **200 integration tests** - API endpoints with database
- ✅ **118 E2E tests** - Complete user workflows with browser automation

All tests run in CI pipeline with proper test fixtures and isolation.
```

---

## Implementation Plan

### Phase 1: Story 001 - Admin Endpoint Tests (Week 1)
- **Days 1-2**: Refactor TestUsageDashboardEndpoint and TestConfigEndpoints
- **Day 3**: Refactor TestTriggerUpdateEndpoint
- **Day 4**: Refactor TestUpdateStatusEndpoint and TestUpdateTaskModel
- **Day 5**: Refactor TestAPIIntegration and verify all pass

### Phase 2: Story 002 - Weekly Update Tests (Week 2)
- **Days 1-2**: Implement database mocking for check_api_usage tests
- **Day 3**: Implement database mocking for get_current_week_wrapper tests
- **Days 4-5**: Implement comprehensive mocking for main function tests

### Phase 3: Documentation (Week 2)
- **Day 5**: Complete Stories 003 and 004

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Tests break due to refactoring | High | Medium | Run tests locally after each change; keep changes small |
| Mocking is too complex | Medium | Medium | Consider Option B (refactor weekly_update.py) if mocking becomes unwieldy |
| CI still fails after refactoring | High | Low | Test in Docker locally before pushing; verify test isolation |
| Tests no longer validate correct behavior | High | Low | Keep test assertions identical; review with original test author |

## Testing Strategy

### Before starting work
```bash
# Baseline - verify skipped tests still pass locally
pytest tests/test_admin_endpoints.py tests/test_weekly_update.py -v
```

### During development
```bash
# Run after each refactored test class
pytest tests/test_admin_endpoints.py::TestUsageDashboardEndpoint -v

# Verify no SessionLocal usage
grep -rn "SessionLocal" tests/test_*.py
```

### Before committing
```bash
# Run full suite
pytest -v

# Verify CI simulation
pytest tests/test_admin_endpoints.py tests/test_weekly_update.py -v --tb=short
```

## Success Metrics

- **Test Pass Rate**: 100% (538/538 tests passing in CI)
- **Test Execution Time**: < 5 minutes for full suite
- **Code Coverage**: Maintained or improved from current
- **CI Build Success Rate**: > 95% (no flaky tests)

## Future Work

After completing this EPIC, consider:
- **EPIC-015**: Increase test coverage for edge cases
- **EPIC-016**: Add performance regression tests
- **EPIC-017**: Implement mutation testing to verify test quality
- Refactor `weekly_update.py` to dependency injection pattern for easier testing
- Create shared test fixtures for common scenarios (factory patterns)

---

## Notes

- Original tests are in git history if we need to reference behavior
- Tests are skipped with clear documentation, so they can be run locally for debugging
- Refactoring should preserve exact test behavior, just change how database is accessed
- Consider this EPIC a prerequisite for production deployment confidence

**Created**: 2025-10-26
**Last Updated**: 2025-10-26
**Owner**: Development Team
