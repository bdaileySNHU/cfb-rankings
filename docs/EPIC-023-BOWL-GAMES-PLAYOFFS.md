# Epic 023: Bowl Games and Playoff Support

**Epic Number**: EPIC-023
**Created**: 2025-11-30
**Status**: Complete
**Completed**: 2025-12-10 (retroactively documented)
**Type**: Brownfield Enhancement
**Dependencies**: EPIC-022 (Conference Championships)

## Implementation Note

This epic was previously marked as "Planning" but was actually **fully implemented** alongside EPIC-022. The implementation includes all three stories (bowl import, playoff import, and frontend display). This document has been updated to reflect the actual completed state discovered during EPIC-028 cleanup.

## Epic Goal

Import and display bowl games and College Football Playoff games on team schedules with proper categorization, enabling users to track complete postseason performance and view the full playoff bracket.

## Epic Description

**Existing System Context:**

- **Current functionality**: System imports regular season games (weeks 1-15) and conference championship games (EPIC-022), but does not import bowl games or playoff games
- **Technology stack**:
  - Backend: Python 3.x, FastAPI, SQLAlchemy
  - Database: SQLite/PostgreSQL with `game_type` field from EPIC-022
  - External API: College Football Data API (CFBD) - supports `season_type='postseason'` parameter
  - Frontend: Vanilla JavaScript
- **Integration points**:
  - `Game` model in `models.py` - already has `game_type` field from EPIC-022
  - `cfbd_client.py` - CFBD API client with `get_games()` method supporting `season_type`
  - `import_real_data.py` - data import script
  - `/api/teams/{team_id}/schedule` endpoint in `main.py:177`
  - `frontend/js/team.js` - team schedule display with game_type badge support from EPIC-022
  - `ranking_service.py` - ELO calculation

**Enhancement Details:**

- **What's being added/changed**:
  1. Add `postseason_name` VARCHAR(100) field to `Game` model to store bowl name or playoff round
  2. Update import scripts to fetch and import bowl games from CFBD postseason API
  3. Update import scripts to fetch and import playoff games from CFBD postseason API
  4. Add frontend filtering to show/hide regular season vs postseason games
  5. Add frontend grouping for bowl games and playoff bracket visualization
  6. Ensure bowl/playoff games display with appropriate badges and metadata

- **How it integrates**:
  - Extends `Game` model with nullable `postseason_name` field (e.g., "Rose Bowl", "CFP Semifinal")
  - Import scripts filter CFBD postseason response by game type (conference championship already handled in EPIC-022)
  - Sets `game_type='bowl'` for bowl games, `game_type='playoff'` for playoff games
  - Frontend checks `game_type` and displays appropriate badges ("BOWL", "PLAYOFF")
  - Frontend adds filter dropdown: "All Games" / "Regular Season" / "Conference Championships" / "Bowls" / "Playoffs"
  - Rankings continue to process all games normally (postseason games contribute to ELO)

- **Success criteria**:
  - All bowl games (25-40 per season) imported correctly with bowl names
  - All playoff games (4-12 per season) imported correctly with round information
  - Team schedules show complete postseason including bowls and playoffs
  - Frontend filtering allows users to focus on regular season or postseason games
  - Bowl and playoff games have clear visual indicators distinct from regular season
  - ELO rankings correctly process bowl and playoff results

## Stories

### Story 23.1: Bowl Game Import and Storage ✅ COMPLETE

**Goal**: Import bowl games from CFBD API with bowl names and display metadata

**Implementation**: `import_real_data.py:689-877` - `import_bowl_games()` function

**Tasks**:
- Add `postseason_name` VARCHAR(100) nullable field to `Game` model
- Create Alembic migration for schema change
- Update `import_real_data.py` to import postseason games with filtering logic:
  - Conference championships: `game_type='conference_championship'` (already handled in EPIC-022)
  - Bowl games: `game_type='bowl'`, `postseason_name` = bowl name from CFBD
  - Playoff games: handle in Story 23.2
- Parse bowl name from CFBD API response and store in `postseason_name` field
- Add validation to ensure bowl games have valid names and dates
- Test import with multiple seasons to verify all major bowls captured

**Acceptance Criteria**:
- ✅ Migration runs successfully without errors (`postseason_name` field exists in Game model)
- ✅ Bowl games imported from CFBD API with `game_type='bowl'` and `postseason_name` populated
- ✅ Expected bowl count per season: 25-40 games (FBS bowl eligible teams) - **Current DB: 35 bowl games**
- ✅ Bowl names accurate and properly formatted (e.g., "Rose Bowl Game", "Sugar Bowl")
- ✅ No duplicate bowl games created during import (duplicate detection in place)
- ✅ Conference championship games (EPIC-022) unaffected by bowl import logic

**Integration Verification**:
- ✅ IV1: Existing games (regular season, conference championships) import correctly alongside bowl games
- ✅ IV2: Bowl games have correct `postseason_name` values from CFBD API
- ✅ IV3: Database queries perform well with additional postseason games (test with full season data)

---

### Story 23.2: Playoff Game Import and Storage ✅ COMPLETE

**Goal**: Import College Football Playoff games with round information

**Implementation**: `import_real_data.py:880-1090` - `import_playoff_games()` function

**Tasks**:
- Update `import_real_data.py` to import playoff games from CFBD postseason API
- Set `game_type='playoff'` for playoff games
- Store playoff round in `postseason_name` field (e.g., "CFP Semifinal - Rose Bowl", "CFP National Championship")
- Add logic to identify playoff games vs regular bowl games (CFBD may use game notes or specific week numbers)
- Handle different playoff formats: 4-team (2014-2023) vs 12-team (2024+) structures
- Add validation to ensure playoff bracket integrity (semifinals before championship, etc.)

**Acceptance Criteria**:
- ✅ Playoff games imported from CFBD API with `game_type='playoff'`
- ✅ Playoff round information stored in `postseason_name` (e.g., "CFP Semifinal", "CFP Championship")
- ✅ Expected playoff count: 4-12 games depending on season - **Current DB: 11 playoff games**
- ✅ Playoff games correctly ordered by round (quarterfinals → semifinals → championship)
- ✅ No duplicate playoff games created during import (duplicate detection in place)
- ✅ Playoff games distinguished from regular bowl games

**Integration Verification**:
- ✅ IV1: Playoff games have distinct `game_type='playoff'` and proper round information
- ✅ IV2: Both old format (4-team) and new format (12-team) playoffs import correctly (logic at lines 955-984)
- ✅ IV3: Playoff game results correctly update team ELO ratings and records

---

### Story 23.3: Enhanced Postseason Display and Filtering ✅ COMPLETE

**Goal**: Update frontend to display bowl/playoff games with filtering and enhanced visualization

**Implementation**:
- Frontend: `frontend/js/team.js:275-417`, `frontend/team.html:136-137`
- Styles: `frontend/css/style.css:710-793`
- Schema: `src/models/schemas.py:272-274` (ScheduleGame includes postseason_name)

**Tasks**:
- Update API response schema to include `postseason_name` field
- Modify `/api/teams/{team_id}/schedule` endpoint to return `postseason_name`
- Update `frontend/js/team.js` to display bowl/playoff badges with game names:
  - Bowl games: Show "BOWL" badge + bowl name (e.g., "Rose Bowl")
  - Playoff games: Show "PLAYOFF" badge + round (e.g., "CFP Semifinal")
- Add filter dropdown to schedule page: "All Games" / "Regular Season" / "Postseason Only"
- Optional: Add postseason sub-filter: "Conference Championships" / "Bowls" / "Playoffs"
- Add CSS styling for bowl and playoff badges (distinct from conference championship badge)
- Ensure postseason games visually grouped or separated from regular season on schedule

**Acceptance Criteria**:
- ✅ Bowl games display with "BOWL" badge and bowl name visible (team.js:366-417)
- ✅ Playoff games display with "PLAYOFF" badge and round information visible (team.js:376-417)
- ✅ Filter dropdown allows users to toggle between regular season and postseason views (team.html:136-137)
- ✅ Filtered views update schedule table dynamically without page reload (team.js:275-279)
- ✅ Mobile responsive design maintains filter usability and badge visibility (style.css:743-793)
- ✅ Badge design is consistent with existing conference championship badge (EPIC-022)
- ✅ Schedule page loads without performance degradation even with full postseason data

**Integration Verification**:
- ✅ IV1: API returns `postseason_name` field for bowl and playoff games (schemas.py:272-274)
- ✅ IV2: Frontend correctly renders distinct badges for bowls vs playoffs vs conference championships
- ✅ IV3: Filtering works correctly and shows appropriate game subsets (game_type filtering)
- ✅ IV4: No visual regressions on regular season or conference championship game display

---

## Compatibility Requirements

- ✓ **Existing APIs remain unchanged**: `/api/teams/{team_id}/schedule` adds optional `postseason_name` field (backward compatible)
- ✓ **Database schema changes are backward compatible**: `postseason_name` field is nullable, existing queries unaffected
- ✓ **UI changes follow existing patterns**: Badge/filter design follows existing patterns from EPIC-011 and EPIC-022
- ✓ **Performance impact is minimal**: Additional API calls only during postseason import (~3-5 extra calls per season)

## Risk Mitigation

**Primary Risk**: Bowl and playoff game identification logic incorrectly categorizes games or misses games

**Mitigation**:
- Use CFBD API's explicit game metadata to distinguish bowl vs playoff games
- Cross-reference with known bowl game names list (Rose, Sugar, Orange, Cotton, Peach, Fiesta, etc.)
- Validate playoff game count matches expected format (4-team or 12-team)
- Run dry-run import and manually verify game counts before production
- Document expected game counts:
  - Conference championships: ~10 games (EPIC-022)
  - Bowl games: 25-40 games
  - Playoff games: 4-12 games depending on season
- Add logging to track which games are categorized as bowl vs playoff

**Rollback Plan**:
- Database migration is additive (new nullable column), rollback drops column if needed
- Alembic downgrade script provided for schema rollback
- Can delete bowl/playoff games if data issues occur:
  - `DELETE FROM games WHERE game_type = 'bowl'`
  - `DELETE FROM games WHERE game_type = 'playoff'`
- Filter UI changes are additive, can be hidden via CSS if needed

## Definition of Done

- ✅ All 3 stories completed with acceptance criteria met
- ✅ Existing functionality verified: regular season and conference championship games unchanged
- ✅ Integration points working: bowls and playoffs imported, displayed, and ranked correctly
- ✅ Documentation updated: Epic document updated to reflect completion status
- ✅ No regression in existing features: all tests pass, regular season functionality intact
- ✅ Complete postseason support: conference championships (EPIC-022) + bowls + playoffs

**Database Stats**:
- 35 bowl games imported and stored
- 11 playoff games imported and stored
- All games properly categorized with `game_type` and `postseason_name` fields

## Future Considerations

Potential future enhancements after EPIC-023 completion:
- **Postseason bracket visualization**: Interactive playoff bracket showing team progression
- **Bowl matchup predictions**: Generate predictions for bowl games based on final ELO ratings
- **Postseason statistics**: Separate stats for regular season vs postseason performance
- **Historical bowl records**: Track team performance across all bowl appearances
- **Rivalry bowl tracking**: Highlight traditional bowl matchups and rivalries

## References

- **EPIC-022**: Conference Championships (dependency - `game_type` field exists)
- **Game Model**: `models.py:60-144`
- **CFBD Client**: `cfbd_client.py:390-400` (get_games method with season_type parameter)
- **Import Script**: `import_real_data.py`
- **Team Schedule API**: `main.py:177-224`
- **Frontend Schedule Display**: `frontend/js/team.js:168-215`
- **Weekly Workflow**: `docs/WEEKLY-WORKFLOW.md`
- **CFBD API Documentation**: https://collegefootballdata.com/
