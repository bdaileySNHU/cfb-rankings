# EPIC-017: Retrospective Prediction Generation - Brownfield Enhancement

**Status:** ✅ Complete
**Completion Date:** 2025-10-27
**Priority:** Medium
**Estimated Effort:** 2-3 days
**Actual Effort:** 1 day
**Dependencies:** None
**Related EPICs:** EPIC-007 (Predictions Storage), EPIC-010 (AP Poll Prediction Comparison)

## Epic Goal

Enable generation of historically accurate predictions for past games by calculating predictions using only the team ratings that existed immediately before each game was played, allowing the Prediction Comparison feature to display meaningful historical prediction accuracy data.

## Epic Description

### Existing System Context

- **Current functionality**: The system has a `generate_predictions()` function that creates predictions for unprocessed games using current team ELO ratings
- **Technology stack**: Python 3, FastAPI, SQLAlchemy ORM, SQLite database
- **Integration points**:
  - `ranking_service.py`: prediction generation logic
  - `models.py`: Prediction model with fields for `home_elo_at_prediction` and `away_elo_at_prediction`
  - `RankingHistory` table: stores historical ELO ratings by week
  - `/api/admin/generate-predictions` endpoint

### Enhancement Details

**What's being added/changed:**

New script (`scripts/backfill_historical_predictions.py`) that generates predictions for completed games by:

1. Querying all processed games without predictions
2. Looking up team ELO ratings from `RankingHistory` for the week BEFORE each game
3. Using the same prediction algorithm as `generate_predictions()` but with historical ratings
4. Saving predictions with `created_at` timestamp reflecting when prediction would have been made

**How it integrates:**

- Reuses existing `_calculate_game_prediction()` helper function from `ranking_service.py`
- Writes to same `predictions` table schema
- Uses `RankingHistory` table that already stores week-by-week ratings
- Can be run as one-time backfill or as part of weekly workflow

**Success criteria:**

- All processed games have corresponding predictions in database
- Predictions use ELO ratings from correct historical timeframe (week before game)
- Prediction Comparison page displays historical predictions with accuracy metrics
- No modification to existing prediction generation workflow

---

## Stories

### Story 001: Create Retrospective Prediction Generation Script

**Priority:** High
**Story Points:** 5

Create a new script `scripts/backfill_historical_predictions.py` that:
- Queries all processed games lacking predictions
- Fetches historical ELO ratings from `RankingHistory` for the week prior to each game
- Generates predictions using historical ratings
- Saves predictions to database with appropriate timestamps

**Acceptance Criteria:**
- [x] Script successfully generates predictions for all past games
- [x] Uses correct historical ELO ratings (from week N-1 for week N games)
- [x] Handles edge cases (Week 1 games, missing historical data)
- [x] Provides progress logging and summary statistics
- [x] Prediction format matches existing prediction schema exactly

**Technical Details:**
- Query: `SELECT * FROM games WHERE is_processed = True AND id NOT IN (SELECT game_id FROM predictions)`
- Historical rating lookup: `SELECT rating FROM ranking_history WHERE team_id = ? AND season = ? AND week = ?`
- For Week 1 games: use preseason ratings (week 0) or initial ELO (1500)

---

### Story 002: Add Data Validation and Safety Checks

**Priority:** High
**Story Points:** 3

Enhance the backfill script with:
- Validation that predictions aren't overwriting existing predictions
- Verification that historical ratings exist before generating predictions
- Dry-run mode to preview changes
- Rollback capability if predictions are incorrect

**Acceptance Criteria:**
- [x] Script has `--dry-run` flag to preview without writing
- [x] Prevents duplicate predictions (checks if prediction already exists for game_id)
- [x] Validates historical data completeness before processing
- [x] Logs warnings for games with missing historical data
- [x] Includes `--delete-backfilled` flag for rollback
- [x] Summary report shows: total games, predictions created, skipped, errors

**Technical Details:**
- Dry-run mode: perform all queries and calculations but don't commit to database
- Duplicate check: `SELECT COUNT(*) FROM predictions WHERE game_id = ?` before insert
- Validation: verify both home and away team have historical ratings for required week
- Rollback: `DELETE FROM predictions WHERE created_at BETWEEN ? AND ?` with start/end timestamps

---

### Story 003: Integrate with Weekly Workflow Documentation

**Priority:** Medium
**Story Points:** 2

Update workflow documentation to include:
- When and how to run backfill script
- Guidelines for verifying backfill accuracy
- Integration with existing `WEEKLY-WORKFLOW.md`

**Acceptance Criteria:**
- [x] `docs/WEEKLY-WORKFLOW.md` updated with backfill section
- [x] Includes usage examples: basic run, dry-run, rollback
- [x] Troubleshooting section covers common backfill issues
- [x] Workflow includes verification steps for historical predictions
- [x] README.md updated with backfill script description
- [x] Example output and expected results documented

**Documentation Sections to Add:**
- "One-Time Setup: Historical Prediction Backfill"
- "Verifying Backfill Accuracy"
- "Troubleshooting Backfill Issues"
- Command examples with expected output

---

## Compatibility Requirements

- ✅ **Existing APIs remain unchanged**: No API modifications required
- ✅ **Database schema changes are backward compatible**: Uses existing `predictions` table schema
- ✅ **UI changes follow existing patterns**: Prediction Comparison page requires no changes
- ✅ **Performance impact is minimal**: Backfill is one-time operation, can be run offline

---

## Risk Mitigation

**Primary Risk:** Incorrect historical ELO ratings could generate inaccurate predictions that don't reflect what the system would have actually predicted

**Mitigation:**
- Use `RankingHistory` table that already stores verified historical ratings
- Add validation to compare generated predictions against expected win probability ranges (10-90%)
- Include dry-run mode to verify predictions before committing
- Log all rating lookups for audit trail

**Rollback Plan:**
- Delete all predictions with `created_at` timestamp from backfill run
- SQL: `DELETE FROM predictions WHERE created_at BETWEEN 'start_time' AND 'end_time'`
- Script includes `--delete-backfilled` flag for easy rollback
- Keep backfill run log with timestamps for reference

---

## Definition of Done

- [x] All 3 stories completed with acceptance criteria met
- [x] Existing prediction generation functionality verified through testing
- [x] Backfill script successfully generates predictions for all past games (411 predictions created)
- [x] Documentation updated with backfill script usage
- [x] No regression in existing prediction generation or Prediction Comparison features
- [x] Historical predictions display correctly on Prediction Comparison page
- [x] Dry-run mode tested and working
- [x] Rollback procedure tested and documented

---

## Technical Implementation Notes

### Database Tables Involved

**predictions** (target table):
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL,
    predicted_winner_id INTEGER NOT NULL,
    predicted_home_score INTEGER NOT NULL,
    predicted_away_score INTEGER NOT NULL,
    win_probability FLOAT NOT NULL,
    home_elo_at_prediction FLOAT NOT NULL,
    away_elo_at_prediction FLOAT NOT NULL,
    was_correct BOOLEAN,
    created_at DATETIME NOT NULL
);
```

**ranking_history** (source for historical ratings):
```sql
CREATE TABLE ranking_history (
    id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    rating FLOAT NOT NULL,
    rank INTEGER,
    wins INTEGER,
    losses INTEGER,
    timestamp DATETIME NOT NULL
);
```

### Algorithm Flow

```
For each processed game without prediction:
    1. Get game.season, game.week, game.home_team_id, game.away_team_id
    2. Lookup week: prediction_week = max(0, game.week - 1)
    3. Query home_rating from ranking_history WHERE team_id=home_team_id, season=game.season, week=prediction_week
    4. Query away_rating from ranking_history WHERE team_id=away_team_id, season=game.season, week=prediction_week
    5. If either rating missing: use default (1500) and log warning
    6. Calculate prediction using _calculate_game_prediction() with historical ratings
    7. Set created_at to approximate date (game.game_date - 2 days)
    8. Insert prediction record
```

### Expected Output Format

```
Retrospective Prediction Backfill
================================================================================
Season: 2025
Processing games from Week 1 through Week 8

Week 1: Processing 48 games...
  ✓ Generated 48 predictions (0 skipped, 0 errors)

Week 2: Processing 50 games...
  ✓ Generated 50 predictions (0 skipped, 0 errors)

...

Summary:
  Total games processed: 350
  Predictions created: 350
  Predictions skipped: 0
  Errors: 0

✅ Backfill completed successfully
```

---

## Related Documentation

- **Prediction Storage:** `docs/EPIC-007-PREDICTIONS-STORAGE.md`
- **Prediction Comparison:** `docs/EPIC-010-AP-POLL-PREDICTION-COMPARISON.md`
- **Weekly Workflow:** `docs/WEEKLY-WORKFLOW.md`
- **Ranking Service:** `ranking_service.py` (lines 403-476: generate_predictions)
- **Models:** `models.py` (Prediction model, RankingHistory model)

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing College Football Rankings System running **Python 3, FastAPI, SQLAlchemy ORM, SQLite**
- Integration points:
  - `RankingHistory` table (stores week-by-week ELO ratings)
  - `Prediction` model and table
  - `generate_predictions()` and `_calculate_game_prediction()` functions in `ranking_service.py`
- Existing patterns to follow:
  - Script structure matches `scripts/generate_predictions.py`
  - Command-line argument handling like `scripts/weekly_update.py`
  - Logging format consistent with existing scripts
- Critical compatibility requirements:
  - Must NOT overwrite existing predictions
  - Must use historical ratings from correct time period
  - Must maintain existing prediction table schema
- Each story must include verification that existing prediction generation workflow remains intact

The epic should maintain system integrity while delivering **historical prediction backfilling for Prediction Comparison feature accuracy analysis**."

---

**Created:** 2025-10-27
**Last Updated:** 2025-10-27
**Owner:** Development Team
**Status:** Ready to Start
