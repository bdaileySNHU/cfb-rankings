# EPIC-013: CI/CD Improvements

**Status:** 🚧 In Progress (Story 001 Complete)
**Priority:** Medium
**Created:** 2025-01-25
**Last Updated:** 2025-01-25

## Quick Summary

Comprehensive improvement of CI/CD pipeline, testing infrastructure, and documentation.

**Progress:** 1/4 stories complete (25%)
- ✅ Story 001: GitHub Actions Updated
- 📋 Story 002: Test Coverage (High Priority)
- 📋 Story 003: E2E Tests
- 📋 Story 004: Documentation

## Overview

Improve the continuous integration and deployment pipeline to use current best practices, fix deprecation warnings, increase test coverage, and create comprehensive documentation for contributors.

## Problem Statement

The current GitHub Actions workflow is using deprecated actions that will stop working in the future:
- `actions/upload-artifact@v3` is deprecated and scheduled for removal
- This causes build failures and warnings in the CI pipeline
- Need to update to v4 to ensure continued functionality

## Goals

1. Update all deprecated GitHub Actions to their latest versions
2. Ensure tests continue to run reliably
3. Improve test coverage and reporting
4. Document the CI/CD pipeline for future maintenance

## Stories

### Story 001: Update GitHub Actions Workflow
**Status:** ✅ Complete

**Description:**
Update the GitHub Actions workflow file to use current, non-deprecated action versions.

**Tasks:**
- [x] Update `actions/upload-artifact` from v3 to v4 (2 instances)
- [x] Update `actions/cache` from v3 to v4
- [x] Update `codecov/codecov-action` from v3 to v4
- [x] Verify `actions/checkout@v4` and `actions/setup-python@v4` already current
- [ ] Test that the workflow runs successfully (will verify on next push)
- [ ] Verify artifact uploads work correctly (will verify on next push)

**Acceptance Criteria:**
- All GitHub Actions use non-deprecated versions ✅
- Test workflow runs without errors or warnings (pending verification)
- Artifacts are uploaded successfully (pending verification)
- No deprecation notices in GitHub Actions logs (pending verification)

**Files modified:**
- `.github/workflows/tests.yml` - Updated all deprecated actions to v4

**Changes made:**
- Line 34: `actions/cache@v3` → `actions/cache@v4`
- Line 69: `codecov/codecov-action@v3` → `codecov/codecov-action@v4`
- Line 79: `actions/upload-artifact@v3` → `actions/upload-artifact@v4`
- Line 124: `actions/upload-artifact@v3` → `actions/upload-artifact@v4`

---

### Story 002: Improve Test Coverage
**Status:** 📋 To Do
**Priority:** High
**Estimated Effort:** 6-8 hours
**Assignee:** TBD

**Description:**
Review current test coverage and add comprehensive tests for critical paths that are missing coverage. This story was motivated by the recent camelCase bug in `update_games.py` that would have been caught with proper testing.

**User Story:**
As a developer, I want comprehensive test coverage so that I can catch bugs before they reach production and refactor with confidence.

**Tasks:**

**Phase 1: Assessment (1 hour)**
- [ ] Run `pytest --cov=. --cov-report=html --cov-report=term-missing` to generate coverage report
- [ ] Identify modules/functions with <50% coverage
- [ ] Document critical paths without tests in this story
- [ ] Prioritize gaps based on risk/impact

**Phase 2: Script Testing (2-3 hours)**
- [ ] Add tests for `scripts/update_games.py`:
  - [ ] Test CFBD API response parsing (camelCase → internal format)
  - [ ] Test null team name handling
  - [ ] Test duplicate game detection
  - [ ] Test FCS team creation logic
  - [ ] Mock CFBD API responses with realistic fixtures
- [ ] Add tests for `scripts/update_current_week.py`
- [ ] Add tests for `scripts/generate_predictions.py`
- [ ] Add tests for `scripts/backfill_historical_predictions.py`

**Phase 3: Core Business Logic (2-3 hours)**
- [ ] Add tests for `ranking_service.py`:
  - [ ] Test `generate_predictions()` with various scenarios
  - [ ] Test week filtering logic
  - [ ] Test next_week parameter behavior
  - [ ] Test prediction calculation accuracy
- [ ] Add tests for `cfbd_client.py`:
  - [ ] Test `get_current_week()` logic
  - [ ] Test `estimate_current_week()` calendar calculation
  - [ ] Test API response parsing for all endpoints
  - [ ] Add schema validation tests (ensure CFBD responses match expectations)
- [ ] Add tests for ELO calculation logic
- [ ] Add tests for SOS (Strength of Schedule) calculations

**Phase 4: API Endpoints (1-2 hours)**
- [ ] Add tests for `/api/predictions` endpoint with filters
- [ ] Add tests for `/api/rankings` endpoint
- [ ] Add tests for `/api/stats` endpoint
- [ ] Test error handling and edge cases

**Acceptance Criteria:**
- [ ] Test coverage increases from current baseline to >70%
- [ ] All scripts in `scripts/` directory have >80% coverage
- [ ] `ranking_service.py` has >85% coverage
- [ ] `cfbd_client.py` has >80% coverage
- [ ] All critical user-facing features have tests
- [ ] API integration points have comprehensive mocking
- [ ] Coverage report shows no critical gaps in business logic
- [ ] All tests pass in CI pipeline
- [ ] Test execution time remains under 2 minutes

**Files to Create/Modify:**
- `tests/test_update_games.py` (new)
- `tests/test_ranking_service.py` (enhance)
- `tests/test_cfbd_client.py` (new)
- `tests/test_scripts.py` (new)
- `tests/test_api_endpoints.py` (enhance)
- `tests/fixtures/cfbd_responses.json` (new - mock API responses)

**Technical Notes:**
- Use `pytest-mock` for mocking CFBD API calls
- Create realistic fixtures based on actual CFBD responses (see `scripts/debug_cfbd_response.py` output)
- Pay special attention to camelCase vs snake_case field mapping
- Test both success and failure scenarios
- Mock database interactions where appropriate

**Definition of Done:**
- [ ] All tasks completed
- [ ] Coverage report generated and reviewed
- [ ] All new tests passing locally and in CI
- [ ] Code review completed
- [ ] Documentation updated with testing guidelines

---

### Story 003: Add E2E Tests
**Status:** 📋 To Do
**Priority:** Medium
**Estimated Effort:** 4-6 hours
**Assignee:** TBD
**Depends On:** Story 002 (Test Coverage)

**Description:**
Add end-to-end tests that verify complete user workflows from data import through the frontend displaying predictions. These tests ensure all components work together correctly and catch integration issues.

**User Story:**
As a developer, I want E2E tests that validate complete user workflows so that I can confidently deploy knowing the system works end-to-end.

**Tasks:**

**Phase 1: Test Infrastructure (1 hour)**
- [ ] Set up E2E test environment with:
  - [ ] Isolated test database (SQLite in-memory or separate test DB)
  - [ ] FastAPI test client for backend
  - [ ] Playwright for frontend testing
  - [ ] Test fixtures for CFBD API responses
- [ ] Create test data fixtures:
  - [ ] Sample teams (10 FBS, 2 FCS)
  - [ ] Sample games for weeks 1-10 (2025 season)
  - [ ] Expected ELO ratings after processing
  - [ ] Expected predictions

**Phase 2: Backend Workflow Tests (2-3 hours)**
- [ ] **Test: Complete Season Import Workflow**
  - [ ] Initialize empty database
  - [ ] Import teams from fixtures
  - [ ] Import games for week 1
  - [ ] Process games and update ELO ratings
  - [ ] Verify rankings are calculated correctly
  - [ ] Generate predictions for week 2
  - [ ] Verify predictions match expected values

- [ ] **Test: Mid-Season Update Workflow**
  - [ ] Start with database at week 5
  - [ ] Import games for weeks 6-10 using `update_games.py` logic
  - [ ] Verify no duplicate games created
  - [ ] Verify FCS teams handled correctly
  - [ ] Generate predictions for new weeks

- [ ] **Test: Edge Cases**
  - [ ] FCS vs FBS game (verify exclusion from rankings)
  - [ ] Neutral site game (verify home field advantage removed)
  - [ ] 0-0 game detection (should not mark as played)
  - [ ] Missing team data handling
  - [ ] Week boundary conditions (week 0, week 16)

**Phase 3: Frontend E2E Tests (1-2 hours)**
- [ ] **Test: Rankings Page Load**
  - [ ] Start backend server with test data
  - [ ] Navigate to `/` (rankings page)
  - [ ] Verify stats card displays correct values
  - [ ] Verify top 25 rankings table populated
  - [ ] Verify prediction accuracy banner shows
  - [ ] Click on team → verify navigation to team page

- [ ] **Test: Predictions Display**
  - [ ] Navigate to rankings page
  - [ ] Verify "Next Week" predictions show by default
  - [ ] Select different week from dropdown
  - [ ] Verify predictions update
  - [ ] Verify prediction cards show correct data:
    - [ ] Team names
    - [ ] Predicted scores
    - [ ] Win probabilities
    - [ ] Game date/time

- [ ] **Test: Team Detail Page**
  - [ ] Navigate to team page (e.g., `/team.html?id=1`)
  - [ ] Verify team stats load
  - [ ] Verify schedule shows past and future games
  - [ ] Verify FCS badge only on completed FCS games

- [ ] **Test: Prediction Comparison Page**
  - [ ] Navigate to `/comparison.html`
  - [ ] Verify AP Poll comparison loads
  - [ ] Verify chart renders
  - [ ] Verify accuracy metrics display

**Phase 4: Deployment Script Tests (30 min)**
- [ ] Test database migration scripts
- [ ] Test `update_current_week.py` with various inputs
- [ ] Test `backfill_historical_predictions.py` on empty predictions table

**Acceptance Criteria:**
- [ ] E2E tests cover 4 main user workflows:
  1. Viewing rankings
  2. Viewing predictions
  3. Viewing team details
  4. Comparing with AP Poll
- [ ] Tests run successfully in CI environment (headless browser)
- [ ] Tests use isolated test database (no impact on dev DB)
- [ ] Tests complete in under 5 minutes
- [ ] All tests documented with clear descriptions
- [ ] Screenshots captured on failure for debugging
- [ ] Tests are maintainable and don't require manual intervention

**Files to Create/Modify:**
- `tests/e2e/test_rankings_workflow.py` (new)
- `tests/e2e/test_predictions_workflow.py` (new)
- `tests/e2e/test_frontend.py` (new)
- `tests/e2e/test_deployment_scripts.py` (new)
- `tests/fixtures/e2e_test_data.json` (new)
- `tests/conftest.py` (enhance with E2E fixtures)
- `.github/workflows/tests.yml` (already configured for E2E)

**Technical Notes:**
- Use `pytest-playwright` for frontend testing
- Run frontend tests in headless mode in CI
- Use `TestClient` from FastAPI for backend API testing
- Create database fixtures using `pytest` fixtures
- Mock CFBD API calls to avoid rate limits
- Use `@pytest.mark.e2e` marker for E2E tests
- E2E tests should be skipped in quick test runs (`pytest -m "not e2e"`)

**Test Data Requirements:**
```python
# Example test fixture structure
{
  "teams": [
    {"id": 1, "name": "Ohio State", "conference": "P5", ...},
    {"id": 2, "name": "Michigan", "conference": "P5", ...},
    # ... 8 more FBS teams
    {"id": 11, "name": "Montana", "conference": "FCS", "is_fcs": true}
  ],
  "games_week_1": [...],
  "expected_rankings_after_week_1": [...],
  "expected_predictions_week_2": [...]
}
```

**Definition of Done:**
- [ ] All E2E test scenarios pass locally
- [ ] All E2E tests pass in CI (headless mode)
- [ ] Test execution time under 5 minutes
- [ ] Screenshots captured on failure
- [ ] Test documentation complete
- [ ] Code review completed

---

### Story 004: CI/CD Documentation
**Status:** 📋 To Do
**Priority:** Medium
**Estimated Effort:** 2-4 hours
**Assignee:** TBD
**Depends On:** Stories 002 & 003 (so we can document actual practices)

**Description:**
Create comprehensive documentation for the CI/CD pipeline, testing strategy, and deployment process to enable new contributors and ensure consistent deployment practices.

**User Story:**
As a new contributor, I want clear documentation on testing and deployment so that I can contribute effectively and deploy with confidence.

**Tasks:**

**Phase 1: Testing Documentation (1 hour)**
- [ ] Create `docs/TESTING.md` with:
  - [ ] Overview of testing strategy (unit, integration, E2E)
  - [ ] How to run tests locally:
    ```bash
    # Run all tests
    pytest -v

    # Run unit tests only
    pytest -m unit -v

    # Run with coverage
    pytest --cov=. --cov-report=html --cov-report=term-missing

    # Run specific test file
    pytest tests/test_ranking_service.py -v

    # Skip slow E2E tests
    pytest -m "not e2e" -v
    ```
  - [ ] Test markers and how to use them
  - [ ] How to write new tests (examples)
  - [ ] Mocking strategy for CFBD API
  - [ ] Test fixtures and how to use them
  - [ ] Coverage requirements and how to check them

- [ ] Update `README.md` with Testing section:
  - [ ] Link to TESTING.md
  - [ ] Quick start for running tests
  - [ ] Badge showing current CI status
  - [ ] Badge showing code coverage percentage

**Phase 2: CI/CD Pipeline Documentation (1 hour)**
- [ ] Create `docs/CI-CD-PIPELINE.md` with:
  - [ ] **Overview** of GitHub Actions workflow
  - [ ] **Workflow Triggers:**
    - Push to main/develop branches
    - Pull requests to main/develop
    - Manual workflow dispatch
  - [ ] **Jobs breakdown:**
    - `test` job: Runs unit and integration tests
    - `e2e-test` job: Runs end-to-end tests
  - [ ] **Workflow steps explained:**
    - Checkout code
    - Set up Python
    - Cache dependencies
    - Install dependencies
    - Run tests with coverage
    - Upload artifacts
  - [ ] **How to view test results:**
    - Where to find GitHub Actions logs
    - How to download test artifacts
    - How to view coverage reports
  - [ ] **Workflow file location:** `.github/workflows/tests.yml`

**Phase 3: Deployment Documentation (1-1.5 hours)**
- [ ] Update `docs/EPIC-003-DEPLOYMENT.md` with:
  - [ ] Prerequisites checklist
  - [ ] Step-by-step deployment guide
  - [ ] Post-deployment verification steps
  - [ ] Common deployment scenarios:
    - [ ] Frontend-only changes (no backend restart needed)
    - [ ] Backend changes (requires systemctl restart)
    - [ ] Database migrations
    - [ ] Full re-import of data
  - [ ] Deployment scripts reference:
    - `import_real_data.py` - Full database reset and import
    - `update_games.py` - Import future games without reset
    - `update_current_week.py` - Update current week number
    - `generate_predictions.py` - Generate predictions for upcoming games
    - `backfill_historical_predictions.py` - Backfill predictions for past games
  - [ ] Migration scripts and when to use them
  - [ ] Rollback procedures

**Phase 4: Troubleshooting Guide (30 min - 1 hour)**
- [ ] Create `docs/TROUBLESHOOTING.md` with common issues:

  **CI/CD Issues:**
  - [ ] "GitHub Actions workflow failing" → Check deprecation warnings, review logs
  - [ ] "Tests passing locally but failing in CI" → Check environment differences, Python version
  - [ ] "Coverage upload failing" → Check Codecov token, artifact upload version
  - [ ] "E2E tests timing out" → Increase timeout, check server startup

  **Testing Issues:**
  - [ ] "Import errors when running tests" → Check PYTHONPATH, virtual environment
  - [ ] "Database errors in tests" → Check test database isolation
  - [ ] "Mock not working" → Check mock patch path
  - [ ] "Coverage not showing all files" → Check .coveragerc configuration

  **Deployment Issues:**
  - [ ] "ModuleNotFoundError on server" → Use `venv/bin/python3` instead of system Python
  - [ ] "Predictions not showing" → Run generate_predictions.py
  - [ ] "Week showing incorrectly" → Run update_current_week.py
  - [ ] "Games not importing" → Check CFBD API field names (camelCase vs snake_case)
  - [ ] "Database migration failed" → Review migration script, check permissions
  - [ ] "Frontend changes not appearing" → Clear browser cache, check deployment
  - [ ] "502 Bad Gateway" → Check if backend service is running, restart systemctl

**Phase 5: README Enhancements (30 min)**
- [ ] Add comprehensive README sections:
  - [ ] **Quick Start** - Get up and running in 5 minutes
  - [ ] **Development Workflow** - How to contribute
  - [ ] **Testing** - Link to TESTING.md with quick commands
  - [ ] **CI/CD** - Link to CI-CD-PIPELINE.md
  - [ ] **Deployment** - Link to EPIC-003-DEPLOYMENT.md
  - [ ] **Troubleshooting** - Link to TROUBLESHOOTING.md
  - [ ] **Project Structure** - Explanation of directory layout
  - [ ] **Scripts** - Quick reference for all scripts in `scripts/`

**Acceptance Criteria:**
- [ ] `docs/TESTING.md` created with comprehensive testing guide
- [ ] `docs/CI-CD-PIPELINE.md` created explaining GitHub Actions workflow
- [ ] `docs/TROUBLESHOOTING.md` created with common issues and solutions
- [ ] `docs/EPIC-003-DEPLOYMENT.md` updated with all recent learnings
- [ ] `README.md` updated with links to all documentation
- [ ] All code examples in docs are tested and working
- [ ] Documentation reviewed by another developer
- [ ] New contributor can successfully:
  - [ ] Run tests locally
  - [ ] Understand CI pipeline
  - [ ] Deploy changes to production
  - [ ] Troubleshoot common issues

**Files to Create/Modify:**
- `docs/TESTING.md` (new)
- `docs/CI-CD-PIPELINE.md` (new)
- `docs/TROUBLESHOOTING.md` (new)
- `docs/EPIC-003-DEPLOYMENT.md` (update)
- `README.md` (update)
- `.coveragerc` (create if doesn't exist - configure coverage tool)

**Documentation Structure:**
```
docs/
├── TESTING.md                    # How to test
├── CI-CD-PIPELINE.md            # CI/CD workflow
├── TROUBLESHOOTING.md           # Common issues
├── EPIC-003-DEPLOYMENT.md       # Deployment guide
├── EPIC-011-FCS-BADGE-FIX.md   # Feature documentation
├── EPIC-012-CONFERENCE-DISPLAY.md
└── EPIC-013-CI-CD-IMPROVEMENTS.md
```

**README.md Structure:**
```markdown
# College Football Rankings

## Quick Start
## Features
## Development
  - Testing (link to TESTING.md)
  - CI/CD (link to CI-CD-PIPELINE.md)
## Deployment (link to EPIC-003-DEPLOYMENT.md)
## Project Structure
## Scripts Reference
## Troubleshooting (link to TROUBLESHOOTING.md)
## Contributing
```

**Technical Notes:**
- Use clear, actionable language
- Include code examples that can be copy-pasted
- Add links between related docs
- Keep docs up-to-date as code changes
- Use consistent formatting (Markdown)
- Include diagrams where helpful (workflow diagrams, architecture)

**Definition of Done:**
- [ ] All documentation files created/updated
- [ ] All code examples tested and working
- [ ] Documentation peer-reviewed
- [ ] README updated with all links
- [ ] New contributor successfully onboarded using docs (test with someone unfamiliar with project)
- [ ] Documentation merged to main branch

---

## Technical Details

### Current Issue
The GitHub Actions workflow uses `actions/upload-artifact@v3`, which shows this deprecation warning:

```
This request has been automatically failed because it uses a deprecated version of
`actions/upload-artifact: v3`. Learn more:
https://github.blog/changelog/2024-04-16-deprecation-notice-v3-of-the-artifact-actions/
```

### Solution
Update `.github/workflows/tests.yml` to use v4:

```yaml
# Before
- uses: actions/upload-artifact@v3

# After
- uses: actions/upload-artifact@v4
```

Note: v4 has some breaking changes, so we need to review the upload/download artifact syntax.

### Related Commits
- bbce678: Add script to debug CFBD API response structure
- d96aed4: Fix update_games.py to use correct CFBD API field names

### Testing Strategy

**Unit Tests:**
- Test individual functions (prediction calculation, ELO updates, etc.)
- Mock external API calls
- Fast execution

**Integration Tests:**
- Test database interactions
- Test API endpoints
- Use test database

**E2E Tests:**
- Test complete workflows
- Use fixtures for reproducibility
- Slower but comprehensive

## Dependencies

- None (self-contained improvements)

## Success Metrics

- ✅ Zero deprecation warnings in GitHub Actions
- ✅ Test coverage above 70%
- ✅ All tests passing consistently
- ✅ CI pipeline runs in under 5 minutes
- ✅ Documentation complete and clear

## Timeline

### Completed
- **Story 001 (GitHub Actions update):** ✅ Complete - 1 hour (2025-01-25)

### Remaining
- **Story 002 (Test coverage):** 6-8 hours - **HIGH PRIORITY**
  - Would have caught the camelCase bug
  - Foundation for confident refactoring
- **Story 003 (E2E tests):** 4-6 hours - **MEDIUM PRIORITY**
  - Depends on Story 002
  - Validates end-to-end workflows
- **Story 004 (Documentation):** 2-4 hours - **MEDIUM PRIORITY**
  - Depends on Stories 002 & 003
  - Captures learnings for future contributors

**Total estimated time:** 12-18 hours remaining (1 hour completed)

## Notes

- Story 001 should be prioritized as it's causing current build failures
- The CFBD API field naming issue (camelCase vs snake_case) exposed a gap in our testing - we should add tests to catch this type of issue earlier
- Consider adding a test that validates CFBD API responses match our expected schema

## Future Enhancements

- Add automated deployment on merge to main
- Add performance testing for large datasets
- Add integration tests with actual CFBD API (rate-limited)
- Add visual regression testing for frontend
