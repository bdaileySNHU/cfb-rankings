# Story 004: Add Dynamic Season & Week Detection Utility

**Story ID**: STORY-004
**Epic**: EPIC-002 - Dynamic Season Management & Complete Game Import
**Status**: Ready for Development
**Priority**: High
**Estimate**: 3-5 hours
**Complexity**: Medium

---

## User Story

**As a** system administrator running the College Football Rankings system,
**I want** the import scripts to automatically detect the current season year and current week,
**So that** I don't have to manually update hardcoded values every year or specify parameters every week.

---

## Story Context

### Existing System Integration

- **Integrates with:** `cfbd_client.py` (CFBD API wrapper)
- **Technology:** Python 3.11+, requests library, datetime module
- **Follows pattern:** Existing `CFBDClient` class structure with `_get()` method for API calls
- **Touch points:**
  - `import_real_data.py` (will use these utilities in Story 2)
  - `update_games.py` (will use these utilities in Story 2)
  - Unit tests in `tests/unit/test_cfbd_client.py`

---

## Acceptance Criteria

### Functional Requirements

1. **Season Detection:**
   - `get_current_season()` function returns correct year based on calendar date
   - New season starts on August 1 each year
   - During Jan-July, returns current calendar year
   - During Aug-Dec, returns current calendar year
   - Example: On July 31, 2025 → returns 2025; On August 1, 2025 → returns 2025

2. **Week Detection from API:**
   - `get_current_week(year)` function queries CFBD API endpoint `/games`
   - Returns highest week number that has completed games
   - Handles empty API responses gracefully
   - Returns `None` or `0` when no games have been played yet (pre-season)

3. **Calendar-Based Fallback:**
   - `estimate_current_week(season_year)` provides fallback when API unavailable
   - Calculates weeks since Labor Day (first Monday of September)
   - Returns reasonable estimate (1-15 for regular season)
   - Returns `0` if before season start, `15` if after regular season

### Integration Requirements

4. **Existing CFBD Client Integration:**
   - New methods added to `CFBDClient` class in `cfbd_client.py`
   - Methods use existing `self._get()` pattern for API calls
   - Error handling follows existing patterns (try/except, logging)
   - No breaking changes to existing CFBD client methods

5. **Error Handling:**
   - API failures return fallback values (not crash)
   - Network errors logged but don't stop execution
   - Invalid API responses handled gracefully

6. **Configuration:**
   - Season start date configurable (default: August 1)
   - Week calculation parameters configurable
   - All constants documented with comments

### Quality Requirements

7. **Test Coverage:**
   - Unit tests for `get_current_season()` with various dates
   - Unit tests for `get_current_week()` with mocked API responses
   - Unit tests for `estimate_current_week()` calendar logic
   - Edge case tests: off-season, week 1, week 15, invalid data
   - Achieve >90% coverage for new functions

8. **Documentation:**
   - Docstrings for all new functions with examples
   - Comments explaining season start logic
   - README update not required for this story (deferred to Story 2)

9. **Existing Functionality:**
   - All existing CFBD client methods continue to work
   - No changes to existing function signatures
   - All 236 existing tests pass without modification

---

## Technical Implementation Details

### Files to Modify

**`cfbd_client.py`** - Add new methods to `CFBDClient` class:

```python
def get_current_season(self) -> int:
    """
    Determine the current college football season year based on calendar date.

    Season year logic:
    - August 1 through December 31: Current calendar year
    - January 1 through July 31: Current calendar year

    Examples:
        July 31, 2025 → 2025 season
        August 1, 2025 → 2025 season (new season starts)
        December 31, 2025 → 2025 season
        January 15, 2026 → 2026 season (next year's planning)

    Returns:
        int: The current season year (e.g., 2025)
    """
    # Implementation here
```

```python
def get_current_week(self, season: int) -> Optional[int]:
    """
    Get the current week of the season from CFBD API.

    Queries the /games endpoint to find the highest week number
    that has completed games.

    Args:
        season: The season year to check

    Returns:
        int: Highest completed week number (1-15), or None if no games played

    Example:
        >>> client.get_current_week(2025)
        8  # Week 8 is the latest with completed games
    """
    # Implementation here
```

```python
def estimate_current_week(self, season: int) -> int:
    """
    Estimate current week based on calendar (fallback when API unavailable).

    Calculates weeks elapsed since the season start (first Saturday after Labor Day).

    Args:
        season: The season year

    Returns:
        int: Estimated week number (0-15)
            0 = pre-season
            1-15 = regular season weeks

    Note:
        This is a fallback estimate only. Use get_current_week() for accurate data.
    """
    # Implementation here
```

### Implementation Notes

**Season Start Date Calculation:**
- Labor Day = First Monday of September
- Season starts = First Saturday after Labor Day (typically week after)
- Store as constant: `SEASON_START_MONTH = 9` (September)

**Week Calculation Logic:**
```python
from datetime import datetime, timedelta

def _find_labor_day(year: int) -> datetime:
    """Find Labor Day (first Monday of September)"""
    september_first = datetime(year, 9, 1)
    # Find first Monday
    days_until_monday = (7 - september_first.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 0  # Already Monday
    labor_day = september_first + timedelta(days=days_until_monday)
    return labor_day

def _find_season_start(year: int) -> datetime:
    """Find season start (first Saturday after Labor Day)"""
    labor_day = _find_labor_day(year)
    days_until_saturday = (5 - labor_day.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7  # Next Saturday
    return labor_day + timedelta(days=days_until_saturday)
```

**CFBD API Query for Current Week:**
```python
def get_current_week(self, season: int) -> Optional[int]:
    # Query all games for the season
    games = self.get_games(season, season_type='regular')

    if not games:
        return None

    # Find max week with completed games (non-null scores)
    max_week = 0
    for game in games:
        if game.get('homePoints') is not None and game.get('awayPoints') is not None:
            week = game.get('week', 0)
            if week > max_week:
                max_week = week

    return max_week if max_week > 0 else None
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/unit/test_cfbd_client.py` (add to existing file)

```python
class TestSeasonDetection:
    def test_get_current_season_august(self):
        """Test season detection in August (new season starts)"""
        # Mock date to August 1, 2025
        with mock_date('2025-08-01'):
            client = CFBDClient()
            assert client.get_current_season() == 2025

    def test_get_current_season_january(self):
        """Test season detection in January (next year planning)"""
        with mock_date('2026-01-15'):
            client = CFBDClient()
            assert client.get_current_season() == 2026

    def test_get_current_season_july(self):
        """Test season detection in July (current year)"""
        with mock_date('2025-07-31'):
            client = CFBDClient()
            assert client.get_current_season() == 2025

class TestWeekDetection:
    def test_get_current_week_with_games(self, mock_cfbd_api):
        """Test week detection when games exist"""
        mock_cfbd_api.return_value = [
            {'week': 1, 'homePoints': 35, 'awayPoints': 28},
            {'week': 2, 'homePoints': 21, 'awayPoints': 24},
            {'week': 8, 'homePoints': 42, 'awayPoints': 17},
            {'week': 9, 'homePoints': None, 'awayPoints': None},  # Future game
        ]

        client = CFBDClient()
        assert client.get_current_week(2025) == 8

    def test_get_current_week_no_games(self, mock_cfbd_api):
        """Test week detection when no games played yet"""
        mock_cfbd_api.return_value = []

        client = CFBDClient()
        assert client.get_current_week(2025) is None

    def test_get_current_week_api_failure(self, mock_cfbd_api):
        """Test week detection when API fails"""
        mock_cfbd_api.side_effect = RequestException("API Error")

        client = CFBDClient()
        assert client.get_current_week(2025) is None

class TestWeekEstimation:
    def test_estimate_current_week_week1(self):
        """Test week estimation during Week 1"""
        # Mock date to first Saturday after Labor Day 2025
        with mock_date('2025-09-06'):  # Assuming this is Week 1
            client = CFBDClient()
            assert client.estimate_current_week(2025) == 1

    def test_estimate_current_week_midseason(self):
        """Test week estimation mid-season"""
        with mock_date('2025-10-25'):  # Approximately Week 8
            client = CFBDClient()
            week = client.estimate_current_week(2025)
            assert 7 <= week <= 9  # Allow 1 week margin

    def test_estimate_current_week_preseason(self):
        """Test week estimation before season starts"""
        with mock_date('2025-08-15'):  # Before Labor Day
            client = CFBDClient()
            assert client.estimate_current_week(2025) == 0
```

### Edge Cases to Test

1. **Leap Years:** February 29 date handling
2. **Year Boundaries:** December 31 → January 1
3. **API Timeouts:** CFBD API slow or unavailable
4. **Invalid API Data:** Malformed JSON responses
5. **Week 0 Games:** Some FBS teams play "Week 0" games
6. **Conference Championship Week:** Week 14-15 games
7. **Off-Season:** February-July (no games)

---

## Risk Assessment

### Primary Risks

**Risk 1: Calendar Logic Bugs**
- **Scenario:** Labor Day calculation incorrect, week estimation off by 1-2 weeks
- **Mitigation:**
  - Thorough unit tests with known dates
  - Manual verification against 2024 and 2025 calendars
  - Use well-tested `datetime` library functions
- **Rollback:** Utilities are not yet used by import scripts, can be fixed without impact

**Risk 2: CFBD API Changes**
- **Scenario:** CFBD changes API response format, breaks week detection
- **Mitigation:**
  - Defensive parsing with `.get()` and type checks
  - Fallback to calendar estimation if API parsing fails
  - Log warnings when API response is unexpected
- **Rollback:** Utilities return fallback values, import scripts can still work

**Risk 3: Timezone Issues**
- **Scenario:** Server timezone different from user, date calculation wrong
- **Mitigation:**
  - Use UTC for all date calculations
  - Document timezone assumptions
  - Add timezone tests
- **Rollback:** Easy fix, just convert to UTC consistently

### Compatibility Impact

- **No breaking changes** - All new code, no existing code modified
- **No database changes**
- **No API changes**
- **Zero risk to existing functionality**

---

## Definition of Done

- [ ] `get_current_season()` implemented and returns correct year for all test dates
- [ ] `get_current_week()` implemented and queries CFBD API correctly
- [ ] `estimate_current_week()` implemented with calendar logic
- [ ] All unit tests written and passing (>90% coverage for new code)
- [ ] Edge cases tested: off-season, week 1, week 15, API failures
- [ ] Docstrings added with examples for all new functions
- [ ] Code follows existing `CFBDClient` class patterns
- [ ] All 236 existing tests pass without modification
- [ ] No lint warnings or errors
- [ ] Code reviewed and ready for Story 2 integration

---

## Dependencies

**Blocked By:**
- None (independent utility functions)

**Blocks:**
- Story 2 (needs these utilities)
- Story 3 (validation uses week detection)

---

## Developer Handoff Notes

**Integration Points for Next Stories:**

After this story completes, Story 2 will use these utilities like this:

```python
# In import_real_data.py
cfbd = CFBDClient(api_key)
current_season = cfbd.get_current_season()
current_week = cfbd.get_current_week(current_season) or cfbd.estimate_current_week(current_season)

print(f"Detected Season: {current_season}")
print(f"Detected Current Week: {current_week}")
```

**Testing Approach:**

Use `freezegun` or similar library to mock `datetime.now()` for consistent testing:

```python
from freezegun import freeze_time

@freeze_time("2025-08-01")
def test_season_start():
    assert client.get_current_season() == 2025
```

**Key Files:**
- Add methods to: `cfbd_client.py`
- Add tests to: `tests/unit/test_cfbd_client.py`

---

**Story Created:** 2025-10-18
**Created By:** John (PM Agent)
**Ready for Development:** Yes
**Assigned To:** Dev Agent (James)
