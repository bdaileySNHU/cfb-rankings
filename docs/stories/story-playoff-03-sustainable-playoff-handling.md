# Story: Implement Sustainable Playoff Game Handling - Brownfield Enhancement

**Status:** 📋 Draft
**Epic:** EPIC-FIX-PLAYOFF-GAMES
**Priority:** High
**Risk Level:** 🟡 Medium Risk (modifies import automation)
**Estimated Effort:** 2-3 hours

---

## Story

As a **system administrator**, I want **playoff games to be automatically imported in future seasons without manual intervention**, so that **the 2025 and beyond playoff seasons are handled correctly from day one, including first-round games, quarterfinals with TBD opponents, and proper postseason categorization**.

---

## Acceptance Criteria

1. **CFBD client enhanced to fetch playoff games**:
   - `get_games()` method supports `season_type` parameter ("regular" or "postseason")
   - Method properly handles playoff-specific API fields (playoff_round, playoff_seed, etc.)
   - Method returns playoff games with correct metadata

2. **Import script distinguishes playoff games from regular season**:
   - `import_real_data.py` updated to import both regular season AND postseason games
   - Playoff games assigned to appropriate week or postseason category (not regular season weeks)
   - Playoff games properly marked with season_type="postseason"

3. **TBD opponent handling implemented**:
   - System can import quarterfinal games before first-round completes
   - Games with TBD opponents stored with placeholder logic or skipped until determined
   - TBD games excluded from ranking calculations
   - Logic to update TBD games when matchups finalized

4. **Weekly update script includes playoff games**:
   - `weekly_update.py` updated to import playoff games during active playoff season
   - Playoff import timing configured (e.g., after Selection Sunday)
   - Weekly updates check for playoff games and import incrementally

5. **Future-season readiness verified**:
   - Configuration allows playoff import to work for any season (2025+)
   - Manual test demonstrates 2025 playoff structure will work
   - Documentation updated with playoff handling approach

6. **No regression in regular season handling**:
   - Regular season game imports continue working unchanged
   - Existing game data unaffected
   - Ranking calculations work correctly with both regular and postseason games

---

## Integration Verification

- **IV1: Regular Season Continuity** - Regular season imports work unchanged, no regressions
- **IV2: Weekly Update Automation** - Weekly update script successfully imports playoff games
- **IV3: Ranking System Compatibility** - Rankings handle playoff games correctly, TBD games excluded
- **IV4: API Compatibility** - Game API endpoints distinguish and return playoff games correctly
- **IV5: Future Season Readiness** - Configuration allows 2025+ playoffs to import automatically

---

## Dev Notes

### Previous Story Insights

**Story 1 Findings:**
- Root cause identified (API parameters, week assignment)
- CFBD API structure documented
- Recommendations for sustainable implementation

**Story 2 Implementation:**
- 2024 playoff games successfully imported
- Import script pattern established
- TBD opponent handling approach tested

**Integration Approach:**
- Merge Story 2's standalone import script logic into main import workflow
- Extend CFBD client with season_type parameter support
- Update weekly automation to include playoff games

[Source: `docs/stories/story-playoff-01-diagnose-import-issues.md`, `docs/stories/story-playoff-02-import-fix-2024-games.md`]

### Data Models

**Game Model Extensions** (if needed):
```python
class Game(Base):
    # ... existing fields ...

    # Ensure these playoff fields exist (add if missing):
    season_type = Column(String, nullable=True, default="regular")
    playoff_round = Column(String, nullable=True)  # first_round, quarterfinals, semifinals, championship
    postseason_name = Column(String, nullable=True)  # "College Football Playoff"
    playoff_seed_home = Column(Integer, nullable=True)
    playoff_seed_away = Column(Integer, nullable=True)
```

**Database Migration** (if fields added):
```python
# migration script: add playoff fields if not present
ALTER TABLE games ADD COLUMN season_type TEXT DEFAULT 'regular';
ALTER TABLE games ADD COLUMN playoff_round TEXT;
ALTER TABLE games ADD COLUMN postseason_name TEXT;
ALTER TABLE games ADD COLUMN playoff_seed_home INTEGER;
ALTER TABLE games ADD COLUMN playoff_seed_away INTEGER;
```

[Source: `src/models/models.py`, CFBD API schema]

### API Specifications

**Enhanced CFBD Client Method:**
```python
def get_games(
    self,
    season: int,
    season_type: str = "regular",  # NEW: "regular" or "postseason"
    week: Optional[int] = None,
    team: Optional[str] = None,
    division: str = "fbs"
) -> List[Dict]:
    """
    Fetch games from CFBD API.

    Args:
        season: Year (e.g., 2024)
        season_type: "regular" or "postseason" (NEW)
        week: Week number (1-15 for regular, None for postseason)
        team: Filter by team name
        division: "fbs" or "fcs"

    Returns:
        List of game dictionaries with playoff fields if applicable
    """
    params = {
        "year": season,
        "seasonType": season_type,  # NEW
        "division": division
    }

    if week is not None:
        params["week"] = week

    # ... API call logic ...
```

**Game Import Logic Enhancement:**
```python
def import_games(season: int, db: Session):
    client = CFBDClient()

    # Import regular season games (existing logic)
    for week in range(1, 16):
        regular_games = client.get_games(season, season_type="regular", week=week)
        # ... existing import logic ...

    # NEW: Import postseason games
    postseason_games = client.get_games(season, season_type="postseason")
    for game_data in postseason_games:
        # Handle playoff-specific fields
        game = Game(
            season=season,
            season_type="postseason",
            playoff_round=game_data.get("playoff_round"),
            postseason_name=game_data.get("notes"),  # or specific playoff field
            # ... other fields ...
        )

        # Check for TBD opponents
        if "TBD" in game.home_team or "TBD" in game.away_team:
            game.exclude_from_rankings = True  # or skip import

        db.add(game)
    db.commit()
```

[Source: `src/integrations/cfbd_client.py`, Story 2 implementation]

### File Locations

**Files to Modify:**

1. **`src/integrations/cfbd_client.py`** (Primary changes)
   - Add `season_type` parameter to `get_games()` method
   - Update API call to include `seasonType` parameter
   - Parse playoff-specific response fields

2. **`scripts/import_real_data.py`** (Integration)
   - Merge Story 2's playoff import logic into main import
   - Add postseason game import section
   - Add TBD opponent handling logic

3. **`scripts/weekly_update.py`** (Automation)
   - Add playoff game import during active playoff season (Dec-Jan)
   - Add configuration for playoff import timing
   - Ensure incremental updates include playoff games

4. **`src/models/models.py`** (If fields missing)
   - Add playoff metadata fields to Game model
   - Create migration script if schema changes needed

5. **Documentation Updates:**
   - Update `docs/architecture.md` or relevant docs with playoff handling
   - Document CFBD API playoff parameters
   - Add playoff import process to operational docs

[Source: `docs/epics/epic-fix-playoff-games-import.md#Files Likely to Modify`]

### Playoff Import Timing Strategy

**When to Import Playoff Games:**

1. **After Selection Sunday** (around Week 15):
   - Import playoff bracket structure (all 8 games)
   - First-round games will have teams assigned
   - Quarterfinals will have TBD opponents

2. **After First-Round Completion** (around Dec 21):
   - Update quarterfinal games with determined matchups
   - Update TBD placeholders with actual teams

3. **Incremental Weekly Updates** (during playoffs):
   - Check for score updates on first-round games
   - Check for quarterfinal matchup determination
   - Import semifinal and championship games as they're scheduled

**Configuration Approach:**
```python
# In weekly_update.py or config
PLAYOFF_IMPORT_CONFIG = {
    "start_week": 15,  # Begin checking for playoffs after Week 15
    "start_month": 12,  # December
    "end_month": 1,     # January
    "import_on_weeks": [15, 16],  # Check for playoffs on these weeks
}
```

[Source: `docs/epics/epic-fix-playoff-games-import.md#Story 3`]

### TBD Opponent Handling Strategy

**Option A: Skip TBD Games Until Determined**
```python
if "TBD" in home_team or "Winner" in home_team:
    logger.info(f"Skipping game with TBD opponent: {home_team} vs {away_team}")
    continue
```

**Option B: Import with Placeholder and Update Later**
```python
game = Game(
    home_team=game_data.get("home_team", "TBD"),  # May be "TBD" or "Winner(...)"
    away_team=game_data.get("away_team"),
    exclude_from_rankings=True,  # Don't include in ELO calculations
    status="pending_matchup"
)
```

**Recommended**: Use Option B - import with placeholders, exclude from rankings, update when determined.

[Source: `docs/epics/epic-fix-playoff-games-import.md#What's being added/changed`]

### Technical Constraints

- **Backward compatibility** - Regular season imports must work unchanged
- **No breaking changes** - Game model additions must be additive (nullable fields)
- **TBD exclusion** - Games with undetermined opponents must not affect rankings
- **Incremental updates** - Weekly update logic must handle playoff games incrementally
- **API efficiency** - Minimize API calls (cache playoff games, don't re-fetch completed games)

[Source: `docs/epics/epic-fix-playoff-games-import.md#Compatibility Requirements`]

### Testing Requirements

**Unit Tests:**
```python
# Test CFBD client season_type parameter
def test_get_games_with_postseason_type():
    client = CFBDClient()
    games = client.get_games(2024, season_type="postseason")
    assert all(g.get("season_type") == "postseason" for g in games)

# Test TBD opponent handling
def test_import_skips_tbd_games():
    # Mock game with TBD opponent
    game_data = {"home_team": "TBD", "away_team": "Georgia"}
    result = import_game(game_data, db)
    assert result.exclude_from_rankings == True

# Test playoff field population
def test_playoff_game_fields_populated():
    game = import_playoff_game(playoff_game_data, db)
    assert game.season_type == "postseason"
    assert game.playoff_round == "first_round"
```

**Integration Tests:**
```python
# Test end-to-end playoff import
def test_import_2024_playoff_games():
    import_real_data(season=2024, postseason=True)
    playoff_games = db.query(Game).filter(
        Game.season == 2024,
        Game.season_type == "postseason"
    ).all()
    assert len(playoff_games) >= 4  # At least first-round games
```

**Manual Verification:**
```sql
-- Verify playoff games imported for 2024
SELECT COUNT(*), playoff_round
FROM games
WHERE season = 2024 AND season_type = 'postseason'
GROUP BY playoff_round;
-- Expected: 4 first_round, 4 quarterfinals (or fewer if TBD skipped)

-- Verify TBD games excluded from rankings
SELECT home_team, away_team, exclude_from_rankings
FROM games
WHERE (home_team LIKE '%TBD%' OR away_team LIKE '%TBD%')
  AND season = 2024;
-- Expected: All TBD games have exclude_from_rankings = true

-- Verify regular season games unaffected
SELECT COUNT(*)
FROM games
WHERE season = 2024 AND season_type = 'regular';
-- Expected: Same count as before Story 3
```

[Source: `docs/epics/epic-fix-playoff-games-import.md#Acceptance Testing`]

### Configuration and Documentation Updates

**Documentation to Update:**

1. **CFBD API Usage** (new or update existing):
   - Document `season_type` parameter usage
   - Document playoff-specific response fields
   - Include example API calls for playoff games

2. **Import Process Documentation**:
   - Document when playoff games are imported (timing)
   - Document TBD opponent handling approach
   - Document how to manually trigger playoff import if needed

3. **Operational Runbook** (if exists):
   - Add playoff game troubleshooting section
   - Document how to verify playoff games imported correctly
   - Add SQL queries for playoff game verification

[Source: `docs/epics/epic-fix-playoff-games-import.md#Definition of Done`]

---

## Tasks / Subtasks

1. **Enhance CFBD Client for Playoff Games** (30 minutes)
   - Add `season_type` parameter to `get_games()` method in `cfbd_client.py`
   - Update API request to include `seasonType` parameter
   - Parse playoff-specific response fields (playoff_round, playoff_seed, etc.)
   - Add unit tests for season_type parameter
   - (AC: 1)

2. **Update Game Model for Playoff Fields** (20 minutes - if needed)
   - Check if Game model has playoff fields (season_type, playoff_round, etc.)
   - Add missing fields as nullable columns
   - Create database migration script if schema changes needed
   - Run migration against test database
   - (AC: 1, 2)

3. **Integrate Playoff Import into Main Import Script** (40 minutes)
   - Merge Story 2's playoff import logic into `import_real_data.py`
   - Add postseason game import section after regular season import
   - Implement TBD opponent handling (skip or placeholder with exclude flag)
   - Add logic to detect and handle duplicate playoff games
   - Add configuration for playoff import (enable/disable, timing)
   - (AC: 2, 3, 6)

4. **Update Weekly Update Script for Playoff Automation** (30 minutes)
   - Modify `weekly_update.py` to import playoff games during Dec-Jan
   - Add playoff import timing configuration (start after Week 15)
   - Ensure incremental updates handle playoff games correctly
   - Add logging for playoff game import status
   - Test weekly update with playoff games
   - (AC: 4, 6)

5. **Implement Tests for Playoff Handling** (30 minutes)
   - Add unit tests for CFBD client season_type parameter
   - Add unit tests for TBD opponent handling
   - Add integration test for end-to-end playoff import
   - Add test for ranking system with playoff games (no errors)
   - Verify all tests pass
   - (AC: 1, 2, 3, 6, IV3)

6. **Verify Future Season Readiness** (20 minutes)
   - Test import with mock 2025 playoff data
   - Verify configuration allows any season year
   - Verify playoff structure works for 12-team format
   - Document any season-specific assumptions or limitations
   - (AC: 5, IV5)

7. **Update Documentation** (25 minutes)
   - Document playoff handling in architecture docs or README
   - Add CFBD API playoff parameters to API documentation
   - Document TBD opponent handling approach
   - Add operational runbook section for playoff troubleshooting
   - Update any developer guides with playoff import process
   - (AC: 5)

8. **Integration Testing and Verification** (25 minutes)
   - Run full import for 2024 season including playoffs
   - Verify regular season games unchanged (IV1, IV6)
   - Verify playoff games imported correctly
   - Test ranking calculations with playoff games (IV3)
   - Test API endpoints return playoff games (IV4)
   - Execute verification SQL queries from Testing Requirements
   - Commit with message: "Implement sustainable playoff game handling (Story playoff-03)"
   - (AC: 1-6, IV1-IV5)

---

## Definition of Done

- [ ] CFBD client supports season_type parameter for playoff games
- [ ] Game model has playoff metadata fields (if missing, migration created)
- [ ] Main import script includes playoff game import logic
- [ ] TBD opponent handling implemented (skip or placeholder with exclusion)
- [ ] Weekly update script includes playoff games during active season
- [ ] Playoff import timing configured (after Week 15/Selection Sunday)
- [ ] All tests pass (unit, integration for playoff handling)
- [ ] Regular season imports verified working unchanged
- [ ] 2025 playoff readiness verified (configuration allows future seasons)
- [ ] Documentation updated (playoff handling, CFBD API, operational runbook)
- [ ] All acceptance criteria met (AC 1-6)
- [ ] All integration verifications pass (IV1-IV5)
- [ ] Changes committed with proper message

---

## Rollback Plan

**Risk Level:** 🟡 Medium Risk (modifies import automation)

**Rollback Steps:**
```bash
# 1. Revert code changes
git revert <commit-hash>

# 2. If database migration was run, rollback migration
# (migration script should have down() method)
python -m alembic downgrade -1

# 3. Verify regular season imports still work
python scripts/import_real_data.py --season 2024

# 4. Verify no playoff games in database (if full rollback desired)
sqlite3 cfb_rankings.db "DELETE FROM games WHERE season_type = 'postseason';"
```

**Rollback Impact:**
- Removes playoff game import automation
- Playoff games imported in Story 2 can remain (data rollback optional)
- Regular season imports will continue working
- Weekly updates will not import playoff games

**Rollback Verification:**
```bash
# Verify code reverted
git log -1

# Verify regular season import works
python scripts/import_real_data.py --season 2024 --dry-run

# Verify weekly update works
python scripts/weekly_update.py
```

[Source: `docs/epics/epic-fix-playoff-games-import.md#Risk Mitigation`]

---

## Notes

- This story completes the epic by making playoff handling automatic
- Focus on maintainability - code should work for 2025+ without changes
- Thorough testing is critical - this modifies core import automation
- Consider running against test database first before production
- Story 2 already imported 2024 playoff data, this makes it sustainable
- TBD opponent handling is key for quarterfinals before first-round completes

---

**Related Documents:**
- Epic: `docs/epics/epic-fix-playoff-games-import.md`
- Story 1: `docs/stories/story-playoff-01-diagnose-import-issues.md`
- Story 2: `docs/stories/story-playoff-02-import-fix-2024-games.md`
- CFBD Client: `src/integrations/cfbd_client.py`
- Import Scripts: `scripts/import_real_data.py`, `scripts/weekly_update.py`
- Game Model: `src/models/models.py`
