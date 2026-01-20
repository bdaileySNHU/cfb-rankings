# Epic: Season-End Finalization and Archival - 2024-2025 Season

**Epic ID**: EPIC-SEASON-END-2025
**Type**: Brownfield Enhancement - Operational
**Status**: ✅ **READY FOR DEVELOPMENT** (Created: 2026-01-20)
**Priority**: High
**Complexity**: Low

---

## Epic Goal

Properly finalize the 2024-2025 college football season by validating all data integrity, computing final season statistics, and archiving the season to prepare the system for the next season's operation.

---

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Season model tracks current_week and is_active status in database
- Game processing updates team records and ELO ratings throughout season (weeks 1-20)
- RankingHistory captures weekly ranking snapshots for historical tracking
- System imports games from CollegeFootballData API including playoff games (weeks 16-20)
- Database stores: Teams, Games, RankingHistory, Seasons, Predictions, APPollRankings
- Prediction accuracy tracked and compared with AP Poll rankings
- Frontend displays historical data through season selector

**Technology stack:**
- Backend: Python FastAPI with SQLAlchemy ORM
- Database: SQLite (cfb_rankings.db)
- Data Source: CollegeFootballData API (cfbd_client.py)
- Frontend: Vanilla JavaScript displaying rankings, games, team details
- Code organization: Modern `src/` structure (post-EPIC-028 cleanup)

**Integration points:**
- `src/models/models.py` - Season, Game, Team, RankingHistory models
- `src/core/ranking_service.py` - ELO calculation and ranking logic
- `src/api/main.py` - Season management endpoints
- Database: SQLite with all season data
- Frontend: Season selector for viewing historical seasons

### Enhancement Details

**What's being added/changed:**

The 2024-2025 season has concluded with the CFP National Championship game. The system needs a proper season-end workflow to:

1. **Data Validation**
   - Verify all playoff games (weeks 16-20) are imported and processed correctly
   - Validate that all game scores are accurate and ELO ratings computed correctly
   - Check for any missing games or data inconsistencies
   - Verify AP Poll rankings are complete for the season
   - Ensure all predictions were recorded and outcomes captured

2. **Final Season Statistics**
   - Calculate final season-end rankings (frozen snapshot)
   - Compute final SOS (Strength of Schedule) for all teams
   - Generate season summary statistics:
     - Total games played
     - Prediction accuracy (ELO system)
     - AP Poll comparison metrics for full season
     - Conference performance statistics
     - Top performers by various metrics
   - Create final ranking history snapshot for week 20/final

3. **Season Archival**
   - Mark season as inactive (is_active = False)
   - Create final ranking history snapshot
   - Generate season summary report/documentation
   - Prepare system for next season initialization
   - Document any notable findings or issues for future reference

**How it integrates:**
- Uses existing Season model and API endpoints
- Extends validation logic to check data completeness
- Creates admin/utility scripts for validation and archival
- Follows existing patterns in ranking_service.py and database models
- No breaking changes to existing functionality
- All historical data remains accessible through frontend season selector

**Success criteria:**
- All 2024-2025 season data validated and confirmed complete
- Final season statistics calculated and stored
- Season properly archived with is_active = False
- System ready to initialize 2025-2026 season
- Documentation of season-end process for future seasons
- Historical data remains accessible through API and frontend

---

## Stories

### Story 1: Season Data Validation and Integrity Check

As a **system administrator**,
I want **a comprehensive data validation script that verifies all games for the 2024-2025 season are imported, processed correctly, and data integrity is maintained**,
so that **I can confidently finalize the season knowing all data is complete and accurate**.

#### Scope

- Create validation script (e.g., `utilities/validate_season.py`)
- Check all games for weeks 1-20 are imported
- Verify all games have is_processed = True
- Validate ELO rating changes sum correctly
- Check for missing or duplicate games
- Verify AP Poll rankings completeness
- Output detailed validation report
- Flag any data inconsistencies for manual review

#### Acceptance Criteria

1. **Validation script created**: `utilities/validate_season.py` with command-line interface:
   - Arguments: `--season 2025`, `--verbose`, `--output report.md`
   - Returns non-zero exit code if validation fails
   - Generates markdown report with findings

2. **Game completeness check**:
   - Query games table for season 2025
   - Count games by week (weeks 1-20)
   - Compare against expected game counts (estimated ~800 FBS games per season)
   - Report weeks with unusually low game counts (potential missing data)
   - List any teams with 0 games (data import issue)

3. **Game processing verification**:
   - Check all games have `is_processed = True`
   - List any unprocessed games with details (teams, week, scores)
   - Verify processed games have non-zero rating changes
   - Flag games with suspicious rating changes (>200 points change)

4. **ELO rating integrity check**:
   - For each game, verify: `home_rating_change + away_rating_change ≈ 0` (zero-sum)
   - Allow small floating-point tolerance (±0.01)
   - Report games with rating change imbalances
   - Verify team current ELO = initial_rating + sum(all rating changes)

5. **AP Poll completeness**:
   - Check ap_poll_rankings table for season 2025
   - Verify AP Poll data exists for weeks 1-20 (where applicable)
   - Report weeks missing AP Poll data
   - Count total AP Poll entries (expect ~25 teams × ~15-20 weeks)

6. **Missing data identification**:
   - Check for duplicate games (same teams, same week, same season)
   - Identify teams with unusual records (e.g., 0-0, 20-0)
   - Flag teams with missing preseason data (recruiting_rank = 999)
   - Report any database constraint violations

7. **Validation report generation**:
   - Create markdown report: `docs/season-2025-validation-report.md`
   - Summary section: total games, processed %, data quality score
   - Detailed findings: missing games, unprocessed games, ELO issues
   - Recommendations: actions needed before finalization
   - Status: PASS (all checks passed) or FAIL (issues found)

8. **Console output**:
   - Print progress: "Validating games... 100%"
   - Print summary: "✓ All 789 games processed correctly"
   - Print warnings: "⚠ 3 weeks missing AP Poll data"
   - Print errors: "✗ 5 games have ELO imbalances"

#### Integration Verification

- **IV1: Read-Only Operations** - Validation script only reads data, makes no modifications
- **IV2: No Service Impact** - Script can run while application is serving traffic
- **IV3: Report Accessibility** - Generated report is human-readable markdown
- **IV4: Existing Data Unchanged** - Verify database state identical before/after validation

#### Rollback Considerations

- **Risk Level**: Very Low - Read-only validation, no data modifications
- **Rollback**: Delete validation script and report (git revert)
- **Data Loss**: None (no data modifications)
- **Rollback Time**: < 1 minute

---

### Story 2: Final Season Statistics Calculation

As a **system analyst**,
I want **comprehensive final statistics calculated and stored for the completed 2024-2025 season**,
so that **I can analyze system performance, compare with previous seasons, and provide season summary to stakeholders**.

#### Scope

- Create season statistics calculation script (e.g., `utilities/finalize_season_stats.py`)
- Calculate final frozen rankings for all teams
- Compute final SOS values
- Calculate overall prediction accuracy for the season
- Generate AP Poll comparison statistics (full season including postseason)
- Calculate conference-level performance metrics
- Store final statistics in appropriate tables or generate report
- Create season summary document

#### Acceptance Criteria

1. **Statistics script created**: `utilities/finalize_season_stats.py` with:
   - Arguments: `--season 2025`, `--output docs/season-2025-summary.md`
   - Calculates all statistics from database queries
   - Generates comprehensive markdown report
   - Stores final snapshot in ranking_history table

2. **Final rankings snapshot**:
   - Calculate final ELO ratings for all teams
   - Calculate final SOS for all teams using `ranking_service.calculate_sos()`
   - Create RankingHistory entries for "final" week (week=20 or special value)
   - Store: team_id, week=20, rank, elo_rating, wins, losses, sos, sos_rank
   - Mark as season-end snapshot in database

3. **Prediction accuracy statistics**:
   - Query predictions table for season 2025
   - Calculate: total predictions, correct predictions, accuracy percentage
   - Break down by week: accuracy per week
   - Break down by game type: regular season vs postseason
   - Compare top 10 vs top 25 vs unranked matchup accuracy
   - Identify best predicted games (highest confidence + correct)
   - Identify worst predicted games (high confidence + incorrect)

4. **AP Poll comparison metrics**:
   - Use existing AP Poll comparison logic from `ap_poll_service.py`
   - Calculate full season comparison statistics:
     - ELO system accuracy vs AP Poll accuracy
     - Head-to-head comparison (games where both made predictions)
     - Weekly accuracy trends (chart data for weeks 1-20)
     - Disagreement analysis (games where predictions differed)
   - Include postseason games (weeks 16-20) in analysis

5. **Conference performance statistics**:
   - Calculate for each conference:
     - Average team ELO rating
     - Conference-wide win-loss record
     - Out-of-conference performance
     - Teams in final top 25
     - Conference champion and their final rank
   - Rank conferences by average team strength

6. **Top performers identification**:
   - Top 25 final rankings (frozen)
   - Biggest risers (largest ELO gain from preseason)
   - Biggest fallers (largest ELO loss from preseason)
   - Toughest schedule (highest SOS)
   - Most improved (largest rating increase during season)
   - Best record vs ranking (teams that overperformed ELO)

7. **Season summary document creation**:
   - Generate: `docs/season-2025-summary.md` with sections:
     - Season Overview (CFP champion, final top 10)
     - Prediction Performance (accuracy stats, comparison charts)
     - Conference Analysis (performance rankings)
     - Notable Achievements (biggest upsets, best performances)
     - System Insights (ELO vs AP comparison, algorithm performance)
   - Include data visualizations (tables, if possible in markdown)
   - Professional formatting for stakeholder presentation

8. **Database storage (optional)**:
   - Consider adding season_statistics table (future enhancement)
   - For now, store as RankingHistory final snapshot + markdown report
   - Document final statistics in season summary report

#### Integration Verification

- **IV1: Rankings Remain Accessible** - Final snapshot added to ranking_history, historical rankings unchanged
- **IV2: API Returns Final Stats** - `/api/rankings?season=2025&week=20` returns final snapshot
- **IV3: Frontend Displays Final Rankings** - Season selector shows final rankings for 2025
- **IV4: Statistics Accuracy** - Spot-check calculated statistics against manual queries

#### Rollback Considerations

- **Risk Level**: Low - Creates new data (final snapshot), doesn't modify existing
- **Rollback**: Delete final RankingHistory entries for week=20, delete summary document
- **Data Loss**: Final statistics can be recalculated from game data
- **Rollback Time**: < 5 minutes

---

### Story 3: Season Archival and System Preparation

As a **system operator**,
I want **the completed 2024-2025 season marked as inactive and the system prepared for the next season**,
so that **the system clearly distinguishes between active and historical seasons and is ready for 2025-2026 season initialization**.

#### Scope

- Create season archival script (e.g., `utilities/archive_season.py`)
- Update Season model: set is_active = False for 2024-2025
- Ensure final RankingHistory snapshot is saved
- Create archival documentation (season summary, key findings)
- Document season-end process for future reference
- Verify historical data remains accessible through API
- Prepare system state for potential 2025-2026 season initialization
- Optional: Add admin endpoint for season archival

#### Acceptance Criteria

1. **Archival script created**: `utilities/archive_season.py` with:
   - Arguments: `--season 2025`, `--confirm` (safety flag)
   - Updates season table: `UPDATE seasons SET is_active = False WHERE year = 2025`
   - Verifies final ranking snapshot exists before archiving
   - Logs all actions performed
   - Requires explicit confirmation to prevent accidents

2. **Season marked inactive**:
   - Query seasons table: `SELECT * FROM seasons WHERE year = 2025`
   - Verify: `is_active = False`
   - Verify: no other seasons have `is_active = True` (no active season)
   - Document: season marked inactive on [date] by [user]

3. **Final snapshot verification**:
   - Verify RankingHistory entries exist for week=20 (final)
   - Verify all teams have final snapshot entries
   - Count: expect ~133 entries (one per FBS team)
   - Log warning if final snapshot missing

4. **Historical data accessibility**:
   - Test API endpoint: `GET /api/rankings?season=2025&week=20`
   - Verify returns final rankings correctly
   - Test API endpoint: `GET /api/teams?season=2025`
   - Verify returns team data for season 2025
   - Test frontend: season selector includes 2025, displays correctly

5. **Archival documentation created**:
   - Copy validation report to: `docs/archive/season-2025-validation.md`
   - Copy season summary to: `docs/archive/season-2025-summary.md`
   - Create: `docs/archive/season-2025-notes.md` for any notable findings
   - Document any data issues, unusual results, or system improvements needed

6. **Season-end process documentation**:
   - Create or update: `docs/season-end-checklist.md`
   - Document steps: validation → statistics → archival
   - Include commands to run for each step
   - Include troubleshooting tips
   - Reference: use this checklist for future season-ends

7. **System readiness check**:
   - Verify: no active season exists (`SELECT * FROM seasons WHERE is_active = True` returns empty)
   - Document: system ready for 2025-2026 season initialization
   - Note: next season can be created with `is_active = True`
   - Verify: all tables are in consistent state (no orphaned records)

8. **Optional: Admin API endpoint** (future enhancement):
   - Consider adding: `POST /api/admin/seasons/{year}/archive`
   - Requires authentication (if/when auth is implemented)
   - Performs same actions as script but via API
   - Returns archival status and summary

#### Integration Verification

- **IV1: Historical Data Preserved** - All 2025 season data remains in database, accessible via API
- **IV2: Frontend Season Selector Works** - Can select season 2025, view rankings and games
- **IV3: No Active Season** - System correctly shows no active season (ready for new season)
- **IV4: All Tests Pass** - Run test suite, verify no regressions from archival

#### Rollback Considerations

- **Risk Level**: Low-Medium - Modifies season status, but reversible
- **Rollback**:
  ```sql
  UPDATE seasons SET is_active = True WHERE year = 2025;
  ```
- **Data Loss**: None (only flag changes, all data preserved)
- **Rollback Time**: < 1 minute (single SQL update)

---

## Compatibility Requirements

- [x] **Existing APIs remain unchanged** - No changes to API endpoints or response schemas
- [x] **Database schema unchanged** - Uses existing tables (seasons, games, ranking_history)
- [x] **Frontend continues to work** - Season selector displays archived season correctly
- [x] **Historical data accessible** - All 2025 season data remains queryable
- [x] **No breaking changes** - All existing functionality preserved

---

## Risk Mitigation

### Primary Risk: Data Loss During Archival

**Risk:** Accidentally deleting or corrupting season data during archival process

**Mitigation:**
- Backup database before archival: `cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d).db`
- Validation script confirms data completeness before archival
- Archival only changes `is_active` flag, doesn't delete data
- Require `--confirm` flag for archival script (prevents accidental runs)
- Test archival process on database copy first

**Rollback Plan:**
- Restore database from backup if needed
- Or simply re-mark season as active: `UPDATE seasons SET is_active = True WHERE year = 2025`

### Secondary Risk: Missing Data Discovered Post-Archival

**Risk:** After archival, discover missing games or incorrect data

**Mitigation:**
- Comprehensive validation in Story 1 before archival
- Validation report reviewed and approved before proceeding
- All data issues fixed before marking season inactive
- Season can be re-activated if needed to fix data

**Rollback Plan:**
- Re-activate season: `UPDATE seasons SET is_active = True WHERE year = 2025`
- Import missing data or fix issues
- Re-run validation and archival process

---

## Definition of Done

- [ ] **Story 1 Complete**: Validation script created and run successfully
- [ ] **Validation Report Generated**: All data issues identified and documented
- [ ] **Data Issues Resolved**: Any missing games or errors fixed before archival
- [ ] **Story 2 Complete**: Final statistics calculated and stored
- [ ] **Season Summary Document**: Comprehensive summary created in docs/
- [ ] **Story 3 Complete**: Season marked as inactive in database
- [ ] **Archival Documentation**: Season archived with complete documentation
- [ ] **Historical Data Accessible**: Frontend and API serve 2025 data correctly
- [ ] **Season-End Process Documented**: Checklist created for future seasons
- [ ] **Database Backup Created**: Backup taken before archival
- [ ] **All Tests Pass**: Existing test suite passes (no regressions)
- [ ] **System Ready for New Season**: No active season, ready for 2025-2026 initialization

---

## Validation Checklist

### Scope Validation

- [x] Epic can be completed in 3 stories
- [x] No architectural changes required
- [x] Enhancement follows existing patterns (utility scripts, database queries)
- [x] Integration complexity is low (read/update operations only)

### Risk Assessment

- [x] Risk to existing system is very low (read-only validation, single flag update)
- [x] Rollback plan is simple and fast (database backup + flag change)
- [x] Testing approach covers data preservation (verify historical access)
- [x] Team has knowledge of database structure and Season model

### Completeness Check

- [x] Epic goal is clear: finalize and archive 2024-2025 season
- [x] Stories are properly scoped: validation → statistics → archival
- [x] Success criteria are measurable: data validated, stats calculated, season archived
- [x] Dependencies identified: validation must pass before archival

---

## Technical Notes

### Database Queries

**Check Season Status:**
```sql
SELECT year, current_week, is_active
FROM seasons
WHERE year = 2025;
```

**Count Games by Week:**
```sql
SELECT week, COUNT(*) as game_count
FROM games
WHERE season = 2025
GROUP BY week
ORDER BY week;
```

**Verify All Games Processed:**
```sql
SELECT COUNT(*)
FROM games
WHERE season = 2025 AND is_processed = False;
```

**Final Rankings Snapshot:**
```sql
SELECT t.name, rh.rank, rh.elo_rating, t.wins, t.losses, rh.sos
FROM ranking_history rh
JOIN teams t ON rh.team_id = t.id
WHERE rh.season = 2025 AND rh.week = 20
ORDER BY rh.rank;
```

**Archive Season:**
```sql
UPDATE seasons
SET is_active = False
WHERE year = 2025;
```

### Files to Create

```
utilities/
├── validate_season.py          # Story 1: Data validation
├── finalize_season_stats.py    # Story 2: Statistics calculation
└── archive_season.py            # Story 3: Season archival

docs/
├── season-2025-validation-report.md   # Story 1 output
├── season-2025-summary.md              # Story 2 output
├── season-end-checklist.md             # Story 3: Process documentation
└── archive/
    ├── season-2025-validation.md       # Story 3: Archived validation
    ├── season-2025-summary.md          # Story 3: Archived summary
    └── season-2025-notes.md            # Story 3: Additional notes
```

### Script Usage Examples

**Validation:**
```bash
# Run validation for 2025 season
python utilities/validate_season.py --season 2025 --output docs/season-2025-validation-report.md

# Verbose output
python utilities/validate_season.py --season 2025 --verbose
```

**Statistics:**
```bash
# Calculate final statistics
python utilities/finalize_season_stats.py --season 2025 --output docs/season-2025-summary.md
```

**Archival:**
```bash
# Archive season (requires confirmation)
python utilities/archive_season.py --season 2025 --confirm

# Dry-run (show what would be done)
python utilities/archive_season.py --season 2025
```

---

## Success Metrics

### Before Epic (Current State)
- 2024-2025 season completed with CFP Championship game
- Season marked as `is_active = True` in database
- No formal validation of data completeness
- No finalized season statistics report
- No documented season-end process

### After Epic (Target State)
- 2024-2025 season fully validated (all games verified)
- Final season statistics calculated and documented
- Season marked as `is_active = False` (archived)
- Comprehensive season summary report available
- Historical data remains accessible through API and frontend
- Season-end process documented for future use
- System ready for 2025-2026 season initialization

---

## Developer Handoff

**Status:** ✅ Ready for development - all stories defined and scoped

**Quick Start:**
- This is a straightforward operational epic (data validation → statistics → archival)
- Work flow: Story 1 → Review results → Story 2 → Story 3
- All stories use utility scripts (no application code changes)
- Estimated effort: 6-9 hours total (2-3 hours per story)

**Key Reminders:**
- Backup database before archival (critical!)
- Run validation script first, review results before proceeding
- Archival only changes `is_active` flag, doesn't delete data
- All historical data must remain accessible after archival
- Document the process for future season-ends

---

## Notes

- **Timeline:** Can be executed immediately (season has concluded)
- **Dependencies:** None (uses existing database and models)
- **Impact:** Low - operational scripts, no application changes
- **Priority:** High - should be completed before next season starts
- **Effort:** Low - 3 straightforward stories, utility scripts only
- **Risk:** Very low - read-only validation, simple flag update
- **Value:** Ensures data integrity, provides season insights, prepares for next season

---

## Appendix: Example Validation Report

```markdown
# Season 2025 Validation Report

**Generated:** 2026-01-20
**Season:** 2025
**Status:** ✅ PASS

## Summary

- **Total Games:** 789
- **Games Processed:** 789 (100%)
- **Weeks Covered:** 1-20 (complete)
- **Teams:** 133 FBS teams
- **Data Quality:** 98.5%

## Detailed Findings

### Game Completeness ✅
- Week 1-15: All regular season games imported
- Week 16-20: All postseason games imported
- No missing games detected

### Game Processing ✅
- All 789 games marked as processed
- All games have ELO rating changes
- No unprocessed games found

### ELO Integrity ✅
- All games pass zero-sum check (±0.01 tolerance)
- No rating imbalances detected
- Team ELO calculations verified correct

### AP Poll Data ⚠️
- Weeks 1-15: Complete (375 entries)
- Weeks 16-20: Partial (75 entries)
- Note: AP Poll not published for all bowl games (expected)

### Data Anomalies
- None detected

## Recommendations

✅ **Ready for Finalization** - All critical data validated
- Proceed with statistics calculation (Story 2)
- Proceed with season archival (Story 3)

## Actions Required

- None - validation successful
```

---

**END OF EPIC DOCUMENT**
