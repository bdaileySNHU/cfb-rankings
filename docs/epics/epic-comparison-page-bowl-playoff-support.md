# Epic: Prediction Comparison Page - Bowl Season & Playoff Support - Brownfield Enhancement

**Epic ID**: EPIC-COMPARISON-BOWL-PLAYOFF
**Type**: Brownfield Enhancement
**Status**: ✅ **READY FOR DEVELOPMENT** (Created: 2026-01-12 | Approved: 2026-01-13)
**Priority**: Medium
**Complexity**: Low

---

## Epic Goal

Enhance the prediction comparison page to properly display and analyze ELO vs AP Poll accuracy for bowl games and playoff games, providing users with complete postseason prediction insights.

---

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Prediction comparison page displays ELO system accuracy vs AP Poll predictions
- Comparison data shows overall accuracy, weekly breakdown, and disagreement analysis
- Page includes interactive chart showing accuracy trends over time by week
- Season selector allows viewing different seasons
- Backend API endpoint `/api/predictions/comparison` calculates comparison statistics

**Technology stack:**
- Frontend: HTML/JavaScript with Chart.js for visualization
- Backend: Python FastAPI with SQLAlchemy ORM
- Database: SQLite with games, predictions, and AP poll rankings tables
- Existing API: `src/core/ap_poll_service.py` (calculate_comparison_stats)

**Integration points:**
- `frontend/comparison.html` - Main comparison page UI
- `frontend/js/comparison.js` - Frontend logic and chart rendering
- `src/api/main.py` - API endpoint `/api/predictions/comparison`
- `src/core/ap_poll_service.py` - Comparison calculation logic
- Database: Games with postseason_name field (weeks 16-20 for bowls/playoffs)

### Enhancement Details

**Current Issue:**

Based on recent system updates supporting playoff weeks 16-20:
- The prediction comparison page currently focuses on regular season games (weeks 1-15)
- Bowl games and playoff games (weeks 16-20) may not display properly in the weekly breakdown
- The "Accuracy Over Time" chart shows "Week X" labels that don't distinguish bowl/playoff games
- Users cannot easily see how ELO vs AP Poll performed specifically for postseason games
- Postseason games are high-visibility matchups where prediction accuracy is particularly interesting

**What's being added/changed:**

1. **Postseason Week Display**
   - Update weekly breakdown to include weeks 16-20 (bowl/playoff weeks)
   - Display postseason games in the "Accuracy Over Time" chart
   - Add appropriate labels for postseason weeks (e.g., "Bowl Week 1", "CFP Quarterfinals")

2. **Postseason-Specific Statistics**
   - Add summary stats for postseason games separately from regular season
   - Show "Regular Season Accuracy" vs "Postseason Accuracy" comparison
   - Highlight bowl game vs playoff game prediction performance

3. **Enhanced Chart Visualization**
   - Update chart labels to distinguish regular season from postseason weeks
   - Consider visual separation (e.g., vertical line after Week 15)
   - Add chart legend clarification for postseason games

**How it integrates:**
- Uses existing comparison calculation logic (`calculate_comparison_stats`)
- Extends frontend JavaScript to handle postseason week labels
- Maintains backward compatibility with regular season functionality
- Follows existing Chart.js visualization patterns

**Success criteria:**
- Comparison page displays bowl game and playoff game accuracy (weeks 16-20)
- Weekly breakdown chart includes postseason weeks with clear labels
- Users can see distinct statistics for regular season vs postseason performance
- No regression in regular season comparison functionality
- Postseason games appear in disagreement table with appropriate week labels

---

## Stories

### Story 1: Backend API Enhancement for Postseason Comparison

**Description:** Update the prediction comparison API endpoint to include postseason games (weeks 16-20) in the weekly breakdown and add postseason-specific statistics.

**Scope:**
- Modify `calculate_comparison_stats` in `src/core/ap_poll_service.py` to include weeks 16-20
- Add postseason summary statistics (regular season vs postseason accuracy)
- Include game_type and postseason_name in weekly breakdown for frontend labeling
- Ensure backward compatibility with existing API response structure
- Add unit tests for postseason comparison calculations

**Acceptance Criteria:**
- API endpoint returns comparison data for weeks 1-20 (not just 1-15)
- Weekly breakdown (by_week) includes postseason weeks with game type metadata
- Response includes new fields: `regular_season_accuracy`, `postseason_accuracy`
- No breaking changes to existing API response structure
- Postseason games with AP poll rankings are included in comparison
- Unit tests verify postseason calculations are correct

---

### Story 2: Frontend Chart Enhancement for Postseason Visualization

**Description:** Update the comparison page chart to properly display postseason weeks with clear labels and visual distinction from regular season.

**Scope:**
- Modify `frontend/js/comparison.js` to handle weeks 16-20 in chart data
- Update chart labels to show descriptive postseason week names:
  - Week 16: "Bowl Week 1" or specific bowl round
  - Week 17-18: "CFP Quarterfinals", "CFP Semifinals"
  - Week 19-20: "Conference Championships", "CFP Championship"
- Add visual separator in chart after Week 15 (optional, based on Chart.js capabilities)
- Ensure chart scales and tooltips work correctly with postseason data
- Update chart legend or subtitle to indicate postseason inclusion

**Acceptance Criteria:**
- Chart displays all weeks 1-20 with appropriate labels
- Postseason weeks have descriptive labels (not just "Week 16", "Week 17")
- Chart remains readable and not overly crowded
- Tooltips show correct week information for postseason games
- Visual distinction between regular season and postseason is clear
- Chart responsiveness maintained on mobile devices

---

### Story 3: Postseason Statistics Summary Display

**Description:** Add a postseason summary section to the comparison page showing regular season vs postseason accuracy comparison.

**Scope:**
- Add new UI section to `frontend/comparison.html` for postseason statistics
- Display "Regular Season Accuracy" vs "Postseason Accuracy" comparison cards
- Show breakdown of bowl game accuracy vs playoff game accuracy (if distinguishable)
- Update disagreement table to show postseason games with appropriate week labels
- Ensure responsive design for summary section
- Handle empty state when postseason data not yet available

**Acceptance Criteria:**
- New section displays postseason accuracy for both ELO and AP Poll
- Regular season vs postseason comparison is clearly presented
- Disagreement table shows postseason games with descriptive week labels
- Empty state message appears when postseason games haven't occurred yet
- UI design is consistent with existing comparison page style
- Postseason section appears below or alongside existing overall statistics

---

## Compatibility Requirements

- [x] Existing comparison API endpoint structure remains unchanged (additive only)
- [x] Regular season comparison functionality continues working unchanged
- [x] Chart.js library version remains compatible (no breaking upgrades required)
- [x] Season selector functionality unaffected
- [x] Mobile responsive design maintained

---

## Risk Mitigation

**Primary Risks:**

1. **Empty Postseason Data:** Current or historical seasons may not have AP poll rankings for postseason
   - **Mitigation:** Add empty state handling; display message "Postseason data not available"
   - **Rollback:** Remove postseason sections if API returns empty data

2. **Chart Readability:** Adding weeks 16-20 might make chart crowded or hard to read
   - **Mitigation:** Test with real data; adjust chart height or font size as needed
   - **Rollback:** Revert to weeks 1-15 display; add "View Postseason" toggle

3. **API Response Size:** Including more weeks might increase API response size
   - **Mitigation:** Monitor response size; postseason adds minimal data (5 weeks max)
   - **Rollback:** Make postseason data optional via query parameter

**Rollback Plan:**
```bash
# Revert frontend changes
git checkout frontend/comparison.html frontend/js/comparison.js

# Revert backend changes
git checkout src/core/ap_poll_service.py

# Or revert entire epic
git revert <commit-hash-range>
```

---

## Definition of Done

- [ ] API endpoint includes postseason games (weeks 16-20) in comparison data
- [ ] Chart displays postseason weeks with descriptive labels
- [ ] Postseason summary statistics display on frontend
- [ ] Disagreement table shows postseason games with appropriate labels
- [ ] No regression in regular season comparison functionality
- [ ] Empty state handling for seasons without postseason data
- [ ] Unit tests for postseason comparison calculations
- [ ] E2E tests updated to verify postseason display
- [ ] Documentation updated (if needed)
- [ ] Changes committed with clear messages
- [ ] Manual verification: browse to comparison page and view postseason data

---

## Validation Checklist

### Scope Validation

- [x] Epic can be completed in 3 stories maximum
- [x] No architectural documentation required (extends existing patterns)
- [x] Enhancement follows existing comparison page patterns
- [x] Integration complexity is manageable (existing API and frontend structure)

### Risk Assessment

- [x] Risk to existing system is low (additive changes to comparison page)
- [x] Rollback plan is feasible (git revert changes)
- [x] Testing approach covers existing functionality (verify regular season unaffected)
- [x] Team has knowledge of integration points (comparison page, Chart.js)

### Completeness Check

- [x] Epic goal is clear and achievable (add postseason support to comparison page)
- [x] Stories are properly scoped (backend, frontend chart, frontend stats)
- [x] Success criteria are measurable (postseason weeks display in chart)
- [x] Dependencies are identified (existing comparison API, Chart.js)

---

## Technical Notes

### Postseason Week Structure

Based on existing game data:
- **Week 16-17:** Bowl games (various bowl games across multiple days)
- **Week 16:** CFP First Round
- **Week 17-18:** CFP Quarterfinals
- **Week 18:** CFP Semifinals
- **Week 19:** Conference Championship games (may vary)
- **Week 20:** CFP National Championship

### Week Label Mapping

Frontend should map week numbers to descriptive labels:
```javascript
function getWeekLabel(week, gameType, postseasonName) {
  if (week <= 15) return `Week ${week}`;

  // Use postseason_name if available, otherwise generic label
  if (postseasonName) {
    // Extract abbreviated name: "CFP Semifinal" → "CFP Semi"
    return postseasonName.replace("College Football Playoff", "CFP");
  }

  // Fallback generic labels
  const postseasonLabels = {
    16: "Bowl Week 1",
    17: "Bowl Week 2",
    18: "CFP Semifinals",
    19: "Conf. Championships",
    20: "CFP Championship"
  };

  return postseasonLabels[week] || `Week ${week}`;
}
```

### API Response Enhancement

Add to existing `/api/predictions/comparison` response:
```json
{
  "season": 2025,
  "elo_accuracy": 0.724,
  "ap_accuracy": 0.698,
  "regular_season_elo_accuracy": 0.720,
  "regular_season_ap_accuracy": 0.695,
  "postseason_elo_accuracy": 0.750,
  "postseason_ap_accuracy": 0.720,
  "by_week": [
    {
      "week": 16,
      "game_type": "bowl",
      "postseason_label": "Bowl Games",
      "elo_accuracy": 0.75,
      "ap_accuracy": 0.70,
      "games_compared": 8
    }
  ]
}
```

### Files Likely to Modify

- `src/core/ap_poll_service.py` - Add postseason calculation logic
- `src/api/main.py` - Update API response (if schema changes needed)
- `frontend/js/comparison.js` - Chart rendering with postseason weeks
- `frontend/comparison.html` - Postseason statistics UI section
- `tests/unit/test_ap_comparison.py` - Unit tests for postseason logic
- `tests/e2e/test_comparison_page.py` - E2E tests for postseason display

---

## Dependencies

**No blocking dependencies:**
- All work uses existing comparison infrastructure
- No external system changes required
- No database migration required (postseason data already exists)

**Builds on:**
- Existing prediction comparison system (EPIC-010)
- Playoff game import (weeks 16-20 support added in recent commits)
- AP Poll ranking integration

**Enables:**
- Complete season prediction accuracy analysis
- Postseason prediction insights for users
- Better understanding of ELO vs AP Poll performance across all game types

---

## Success Metrics

### Before Epic
- **Weeks Displayed:** 1-15 (regular season only)
- **Postseason Visibility:** Not included or unclear in comparison
- **User Insight:** Limited to regular season prediction accuracy

### After Epic (Target)
- **Weeks Displayed:** 1-20 (complete season including postseason)
- **Postseason Visibility:** Clear breakdown and dedicated statistics
- **User Insight:** Full season prediction accuracy including high-profile bowl/playoff games
- **System Integrity:** No regression in regular season comparison functionality

---

## Developer Handoff

**Status:** ✅ Ready for development - all stories defined and approved

**Quick Start:**
- This is an enhancement to the existing prediction comparison page
- Work flow: Story 1 (Backend) → Story 2 (Chart) → Story 3 (Stats UI)
- All integration points, file paths, and code examples documented above
- Estimated effort: 6-9 hours total (2-3 hours per story)

**Key Reminders:**
- Maintain backward compatibility - no breaking changes to API
- Verify regular season comparison continues working after each story
- Follow existing patterns in `ap_poll_service.py` and Chart.js visualization
- Test empty state handling for seasons without postseason data

---

## Notes

- **Related Work:**
  - Builds on playoff import work (recent commits added weeks 16-20 support)
  - May inform future work on game-type-specific analysis
- **Impact:** Provides complete season prediction analysis for users
- **Effort:** Low - extends existing patterns with additive changes
- **Risk:** Low - isolated to comparison page, additive only
- **Priority:** Medium - enhances existing feature, not critical but valuable
- **User Value:** Users interested in postseason prediction accuracy gain complete insights

---

## Acceptance Testing

**Manual Verification Steps:**

After all stories complete:

1. **Verify API Returns Postseason Data:**
   ```bash
   # Test API endpoint includes weeks 16-20
   curl "http://localhost:8000/api/predictions/comparison?season=2025" | jq '.by_week | map(.week)'

   # Expected: Array includes weeks 16-20 (if postseason games exist)
   ```

2. **Verify Chart Displays Postseason:**
   - Navigate to comparison page
   - Select season with postseason games
   - Verify chart shows weeks beyond 15
   - Verify postseason weeks have descriptive labels (not just "Week 16")

3. **Verify Postseason Statistics:**
   - Check postseason summary section appears
   - Verify regular season vs postseason accuracy displayed
   - Confirm disagreement table includes postseason games

4. **Verify No Regression:**
   - Select season with only regular season games (e.g., in-progress season)
   - Verify page works correctly without postseason data
   - Verify empty state message for postseason appears appropriately

5. **Test Responsiveness:**
   - View comparison page on mobile device or narrow browser window
   - Verify chart and postseason statistics remain readable
   - Confirm no layout issues with additional data

---

## Conclusion

This epic enhances the prediction comparison page to provide complete season analysis including bowl games and playoffs. The focused scope (3 stories, additive changes only) allows for straightforward implementation while maintaining system integrity. Success will give users valuable insights into ELO vs AP Poll performance across all game types, including high-profile postseason matchups.

**Estimated Effort:**
- Story 1: 2-3 hours (backend API enhancement + tests)
- Story 2: 2-3 hours (chart visualization updates)
- Story 3: 2-3 hours (postseason statistics UI)
- **Total: 6-9 hours (2-3 development sessions)**

**Impact:**
- Complete season prediction accuracy analysis
- Enhanced user insights for postseason games
- No regression in existing functionality
- Improved system completeness and value
