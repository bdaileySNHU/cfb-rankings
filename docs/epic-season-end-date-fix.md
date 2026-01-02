# Season End Date Logic Fix - Brownfield Enhancement

## Epic Goal

Fix the season year detection logic to correctly identify the active college football season during January and early February, preventing premature rollover to the next season while playoffs are still ongoing.

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Season year is determined by `get_current_season()` in `src/integrations/cfbd_client.py` which returns the current calendar year
- Active season detection in `scripts/weekly_update.py` checks if current month is August-December OR January
- Frontend displays the active season via `/api/seasons/active` endpoint
- Database tracks which season is active via `Season.is_active` flag

**Technology stack:**
- Backend: Python, SQLAlchemy, FastAPI
- Frontend: Vanilla JavaScript
- Database: SQLite with Season model

**Integration points:**
- `CFBDClient.get_current_season()` - determines season year for API calls
- `is_active_season()` - determines if system should process games
- `/api/seasons/active` endpoint - provides active season to frontend
- Season dropdown UI component - displays current season marker

### Enhancement Details

**Problem:**
When the calendar year changes to 2026 on January 1st, the system incorrectly identifies 2026 as the current season. However, the 2025-2026 college football season continues through mid-January with the College Football Playoff National Championship (typically around January 20th). This causes the website to prematurely show 2026 season data when the 2025 season is still active.

**What's being added/changed:**
1. **Update season year logic** - Modify `get_current_season()` to return the previous calendar year when in January/early February before the championship game
2. **Configure season end date** - Add configuration for the actual season end date (approximately mid-January through early February)
3. **Update active season logic** - Ensure `is_active_season()` and database `is_active` flag align with the corrected season year logic

**How it integrates:**
- Modify existing `get_current_season()` method in `cfbd_client.py`
- Add season end date configuration (environment variable or config file)
- Update `is_active_season()` function to use the new logic
- No API contract changes needed - existing endpoints continue working
- No database schema changes required
- No frontend changes required (automatically reflects corrected backend logic)

**Success criteria:**
- When viewing the site in January 2026, the active season shows as 2025 (not 2026) until the championship game concludes
- Season rollover happens after the configured season end date (mid-January through early February)
- Historical season data remains accessible and unaffected
- Automated weekly updates continue processing the correct season

## Stories

1. **Story 1: Add Configurable Season End Date**
   - Add configuration for season end date (environment variable with default ~February 1st)
   - Update documentation for the new configuration option
   - Validate configuration loads correctly

2. **Story 2: Fix Season Year Detection Logic**
   - Modify `get_current_season()` to check if current date is before season end date
   - If in January/February before end date, return previous calendar year
   - Update method docstring with new logic explanation
   - Add unit tests for season year detection across year boundary

3. **Story 3: Verify Active Season Detection Consistency**
   - Ensure `is_active_season()` aligns with corrected season year logic
   - Verify `/api/seasons/active` endpoint returns correct season during rollover period
   - Test frontend season display during January with corrected logic
   - Validate weekly update script processes correct season

## Compatibility Requirements

- [x] Existing APIs remain unchanged - `/api/seasons/active` continues to work without contract changes
- [x] Database schema changes are backward compatible - No schema changes required
- [x] UI changes follow existing patterns - No UI changes required
- [x] Performance impact is minimal - Simple date comparison logic

## Risk Mitigation

**Primary Risk:**
Incorrect season year calculation could cause the system to:
- Fetch data for the wrong season from CFBD API
- Process games for the wrong season
- Display incorrect rankings to users

**Mitigation:**
- Add comprehensive unit tests covering all date boundary scenarios (late December, early January, mid-January, February)
- Test with specific dates: December 31, January 1, January 20, February 1
- Verify behavior in staging before deploying to production
- Monitor logs during January to confirm correct season is being processed

**Rollback Plan:**
- Simple code revert of `get_current_season()` method returns system to current behavior
- No database migrations to rollback
- No API contract changes to revert
- Configuration change can be removed or reset to previous value

## Definition of Done

- [x] All stories completed with acceptance criteria met
- [x] Existing functionality verified through testing (season selection, API endpoints, frontend display)
- [x] Integration points working correctly (CFBD API calls, weekly updates, frontend)
- [x] Documentation updated appropriately (README, configuration docs)
- [x] No regression in existing features (historical season viewing, rankings display)
- [x] Unit tests added for season year detection logic
- [x] Manual testing performed with dates spanning December-February

---

## Story Manager Handoff

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing system running Python/FastAPI backend with vanilla JavaScript frontend
- Integration points:
  - `CFBDClient.get_current_season()` in `src/integrations/cfbd_client.py`
  - `is_active_season()` in `scripts/weekly_update.py`
  - `/api/seasons/active` API endpoint
  - Season dropdown UI component in frontend
- Existing patterns to follow:
  - Configuration via environment variables (following existing pattern)
  - Date-based logic similar to existing `is_active_season()` function
  - Unit testing in appropriate test files
- Critical compatibility requirements:
  - No API contract changes
  - No database schema changes
  - Preserve all existing season viewing functionality
  - Maintain backward compatibility with historical seasons
- Each story must include verification that existing functionality remains intact, especially:
  - Historical season data viewing
  - Season selection dropdown
  - Weekly update script processing
  - Rankings display

The epic should maintain system integrity while delivering correct season year identification during the January-February transition period when the college football season extends into the new calendar year."

---

## Validation Notes

**Scope Validation:**
- Epic can be completed in 3 stories ✓
- No architectural documentation required ✓
- Enhancement follows existing patterns (environment config, date logic) ✓
- Integration complexity is manageable (focused changes to season detection) ✓

**Risk Assessment:**
- Risk to existing system is low (isolated logic change) ✓
- Rollback plan is feasible (simple code revert) ✓
- Testing approach covers existing functionality (unit + manual testing) ✓
- Team has sufficient knowledge of integration points ✓

**Completeness Check:**
- Epic goal is clear and achievable ✓
- Stories are properly scoped (config, logic fix, verification) ✓
- Success criteria are measurable ✓
- Dependencies are identified (none - self-contained enhancement) ✓
