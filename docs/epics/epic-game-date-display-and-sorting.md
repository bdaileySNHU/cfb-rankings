# Epic: Game Date Display and Sorting - Brownfield Enhancement

**Epic ID**: EPIC-GAME-DATE-SORTING
**Type**: Brownfield - UI/UX Enhancement
**Status**: Draft
**Created**: 2025-12-23
**Target Completion**: 2-3 development sessions (3-5 hours)
**Priority**: Medium-High
**Complexity**: Low

---

## Epic Goal

Add game date display throughout the interface and implement secondary sorting by date after week to improve user experience, especially for bowl and playoff games which are spread across multiple days.

---

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Games are displayed in multiple locations: games list page, team schedules, and predictions
- Database already stores `game_date` field (DateTime, nullable) for all games
- API schemas include `game_date` field in responses
- Current sorting is by week only (descending for games list, ascending for schedules)
- Predictions already display formatted dates using `game_date` field

**Technology stack:**
- Backend: Python 3.11, FastAPI, SQLAlchemy ORM
- Frontend: Vanilla JavaScript, HTML/CSS
- Database: SQLite with `game_date` column already populated
- API: RESTful endpoints with Pydantic schemas

**Integration points:**
- API endpoints: `/api/games`, `/api/teams/{id}/schedule`, `/api/predictions`
- Frontend components: `games.html`, `team.js`, `app.js`
- Database model: `Game` model in `src/models/models.py`

### Enhancement Details

**What's being added/changed:**

1. **Date Display in Games List**
   - Add date column to games table on `games.html`
   - Format dates consistently (e.g., "Dec 21, 2024" or "Sat, Dec 21")
   - Display "TBD" for games without scheduled dates
   - Ensure dates are responsive and mobile-friendly

2. **Secondary Sorting by Date**
   - Backend: Update API `/api/games` endpoint to sort by week DESC, then date DESC
   - Backend: Update `/api/teams/{id}/schedule` to sort by week ASC, then date ASC
   - Frontend: Ensure games within same week display in date order
   - Especially important for bowl/playoff games (weeks 15-19) which span multiple days

3. **Consistent Date Formatting**
   - Use same date formatting across all game displays
   - Show relative dates for upcoming games ("Tomorrow", "In 3 days")
   - Show absolute dates for completed games
   - Handle null dates gracefully

**How it integrates:**
- Leverages existing `game_date` field (no database schema changes needed)
- Follows existing API response patterns (Pydantic schemas)
- Uses existing JavaScript utilities for date formatting
- Maintains backward compatibility (date field is already optional)

**Success criteria:**
- Dates visible in all game list views (games page, team schedules, predictions)
- Games within same week sorted chronologically by date
- Bowl/playoff games display in correct chronological order
- Date formatting consistent across all views
- No performance degradation in API responses
- Existing functionality remains intact

---

## Stories

### Story 1: Add Date Display to Games List UI

**Description:** Update the games list page (`games.html`) to display game dates alongside existing game information, with proper formatting and responsive design.

**Scope:**
- Add "Date" column to games table header
- Display formatted date for each game
- Handle null dates with "TBD" placeholder
- Ensure responsive layout (dates visible on mobile)
- Use consistent date formatting

**Acceptance Criteria:**
- Games list shows date column with formatted dates
- Dates format as "Day, Mon DD" (e.g., "Sat, Dec 21")
- Future games without dates show "TBD"
- Layout remains responsive on mobile devices
- No visual regressions in existing game display

---

### Story 2: Implement Secondary Sorting by Date in API

**Description:** Update backend API endpoints to include secondary sorting by game date after week, ensuring chronological order within each week.

**Scope:**
- Modify `/api/games` endpoint to sort by week DESC, then game_date DESC
- Modify `/api/teams/{id}/schedule` endpoint to sort by week ASC, then game_date ASC
- Ensure null dates are handled gracefully in sorting (appear last)
- Add query parameter for sort customization (optional)
- Update API documentation/schemas if needed

**Acceptance Criteria:**
- Games endpoint returns games sorted by week descending, then date descending
- Team schedule endpoint returns games sorted by week ascending, then date ascending
- Games without dates appear after games with dates within same week
- No performance degradation in API response times
- Existing API contracts remain unchanged (backward compatible)

---

### Story 3: Enhance Date Display Across All Views

**Description:** Ensure consistent date display and formatting across all game-related views (team schedules, predictions) and add relative date formatting for upcoming games.

**Scope:**
- Update team schedule view (`team.js`) to display dates
- Verify predictions view already shows dates correctly
- Add relative date formatting ("Today", "Tomorrow", "In 3 days") for upcoming games
- Ensure consistent date formatting across all views
- Add tooltip/hover for full date details

**Acceptance Criteria:**
- Team schedules show formatted dates for all games
- Predictions view maintains existing date display
- Upcoming games within 7 days show relative dates
- All date formats are consistent across the application
- Tooltips show full date/time on hover
- No visual regressions in any view

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (only sorting order changes, response format same)
- [x] Database schema changes not required (game_date field already exists)
- [x] UI changes follow existing patterns (table columns, date formatting)
- [x] Performance impact is minimal (simple SQL ORDER BY addition)
- [x] Backward compatible (date field is optional, nulls handled gracefully)

---

## Risk Mitigation

**Primary Risks:**

1. **Date Formatting Inconsistency:** Different views might show dates differently
   - **Mitigation:** Create shared JavaScript utility function for date formatting
   - **Rollback:** Revert to hiding dates if formatting issues arise

2. **Null Date Handling:** Games without dates might break sorting or display
   - **Mitigation:** Test with null dates, ensure "TBD" placeholder and proper SQL sorting
   - **Rollback:** Exclude games without dates from sort logic

3. **Mobile Layout Issues:** Adding date column might break responsive design
   - **Mitigation:** Test on multiple screen sizes, use responsive CSS techniques
   - **Rollback:** Make date column optional/collapsible on mobile

**Rollback Plan:**
```bash
# Revert backend changes
git revert <commit-hash>
sudo systemctl restart cfb-rankings

# Revert frontend changes
git checkout HEAD~1 frontend/games.html frontend/js/team.js
# Clear browser cache and reload
```

---

## Definition of Done

- [x] Dates displayed in games list with consistent formatting
- [x] Games sorted by week first, then by date within each week
- [x] All views (games list, team schedules, predictions) show dates
- [x] Null dates handled gracefully with "TBD" placeholder
- [x] Responsive design maintained on mobile devices
- [x] No performance degradation in API responses
- [x] No regression in existing functionality
- [x] Code committed with clear messages
- [x] Manual verification: browse games and verify date display and sorting

---

## Validation Checklist

### Scope Validation

- [x] Epic can be completed in 3 stories maximum
- [x] No architectural documentation required (uses existing patterns)
- [x] Enhancement follows existing patterns (UI tables, API sorting)
- [x] Integration complexity is manageable (frontend + API updates)

### Risk Assessment

- [x] Risk to existing system is low (additive changes, no breaking changes)
- [x] Rollback plan is feasible (git revert)
- [x] Testing approach covers existing functionality (manual verification)
- [x] Team has sufficient knowledge of integration points (JavaScript, FastAPI)

### Completeness Check

- [x] Epic goal is clear and achievable (add dates, sort by date)
- [x] Stories are properly scoped (UI, API, consistency)
- [x] Success criteria are measurable (dates visible, sorting works)
- [x] Dependencies are identified (existing game_date field)

---

## Technical Notes

### Current Implementation Analysis

**Database:**
- `game_date` field exists in `Game` model (Line 227, `src/models/models.py`)
- Field type: `DateTime`, nullable (allows null for unscheduled games)
- Already populated for most games from CFBD API imports

**API Schemas:**
- `GameBase` schema includes `game_date: Optional[datetime]` (Line 134, `src/models/schemas.py`)
- `GamePrediction` schema includes `game_date: Optional[str]` (Line 451)
- API already returns game_date in responses

**Current Sorting Logic:**
- `/api/games`: `order_by(Game.week.desc(), Game.id.desc())` (Line 441, `src/api/main.py`)
- `/api/teams/{id}/schedule`: `order_by(Game.week)` (Line 374, `src/api/main.py`)
- Frontend games.html: `games.sort((a, b) => b.week - a.week || b.id - a.id)` (Line 116)

**Date Display Precedent:**
- Predictions already display dates using formatting (Lines 391-403, `frontend/js/app.js`)
- Format: `new Date(game.game_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })`

### Files to Modify

**Backend (API):**
1. `src/api/main.py` - Update sorting logic in `/api/games` and `/api/teams/{id}/schedule` endpoints

**Frontend (UI):**
1. `frontend/games.html` - Add date column to games table
2. `frontend/js/team.js` - Add date display to team schedules
3. `frontend/js/app.js` - Verify predictions date display (likely already good)

**Potential Shared Utility:**
1. `frontend/js/utils.js` (create if doesn't exist) - Shared date formatting function

---

## Example Implementation Snippets

### Backend API Sorting

```python
# In src/api/main.py, update /api/games endpoint (around line 441)
# Change from:
games_query = games_query.order_by(Game.week.desc(), Game.id.desc())

# Change to:
games_query = games_query.order_by(
    Game.week.desc(),
    Game.game_date.desc().nulls_last(),  # Secondary sort by date
    Game.id.desc()  # Tertiary sort by ID
)
```

### Frontend Date Display

```javascript
// In frontend/games.html, add date column (around line 116)
function displayGames(games) {
    // ... existing code ...

    const formattedDate = game.game_date
        ? formatGameDate(game.game_date)  // Utility function
        : 'TBD';

    gameRow.innerHTML = `
        <td>${formattedDate}</td>  <!-- NEW: Date column -->
        <td class="winner">${winner.team_name}</td>
        <td class="score">${winner.score}-${loser.score}</td>
        <td class="loser">${loser.team_name}</td>
        <td>${location}</td>
    `;

    // ... existing code ...
}

// Utility function for consistent date formatting
function formatGameDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });
}
```

---

## Dependencies

**No blocking dependencies:**
- All work uses existing `game_date` field (already in database)
- No external API changes required
- No new libraries or frameworks needed
- No database migration required

**Builds on:**
- Existing game data model with `game_date` field
- Existing API response schemas
- Existing frontend JavaScript and HTML structure

**Enables:**
- Better user experience for viewing games chronologically
- Improved clarity for bowl/playoff game schedules
- Foundation for future date-based features (filters, calendars)

---

## Success Metrics

### Before Epic
- **Date Visibility:** Dates not displayed in games list or team schedules
- **Sorting:** Games sorted by week only, order within week is arbitrary (by ID)
- **Bowl/Playoff UX:** Games in weeks 15-19 appear in random order despite spanning multiple days

### After Epic (Target)
- **Date Visibility:** 100% of game views show formatted dates
- **Sorting:** Games sorted chronologically (week first, then date)
- **Bowl/Playoff UX:** Playoff games display in actual chronological order (Dec 19, Dec 20, Dec 21, etc.)
- **Consistency:** All views use same date formatting
- **Performance:** No measurable performance degradation (<5% response time increase)

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing CFB ranking system running Python 3.11 (FastAPI) and vanilla JavaScript frontend
- Integration points:
  - Backend API endpoints (`/api/games`, `/api/teams/{id}/schedule` in `src/api/main.py`)
  - Frontend game displays (`games.html`, `team.js`, `app.js`)
  - Database `game_date` field (already exists, no migration needed)
- Existing patterns to follow:
  - SQLAlchemy `order_by()` for API sorting
  - Pydantic schemas for API responses (already include `game_date`)
  - JavaScript date formatting (see predictions view for precedent)
  - Responsive table design in `games.html`
- Critical compatibility requirements:
  - API response format must remain unchanged (only sort order changes)
  - Handle null `game_date` values gracefully (show "TBD")
  - Maintain responsive design on mobile
  - No breaking changes to existing JavaScript
- Each story must verify that existing functionality (game display, filtering, navigation) remains intact

The epic should improve UX by making game dates visible and ensuring chronological order, especially critical for bowl/playoff games."

---

## Notes

- **User Impact:** High - users expect to see game dates, especially for postseason
- **Technical Complexity:** Low - field already exists, just need to display and sort
- **Design Consideration:** Date formatting should be consistent but can have contextual variations (relative vs absolute)
- **Future Enhancements:** Could add date-based filtering, calendar view, timezone support
- **Bowl/Playoff Priority:** This epic particularly improves UX for weeks 15-19 where games span multiple days

---

## Acceptance Testing

**Manual Verification Steps:**

After all stories complete:

1. **Verify Date Display in Games List:**
   ```bash
   # Visit games page in browser
   open https://cfb.bdailey.com/games.html

   # Check:
   # - Date column is visible
   # - Dates are formatted consistently (e.g., "Sat, Dec 21")
   # - Games without dates show "TBD"
   # - Layout is responsive on mobile (resize browser)
   ```

2. **Verify Chronological Sorting:**
   ```bash
   # Check API response
   curl https://cfb.bdailey.com/api/games?season=2025&week=16 | python3 -m json.tool

   # Verify:
   # - Games are sorted by date within the week
   # - Dec 19 games appear before Dec 20 games
   # - Dec 21 games appear last
   ```

3. **Verify Team Schedule Dates:**
   ```bash
   # Visit team schedule page
   open https://cfb.bdailey.com/team.html?id=1

   # Check:
   # - Dates are displayed for all games
   # - Games are in chronological order (earliest first)
   # - Formatting matches games list
   ```

4. **Verify No Regression:**
   ```bash
   # Test existing functionality
   # - Filter games by week (dropdown still works)
   # - Click team names (navigation still works)
   # - View predictions (predictions page unaffected)
   # - Mobile view (responsive design intact)
   ```

---

## Conclusion

This epic enhances user experience by making game dates visible and ensuring chronological sorting, with minimal risk and complexity. The `game_date` field already exists in the database and API, so this is primarily a frontend enhancement with minor backend sorting updates. The focused scope (3 stories, no architectural changes) allows for quick implementation while delivering significant UX value, especially for bowl and playoff games which are spread across multiple days.

**Timeline:**
- Story 1: 1-2 hours (add date column to games list)
- Story 2: 1 hour (update API sorting logic)
- Story 3: 1-2 hours (enhance date display across views)
- **Total: 3-5 hours (2-3 development sessions)**

**Impact:**
- Improved user experience for viewing games
- Better clarity for bowl/playoff schedules
- Chronological order within each week
- Foundation for future date-based features
