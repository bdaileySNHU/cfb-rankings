# EPIC-013: CI/CD Improvements

**Status:** 📋 Planned
**Priority:** Medium
**Created:** 2025-01-25

## Overview

Improve the continuous integration and deployment pipeline to use current best practices and fix deprecation warnings.

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
**Status:** 📋 To Do

**Description:**
Update the GitHub Actions workflow file to use current, non-deprecated action versions.

**Tasks:**
- [ ] Update `actions/upload-artifact` from v3 to v4
- [ ] Update `actions/checkout` to latest version if needed
- [ ] Update `actions/setup-python` to latest version if needed
- [ ] Test that the workflow runs successfully
- [ ] Verify artifact uploads work correctly

**Acceptance Criteria:**
- All GitHub Actions use non-deprecated versions
- Test workflow runs without errors or warnings
- Artifacts are uploaded successfully (if applicable)
- No deprecation notices in GitHub Actions logs

**Files to modify:**
- `.github/workflows/tests.yml` (or similar CI workflow file)

---

### Story 002: Improve Test Coverage
**Status:** 📋 To Do

**Description:**
Review current test coverage and add tests for critical paths that are missing coverage.

**Tasks:**
- [ ] Run coverage report to identify gaps
- [ ] Add tests for `update_games.py` script
- [ ] Add tests for CFBD API field mapping (camelCase vs snake_case)
- [ ] Add tests for prediction generation logic
- [ ] Add tests for week detection logic

**Acceptance Criteria:**
- Test coverage increases by at least 10%
- All critical user-facing features have tests
- API integration points have tests

---

### Story 003: Add E2E Tests
**Status:** 📋 To Do

**Description:**
Add end-to-end tests that verify the entire workflow from data import through prediction generation.

**Tasks:**
- [ ] Create test fixture data for a sample week of games
- [ ] Test full workflow: import → ranking calculation → prediction generation
- [ ] Test edge cases (FCS teams, neutral site games, etc.)
- [ ] Add tests for deployment scripts

**Acceptance Criteria:**
- E2E tests cover main user workflows
- Tests can run in CI environment
- Tests are documented and maintainable

---

### Story 004: CI/CD Documentation
**Status:** 📋 To Do

**Description:**
Document the CI/CD pipeline, testing strategy, and deployment process.

**Tasks:**
- [ ] Document GitHub Actions workflow
- [ ] Document test running locally
- [ ] Document deployment process
- [ ] Create troubleshooting guide for common CI issues

**Acceptance Criteria:**
- README has section on testing and CI
- New contributors can understand how to run tests
- Deployment process is fully documented

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

- **Story 001 (GitHub Actions update):** 1 hour - CRITICAL (fix failing builds)
- **Story 002 (Test coverage):** 4-8 hours
- **Story 003 (E2E tests):** 4-8 hours
- **Story 004 (Documentation):** 2-4 hours

**Total estimated time:** 11-21 hours

## Notes

- Story 001 should be prioritized as it's causing current build failures
- The CFBD API field naming issue (camelCase vs snake_case) exposed a gap in our testing - we should add tests to catch this type of issue earlier
- Consider adding a test that validates CFBD API responses match our expected schema

## Future Enhancements

- Add automated deployment on merge to main
- Add performance testing for large datasets
- Add integration tests with actual CFBD API (rate-limited)
- Add visual regression testing for frontend
