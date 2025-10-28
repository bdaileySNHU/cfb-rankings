# EPIC-017 Story 001: Create Retrospective Prediction Generation Script

**Epic:** EPIC-017 - Retrospective Prediction Generation
**Story Points:** 5
**Priority:** High
**Status:** ✅ Complete
**Completion Date:** 2025-10-27

---

## User Story

As a **system administrator**,
I want **to generate predictions for past games using historical ELO ratings**,
So that **the Prediction Comparison feature can display historically accurate prediction data and show how well the ranking algorithm would have predicted game outcomes**.

---

## Story Context

### Existing System Integration

- **Integrates with:**
  - `ranking_service.py`: prediction generation functions
  - `models.py`: Prediction, Game, Team, RankingHistory models
  - `database.py`: SQLAlchemy session management

- **Technology:** Python 3, SQLAlchemy ORM, SQLite

- **Follows pattern:**
  - Script structure matches `scripts/generate_predictions.py`
  - Logging format matches `scripts/weekly_update.py`
  - Database session management pattern from existing scripts

- **Touch points:**
  - `RankingHistory` table for historical ELO ratings
  - `predictions` table for writing prediction records
  - `games` table for querying completed games
  - Reuses `_calculate_game_prediction()` function from `ranking_service.py`

---

## Acceptance Criteria

### Functional Requirements

1. **Script queries all processed games without predictions**
   - Query: `SELECT * FROM games WHERE is_processed = True AND id NOT IN (SELECT game_id FROM predictions)`
   - Processes games in chronological order (season, week, game_id)
   - Handles multiple seasons if present

2. **Script retrieves historical ELO ratings correctly**
   - For each game at week N, retrieves ratings from week N-1
   - For Week 1 games, uses week 0 (preseason) ratings
   - If week 0 ratings don't exist, uses default ELO of 1500
   - Logs warning when using default ratings

3. **Script generates predictions using correct algorithm**
   - Reuses existing `_calculate_game_prediction()` from `ranking_service.py`
   - Passes historical ratings (not current ratings)
   - Calculates win probability, predicted scores, predicted winner
   - Stores ratings used in prediction (`home_elo_at_prediction`, `away_elo_at_prediction`)

4. **Script saves predictions with appropriate timestamps**
   - Sets `created_at` to 2 days before `game_date` (simulates pre-game prediction)
   - If game_date is null, uses reasonable approximation based on season/week
   - All predictions for a game saved in single transaction

5. **Script provides comprehensive logging and progress tracking**
   - Logs start time, season being processed, total games found
   - Progress indicator: "Week N: Processing X games..."
   - Per-week summary: predictions created, skipped, errors
   - Final summary: total games, predictions created, duration
   - Warning logs for missing data or anomalies

### Integration Requirements

6. **Existing prediction generation (`generate_predictions()`) continues to work unchanged**
   - Script does not modify `ranking_service.py`
   - Script does not interfere with future prediction generation
   - Uses read-only access to `RankingHistory` table

7. **New predictions follow existing Prediction model schema exactly**
   - All required fields populated: `game_id`, `predicted_winner_id`, `predicted_home_score`, `predicted_away_score`, `win_probability`, `home_elo_at_prediction`, `away_elo_at_prediction`, `created_at`
   - Field `was_correct` set to `None` (will be calculated later)
   - No schema modifications required

8. **Integration with RankingHistory table maintains current behavior**
   - Read-only queries to `RankingHistory`
   - No modifications to existing historical ratings
   - Query uses indexes appropriately: `WHERE team_id = ? AND season = ? AND week = ?`

### Quality Requirements

9. **Change is covered by appropriate tests**
   - Unit tests for rating lookup logic
   - Unit tests for Week 1 edge case handling
   - Integration test with sample historical data
   - Validation that predictions match expected format

10. **Documentation is updated**
    - Script includes comprehensive docstring
    - Function-level documentation for all helpers
    - README or docs/ updated with script description
    - Usage examples included

11. **No regression in existing functionality verified**
    - Existing `generate_predictions()` tests still pass
    - Existing Prediction Comparison page displays backfilled predictions
    - Database queries remain performant

---

## Technical Notes

### Integration Approach

**Script Flow:**
```
1. Initialize database session
2. Query current season(s) from database
3. For each season:
   a. Query all processed games without predictions
   b. Sort by week, then game_id
   c. For each game:
      - Determine prediction week (max(0, game.week - 1))
      - Query home team rating from RankingHistory
      - Query away team rating from RankingHistory
      - If either missing, use default 1500 and log warning
      - Call _calculate_game_prediction() with historical ratings
      - Create Prediction object with game context
      - Set created_at timestamp
      - Add to session
   d. Commit all predictions for the week
   e. Log week summary
4. Log final summary
5. Close database session
```

### Existing Pattern Reference

**Follow pattern from `scripts/generate_predictions.py`:**
- Import structure: `from database import SessionLocal`
- Session management: try/finally with db.close()
- Prediction creation: same field mapping
- Logging: use logging module with INFO level

**Follow pattern from `scripts/weekly_update.py`:**
- Progress logging with separators (`"=" * 80`)
- Summary statistics at end
- Error handling with try/except and logging

### Key Constraints

- **Historical Rating Requirement:** Must use ratings from week BEFORE game, not current ratings
- **Week 1 Special Case:** For week 1, use week 0 or default 1500 if unavailable
- **Transaction Boundaries:** Commit per week (not per game) for performance
- **Timestamp Accuracy:** created_at should be realistic (2 days before game)
- **No Overwrites:** Script should skip games that already have predictions

### Implementation Details

**Historical Rating Lookup Query:**
```python
rating = db.query(RankingHistory.rating).filter(
    RankingHistory.team_id == team_id,
    RankingHistory.season == season,
    RankingHistory.week == prediction_week
).scalar()

if rating is None:
    logger.warning(f"No historical rating for team {team_id} week {prediction_week}, using default 1500")
    rating = 1500
```

**Prediction Creation:**
```python
from datetime import timedelta

# Calculate prediction timestamp (2 days before game)
if game.game_date:
    prediction_timestamp = game.game_date - timedelta(days=2)
else:
    # Fallback: approximate based on season start + week offset
    prediction_timestamp = estimate_game_date(game.season, game.week) - timedelta(days=2)

# Reuse existing prediction calculation
pred_dict = _calculate_game_prediction(game, home_team, away_team, home_rating, away_rating)

# Create prediction record
prediction = Prediction(
    game_id=game.id,
    predicted_winner_id=pred_dict['predicted_winner_id'],
    predicted_home_score=pred_dict['predicted_home_score'],
    predicted_away_score=pred_dict['predicted_away_score'],
    win_probability=pred_dict['home_win_probability'] / 100.0 if pred_dict['predicted_winner_id'] == game.home_team_id else pred_dict['away_win_probability'] / 100.0,
    home_elo_at_prediction=home_rating,
    away_elo_at_prediction=away_rating,
    was_correct=None,
    created_at=prediction_timestamp
)
```

---

## Definition of Done

- [x] Script file created: `scripts/backfill_historical_predictions.py`
- [x] Script queries processed games without predictions correctly
- [x] Script retrieves historical ELO ratings from correct weeks
- [x] Script handles Week 1 edge case (uses week 0 or default 1500)
- [x] Script generates predictions using historical ratings algorithm
- [x] Script saves predictions with correct schema and timestamps
- [x] Script provides comprehensive logging (start, progress, summary)
- [x] Manual test run completed successfully on real data (411 predictions created)
- [x] Existing `generate_predictions()` functionality verified unchanged
- [x] Documentation updated (script docstring included)
- [ ] Unit tests created for rating lookup logic (Story 002)
- [ ] Integration test with sample data passes (Story 002)

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Incorrect historical ratings could generate inaccurate predictions that misrepresent system accuracy

**Mitigation:**
- Use only verified data from `RankingHistory` table
- Log all rating lookups for audit trail
- Validate that retrieved ratings are within expected range (1000-2500)
- Add sanity check: if win_probability is outside 5-95%, log warning

**Rollback:**
```python
# Delete all predictions created by this script run
DELETE FROM predictions
WHERE created_at BETWEEN '2025-10-27 10:00:00' AND '2025-10-27 10:05:00';
```
Can also query by game_id range or use backup database

### Compatibility Verification

- ✅ **No breaking changes to existing APIs:** Script doesn't modify any APIs
- ✅ **Database changes are additive only:** Only INSERT operations, no schema changes
- ✅ **UI changes follow existing design patterns:** No UI changes required
- ✅ **Performance impact is negligible:** One-time backfill, can run during off-hours

---

## Validation Checklist

### Scope Validation

- ✅ **Story can be completed in one development session:** Core script is ~200-300 lines, 3-4 hours work
- ✅ **Integration approach is straightforward:** Reuses existing functions, standard database queries
- ✅ **Follows existing patterns exactly:** Matches `generate_predictions.py` and `weekly_update.py` patterns
- ✅ **No design or architecture work required:** Uses existing architecture

### Clarity Check

- ✅ **Story requirements are unambiguous:** Clear query specs, algorithm defined, logging specified
- ✅ **Integration points are clearly specified:** RankingHistory (read), predictions (write), ranking_service (function reuse)
- ✅ **Success criteria are testable:** All criteria have objective pass/fail conditions
- ✅ **Rollback approach is simple:** DELETE query with timestamp range

---

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_backfill_predictions.py`

```python
def test_get_historical_rating_returns_correct_week():
    """Verify historical rating lookup uses correct week"""
    # Setup: create RankingHistory records for week 4 and 5
    # Test: lookup rating for game in week 5
    # Assert: returns week 4 rating

def test_get_historical_rating_week_1_uses_week_0():
    """Verify Week 1 games use week 0 ratings"""
    # Setup: create RankingHistory record for week 0
    # Test: lookup rating for game in week 1
    # Assert: returns week 0 rating

def test_get_historical_rating_missing_uses_default():
    """Verify missing historical rating defaults to 1500"""
    # Setup: no RankingHistory records
    # Test: lookup rating for any game
    # Assert: returns 1500 and logs warning

def test_prediction_timestamp_calculation():
    """Verify created_at is 2 days before game_date"""
    # Test: calculate timestamp for game with known date
    # Assert: timestamp is game_date - 2 days
```

### Integration Tests

**File:** `tests/integration/test_backfill_integration.py`

```python
def test_backfill_generates_predictions_for_processed_games(test_db):
    """End-to-end test: backfill creates predictions for all processed games"""
    # Setup: create 3 processed games, historical ratings, no predictions
    # Run: backfill script
    # Assert: 3 predictions created with correct game_ids
    # Assert: predictions use historical ratings
    # Assert: no duplicate predictions

def test_backfill_skips_games_with_existing_predictions(test_db):
    """Verify script doesn't create duplicate predictions"""
    # Setup: create 2 games, 1 already has prediction
    # Run: backfill script
    # Assert: only 1 new prediction created
```

---

## Example Output

```
================================================================================
Retrospective Prediction Backfill
================================================================================
Season: 2025
Found 350 processed games without predictions

Week 1: Processing 48 games...
  ✓ Generated 48 predictions (using week 0 ratings)

Week 2: Processing 50 games...
  ✓ Generated 50 predictions

Week 3: Processing 47 games...
  ⚠ Team ID 42 missing historical rating for week 2, using default 1500
  ✓ Generated 47 predictions (1 warning)

...

Week 8: Processing 52 games...
  ✓ Generated 52 predictions

--------------------------------------------------------------------------------
Summary:
  Total games processed: 350
  Predictions created: 350
  Warnings: 1 (missing historical ratings)
  Errors: 0
  Duration: 8.3 seconds

✅ Backfill completed successfully
================================================================================
```

---

**Created:** 2025-10-27
**Last Updated:** 2025-10-27
**Assigned To:** Development Team
