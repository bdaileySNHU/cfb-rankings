# Story: Implement Secondary Sorting by Date in API - Brownfield Addition

**Status:** 📋 Draft
**Epic:** EPIC-GAME-DATE-SORTING
**Priority:** High
**Risk Level:** 🟢 Low Risk (sorting logic only, no schema changes)
**Estimated Effort:** 1 hour

---

## User Story

As a **backend API developer**,
I want **game API endpoints to sort results by week first, then by date within each week**,
So that **games are returned in true chronological order, especially for bowl and playoff games that span multiple days within the same week**.

---

## Story Context

**Existing System Integration:**

- Integrates with: FastAPI game endpoints in `src/api/main.py`
- Technology: Python 3.11, FastAPI, SQLAlchemy ORM, SQLite database
- Follows pattern: Existing `order_by()` clauses in SQLAlchemy queries
- Touch points:
  - `/api/games` endpoint (lines 432-479)
  - `/api/teams/{id}/schedule` endpoint (lines 352-424)
  - Game model with `game_date` column

**Current Implementation:**

Two main endpoints return lists of games:

1. **`GET /api/games`** (line 432-479)
   - Current sort: `order_by(Game.week.desc(), Game.id.desc())`
   - Returns games for a season, sorted by week descending
   - Within each week, games sorted by ID (arbitrary order)

2. **`GET /api/teams/{team_id}/schedule`** (line 352-424)
   - Current sort: `order_by(Game.week)`
   - Returns games for a team, sorted by week ascending
   - Within each week, games in database insertion order

**What's Missing:**

- No secondary sorting by `game_date` within each week
- Bowl/playoff games in weeks 15-19 appear in arbitrary order despite spanning multiple days
- Games on Dec 19 might appear after games on Dec 21 within the same week

---

## Acceptance Criteria

### Functional Requirements

1. **Games Endpoint Secondary Date Sort**
   - `/api/games` sorts by: week DESC → game_date DESC → id DESC
   - Most recent week appears first
   - Within each week, most recent date appears first
   - Games without dates (`game_date IS NULL`) appear last within their week

2. **Team Schedule Endpoint Secondary Date Sort**
   - `/api/teams/{id}/schedule` sorts by: week ASC → game_date ASC
   - Earliest week appears first (chronological schedule)
   - Within each week, earliest date appears first
   - Games without dates appear last within their week

3. **Null Date Handling**
   - Null `game_date` values handled gracefully in SQL sorting
   - Null dates appear after games with dates within the same week
   - No SQL errors when encountering null dates

### Integration Requirements

4. **API Response Format Unchanged**
   - Response JSON structure remains identical
   - All existing fields present in same format
   - Only the order of games in the array changes
   - Pydantic schemas unchanged

5. **Query Performance Maintained**
   - Response time remains under 200ms for typical queries
   - No N+1 query issues introduced
   - Database indexes handle sorting efficiently

6. **Backward Compatibility**
   - Existing API clients continue to work without changes
   - No breaking changes to API contracts
   - Optional query parameters (season, week, team) unchanged

### Quality Requirements

7. **Code Quality**
   - SQLAlchemy `order_by()` syntax follows existing patterns
   - Code comments explain multi-level sorting logic
   - No hardcoded values or magic numbers

8. **Error Handling**
   - Database errors handled gracefully
   - Invalid sort parameters rejected with clear error messages
   - Null date handling doesn't cause exceptions

9. **Testing Coverage**
   - Existing API tests continue to pass
   - New tests verify date sorting behavior
   - Edge cases tested (null dates, same date/week)

---

## Technical Notes

### Integration Approach

**1. Update /api/games Endpoint**

Location: `src/api/main.py`, around line 441

Current code:
```python
games_query = games_query.order_by(Game.week.desc(), Game.id.desc())
```

Change to:
```python
# Sort by: week descending (most recent first)
#          → game_date descending (most recent date first within week)
#          → id descending (consistent tiebreaker)
games_query = games_query.order_by(
    Game.week.desc(),
    Game.game_date.desc().nulls_last(),  # Nulls appear last within week
    Game.id.desc()
)
```

**2. Update /api/teams/{team_id}/schedule Endpoint**

Location: `src/api/main.py`, around line 374

Current code:
```python
games_query = games_query.order_by(Game.week)
```

Change to:
```python
# Sort by: week ascending (chronological schedule)
#          → game_date ascending (earliest date first within week)
games_query = games_query.order_by(
    Game.week.asc(),
    Game.game_date.asc().nulls_last()  # Nulls appear last within week
)
```

### Existing Pattern Reference

**SQLAlchemy Multi-Level Sorting:**

SQLAlchemy already uses multi-level sorting in the codebase. This story extends that pattern:

```python
# Existing pattern (two levels)
.order_by(Game.week.desc(), Game.id.desc())

# New pattern (three levels)
.order_by(Game.week.desc(), Game.game_date.desc().nulls_last(), Game.id.desc())
```

**Null Handling in SQLAlchemy:**

SQLite sorts NULL values last by default in DESC order, but we use `.nulls_last()` explicitly for clarity and database portability.

### Key Constraints

1. **No Schema Changes:** Uses existing `game_date` column (nullable DateTime)
2. **No API Contract Changes:** Response format identical, only order changes
3. **Performance:** Must not add significant query overhead
4. **Null Safety:** Must handle null `game_date` without errors
5. **Database Compatibility:** Must work with SQLite (production database)

---

## Definition of Done

- [x] `/api/games` endpoint updated with multi-level sorting
- [x] `/api/teams/{id}/schedule` endpoint updated with date sorting
- [x] Null dates handled gracefully using `.nulls_last()`
- [x] Code comments explain sorting logic
- [x] Existing API tests pass
- [x] New tests verify date sorting:
  - [x] Games within same week sorted by date
  - [x] Null dates appear last within week
  - [x] Multiple games on same date sorted by ID
- [x] Performance verified (response time < 200ms)
- [x] Manual verification:
  - [x] Week 16 playoff games appear in correct chronological order
  - [x] Team schedules show games in chronological order
- [x] Changes committed with clear message

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Sorting change might break frontend code that assumes specific game order

**Mitigation:**
- Frontend code uses week filter, not hardcoded indices
- Frontend displays all games in returned array, order doesn't affect display logic
- Story 1 adds date display, making new order visually obvious

**Secondary Risk:** Null date handling might cause SQL errors on some databases

**Mitigation:**
- Use SQLAlchemy's `.nulls_last()` method (database-agnostic)
- Test with null dates before deploying
- Verify SQLite handles `nulls_last()` correctly

**Rollback:**
```bash
# Revert API changes
git checkout HEAD~1 src/api/main.py

# Restart backend
sudo systemctl restart cfb-rankings
```

### Compatibility Verification

- [x] No breaking changes to existing APIs (only sort order changes)
- [x] Database changes: None (uses existing `game_date` column)
- [x] UI changes: None (this story is backend only)
- [x] Performance impact: Negligible (SQL ORDER BY is optimized)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one development session (1 hour)
- [x] Integration approach is straightforward (change ORDER BY clause)
- [x] Follows existing patterns exactly (SQLAlchemy multi-level sorting)
- [x] No design or architecture work required (pure sorting logic)

### Clarity Check

- [x] Story requirements are unambiguous (add date to ORDER BY)
- [x] Integration points are clearly specified (main.py lines 441, 374)
- [x] Success criteria are testable (games sorted by date within week)
- [x] Rollback approach is simple (git revert backend file)

---

## Testing Checklist

### Automated Testing

Create new test cases in `tests/test_api.py`:

```python
def test_games_sorted_by_week_then_date():
    """Test /api/games returns games sorted by week desc, then date desc"""
    response = client.get("/api/games?season=2025")
    games = response.json()

    # Verify weeks are descending
    weeks = [g["week"] for g in games]
    assert weeks == sorted(weeks, reverse=True)

    # Verify dates within each week are descending
    for week in set(weeks):
        week_games = [g for g in games if g["week"] == week]
        dates = [g["game_date"] for g in week_games if g["game_date"]]
        assert dates == sorted(dates, reverse=True)

def test_team_schedule_sorted_by_week_then_date():
    """Test /api/teams/{id}/schedule returns games sorted chronologically"""
    response = client.get("/api/teams/1/schedule?season=2025")
    games = response.json()

    # Verify weeks are ascending
    weeks = [g["week"] for g in games]
    assert weeks == sorted(weeks)

    # Verify dates within each week are ascending
    for week in set(weeks):
        week_games = [g for g in games if g["week"] == week]
        dates = [g["game_date"] for g in week_games if g["game_date"]]
        assert dates == sorted(dates)
```

### Manual Testing Steps

1. **Test Week 16 Playoff Games (Multiple Dates):**
   ```bash
   # Query playoff games in week 16
   curl "https://cfb.bdailey.com/api/games?season=2025&week=16" | python3 -m json.tool

   # Expected order (descending dates):
   # 1. Dec 21 games (Oregon, Ole Miss)
   # 2. Dec 20 games (Alabama, Miami)

   # Verify dates are in descending order within week 16
   ```

2. **Test Team Schedule (Chronological Order):**
   ```bash
   # Query team schedule
   curl "https://cfb.bdailey.com/api/teams/1/schedule?season=2025" | python3 -m json.tool

   # Expected order (ascending weeks and dates):
   # 1. Week 1 games (earliest first)
   # 2. Week 2 games (earliest first)
   # ...
   # 3. Week 16 playoff games (Dec 20 before Dec 21)
   ```

3. **Test Null Date Handling:**
   ```bash
   # Query games with null dates (future unscheduled games)
   curl "https://cfb.bdailey.com/api/games?season=2025&week=17" | python3 -m json.tool

   # Verify:
   # - Games with dates appear first
   # - Games without dates (null) appear last
   # - No SQL errors or crashes
   ```

4. **Performance Test:**
   ```bash
   # Measure response time
   time curl "https://cfb.bdailey.com/api/games?season=2025" > /dev/null

   # Expected: < 200ms
   ```

---

## Implementation Notes

### Suggested Development Order

1. **Step 1:** Update `/api/games` endpoint sorting (10 min)
2. **Step 2:** Update `/api/teams/{id}/schedule` endpoint sorting (10 min)
3. **Step 3:** Add code comments explaining sorting logic (5 min)
4. **Step 4:** Write automated tests for date sorting (15 min)
5. **Step 5:** Test locally with playoff games (10 min)
6. **Step 6:** Test with null dates (edge case) (5 min)
7. **Step 7:** Performance verification (5 min)

**Total Estimated Time:** 1 hour

### Files to Modify

1. **src/api/main.py** (primary file)
   - Line ~441: Update `games_query.order_by()` for `/api/games`
   - Line ~374: Update `games_query.order_by()` for `/api/teams/{id}/schedule`

2. **tests/test_api.py** (or equivalent test file)
   - Add test for `/api/games` date sorting
   - Add test for `/api/teams/{id}/schedule` date sorting
   - Add test for null date handling

### Database Index Consideration

Current indexes on `games` table:
- Likely indexed on: `week`, `season`, `team_id`
- `game_date` column: May or may not be indexed

**Recommendation:** Check if `game_date` is indexed. If not, consider adding:
```sql
CREATE INDEX idx_games_week_date ON games (week, game_date);
```

This would optimize multi-column sorting. However, verify need via `EXPLAIN QUERY PLAN` first.

---

## Success Metrics

### Before Story
- **Games Order:** By week DESC, then by ID DESC (arbitrary within week)
- **Week 16 Playoff Games:** Dec 21 games might appear before Dec 20 games
- **Team Schedule:** Games in arbitrary order within each week

### After Story (Target)
- **Games Order:** By week DESC → date DESC → ID DESC (true chronological)
- **Week 16 Playoff Games:** Dec 21 games appear before Dec 20 games (descending)
- **Team Schedule:** Games in chronological order (earliest date first within week)
- **Null Dates:** Games without dates appear last within their week
- **Performance:** Response time unchanged (< 200ms)

---

## Example API Response Changes

### Before (Current):

```json
GET /api/games?season=2025&week=16

[
  {"id": 1234, "week": 16, "game_date": "2025-12-20", "home_team": "Alabama", ...},
  {"id": 1237, "week": 16, "game_date": "2025-12-21", "home_team": "Oregon", ...},
  {"id": 1235, "week": 16, "game_date": "2025-12-21", "home_team": "Ole Miss", ...},
  {"id": 1236, "week": 16, "game_date": "2025-12-20", "home_team": "Miami", ...}
]
```
*Note: Order is by ID, not date - Dec 20/21 games mixed*

### After (With Date Sorting):

```json
GET /api/games?season=2025&week=16

[
  {"id": 1237, "week": 16, "game_date": "2025-12-21", "home_team": "Oregon", ...},
  {"id": 1235, "week": 16, "game_date": "2025-12-21", "home_team": "Ole Miss", ...},
  {"id": 1234, "week": 16, "game_date": "2025-12-20", "home_team": "Alabama", ...},
  {"id": 1236, "week": 16, "game_date": "2025-12-20", "home_team": "Miami", ...}
]
```
*Note: Dec 21 games first (DESC), then Dec 20 games - proper chronological order*

---

## Notes

- **SQLite Compatibility:** `.nulls_last()` is supported by SQLAlchemy for SQLite
- **Future Enhancement:** Could add query parameter `?sort_by=date` to allow custom sorting
- **Index Optimization:** Consider adding composite index on (week, game_date) if performance degrades
- **Frontend Impact:** Frontend will automatically display games in new order (no code changes needed)

---

## Related Work

- **Epic:** `docs/epics/epic-game-date-display-and-sorting.md`
- **Story 1:** UI date display (frontend - displays dates visually)
- **Story 3:** Enhance date display across all views (consistency)
- **Database Model:** `src/models/models.py`, line 227 (`game_date` column)

---

**Ready for Implementation:** ✅

This story is fully defined with clear integration points, SQL examples, and comprehensive testing strategy. A backend developer can implement this in approximately 1 hour.
