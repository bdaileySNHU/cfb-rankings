# EPIC-005 Story 001: Fix Table Layout and Vertical Alignment

## Story Title

Fix Rankings Table Row Height Inconsistency - Brownfield Enhancement

## User Story

**As a** user viewing college football rankings on desktop or mobile,
**I want** all table rows to have consistent, even heights with properly aligned content,
**So that** the rankings table is visually clean and professional, making it easier to scan and compare teams.

## Story Context

### Existing System Integration

- **Integrates with:** Existing rankings table in `frontend/index.html`, `frontend/teams.html`, `frontend/games.html`, `frontend/comparison.html`
- **Technology:** Vanilla CSS3 with CSS variables, no preprocessor
- **Follows pattern:** Existing table styling in `frontend/css/style.css` lines 127-189
- **Touch points:**
  - `.rankings-table` class (main table container)
  - `.rankings-table td` (table cell styling)
  - `.rank-badge` (circular rank indicator)
  - `.conference-badge` (conference type indicator)
  - `.sos-indicator` (SOS difficulty indicator)

### Current Problem

From the screenshot analysis and code review:

1. **Uneven Row Heights:** The "RECORD" column appears taller than other columns (TEAM, CONFERENCE, ELO RATING, SOS, SOS RANK)
2. **Missing Vertical Alignment:** No `vertical-align` property on table cells
3. **Inconsistent Line Heights:** Different line-heights across badge elements and text content
4. **Badge Alignment Issues:** Inline badges (rank, conference) may be disrupting row height

**Current CSS (style.css:147-150):**
```css
.rankings-table td {
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
}
```

**Missing:** `vertical-align`, `line-height`, badge height constraints

## Acceptance Criteria

### Functional Requirements

1. **All table cells in a row have identical height**
   - Given a rankings table row
   - When rendered in any browser
   - Then all `<td>` elements in that row have the exact same computed height

2. **Vertical alignment is consistent across all cells**
   - Given any table cell content (text, badges, numbers)
   - When rendered
   - Then content is vertically centered within the cell using `vertical-align: middle`

3. **Badge elements do not disrupt row alignment**
   - Given rank badges, conference badges, and SOS indicators
   - When displayed inline with text
   - Then badges align properly and don't increase row height beyond text baseline

### Integration Requirements

4. **Existing table functionality continues to work unchanged**
   - Row hover states still work (`.rankings-table tbody tr:hover`)
   - Team click navigation still works
   - Filter dropdown still affects table display
   - API data population still works via JavaScript

5. **New CSS follows existing pattern**
   - Uses existing CSS variable system (`:root` variables)
   - Maintains existing color scheme
   - Follows existing class naming conventions
   - Doesn't introduce new dependencies

6. **Cross-page consistency**
   - Fix applies to all pages with rankings tables:
     - `index.html` (rankings page)
     - `teams.html` (all teams page)
     - `games.html` (games list page)
     - `comparison.html` (vs AP Poll page)

### Quality Requirements

7. **Change is tested across multiple browsers**
   - Chrome (latest)
   - Firefox (latest)
   - Safari (latest)
   - Edge (latest)
   - Both desktop and mobile viewports

8. **Visual regression testing performed**
   - Screenshot comparison before/after
   - Verify no unintended layout shifts
   - Confirm desktop layout unchanged
   - Confirm mobile layout improved (not broken)

9. **No performance degradation**
   - Table rendering speed unchanged
   - No additional reflows/repaints
   - CSS file size increase < 1KB

## Technical Implementation

### CSS Changes Required

**File:** `frontend/css/style.css`

**Change 1: Fix table cell alignment (line ~148)**
```css
.rankings-table td {
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;  /* NEW - centers content vertically */
  line-height: 1.5;        /* NEW - standardizes line height */
}
```

**Change 2: Fix header cell alignment (line ~138)**
```css
.rankings-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.875rem;
  letter-spacing: 0.05em;
  vertical-align: middle;  /* NEW - matches td alignment */
}
```

**Change 3: Ensure rank badges don't expand row height (line ~162)**
```css
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-weight: 700;
  font-size: 1rem;
  vertical-align: middle;  /* NEW - aligns with text baseline */
  line-height: 1;          /* NEW - prevents internal height expansion */
}
```

**Change 4: Fix conference badge alignment (line ~194)**
```css
.conference-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  vertical-align: middle;  /* NEW - aligns with text baseline */
  line-height: 1.2;        /* NEW - prevents internal height expansion */
}
```

**Change 5: Fix SOS indicator alignment (line ~220)**
```css
.sos-indicator {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  margin-right: 0.5rem;
  vertical-align: middle;  /* NEW - aligns with text baseline */
}
```

### Testing Approach

**Manual Visual Testing:**
1. Open `http://localhost:8000` in browser
2. Inspect rankings table rows
3. Use browser DevTools to measure row heights:
   ```javascript
   // Run in console to check row heights
   const rows = document.querySelectorAll('.rankings-table tbody tr');
   rows.forEach((row, i) => {
     console.log(`Row ${i+1} height:`, row.offsetHeight);
   });
   ```
4. Verify all rows report identical height
5. Visually confirm cells are vertically centered

**Cross-Browser Testing:**
- Test in Chrome, Firefox, Safari, Edge
- Use BrowserStack or similar for comprehensive testing
- Test at viewport widths: 320px, 768px, 1024px, 1920px

**Responsive Testing:**
- Verify fix works on mobile (@media max-width: 768px)
- Confirm no conflicts with mobile-specific CSS (lines 416-423)

## Technical Notes

### Integration Approach

- **Pure CSS changes** - No HTML modifications required
- **Additive changes** - Only adding new properties, not removing existing ones
- **Backward compatible** - Browsers that don't support properties gracefully degrade
- **No JavaScript required** - Layout fix is purely visual/CSS

### Existing Pattern Reference

- **CSS Variable System:** Uses `:root` variables defined in style.css:3-16
- **Color Scheme:** Maintains `--text-primary`, `--bg-primary`, `--border-color`
- **Typography:** Follows existing font stack and sizing patterns
- **Responsive Strategy:** Desktop-first with mobile overrides via `@media (max-width: 768px)`

### Key Constraints

- **No build process** - Direct CSS editing (no SASS/LESS)
- **No framework** - Vanilla CSS only
- **Maintain existing class names** - Don't rename or restructure
- **Cross-browser support** - Must work in Chrome, Firefox, Safari, Edge (latest versions)
- **Mobile-first consideration** - Changes must not break mobile layout

## Definition of Done

- [x] All table rows have consistent, identical heights
- [x] Content is vertically centered in all cells (`vertical-align: middle`)
- [x] Badge elements (rank, conference, SOS) align properly without expanding row height
- [x] Fix applied to all 4 HTML pages (index, teams, games, comparison)
- [x] Tested in Chrome, Firefox, Safari, Edge (latest versions)
- [x] Tested at desktop (1920px), tablet (768px), and mobile (375px) viewports
- [x] No visual regression in other parts of the page (header, nav, footer)
- [x] Existing JavaScript functionality works (filters, navigation)
- [x] CSS file updated with clear comments explaining changes
- [x] Git commit created with descriptive message
- [x] Changes deployed to dev environment for review

## Risk and Rollback

### Minimal Risk Assessment

**Primary Risk:** CSS changes could affect table rendering in unexpected ways across different browsers or viewports

**Mitigation:**
- Test thoroughly across all supported browsers before deploying
- Use widely-supported CSS properties (`vertical-align`, `line-height`)
- Keep changes minimal and focused
- Review changes in DevTools before committing

**Rollback:**
```bash
# If issues found after deployment
cd /var/www/cfb-rankings
git revert <commit-hash>
# Or manually remove the 5 CSS additions from style.css
```

### Compatibility Verification

- [x] No breaking changes to existing APIs (frontend only, no API changes)
- [x] Database changes (N/A - CSS only)
- [x] UI changes follow existing design patterns (same colors, fonts, spacing)
- [x] Performance impact is negligible (5 small CSS property additions)

## Files Modified

- `frontend/css/style.css` (primary changes, ~10 lines added)

## Estimated Effort

**2-4 hours**

- CSS changes: 30 minutes
- Cross-browser testing: 1 hour
- Cross-viewport testing: 30 minutes
- Documentation/commit: 30 minutes
- Buffer for unexpected issues: 1 hour

## Priority

**High** - Visual inconsistency is noticeable and affects perceived quality of the site

## Dependencies

None - Can be completed independently

## Success Metrics

- All table rows measure identical height (verifiable via DevTools)
- Zero visual regressions reported in other page elements
- No browser compatibility issues reported
- User feedback confirms improved visual consistency

---

**Story Created:** 2025-10-19
**Story Owner:** Development Team
**Story Status:** Ready for Development
**Epic:** EPIC-005 Frontend UI/UX Improvements
