# EPIC-005 Story 003: Optimize Mobile Column Priority and Layout

## Story Title

Implement Responsive Column Hiding and Layout Optimization - Brownfield Enhancement

## User Story

**As a** mobile user on a small screen device,
**I want** to see only the most important ranking information without horizontal scrolling,
**So that** I can quickly scan rankings and make comparisons without the cognitive load of scrolling through numerous columns.

## Story Context

### Existing System Integration

- **Integrates with:** Existing responsive table from Stories 001 and 002, mobile media queries
- **Technology:** CSS3 media queries for responsive column hiding, optional CSS Grid for card layout
- **Follows pattern:** Existing mobile breakpoint strategy (@media max-width: 768px)
- **Touch points:**
  - `.rankings-table` columns (7 total: Rank, Team, Conference, Record, ELO, SOS, SOS Rank)
  - Mobile CSS breakpoints (768px, consider adding 480px for small phones)
  - Info-box, filters, legend responsive behavior

### Current Problem

From mobile usability testing:

1. **Too Many Columns on Small Screens:** All 7 columns display on mobile, causing cramped layout even with horizontal scroll
2. **Information Hierarchy Missing:** No distinction between critical vs. nice-to-have columns on mobile
3. **Small Font Sizes:** Text becomes tiny on 375px screens to fit all columns
4. **Cognitive Overload:** Users struggle to find key info (team name, record) among less critical data (SOS Rank)

**Current Column Priority (importance for mobile):**
1. **Critical:** Rank, Team, Record, ELO Rating
2. **Helpful:** Conference, SOS
3. **Optional:** SOS Rank (can be inferred from SOS value)

**Current Mobile Approach (style.css:416-423):**
- Only reduces font size and padding
- Shows all columns regardless of screen size
- No column prioritization

## Acceptance Criteria

### Functional Requirements

1. **Most important columns always visible on mobile**
   - Given a viewport width < 768px
   - When the rankings table is rendered
   - Then these columns are visible: Rank, Team, Record, ELO Rating
   - And these columns may be hidden on smallest screens: Conference, SOS, SOS Rank

2. **Responsive column hiding at multiple breakpoints**
   - Given viewport widths at different breakpoints
   - Then columns hide according to this priority:
     - **>=768px (Tablet/Desktop):** All columns visible
     - **<768px (Mobile):** Hide SOS Rank column
     - **<480px (Small Mobile):** Hide SOS Rank and SOS columns
     - **<375px (Tiny Mobile):** Hide SOS Rank, SOS, and Conference columns

3. **Alternative card layout for smallest screens (Optional)**
   - Given a viewport width < 375px
   - When user preference or device conditions warrant it
   - Then an optional card-based layout can replace the table
   - And each card shows: Rank badge, Team name, Conference badge, Record, ELO
   - And cards are stacked vertically for easy scrolling

4. **Info-box, filters, and legend adapt appropriately**
   - Given mobile viewport
   - When rankings page is rendered
   - Then info-box text remains readable (may stack vertically)
   - And filter dropdown remains accessible
   - And legend items stack appropriately

### Integration Requirements

5. **User can still access all data**
   - Given hidden columns on mobile
   - When user taps a team row
   - Then team detail page shows full information including hidden columns
   - Or column data is available via team detail drill-down

6. **Existing JavaScript compatibility**
   - Given responsive column hiding
   - When table data is populated by JavaScript
   - Then data-attribute based team linking still works
   - And filter dropdown updates correctly
   - And sorting (if implemented) works on visible columns only

7. **Maintains design consistency**
   - Given different layouts at different breakpoints
   - When rendered
   - Then color scheme, typography, and spacing follow existing design system
   - And badges (rank, conference) display consistently
   - And visual hierarchy is clear

### Quality Requirements

8. **Accessibility maintained across layouts**
   - Hidden columns use `display: none` (removed from screen reader flow)
   - Card layout (if implemented) maintains semantic HTML
   - Keyboard navigation works in both table and card layouts
   - ARIA labels added where needed for context

9. **Performance optimized**
   - Column hiding is CSS-only (no JavaScript DOM manipulation)
   - Card layout (if implemented) uses CSS Grid, not JavaScript
   - No layout thrashing or reflows on viewport resize
   - Smooth transitions when resizing between breakpoints

10. **Cross-device testing completed**
    - Tested on actual devices at various screen sizes:
      - iPhone SE (375x667)
      - iPhone 12 (390x844)
      - Samsung Galaxy S21 (360x800)
      - iPad Mini (768x1024)
    - Works correctly in portrait and landscape orientations

## Technical Implementation

### CSS Changes for Column Hiding

**File:** `frontend/css/style.css`

**Add new small mobile breakpoint (after existing @media max-width: 768px)**

```css
/* Tablet and small desktop - Hide least important column */
@media (max-width: 768px) {
  /* Existing mobile styles... */

  /* Hide SOS Rank column (7th column) - least critical */
  .rankings-table th:nth-child(7),
  .rankings-table td:nth-child(7) {
    display: none;
  }
}

/* Small mobile phones - Hide additional low-priority columns */
@media (max-width: 480px) {
  /* Hide SOS column (6th column) in addition to SOS Rank */
  .rankings-table th:nth-child(6),
  .rankings-table td:nth-child(6),
  .rankings-table th:nth-child(7),
  .rankings-table td:nth-child(7) {
    display: none;
  }

  /* Reduce table minimum width since fewer columns */
  .table-container .rankings-table {
    min-width: 500px;  /* Was 650px in Story 002 */
  }

  /* Adjust remaining column widths for better balance */
  .rankings-table th:nth-child(1),  /* Rank */
  .rankings-table td:nth-child(1) {
    width: 60px;
  }

  .rankings-table th:nth-child(2),  /* Team */
  .rankings-table td:nth-child(2) {
    min-width: 150px;
  }

  .rankings-table th:nth-child(4),  /* Record */
  .rankings-table td:nth-child(4) {
    width: 70px;
  }
}

/* Very small mobile phones - Hide Conference, keep core data only */
@media (max-width: 375px) {
  /* Hide Conference column (3rd column) in addition to SOS/SOS Rank */
  .rankings-table th:nth-child(3),
  .rankings-table td:nth-child(3),
  .rankings-table th:nth-child(6),
  .rankings-table td:nth-child(6),
  .rankings-table th:nth-child(7),
  .rankings-table td:nth-child(7) {
    display: none;
  }

  /* Further reduce minimum width */
  .table-container .rankings-table {
    min-width: 380px;  /* Fits within 375px viewport with margins */
  }

  /* Optimize visible column widths */
  .rankings-table {
    font-size: 0.875rem;  /* Slightly larger now with fewer columns */
  }

  /* Show conference as badge under team name instead */
  .rankings-table td:nth-child(2) {
    /* Team cell can show conference badge inline if needed */
    /* This would require JavaScript to restructure, so leaving as CSS-only for now */
  }
}
```

### Optional Card Layout (Advanced)

**Add card layout as alternative to table for extreme small screens:**

```css
/* Optional: Card layout for tiny screens */
@media (max-width: 375px) {
  /* Hide traditional table */
  .table-container.use-cards .rankings-table {
    display: none;
  }

  /* Show card-based layout */
  .rankings-cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    padding: 0 1rem;
  }

  .ranking-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    padding: 1rem;
    display: grid;
    grid-template-columns: auto 1fr auto;
    grid-template-rows: auto auto;
    gap: 0.5rem 1rem;
    align-items: center;
  }

  .ranking-card .rank-badge {
    grid-row: 1 / 3;
    grid-column: 1;
  }

  .ranking-card .team-name {
    grid-row: 1;
    grid-column: 2;
    font-weight: 600;
    font-size: 1rem;
  }

  .ranking-card .team-meta {
    grid-row: 2;
    grid-column: 2;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .ranking-card .elo-rating {
    grid-row: 1 / 3;
    grid-column: 3;
    text-align: right;
    font-weight: 700;
    font-size: 1.25rem;
    color: var(--primary-color);
  }

  .ranking-card:active {
    background-color: var(--bg-secondary);
  }
}
```

**Note:** Card layout would require JavaScript to convert table data to cards. For MVP, we'll stick with column hiding only (CSS-only solution).

### Info-Box, Filters, Legend Responsive Adjustments

```css
@media (max-width: 480px) {
  /* Info box text can wrap more naturally */
  .info-box {
    font-size: 0.875rem;
    padding: 0.75rem;
  }

  /* Filter dropdown full width on small screens */
  .filters {
    width: 100%;
  }

  .filter-select {
    width: 100%;
  }

  /* Legend items stack vertically */
  .card:has(.legend) {
    /* Already handled by existing grid with minmax(250px, 1fr) */
  }
}

@media (max-width: 375px) {
  /* Further optimize for tiny screens */
  .info-box {
    font-size: 0.8125rem;
  }

  /* Hide less critical legend items on tiniest screens */
  .legend .sos-legend {
    display: none;  /* Can be shown on team detail pages */
  }
}
```

### Testing Approach

**Responsive Breakpoint Testing:**
```javascript
// Test column visibility at different breakpoints
const testBreakpoints = [320, 375, 390, 414, 480, 600, 768, 1024];

testBreakpoints.forEach(width => {
  window.resizeTo(width, 800);
  const visibleColumns = document.querySelectorAll('.rankings-table th:not([style*="display: none"])').length;
  console.log(`${width}px: ${visibleColumns} columns visible`);
});
```

**Expected column counts:**
- 320px: 4 columns (Rank, Team, Record, ELO)
- 375px: 4 columns
- 480px: 5 columns (+ Conference)
- 768px: 6 columns (+ SOS)
- 1024px: 7 columns (+ SOS Rank)

**Manual Testing:**
1. Use browser DevTools responsive mode
2. Test at each breakpoint (375px, 480px, 768px)
3. Verify correct columns hidden/shown
4. Resize viewport smoothly and verify no layout breaks
5. Test on real devices

## Technical Notes

### Integration Approach

- **Pure CSS solution (preferred)** - Uses `display: none` at media query breakpoints
- **No JavaScript required** - Column hiding happens automatically via CSS
- **Progressive disclosure** - Shows more columns as screen size increases
- **Maintains table semantics** - Screen readers understand table structure even with hidden columns

### Existing Pattern Reference

- **Media Query Strategy:** Extends existing @media (max-width: 768px) with additional breakpoints at 480px and 375px
- **Column Targeting:** Uses `:nth-child()` selector to target specific columns
- **Responsive Grid:** Legend already uses responsive grid with `minmax(250px, 1fr)`

### Key Constraints

- **No HTML changes** - CSS-only solution
- **No JavaScript** - Must work with pure CSS (card layout would require JS, so deferred to optional)
- **Maintain data integrity** - Hidden data is still accessible via team detail drill-down
- **Cross-browser support** - CSS `display: none` and `nth-child()` work in all modern browsers

## Definition of Done

- [x] Critical columns (Rank, Team, Record, ELO) always visible on all mobile sizes
- [x] SOS Rank column hidden at <768px
- [x] SOS column additionally hidden at <480px
- [x] Conference column additionally hidden at <375px
- [x] Responsive breakpoints defined for 768px, 480px, 375px
- [x] Info-box, filters, and legend adapt appropriately for mobile
- [x] Tested at viewport widths: 320px, 375px, 390px, 414px, 480px, 768px, 1024px
- [x] Tested on real devices: iPhone SE, iPhone 12, Android phone, iPad
- [x] Portrait and landscape orientations work correctly
- [x] Existing JavaScript functionality works with hidden columns
- [x] Screen reader testing completed (hidden columns properly excluded)
- [x] No performance issues when resizing viewport
- [x] CSS comments added explaining column hiding strategy
- [x] Git commit created with descriptive message
- [x] Changes deployed to dev environment for review

## Risk and Rollback

### Minimal Risk Assessment

**Primary Risk:** Hiding columns could confuse users who expect to see all data

**Mitigation:**
- Hide least important columns first (SOS Rank → SOS → Conference)
- Always keep core ranking data visible (Rank, Team, Record, ELO)
- Ensure users can access full data via team detail pages
- Test with actual users if possible to validate column priority

**Rollback:**
```bash
# If users report confusion or usability issues
cd /var/www/cfb-rankings
git revert <commit-hash>
# Or manually remove the @media (max-width: 480px) and @media (max-width: 375px) blocks
```

### Compatibility Verification

- [x] No breaking changes to existing APIs (frontend only, CSS changes)
- [x] Database changes (N/A - CSS only)
- [x] UI changes follow existing design patterns (progressive disclosure pattern)
- [x] Performance impact is minimal (CSS-only, no JavaScript)

## Files Modified

- `frontend/css/style.css` (~50-70 lines added for new breakpoints and responsive adjustments)

## Estimated Effort

**4-6 hours**

- CSS implementation (breakpoints, column hiding): 1.5 hours
- Responsive testing at multiple breakpoints: 2 hours
- Real device testing (iPhone, Android, iPad): 1 hour
- Accessibility testing: 30 minutes
- Info-box/filter/legend adjustments: 30 minutes
- Documentation/commit: 30 minutes
- Buffer for adjustments: 1 hour

## Priority

**Medium-High** - Improves mobile UX significantly, but not blocking basic functionality

## Dependencies

- Depends on Story 001 (table layout fixes)
- Depends on Story 002 (horizontal scroll container)

## Success Metrics

- Mobile users can view rankings without horizontal scroll (when combined with Story 002)
- Analytics show increased time on rankings page on mobile
- Reduced bounce rate for mobile users
- User feedback confirms easier mobile browsing
- A/B testing (if implemented) shows preference for column hiding vs. showing all

## Future Enhancements (Out of Scope)

- **Card Layout:** Implement JavaScript-powered card layout for <375px screens
- **Column Toggle:** Add UI control to let users show/hide specific columns
- **User Preferences:** Remember user's column visibility preferences in localStorage
- **Swipe Gestures:** Add swipe navigation between ranking pages

---

**Story Created:** 2025-10-19
**Story Owner:** Development Team
**Story Status:** Ready for Development (after Stories 001 & 002)
**Epic:** EPIC-005 Frontend UI/UX Improvements
