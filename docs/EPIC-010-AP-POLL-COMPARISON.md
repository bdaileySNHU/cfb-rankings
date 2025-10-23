# EPIC-010: AP Poll Prediction Comparison - Brownfield Enhancement

## Epic Goal

Compare ELO prediction accuracy against AP Poll "predictions" (where higher-ranked team is predicted to win) to validate that the ELO system provides superior predictive performance over simple ranking-based predictions.

## Epic Overview

**Priority:** Medium-High
**Estimated Total Effort:** 10-14 hours
**Status:** Ready for Development
**Type:** Feature Enhancement + Validation
**Dependencies:**
- EPIC-009 (Prediction Accuracy Tracking)
- CFBD API rankings endpoint

---

## Problem Statement

While the ELO system generates predictions based on mathematical models, there's no benchmark to validate its performance against traditional ranking systems. The AP Poll is widely recognized and provides an implicit prediction mechanism: "the higher-ranked team should win." Without a comparison:

- Users cannot assess whether ELO predictions are better than simple rankings
- No evidence that complexity of ELO system adds value over simpler approaches
- Missing compelling validation of the system's predictive power
- No competitive edge demonstrated in prediction accuracy

This epic creates a benchmark comparison that demonstrates the ELO system's superior predictive accuracy.

---

## Epic Description

### Existing System Context

**Current functionality:**
- ELO predictions stored in database (EPIC-009)
- Prediction accuracy tracked and calculated (EPIC-009)
- CFBD API provides weekly AP Poll rankings
- `cfbd_client.py` handles API calls
- API endpoints expose prediction accuracy stats

**Technology stack:**
- Backend: FastAPI with SQLAlchemy ORM
- Database: SQLite with `Prediction`, `Game`, `Team` models
- CFBD API: `/rankings` endpoint provides AP Poll data
- Frontend: Vanilla JavaScript with charts/tables

**Integration points:**
- CFBD API: Add `get_ap_poll()` method to fetch weekly AP Top 25
- Database: New `APPollRanking` model to store historical poll data
- Prediction evaluation: Compare AP implied predictions with actual results
- API endpoints: New `/api/predictions/comparison` endpoint
- Frontend: Comparison dashboard showing ELO vs AP accuracy

### Enhancement Details

**What's being added/changed:**

1. **AP Poll Data Collection**
   - New `APPollRanking` model to store weekly AP Poll rankings
   - CFBD client method to fetch AP Poll data
   - Import logic to store AP rankings when importing game data
   - Historical poll data for completed weeks

2. **AP "Prediction" Calculation**
   - For each game, determine AP-implied prediction:
     - If Team A ranked #5 vs Team B ranked #12 → predict Team A wins
     - If Team A ranked vs Team B unranked → predict Team A wins
     - If both unranked → no AP prediction (skip from comparison)
     - If rankings equal → no prediction (edge case, very rare)
   - Store AP predictions alongside ELO predictions

3. **Comparison Analytics**
   - Calculate accuracy for both systems:
     - ELO accuracy: % of ELO predictions that were correct
     - AP accuracy: % of AP-implied predictions that were correct
   - Break down by:
     - Overall season accuracy
     - Accuracy by week
     - Accuracy by conference
     - Accuracy when both ranked vs one ranked vs both unranked
     - Accuracy by ranking gap (e.g., #1 vs #25 easier than #10 vs #12)

4. **API Endpoints**
   - `GET /api/predictions/comparison` - Side-by-side comparison stats
   - `GET /api/predictions/comparison/games` - Game-by-game breakdown
   - Response includes: ELO accuracy, AP accuracy, advantage metrics

5. **Frontend Comparison Dashboard**
   - New comparison page or section on rankings page
   - Side-by-side accuracy display: "ELO: 73% vs AP: 68%"
   - Charts showing accuracy over time (by week)
   - Table of games where systems disagreed
   - Highlight games where ELO was correct and AP was wrong
   - Breakdown showing where ELO excels (e.g., G5 teams, ranking gaps)

**How it integrates:**
- Extends EPIC-009 prediction tracking system
- Uses existing CFBD API client patterns
- Follows existing database model conventions
- Builds on existing prediction accuracy calculations
- Frontend adds new page/section without modifying existing pages
- No changes to ELO calculation or game processing

**Success criteria:**
- AP Poll rankings automatically stored for each week
- AP-implied predictions calculated for ranked matchups
- Comparison API returns accurate side-by-side stats
- Frontend displays clear, compelling comparison showing ELO advantage
- System tracks both accuracies over time
- Comparison updates automatically as new games complete
- Performance: Comparison calculations <1 second for full season

---

## Stories

### Story 001: AP Poll Data Collection and Storage

**Description:** Add database model for AP Poll rankings, implement CFBD client method to fetch poll data, and integrate into import workflow.

**Scope:**
- Create `APPollRanking` model in `models.py`
  - Fields: id, season, week, poll_type, rank, team_id, first_place_votes, points
- Add `get_ap_poll(year, week)` method to `cfbd_client.py`
- Modify `import_real_data.py` to fetch and store AP rankings
- Add helper to find team's AP rank for given week
- Database migration for new table
- Unit tests for AP poll fetching and storage

**Acceptance Criteria:**
- `APPollRanking` table exists with proper foreign keys and indexes
- CFBD client can fetch AP Poll for any week/season
- When importing game data, AP rankings are automatically fetched and stored
- Helper function returns team's rank for given week (or None if unranked)
- Duplicate rankings prevented (unique constraint on season/week/team)
- Tests verify AP poll fetch and storage logic

**Estimated Effort:** 4-5 hours

---

### Story 002: AP Prediction Calculation and Comparison Analytics

**Description:** Implement logic to calculate AP-implied predictions, compare against actual results, and generate comparison statistics.

**Scope:**
- Add `get_ap_prediction_for_game()` function
  - Compare team rankings to determine predicted winner
  - Handle unranked teams
  - Return predicted winner or None if no prediction possible
- Modify prediction evaluation to track AP predictions alongside ELO
- Add `calculate_comparison_stats()` function
  - Overall accuracy for each system
  - Accuracy by week, conference, ranking scenarios
  - Games where systems disagreed
  - Highlight where ELO outperformed
- Create comparison API endpoint: `GET /api/predictions/comparison`
- Add `ComparisonStats` Pydantic schema
- Unit and integration tests for comparison logic

**Acceptance Criteria:**
- AP predictions correctly calculated based on rankings
- Unranked matchups handled appropriately (skipped from comparison)
- Comparison stats accurately calculate both accuracies
- API endpoint returns comprehensive comparison data
- Response includes: overall%, by week, by conference, disagreements
- Statistics update automatically when new games complete
- Tests verify AP prediction logic and accuracy calculations

**Estimated Effort:** 4-5 hours

---

### Story 003: Frontend Comparison Dashboard

**Description:** Create frontend display to showcase ELO vs AP Poll prediction accuracy comparison with charts and tables.

**Scope:**
- Create new comparison section on rankings page or dedicated page
- **Hero Stats Display:**
  - Large display: "ELO: 73% | AP Poll: 68%"
  - Highlight ELO advantage: "+5% more accurate"
- **Accuracy Over Time Chart:**
  - Line chart showing both accuracies by week
  - Visual highlighting when ELO outperforms
- **Breakdown Tables:**
  - Accuracy by conference
  - Accuracy by ranking scenarios (both ranked, one ranked, etc.)
  - Accuracy by ranking gap
- **Disagreement Table:**
  - Games where ELO and AP predicted differently
  - Show which system was correct
  - Highlight ELO wins in green
- Add JavaScript API client methods for comparison endpoints
- Add CSS styling for comparison display
- Responsive design for mobile

**Acceptance Criteria:**
- Comparison page/section clearly displays both accuracies
- Visual design emphasizes ELO advantage (when applicable)
- Charts show accuracy trends over time
- Tables provide detailed breakdowns
- Disagreement cases are easy to identify
- Page updates automatically when data changes
- Mobile responsive
- No regressions in existing pages

**Estimated Effort:** 2-4 hours

---

## Compatibility Requirements

- [x] Existing prediction functionality unchanged (EPIC-009)
- [x] No modifications to ELO calculation
- [x] Database changes are additive only (new table)
- [x] Existing API endpoints continue working
- [x] Frontend additions don't break existing pages
- [x] Performance impact minimal (indexed queries)

---

## Risk Mitigation

**Primary Risk:**
AP Poll data not available for all weeks (e.g., preseason, off-weeks, late season).

**Mitigation:**
- Check poll availability before attempting to fetch
- Gracefully handle weeks without polls
- Comparison only includes weeks where poll exists
- Document which weeks are included in comparison
- Consider using Coaches Poll as fallback if AP unavailable

**Secondary Risk:**
Comparison may show ELO performs worse than AP Poll in some scenarios (negative result).

**Mitigation:**
- This is actually valuable insight! Shows where ELO can improve
- Transparently display results regardless of outcome
- Break down by different scenarios to find where each excels
- Use findings to refine ELO parameters if needed
- Market as "honest validation" - builds credibility

**Tertiary Risk:**
CFBD API rate limits when fetching historical AP Poll data.

**Mitigation:**
- Fetch polls incrementally during normal imports (not bulk backfill)
- Cache poll data in database (don't re-fetch each time)
- Add rate limit delays if needed (existing API tracking helps)
- Start with current season only, backfill historical data gradually

**Rollback Plan:**
1. Remove comparison display from frontend
2. Remove comparison API endpoints
3. Stop fetching AP Poll data in imports
4. Keep `APPollRanking` table (data useful for future enhancements)
5. System returns to EPIC-009 state (ELO-only accuracy tracking)

---

## Definition of Done

- [x] All three stories completed with acceptance criteria met
- [x] `APPollRanking` model integrated into database
- [x] AP Poll rankings automatically fetched and stored
- [x] AP-implied predictions calculated correctly
- [x] Comparison statistics accurate and comprehensive
- [x] API endpoint provides comparison data
- [x] Frontend displays compelling comparison visualization
- [x] All tests pass (unit, integration, frontend)
- [x] Documentation updated (API docs, model docs)
- [x] No regression in existing functionality
- [x] Performance benchmarks met (<1s comparison calculation)

---

## Technical Notes

**AP Poll Prediction Logic:**

```python
def get_ap_prediction_for_game(game: Game, week: int) -> Optional[int]:
    """
    Determine AP-implied prediction for a game.

    Returns:
        team_id of predicted winner, or None if no prediction
    """
    home_rank = get_team_ap_rank(game.home_team_id, game.season, week)
    away_rank = get_team_ap_rank(game.away_team_id, game.season, week)

    # Both unranked - no prediction
    if home_rank is None and away_rank is None:
        return None

    # One team unranked - predict ranked team
    if home_rank is None:
        return game.away_team_id
    if away_rank is None:
        return game.home_team_id

    # Both ranked - lower number = higher rank = predicted winner
    if home_rank < away_rank:
        return game.home_team_id
    elif away_rank < home_rank:
        return game.away_team_id
    else:
        # Equal rankings (very rare) - no prediction
        return None
```

**Database Schema:**

```sql
CREATE TABLE ap_poll_rankings (
    id INTEGER PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    poll_type VARCHAR(50) DEFAULT 'AP Top 25',
    rank INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    first_place_votes INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    UNIQUE(season, week, team_id)
);

CREATE INDEX idx_ap_season_week ON ap_poll_rankings(season, week);
CREATE INDEX idx_ap_team_season ON ap_poll_rankings(team_id, season);
```

**API Response Example:**

```json
{
  "season": 2024,
  "elo_accuracy": 0.73,
  "ap_accuracy": 0.68,
  "elo_advantage": 0.05,
  "total_games_compared": 127,
  "elo_correct": 93,
  "ap_correct": 86,
  "both_correct": 79,
  "elo_only_correct": 14,
  "ap_only_correct": 7,
  "both_wrong": 27,
  "by_week": [
    {
      "week": 1,
      "elo_accuracy": 0.71,
      "ap_accuracy": 0.67,
      "games": 15
    }
  ],
  "disagreements": [
    {
      "game_id": 127,
      "week": 5,
      "matchup": "Georgia vs Tennessee",
      "elo_predicted": "Georgia",
      "ap_predicted": "Tennessee",
      "actual_winner": "Georgia",
      "elo_correct": true,
      "ap_correct": false
    }
  ]
}
```

---

## Expected Results

Based on typical ELO performance vs ranking-based predictions:

- **Expected ELO Advantage:** 5-10% better accuracy
- **Best ELO Performance:** G5 games, unranked matchups, close rankings
- **AP Poll Strengths:** Top 10 matchups (where rankings are highly accurate)
- **Key Insight:** ELO should excel when rankings lag behind actual team strength

**Marketing Value:**
- "Our ELO system is 7% more accurate than AP Poll predictions"
- "In 14 games where systems disagreed, ELO was right 12 times"
- Builds credibility and demonstrates system sophistication

---

## Related Work

**Depends On:**
- EPIC-009: Prediction Accuracy Tracking - Provides ELO prediction storage
- EPIC-007: Game Predictions - Provides prediction algorithm
- CFBD API: Rankings endpoint for AP Poll data

**Enables:**
- EPIC-011 (potential): Coaches Poll comparison
- EPIC-012 (potential): FPI/SP+ comparison (if data available)
- EPIC-013 (potential): Ensemble predictions combining multiple models

**Related Documentation:**
- `docs/EPIC-009-PREDICTION-ACCURACY-TRACKING.md` - ELO prediction tracking
- `docs/EPIC-007-GAME-PREDICTIONS.md` - Prediction algorithm
- `cfbd_client.py` - CFBD API integration
- `ranking_service.py` - ELO calculation

---

## Success Metrics

**Quantitative:**
- Comparison calculation completes in <1 second
- API response time <500ms
- Frontend page load time <2 seconds
- All historical weeks with AP Poll data successfully imported

**Qualitative:**
- Comparison clearly demonstrates ELO system value (or reveals areas to improve)
- Frontend design is compelling and easy to understand
- Users can quickly grasp which system performs better
- Data presentation builds confidence in ELO system

**Validation:**
- Comparison results match manual calculations
- Edge cases handled correctly (unranked, missing data)
- System accurately identifies games where ELO outperforms AP
