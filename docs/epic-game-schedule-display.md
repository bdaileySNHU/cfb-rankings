# Epic: Game Schedule Display - Brownfield Enhancement

**Epic ID**: EPIC-001
**Created**: 2025-10-17
**Status**: Ready for Development
**Type**: Brownfield Enhancement

---

## Epic Goal

Enable users to view complete game schedules (past and future games) on both the Games page and Team detail pages, providing comprehensive visibility into team schedules throughout the season.

---

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Backend API endpoints exist (`GET /api/games` and `GET /api/teams/{id}/schedule`) that return game data
- Frontend has `games.html` and `team.html` pages with schedule tables
- Database stores all games (both completed and scheduled) with scores, weeks, teams, etc.
- **Issue**: Frontend JavaScript does not properly display games without scores (future/scheduled games)

**Technology stack:**
- Backend: FastAPI (Python 3.11+), SQLAlchemy ORM, SQLite database
- Frontend: Vanilla JavaScript (ES6+), HTML5, CSS3
- API: RESTful JSON endpoints

**Integration points:**
- Frontend pages: `frontend/games.html`, `frontend/team.html`
- Frontend scripts: `frontend/js/team.js`, inline JavaScript in `games.html`
- Backend API endpoints: `GET /api/games`, `GET /api/teams/{id}/schedule`
- Database: Games table (existing schema, no changes needed)

### Enhancement Details

**What's being added/changed:**

1. **Games Page Enhancement** (`games.html`)
   - Display all games from the current season (both completed with scores and scheduled without scores)
   - Handle games without scores gracefully (show "TBD" or "Scheduled")
   - Maintain existing week filtering functionality for all games

2. **Team Detail Page Enhancement** (`team.html` / `team.js`)
   - Show complete season schedule including future games
   - Visual distinction between completed games (with W/L results) and upcoming games (TBD)
   - Preserve existing functionality for completed games

3. **Visual Improvements**
   - CSS styling to differentiate past vs future games
   - Clear visual indicators (scores for past, "vs [Opponent]" for future)
   - Date display where available
   - Improved empty states and loading states

**How it integrates:**
- Uses existing API endpoints without any backend modifications
- Enhances frontend JavaScript to handle null/undefined scores
- Leverages existing CSS classes and design patterns
- No database schema changes required

**Success criteria:**
- ✅ Games page displays all season games (past with scores, future with TBD)
- ✅ Team detail page shows complete season schedule
- ✅ Visual distinction is clear between completed and scheduled games
- ✅ Week filtering works correctly for all games
- ✅ No JavaScript errors in browser console
- ✅ Existing functionality remains intact (rankings, other pages)

---

## Stories

### Story 1: Fix Games Page to Display All Season Games

**Description:**
Update the Games page (`games.html`) to fetch and display all games from the current season, including both completed games with scores and future scheduled games without scores.

**Tasks:**
- Modify the `displayGames()` function to handle games with null/undefined scores
- Add logic to display "TBD" or "Scheduled" for games without scores
- Update winner/loser determination to check if scores exist before calculating
- Add visual styling for scheduled games (e.g., grayed out or different text color)
- Ensure week filter works for both completed and scheduled games
- Test with games that have scores and games without scores

**Acceptance Criteria:**
- All games from the season are displayed (past and future)
- Future games show "TBD" or "Scheduled" instead of scores
- No JavaScript errors when displaying games without scores
- Week filtering includes both completed and scheduled games
- Visual distinction between completed and scheduled games is clear

**Files to modify:**
- `frontend/games.html` (inline JavaScript)
- Potentially `frontend/css/style.css` (new CSS classes for scheduled games)

---

### Story 2: Enhance Team Detail Page Schedule Display

**Description:**
Update the Team detail page schedule section to display the full season schedule, including both past games with results and future scheduled games.

**Tasks:**
- Modify `createScheduleRow()` function in `team.js` to handle future games
- Update the Result column logic to check if game has been played before showing W/L
- Add "vs [Opponent]" display for future games instead of score
- Ensure opponent links work for both past and future games
- Handle neutral site and home/away display for scheduled games
- Test schedule display with mix of completed and scheduled games

**Acceptance Criteria:**
- Team schedule shows all games (completed and scheduled)
- Past games display W/L with scores
- Future games show "vs [Opponent]" or "TBD"
- Opponent names are clickable links for all games
- Location (Home/Away/Neutral) is displayed correctly for all games
- No errors when schedule contains games without scores

**Files to modify:**
- `frontend/js/team.js` (specifically `createScheduleRow()` and related functions)
- Potentially `frontend/team.html` (if table structure needs adjustment)

---

### Story 3: Add Visual Enhancements for Schedule Clarity

**Description:**
Improve the visual presentation of game schedules across both the Games page and Team detail page to clearly distinguish between completed and scheduled games.

**Tasks:**
- Create CSS classes for scheduled games (e.g., `.game-scheduled`, `.game-future`)
- Add styling to differentiate scheduled games (lighter text, different background, icons)
- Add date display if available from game data (check API response)
- Update table styling for better readability
- Improve loading states for schedule sections
- Add helpful empty state messages (e.g., "No upcoming games scheduled")
- Ensure responsive design works on mobile devices

**Acceptance Criteria:**
- Scheduled games have distinct visual styling (color, font weight, or icons)
- Completed games have clear win/loss indicators (existing green/red styling)
- Date information is displayed where available
- Loading states show appropriate spinners/messages
- Empty states provide helpful context to users
- Responsive design works on mobile and tablet screens
- Visual design is consistent with existing site styling

**Files to modify:**
- `frontend/css/style.css`
- `frontend/games.html` (update display logic to apply new CSS classes)
- `frontend/js/team.js` (apply new CSS classes in `createScheduleRow()`)

---

## Compatibility Requirements

- ✅ **Existing APIs remain unchanged** - No modifications to backend endpoints
- ✅ **Database schema changes are not required** - Uses existing Games table structure
- ✅ **UI changes follow existing patterns** - Reuses existing CSS classes, table structures, and design language
- ✅ **Performance impact is minimal** - Same API calls as before, slightly enhanced rendering logic

---

## Risk Mitigation

**Primary Risk:**
Games without scores (future games) may cause JavaScript errors or display issues if the frontend assumes scores are always present.

**Mitigation Strategy:**
- Add defensive null/undefined checks for score fields before accessing them
- Use optional chaining (`?.`) and nullish coalescing (`??`) operators in JavaScript
- Test thoroughly with games that have no scores
- Add error boundaries to prevent entire page failure if one game fails to render

**Secondary Risk:**
Users may be confused if visual distinction between past and future games is not clear enough.

**Mitigation Strategy:**
- Use multiple visual cues (text, color, icons) to distinguish game states
- Add clear labels ("Completed", "Scheduled", "TBD")
- Conduct quick user testing or feedback review after implementation

**Rollback Plan:**
- Frontend changes are isolated to HTML, JavaScript, and CSS files
- Can quickly revert by restoring previous versions of:
  - `frontend/games.html`
  - `frontend/team.html`
  - `frontend/js/team.js`
  - `frontend/css/style.css`
- No database migrations or backend changes to roll back
- Git commit history allows for easy revert

---

## Definition of Done

- ✅ All 3 stories completed with acceptance criteria met
- ✅ Games page displays both past and future games correctly
- ✅ Team detail page shows complete season schedule
- ✅ Visual distinction between completed and scheduled games is clear and intuitive
- ✅ Week filtering works correctly for all game types
- ✅ No JavaScript errors in browser console (checked in Chrome, Firefox, Safari)
- ✅ Existing functionality verified through manual testing:
  - Rankings page still loads correctly
  - Team detail stats still display correctly
  - Navigation between pages works
  - Other API calls remain functional
- ✅ No regression in existing features
- ✅ Code follows existing project patterns and conventions
- ✅ Responsive design tested on desktop, tablet, and mobile viewports

---

## Technical Notes

### API Response Structure (Reference)

**`GET /api/games` response:**
```json
[
  {
    "id": 1,
    "home_team_id": 5,
    "away_team_id": 12,
    "home_score": 35,
    "away_score": 28,
    "week": 3,
    "season": 2024,
    "is_neutral_site": false,
    "game_date": "2024-09-14T19:00:00Z",
    "is_processed": true,
    "home_rating_change": 12.5,
    "away_rating_change": -12.5
  },
  {
    "id": 2,
    "home_team_id": 8,
    "away_team_id": 15,
    "home_score": null,
    "away_score": null,
    "week": 14,
    "season": 2024,
    "is_neutral_site": false,
    "game_date": "2024-11-23T15:30:00Z",
    "is_processed": false,
    "home_rating_change": 0.0,
    "away_rating_change": 0.0
  }
]
```

**Key observations:**
- Future games have `home_score` and `away_score` as `null`
- Future games have `is_processed: false`
- `game_date` is available for all games
- Team IDs are always present, can be used to fetch team names

### Implementation Approach

**Recommended JavaScript pattern for handling scores:**
```javascript
function displayGame(game) {
  const hasScore = game.home_score !== null && game.away_score !== null;

  if (hasScore) {
    // Display score and winner/loser
    const winner = game.home_score > game.away_score ? 'Home' : 'Away';
    // ... existing logic
  } else {
    // Display as scheduled game
    return 'TBD';
  }
}
```

**CSS classes to add:**
```css
.game-scheduled {
  color: var(--text-secondary);
  font-style: italic;
}

.game-future {
  opacity: 0.7;
}
```

---

## Handoff to Story Manager

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing **College Football Rankings System** running **FastAPI (Python) backend + Vanilla JavaScript frontend**
- Integration points:
  - `GET /api/games` (returns all games including future games with null scores)
  - `GET /api/teams/{id}/schedule` (returns team schedule)
  - Frontend pages: `games.html`, `team.html`
  - Frontend scripts: `team.js`, inline JS in `games.html`
- Existing patterns to follow:
  - Use existing CSS classes (`.schedule-table`, `.loading`, `.hidden`, etc.)
  - Follow existing API call pattern using `api.getGames()` and `api.getTeamSchedule()`
  - Maintain existing table structures in HTML
- Critical compatibility requirements:
  - No backend API changes
  - No database schema changes
  - Must handle games with `null` scores gracefully
  - Must not break existing functionality (rankings, team stats, navigation)
- Each story must include:
  - Defensive null checks for game scores
  - Testing with both completed and scheduled games
  - Verification that existing functionality remains intact

The epic should maintain system integrity while delivering **comprehensive game schedule visibility for users**."

---

## Epic Status

**Current Status**: ✅ **Ready for Development**

**Next Steps:**
1. Review epic with development team
2. Assign stories to developers
3. Begin with Story 1 (Games page) as foundation
4. Proceed to Story 2 (Team detail page) after Story 1 is complete
5. Complete Story 3 (visual enhancements) last to polish the feature
6. Conduct manual testing across all affected pages
7. Deploy to production once all Definition of Done criteria are met

---

**Epic Owner**: Product Manager (John)
**Target Completion**: 1-2 sprints (estimated 3-5 days of development)
**Priority**: Medium (user-facing enhancement, not critical bug)
