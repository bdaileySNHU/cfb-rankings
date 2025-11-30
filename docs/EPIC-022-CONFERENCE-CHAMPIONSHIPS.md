# Epic 022: Conference Championship Game Support

**Epic Number**: EPIC-022
**Created**: 2025-11-30
**Status**: Planning
**Type**: Brownfield Enhancement

## Epic Goal

Add conference championship games to team schedules and display them with proper visual indicators, enabling users to track postseason performance and setting the foundation for future bowl game and playoff support.

## Epic Description

**Existing System Context:**

- **Current functionality**: System imports and displays regular season FBS games (weeks 1-15), but does not currently import or distinguish conference championship games from regular season games
- **Technology stack**:
  - Backend: Python 3.x, FastAPI, SQLAlchemy
  - Database: SQLite/PostgreSQL
  - External API: College Football Data API (CFBD) - already supports `season_type='postseason'` parameter
  - Frontend: Vanilla JavaScript
- **Integration points**:
  - `Game` model in `models.py` (stores game data with week/season)
  - `cfbd_client.py` - CFBD API client with `get_games()` method
  - `import_real_data.py` - main data import script
  - `/api/teams/{team_id}/schedule` endpoint in `main.py:177`
  - `frontend/js/team.js` - team schedule display (loadSchedule function at line 168)
  - `ranking_service.py` - ELO calculation (MAX_WEEK = 15 supports postseason)

**Enhancement Details:**

- **What's being added/changed**:
  1. Add `game_type` field to `Game` model to distinguish regular season vs conference championship games
  2. Update CFBD API client to fetch postseason games (conference championships)
  3. Modify import scripts to import conference championship games alongside regular season
  4. Add visual indicator (badge/icon) on frontend to highlight conference championship games
  5. Ensure ELO rankings properly process conference championship games

- **How it integrates**:
  - Extends `Game` model with nullable `game_type` field (backward compatible - NULL = regular season)
  - Updates `cfbd_client.get_games()` to support `season_type` parameter
  - Import scripts call CFBD API twice: once for regular season, once for postseason
  - Frontend checks `game_type` field and displays "Conference Championship" badge when applicable
  - Rankings continue to process all games normally (conference championships already fall within week 1-15 range)

- **Success criteria**:
  - Conference championship games appear on team schedules
  - Conference championship games have clear visual indicator differentiating them from regular season
  - ELO rankings correctly process conference championship results
  - System performance remains unchanged (minimal additional API calls)
  - Existing regular season game display unchanged

## Stories

### Story 22.1: Game Type Data Model and Conference Championship Import

**Goal**: Add game_type field to database and import conference championship games from CFBD API

**Tasks**:
- Add `game_type` VARCHAR(50) nullable field to `Game` model (values: NULL/regular/conference_championship)
- Create Alembic migration for schema change
- Update `cfbd_client.py` to add `season_type` parameter to `get_games()` method
- Modify `import_real_data.py` to import postseason games (season_type='postseason')
- Filter imported postseason games to only include conference championships (exclude bowl games for now)
- Add validation to ensure conference championship games have valid week numbers

**Acceptance Criteria**:
- Migration runs successfully without errors
- Conference championship games imported from CFBD API with `game_type='conference_championship'`
- Existing regular season games have `game_type=NULL` (backward compatible)
- Import script successfully identifies and imports 10-14 conference championship games per season
- No duplicate games created during import

**Integration Verification**:
- IV1: Existing games without game_type (NULL) display and process correctly
- IV2: API imports complete successfully with new game_type field populated
- IV3: Database queries perform within acceptable thresholds (index on game_type if needed)

---

### Story 22.2: Frontend Display of Conference Championship Games

**Goal**: Update frontend to display conference championship indicator on team schedules

**Tasks**:
- Update API response schema to include `game_type` field in game objects
- Modify `/api/teams/{team_id}/schedule` endpoint to return `game_type` for each game
- Update `frontend/js/team.js` `createScheduleRow()` function to display badge for conference championships
- Add CSS styling for conference championship badge (e.g., gold border or "CONF CHAMP" label)
- Ensure badge displays consistently across all schedule views

**Acceptance Criteria**:
- Conference championship games display with clear visual indicator (badge/label)
- Regular season games display without badge (no regression)
- Badge is visually distinct and easy to identify
- Mobile responsive design maintains badge visibility
- Schedule page loads without performance degradation

**Integration Verification**:
- IV1: Schedule API returns game_type field for all games
- IV2: Frontend correctly renders badge for conference championship games
- IV3: No visual regressions on regular season game display

---

### Story 22.3: Ranking Processing for Conference Championships

**Goal**: Verify and document that ELO rankings correctly process conference championship games

**Tasks**:
- Verify `ranking_service.py` processes conference championship games correctly (no code changes needed - just validation)
- Test that conference championship games contribute to team ELO ratings as expected
- Verify week numbering for conference championships (typically week 14-15) processes correctly
- Document how conference championships impact rankings
- Add integration test for ranking calculation with conference championship games

**Acceptance Criteria**:
- Conference championship game results correctly update team ELO ratings
- Win/loss records include conference championship results
- Ranking history shows correct ratings after conference championship week
- No edge cases or errors when processing conference championship games
- Integration test passes validating conference championship ranking updates

**Integration Verification**:
- IV1: Teams playing in conference championships have correct updated ELO ratings
- IV2: Historical rankings show accurate progression through conference championship week
- IV3: Prediction system can generate predictions for conference championship games

---

## Compatibility Requirements

- ✓ **Existing APIs remain unchanged**: `/api/teams/{team_id}/schedule` adds optional `game_type` field (backward compatible)
- ✓ **Database schema changes are backward compatible**: `game_type` field is nullable, existing queries unaffected
- ✓ **UI changes follow existing patterns**: Badge design follows existing FCS badge pattern from EPIC-011
- ✓ **Performance impact is minimal**: Additional API calls only during weekly import (~2-3 extra calls per week during championship week)

## Risk Mitigation

**Primary Risk**: Conference championship games imported incorrectly or duplicated with regular season games

**Mitigation**:
- Use CFBD API's `season_type` parameter to clearly separate regular vs postseason imports
- Add explicit filtering to exclude bowl games and playoff games (import only conference championships)
- Implement duplicate detection based on team matchups and game dates
- Run dry-run import and validate game counts before production import
- Document expected conference championship count (10 FBS conferences = ~10 championship games)

**Rollback Plan**:
- Database migration is additive (new nullable column), rollback drops column if needed
- Alembic downgrade script provided for schema rollback
- Can toggle import of postseason games via configuration flag
- If data issues occur, delete postseason games with: `DELETE FROM games WHERE game_type = 'conference_championship'`

## Definition of Done

- ✓ All 3 stories completed with acceptance criteria met
- ✓ Existing functionality verified: regular season games display and process unchanged
- ✓ Integration points working: conference championships imported, displayed, and ranked correctly
- ✓ Documentation updated: Epic document completed, migration notes added
- ✓ No regression in existing features: all tests pass, regular season functionality intact

## Future Considerations

This epic sets the foundation for **EPIC-023: Bowl Games and Playoffs** which will:
- Import bowl games (25+ games) with `game_type='bowl'`
- Import playoff games (4-12 games) with `game_type='playoff'`
- Enhanced UI showing postseason bracket views
- Filtering/grouping by game type on schedules

## References

- **Game Model**: `models.py:60-144`
- **CFBD Client**: `cfbd_client.py:390-400` (get_games method)
- **Import Script**: `import_real_data.py`
- **Team Schedule API**: `main.py:177-224`
- **Frontend Schedule Display**: `frontend/js/team.js:168-215`
- **Weekly Workflow**: `docs/WEEKLY-WORKFLOW.md`
