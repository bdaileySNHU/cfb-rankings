# EPIC-005: Frontend UI/UX Improvements - Brownfield Enhancement

## Epic Goal

Improve the user experience of the College Football Rankings website by fixing table layout inconsistencies and enhancing mobile responsiveness, making the site more accessible and usable across all devices.

## Epic Description

### Existing System Context

- **Current Functionality:** Static HTML/CSS/JS frontend displaying college football rankings in a responsive table layout
- **Technology Stack:**
  - Vanilla HTML5
  - CSS3 with CSS variables
  - Vanilla JavaScript
  - FastAPI backend serving data
- **Integration Points:**
  - Frontend served as static files via Nginx
  - API calls to FastAPI backend at `/api/rankings`
  - Responsive design with mobile breakpoint at 768px

### Enhancement Details

**What's being added/changed:**

1. **Table Layout Fixes:**
   - Fix uneven row heights in rankings table (Record column currently taller than other columns)
   - Ensure consistent vertical alignment across all table cells
   - Standardize padding and line-height for visual consistency

2. **Mobile Responsiveness Improvements:**
   - Reduce table width on mobile devices to prevent horizontal scrolling
   - Implement horizontal scrolling container for table on mobile (not entire page)
   - Consider card-based layout alternative for mobile devices
   - Optimize column display priority for small screens

**How it integrates:**
- Pure CSS/HTML changes to existing frontend
- No backend changes required
- No API modifications
- Maintains existing design system (colors, fonts, spacing)

**Success Criteria:**
- ✅ Table rows have consistent, even heights across all columns
- ✅ Record column aligns properly with other columns
- ✅ Mobile users can view rankings table without horizontal page scroll
- ✅ Table content remains readable on screens down to 320px width
- ✅ No regression in desktop layout
- ✅ Maintains existing visual design language

## Stories

### Story 1: Fix Table Layout and Vertical Alignment

**Description:** Fix the uneven row heights in the rankings table, specifically addressing the Record column being taller than other columns.

**Acceptance Criteria:**
- All table cells in a row have identical height
- Vertical alignment is consistent (middle or top, consistently applied)
- Line-height and padding are standardized across all cells
- Text content doesn't cause row height variations
- Badge elements (rank badges, conference badges) don't disrupt row alignment

**Technical Approach:**
- Add `vertical-align: middle` to all `td` elements
- Standardize line-height across table cells
- Ensure badges and inline elements have consistent dimensions
- Test with varying content lengths (team names, records)

### Story 2: Implement Responsive Table Container for Mobile

**Description:** Make the rankings table mobile-friendly by implementing a horizontal scroll container that keeps the table readable without forcing page-wide scrolling.

**Acceptance Criteria:**
- Table scrolls horizontally within a container on mobile (<768px)
- Page itself doesn't scroll horizontally
- Scroll indicator/hint visible to users on mobile
- Table maintains readability at minimum mobile width (320px)
- All columns remain accessible via horizontal scroll
- Works across iOS Safari, Chrome Mobile, and Firefox Mobile

**Technical Approach:**
- Wrap table in `.table-container` div with `overflow-x: auto`
- Add visual scroll hint (fade gradient or scrollbar styling)
- Set minimum table width to prevent column crushing
- Add touch-friendly scroll behavior
- Test on actual mobile devices

### Story 3: Optimize Mobile Column Priority and Layout

**Description:** Enhance mobile user experience by optimizing column visibility and considering alternative layouts for small screens.

**Acceptance Criteria:**
- Most important columns (Rank, Team, Record, ELO) always visible on mobile
- Less critical columns (SOS Rank) hidden on smallest screens
- Responsive breakpoints defined for tablet (768px) and mobile (480px)
- Consider stacked/card layout as alternative to table on mobile
- User can still access all data (via tap/expand if card layout used)
- Loading states and error states work correctly in new layout

**Technical Approach:**
- Use CSS `display: none` for non-critical columns on mobile
- Implement media queries for 480px, 768px breakpoints
- *Optional:* Create card-based layout alternative using CSS Grid
- Maintain data-attribute based team linking for drill-down
- Ensure info-box, filters, and legend adapt appropriately

## Compatibility Requirements

- [x] Existing APIs remain unchanged (no backend modifications)
- [x] Database schema changes are backward compatible (no DB changes)
- [x] UI changes follow existing patterns (same color scheme, typography)
- [x] Performance impact is minimal (CSS-only changes, no JS framework added)
- [x] Works in existing supported browsers (Chrome, Firefox, Safari, Edge)

## Risk Mitigation

**Primary Risk:** Layout changes could break existing desktop user experience or cause unexpected behavior in mobile browsers

**Mitigation:**
- Test thoroughly across multiple browsers and devices
- Use progressive enhancement approach (desktop-first CSS, mobile overrides)
- Implement changes incrementally (Story 1 → Story 2 → Story 3)
- Use CSS feature detection where needed
- Maintain existing class names and structure

**Rollback Plan:**
- CSS changes are easily reversible via git revert
- No database migrations required
- Static file deployment allows instant rollback
- Keep backup of `style.css` before modifications

## Definition of Done

- [x] All stories completed with acceptance criteria met
- [x] Existing functionality verified through testing
  - Desktop layout unchanged and working
  - Rankings data loads correctly
  - Team links navigate properly
  - Filters function as expected
- [x] Integration points working correctly
  - API calls unchanged
  - Nginx serves updated static files
  - No console errors
- [x] Documentation updated appropriately
  - CSS comments added for new responsive rules
  - README updated if user-facing changes
- [x] No regression in existing features
  - Cross-browser testing completed
  - Mobile device testing completed
  - Accessibility verified (screen readers, keyboard nav)

## Technical Specifications

### Current Issues Identified

1. **Table Row Height Inconsistency:**
   - Location: `frontend/css/style.css` lines 147-150
   - Current CSS:
     ```css
     .rankings-table td {
       padding: 1rem;
       border-bottom: 1px solid var(--border-color);
     }
     ```
   - Missing: `vertical-align`, consistent `line-height`

2. **Mobile Overflow Issue:**
   - Location: `frontend/css/style.css` lines 416-423
   - Current CSS only reduces font-size and padding, doesn't handle table width
   - No horizontal scroll container implemented

3. **No Column Priority System:**
   - All columns show on mobile, causing cramped layout
   - No progressive disclosure of information
   - Table becomes unreadable below 600px width

### Proposed Solutions

**Story 1 Fix:**
```css
.rankings-table td {
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle; /* NEW */
  line-height: 1.5; /* NEW */
}

.rank-badge {
  /* Ensure badges don't expand row height */
  vertical-align: middle; /* NEW */
  line-height: 1; /* NEW */
}
```

**Story 2 Fix:**
```css
.table-container {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 0 -1rem; /* Extend to card edges */
}

@media (max-width: 768px) {
  .table-container {
    /* Add scroll hint */
    background: linear-gradient(90deg,
      var(--bg-primary) 0%,
      transparent 3%,
      transparent 97%,
      var(--bg-primary) 100%
    );
  }

  .rankings-table {
    min-width: 650px; /* Prevent column crush */
  }
}
```

**Story 3 Fix:**
```css
@media (max-width: 480px) {
  .rankings-table th:nth-child(7), /* SOS Rank */
  .rankings-table td:nth-child(7) {
    display: none;
  }

  .rankings-table th:nth-child(3), /* Conference */
  .rankings-table td:nth-child(3) {
    display: none; /* Or show as badge under team name */
  }
}
```

## Testing Plan

### Desktop Testing (>768px)
- [ ] Chrome, Firefox, Safari, Edge on macOS/Windows
- [ ] Table displays correctly with even row heights
- [ ] No horizontal scroll
- [ ] All columns visible
- [ ] Hover states work

### Tablet Testing (768px - 480px)
- [ ] iPad, Android tablets
- [ ] Table scrolls horizontally within container
- [ ] All columns accessible
- [ ] Page doesn't scroll horizontally

### Mobile Testing (<480px)
- [ ] iPhone (Safari), Android (Chrome)
- [ ] Critical columns visible
- [ ] Table remains usable
- [ ] Touch scrolling works smoothly
- [ ] 320px width edge case (iPhone SE)

### Cross-Browser Testing
- [ ] Chrome (latest, latest-1)
- [ ] Firefox (latest, latest-1)
- [ ] Safari (latest, iOS latest)
- [ ] Edge (latest)

### Accessibility Testing
- [ ] Screen reader navigation (VoiceOver, NVDA)
- [ ] Keyboard navigation works
- [ ] Color contrast maintained
- [ ] Text scales with browser zoom

## Deployment Notes

**Files Modified:**
- `frontend/css/style.css` (primary changes)
- `frontend/index.html` (add table-container div)
- `frontend/teams.html` (same table fix)
- `frontend/games.html` (same table fix)
- `frontend/comparison.html` (same table fix)

**Deployment Process:**
1. Make CSS changes locally
2. Test thoroughly in dev environment
3. Commit changes to git
4. Deploy to VPS (static files updated automatically via Nginx)
5. Verify on production
6. Monitor for user feedback

**Rollback:**
```bash
# If issues found in production
cd /var/www/cfb-rankings
git revert <commit-hash>
sudo systemctl reload nginx
```

## Story Manager Handoff

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing frontend running **vanilla HTML/CSS/JS with FastAPI backend**
- Integration points:
  - Nginx serves static files from `frontend/` directory
  - JavaScript calls FastAPI backend APIs
  - No build process (direct CSS/HTML editing)
- Existing patterns to follow:
  - CSS variables for theming (`:root` in style.css)
  - Mobile-first responsive design (currently 768px breakpoint)
  - Class naming convention (.kebab-case)
- Critical compatibility requirements:
  - **No backend changes**
  - **No new dependencies/frameworks**
  - **Maintain existing design system**
  - **Cross-browser compatibility (Chrome, Firefox, Safari, Edge)**
- Each story must include verification that existing functionality remains intact

The epic should maintain system integrity while delivering **improved table layouts and mobile responsiveness**."

## Estimated Effort

- **Story 1:** 2-4 hours (CSS fixes, cross-browser testing)
- **Story 2:** 4-6 hours (Container implementation, mobile testing)
- **Story 3:** 4-6 hours (Responsive strategy, multiple breakpoint testing)

**Total:** 10-16 hours for full epic completion

## Priority

**High** - User-reported issues affecting mobile experience (majority of web traffic is mobile)

## Dependencies

- None (frontend-only changes)

## Related Work

- Complements EPIC-004 (backend improvements completed)
- Prepares foundation for future progressive web app (PWA) features
- Improves accessibility for compliance with WCAG 2.1 AA

---

**Epic Created:** 2025-10-19
**Epic Owner:** Product Manager (John)
**Epic Status:** Draft - Ready for Story Development
