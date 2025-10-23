# EPIC-008: Future Game Imports for Predictions Feature

## Epic Goal

Enable the import of scheduled/future games (without scores yet) into the database so that the predictions feature (EPIC-007) can generate predictions for upcoming quality matchups, not just leftover FBS vs FCS games.

## Epic Overview

**Priority:** High
**Estimated Total Effort:** 6-9 hours
**Status:** Ready for Development
**Type:** Bug Fix / Feature Enhancement
**Blocks:** EPIC-007 (Game Predictions) full functionality

---

## Problem Statement

The predictions feature (EPIC-007) was recently completed and is functional, but it has a critical data availability issue:

**Current Behavior:**
- `import_real_data.py` (line ~254): `if home_score is None or away_score is None: continue`
- This logic **completely skips** all games without scores
- Future/scheduled games are **never imported** into the database
- The `Game` table only contains completed games with final scores

**Impact:**
- Predictions feature only works on leftover FBS vs FCS games that never received scores
- Users cannot see predictions for upcoming ranked matchups (the most valuable predictions)
- The predictions feature appears broken or useless to end users
- Business value of EPIC-007 is not realized

**Why This Matters:**
- Users want to see predictions for **next week's Top 25 matchups** (e.g., Alabama vs Georgia)
- Currently, predictions only show obscure FBS vs FCS games that were scheduled but canceled
- This makes the predictions feature essentially non-functional for its intended purpose
- The feature was built assuming future games would be in the database

---

## Epic Description

### Existing System Context

**Current functionality:**
- Weekly data import from CollegeFootballData (CFBD) API via `import_real_data.py`
- CFBD API provides both completed games (with scores) and scheduled games (no scores yet)
- Database has `Game.is_processed` flag to distinguish processed vs unprocessed games
- ELO ratings are only calculated for processed games (EPIC-001)
- Predictions feature (EPIC-007) queries unprocessed games (`is_processed = False`)

**Technology stack:**
- Backend: Python 3, FastAPI, SQLAlchemy ORM
- Database: SQLite with `Game`, `Team`, `Season` models
- Data source: CFBD API (provides scheduled games with dates but null scores)
- Import script: `import_real_data.py` (runs weekly to update database)

**Integration points:**
- Database: `Game` model (has `is_processed` flag, scores can be nullable or defaulted)
- Import script: `import_real_data.py` (needs modification to import future games)
- CFBD API: Already provides future games (we just skip them currently)
- Predictions API: Already designed to use `is_processed = False` games (no changes needed)
- ELO processing: Must NOT process future games for rankings (prevent corruption)

### Enhancement Details

**What's being added/changed:**
1. **Modify import logic** to import future/scheduled games:
   - Remove the skip condition for games without scores
   - Set `home_score = 0` and `away_score = 0` for future games (placeholder values)
   - Set `is_processed = False` for future games (prevents ELO calculation)
   - Set `excluded_from_rankings = True` initially (optional safety measure)

2. **Add update logic** for when scores become available:
   - Implement upsert logic (INSERT if new, UPDATE if exists)
   - When re-importing data, check if game already exists by unique key
   - If game exists with scores = 0 and new data has real scores, UPDATE the game
   - After updating scores, set `is_processed = False` to trigger ELO recalculation
   - Ensure no duplicate games are created

3. **Preserve data integrity:**
   - Do NOT process future games for ELO (would corrupt rankings)
   - Do NOT create duplicate games when scores become available
   - Do NOT lose historical game data during updates
   - Maintain existing behavior for completed games

**How it integrates:**
- Predictions feature (EPIC-007) already queries `is_processed = False` games
- No changes needed to predictions API or frontend
- ELO processing logic remains unchanged (only processes `is_processed = False` after scores added)
- Weekly import script becomes idempotent (can run multiple times safely)
- Database schema has all necessary fields (no migrations needed)

**Success criteria:**
- Future games are imported with `is_processed = False` and scores = 0
- Predictions feature shows upcoming Top 25 matchups
- When scores become available, games are updated (not duplicated)
- ELO rankings are only calculated after scores are imported
- No existing functionality is broken (completed games still import correctly)
- Weekly import script can run multiple times without creating duplicates

---

## Stories

### Story 001: Modify Import Logic to Import Future Games

**Goal:** Change `import_real_data.py` to import scheduled games without scores

**Estimated Effort:** 2-3 hours

**Key Tasks:**
- Remove or modify the skip condition for games without scores
- Add logic to detect future games (no scores yet)
- Set default scores (0-0) for future games
- Set `is_processed = False` for future games
- Optionally set `excluded_from_rankings = True` for safety
- Preserve existing behavior for completed games
- Add logging to distinguish future vs completed game imports

**Deliverables:**
- Modified `import_games()` function in `import_real_data.py`
- Future games imported with placeholder data
- Import summary shows count of future games imported
- Manual test: Run import and verify future games in database

---

### Story 002: Add Update Logic for When Scores Become Available

**Goal:** Implement upsert logic to update existing games when scores are added

**Estimated Effort:** 2-3 hours

**Key Tasks:**
- Define unique game identifier (home_team_id, away_team_id, week, season)
- Before inserting game, check if it already exists
- If exists and has scores = 0, update with new scores
- If exists with real scores, skip (already processed)
- If doesn't exist, insert new game
- After updating scores, reset `is_processed = False` to trigger ELO
- Add logging for updates vs inserts
- Ensure no duplicate games are created

**Deliverables:**
- Upsert logic in `import_games()` function
- Games update correctly when scores become available
- No duplicate games in database
- Import summary shows count of updated games
- Manual test: Import week twice, verify no duplicates

---

### Story 003: Testing, Validation, and Documentation

**Goal:** Ensure import changes work correctly and are well-documented

**Estimated Effort:** 2-3 hours

**Key Tasks:**
- Add validation to prevent duplicate games
- Test import with future games (no scores)
- Test update when scores become available
- Test that ELO is NOT calculated for future games
- Test that predictions API returns future games
- Verify no regression in existing import functionality
- Update import script documentation
- Document import workflow in developer docs
- Add comments explaining future game logic

**Deliverables:**
- Validation prevents duplicate games
- Manual testing confirms all scenarios work
- Integration test for future game import (optional)
- Updated README or developer documentation
- Code comments explaining logic

---

## Compatibility Requirements

- [x] Existing database schema supports future games (no migrations needed)
- [x] Existing predictions API already queries `is_processed = False` (no changes needed)
- [x] ELO processing logic unchanged (only processes games with real scores)
- [x] Existing import behavior for completed games preserved
- [x] No breaking changes to API or frontend

---

## Risk Assessment

### Primary Risks

1. **Duplicate games created during updates**
   - **Mitigation:** Implement unique constraint check before insert
   - **Mitigation:** Use upsert logic (check exists, then update or insert)
   - **Rollback:** Delete duplicate games manually, fix import script, re-run

2. **ELO corruption if future games are accidentally processed**
   - **Mitigation:** Ensure `is_processed = False` for all future games
   - **Mitigation:** Add validation in ELO processing to check for real scores (> 0)
   - **Mitigation:** Set `excluded_from_rankings = True` as extra safety
   - **Rollback:** Reset database from backup, fix import logic, re-import

3. **Import script breaks for completed games**
   - **Mitigation:** Preserve existing logic path for completed games
   - **Mitigation:** Test with historical data before deploying
   - **Rollback:** Revert `import_real_data.py` to previous version, re-import

4. **Future games without dates cause frontend errors**
   - **Mitigation:** CFBD API provides game dates for scheduled games
   - **Mitigation:** Frontend already handles null dates gracefully (EPIC-007)
   - **Note:** This is unlikely as CFBD provides dates for scheduled games

5. **Weekly re-imports create data churn**
   - **Mitigation:** Upsert logic prevents duplicates
   - **Mitigation:** Only update games when scores change from 0 to real values
   - **Impact:** Minimal - database writes are inexpensive for small dataset

### Rollback Plan

```bash
# If import script causes issues:

# 1. Revert import_real_data.py to previous version
git checkout HEAD~1 import_real_data.py

# 2. Delete any future games (if needed)
# In Python shell:
from database import SessionLocal
from models import Game
db = SessionLocal()
db.query(Game).filter(Game.home_score == 0, Game.away_score == 0).delete()
db.commit()

# 3. Re-import clean data
python3 import_real_data.py --season 2025

# 4. Verify predictions API works
curl http://localhost:8000/api/predictions | jq
```

---

## Definition of Done

- [ ] Story 001: Future games imported with `is_processed = False` and scores = 0
- [ ] Story 001: Import summary shows count of future games
- [ ] Story 002: Upsert logic prevents duplicate games
- [ ] Story 002: Games update correctly when scores become available
- [ ] Story 002: Import can run multiple times without duplicates
- [ ] Story 003: Validation prevents duplicate games
- [ ] Story 003: Manual testing confirms all scenarios
- [ ] Story 003: Documentation updated
- [ ] Predictions API shows upcoming Top 25 matchups
- [ ] ELO rankings not corrupted by future games
- [ ] No regression in existing import functionality
- [ ] Weekly import script is idempotent (safe to re-run)

---

## Technical Approach

### Current Problem (import_real_data.py lines 244-258)

```python
for game_data in games_data:
    # API uses camelCase
    home_team_name = game_data.get('homeTeam')
    away_team_name = game_data.get('awayTeam')
    home_score = game_data.get('homePoints')
    away_score = game_data.get('awayPoints')

    game_desc = f"{away_team_name} @ {home_team_name}"

    # Skip if game not completed
    if home_score is None or away_score is None:
        week_skipped += 1
        skipped_incomplete += 1
        skipped_details.append((week, "Game not completed", game_desc))
        continue  # <-- THIS IS THE PROBLEM
```

### Proposed Solution (Story 001)

```python
for game_data in games_data:
    # API uses camelCase
    home_team_name = game_data.get('homeTeam')
    away_team_name = game_data.get('awayTeam')
    home_score = game_data.get('homePoints')
    away_score = game_data.get('awayPoints')

    game_desc = f"{away_team_name} @ {home_team_name}"

    # Detect future games (no scores yet)
    is_future_game = home_score is None or away_score is None

    if is_future_game:
        # Import with placeholder scores
        home_score = 0
        away_score = 0
        is_processed = False
        excluded_from_rankings = True  # Extra safety
        print(f"    Importing future game: {game_desc}")
    else:
        # Completed game - normal processing
        is_processed = False  # Will be set to True after ELO processing
        excluded_from_rankings = is_fcs_game  # Existing logic

    # Continue with rest of import logic...
```

### Proposed Solution (Story 002)

```python
# Check if game already exists (upsert logic)
existing_game = db.query(Game).filter(
    Game.home_team_id == home_team.id,
    Game.away_team_id == away_team.id,
    Game.week == week,
    Game.season == year
).first()

if existing_game:
    # Game exists - check if we need to update it
    if existing_game.home_score == 0 and existing_game.away_score == 0:
        # Future game now has scores - update it
        if not is_future_game:
            existing_game.home_score = home_score
            existing_game.away_score = away_score
            existing_game.is_processed = False  # Will trigger ELO processing
            existing_game.excluded_from_rankings = is_fcs_game
            db.commit()
            print(f"    Updated game: {game_desc} -> {home_score}-{away_score}")
            week_updated += 1
            total_updated += 1
    # else: game already has scores, skip
    continue

# Game doesn't exist - insert new game
game = Game(
    home_team_id=home_team.id,
    away_team_id=away_team.id,
    home_score=home_score,
    away_score=away_score,
    week=week,
    season=year,
    is_neutral_site=is_neutral,
    is_processed=is_processed,
    excluded_from_rankings=excluded_from_rankings,
    game_date=parse_game_date(game_data)  # Helper function
)
db.add(game)
db.commit()
```

### ELO Processing Safety (Story 003)

```python
# In ranking_service.py - ensure future games not processed
def process_game(self, game: Game) -> dict:
    """Process a game and update ELO ratings"""

    # Validation: Don't process future games
    if game.home_score == 0 and game.away_score == 0:
        raise ValueError(f"Cannot process game {game.id} - no scores available")

    if game.is_processed:
        raise ValueError(f"Game {game.id} already processed")

    # Rest of existing logic...
```

---

## Files Modified

**Story 001 (Import Future Games):**
- `import_real_data.py` (~30 lines modified in `import_games()` function)

**Story 002 (Upsert Logic):**
- `import_real_data.py` (~40 lines added for upsert logic)
- Possibly `models.py` (~5 lines to add unique constraint - optional)

**Story 003 (Testing & Documentation):**
- `ranking_service.py` (~10 lines for validation in `process_game()`)
- `README.md` or `docs/IMPORT.md` (~20 lines documentation)
- Manual testing scripts (optional)

---

## Success Metrics

### Quantitative
- Future games imported: Expected ~50-100 games per week (unplayed games)
- Duplicate prevention: 0 duplicate games after running import twice
- Predictions availability: Predictions API returns >30 upcoming games
- ELO integrity: ELO ratings unchanged by future game imports (verified by comparison)
- Import time: <5 seconds additional time for future games

### Qualitative
- Predictions feature shows relevant upcoming matchups (Top 25 games)
- Users can see predictions for next week's best games
- Import script logs clearly show future vs completed games
- Developers understand the upsert logic
- Weekly imports run smoothly without manual intervention

---

## Deployment Plan

### Pre-Deployment Testing

```bash
# 1. Test on development database
python3 import_real_data.py --season 2025 --max-week 13

# 2. Verify future games imported
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE home_score = 0 AND away_score = 0;"

# 3. Verify predictions API works
curl http://localhost:8000/api/predictions?next_week=true | jq

# 4. Run import again - verify no duplicates
python3 import_real_data.py --season 2025 --max-week 13
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE home_score = 0 AND away_score = 0;"
# Should be same count as step 2

# 5. Manually update a game's scores in test database
sqlite3 cfb_rankings.db "UPDATE games SET home_score = 0, away_score = 0 WHERE id = 1;"

# 6. Re-import and verify game updates
python3 import_real_data.py --season 2025 --max-week 13
sqlite3 cfb_rankings.db "SELECT home_score, away_score FROM games WHERE id = 1;"
# Should show real scores now
```

### Production Deployment

```bash
# 1. SSH to VPS
ssh user@vps

# 2. Backup database
cd /var/www/cfb-rankings
cp cfb_rankings.db cfb_rankings.db.backup-$(date +%Y%m%d)

# 3. Pull latest code
git pull origin main

# 4. Run import with new logic
python3 import_real_data.py --season 2025

# 5. Verify predictions API works
curl http://your-domain.com/api/predictions | jq

# 6. Check logs for errors
tail -f /var/log/gunicorn-error.log
```

---

## Future Enhancements (Out of Scope)

- **Scheduled job for weekly imports**: Automate import via cron job
- **Import delta only**: Only import new/updated games (not full re-import)
- **Historical prediction tracking**: Store predictions before games played, compare accuracy
- **Game status field**: Add enum for "scheduled", "in_progress", "final", "postponed"
- **Time-based imports**: Import games from specific date ranges
- **Notification system**: Alert when new games are added or scores updated
- **Admin UI for import**: Web interface to trigger imports and view status

---

**Epic Created:** 2025-10-21
**Epic Owner:** Product Manager / Engineering Lead
**Depends On:** EPIC-007 (Game Predictions) - feature exists but needs data
**Ready for Development:** ✅

---

## Story Documents

- **Epic:** `docs/EPIC-008-FUTURE-GAME-IMPORTS.md` (this document)
- **Story 001:** `docs/EPIC-008-STORY-001.md`
- **Story 002:** `docs/EPIC-008-STORY-002.md`
- **Story 003:** `docs/EPIC-008-STORY-003.md`

---

## Context: Why This Epic Exists

This epic was created after completing EPIC-007 (Game Predictions). During testing, we discovered that while the predictions API and frontend work correctly, they have no useful data to display because:

1. The import script skips all future games
2. The database only contains completed games
3. Predictions only work on leftover FBS vs FCS games that never got scores
4. Users cannot see predictions for ranked matchups

**This epic unblocks the full value of EPIC-007** by ensuring future games are imported and available for predictions.
