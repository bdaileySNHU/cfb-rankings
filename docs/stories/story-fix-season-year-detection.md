# Story 2: Fix Season Year Detection Logic - Brownfield Addition

**Epic:** Season End Date Logic Fix
**Story ID:** story-fix-season-year-detection
**Priority:** High
**Effort:** Small (3-4 hours)
**Depends On:** Story 1 (story-season-end-date-config)

## User Story

As a **college football fan**,
I want **the website to show the correct active season during January**,
So that **I can view current season rankings and games during the playoff period without the system prematurely switching to the next season**.

## Story Context

### Existing System Integration:

- **Integrates with:** `CFBDClient.get_current_season()` method in `src/integrations/cfbd_client.py`
- **Technology:** Python, datetime module, CFBD API integration
- **Follows pattern:** Existing date-based logic similar to `is_active_season()` in `scripts/weekly_update.py`
- **Touch points:**
  - `get_current_season()` method at line 294-315 in `cfbd_client.py`
  - Season end date configuration from Story 1
  - All CFBD API calls that use season year parameter
  - Weekly update script that processes games

## Acceptance Criteria

### Functional Requirements:

1. **Update `get_current_season()` method** to check if current date is before the configured season end date (from Story 1)
2. **Return previous calendar year** when current date is in January/February before the season end date (e.g., return 2025 when it's January 15, 2026)
3. **Return current calendar year** when current date is after the season end date or during August-December (existing behavior)
4. **Update method docstring** to clearly explain the new logic and date-based season determination

### Integration Requirements:

5. **Existing CFBD API calls** continue to work with the corrected season year parameter
6. **Weekly update script** processes games for the correct season during January transition period
7. **Season year calculation** is consistent across all code paths that use `get_current_season()`

### Quality Requirements:

8. **Unit tests added** covering multiple date scenarios:
   - December 31st (should return current year)
   - January 1st through configured end date (should return previous year)
   - Day after configured end date (should return current year)
   - August through December (should return current year)
9. **Method behavior verified** with specific test dates simulating year boundary
10. **No regression** in existing season detection for August-December period

## Technical Notes

### Integration Approach:

The method currently in `src/integrations/cfbd_client.py` (lines 294-315):

```python
def get_current_season(self) -> int:
    """
    Determine the current college football season year based on calendar date.
    Season year logic:
    - August 1 through December 31: Current calendar year
    - January 1 through July 31: Current calendar year
    Returns:
        int: The current season year (e.g., 2025)
    """
    now = datetime.now()
    return now.year
```

**Updated implementation approach:**

```python
def get_current_season(self) -> int:
    """
    Determine the current college football season year based on calendar date.

    College football seasons span two calendar years (e.g., 2025-2026 season).
    The season starts in August of year N and ends in January/February of year N+1
    with the College Football Playoff National Championship.

    Season year logic:
    - August through December: Current calendar year
    - January 1 through season end date: Previous calendar year (playoffs ongoing)
    - After season end date through July: Current calendar year (offseason)

    The season end date is configured via CFB_SEASON_END_DATE environment variable
    (default: February 1st).

    Returns:
        int: The current season year (e.g., when it's January 15, 2026, returns 2025)

    Examples:
        - December 31, 2025 → returns 2025
        - January 15, 2026 → returns 2025 (playoffs still ongoing)
        - February 2, 2026 → returns 2026 (offseason)
        - August 1, 2026 → returns 2026 (new season starting)
    """
    from datetime import datetime

    now = datetime.now()
    current_month = now.month
    current_day = now.day

    # Get configured season end date from Story 1
    season_end_month, season_end_day = get_season_end_date()

    # January through season end date: previous year (playoffs ongoing)
    if current_month == 1:
        # In January, always previous year (playoffs)
        return now.year - 1
    elif current_month == season_end_month and current_day < season_end_day:
        # Before end date in end month: previous year
        return now.year - 1
    elif current_month < season_end_month:
        # Between February and end month: previous year
        return now.year - 1
    else:
        # After season end date through December: current year
        return now.year
```

### Existing Pattern Reference:

Similar date-based logic exists in `scripts/weekly_update.py`:

```python
def is_active_season() -> bool:
    """
    Check if current date is during active CFB season.
    Active season runs from August 1 through January 31.
    """
    today = datetime.now()
    month = today.month
    # Active season: August (8) through December (12) OR January (1)
    return month >= 8 or month <= 1
```

### Key Constraints:

- Must maintain backward compatibility with existing code that calls `get_current_season()`
- Must not require changes to method signature or return type
- Must handle edge cases (leap years, different month lengths)
- Performance must remain constant (simple date comparison)
- Configuration must be read from Story 1's `get_season_end_date()` function

## Risk and Compatibility Check

### Minimal Risk Assessment:

- **Primary Risk:** Incorrect date logic could return wrong season year, causing:
  - CFBD API calls to fetch wrong season data
  - Wrong games/rankings to be displayed
  - Weekly updates to process wrong season
- **Mitigation:**
  - Comprehensive unit tests with specific dates covering all boundary conditions
  - Manual testing with different date scenarios
  - Verify in staging environment before production deployment
  - Monitor logs during January to confirm correct season
- **Rollback:** Simple code revert to previous `get_current_season()` implementation - no database changes, no API contract changes

### Compatibility Verification:

- [x] **No breaking changes to existing APIs** - Method signature unchanged, return type unchanged
- [x] **Database changes** - None required
- [x] **UI changes** - None required (frontend automatically reflects corrected season)
- [x] **Performance impact** - Negligible (simple date comparison added)

## Definition of Done

- [x] `get_current_season()` method updated with new date-based logic
- [x] Method uses `get_season_end_date()` configuration from Story 1
- [x] Method docstring updated with clear explanation and examples
- [x] Unit tests added and passing for all date scenarios:
  - December 31 → current year
  - January 1-19 → previous year (assuming Feb 1 end date)
  - January 20-31 → previous year
  - February 1+ → current year
  - August-December → current year
- [x] Existing CFBD API integration still works correctly
- [x] Weekly update script can determine correct season during January
- [x] Code follows existing patterns and style
- [x] No regression in season detection for non-January months

## Testing Guidance

### Unit Tests to Add:

```python
import pytest
from datetime import datetime
from unittest.mock import patch
from src.integrations.cfbd_client import CFBDClient

class TestGetCurrentSeason:
    """Test suite for get_current_season() method."""

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_december(self, mock_datetime, mock_end_date):
        """December should return current calendar year."""
        mock_end_date.return_value = (2, 1)  # Feb 1
        mock_datetime.now.return_value = datetime(2025, 12, 31)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = CFBDClient()
        assert client.get_current_season() == 2025

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_january_early(self, mock_datetime, mock_end_date):
        """January 1st should return previous calendar year (playoffs ongoing)."""
        mock_end_date.return_value = (2, 1)  # Feb 1
        mock_datetime.now.return_value = datetime(2026, 1, 1)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = CFBDClient()
        assert client.get_current_season() == 2025

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_january_championship(self, mock_datetime, mock_end_date):
        """January 20th (typical championship date) should return previous year."""
        mock_end_date.return_value = (2, 1)  # Feb 1
        mock_datetime.now.return_value = datetime(2026, 1, 20)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = CFBDClient()
        assert client.get_current_season() == 2025

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_after_season_end(self, mock_datetime, mock_end_date):
        """February 1st (season end date) should return current year (offseason)."""
        mock_end_date.return_value = (2, 1)  # Feb 1
        mock_datetime.now.return_value = datetime(2026, 2, 1)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = CFBDClient()
        assert client.get_current_season() == 2026

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_august(self, mock_datetime, mock_end_date):
        """August (season start) should return current year."""
        mock_end_date.return_value = (2, 1)  # Feb 1
        mock_datetime.now.return_value = datetime(2026, 8, 1)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = CFBDClient()
        assert client.get_current_season() == 2026

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_custom_end_date(self, mock_datetime, mock_end_date):
        """Test with custom season end date (Jan 20)."""
        mock_end_date.return_value = (1, 20)  # Jan 20
        mock_datetime.now.return_value = datetime(2026, 1, 19)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = CFBDClient()
        assert client.get_current_season() == 2025  # Before end date

        mock_datetime.now.return_value = datetime(2026, 1, 20)
        assert client.get_current_season() == 2026  # On end date

    @patch('src.integrations.cfbd_client.get_season_end_date')
    @patch('src.integrations.cfbd_client.datetime')
    def test_get_current_season_year_boundary(self, mock_datetime, mock_end_date):
        """Test transition from Dec 31 to Jan 1."""
        mock_end_date.return_value = (2, 1)  # Feb 1

        # December 31, 2025 → 2025
        mock_datetime.now.return_value = datetime(2025, 12, 31, 23, 59, 59)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        client = CFBDClient()
        assert client.get_current_season() == 2025

        # January 1, 2026 → 2025 (playoffs ongoing)
        mock_datetime.now.return_value = datetime(2026, 1, 1, 0, 0, 0)
        assert client.get_current_season() == 2025
```

### Manual Testing Checklist:

- [ ] Test with current date in December → should show current year
- [ ] Test with mocked date of January 10, 2026 → should show 2025 season
- [ ] Test with mocked date of February 2, 2026 → should show 2026 season
- [ ] Verify CFBD API calls use correct season year
- [ ] Check frontend displays correct "(Current)" season marker
- [ ] Confirm weekly update script processes correct season

## Notes for Developer:

- The implementation needs to import `get_season_end_date()` from Story 1
- Consider using Python's `unittest.mock.patch` to freeze time in unit tests
- The existing `is_active_season()` function in `weekly_update.py` may also need updating in Story 3
- Watch for timezone considerations - using `datetime.now()` is fine for local server time

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List
**Modified:**
- `src/integrations/cfbd_client.py` - Updated `get_current_season()` method with date-based logic (lines 332-373)
- `tests/test_cfbd_client.py` - Updated existing test and added 9 comprehensive tests for season logic

**Created:**
- None

**Deleted:**
- None

### Completion Notes
- Successfully updated `get_current_season()` method with date-based season detection logic
- Method now correctly handles January transition period (returns previous year before season end date)
- Fixed initial logic bug where January was always returning previous year (needed to handle custom end dates in January)
- All 36 tests in test_cfbd_client.py pass (including 9 new season detection tests + 1 updated test)
- Updated method docstring with comprehensive explanation and examples
- Logic correctly handles:
  - Months before season end month (e.g., January when end is Feb): returns previous year
  - Days before end date in end month: returns previous year
  - On/after end date through December: returns current year
- No regressions in existing CFBD API functionality
- Method signature unchanged - backward compatible

### Change Log
1. Updated `get_current_season()` method in cfbd_client.py (lines 332-373)
2. Rewrote method docstring with season span explanation and examples
3. Implemented date comparison logic using `get_season_end_date()` from Story 1
4. Updated existing test in TestCFBDClient::test_get_current_season to use mock for season end date
5. Created TestGetCurrentSeasonWithDateLogic class with 9 comprehensive tests (lines 428-523)
6. Fixed logic bug: removed January-specific case to properly handle custom end dates
7. All tests pass - no regressions detected

### Debug Log
- **Issue 1**: Initial test failure on `test_get_current_season_custom_end_date_on`
  - **Root Cause**: Logic had special case for January that always returned previous year, but should check against end date
  - **Fix**: Removed January-specific condition, unified logic to check `current_month < season_end_month` first
  - **Resolution**: All tests now pass

### Status
**Ready for Review**
