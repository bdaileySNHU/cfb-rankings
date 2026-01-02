# Story 1: Add Configurable Season End Date - Brownfield Addition

**Epic:** Season End Date Logic Fix
**Story ID:** story-season-end-date-config
**Priority:** High
**Effort:** Small (2-3 hours)

## User Story

As a **system administrator**,
I want **a configurable season end date setting**,
So that **the system can correctly determine when one college football season ends and the next begins, accounting for playoffs extending into the new calendar year**.

## Story Context

### Existing System Integration:

- **Integrates with:** Configuration management system (environment variables)
- **Technology:** Python, environment variables, existing config pattern
- **Follows pattern:** Existing environment variable configuration (e.g., `CFBD_API_KEY`, `CFBD_MONTHLY_LIMIT`)
- **Touch points:**
  - Environment variable loading in application startup
  - Configuration documentation (README.md)
  - Season detection logic (will be consumed by Story 2)

## Acceptance Criteria

### Functional Requirements:

1. **Add environment variable `CFB_SEASON_END_DATE`** with default value of `"02-01"` (February 1st, MM-DD format)
2. **Load and validate the configuration** - parse the date string and handle invalid formats gracefully with clear error messages
3. **Document the configuration** - update README.md with the new environment variable, its purpose, format, and default value

### Integration Requirements:

4. **Existing configuration loading** continues to work unchanged - no breaking changes to current env var processing
5. **New configuration follows existing pattern** - matches style and approach of other environment variables (e.g., `CFBD_API_KEY`)
6. **Configuration is accessible** to season detection logic without requiring changes to existing function signatures

### Quality Requirements:

7. **Unit tests added** for configuration loading and validation (valid date, invalid format, missing value defaults)
8. **Documentation updated** in README.md with clear examples
9. **No regression** in existing environment variable loading verified

## Technical Notes

### Integration Approach:
- Add new environment variable `CFB_SEASON_END_DATE` with default `"02-01"`
- Create helper function `get_season_end_date()` to parse the configuration (returns month and day as integers)
- Place configuration loading in appropriate module (likely `src/integrations/cfbd_client.py` or separate config module if one exists)
- Use Python's `os.getenv()` with default value, similar to existing pattern

### Existing Pattern Reference:
```python
# Example from existing codebase pattern
CFBD_API_KEY = os.getenv("CFBD_API_KEY", "")
CFBD_MONTHLY_LIMIT = int(os.getenv("CFBD_MONTHLY_LIMIT", "30000"))
```

### Key Constraints:
- Must use MM-DD format (e.g., "02-01" for February 1st) for simplicity
- Must provide sensible default (February 1st accounts for late championship games)
- Must handle invalid formats gracefully without crashing application
- Configuration should be read once at startup, not repeatedly

### Suggested Implementation:

```python
# In appropriate config/settings module or cfbd_client.py
import os
from datetime import datetime

def get_season_end_date() -> tuple[int, int]:
    """
    Get the configured season end date (month, day).

    Returns:
        tuple[int, int]: (month, day) when CFB season ends

    Raises:
        ValueError: If CFB_SEASON_END_DATE format is invalid
    """
    default_end = "02-01"  # February 1st
    end_date_str = os.getenv("CFB_SEASON_END_DATE", default_end)

    try:
        month, day = map(int, end_date_str.split("-"))
        # Validate month and day ranges
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            raise ValueError(f"Invalid date components: month={month}, day={day}")
        return (month, day)
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"CFB_SEASON_END_DATE must be in MM-DD format (e.g., '02-01'). "
            f"Got: '{end_date_str}'. Error: {e}"
        )
```

## Risk and Compatibility Check

### Minimal Risk Assessment:

- **Primary Risk:** Invalid date configuration could cause application startup failure or incorrect season detection
- **Mitigation:**
  - Provide clear default value
  - Add validation with helpful error messages
  - Unit tests covering valid and invalid inputs
  - Documentation with examples
- **Rollback:** Remove environment variable and configuration loading code - system returns to current behavior (no external dependencies)

### Compatibility Verification:

- [x] **No breaking changes to existing APIs** - This is purely additive configuration
- [x] **Database changes** - None required
- [x] **UI changes** - None required (backend configuration only)
- [x] **Performance impact** - Negligible (configuration loaded once at startup)

## Definition of Done

- [x] `CFB_SEASON_END_DATE` environment variable added with default `"02-01"`
- [x] `get_season_end_date()` helper function created and tested
- [x] Configuration validation handles invalid formats with clear error messages
- [x] Unit tests pass for valid date, invalid format, missing value (uses default)
- [x] README.md updated with new environment variable documentation including:
  - Variable name and purpose
  - Format specification (MM-DD)
  - Default value (02-01)
  - Example usage
- [x] Code follows existing environment variable patterns
- [x] Existing configuration loading still works (no regressions)
- [x] Configuration is accessible for use in Story 2

## Validation Checklist

### Scope Validation:
- [x] Story can be completed in one development session (2-3 hours)
- [x] Integration approach is straightforward (standard env var pattern)
- [x] Follows existing patterns exactly (matches CFBD_API_KEY pattern)
- [x] No design or architecture work required

### Clarity Check:
- [x] Story requirements are unambiguous
- [x] Integration points clearly specified (env vars, config loading)
- [x] Success criteria are testable (unit tests, documentation check)
- [x] Rollback approach is simple (remove added code)

## Testing Guidance

### Unit Tests to Add:

```python
def test_get_season_end_date_default():
    """Test default season end date when env var not set."""
    # Clear env var if set
    if "CFB_SEASON_END_DATE" in os.environ:
        del os.environ["CFB_SEASON_END_DATE"]
    month, day = get_season_end_date()
    assert month == 2
    assert day == 1

def test_get_season_end_date_custom():
    """Test custom season end date."""
    os.environ["CFB_SEASON_END_DATE"] = "01-20"
    month, day = get_season_end_date()
    assert month == 1
    assert day == 20

def test_get_season_end_date_invalid_format():
    """Test invalid date format raises error."""
    os.environ["CFB_SEASON_END_DATE"] = "invalid"
    with pytest.raises(ValueError, match="MM-DD format"):
        get_season_end_date()

def test_get_season_end_date_invalid_values():
    """Test invalid month/day values raise error."""
    os.environ["CFB_SEASON_END_DATE"] = "13-45"  # Invalid month and day
    with pytest.raises(ValueError):
        get_season_end_date()
```

## README.md Documentation Example:

```markdown
### Environment Variables

- `CFB_SEASON_END_DATE` (optional): The date when the college football season ends, in MM-DD format. Used to correctly determine the active season during January when the previous season's playoffs extend into the new calendar year. Default: `02-01` (February 1st)
  - Example: `CFB_SEASON_END_DATE=01-20` (January 20th)
```

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List
**Modified:**
- `src/integrations/cfbd_client.py` - Added `get_season_end_date()` function
- `tests/test_cfbd_client.py` - Added `TestGetSeasonEndDate` test class with 8 tests
- `README.md` - Added `CFB_SEASON_END_DATE` environment variable documentation

**Created:**
- None

**Deleted:**
- None

### Completion Notes
- Successfully implemented `get_season_end_date()` function in `src/integrations/cfbd_client.py:245-280`
- Added comprehensive unit tests with 8 test cases covering valid/invalid inputs
- All 27 tests in test_cfbd_client.py pass (including 8 new tests)
- Documentation updated in 2 locations in README.md (Configuration section and Setup section)
- Function follows existing environment variable pattern (similar to CFBD_MONTHLY_LIMIT)
- Default value set to "02-01" (February 1st) to account for playoff games in January
- Validation includes proper error messages for invalid formats
- Configuration is now accessible for Story 2 implementation

### Change Log
1. Added `get_season_end_date()` function to cfbd_client.py (lines 245-280)
2. Imported function in test file (line 18)
3. Created TestGetSeasonEndDate class with 8 comprehensive tests (lines 348-416)
4. Updated README.md Configuration section (line 87)
5. Updated README.md Setup section (line 427)
6. All tests pass - no regressions detected

### Debug Log
No issues encountered during implementation.

### Status
**Ready for Review**
