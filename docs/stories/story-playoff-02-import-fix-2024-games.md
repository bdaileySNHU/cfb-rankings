# Story: Import and Fix 2024 Playoff Games - Brownfield Enhancement

**Status:** 📋 Draft
**Epic:** EPIC-FIX-PLAYOFF-GAMES
**Priority:** High
**Risk Level:** 🟡 Low Risk (data import with rollback plan)
**Estimated Effort:** 1-2 hours

---

## Story

As a **CFB ranking system user**, I want **all 2024 College Football Playoff games correctly imported with complete data**, so that **I can view accurate first-round playoff results and see quarterfinal matchups with proper placeholder handling for teams yet to be determined**.

---

## Acceptance Criteria

1. **All 4 first-round playoff games imported** (Dec 19-20, 2024):
   - 12 James Madison vs 5 Oregon (Dec 20)
   - 9 Alabama vs 8 Oklahoma (Dec 20)
   - 11 Tulane vs 6 Ole Miss (Dec 19)
   - 10 Miami vs 7 Texas A&M (Dec 19)
   - Each game has: correct teams, date, venue, seeds, and actual scores
   - Games properly marked as postseason/playoff games
   - No 0-0 scores for completed games

2. **All 4 quarterfinal games imported** with TBD opponent handling:
   - 4 Texas Tech vs Winner(12 JMU/5 Oregon)
   - Winner(9 Alabama/8 Oklahoma) vs 1 Indiana
   - Winner(11 Tulane/6 Ole Miss) vs 3 Georgia
   - Winner(10 Miami/7 Texas A&M) vs 2 Ohio State
   - TBD opponents handled appropriately (placeholder logic or awaiting results)
   - Games properly scheduled with correct dates

3. **Existing incomplete games updated** (if games exist with 0-0 scores):
   - Update in-place rather than creating duplicates
   - Verify no duplicate games created during import
   - Use UPDATE queries for existing games, INSERT for missing games

4. **Games properly categorized as playoff games**:
   - Week assignment appropriate for playoff games (not regular season weeks)
   - season_type field set to "postseason"
   - game_type or playoff_round fields populated if available
   - neutral_site set to true

5. **No regression in ranking system**:
   - Ranking calculations continue working correctly
   - Playoff games don't cause unexpected ranking changes
   - Games with TBD opponents excluded from rankings until both teams determined

---

## Integration Verification

- **IV1: Database Integrity** - No duplicate games created, existing games updated correctly
- **IV2: Ranking System Continuity** - Ranking calculations work unchanged, no errors from playoff games
- **IV3: Regular Season Unchanged** - Verify regular season game count and data unchanged by playoff import
- **IV4: API Compatibility** - Game API endpoints return playoff games correctly

---

## Dev Notes

### Previous Story Insights

**Story 1 Findings** (to be incorporated):
- Root cause of 0-0 scores identified
- CFBD API parameters for playoff games documented
- List of specific games to import/fix created
- Recommended approach for update vs insert strategy

This story implements the fixes based on Story 1's diagnostic report.

[Source: `docs/stories/story-playoff-01-diagnose-import-issues.md`, `docs/diagnostics/playoff-games-investigation.md`]

### Data Models

**Game Model** (from `src/models/models.py`):
```python
class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    home_team = Column(String, ForeignKey("teams.name"), nullable=False)
    away_team = Column(String, ForeignKey("teams.name"), nullable=False)
    home_points = Column(Integer, nullable=True)
    away_points = Column(Integer, nullable=True)
    game_date = Column(Date, nullable=True)
    neutral_site = Column(Boolean, default=False)

    # Playoff fields (check if these exist from Story 1 investigation):
    season_type = Column(String, nullable=True)  # "postseason" or "regular"
    game_type = Column(String, nullable=True)    # "playoff", "bowl", etc.
    playoff_round = Column(String, nullable=True) # "first_round", "quarterfinals", etc.
    postseason_name = Column(String, nullable=True) # "College Football Playoff"
```

**Database Operations:**
- **Update existing games**: `UPDATE games SET home_points=X, away_points=Y WHERE id=Z`
- **Insert new games**: Use SQLAlchemy ORM `db.add(game)` or bulk insert
- **Check for duplicates**: Query by (season, home_team, away_team, game_date) before insert

[Source: `src/models/models.py`, Story 1 findings]

### API Specifications

**CFBD API Parameters for Playoff Games:**
```python
client.get_games(
    season=2024,
    season_type="postseason",  # KEY: Use "postseason" not "regular"
    week=None,  # Playoff games may not have week numbers
    division="fbs"
)
```

**Expected API Response Fields:**
```json
{
  "id": 401628529,
  "season": 2024,
  "week": null,
  "season_type": "postseason",
  "home_team": "Oregon",
  "away_team": "James Madison",
  "home_points": 31,
  "away_points": 24,
  "game_date": "2024-12-20",
  "neutral_site": true,
  "playoff_round": "first_round",
  "home_playoff_seed": 5,
  "away_playoff_seed": 12
}
```

[Source: CFBD API documentation, Story 1 findings]

### File Locations

**Files to Modify:**
- `src/integrations/cfbd_client.py` - Enhance get_games() to support season_type parameter
- `scripts/import_real_data.py` - Add playoff game import logic OR create separate playoff import script

**Option 1: Modify Existing Import Script**
- Add playoff game import to `import_real_data.py`
- Use existing patterns for game creation

**Option 2: Create Standalone Script**
- Create `scripts/import_playoff_games.py`
- Focused script for one-time playoff import
- Can be integrated into main import later

**Recommended**: Use Option 2 for this story (standalone script), then integrate into main import in Story 3.

[Source: `docs/epics/epic-fix-playoff-games-import.md#Files Likely to Modify`]

### Import Strategy

**Based on Story 1 Findings, use one of:**

**Strategy A: Update Existing Games**
```python
# For games that exist with 0-0 scores
existing_game = db.query(Game).filter(
    Game.season == 2024,
    Game.home_team == "Oregon",
    Game.away_team == "James Madison"
).first()

if existing_game:
    existing_game.home_points = api_data["home_points"]
    existing_game.away_points = api_data["away_points"]
    existing_game.season_type = "postseason"
    existing_game.playoff_round = "first_round"
    db.commit()
```

**Strategy B: Delete and Re-import**
```python
# Delete existing playoff games
db.query(Game).filter(
    Game.season == 2024,
    Game.game_date >= "2024-12-19",
    Game.game_date <= "2024-12-31"
).delete()

# Re-import from CFBD API
# (safer if data is corrupted)
```

**TBD Opponent Handling:**
```python
# Option 1: Skip quarterfinals until first round complete
if not all_first_round_complete:
    logger.info("Skipping quarterfinal import - first round not complete")

# Option 2: Import with placeholder teams
game.home_team = "TBD (Winner JMU/Oregon)"
game.away_team = "Texas Tech"
# Exclude from rankings until updated
```

[Source: Story 1 recommendations]

### Technical Constraints

- **No breaking changes** - Existing game import functionality must continue working
- **No duplicate games** - Check for existing games before insert
- **Proper playoff categorization** - Use correct season_type, game_type, playoff_round
- **TBD handling** - Don't break ranking calculations with incomplete matchups
- **Database integrity** - Use transactions, rollback on error

[Source: `docs/epics/epic-fix-playoff-games-import.md#Compatibility Requirements`]

### Testing Requirements

**Unit Tests:**
- Test playoff game fetching from CFBD API
- Test update vs insert logic (no duplicates)
- Test TBD opponent handling
- Test playoff game field population

**Integration Tests:**
- Test playoff game import end-to-end
- Test ranking system with playoff games
- Test API endpoints return playoff games

**Manual Verification:**
```sql
-- Verify all 8 playoff games exist
SELECT COUNT(*) FROM games
WHERE season = 2024 AND season_type = 'postseason';
-- Expected: 8 (or 4 if only first-round imported)

-- Verify first-round games have scores
SELECT home_team, away_team, home_points, away_points, game_date
FROM games
WHERE season = 2024
  AND game_date BETWEEN '2024-12-19' AND '2024-12-20'
ORDER BY game_date;
-- Expected: 4 games with actual scores (not 0-0)

-- Check for duplicates
SELECT home_team, away_team, game_date, COUNT(*)
FROM games
WHERE season = 2024 AND season_type = 'postseason'
GROUP BY home_team, away_team, game_date
HAVING COUNT(*) > 1;
-- Expected: 0 duplicates
```

[Source: `docs/epics/epic-fix-playoff-games-import.md#Acceptance Testing`]

---

## Tasks / Subtasks

1. **Create Playoff Game Import Script** (30 minutes)
   - Create `scripts/import_playoff_games.py`
   - Add CFBD API client initialization
   - Add command-line arguments (--season, --dry-run, --update-existing)
   - Add logging setup
   - (AC: 1, 2)

2. **Implement First-Round Game Import** (20 minutes)
   - Fetch first-round playoff games from CFBD API with `season_type="postseason"`
   - Parse API response for 4 first-round games (Dec 19-20)
   - Check for existing games with same teams and date
   - Update existing games or insert new games
   - Populate playoff-specific fields (season_type, playoff_round, neutral_site)
   - Add transaction handling with rollback on error
   - (AC: 1, 3, 4)

3. **Implement Quarterfinal Game Import** (20 minutes)
   - Fetch quarterfinal games from CFBD API
   - Handle TBD opponents (skip import or use placeholder logic per Story 1 recommendation)
   - Insert quarterfinal games with proper dates and known teams
   - Mark games as excluded from rankings if TBD opponents present
   - (AC: 2, 4, 5)

4. **Add Import Validation** (15 minutes)
   - Check no duplicate games created
   - Verify game count matches expected (8 games or 4 if quarterfinals skipped)
   - Verify no 0-0 scores for completed first-round games
   - Log summary of games imported/updated
   - (AC: 1, 2, 3)

5. **Test Import Script** (20 minutes)
   - Run with --dry-run flag first to preview changes
   - Execute import against test database
   - Verify all 4 first-round games imported correctly
   - Verify quarterfinals handled correctly (imported or skipped per strategy)
   - Check no duplicates created
   - (AC: 1, 2, 3, 4)

6. **Verify Ranking System Compatibility** (10 minutes)
   - Run ranking calculations with playoff games present
   - Verify no errors or unexpected ranking changes
   - Verify TBD games excluded from rankings
   - Test API endpoints return playoff games correctly
   - (AC: 5, IV2, IV4)

7. **Execute Production Import and Verify** (15 minutes)
   - Backup database before import: `cp cfb_rankings.db cfb_rankings.db.backup_playoff_fix`
   - Run import script against production database
   - Execute verification SQL queries from Testing Requirements
   - Verify via API or UI that playoff games display correctly
   - Document import results
   - Commit with message: "Import and fix 2024 playoff games (Story playoff-02)"
   - (AC: 1-5, IV1-IV4)

---

## Definition of Done

- [ ] Playoff game import script created (`scripts/import_playoff_games.py`)
- [ ] All 4 first-round games imported with complete data
- [ ] All 4 quarterfinal games handled appropriately (imported or marked as pending)
- [ ] No duplicate games created
- [ ] Existing 0-0 games updated with correct scores
- [ ] Games properly categorized as postseason/playoff games
- [ ] No regression in ranking calculations
- [ ] Database backup created before import
- [ ] Verification SQL queries pass
- [ ] All acceptance criteria met (AC 1-5)
- [ ] All integration verifications pass (IV1-IV4)
- [ ] Changes committed with proper message

---

## Rollback Plan

**Risk Level:** 🟡 Low Risk (data import with backup)

**Rollback Steps:**
```bash
# 1. Restore database from backup
cp cfb_rankings.db.backup_playoff_fix cfb_rankings.db

# OR use SQL to delete imported games
sqlite3 cfb_rankings.db "DELETE FROM games WHERE season = 2024 AND season_type = 'postseason';"

# OR delete by date range
sqlite3 cfb_rankings.db "DELETE FROM games WHERE season = 2024 AND game_date >= '2024-12-19';"
```

**Rollback Impact:**
- Removes playoff games, returns to state before Story 2
- No impact on regular season games
- Ranking calculations return to pre-import state

**Rollback Verification:**
```sql
-- Verify playoff games removed
SELECT COUNT(*) FROM games WHERE season = 2024 AND season_type = 'postseason';
-- Expected: 0

-- Verify regular season games intact
SELECT COUNT(*) FROM games WHERE season = 2024 AND week <= 15;
-- Expected: Same count as before import
```

[Source: `docs/epics/epic-fix-playoff-games-import.md#Risk Mitigation`]

---

## Notes

- This story delivers immediate value (complete 2024 playoff data)
- Focus on correctness over automation (Story 3 handles future seasons)
- Backup database before running import
- Use --dry-run flag to preview changes before executing
- Story 3 will integrate this logic into regular import workflow
- Consider running import script manually first time for verification

---

**Related Documents:**
- Epic: `docs/epics/epic-fix-playoff-games-import.md`
- Story 1: `docs/stories/story-playoff-01-diagnose-import-issues.md`
- Diagnostic Report: `docs/diagnostics/playoff-games-investigation.md` (from Story 1)
- CFBD Client: `src/integrations/cfbd_client.py`
- Import Scripts: `scripts/import_real_data.py`
