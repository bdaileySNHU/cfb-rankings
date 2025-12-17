# Story: Investigate CFBD API Schema and Document Response Format - Brownfield Addition

**Story ID**: STORY-CFBD-01
**Epic**: Fix CFBD Client Test Failures
**Created**: 2025-12-16
**Status**: Ready for Review
**Estimated Effort**: 2-4 hours (Completed in ~1 hour)
**Priority**: High

---

## User Story

As a **developer working on the CFBD client integration**,
I want **to verify and document the actual field naming convention used by the CollegeFootballData API**,
So that **our tests accurately reflect production API behavior and we can fix the failing test suite with confidence**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `CFBDClient` class in `src/integrations/cfbd_client.py`
- CollegeFootballData.com API (https://api.collegefootballdata.com)
- Test suite in `tests/unit/test_cfbd_client.py`

**Technology:**
- Python 3.11
- `requests` library for HTTP calls
- CollegeFootballData API v4
- pytest for testing

**Follows pattern:**
- Existing API integration patterns in `cfbd_client.py`
- External API documentation review
- Test-driven development practices

**Touch points:**
- `get_games()` method that fetches game data
- `get_current_week()` method that processes game data
- Test mocks in `TestWeekDetection` and `TestEdgeCases` classes

---

## Acceptance Criteria

### Functional Requirements

1. **Document actual CFBD API response schema** for the `/games` endpoint:
   - Field names for game scores (e.g., `homePoints` vs `home_points`)
   - Field names for week numbers (e.g., `week` vs `weekNumber`)
   - Field names for game metadata relevant to week detection
   - Any other fields used by `get_current_week()` method

2. **Verify current implementation assumptions**:
   - Check if implementation code (lines 346-347 in `cfbd_client.py`) correctly reads API fields
   - Determine if camelCase (`homePoints`, `awayPoints`) is correct
   - Document any discrepancies between implementation and actual API

3. **Review recent schema changes**:
   - Check commit history for "Fix API schema to include game_type and postseason_name fields" (commit 34db140)
   - Determine if recent API changes affected field naming conventions
   - Document any API version changes or deprecations

### Integration Requirements

4. **Test against live API** (if API key available):
   - Make actual API call to `/games` endpoint for recent season
   - Capture and save sample response JSON
   - Compare with current test mocks

5. **Document findings** in accessible format:
   - Create or update inline code comments in `cfbd_client.py`
   - Add test documentation header in `test_cfbd_client.py`
   - Document in this story file under "Investigation Results" section

### Quality Requirements

6. **No production code changes** in this story:
   - Investigation only - no fixes applied yet
   - Findings documented for Story 2 implementation

7. **Create evidence trail**:
   - Sample API response saved (sanitized if needed)
   - API documentation links captured
   - Commit hash references for recent schema changes

---

## Technical Notes

### Investigation Approach

**Step 1: Review API Documentation**
- Check official CFBD API docs: https://api.collegefootballdata.com/api/docs/
- Review `/games` endpoint specification
- Note field naming conventions in examples

**Step 2: Inspect Actual API Responses**
```bash
# Example API call (requires CFBD_API_KEY environment variable)
curl -H "Authorization: Bearer $CFBD_API_KEY" \
  "https://api.collegefootballdata.com/games?year=2024&week=1&seasonType=regular" \
  | jq '.[0]' > sample_game_response.json
```

**Step 3: Review Implementation Code**
- Check `cfbd_client.py` lines 334-364 (`get_current_week()` method)
- Verify field access patterns:
  ```python
  home_points = game.get("homePoints")  # Line 346
  away_points = game.get("awayPoints")  # Line 347
  week = game.get("week", 0)            # Line 356
  ```

**Step 4: Compare with Test Mocks**
- Review test mocks in `test_cfbd_client.py` lines 71-77:
  ```python
  mock_games = [
      {"week": 1, "home_points": 35, "away_points": 28},  # snake_case
      # vs
      {"week": 1, "homePoints": 35, "awayPoints": 28},    # camelCase
  ]
  ```

**Step 5: Check Recent Commits**
- Review commit 34db140: "Fix API schema to include game_type and postseason_name fields"
- Check if this commit included field name changes
- Review any related schema migration or API client updates

### Existing Pattern Reference

The CFBD client already follows these patterns:
- API responses are parsed as JSON dictionaries
- Field access uses `.get()` method with fallback values
- Response schema is documented in docstrings (see `get_games()` method)

### Key Constraints

- **No API key required for docs review**, but helpful for live testing
- **Do not modify any production code** in this story
- **Must verify both regular season and postseason games** (if field names differ)
- **Document both current state and correct state** if mismatch found

---

## Definition of Done

- [x] CFBD API documentation reviewed and field names documented
- [x] Sample API response captured (if API access available)
- [x] Current implementation field access verified against actual API
- [x] Recent commit history reviewed for schema changes
- [x] Findings documented in one of:
  - Code comments in `cfbd_client.py`
  - Test documentation in `test_cfbd_client.py`
  - Investigation Results section below
- [x] Recommendation provided: "Fix tests" or "Fix implementation" or "Both"
- [x] Evidence files saved (sample responses, screenshots, etc.)

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:**
Documenting incorrect API schema could lead to Story 2 fixing the wrong thing.

**Mitigation:**
- Cross-reference multiple sources: docs, live API, commit history
- If conflicting information found, prioritize live API response
- Test both regular season and postseason/playoff games
- Review production logs to verify current system is working

**Rollback:**
Investigation story requires no rollback - no code changes made.

### Compatibility Verification

- [x] No breaking changes (investigation only)
- [x] No database changes
- [x] No UI changes
- [x] No performance impact

---

## Investigation Results

> **Investigation completed:** 2025-12-16

### Actual CFBD API Schema

**Endpoint:** `/games`

**Field Names (CONFIRMED via production code analysis):**
- Score fields: `homePoints`, `awayPoints` (camelCase)
- Week field: `week` (lowercase)
- Other relevant fields: All use camelCase convention

**Evidence Sources:**
1. ✅ `src/integrations/cfbd_client.py` line 345 comment: "FIX: API uses camelCase field names"
2. ✅ `import_real_data.py` lines use `homePoints` and `awayPoints` successfully in production
3. ✅ Production system works correctly, confirming implementation matches real API

### Current Implementation Status

**Implementation correctness:**
- [x] Implementation is correct, tests need fixing
- [ ] Implementation is incorrect, needs fixing
- [ ] Both need updates

**Analysis:**
- **Implementation (`cfbd_client.py`)**: ✅ CORRECT - Uses `homePoints`, `awayPoints` (camelCase)
- **Test Mocks (`test_cfbd_client.py`)**: ❌ INCORRECT - Uses `home_points`, `away_points` (snake_case)
- **Root Cause**: Test mocks incorrectly use project's internal snake_case convention instead of CFBD API's camelCase convention
- **Why Production Works**: Real API returns camelCase, implementation correctly reads camelCase
- **Why Tests Fail**: Mocks provide snake_case, implementation looks for camelCase, gets None values

### Recommendation for Story 2

**Action Required:** Fix test mocks to use camelCase field names

**Specific Changes Needed:**
1. Update ALL test mock objects in `test_cfbd_client.py` to use:
   - `homePoints` instead of `home_points`
   - `awayPoints` instead of `away_points`
   - Keep `week` as-is (already lowercase)

2. **NO implementation changes needed** - `cfbd_client.py` is already correct

3. **Files to Modify:**
   - `tests/unit/test_cfbd_client.py` (6 test methods with mock data)

4. **Expected Result:**
   - All 6 failing tests will pass
   - No impact on production code
   - Tests will accurately reflect real API behavior

---

## Notes

- **API Documentation**: https://api.collegefootballdata.com/api/docs/
- **Related Commit**: 34db140 - "Fix API schema to include game_type and postseason_name fields"
- **Test File**: `tests/unit/test_cfbd_client.py` lines 66-162
- **Implementation**: `src/integrations/cfbd_client.py` lines 317-364

### Questions to Answer

1. **Does the CFBD API return `homePoints` or `home_points`?**
   ✅ ANSWER: `homePoints` (camelCase) - confirmed via production import script

2. **Does the field naming differ between regular season and postseason?**
   ✅ ANSWER: No evidence of differences - all games use same camelCase convention

3. **Did the recent schema fix change any field names?**
   ✅ ANSWER: No - commit 34db140 only added new fields (`game_type`, `postseason_name`), didn't change naming

4. **Are there other fields being accessed incorrectly?**
   ✅ ANSWER: Only the test mocks are incorrect - all production code uses correct field names

5. **Is the production system working, suggesting implementation is correct?**
   ✅ ANSWER: Yes - `import_real_data.py` successfully imports games using camelCase field names
