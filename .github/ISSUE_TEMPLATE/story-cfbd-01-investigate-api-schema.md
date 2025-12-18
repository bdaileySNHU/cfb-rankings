---
name: "Story 1: Investigate CFBD API Schema"
about: Verify and document the actual field naming convention used by CFBD API
title: '[STORY-CFBD-01] Investigate CFBD API Schema and Document Response Format'
labels: 'investigation, tests, priority-high, epic-cfbd-test-failures'
assignees: ''
---

## 📋 Story Overview

**Epic**: Fix CFBD Client Test Failures
**Story ID**: STORY-CFBD-01
**Estimated Effort**: 2-4 hours
**Priority**: High
**Status**: Ready for Development

---

## 🎯 User Story

**As a** developer working on the CFBD client integration
**I want** to verify and document the actual field naming convention used by the CollegeFootballData API
**So that** our tests accurately reflect production API behavior and we can fix the failing test suite with confidence

---

## 📝 Context

### Problem
We have 6 failing tests in `test_cfbd_client.py` where `get_current_week()` returns `None` instead of expected week numbers. The root cause appears to be a mismatch between:
- Implementation code expecting camelCase: `homePoints`, `awayPoints`
- Test mocks providing snake_case: `home_points`, `away_points`

### Goal
Determine which format is correct by investigating the actual CFBD API responses.

### Integration Points
- `CFBDClient` class in `src/integrations/cfbd_client.py`
- Test suite in `tests/unit/test_cfbd_client.py`
- CollegeFootballData.com API

---

## ✅ Acceptance Criteria

### Investigation Requirements

- [ ] **Document actual CFBD API response schema** for `/games` endpoint
  - Field names for game scores (`homePoints` vs `home_points`)
  - Field names for week numbers (`week` vs `weekNumber`)
  - Field names for game metadata relevant to week detection

- [ ] **Verify current implementation assumptions**
  - Check if `cfbd_client.py` lines 346-347 correctly read API fields
  - Determine if camelCase (`homePoints`, `awayPoints`) is correct
  - Document any discrepancies

- [ ] **Review recent schema changes**
  - Check commit `34db140`: "Fix API schema to include game_type and postseason_name fields"
  - Determine if recent changes affected field naming
  - Document any API version changes

- [ ] **Test against live API** (if API key available)
  - Make actual API call to `/games` endpoint
  - Capture and save sample response JSON
  - Compare with current test mocks

- [ ] **Document findings** in accessible format
  - Update code comments in `cfbd_client.py` OR
  - Add test documentation in `test_cfbd_client.py` OR
  - Document in this issue under "Investigation Results"

### Quality Requirements

- [ ] No production code changes (investigation only)
- [ ] Evidence trail created (sample responses, API doc links, commit references)

---

## 🔧 Investigation Approach

### Step 1: Review API Documentation
- Check official docs: https://api.collegefootballdata.com/api/docs/
- Review `/games` endpoint specification
- Note field naming conventions in examples

### Step 2: Inspect Actual API Responses
```bash
# Example API call (requires CFBD_API_KEY)
curl -H "Authorization: Bearer $CFBD_API_KEY" \
  "https://api.collegefootballdata.com/games?year=2024&week=1&seasonType=regular" \
  | jq '.[0]' > sample_game_response.json
```

### Step 3: Review Implementation Code
Check these lines in `cfbd_client.py`:
- Line 346: `home_points = game.get("homePoints")`
- Line 347: `away_points = game.get("awayPoints")`
- Line 356: `week = game.get("week", 0)`

### Step 4: Compare with Test Mocks
Review test mocks in `test_cfbd_client.py` (lines 71-77 and similar)

### Step 5: Check Recent Commits
- Review commit `34db140` for schema-related changes
- Check any related API client updates

---

## 📊 Definition of Done

- [ ] CFBD API documentation reviewed and field names documented
- [ ] Sample API response captured (if API access available)
- [ ] Current implementation verified against actual API
- [ ] Recent commit history reviewed for schema changes
- [ ] Findings documented (choose one location):
  - [ ] Code comments in `cfbd_client.py`
  - [ ] Test documentation in `test_cfbd_client.py`
  - [ ] Investigation Results section below
- [ ] **Recommendation provided**: "Fix tests" OR "Fix implementation" OR "Both"
- [ ] Evidence files saved and linked in this issue

---

## 📖 Investigation Results

> **Fill this section during implementation**

### Actual CFBD API Schema

**Endpoint:** `/games`

**Field Names:**
- Score fields: `_________________`
- Week field: `_________________`
- Other relevant fields: `_________________`

**API Documentation Link:** _________________

**Sample Response:** (attach file or paste snippet)
```json
{
  "TBD": "paste sample game object here"
}
```

### Current Implementation Status

**Implementation correctness:**
- [ ] ✅ Implementation is correct, tests need fixing
- [ ] ❌ Implementation is incorrect, needs fixing
- [ ] ⚠️ Both need updates

### Recommendation for Story 2

> Document specific actions needed based on findings:

---

## 🔗 Related Links

- **Epic**: Fix CFBD Client Test Failures ([docs/epic-fix-cfbd-test-failures.md](../../docs/epic-fix-cfbd-test-failures.md))
- **Story Doc**: [story-cfbd-01-investigate-api-schema.md](../../docs/stories/story-cfbd-01-investigate-api-schema.md)
- **Test File**: `tests/unit/test_cfbd_client.py` (lines 66-162)
- **Implementation**: `src/integrations/cfbd_client.py` (lines 317-364)
- **API Docs**: https://api.collegefootballdata.com/api/docs/
- **GitHub Actions**: https://github.com/bdaileySNHU/cfb-rankings/actions

---

## ❓ Questions to Answer

- [ ] Does the CFBD API return `homePoints` or `home_points`?
- [ ] Does the field naming differ between regular season and postseason?
- [ ] Did the recent schema fix change any field names?
- [ ] Are there other fields being accessed incorrectly?
- [ ] Is the production system working (suggesting implementation is correct)?

---

## 💡 Notes

- This is **investigation only** - no code fixes in this story
- Findings will guide Story 2 implementation
- If uncertain, prioritize live API response over documentation
- Test both regular season and postseason games if possible
