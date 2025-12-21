# Story: Diagnose Playoff Game Import Issues - Brownfield Investigation

**Status:** 📋 Draft
**Epic:** EPIC-FIX-PLAYOFF-GAMES
**Priority:** High
**Risk Level:** 🟢 Zero Risk (read-only investigation)
**Estimated Effort:** 1-2 hours

---

## Story

As a **system administrator managing the CFB ranking system**, I want **to understand why 2024 playoff games are missing or showing 0-0 scores**, so that **I can implement the correct fix to import complete playoff game data and prevent similar issues in future seasons**.

---

## Acceptance Criteria

1. **Root cause identified** for why playoff games have 0-0 scores or are missing:
   - Determine if issue is timing (games unavailable when API called)
   - Determine if issue is API parameters (wrong season type, missing week parameter)
   - Determine if issue is week assignment logic (playoffs assigned to wrong week)
   - Document specific cause with evidence

2. **CFBD API playoff game structure documented**:
   - Document required API parameters for fetching playoff games (season, seasonType, week, etc.)
   - Document playoff-specific fields in API response (playoff_round, playoff_seed, etc.)
   - Document how CFBD differentiates regular season vs postseason games
   - Create example API response for reference

3. **List of specific games needing import/fixing created**:
   - List all 4 first-round games (Dec 19-20) with expected teams and dates
   - List all 4 quarterfinal games with TBD opponent scenarios
   - Identify any existing games in database that need updating vs new imports needed

4. **Recommendations for fix approach documented**:
   - Recommend whether to update existing 0-0 games in-place or delete and re-import
   - Recommend API parameter changes needed for import scripts
   - Recommend database schema changes (if any) for playoff metadata
   - Document approach for handling TBD opponents in quarterfinal games

5. **Diagnostic report created** in `docs/diagnostics/playoff-games-investigation.md`:
   - Contains all findings from AC 1-4
   - Includes SQL queries used to investigate database state
   - Includes CFBD API examples used to test playoff game fetching
   - Includes recommendations for Stories 2 and 3

---

## Integration Verification

- **IV1: No Database Changes** - This story is read-only investigation, database remains unchanged
- **IV2: No Code Changes** - No changes to import scripts or CFBD client in this story
- **IV3: Diagnostic Queries Non-Destructive** - All SQL queries use SELECT only, no INSERT/UPDATE/DELETE

---

## Dev Notes

### Previous Story Insights

This is the first story in EPIC-FIX-PLAYOFF-GAMES. No previous stories for this epic.

**Context:**
- User reported missing/incomplete playoff games in Week 16
- Screenshot shows games like "James Madison vs Oregon" and "Alabama vs Oklahoma" with 0-0 scores
- Some first-round playoff games (Dec 19-20) may be completely missing
- System currently imports regular season games successfully
- Need to ensure playoff handling works for 2025+ seasons

[Source: `docs/epics/epic-fix-playoff-games-import.md`]

### Data Models

**Game Model** (existing):
- Located in: `src/models/models.py`
- Key fields: `home_team`, `away_team`, `home_points`, `away_points`, `week`, `season`, `game_date`, `neutral_site`
- Possible playoff fields to investigate: `season_type`, `playoff_round`, `postseason_name`, `game_type`

**Investigation Focus:**
- Check if Game model has fields for playoff metadata
- Determine if we need to add fields or if they already exist but aren't being populated

[Source: CFBD API schema, `src/models/models.py`]

### API Specifications

**CFBD API Endpoints to Test:**
- `GET /games` with parameters:
  - `season=2024`
  - `seasonType=postseason` (vs `regular`)
  - `week=NULL` or specific playoff round
  - `division=fbs`

**Expected Playoff Game Fields:**
- `playoff_round`: "first_round", "quarterfinals", "semifinals", "championship"
- `playoff_seed`: Team seed number (1-12)
- `neutral_site`: true (playoff games are neutral)
- `season_type`: "postseason"
- `postseason_name`: "College Football Playoff"

[Source: `docs/epics/epic-fix-playoff-games-import.md#Technical Notes`]

### File Locations

**Files to Investigate:**
- `src/integrations/cfbd_client.py` - Check current API parameters for get_games()
- `scripts/import_real_data.py` - Check if postseason games are in import scope
- `scripts/weekly_update.py` - Check if weekly updates include playoff games
- `src/models/models.py` - Check Game model schema for playoff fields

**Diagnostic Queries Location:**
- Create: `docs/diagnostics/playoff-games-investigation.md`

**SQL Queries to Run:**
```sql
-- Check Week 16 games with 0-0 scores
SELECT week, home_team, away_team, home_points, away_points, game_date, season_type, game_type
FROM games
WHERE week = 16 AND season = 2024;

-- Check all 2024 postseason games
SELECT COUNT(*), season_type
FROM games
WHERE season = 2024
GROUP BY season_type;

-- Check for games in Dec 19-20 date range (first-round playoff dates)
SELECT home_team, away_team, home_points, away_points, game_date
FROM games
WHERE season = 2024 AND game_date BETWEEN '2024-12-19' AND '2024-12-20'
ORDER BY game_date;
```

[Source: `docs/epics/epic-fix-playoff-games-import.md#Investigation Commands`]

### Investigation Approach

**Step 1: Database Investigation**
1. Run SQL queries to check current state of playoff games
2. Identify games with 0-0 scores in Week 16 or postseason weeks
3. Check if any games exist for Dec 19-20 first-round dates
4. Document which teams and matchups are present vs missing

**Step 2: CFBD API Investigation**
1. Query CFBD API with `seasonType=postseason` for 2024 season
2. Check API response structure for playoff-specific fields
3. Compare API data to database data to identify what's missing
4. Test different API parameter combinations to find correct approach

**Step 3: Code Review**
1. Review `cfbd_client.py` get_games() method - check if it requests postseason games
2. Review `import_real_data.py` - check if playoff games are in scope
3. Review `weekly_update.py` - check if it includes playoff game imports
4. Identify where code needs modification

**Step 4: Create Diagnostic Report**
1. Document all findings in `docs/diagnostics/playoff-games-investigation.md`
2. Include root cause analysis
3. Provide specific recommendations for Stories 2 and 3
4. Include example API calls and SQL queries for future reference

[Source: `docs/epics/epic-fix-playoff-games-import.md#Story 1`]

### Technical Constraints

- **Read-only investigation** - No database writes, no code changes in this story
- **Non-destructive queries** - Only SELECT queries, no modifications
- **Document findings clearly** - Diagnostic report must be detailed enough for implementation
- **Test API safely** - Use API calls that don't consume excessive quota

[Source: `docs/epics/epic-fix-playoff-games-import.md#Compatibility Requirements`]

### Testing Requirements

**Manual Verification:**
1. Run all diagnostic SQL queries against production database
2. Execute CFBD API test calls to verify playoff game structure
3. Review import scripts to confirm current behavior
4. Verify diagnostic report is comprehensive and actionable

**Validation Checklist:**
- [ ] Root cause clearly identified with evidence
- [ ] CFBD API structure fully documented
- [ ] List of games to fix/import is complete
- [ ] Recommendations are specific and actionable
- [ ] Diagnostic report created in docs/diagnostics/

[Source: `docs/epics/epic-fix-playoff-games-import.md#Story 1 Acceptance Criteria`]

---

## Tasks / Subtasks

1. **Run Database Diagnostic Queries** (20 minutes)
   - Query Week 16 games to identify 0-0 scores
   - Query games by date range (Dec 19-20) to check first-round games
   - Query games by season_type to check postseason vs regular season
   - Count playoff games vs expected 8 games (4 first-round + 4 quarterfinals)
   - Document current database state with evidence
   - (AC: 3)

2. **Test CFBD API for Playoff Games** (30 minutes)
   - Create test script to query CFBD API with `seasonType=postseason`
   - Test with different parameter combinations (week, division, etc.)
   - Document playoff-specific fields in API response (playoff_round, playoff_seed, etc.)
   - Save example API response for reference
   - Compare API data to database data to identify gaps
   - (AC: 2, 3)

3. **Review Import Code for Playoff Handling** (20 minutes)
   - Read `src/integrations/cfbd_client.py` get_games() method
   - Check if seasonType parameter is used or hardcoded to "regular"
   - Read `scripts/import_real_data.py` to check playoff game import logic
   - Read `scripts/weekly_update.py` to check if playoffs are included
   - Identify specific code locations that need modification
   - (AC: 1, 4)

4. **Analyze Root Cause** (15 minutes)
   - Compare database state, API data, and code behavior
   - Determine if issue is timing, API parameters, or week assignment
   - Document specific root cause with evidence from Steps 1-3
   - Identify whether existing games should be updated or deleted and re-imported
   - (AC: 1, 4)

5. **Create Diagnostic Report** (35 minutes)
   - Create `docs/diagnostics/playoff-games-investigation.md`
   - Document root cause with supporting evidence
   - Document CFBD API structure and required parameters
   - List all games needing import/fixing (4 first-round + 4 quarterfinals)
   - Provide recommendations for Stories 2 and 3 implementation approach
   - Include SQL queries, API examples, and code references
   - (AC: 1, 2, 3, 4, 5)

---

## Definition of Done

- [ ] All diagnostic SQL queries executed and results documented
- [ ] CFBD API playoff game structure tested and documented
- [ ] Import scripts reviewed and current behavior understood
- [ ] Root cause identified with supporting evidence
- [ ] List of games to fix/import created (8 games total)
- [ ] Diagnostic report created at `docs/diagnostics/playoff-games-investigation.md`
- [ ] Recommendations for Stories 2 and 3 documented
- [ ] All acceptance criteria met (AC 1-5)
- [ ] All integration verifications pass (IV1-IV3)
- [ ] No database or code changes made (investigation only)

---

## Rollback Plan

**Risk Level:** 🟢 Zero Risk (investigation only, no changes)

**Rollback Steps:**
1. Delete diagnostic report if needed: `rm docs/diagnostics/playoff-games-investigation.md`

**Rollback Impact:** None - investigation story, no system changes

---

## Notes

- This story sets the foundation for Stories 2 and 3
- Focus on thorough investigation over quick fixes
- Document everything clearly for future reference
- The diagnostic report becomes the blueprint for implementation
- This is a zero-risk story - perfect first step for the epic

---

**Related Documents:**
- Epic: `docs/epics/epic-fix-playoff-games-import.md`
- CFBD Client: `src/integrations/cfbd_client.py`
- Import Scripts: `scripts/import_real_data.py`, `scripts/weekly_update.py`
- Game Model: `src/models/models.py`
