# EPIC-002: Dynamic Season Management & Complete Game Import

**Epic Type:** Brownfield Enhancement
**Priority:** High
**Estimated Effort:** 3 Stories
**Risk Level:** Medium

---

## Epic Goal

Eliminate hardcoded season/year values and ensure complete game imports by implementing dynamic season detection and improving data import reliability, enabling the system to automatically adapt to the current college football season without manual code changes.

---

## Epic Description

### Existing System Context

**Current Relevant Functionality:**
- College Football Rankings system with FastAPI backend, SQLite database
- Real data import from CollegeFootballData.com API via `import_real_data.py` and `update_games.py`
- Season model tracks year, current_week, and is_active status
- Frontend displays games, teams, and rankings for a specific season

**Technology Stack:**
- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- Frontend: Vanilla JavaScript (ES6+), HTML5, CSS3
- External API: CollegeFootballData.com (CFBD)
- Deployment: Ubuntu/Debian VPS, Nginx, Gunicorn, systemd

**Integration Points:**
- `import_real_data.py` - Initial full season import (RESETS database)
- `update_games.py` - Incremental weekly updates (SAFE, additive only)
- Frontend JavaScript files (`games.html`, `team.js`, `comparison.js`)
- CFBD API client (`cfbd_client.py`)
- Season model and database schema

### Current Problems

**Problem 1: Hardcoded Season Year (2025)**

Hardcoded values found in:
- `import_real_data.py:233` - `Season(year=2025, ...)`
- `import_real_data.py:238` - `import_teams(cfbd, db, year=2025)`
- `import_real_data.py:254` - `import_games(..., year=2025, ...)`
- `import_real_data.py:246-249` - User prompt mentions "2025 season" and "Week 6"
- `frontend/games.html:84` - `api.getGames({ season: 2025, limit: 200 })`
- `frontend/js/comparison.js:47` - `api.getGames({ season: 2025, limit: 300 })`

**Impact:**
When the 2026 season starts, every file must be manually updated. This creates maintenance burden and risk of inconsistent updates.

**Problem 2: Incomplete Game Imports**

**Evidence:**
- User reports Ohio State showing 4-0 instead of 6-0 (Week 8 data)
- Screenshot shows successful import of 296 games through Week 6, but missing subsequent weeks
- Some Week 2 games not imported (Ohio State example)

**Root Causes Identified:**
1. `import_real_data.py` prompts user for max week with hardcoded suggestion: "Week 6" (line 246)
2. Initial import may have stopped at Week 6, leaving Weeks 7-8 unimported
3. No validation that ALL completed games for a given week were imported
4. No automatic detection of current week from CFBD API or calendar
5. Team name mismatches between CFBD API and local database can silently skip games

**Impact:**
Rankings are inaccurate, user trust is compromised, manual intervention required weekly.

### Enhancement Details

**What's Being Added/Changed:**

1. **Dynamic Season Detection:**
   - Auto-detect current season year from system date (August 1 = new season starts)
   - Fall back to CFBD API if available
   - Remove all hardcoded year references

2. **Automatic Current Week Detection:**
   - Query CFBD API for latest completed week
   - Use calendar logic as fallback (season starts Labor Day weekend)
   - Store and update `current_week` in Season model automatically

3. **Import Validation & Completeness:**
   - Validate all games were imported for each week
   - Detect and report team name mismatches
   - Add retry logic for failed API calls
   - Provide detailed import summary with warnings

**How It Integrates:**

- Modify `import_real_data.py` to calculate season year dynamically
- Modify `update_games.py` to auto-detect next weeks to import
- Add utility functions to `cfbd_client.py` for week detection
- Update frontend to fetch active season from backend API
- Maintain backward compatibility with existing Season model

**Success Criteria:**

1. No hardcoded season years in any Python or JavaScript files
2. System correctly determines current season year on any date
3. Import scripts automatically detect and import all available weeks
4. Import process reports any missing or skipped games with reasons
5. Frontend dynamically loads current active season from backend
6. All 236 existing tests continue to pass (use factories for test data years)

---

## Stories

### Story 1: Add Dynamic Season & Week Detection Utility

**Description:** Create utility functions to dynamically detect current season year and current week from CFBD API and calendar logic.

**Scope:**
- Add `get_current_season()` function to `cfbd_client.py`
- Add `get_current_week()` function that queries CFBD for latest completed week
- Add calendar-based fallback for season/week detection
- Unit tests for edge cases (off-season, week 1, week 15)

**Acceptance Criteria:**
- `get_current_season()` returns correct year based on date (Aug 1+ = new season)
- `get_current_week()` queries CFBD API and returns highest completed week
- Fallback logic works when API unavailable
- Handles edge cases: off-season (returns previous season), mid-season, postseason

**Estimated Effort:** 3-5 hours

---

### Story 2: Remove Hardcoded Season Years & Implement Dynamic Detection

**Description:** Replace all hardcoded season year references with dynamic detection using the utilities from Story 1.

**Scope:**
- Update `import_real_data.py` to use `get_current_season()`
- Update `update_games.py` to auto-detect season and starting week
- Remove hardcoded "Week 6" prompts and calculate max week dynamically
- Update frontend (`games.html`, `comparison.js`) to fetch active season from API
- Add `/api/seasons/active` endpoint to return current active season

**Files to Modify:**
- `import_real_data.py` (lines 233, 238, 246-249, 254)
- `update_games.py` (add auto-detection for start_week)
- `frontend/games.html` (line 84)
- `frontend/js/comparison.js` (line 47)
- `main.py` (add `/api/seasons/active` endpoint)

**Acceptance Criteria:**
- All hardcoded `2025` references removed from production code
- Scripts automatically determine current season without user input
- Frontend fetches season from `/api/seasons/active` API
- User can still override season/week with command-line arguments if needed
- All existing tests pass (tests can use hardcoded years via factories)

**Estimated Effort:** 4-6 hours

---

### Story 3: Add Import Validation & Completeness Checks

**Description:** Enhance import scripts to validate completeness, detect team name mismatches, and report any skipped games.

**Scope:**
- Add pre-import validation: check CFBD API connectivity
- Add per-week validation: compare expected vs actual game count from CFBD
- Detect and report team name mismatches that cause game skips
- Add import summary with warnings and statistics
- Add `--validate-only` flag to check import without making changes

**Enhancements to `import_real_data.py` and `update_games.py`:**
- Query CFBD for total games in week, compare to imported count
- Log warnings for any teams in CFBD response not found in local database
- Print summary: "Expected 50 games for Week 7, imported 48, skipped 2"
- List skipped games with reasons (team not found, FCS opponent, etc.)

**Acceptance Criteria:**
- Import scripts print validation summary after each week
- Warnings shown for team name mismatches with suggested fixes
- `--validate-only` mode allows checking without modifying database
- Import logs clearly show: expected, imported, skipped counts
- Documentation updated with troubleshooting guide for import issues

**Estimated Effort:** 5-7 hours

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (new `/api/seasons/active` endpoint added)
- [x] Database schema unchanged (uses existing Season model fields)
- [x] UI changes are backward compatible (graceful degradation if API fails)
- [x] Performance impact minimal (one additional API query on page load)
- [x] Import scripts maintain existing command-line interface
- [x] All 236 existing tests pass without modification

---

## Risk Mitigation

### Primary Risks

**Risk 1: Dynamic Detection Fails**
- **Scenario:** CFBD API is down, calendar logic has bugs, wrong season detected
- **Mitigation:**
  - Implement robust fallback logic
  - Add `--season YYYY` and `--max-week N` override flags
  - Log detailed debug info about detection process
  - Alert user if detected season seems incorrect (e.g., 2030)
- **Rollback:** Command-line overrides allow manual specification

**Risk 2: Import Validation Breaks Existing Workflow**
- **Scenario:** New validation is too strict, blocks valid imports
- **Mitigation:**
  - Make validation warnings-only by default
  - Add `--strict` flag for blocking on validation failures
  - Thoroughly test with historical data (2023, 2024, 2025 seasons)
- **Rollback:** Validation can be disabled with `--skip-validation` flag

**Risk 3: Frontend Season Detection Fails**
- **Scenario:** `/api/seasons/active` returns error, frontend breaks
- **Mitigation:**
  - Implement try/catch with fallback to hardcoded current year
  - Show user-friendly error message: "Using data from 2025 season"
  - Log error to browser console for debugging
- **Rollback:** Frontend can fall back to hardcoded season if API fails

### Rollback Plan

**If EPIC-002 causes issues in production:**

1. **Immediate Rollback (Git):**
   ```bash
   cd /var/www/cfb-rankings
   git revert <commit-hash>
   sudo systemctl restart cfb-rankings
   ```

2. **Manual Overrides:**
   - Use `--season 2025` flag on import scripts
   - Edit `.env` to set `DEFAULT_SEASON=2025`
   - Frontend falls back to hardcoded year

3. **Database Rollback:**
   - No schema changes, so database remains compatible
   - Re-run import with explicit season if needed

---

## Definition of Done

### Epic Complete When:

- [x] All 3 stories completed with acceptance criteria met
- [x] No hardcoded season years in production code (tests excluded)
- [x] Import scripts automatically detect season and current week
- [x] Frontend dynamically loads active season from backend
- [x] Import validation reports completeness for each week
- [x] All 236 existing tests pass without modification
- [x] New utility functions have >80% test coverage
- [x] Documentation updated:
  - `docs/UPDATE-GAME-DATA.md` - Updated with new auto-detection behavior
  - `README.md` - Note about dynamic season management
- [x] Production deployment guide updated
- [x] No regressions in existing functionality verified through:
  - Automated test suite (236 tests)
  - Manual testing on staging/production
  - Import process tested with 2024 and 2025 seasons

---

## Testing Strategy

### Automated Testing

**Unit Tests (New):**
- `test_season_detection()` - Season year calculation for various dates
- `test_week_detection()` - Current week detection from CFBD API
- `test_calendar_fallback()` - Fallback logic when API unavailable
- `test_import_validation()` - Game count validation logic

**Integration Tests (Modified):**
- Update existing tests to use `SeasonFactory` with explicit years
- Verify `/api/seasons/active` endpoint
- Test import scripts with dynamic detection

**Regression Tests:**
- All 236 existing tests must pass
- Add regression test for hardcoded year detection (grep for "202[5-9]")

### Manual Testing

**Import Testing:**
1. Run `import_real_data.py` without arguments → detects current season
2. Run `update_games.py` without arguments → auto-detects next week to import
3. Verify validation warnings appear for team name mismatches
4. Test with `--validate-only` flag

**Frontend Testing:**
1. Visit production site → verify current season loads
2. Simulate API failure → verify graceful fallback
3. Check browser console for season detection logs
4. Test on multiple browsers

**Edge Case Testing:**
1. Run scripts on August 1 (season boundary)
2. Run scripts in off-season (February)
3. Test with invalid CFBD API key
4. Test with network disconnected

---

## Dependencies & Prerequisites

### External Dependencies

- **CFBD API Access:** Requires valid API key for season/week detection
- **Network Connectivity:** Import scripts need internet access
- **Python Packages:** No new dependencies required (uses existing requests library)

### Internal Dependencies

- **Season Model:** Uses existing `season` field, `current_week`, `is_active`
- **CFBD Client:** Extends `cfbd_client.py` with new methods
- **Import Scripts:** Modifies `import_real_data.py` and `update_games.py`

### Blocked By

- None (all dependencies exist)

### Blocks

- None (this is an independent enhancement)

---

## Story Sequencing Rationale

**Why This Order:**

1. **Story 1 First:** Create utility functions before using them (foundation)
2. **Story 2 Second:** Replace hardcoded values using new utilities (implementation)
3. **Story 3 Last:** Add validation after core functionality works (polish)

This sequence minimizes risk:
- Each story builds on the previous
- Story 1 can be tested in isolation
- Story 2 delivers user-visible value
- Story 3 adds reliability without changing core behavior

---

## Story Manager Handoff

**Ready for Story Development**

Please develop detailed user stories for this brownfield epic. Key considerations:

**Integration Context:**
- This is an enhancement to existing College Football Rankings system
- Technology stack: Python/FastAPI backend, vanilla JS frontend, SQLite database
- Import scripts already exist and work, we're making them smarter
- CFBD API client already integrated

**Integration Points:**
- `cfbd_client.py` - Extend with season/week detection methods
- `import_real_data.py` - Remove hardcoded years, use dynamic detection
- `update_games.py` - Auto-detect starting week for incremental imports
- Frontend JavaScript - Fetch active season from backend API
- `main.py` - Add new `/api/seasons/active` API endpoint

**Existing Patterns to Follow:**
- Use existing `CFBDClient` class structure
- Follow existing error handling patterns (try/except with logging)
- Maintain existing CLI argument structure (add, don't break)
- Frontend follows existing API service pattern (`api.js`)

**Critical Compatibility Requirements:**
- All 236 existing tests must pass without modification
- Existing CLI arguments continue to work (add new optional args)
- Database schema remains unchanged
- No breaking changes to existing import workflow
- Frontend gracefully degrades if new API endpoint fails

**Each Story Must Include:**
- Verification that existing functionality remains intact
- Test coverage for new utility functions (>80%)
- Documentation updates for changed behavior
- Example command outputs showing new dynamic detection
- Rollback procedure if issues arise

**Epic Goal:**
Eliminate hardcoded season years and improve import completeness while maintaining 100% backward compatibility with existing workflows. The system should "just work" for the current season without manual code changes.

---

**Epic Created:** 2025-10-18
**Created By:** John (PM Agent)
**Status:** Ready for Story Development
**Next Steps:** Hand off to Dev Agent for story implementation
