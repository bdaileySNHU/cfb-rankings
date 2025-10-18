# Story 005: Remove Hardcoded Season Years & Implement Dynamic Detection

**Story ID**: STORY-005
**Epic**: EPIC-002 - Dynamic Season Management & Complete Game Import
**Status**: Ready for Development
**Priority**: High
**Estimate**: 4-6 hours
**Complexity**: Medium-High

---

## User Story

**As a** system administrator and website user,
**I want** the system to automatically determine the current season without hardcoded values,
**So that** the site automatically works for future seasons without manual code updates each year.

---

## Story Context

### Existing System Integration

- **Integrates with:**
  - `import_real_data.py` (data import script)
  - `update_games.py` (weekly update script)
  - `frontend/games.html` (games listing page)
  - `frontend/js/comparison.js` (team comparison feature)
  - `main.py` (FastAPI backend)

- **Technology:**
  - Backend: Python 3.11+, FastAPI, SQLAlchemy
  - Frontend: Vanilla JavaScript (ES6+)
  - Database: SQLite with Season model

- **Follows pattern:**
  - Backend API endpoint pattern (`main.py`)
  - Frontend API service pattern (`frontend/js/api.js`)
  - Import script CLI argument pattern

- **Touch points:**
  - Utilities from Story 1 (`cfbd_client.py`)
  - Season model (`models.py`)
  - Frontend API service (`api.js`)
  - All import scripts

---

## Acceptance Criteria

### Functional Requirements - Backend

1. **Import Script Dynamic Detection:**
   - `import_real_data.py` uses `get_current_season()` instead of hardcoded `2025`
   - User is shown detected season: "Detected Season: 2025"
   - User can still override with `--season YYYY` flag
   - Default max week calculated from `get_current_week()` instead of prompting "1-6"

2. **Update Script Smart Detection:**
   - `update_games.py` automatically detects season from database (active season)
   - Auto-detects starting week from highest week in database
   - Calculates end week from `get_current_week()` + 1 (to catch in-progress weeks)
   - User can override with `--start-week` and `--end-week` flags

3. **New API Endpoint:**
   - `GET /api/seasons/active` endpoint returns currently active season
   - Response format: `{"year": 2025, "current_week": 8, "is_active": true}`
   - Returns 404 if no active season exists
   - Handles multiple active seasons gracefully (returns most recent)

### Functional Requirements - Frontend

4. **Games Page Dynamic Season:**
   - `frontend/games.html` fetches active season from `/api/seasons/active`
   - Falls back to current year if API fails: `new Date().getFullYear()`
   - User sees loading indicator while fetching season
   - Error message if both API and fallback fail

5. **Comparison Page Dynamic Season:**
   - `frontend/js/comparison.js` uses same pattern as games page
   - Fetches from `/api/seasons/active` with fallback
   - Consistent behavior across all frontend pages

### Integration Requirements

6. **CLI Backward Compatibility:**
   - All existing command-line arguments continue to work
   - New optional flags added: `--season YYYY`, `--start-week N`, `--end-week N`
   - Help text updated to show new auto-detection behavior
   - Examples in help output

7. **Frontend Graceful Degradation:**
   - If `/api/seasons/active` fails, frontend uses current year
   - User sees error in console: "Unable to detect season, using 2025"
   - Page remains functional (doesn't break)
   - Error logged for debugging

8. **Database Compatibility:**
   - No schema changes required
   - Uses existing `Season` model fields
   - Works with existing data (no migration needed)

### Quality Requirements

9. **Test Coverage:**
   - Unit tests for new API endpoint
   - Integration tests for import scripts with `--season` override
   - Frontend tests for season fetching with mocked API
   - Test all CLI arguments work correctly

10. **Documentation:**
    - Update `docs/UPDATE-GAME-DATA.md` with new auto-detection behavior
    - Update script help text (`--help`) to mention auto-detection
    - Add docstrings for new API endpoint
    - Comment hardcoded fallback values in frontend

11. **Existing Functionality:**
    - All 236 existing tests pass without modification
    - Existing import workflow unchanged (except auto-detection added)
    - Frontend pages continue to work if API fails

---

## Files to Modify

### Backend Files

**`import_real_data.py`** - Remove hardcoded season year:

**Lines to Change:**
- Line 233: `Season(year=2025, ...)` → `Season(year=current_season, ...)`
- Line 238: `import_teams(cfbd, db, year=2025)` → `import_teams(cfbd, db, year=current_season)`
- Line 246-249: Remove hardcoded "Week 6" message
- Line 254: `import_games(..., year=2025, ...)` → `import_games(..., year=current_season, ...)`

**New Code:**
```python
# Add at top of main()
cfbd = CFBDClient(api_key)
current_season = cfbd.get_current_season()
max_week_available = cfbd.get_current_week(current_season)

print(f"Detected current season: {current_season}")
print(f"Latest completed week: {max_week_available or 'None (pre-season)'}")

# Add argparse for overrides
import argparse
parser = argparse.ArgumentParser(description='Import college football data')
parser.add_argument('--season', type=int, help=f'Season year (default: auto-detect, currently {current_season})')
parser.add_argument('--max-week', type=int, help='Maximum week to import (default: all available)')
args = parser.parse_args()

season = args.season or current_season
max_week = args.max_week or max_week_available
```

**`update_games.py`** - Smart auto-detection:

**New logic:**
```python
# Auto-detect season from database
def get_active_season(db) -> Optional[int]:
    """Get currently active season from database"""
    season = db.query(Season).filter(Season.is_active == True).first()
    return season.year if season else None

# Auto-detect start week
def get_last_imported_week(db, season: int) -> int:
    """Get highest week number in database for season"""
    highest = db.query(Game).filter(Game.season == season).order_by(Game.week.desc()).first()
    return highest.week if highest else 0

# In main()
season = args.season or get_active_season(db) or cfbd.get_current_season()
start_week = args.start_week or get_last_imported_week(db, season)
end_week = args.end_week or (cfbd.get_current_week(season) or start_week + 4)
```

**`main.py`** - Add new API endpoint:

```python
@app.get("/api/seasons/active")
def get_active_season(db: Session = Depends(get_db)):
    """
    Get the currently active season.

    Returns:
        dict: Active season data with year, current_week, is_active

    Raises:
        HTTPException: 404 if no active season found
    """
    season = db.query(Season).filter(Season.is_active == True).order_by(Season.year.desc()).first()

    if not season:
        raise HTTPException(status_code=404, detail="No active season found")

    return {
        "year": season.year,
        "current_week": season.current_week,
        "is_active": season.is_active
    }
```

### Frontend Files

**`frontend/games.html`** - Line 84:

**Before:**
```javascript
api.getGames({ season: 2025, limit: 200 }),
```

**After:**
```javascript
// Fetch active season from API
async function getActiveSeason() {
  try {
    const response = await fetch('/api/seasons/active');
    if (!response.ok) throw new Error('Failed to fetch active season');
    const data = await response.json();
    return data.year;
  } catch (error) {
    console.error('Unable to detect season, using current year:', error);
    // Fallback to current year
    return new Date().getFullYear();
  }
}

// In loadData():
const activeSeason = await getActiveSeason();
api.getGames({ season: activeSeason, limit: 200 }),
```

**`frontend/js/comparison.js`** - Line 47:

Same pattern as `games.html`, extract `getActiveSeason()` to `api.js` for reuse:

**`frontend/js/api.js`** - Add helper method:

```javascript
// Add to ApiService class
async getActiveSeason() {
  try {
    const response = await this.fetch('/seasons/active');
    return response.year;
  } catch (error) {
    console.error('Failed to fetch active season:', error);
    return new Date().getFullYear(); // Fallback to current year
  }
}
```

Then use in both `games.html` and `comparison.js`:
```javascript
const activeSeason = await api.getActiveSeason();
```

---

## Implementation Checklist

### Backend Changes

- [ ] Add argparse to `import_real_data.py`
- [ ] Replace line 233 hardcoded `2025`
- [ ] Replace line 238 hardcoded `2025`
- [ ] Replace line 254 hardcoded `2025`
- [ ] Update lines 246-249 prompt message
- [ ] Add `--season` and `--max-week` CLI arguments
- [ ] Test import script with and without `--season` flag
- [ ] Add `get_active_season()` to `update_games.py`
- [ ] Add `get_last_imported_week()` to `update_games.py`
- [ ] Add auto-detection logic to `update_games.py` main()
- [ ] Add `--start-week` and `--end-week` CLI arguments
- [ ] Test update script auto-detection
- [ ] Add `/api/seasons/active` endpoint to `main.py`
- [ ] Test new API endpoint with curl

### Frontend Changes

- [ ] Add `getActiveSeason()` method to `frontend/js/api.js`
- [ ] Update `frontend/games.html` line 84
- [ ] Update `frontend/js/comparison.js` line 47
- [ ] Test frontend with working API
- [ ] Test frontend with API failure (graceful fallback)
- [ ] Verify loading states work correctly
- [ ] Check browser console for errors

### Testing

- [ ] All 236 existing tests pass
- [ ] Add unit test for `/api/seasons/active` endpoint
- [ ] Add test for import script `--season` override
- [ ] Add test for update script auto-detection
- [ ] Add frontend test for season fetching (if E2E tests exist)
- [ ] Manual testing: import with no args (auto-detects)
- [ ] Manual testing: import with `--season 2024` (uses override)
- [ ] Manual testing: frontend loads active season

### Documentation

- [ ] Update `docs/UPDATE-GAME-DATA.md` (mention auto-detection)
- [ ] Update `import_real_data.py --help` text
- [ ] Update `update_games.py --help` text
- [ ] Add comments to frontend fallback logic
- [ ] Update EPIC-002 status to "Story 2 Complete"

---

## Testing Strategy

### Backend API Tests

**Test:** `/api/seasons/active` endpoint

```python
def test_get_active_season_success(test_client, test_db):
    """Test active season endpoint with valid data"""
    season = SeasonFactory(year=2025, current_week=8, is_active=True)
    test_db.add(season)
    test_db.commit()

    response = test_client.get("/api/seasons/active")

    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2025
    assert data["current_week"] == 8
    assert data["is_active"] is True

def test_get_active_season_not_found(test_client, test_db):
    """Test active season endpoint with no active season"""
    # No active season in database
    response = test_client.get("/api/seasons/active")

    assert response.status_code == 404
    assert "No active season found" in response.json()["detail"]

def test_get_active_season_multiple_active(test_client, test_db):
    """Test returns most recent when multiple active seasons exist"""
    season_2024 = SeasonFactory(year=2024, is_active=True)
    season_2025 = SeasonFactory(year=2025, is_active=True)
    test_db.add_all([season_2024, season_2025])
    test_db.commit()

    response = test_client.get("/api/seasons/active")

    assert response.status_code == 200
    assert response.json()["year"] == 2025  # Returns most recent
```

### Import Script Tests

**Test:** `import_real_data.py` auto-detection and overrides

```bash
# Test 1: Auto-detection (should detect 2025)
python3 import_real_data.py
# Verify output: "Detected current season: 2025"

# Test 2: Override with --season
python3 import_real_data.py --season 2024
# Verify uses 2024 instead

# Test 3: Show help
python3 import_real_data.py --help
# Verify mentions auto-detection
```

### Frontend Tests

**Test:** Season fetching with API success and failure

```javascript
// Test 1: API returns active season
test('loads active season from API', async () => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ year: 2025 })
    })
  );

  const season = await api.getActiveSeason();
  expect(season).toBe(2025);
});

// Test 2: API fails, fallback to current year
test('falls back to current year on API failure', async () => {
  global.fetch = jest.fn(() => Promise.reject('API Error'));

  const season = await api.getActiveSeason();
  expect(season).toBe(new Date().getFullYear());
});
```

---

## Risk Assessment

### Primary Risks

**Risk 1: Frontend API Call Adds Latency**
- **Scenario:** `/api/seasons/active` call slows page load
- **Mitigation:**
  - Cache response in sessionStorage for 1 hour
  - Load season asynchronously, show loading state
  - Fallback is instant (no network call)
- **Rollback:** Remove API call, use hardcoded year fallback

**Risk 2: Auto-Detection Detects Wrong Year**
- **Scenario:** Season detection logic has bug, imports wrong year
- **Mitigation:**
  - Show detected season to user before proceeding
  - Require user confirmation in import script
  - `--season` override always available
- **Rollback:** Use `--season 2025` to override

**Risk 3: No Active Season in Database**
- **Scenario:** Fresh install, no season marked active
- **Mitigation:**
  - Import script creates season as active by default
  - Frontend falls back to current year
  - Error handling prevents crashes
- **Rollback:** Frontend already has fallback

### Compatibility Impact

- **Breaking Changes:** None
- **New API Endpoint:** `/api/seasons/active` (additive, optional)
- **CLI Arguments:** All new flags are optional
- **Database:** No schema changes

---

## Definition of Done

- [ ] All hardcoded `2025` references removed from:
  - `import_real_data.py`
  - `update_games.py`
  - `frontend/games.html`
  - `frontend/js/comparison.js`

- [ ] New `/api/seasons/active` API endpoint working and tested

- [ ] Import scripts use `get_current_season()` from Story 1

- [ ] Frontend fetches active season from backend API

- [ ] CLI overrides (`--season`, `--start-week`, `--end-week`) working

- [ ] Frontend graceful fallback working (tested by simulating API failure)

- [ ] All 236 existing tests pass

- [ ] New API endpoint has unit tests

- [ ] Documentation updated (`UPDATE-GAME-DATA.md`, script help text)

- [ ] Manual testing completed:
  - [ ] Import with auto-detection
  - [ ] Import with `--season` override
  - [ ] Update with auto-detection
  - [ ] Frontend loads correct season
  - [ ] Frontend fallback when API fails

- [ ] No lint errors or warnings

- [ ] Code reviewed and approved

---

## Dependencies

**Blocked By:**
- Story 1 (STORY-004) - Requires `get_current_season()` and `get_current_week()` utilities

**Blocks:**
- Story 3 (STORY-006) - Validation can use dynamic week detection

---

## Rollback Plan

If issues arise after deployment:

1. **Emergency Rollback (Git):**
   ```bash
   git revert <commit-hash>
   sudo systemctl restart cfb-rankings
   ```

2. **Manual Override Workaround:**
   ```bash
   # Run import with explicit season
   python3 import_real_data.py --season 2025 --max-week 8
   ```

3. **Frontend Hotfix:**
   - Frontend already has fallback to current year
   - Can temporarily hardcode if needed:
   ```javascript
   const activeSeason = 2025; // Temporary hardcode
   ```

4. **Database Fix:**
   - If wrong season imported, can re-run with correct `--season` flag
   - No schema changes to rollback

---

## Developer Handoff Notes

**Key Implementation Points:**

1. **Import Script Flow:**
   - Detect season → Show to user → Proceed with detected or overridden value
   - Always inform user what season is being used

2. **Frontend Pattern:**
   - Extract `getActiveSeason()` to `api.js` for reuse
   - Use async/await consistently
   - Always have fallback to prevent page breaks

3. **Error Messages:**
   - User-friendly: "Unable to detect season, using 2025"
   - Developer-friendly in console: Include full error details

4. **Testing Focus:**
   - Test overrides work correctly
   - Test fallbacks work when API fails
   - Test with both 2024 and 2025 seasons

**Code Review Checklist:**

- [ ] No remaining hardcoded `2025` in production code
- [ ] All CLI args documented in help text
- [ ] Frontend has try/catch with fallback
- [ ] API endpoint handles edge cases (no active season)
- [ ] Tests cover success and failure paths

---

**Story Created:** 2025-10-18
**Created By:** John (PM Agent)
**Ready for Development:** After Story 1 completes
**Assigned To:** Dev Agent (James)
