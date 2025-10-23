# EPIC-009: Prediction Accuracy Tracking & Display - Brownfield Enhancement

## Epic Goal

Enable users to view historical prediction accuracy by storing predictions when games are upcoming, then comparing them to actual results after games complete. Display prediction history on team pages and game pages to demonstrate ELO system performance.

## Epic Overview

**Priority:** Medium
**Estimated Total Effort:** 12-16 hours
**Status:** Ready for Development
**Type:** Feature Enhancement
**Dependencies:** EPIC-007 (Game Predictions), EPIC-008 (Future Game Imports)

---

## Problem Statement

The current prediction system (EPIC-007) generates predictions on-the-fly for upcoming games, but these predictions disappear once games are played. This creates several missed opportunities:

- Users cannot see how accurate the predictions were after games complete
- No way to validate that the ELO system is making good predictions
- Missing transparency about model performance
- Team pages don't show prediction history for completed games
- No aggregate accuracy metrics (e.g., "75% of predictions correct this season")

---

## Epic Description

### Existing System Context

**Current functionality:**
- EPIC-007 provides `/api/predictions` endpoint that generates predictions for future games
- Predictions are calculated using current ELO ratings
- `Game` model has `is_processed` flag to distinguish future vs completed games
- Future games are stored with 0-0 scores (EPIC-008) until they complete
- Team pages display game history with actual results
- Games page shows matchups with actual scores

**Technology stack:**
- Backend: FastAPI with SQLAlchemy ORM
- Database: SQLite with `Game` and `Team` models
- Frontend: Vanilla JavaScript (team.html, games page, index.html)
- Prediction algorithm: ELO-based win probability and score estimation

**Integration points:**
- Database: Need new `Prediction` model to store pre-game predictions
- Game import/update: Store predictions when future games are imported
- API endpoints:
  - `/api/predictions` (existing - no changes needed)
  - `/api/predictions/accuracy` (new - aggregate accuracy stats)
  - `/api/games/{id}/prediction` (new - get prediction for specific game)
- Frontend pages:
  - `team.html` - Show prediction vs actual for each game
  - Game detail pages - Display "We predicted X, actual Y"
  - Rankings page - Show overall prediction accuracy stats

### Enhancement Details

**What's being added/changed:**

1. **Database Schema**
   - New `Prediction` model to store pre-game predictions:
     - game_id (FK to Game)
     - predicted_winner_id (FK to Team)
     - predicted_home_score (Integer)
     - predicted_away_score (Integer)
     - win_probability (Float) - probability for predicted winner
     - home_elo_at_prediction (Float) - snapshot of ratings
     - away_elo_at_prediction (Float)
     - created_at (DateTime) - when prediction was made
     - was_correct (Boolean, nullable) - set after game completes

2. **Prediction Storage Logic**
   - When future games are imported (`import_real_data.py`), generate and store predictions
   - When games are updated with scores (`update_games.py`), evaluate prediction accuracy
   - Set `was_correct` flag based on actual winner vs predicted winner

3. **API Endpoints**
   - `GET /api/predictions/accuracy` - Aggregate accuracy stats
     - Overall accuracy percentage
     - Accuracy by week
     - Accuracy by conference
     - Average win probability when correct/incorrect
   - `GET /api/games/{id}/prediction` - Get stored prediction for specific game
   - `GET /api/teams/{id}/prediction-history` - Get prediction accuracy for team's games

4. **Frontend Display**
   - **Team Page Enhancement:**
     - Add "Prediction" column to game history table
     - Show predicted winner/score vs actual
     - Color code: green = correct, red = incorrect
     - Show win probability that was predicted

   - **Games Page Enhancement:**
     - For completed games, show prediction vs actual
     - "We predicted [Team A] by 7, actual result [Team A] by 10"

   - **Rankings Page Enhancement:**
     - Add "Prediction Accuracy" stat box
     - Show overall % correct
     - Link to detailed accuracy page

**How it integrates:**
- Leverages existing `Game` model (foreign key relationship)
- Uses existing prediction algorithm from EPIC-007
- Integrates with import scripts (`import_real_data.py`, `update_games.py`)
- Extends existing API patterns (same response schema style)
- Frontend builds on existing game display components
- No changes to ELO calculation or existing prediction generation

**Success criteria:**
- Predictions are stored automatically when future games are imported
- Prediction accuracy is calculated automatically when games complete
- Team pages show prediction vs actual for all completed games
- Games page displays prediction history
- Overall accuracy metrics are available via API
- Frontend clearly shows when predictions were correct/incorrect
- System tracks accuracy over time (by week, by conference, etc.)

---

## Stories

### Story 001: Create Prediction Model and Storage Logic

**Description:** Add database schema for storing predictions and implement logic to save predictions when future games are imported.

**Scope:**
- Create `Prediction` model in `models.py`
- Add database migration/schema update
- Modify `import_real_data.py` to generate and store predictions for future games
- Add helper function to create prediction from game and current ELO ratings
- Unit tests for prediction storage

**Acceptance Criteria:**
- `Prediction` table exists in database with all required fields
- When future games are imported, predictions are automatically created and stored
- Predictions capture ELO ratings at time of prediction
- Database constraints prevent duplicate predictions for same game
- Tests verify prediction creation logic

**Estimated Effort:** 4-5 hours

---

### Story 002: Prediction Accuracy Evaluation and API Endpoints

**Description:** Implement logic to evaluate prediction accuracy when games complete, and create API endpoints to retrieve accuracy data.

**Scope:**
- Modify `update_games.py` to evaluate predictions when games get scores
- Set `was_correct` flag on `Prediction` records
- Create `GET /api/predictions/accuracy` endpoint with aggregate stats
- Create `GET /api/games/{id}/prediction` endpoint
- Create `GET /api/teams/{id}/prediction-history` endpoint
- Add `PredictionAccuracy` and related Pydantic schemas
- Integration tests for accuracy calculation and endpoints

**Acceptance Criteria:**
- When game scores are imported, corresponding prediction is evaluated
- `was_correct` flag is set correctly (True if predicted winner matches actual)
- Accuracy API returns overall %, accuracy by week, accuracy by conference
- Game prediction endpoint returns stored prediction with was_correct flag
- Team prediction history endpoint returns all predictions for team's games
- API responses are <500ms for typical queries
- Tests verify accuracy calculation logic

**Estimated Effort:** 5-6 hours

---

### Story 003: Frontend Display of Prediction Accuracy

**Description:** Update frontend pages to display prediction history and accuracy stats alongside actual game results.

**Scope:**
- Update `team.html` to show prediction column in game history table
  - Display predicted winner and score
  - Show win probability
  - Color code correct (green) vs incorrect (red)
- Add prediction vs actual display to games page
- Add "Prediction Accuracy" stat box to rankings page (index.html)
- Update JavaScript API client to fetch prediction data
- Add CSS styles for prediction accuracy display
- Frontend tests for prediction display

**Acceptance Criteria:**
- Team page game table shows prediction vs actual for completed games
- Predictions are clearly distinguished from actual results
- Color coding makes correct/incorrect immediately visible
- Win probability is displayed (e.g., "70% confidence")
- Rankings page shows overall accuracy stats
- Games page shows "We predicted X, actual Y" for completed games
- Mobile responsive design maintained
- No regressions in existing page functionality

**Estimated Effort:** 3-5 hours

---

## Compatibility Requirements

- [x] Existing prediction API (`/api/predictions`) remains unchanged
- [x] No changes to ELO calculation or game processing logic
- [x] Database schema changes are additive only (new table, no modifications)
- [x] Existing frontend pages continue to work (enhancement only)
- [x] Performance impact is minimal (indexed foreign keys)

---

## Risk Mitigation

**Primary Risk:**
Storing predictions for every game could grow database size significantly over multiple seasons.

**Mitigation:**
- Predictions table is relatively small (8-10 fields, mostly integers/floats)
- Index on `game_id` for fast lookups
- Can add data retention policy later if needed (e.g., keep only current season + last 2 years)
- Estimate: 500 games/season × 8 bytes/field × 10 fields = ~40KB per season (negligible)

**Secondary Risk:**
Predictions stored at import time may become stale if ELO ratings change significantly before game is played.

**Mitigation:**
- This is actually a feature - shows what prediction was at time of import
- If needed, can add logic to update predictions when ELO changes significantly
- For MVP, store once at import time (simpler, more transparent)

**Rollback Plan:**
1. Remove prediction display from frontend (revert JS/HTML changes)
2. Remove new API endpoints (comment out routes)
3. Drop `Prediction` table from database
4. Revert import script changes
5. System returns to EPIC-007 state (on-the-fly predictions only)

---

## Definition of Done

- [x] All three stories completed with acceptance criteria met
- [x] `Prediction` model integrated into database schema
- [x] Predictions automatically stored when future games are imported
- [x] Predictions automatically evaluated when games complete
- [x] API endpoints provide prediction accuracy data
- [x] Team pages show prediction vs actual for completed games
- [x] Rankings page displays overall accuracy stats
- [x] All tests pass (unit, integration, frontend)
- [x] Documentation updated (API docs, schema docs)
- [x] No regression in existing game/prediction functionality
- [x] Performance benchmarks met (<500ms API response)

---

## Technical Notes

**Database Considerations:**
- Foreign key on `game_id` (indexed for performance)
- Foreign key on `predicted_winner_id` (references `Team`)
- Unique constraint on `game_id` to prevent duplicate predictions
- `was_correct` nullable initially (set after game completes)
- Consider composite index on `(game_id, was_correct)` for accuracy queries

**API Response Schema Example:**
```json
{
  "overall_accuracy": 0.73,
  "total_predictions": 127,
  "correct_predictions": 93,
  "by_week": [
    {"week": 1, "accuracy": 0.71, "total": 15},
    {"week": 2, "accuracy": 0.75, "total": 18}
  ],
  "by_conference": [
    {"conference": "P5", "accuracy": 0.77, "total": 85},
    {"conference": "G5", "accuracy": 0.65, "total": 42}
  ]
}
```

**Frontend Display Example:**
```
Team Game History:
Week  Opponent      Prediction        Actual        Result
----  ----------   ---------------  -----------   --------
1     Alabama      Loss (45% win)    W 24-21      ✓ Wrong
2     Georgia      Win (65% win)     W 31-28      ✓ Correct
3     Tennessee    Win (58% win)     L 21-35      ✗ Wrong
```

---

## Related Work

**Depends On:**
- EPIC-007: Game Predictions - Provides prediction algorithm
- EPIC-008: Future Game Imports - Provides future games to predict

**Future Enhancements:**
- EPIC-010 (potential): Advanced accuracy analytics (by team strength, by margin, etc.)
- EPIC-011 (potential): User-facing "prediction confidence" indicators
- EPIC-012 (potential): Compare ELO predictions to other prediction models

**Related Documentation:**
- `docs/EPIC-007-GAME-PREDICTIONS.md` - Current prediction implementation
- `docs/EPIC-008-STORY-001.md` - Future game import logic
- `models.py` - Current database schema
- `ranking_service.py` - ELO calculation and prediction algorithm
