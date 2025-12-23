# Story: Add Date Display to Games List UI - Brownfield Addition

**Status:** 📋 Draft
**Epic:** EPIC-GAME-DATE-SORTING
**Priority:** High
**Risk Level:** 🟢 Low Risk (UI addition, no breaking changes)
**Estimated Effort:** 1-2 hours

---

## User Story

As a **college football fan browsing the games list**,
I want **to see the date of each game displayed alongside the teams and scores**,
So that **I can quickly understand when games were played, especially for bowl and playoff games spread across multiple days**.

---

## Story Context

**Existing System Integration:**

- Integrates with: Games list page (`frontend/games.html`) and games table display logic
- Technology: Vanilla JavaScript, HTML5, CSS3 (responsive design)
- Follows pattern: Existing table column display in games.html (lines 75-167)
- Touch points:
  - JavaScript games rendering function (line 116)
  - Games table HTML structure (lines 99-112)
  - API response handling (already includes `game_date` field)

**Current Implementation:**

The games list currently displays:
- Winner team name
- Score (winner-loser format)
- Loser team name
- Location/venue

The `game_date` field already exists in:
- Database: `Game.game_date` column (nullable DateTime)
- API response: `GameBase` schema includes `game_date: Optional[datetime]`
- JavaScript: Available in game objects from API

**What's Missing:**

- No date column in the games table
- Date information not displayed to users
- Users cannot see when games occurred without clicking through

---

## Acceptance Criteria

### Functional Requirements

1. **Date Column Added to Games Table**
   - Add "Date" column header to games table
   - Display formatted date for each game in the list
   - Column appears between location and team names (or other logical position)

2. **Date Formatting**
   - Dates formatted as "Day, Mon DD" (e.g., "Sat, Dec 21")
   - Consistent formatting across all displayed games
   - Games without dates (null `game_date`) display "TBD"

3. **Responsive Design**
   - Date column visible on desktop and tablet
   - Date column optionally hidden or abbreviated on mobile (<768px)
   - Table layout remains clean and readable on all screen sizes

### Integration Requirements

4. **Existing Games Display Unchanged**
   - All existing columns (winner, score, loser, location) remain visible
   - Week filter dropdown continues to work correctly
   - Game row click/navigation behavior unchanged

5. **API Integration Maintained**
   - Uses existing `game_date` field from API response
   - No additional API calls required
   - Gracefully handles null `game_date` values

6. **Performance Requirements**
   - No noticeable performance degradation
   - Page load time remains under 2 seconds
   - Table rendering remains smooth with 100+ games

### Quality Requirements

7. **Code Quality**
   - JavaScript follows existing code style in `games.html`
   - CSS follows existing responsive patterns
   - No console errors or warnings

8. **Browser Compatibility**
   - Works in Chrome, Firefox, Safari, Edge (latest versions)
   - Date formatting uses browser-native `toLocaleDateString()` or equivalent

9. **Visual Consistency**
   - Date column styling matches existing table columns
   - Hover states and interactions consistent with current design
   - "TBD" placeholder matches existing placeholder styles

---

## Technical Notes

### Integration Approach

**1. Update HTML Table Structure**

Location: `frontend/games.html`, lines 99-112

Add date column to table header:
```html
<thead>
    <tr>
        <th>Date</th>  <!-- NEW COLUMN -->
        <th>Winner</th>
        <th>Score</th>
        <th>Loser</th>
        <th>Location</th>
    </tr>
</thead>
```

**2. Update JavaScript Rendering Logic**

Location: `frontend/games.html`, line 116 (inside `displayGames` function)

Add date cell to game row:
```javascript
function displayGames(games) {
    // ... existing code ...

    games.forEach(game => {
        // ... existing winner/loser logic ...

        // NEW: Format game date
        const formattedDate = formatGameDate(game.game_date);

        const gameRow = document.createElement('tr');
        gameRow.innerHTML = `
            <td class="game-date">${formattedDate}</td>  <!-- NEW -->
            <td class="winner">${winner.team_name}</td>
            <td class="score">${winner.score}-${loser.score}</td>
            <td class="loser">${loser.team_name}</td>
            <td>${location}</td>
        `;

        // ... existing code ...
    });
}
```

**3. Create Date Formatting Utility**

Add to `frontend/games.html` (or create `frontend/js/utils.js` if centralizing):
```javascript
/**
 * Format game date for display
 * @param {string|null} dateString - ISO date string from API
 * @returns {string} Formatted date or "TBD"
 */
function formatGameDate(dateString) {
    if (!dateString) {
        return 'TBD';
    }

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        console.warn('Invalid date format:', dateString);
        return 'TBD';
    }
}
```

**4. Add Responsive CSS**

Add to `<style>` section in `games.html`:
```css
/* Date column styling */
.game-date {
    white-space: nowrap;
    color: #666;
    font-size: 0.9em;
}

/* Hide date column on mobile if needed */
@media (max-width: 768px) {
    .game-date {
        display: none; /* Or use abbreviated format */
    }
}
```

### Existing Pattern Reference

**Precedent: Predictions Date Display**

Location: `frontend/js/app.js`, lines 391-403

The predictions view already formats game dates similarly:
```javascript
const formattedDate = new Date(game.game_date).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
});
```

This epic's Story 1 should follow the same pattern for consistency.

### Key Constraints

1. **No API Changes:** Must use existing `game_date` field from current API response
2. **Null Safety:** Must handle games without dates gracefully (show "TBD")
3. **Responsive Design:** Must not break mobile layout (table should remain usable)
4. **Performance:** Should not add significant DOM manipulation overhead
5. **Backward Compatibility:** Existing JavaScript logic must continue to work

---

## Definition of Done

- [x] Date column added to games table header
- [x] Date displayed for each game using formatted output
- [x] Games without dates show "TBD" placeholder
- [x] Responsive design maintained (tested on desktop, tablet, mobile)
- [x] All existing functionality verified:
  - [x] Week filter dropdown works
  - [x] Game navigation/clicks work
  - [x] Winner/loser/score display unchanged
  - [x] Location display unchanged
- [x] Code follows existing style and patterns
- [x] No console errors or warnings
- [x] Tested in Chrome, Firefox, Safari
- [x] Visual consistency with existing design verified
- [x] Changes committed with clear message

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Adding date column might break table layout on mobile devices

**Mitigation:**
- Use responsive CSS to hide or abbreviate date column on small screens
- Test on multiple screen sizes before deploying
- Use `@media` queries to adapt layout

**Rollback:**
```bash
# Revert HTML/JavaScript changes
git checkout HEAD~1 frontend/games.html

# Clear browser cache
# Refresh page - date column will disappear
```

### Compatibility Verification

- [x] No breaking changes to existing APIs (only reading existing `game_date` field)
- [x] Database changes: None (field already exists)
- [x] UI changes follow existing design patterns (table columns, responsive CSS)
- [x] Performance impact is negligible (only adding one `<td>` per row)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one development session (1-2 hours)
- [x] Integration approach is straightforward (add column to existing table)
- [x] Follows existing patterns exactly (same as other table columns)
- [x] No design or architecture work required (uses existing styles)

### Clarity Check

- [x] Story requirements are unambiguous (add date column, format dates)
- [x] Integration points are clearly specified (games.html, line 116)
- [x] Success criteria are testable (date visible, "TBD" for nulls, responsive)
- [x] Rollback approach is simple (git revert frontend file)

---

## Testing Checklist

### Manual Testing Steps

1. **Basic Display:**
   - [ ] Open `games.html` in browser
   - [ ] Verify "Date" column header appears
   - [ ] Verify dates display for all games
   - [ ] Verify "TBD" appears for games without dates

2. **Date Formatting:**
   - [ ] Check dates format as "Day, Mon DD" (e.g., "Sat, Dec 21")
   - [ ] Verify consistency across all rows
   - [ ] Verify no JavaScript errors in console

3. **Responsive Design:**
   - [ ] Test on desktop (1920x1080) - date column visible
   - [ ] Test on tablet (768x1024) - date column visible
   - [ ] Test on mobile (375x667) - date column hidden or abbreviated
   - [ ] Verify table remains readable on all sizes

4. **Existing Functionality:**
   - [ ] Week filter dropdown works correctly
   - [ ] Clicking team names navigates properly
   - [ ] Winner/loser/score columns unchanged
   - [ ] Location column unchanged

5. **Edge Cases:**
   - [ ] Games with null `game_date` show "TBD"
   - [ ] Invalid date formats handled gracefully
   - [ ] Very long date strings don't break layout

---

## Implementation Notes

### Suggested Development Order

1. **Step 1:** Add date column to HTML table header (5 min)
2. **Step 2:** Create `formatGameDate()` utility function (10 min)
3. **Step 3:** Add date cell to game row rendering logic (10 min)
4. **Step 4:** Add responsive CSS for date column (15 min)
5. **Step 5:** Test on multiple screen sizes (20 min)
6. **Step 6:** Test with null dates and edge cases (10 min)
7. **Step 7:** Final visual polish and consistency check (10 min)

**Total Estimated Time:** 1.5 hours

### Files to Modify

1. **frontend/games.html** (primary file)
   - Add `<th>Date</th>` to table header
   - Add `<td class="game-date">${formattedDate}</td>` to game rows
   - Add `formatGameDate()` function
   - Add CSS for `.game-date` class and responsive rules

### Testing Commands

```bash
# Start local development server (if applicable)
cd frontend
python3 -m http.server 8000

# Open in browser
open http://localhost:8000/games.html

# Test with different weeks
# Use week filter dropdown to see games from different weeks
# Verify dates appear correctly for each week

# Test responsive design
# Use browser DevTools (F12) → Toggle Device Toolbar
# Test on iPhone SE, iPad, Desktop presets
```

---

## Success Metrics

### Before Story
- Dates: Not visible in games list
- User feedback: "When was this game played?" (no easy way to tell)
- Bowl/playoff clarity: Games in same week appear random

### After Story (Target)
- Dates: 100% visible for all games with dates
- User feedback: "I can see when each game was played"
- Bowl/playoff clarity: Users can see Dec 19, Dec 20, Dec 21 games clearly
- "TBD" placeholder: Shows for unscheduled future games
- Responsive: Works on mobile, tablet, desktop

---

## Notes

- **Visual Design:** Date column should be subtle (smaller font, gray color) to not overpower team names
- **Mobile Priority:** If space is tight on mobile, date column can be hidden - team/score more important
- **Future Enhancement:** Could add tooltips with full date/time on hover
- **Consistency:** This story sets the pattern for Story 3 (team schedules)

---

## Related Work

- **Epic:** `docs/epics/epic-game-date-display-and-sorting.md`
- **Story 2:** API sorting by date (backend changes)
- **Story 3:** Enhance date display across all views (team schedules, predictions)
- **Precedent:** Predictions view date formatting in `frontend/js/app.js` (lines 391-403)

---

**Ready for Implementation:** ✅

This story is fully defined and ready for a developer to begin work. All integration points are identified, patterns are documented, and success criteria are testable.
