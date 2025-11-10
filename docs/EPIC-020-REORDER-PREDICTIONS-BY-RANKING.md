# EPIC-020: Reorder Game Predictions by Ranking - Brownfield Enhancement

## Epic Goal

Improve the main page UX by reordering game predictions to show the most compelling matchups first (based on team rankings) and repositioning the predictions section below the rankings table for better page flow.

## Epic Description

### Existing System Context

**Current Relevant Functionality:**
- Main page (`frontend/index.html`) displays predictions ABOVE rankings
- Predictions shown in API return order (no sorting)
- Prediction cards display matchups with win probabilities and confidence
- Backend already provides `home_team_rating` and `away_team_rating` in API response

**Technology Stack:**
- Frontend: HTML, CSS, JavaScript (vanilla JS)
- Backend: FastAPI (Python) - no changes needed
- Predictions API: `/api/predictions` returns ELO ratings for both teams
- Page structure: `frontend/index.html`, logic in `frontend/js/app.js`

**Integration Points:**
- `frontend/index.html` - HTML layout and card positioning
- `frontend/js/app.js` - `loadPredictions()` function fetches and displays predictions
- `frontend/js/app.js` - `createPredictionCard()` renders individual prediction cards
- Predictions API response already includes rating data for sorting

### Enhancement Details

**What's Being Added/Changed:**

1. **Reorder HTML Layout**
   - Move predictions card BELOW rankings card in `index.html`
   - Improves page flow: stats → rankings → predictions
   - Users see rankings context before predictions

2. **Sort Predictions by Rating**
   - Sort predictions by highest team rating in matchup
   - Best matchups (highest-rated teams) appear first
   - Formula: `Math.max(home_team_rating, away_team_rating)` descending
   - Keeps compelling #1 vs #5 type games at top

3. **Optional: Add Ranking Indicators** (Story 3)
   - Show team ranking badges in prediction cards
   - Visual context: "Ohio State (#2) vs Michigan (#3)"
   - Requires fetching current rankings data for cross-reference

**How It Integrates:**
- Pure frontend changes, no backend modifications
- Uses existing `home_team_rating` and `away_team_rating` from API
- Maintains all existing prediction card functionality
- No database schema changes required

**Success Criteria:**
- ✅ Predictions appear below rankings on main page
- ✅ Predictions sorted by highest team rating (best games first)
- ✅ Page flow makes logical sense: rankings → predictions
- ✅ No performance degradation (client-side sorting is fast)
- ✅ Mobile responsive layout maintained
- ✅ All existing prediction features work (filtering, refresh, etc.)

## Stories

### Story 1: Reposition Predictions Below Rankings

**Description:** Move the predictions card below the rankings card in the HTML layout to improve page flow and provide ranking context before showing predictions.

**Changes:**
- Reorder HTML structure in `frontend/index.html`
- Move predictions card (lines 61-110) below rankings card (lines 112-167)
- Verify mobile responsive layout still works
- Update any CSS if needed for spacing/padding

**Acceptance Criteria:**
- [ ] Predictions card appears below rankings card
- [ ] Page maintains proper spacing and visual hierarchy
- [ ] Responsive layout works on mobile
- [ ] No visual regressions in existing design

### Story 2: Sort Predictions by Team Rating

**Description:** Sort predictions by the highest team rating in each matchup so the best/most compelling games appear first.

**Changes:**
- Add sorting logic to `loadPredictions()` in `frontend/js/app.js`
- Sort by `Math.max(home_team_rating, away_team_rating)` descending
- Apply sorting before rendering predictions
- Preserve week filter and refresh functionality

**Sorting Logic:**
```javascript
// Sort predictions by highest team rating (best matchups first)
predictions.sort((a, b) => {
  const maxRatingA = Math.max(a.home_team_rating, a.away_team_rating);
  const maxRatingB = Math.max(b.home_team_rating, b.away_team_rating);
  return maxRatingB - maxRatingA; // Descending order
});
```

**Acceptance Criteria:**
- [ ] Predictions sorted by highest team rating
- [ ] Top-ranked matchups appear first in grid
- [ ] Sorting works with week filters
- [ ] Sorting works with refresh functionality
- [ ] No performance issues (sorting is client-side and fast)

### Story 3: Add Ranking Badges to Prediction Cards (Optional Enhancement)

**Description:** Display team rankings in prediction cards to provide visual context for matchup quality (e.g., "#2 Ohio State vs #5 Penn State").

**Changes:**
- Fetch current rankings data when loading predictions
- Cross-reference team names to get current rankings
- Add ranking badges to prediction card display
- Style badges similar to existing rank badges in rankings table

**Display Format:**
```
#2 Ohio State (predicted winner)
@
#5 Penn State
```

**Acceptance Criteria:**
- [ ] Team rankings displayed in prediction cards
- [ ] Rankings update when predictions refresh
- [ ] Unranked teams show no badge or "NR" indicator
- [ ] Visual styling matches existing rank badges
- [ ] Performance impact is minimal (cache rankings data)

## Compatibility Requirements

- [x] Existing APIs remain unchanged (no backend changes)
- [x] Database schema changes are backward compatible (no schema changes)
- [x] UI changes follow existing patterns (uses existing card styles)
- [x] Performance impact is minimal (client-side sorting only)

## Risk Mitigation

**Primary Risk:** Reordering HTML breaks existing mobile responsive layout or JavaScript references

**Mitigation:**
- Test on multiple screen sizes after HTML reordering
- Verify all JavaScript event listeners still work
- Check that IDs and classes are properly referenced
- Incremental changes (Story 1 first, then Story 2)

**Rollback Plan:**
- Revert HTML changes by moving predictions card back above rankings
- Remove sorting logic from `loadPredictions()` function
- Changes are isolated to frontend files only

## Definition of Done

- [x] All stories completed with acceptance criteria met
- [x] Existing functionality verified through testing
  - [ ] Predictions display correctly below rankings
  - [ ] Sorting works for all weeks
  - [ ] Week filters still function properly
  - [ ] Refresh button works
  - [ ] Mobile layout responsive
- [x] Integration points working correctly
  - [ ] HTML layout renders properly
  - [ ] JavaScript sorting logic works
  - [ ] API calls unchanged
  - [ ] CSS styling maintained
- [x] Documentation updated appropriately
  - [ ] README updated with new page layout
  - [ ] Code comments added for sorting logic
- [x] No regression in existing features
  - [ ] All prediction filters work
  - [ ] Prediction cards display correctly
  - [ ] No console errors
  - [ ] Performance unchanged

---

## Story Manager Handoff

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing College Football Ranking System running HTML/CSS/JavaScript frontend with FastAPI backend
- Integration points:
  - `frontend/index.html` - HTML layout structure
  - `frontend/js/app.js` - `loadPredictions()` and `createPredictionCard()` functions
  - Predictions API: `/api/predictions` (no changes needed)
  - Existing CSS in `frontend/css/style.css`
- Existing patterns to follow:
  - Card-based layout (stats card, predictions card, rankings card)
  - Responsive grid system for predictions
  - Existing rank badge styling (`rank-badge` classes)
  - Client-side filtering and state management
- Critical compatibility requirements:
  - No backend API changes
  - No database schema changes
  - Maintain mobile responsive layout
  - Preserve all existing prediction features (filters, refresh)
  - Client-side sorting only (no server changes)
- Each story must include verification that existing functionality remains intact

The epic should maintain system integrity while delivering improved UX with predictions ordered by ranking and positioned below rankings table."

---

## Validation Checklist

**Scope Validation:**
- ✅ Epic can be completed in 1-3 stories maximum (3 stories total, Story 3 optional)
- ✅ No architectural documentation is required (pure frontend changes)
- ✅ Enhancement follows existing patterns (uses existing card layouts and styles)
- ✅ Integration complexity is manageable (client-side JavaScript only)

**Risk Assessment:**
- ✅ Risk to existing system is low (isolated frontend changes)
- ✅ Rollback plan is feasible (revert HTML and remove sorting code)
- ✅ Testing approach covers existing functionality (manual UI testing)
- ✅ Team has sufficient knowledge of integration points (standard HTML/JS)

**Completeness Check:**
- ✅ Epic goal is clear and achievable (better UX through reordering)
- ✅ Stories are properly scoped (incremental changes)
- ✅ Success criteria are measurable (visual positioning, sorting order)
- ✅ Dependencies are identified (none - pure frontend work)

---

## Notes

- This enhancement is purely cosmetic/UX focused
- No backend changes required - predictions API already provides rating data
- Primary benefit: Users see most compelling matchups first
- Secondary benefit: Logical page flow (rankings context before predictions)
- Estimated complexity: Low - simple HTML reordering and array sorting
- Estimated timeline: 1 day for Stories 1-2, optional Story 3 can be deferred
- Story 3 (ranking badges) is optional and can be implemented later if desired
