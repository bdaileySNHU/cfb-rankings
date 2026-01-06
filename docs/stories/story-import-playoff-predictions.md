# Story: Import Playoff Games and Generate Predictions - Brownfield Addition

## User Story

As a **college football fan**,
I want **predictions for upcoming playoff games to be displayed on the site**,
So that **I can see ELO predictions for the next round of playoff matchups**.

## Story Context

**Existing System Integration:**

- Integrates with: Game import system (weekly_update.py, import_real_data.py) and prediction generation (generate_predictions.py)
- Technology: Python, CFBD API, SQLite database, FastAPI backend
- Follows pattern: Existing game import and prediction generation scripts
- Touch points:
  - `scripts/weekly_update.py` (weekly game import)
  - `scripts/generate_predictions.py` (prediction generation)
  - `src/core/ranking_service.py` (generate_predictions function)
  - CFBD API `/games` endpoint
  - Database tables: games, predictions

**Current Issue:**

The prediction page shows "No upcoming games to predict" because:
1. The next round of playoff games hasn't been imported from CFBD API yet
2. Without imported games, predictions can't be generated
3. The weekly update script may not automatically pick up postseason games

## Acceptance Criteria

**Functional Requirements:**

1. Upcoming playoff games (next round) are imported into the database
2. Predictions are generated for all upcoming playoff games
3. Predictions display on the frontend "Game Predictions" section

**Integration Requirements:**

4. Game import uses existing CFBD API integration patterns
5. Prediction generation follows existing `generate_predictions()` logic
6. Imported games have correct postseason flags and game_type set

**Quality Requirements:**

7. Imported games include all necessary fields (teams, date, neutral site, etc.)
8. Predictions include win probabilities and predicted scores
9. No duplicate games or predictions created

## Technical Notes

**Integration Approach:**

Option 1: **Manual Script Execution** (Fastest)
```bash
# On production server
cd /var/www/cfb-rankings
sudo -u www-data bash -c "source venv/bin/activate && python3 scripts/weekly_update.py"
# This should import new games from CFBD API

# Then generate predictions
sudo -u www-data bash -c "source venv/bin/activate && python3 scripts/generate_predictions.py"
```

Option 2: **API-Triggered Import** (If API endpoint exists)
```bash
curl -X POST "http://localhost:8000/api/admin/import-games"
```

**Existing Pattern Reference:**
- Game import: `weekly_update.py` calls `import_real_data.py` which uses CFBD API
- Prediction generation: `generate_predictions.py` queries unprocessed games and generates predictions
- Both scripts follow same pattern as historical data import

**Key Constraints:**
- CFBD API must have playoff schedule data available
- Games must be unprocessed (is_processed = False) to generate predictions
- Playoff games should have `postseason_name` field populated (e.g., "College Football Playoff")

**Verification Queries:**
```sql
-- Check if playoff games exist
SELECT * FROM games
WHERE season = 2025
  AND is_processed = FALSE
  AND postseason_name IS NOT NULL
ORDER BY game_date;

-- Check if predictions were created
SELECT COUNT(*) FROM predictions p
JOIN games g ON p.game_id = g.id
WHERE g.season = 2025 AND g.postseason_name IS NOT NULL;
```

## Definition of Done

- [ ] Next round playoff games imported from CFBD API
- [ ] Predictions generated for all playoff games
- [ ] Predictions visible on frontend "Game Predictions" page
- [ ] No duplicate games or predictions created
- [ ] Games have correct postseason_name and game_type values
- [ ] Verification queries confirm data is correct

## Risk and Compatibility Check

**Minimal Risk Assessment:**

- **Primary Risk:** CFBD API may not have playoff schedule data yet
- **Mitigation:** Check CFBD API manually first, delay if data not available
- **Rollback:** Delete imported games/predictions with WHERE postseason_name condition

**Compatibility Verification:**

- [x] No breaking changes to existing APIs (uses existing scripts)
- [x] Database changes are additive only (new rows in games/predictions tables)
- [x] UI changes: None (existing prediction page will display new data)
- [x] Performance impact: Negligible (small number of playoff games)

## Validation Checklist

**Scope Validation:**

- [x] Story can be completed in one development session (< 1 hour)
- [x] Integration approach is straightforward (use existing scripts)
- [x] Follows existing patterns exactly (weekly_update + generate_predictions)
- [x] No design or architecture work required

**Clarity Check:**

- [x] Story requirements are unambiguous (import games, generate predictions)
- [x] Integration points are clearly specified (existing scripts)
- [x] Success criteria are testable (query database, check frontend)
- [x] Rollback approach is simple (DELETE WHERE postseason_name...)

## Story Metadata

- **Story Type:** Data Import / Operations
- **Complexity:** Trivial (use existing scripts)
- **Estimated Effort:** < 1 hour
- **Dependencies:** CFBD API has playoff schedule data available
- **Related:** Game import system, prediction generation system
- **Priority:** High (user-facing feature gap)

## Implementation Notes

**Step-by-step execution:**

1. **Verify CFBD API has data:**
   ```bash
   # Check if CFBD API has playoff games
   curl "https://api.collegefootballdata.com/games?year=2025&seasonType=postseason" \
     -H "Authorization: Bearer $CFBD_API_KEY"
   ```

2. **Import games (production):**
   ```bash
   cd /var/www/cfb-rankings
   sudo -u www-data bash -c "source venv/bin/activate && python3 scripts/weekly_update.py"
   ```

3. **Generate predictions (production):**
   ```bash
   sudo -u www-data bash -c "source venv/bin/activate && python3 scripts/generate_predictions.py"
   ```

4. **Verify results:**
   ```bash
   # Check games imported
   sudo -u www-data bash -c "cd /var/www/cfb-rankings && sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM games WHERE season = 2025 AND is_processed = FALSE AND postseason_name IS NOT NULL;'"

   # Check predictions created
   sudo -u www-data bash -c "cd /var/www/cfb-rankings && sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM predictions p JOIN games g ON p.game_id = g.id WHERE g.season = 2025 AND g.postseason_name IS NOT NULL;'"
   ```

5. **Refresh frontend:**
   - Visit cfb.bdailey.com
   - Navigate to Rankings page
   - Check "Game Predictions" section shows playoff games

## Alternative: Future Automation

For future seasons, consider enhancing `weekly_update.py` to explicitly check for postseason games:
- Add check for `seasonType=postseason` in CFBD API call
- Ensure playoff games are imported even if regular season has ended
- Document in README.md when to run for playoffs

**Note:** This is out of scope for this story but could be a future enhancement.

---

## Dev Agent Record

### Status
Ready for Review

### Agent Model Used
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Implementation Progress

**Completed:**
- [x] Verified CFBD API has playoff schedule data
- [x] Created execution script: `import_playoff_games.sh`
- [x] Imported 2 CFP semifinal games from CFBD API (Week 18)
- [x] Generated predictions for playoff games (games 1868 and 1869)
- [x] Added playoff weeks to frontend dropdown (Weeks 16-18)
- [x] Verified predictions exist in production database
- [x] Frontend now displays playoff predictions when Week 18 is selected

### Debug Log References
None

### Completion Notes
- Successfully imported 2 CFP semifinal games (Week 18) from CFBD API
  - Game 1868: Ole Miss vs Miami
  - Game 1869: Indiana vs Oregon
- Created predictions for both playoff games
  - Ole Miss predicted winner (54.7% confidence)
  - Indiana predicted winner (52.8% confidence)
- Identified and fixed season rollover issue:
  - CFBDClient.get_current_season() correctly handles January playoffs as 2025 season
  - generate_all_predictions.py now uses correct season logic
- Fixed frontend week dropdown to include playoff weeks 16-18
- All predictions verified in production database

### File List
**New Files:**
- `import_playoff_games.sh` - Production execution script with verification and env loading
- `scripts/generate_all_predictions.py` - Script to generate predictions for all unprocessed games

**Modified Files:**
- `docs/stories/story-import-playoff-predictions.md` - Added Dev Agent Record section
- `frontend/index.html` - Added playoff weeks (16-18) to prediction dropdown

### Change Log
- 2026-01-06: Verified CFBD API has 2 CFP semifinal games (Week 18)
- 2026-01-06: Created import_playoff_games.sh execution script
- 2026-01-06: Fixed script to load .env file for API authentication
- 2026-01-06: Fixed SQL queries to use JOINs for team names
- 2026-01-06: Created generate_all_predictions.py with correct season logic
- 2026-01-06: Fixed season rollover logic for January playoffs (2025 season)
- 2026-01-06: Executed import and prediction generation on production
- 2026-01-06: Added playoff weeks 16-18 to frontend dropdown
- 2026-01-06: Verified predictions display correctly in frontend
