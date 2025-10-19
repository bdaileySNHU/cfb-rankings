# Story 009: Frontend FCS Game Display on Team Schedules

**Epic**: EPIC-003 FCS Game Display for Schedule Completeness
**Story Type**: Brownfield Frontend Enhancement
**Priority**: High
**Estimated Effort**: 2-3 hours

---

## User Story

As a **college football fan viewing a team page**,
I want **to see the team's complete schedule including FCS opponents**,
So that **I understand the full context of their season without confusion about rankings**.

---

## Story Context

### Existing System Integration

- **Integrates with**:
  - `frontend/team.html` (team detail page)
  - `frontend/js/team.js` (schedule display logic)
  - `frontend/js/api.js` (API client)
  - `frontend/css/team.css` (styling)
- **Technology**: Vanilla JavaScript (ES6+), HTML5, CSS3
- **Follows pattern**: Existing schedule rendering in `createScheduleRow()` function
- **Touch points**:
  - `loadSchedule()` function (fetches data)
  - `createScheduleRow()` function (renders each game)
  - Team record display (must show FBS-only record)

### Current Behavior

Currently, `team.js` fetches and displays only FBS games. The schedule table shows gaps where FCS games occurred (e.g., Ohio State shows Week 1, 3, 5, 6 but not Week 2).

### New Behavior

After this story:
1. Schedule table shows all weeks including FCS games
2. FCS games are visually distinct (grayed out, labeled "FCS")
3. FCS games have tooltip/badge explaining they don't count toward rankings
4. Team record display continues to show FBS-only record
5. User understands complete schedule at a glance

---

## Acceptance Criteria

### Functional Requirements

1. **Display FCS games in schedule table**
   - All games (FBS and FCS) appear in chronological order by week
   - No gaps in week numbers
   - FCS games are clearly visible but visually distinct

2. **Visual distinction for FCS games**
   - FCS game rows have different styling (grayed text, lighter background)
   - FCS opponent name has "FCS" badge or label
   - Score display is de-emphasized for FCS games
   - Clear visual hierarchy: FBS games prominent, FCS games secondary

3. **Team record shows FBS games only**
   - Team record (e.g., "5-0") reflects FBS games only
   - Clarifying text: "Record (FBS only)" or similar
   - Tooltip or note explains FCS games are excluded from record

### Integration Requirements

4. **Existing schedule display continues to work**
   - FBS games render with current styling
   - Game results (W/L) display correctly
   - Opponent links work for both FBS and FCS teams
   - Neutral site indicator works

5. **Follows existing frontend patterns**
   - Uses same DOM manipulation patterns as `createScheduleRow()`
   - CSS follows existing class naming conventions
   - JavaScript follows ES6 module pattern
   - Responsive design maintained

6. **API integration works correctly**
   - `api.getTeamSchedule()` handles new fields
   - Properly reads `excluded_from_rankings` and `is_fcs` flags
   - Error handling for missing/unexpected data

### Quality Requirements

7. **Visual design is clear and intuitive**
   - User immediately understands FCS vs FBS distinction
   - No confusion about why some games look different
   - Design is accessible (color contrast, screen readers)
   - Mobile responsive (works on small screens)

8. **Code quality**
   - Code is clean and well-commented
   - No duplicate logic
   - Follows existing code style
   - No console errors

9. **No regression in existing functionality**
   - FBS game display unchanged
   - Team record display accurate
   - Schedule table formatting preserved
   - Page load performance acceptable

---

## Technical Implementation Notes

### API Client Update (frontend/js/api.js)

No changes needed - `getTeamSchedule()` already fetches all fields. The API response now includes `excluded_from_rankings` and `is_fcs` fields.

### Schedule Display Update (frontend/js/team.js)

```javascript
function createScheduleRow(game) {
  const row = document.createElement('tr');

  // Check if game has been played
  const isPlayed = game.is_played && game.score;

  // NEW: Check if FCS game
  const isFCS = game.is_fcs || game.excluded_from_rankings;

  // Apply appropriate row styling
  if (!isPlayed) {
    row.classList.add('game-scheduled');
  } else if (isFCS) {
    row.classList.add('game-fcs');  // NEW: FCS game styling
  }

  // Week cell
  const weekCell = document.createElement('td');
  weekCell.textContent = `Week ${game.week}`;
  weekCell.style.fontWeight = '600';
  row.appendChild(weekCell);

  // Opponent cell
  const oppCell = document.createElement('td');
  const oppLink = document.createElement('a');
  oppLink.href = `team.html?id=${game.opponent_id}`;
  oppLink.textContent = game.opponent_name;

  if (isFCS) {
    // FCS opponent - grayed out styling
    oppLink.style.color = 'var(--text-secondary)';
    oppLink.style.fontStyle = 'normal';

    // Add FCS badge
    const fcsBadge = document.createElement('span');
    fcsBadge.className = 'fcs-badge';
    fcsBadge.textContent = 'FCS';
    fcsBadge.title = 'FCS opponent - not included in rankings';
    oppCell.appendChild(oppLink);
    oppCell.appendChild(document.createTextNode(' '));
    oppCell.appendChild(fcsBadge);
  } else if (isPlayed) {
    // FBS played game - normal styling
    oppLink.style.color = 'var(--primary-color)';
    oppLink.style.fontWeight = '600';
    oppCell.appendChild(oppLink);
  } else {
    // Future FBS game - grayed out
    oppLink.style.color = 'var(--text-secondary)';
    oppLink.style.fontStyle = 'italic';
    oppCell.appendChild(oppLink);
  }

  oppLink.style.textDecoration = 'none';
  oppLink.onmouseover = () => oppLink.style.textDecoration = 'underline';
  oppLink.onmouseout = () => oppLink.style.textDecoration = 'none';

  row.appendChild(oppCell);

  // Location cell
  const locCell = document.createElement('td');
  if (game.is_neutral_site) {
    locCell.textContent = 'Neutral';
  } else {
    locCell.textContent = game.is_home ? 'Home' : 'Away';
  }
  locCell.style.color = 'var(--text-secondary)';
  if (!isPlayed || isFCS) {
    locCell.style.fontStyle = 'italic';
  }
  row.appendChild(locCell);

  // Result cell
  const resultCell = document.createElement('td');
  if (isPlayed) {
    const resultSpan = document.createElement('span');
    resultSpan.className = 'game-result';

    if (isFCS) {
      // FCS game - de-emphasized result
      resultSpan.textContent = game.score;
      resultSpan.style.color = 'var(--text-secondary)';
      resultSpan.style.fontStyle = 'italic';
      resultSpan.title = 'FCS game - not included in rankings or record';
    } else {
      // FBS game - normal result styling
      const isWin = game.score.startsWith('W');
      resultSpan.classList.add(isWin ? 'win' : 'loss');
      resultSpan.textContent = game.score;
    }

    resultCell.appendChild(resultSpan);
  } else {
    // Future game
    resultCell.textContent = `vs ${game.opponent_name}`;
    resultCell.style.color = 'var(--text-secondary)';
    resultCell.style.fontStyle = 'italic';
  }
  row.appendChild(resultCell);

  return row;
}
```

### CSS Updates (frontend/css/team.css or inline styles)

```css
/* FCS Game Row Styling */
.game-fcs {
  background-color: rgba(0, 0, 0, 0.02);
  opacity: 0.75;
}

.game-fcs:hover {
  background-color: rgba(0, 0, 0, 0.04);
  opacity: 0.85;
}

/* FCS Badge */
.fcs-badge {
  display: inline-block;
  padding: 2px 6px;
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 3px;
  margin-left: 8px;
  cursor: help;
}

.fcs-badge:hover {
  background-color: var(--accent-color);
  color: white;
}
```

### Team Record Display Update

Update the team info section to clarify FBS-only record:

```javascript
// In populateTeamInfo() function
const recordEl = document.getElementById('team-record');
recordEl.innerHTML = `
  <span class="record-value">${team.wins}-${team.losses}</span>
  <span class="record-note" title="Record includes FBS opponents only">FBS Only</span>
`;

if (team.losses === 0 && team.wins > 0) {
  recordEl.querySelector('.record-value').classList.add('undefeated');
}
```

Additional CSS:
```css
.record-note {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-left: 4px;
  font-weight: normal;
  cursor: help;
}
```

### HTML Update (frontend/team.html)

Add informational note above schedule table:

```html
<div class="schedule-section">
  <h2>Schedule</h2>

  <!-- NEW: Info box explaining FCS games -->
  <div class="info-box">
    <span class="info-icon">ℹ️</span>
    <span class="info-text">
      Complete schedule shown. FCS opponents are displayed but excluded from rankings and record.
    </span>
  </div>

  <div id="schedule-loading" class="loading hidden">
    Loading schedule...
  </div>

  <!-- ... existing schedule table ... -->
</div>
```

CSS for info box:
```css
.info-box {
  background-color: var(--bg-secondary);
  border-left: 4px solid var(--accent-color);
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 4px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  font-size: 1.2rem;
}

.info-text {
  line-height: 1.4;
}
```

---

## Design Mockup

### Before (Current)
```
SCHEDULE
Week 1    Texas          Away    W 14-7
Week 3    Ohio           Home    W 37-9
Week 5    Washington     Away    W 24-6
Week 6    Minnesota      Home    W 42-3
```

### After (With FCS Games)
```
SCHEDULE
ℹ️ Complete schedule shown. FCS opponents are displayed but excluded from rankings and record.

Week 1    Texas          Away    W 14-7
Week 2    Grambling FCS  Home    W 70-0    [grayed out, italic]
Week 3    Ohio           Home    W 37-9
Week 5    Washington     Away    W 24-6
Week 6    Minnesota      Home    W 42-3

Record: 4-0 (FBS Only)
```

---

## Acceptance Criteria Details

### Visual Requirements

**FCS Game Row:**
- Background: Light gray (rgba(0,0,0,0.02))
- Text color: Secondary (grayed)
- Font style: Normal weight (not bold)
- Opacity: 0.75

**FCS Badge:**
- Text: "FCS"
- Size: Small (0.75rem)
- Color: Secondary text on secondary background
- Tooltip: "FCS opponent - not included in rankings"
- Position: After opponent name

**Record Display:**
- Text: "4-0 (FBS Only)" or "4-0" with note
- Note style: Small, secondary color
- Tooltip: Explains FCS exclusion

### Accessibility Requirements

- Color contrast meets WCAG AA standards
- Screen reader announces FCS badge
- Keyboard navigation works
- Tooltips are accessible

---

## Definition of Done

- ✅ FCS games display in schedule table
- ✅ FCS games have distinct visual styling
- ✅ FCS badge appears next to opponent name
- ✅ Team record shows "FBS Only" clarification
- ✅ Info box explains FCS exclusion
- ✅ All existing schedule features work (links, neutral site, etc.)
- ✅ Responsive design maintained
- ✅ Accessible (keyboard, screen reader)
- ✅ No console errors
- ✅ Code follows existing style

---

## Test Cases

### Manual Testing Checklist

**Ohio State Schedule:**
- ✅ Shows 5 games (Weeks 1, 2, 3, 5, 6)
- ✅ Week 2 (Grambling) is grayed out with FCS badge
- ✅ FBS games (1, 3, 5, 6) have normal styling
- ✅ Record shows "4-0" or "4-0 (FBS Only)"
- ✅ Hover over FCS badge shows tooltip
- ✅ Info box displays above schedule

**Georgia Schedule:**
- ✅ Shows 5 games (Weeks 1, 2, 3, 5, 6)
- ✅ Week 2 (Austin Peay) is FCS game with badge
- ✅ Record accurate (excludes FCS game)

**Responsive Design:**
- ✅ Mobile view works (schedule table scrolls or stacks)
- ✅ FCS badge doesn't break layout on small screens
- ✅ Info box is readable on mobile

**Accessibility:**
- ✅ Tab navigation works through schedule
- ✅ Screen reader announces FCS badge
- ✅ Tooltips accessible via keyboard
- ✅ Color contrast sufficient

### Edge Cases

- ✅ Team with no FCS games (schedule looks normal)
- ✅ Team with all FCS games (all grayed, record is 0-0)
- ✅ Team with no games yet (empty schedule)
- ✅ FCS team page (if accessible) displays correctly

---

## Risk Assessment

### Primary Risk
User confusion about why some games are grayed out

### Mitigation
- Clear info box at top of schedule
- FCS badge with descriptive tooltip
- "FBS Only" note on record
- Consistent visual language

### Rollback Plan
- Git revert of `team.js` and CSS changes
- Changes are purely frontend (no backend dependency)
- Can rollback independently of Stories 007/008

---

## Dependencies

- **Depends on**: Story 008 (API returns FCS games)
- **Blocked by**: None
- **Blocks**: None (can be deployed independently after 008)

---

## Future Enhancements (Out of Scope)

- Filter toggle to show/hide FCS games
- Separate FBS and FCS record display (e.g., "4-0 FBS, 1-0 FCS")
- Detailed stats for FCS games
- FCS opponent detail pages

---

**Created by**: John (PM Agent)
**Date**: 2025-10-18
**Story Points**: 3
**Priority**: P2 (After Story 008)
