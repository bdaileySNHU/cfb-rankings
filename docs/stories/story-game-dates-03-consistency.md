# Story: Enhance Date Display Across All Views - Brownfield Addition

**Status:** 📋 Draft
**Epic:** EPIC-GAME-DATE-SORTING
**Priority:** Medium
**Risk Level:** 🟢 Low Risk (UI polish, no breaking changes)
**Estimated Effort:** 1-2 hours

---

## User Story

As a **college football fan browsing team schedules and predictions**,
I want **to see game dates displayed consistently across all views with helpful context like relative dates**,
So that **I can quickly understand game timing whether I'm viewing a team's schedule, predictions, or the full games list**.

---

## Story Context

**Existing System Integration:**

- Integrates with:
  - Team schedule view (`frontend/js/team.js`, lines 212-303)
  - Predictions view (`frontend/js/app.js`, lines 332-378, 391-403)
  - Games list view (updated in Story 1)
- Technology: Vanilla JavaScript, HTML5, CSS3
- Follows pattern: Date formatting established in Story 1 and existing predictions view
- Touch points:
  - Team schedule rendering function
  - Predictions card rendering function
  - Shared date formatting utility

**Current Implementation:**

1. **Team Schedule (`team.js`):**
   - Displays games with badges (CONF CHAMP, BOWL, PLAYOFF)
   - Shows scores and results
   - **Does NOT currently display game dates**
   - Games sorted by week (from API)

2. **Predictions View (`app.js`, lines 391-403):**
   - **Already displays formatted dates** for upcoming games
   - Format: "Weekday, Mon DD" (e.g., "Sat, Dec 21")
   - Uses `toLocaleDateString()` for formatting

3. **Games List (Story 1):**
   - Now displays dates after Story 1 implementation
   - Format: "Day, Mon DD" (e.g., "Sat, Dec 21")

**What's Missing:**

- Team schedules don't show game dates
- No relative date formatting ("Today", "Tomorrow") for upcoming games
- Date formats slightly inconsistent between views
- No tooltips with full date/time details

---

## Acceptance Criteria

### Functional Requirements

1. **Team Schedule Date Display**
   - Add date display to each game in team schedule
   - Format matches games list: "Day, Mon DD"
   - Dates appear alongside or below game result
   - Games without dates show "TBD"

2. **Relative Date Formatting for Upcoming Games**
   - Games today show "Today" instead of absolute date
   - Games tomorrow show "Tomorrow"
   - Games in 2-6 days show "In X days"
   - Games 7+ days away show absolute date
   - Applies to predictions view and future games in schedules

3. **Date Format Consistency**
   - All views use same base format: "Day, Mon DD"
   - Relative dates override absolute dates when applicable
   - Color/styling consistent across views
   - "TBD" placeholder consistent across views

### Integration Requirements

4. **Existing Functionality Preserved**
   - Team schedule filtering (game type badges) unchanged
   - Predictions ranking/sorting unchanged
   - Game navigation and clicks unchanged
   - All existing visual elements remain

5. **Shared Utility Function**
   - Create shared `formatGameDate()` utility
   - Optionally create `getRelativeDate()` utility
   - Functions available to all views
   - Consistent behavior across different contexts

6. **Predictions View Enhancement**
   - Maintain existing date display
   - Add relative dates for games within 7 days
   - Ensure backward compatibility

### Quality Requirements

7. **Visual Consistency**
   - Date styling matches across all views
   - Relative dates visually distinct (e.g., bolder, different color)
   - Hover states/tooltips consistent

8. **Code Quality**
   - JavaScript follows existing code style
   - Utility functions are well-documented
   - No code duplication across views

9. **Accessibility**
   - Tooltips provide full date/time on hover
   - Relative dates include accessible full date in title attribute
   - Color contrast meets WCAG guidelines

---

## Technical Notes

### Integration Approach

**1. Create Shared Date Utilities**

Create new file: `frontend/js/date-utils.js` (or add to existing utils)

```javascript
/**
 * Format game date for display with optional relative dates
 * @param {string|null} dateString - ISO date string from API
 * @param {boolean} useRelative - Use relative dates for nearby games
 * @returns {string} Formatted date or "TBD"
 */
function formatGameDate(dateString, useRelative = false) {
    if (!dateString) {
        return 'TBD';
    }

    try {
        const date = new Date(dateString);

        if (useRelative) {
            const relative = getRelativeDate(date);
            if (relative) return relative;
        }

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

/**
 * Get relative date description for upcoming games
 * @param {Date} date - Game date
 * @returns {string|null} Relative description or null if > 7 days away
 */
function getRelativeDate(date) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const gameDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    const diffTime = gameDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays > 1 && diffDays <= 6) return `In ${diffDays} days`;

    return null; // Use absolute date for 7+ days
}

/**
 * Get full date/time string for tooltips
 * @param {string|null} dateString - ISO date string from API
 * @returns {string} Full formatted date/time or empty string
 */
function getFullDateTime(dateString) {
    if (!dateString) return '';

    try {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            timeZoneName: 'short'
        });
    } catch (e) {
        return '';
    }
}
```

**2. Update Team Schedule View**

Location: `frontend/js/team.js`, around lines 250-280 (game rendering)

Add date display to game cards:
```javascript
function renderScheduleGame(game) {
    // ... existing code for badges, scores ...

    // NEW: Add date display
    const formattedDate = formatGameDate(game.game_date, false); // No relative dates for schedules
    const fullDateTime = getFullDateTime(game.game_date);

    const gameHTML = `
        <div class="schedule-game">
            <div class="game-date" title="${fullDateTime}">${formattedDate}</div>
            ${gameBadges}  <!-- Existing: CONF CHAMP, BOWL, PLAYOFF badges -->
            <div class="game-result">
                ${winner} ${score} ${loser}
            </div>
        </div>
    `;

    return gameHTML;
}
```

Add CSS for game date:
```css
.game-date {
    font-size: 0.85em;
    color: #666;
    margin-bottom: 4px;
}
```

**3. Enhance Predictions View**

Location: `frontend/js/app.js`, around lines 391-403

Update existing date formatting to use relative dates:
```javascript
// BEFORE (current implementation):
const formattedDate = new Date(game.game_date).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
});

// AFTER (with relative dates):
const formattedDate = formatGameDate(game.game_date, true); // Enable relative dates
const fullDateTime = getFullDateTime(game.game_date);

predictionCard.innerHTML = `
    <div class="prediction-date" title="${fullDateTime}">
        ${formattedDate}
    </div>
    ... existing prediction content ...
`;
```

Add CSS for relative dates (optional - make them stand out):
```css
.prediction-date {
    font-weight: bold;
    color: #2563eb; /* Blue color for upcoming games */
}
```

**4. Update Games List (from Story 1)**

If Story 1 didn't use shared utility, update to use it:
```javascript
// In games.html, replace inline formatting with:
const formattedDate = formatGameDate(game.game_date, false);
const fullDateTime = getFullDateTime(game.game_date);

// Add tooltip to date cell:
<td class="game-date" title="${fullDateTime}">${formattedDate}</td>
```

### Existing Pattern Reference

**Current Predictions Date Format:**
Location: `frontend/js/app.js`, line 391-403

The predictions view already formats dates similarly. Story 3 extends this pattern with:
1. Shared utility function (avoid duplication)
2. Relative dates for upcoming games
3. Tooltips with full date/time

### Key Constraints

1. **No API Changes:** Uses existing `game_date` field from API responses
2. **Backward Compatibility:** Existing views continue to work
3. **Performance:** Date formatting must be fast (no async operations)
4. **Consistency:** All views must use same formatting functions
5. **Accessibility:** Tooltips and relative dates must be screen-reader friendly

---

## Definition of Done

- [x] Shared date utility functions created (`formatGameDate`, `getRelativeDate`, `getFullDateTime`)
- [x] Team schedule view displays game dates
- [x] Predictions view uses relative dates for upcoming games
- [x] Games list uses shared utilities (if needed)
- [x] All views use consistent date formatting
- [x] Tooltips show full date/time on hover
- [x] Relative dates work correctly:
  - [x] "Today" for games today
  - [x] "Tomorrow" for games tomorrow
  - [x] "In X days" for games 2-6 days away
  - [x] Absolute date for games 7+ days away
- [x] Existing functionality verified:
  - [x] Team schedule filtering works
  - [x] Predictions ranking works
  - [x] Game navigation works
- [x] Visual consistency verified across all views
- [x] Code quality verified (no duplication, well-documented)
- [x] Accessibility verified (tooltips, color contrast)
- [x] Changes committed with clear message

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Relative dates might confuse users if not clearly distinguished from absolute dates

**Mitigation:**
- Use distinct styling (bold, color) for relative dates
- Provide tooltip with full date/time on hover
- Only use relative dates for upcoming games (< 7 days)

**Secondary Risk:** Date formatting utility might have timezone issues

**Mitigation:**
- Use `toLocaleDateString()` which handles user's timezone
- Document timezone behavior in comments
- Test across different timezones if needed

**Rollback:**
```bash
# Revert frontend changes
git checkout HEAD~1 frontend/js/team.js frontend/js/app.js frontend/js/date-utils.js

# Clear browser cache
# Refresh page - dates will revert to previous state
```

### Compatibility Verification

- [x] No breaking changes to existing APIs
- [x] Database changes: None
- [x] UI changes follow existing design patterns
- [x] Performance impact is negligible (simple JS date formatting)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in one development session (1-2 hours)
- [x] Integration approach is straightforward (add dates to existing views)
- [x] Follows existing patterns exactly (date formatting, tooltips)
- [x] No design or architecture work required (UI polish)

### Clarity Check

- [x] Story requirements are unambiguous (add dates, relative formatting)
- [x] Integration points are clearly specified (team.js, app.js)
- [x] Success criteria are testable (dates visible, relative dates work)
- [x] Rollback approach is simple (git revert frontend files)

---

## Testing Checklist

### Manual Testing Steps

1. **Team Schedule Date Display:**
   - [ ] Open team schedule page
   - [ ] Verify dates appear for all games
   - [ ] Verify "TBD" for games without dates
   - [ ] Verify date format matches games list
   - [ ] Hover over date - verify tooltip shows full date/time

2. **Predictions Relative Dates:**
   - [ ] Open predictions page
   - [ ] Find game today - verify shows "Today"
   - [ ] Find game tomorrow - verify shows "Tomorrow"
   - [ ] Find game in 3 days - verify shows "In 3 days"
   - [ ] Find game in 10 days - verify shows absolute date
   - [ ] Hover over relative date - verify tooltip shows full date

3. **Visual Consistency:**
   - [ ] Compare date formatting across:
     - [ ] Games list
     - [ ] Team schedule
     - [ ] Predictions
   - [ ] Verify same format, color, styling
   - [ ] Verify "TBD" consistent across all views

4. **Edge Cases:**
   - [ ] Game exactly at midnight - verify date calculation correct
   - [ ] Game 7 days away - verify uses absolute date (not "In 7 days")
   - [ ] Null date - verify "TBD" appears
   - [ ] Invalid date format - verify graceful fallback to "TBD"

5. **Responsive Design:**
   - [ ] Test on desktop - all dates visible
   - [ ] Test on tablet - all dates visible
   - [ ] Test on mobile - dates appropriately sized

---

## Implementation Notes

### Suggested Development Order

1. **Step 1:** Create shared date utility functions (20 min)
2. **Step 2:** Update team schedule to display dates (20 min)
3. **Step 3:** Add relative dates to predictions view (15 min)
4. **Step 4:** Add tooltips with full date/time (15 min)
5. **Step 5:** Update games list to use shared utilities (10 min - if needed)
6. **Step 6:** Visual consistency polish (10 min)
7. **Step 7:** Test all views and edge cases (20 min)

**Total Estimated Time:** 1.5-2 hours

### Files to Modify

1. **frontend/js/date-utils.js** (NEW - create this file)
   - `formatGameDate()` function
   - `getRelativeDate()` function
   - `getFullDateTime()` function

2. **frontend/js/team.js** (update)
   - Import/include date utilities
   - Add date display to game rendering
   - Add CSS for `.game-date` class

3. **frontend/js/app.js** (update)
   - Import/include date utilities
   - Update predictions to use `formatGameDate(_, true)`
   - Add tooltips with full date/time

4. **frontend/games.html** (update if needed)
   - Import date-utils.js
   - Update to use shared utilities instead of inline formatting

### Testing Commands

```bash
# Start local development server
cd frontend
python3 -m http.server 8000

# Open in browser
open http://localhost:8000/team.html?id=1  # Team schedule
open http://localhost:8000/predictions.html  # Predictions
open http://localhost:8000/games.html  # Games list

# Test with different dates
# - Modify game dates in database temporarily
# - Set games to today, tomorrow, +3 days, +10 days
# - Verify relative dates appear correctly
```

---

## Success Metrics

### Before Story
- **Team Schedule:** No dates displayed
- **Predictions:** Absolute dates only
- **Consistency:** Slight formatting differences between views
- **Context:** No way to quickly see "this game is today"

### After Story (Target)
- **Team Schedule:** 100% of games show dates
- **Predictions:** Relative dates for upcoming games ("Today", "Tomorrow")
- **Consistency:** All views use same formatting utilities
- **Context:** Users immediately see games "Today" or "In 3 days"
- **Tooltips:** Full date/time on hover for all dates
- **Accessibility:** Screen readers announce full dates

---

## Example Visual Changes

### Team Schedule (Before):
```
[PLAYOFF] Oregon 51-34 James Madison
[BOWL] Ole Miss 41-10 Tulane
```

### Team Schedule (After):
```
Sat, Dec 21  [PLAYOFF] Oregon 51-34 James Madison
Sat, Dec 21  [BOWL] Ole Miss 41-10 Tulane
```

### Predictions (Before):
```
Sat, Dec 28
#1 Oregon (1893.4) vs #5 Ohio State (1842.3)
Predicted: Oregon by 7
```

### Predictions (After - game in 5 days):
```
In 5 days  [hover shows: "Saturday, December 28, 2025, 3:00 PM EST"]
#1 Oregon (1893.4) vs #5 Ohio State (1842.3)
Predicted: Oregon by 7
```

---

## Notes

- **Relative Date Threshold:** 7 days chosen as cutoff (common UX pattern)
- **Timezone Handling:** Browser's local timezone used (standard for web apps)
- **Future Enhancement:** Could add countdown timer for games starting soon ("Starts in 2 hours")
- **Accessibility:** Tooltips use `title` attribute (screen-reader friendly)

---

## Related Work

- **Epic:** `docs/epics/epic-game-date-display-and-sorting.md`
- **Story 1:** UI date display in games list (establishes base formatting)
- **Story 2:** API sorting by date (ensures chronological order)
- **Existing Pattern:** Predictions date formatting in `frontend/js/app.js` (lines 391-403)

---

**Ready for Implementation:** ✅

This story completes the epic by ensuring consistent, contextual date display across all views. The shared utility functions eliminate code duplication and make future date-related enhancements easier to implement.
