# EPIC: Fix CFBD Client Test Failures - Brownfield Enhancement

**Epic ID**: EPIC-TBD
**Created**: 2025-12-16
**Status**: Draft
**Type**: Brownfield Enhancement (Bug Fix)

---

## Epic Goal

Fix 6 failing unit tests in the CFBD client test suite to restore CI/CD pipeline to green status and ensure reliable week detection functionality.

## Epic Description

### Existing System Context

**Current Relevant Functionality:**
- The `CFBDClient` class (`src/integrations/cfbd_client.py`) interfaces with the CollegeFootballData.com API
- The `get_current_week()` method detects the current week of the CFB season by analyzing completed games
- Method looks for games with non-null scores to determine the highest completed week
- Used by the ranking system to determine which week's games to process

**Technology Stack:**
- Python 3.11
- pytest 7.4.3 for testing with pytest-mock for mocking
- FastAPI backend with SQLAlchemy ORM
- CollegeFootballData API integration

**Integration Points:**
- `get_current_week()` is called by ranking calculation services
- Depends on `get_games()` method to fetch game data from CFBD API
- Test suite mocks API responses to validate week detection logic

### Enhancement Details

**What's Being Added/Changed:**

The failing tests reveal a **field name mismatch** between test mocks and implementation code:

**Failing Tests (6 total):**
1. `test_get_current_week_with_completed_games` - expects week 8, gets None
2. `test_get_current_week_week_1_only` - expects week 1, gets None
3. `test_get_current_week_ignores_missing_week_field` - expects week 5, gets None
4. `test_get_current_week_excludes_future_games_with_zero_scores` - expects week 5, gets None
5. `test_get_current_week_epic_008_scenario` - expects week 9, gets None
6. `test_get_current_week_with_mixed_data` - expects week 3, gets None

**Root Cause:**
- Implementation code (lines 346-347 in `cfbd_client.py`) checks for `homePoints` and `awayPoints` (camelCase)
- Test mocks provide `home_points` and `away_points` (snake_case)
- This mismatch causes the method to treat all mocked games as "future games" with null scores
- Result: method returns None instead of detecting the completed week

**How It Integrates:**
- Fix must maintain compatibility with actual CFBD API response format
- Must verify which field naming convention the real API uses (camelCase vs snake_case)
- Tests must accurately reflect real API behavior
- No changes to public API or method signatures

**Success Criteria:**
- All 6 failing tests pass
- CI/CD pipeline returns to green status
- Week detection works correctly for both test scenarios and production API calls
- No regression in other CFBD client functionality

---

## Stories

This epic consists of 2 focused stories:

### **Story 1: Investigate CFBD API Schema and Document Actual Response Format**

**Description:** Determine the actual field naming convention used by the CollegeFootballData API by examining real API responses, reviewing API documentation, and checking recent commits related to schema changes.

**Acceptance Criteria:**
- Document actual field names returned by CFBD `/games` endpoint
- Verify whether API uses camelCase, snake_case, or a mix
- Check if recent API changes (referenced in commit "Fix API schema to include game_type and postseason_name fields") affected field naming
- Document findings in code comments or test documentation

**Estimated Complexity:** Small (2-4 hours)

---

### **Story 2: Fix Test Mocks to Match Actual CFBD API Response Schema**

**Description:** Update the test mock data in `test_cfbd_client.py` to use the correct field naming convention that matches the actual CFBD API responses, ensuring tests accurately validate production behavior.

**Acceptance Criteria:**
- Update all game mock objects in failing tests to use correct field names
- All 6 failing tests pass
- Verify `get_current_week()` implementation correctly reads the actual API field names
- Add test documentation clarifying the API schema being tested
- Run full test suite to ensure no regressions
- CI/CD pipeline returns to green status

**Estimated Complexity:** Small (2-4 hours)

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (no changes to `get_current_week()` public interface)
- [x] Database schema changes are backward compatible (no DB changes)
- [x] UI changes follow existing patterns (no UI changes)
- [x] Performance impact is minimal (test fixes only, no runtime impact)

---

## Risk Mitigation

**Primary Risk:**
Fixing tests to match implementation without verifying actual API behavior could mask a real bug where the implementation doesn't work with the live API.

**Mitigation:**
- Story 1 explicitly requires verification of actual API response format
- Test against real API responses (if possible in dev environment)
- Review commit history for schema change context
- Check if existing production deployment is working correctly (indicating implementation is correct)

**Rollback Plan:**
- Changes are isolated to test files
- Git revert to restore original test code if issues arise
- No production code changes means zero production risk

---

## Definition of Done

- [x] All 6 failing unit tests pass
- [x] Test mocks accurately reflect real CFBD API schema
- [x] Documentation added explaining API schema expectations
- [x] Full test suite passes with no regressions
- [x] CI/CD pipeline shows green status
- [x] Code reviewed for correctness against actual API behavior
- [x] No changes to production code logic or public APIs

---

## Epic Validation Checklist

**Scope Validation:**
- [x] Epic can be completed in 2 stories (within 1-3 story limit)
- [x] No architectural documentation required
- [x] Enhancement follows existing testing patterns
- [x] Integration complexity is manageable (test-only changes)

**Risk Assessment:**
- [x] Risk to existing system is low (test-only changes)
- [x] Rollback plan is feasible (simple git revert)
- [x] Testing approach covers existing functionality
- [x] Team has sufficient knowledge of integration points

**Completeness Check:**
- [x] Epic goal is clear and achievable (fix 6 failing tests)
- [x] Stories are properly scoped (investigate + fix)
- [x] Success criteria are measurable (tests pass, CI green)
- [x] Dependencies are identified (need to verify API schema)

---

## Notes

- This is a **test correction issue**, not a production bug (assuming current production is working)
- The commit "Fix API schema to include game_type and postseason_name fields" suggests recent API changes may have caused confusion
- If investigation reveals the implementation is wrong (not the tests), Story 2 scope may shift to fix implementation instead
- Priority is HIGH - failing CI/CD blocks all future deployments

---

## Handoff to Story Manager

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is test correction for an existing CFBD client integration in a Python 3.11/FastAPI system
- Integration points: `get_current_week()` method in `src/integrations/cfbd_client.py`, test suite in `tests/unit/test_cfbd_client.py`
- Existing patterns to follow: pytest with mocking, existing CFBD client test structure
- Critical compatibility requirements:
  - Must verify actual CFBD API schema before making changes
  - Must maintain compatibility with production API calls
  - Test mocks must accurately reflect real API behavior
- Each story must include verification that:
  - Tests pass after changes
  - No regression in other CFBD client tests
  - CI/CD pipeline returns to green

The epic should restore CI/CD pipeline integrity while ensuring test accuracy matches production API behavior."
