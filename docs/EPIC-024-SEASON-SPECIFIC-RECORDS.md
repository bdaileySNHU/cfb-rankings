# EPIC-024: Season-Specific Team Records

**Status:** Proposed
**Priority:** Critical (P0)
**Created:** 2025-11-30
**Category:** Data Architecture / Bug Fix

---

## Problem Statement

### Current Issue

Team records in the `teams` table are **cumulative across all seasons**, causing incorrect displays:

**Evidence (2025 Season Week 14):**
- Oregon: 22-1 (impossible - only 14 weeks played)
- Texas: 20-5 (same as 2024 end-of-season)
- Notre Dame: 21-3 (wrong for current season)

**Root Cause:**
- Teams table stores `wins` and `losses` fields
- These fields accumulate across seasons
- No season reset mechanism
- Current rankings display uses cumulative data

### Impact

**User-Facing Issues:**
- ❌ Current season rankings show incorrect records
- ❌ Team pages show wrong win/loss totals
- ❌ Can't browse historical seasons accurately
- ❌ Rankings calculations may be affected

**Data Integrity:**
- Season boundaries are blurred
- Historical data is corrupted/unreliable
- No clear separation between seasons

---

## Business Value

### User Benefits
1. **Accurate current season rankings** - Users see correct W-L records
2. **Historical season browsing** - View any past season accurately
3. **Season comparisons** - Compare team performance across years
4. **Data trust** - Reliable, verifiable statistics

### Technical Benefits
1. **Data integrity** - Each season isolated and preserved
2. **Scalability** - Adding seasons doesn't corrupt data
3. **Reporting** - Season-by-season analytics
4. **Compliance** - Accurate historical record keeping

---

## Proposed Solution

### Architecture Decision

**Store season-specific records separately from teams table**

**Option A: Use Existing ranking_history Table (Recommended)**
- `ranking_history` already stores wins/losses per week per season
- Modify displays to query ranking_history instead of teams table
- Teams table becomes metadata only (name, conference)
- **Pros:** No schema changes, data already exists, quick implementation
- **Cons:** Requires changes to multiple display/calculation points

**Option B: Create team_seasons Table**
- New table: `team_seasons` with season-specific stats
- Schema: `team_id`, `season`, `wins`, `losses`, `elo_rating`, etc.
- Teams table becomes template/metadata
- **Pros:** Clean separation, purpose-built for this use case
- **Cons:** Schema migration, data backfill, more complex

**Recommendation:** **Option A** - Use ranking_history

---

## Stories

### Story 24.1: Audit and Fix Current Season Records
**Priority:** P0 - Critical Bug Fix
**Effort:** 2-3 hours

**Objective:** Fix 2025 rankings to show correct records

**Tasks:**
- [ ] Count actual games played per team in 2025
- [ ] Calculate correct win/loss records from game results
- [ ] Update teams table with accurate 2025 records
- [ ] Verify rankings page shows correct data

**Acceptance Criteria:**
- Oregon shows correct 2025 record (not 22-1)
- All teams show records matching actual 2025 games
- Rankings page displays accurately

---

### Story 24.2: Refactor Rankings Display to Use Season Data
**Priority:** P0 - Architectural Fix
**Effort:** 4-6 hours

**Objective:** Change rankings display to use season-specific data from ranking_history

**Tasks:**
- [ ] Update `/api/rankings` endpoint to query ranking_history
- [ ] Modify frontend to display season-specific records
- [ ] Update team detail page to use ranking_history
- [ ] Add season selector to rankings page

**Acceptance Criteria:**
- Rankings page queries ranking_history, not teams table
- Team records are season-specific
- Historical seasons display correctly
- Current season shows accurate data

**Files to Modify:**
- `main.py` - Rankings endpoints
- `frontend/js/rankings.js` - Rankings display
- `frontend/js/team.js` - Team detail (already partially done)

---

### Story 24.3: Season Management & Reset Process
**Priority:** P1 - Preventive
**Effort:** 3-4 hours

**Objective:** Create process for season transitions

**Tasks:**
- [ ] Create season initialization script
- [ ] Document season start/end procedures
- [ ] Add season status indicators (active, archived)
- [ ] Create season rollover automation

**Acceptance Criteria:**
- Script to prepare database for new season
- Documentation for season transitions
- Automated checks for season boundaries

**Deliverables:**
- `scripts/start_new_season.py`
- `docs/SEASON-MANAGEMENT.md`

---

### Story 24.4: Historical Season Selector UI
**Priority:** P2 - Enhancement
**Effort:** 2-3 hours

**Objective:** Add UI to browse historical seasons

**Tasks:**
- [ ] Add season dropdown to rankings page
- [ ] Add season dropdown to team pages
- [ ] Show "Historical Season" indicator
- [ ] Link to different seasons

**Acceptance Criteria:**
- Users can select any season from dropdown
- Page updates to show that season's data
- Clear visual indicator for historical vs current

---

## Technical Implementation

### Data Model Changes

**Current (Broken):**
```
teams table:
  - wins (cumulative across all seasons) ❌
  - losses (cumulative across all seasons) ❌
  - elo_rating (current only)
```

**Proposed (Option A):**
```
teams table:
  - name, conference, metadata only
  - wins/losses deprecated (or removed)

ranking_history table (already exists):
  - team_id, season, week
  - wins, losses (season-specific) ✓
  - elo_rating (weekly snapshot) ✓
  - rank (weekly)
```

**Proposed (Option B - Alternative):**
```
team_seasons table (new):
  - team_id, season
  - wins, losses (season-specific)
  - elo_rating (final)
  - final_rank
```

### API Changes

**Before:**
```python
# GET /api/rankings?season=2025
# Returns: teams.wins, teams.losses ❌
```

**After:**
```python
# GET /api/rankings?season=2025&week=14
# Returns: ranking_history WHERE season=2025, week=14 ✓
```

### Migration Path

1. **Immediate (Story 24.1):**
   - Manually fix 2025 teams table records
   - Stopgap to show correct current season

2. **Short-term (Story 24.2):**
   - Refactor to use ranking_history
   - Works for all historical seasons

3. **Long-term (Story 24.3):**
   - Automate season management
   - Prevent future occurrences

---

## Testing Strategy

### Validation Checks

**Current Season (2025):**
- [ ] Team records match actual game results
- [ ] Rankings calculate correctly
- [ ] No games from previous seasons counted

**Historical Seasons (2024, 2023, etc.):**
- [ ] Can browse each season independently
- [ ] Records are frozen/accurate
- [ ] No cross-season contamination

**Season Transitions:**
- [ ] New season starts with 0-0 records
- [ ] Previous season data preserved
- [ ] Ranking history complete

---

## Risks and Mitigation

### Risk 1: Data Loss
**Risk:** Accidentally overwrite historical records
**Mitigation:**
- Backup database before changes
- Read-only access to historical data
- Thorough testing on dev/staging

### Risk 2: Performance
**Risk:** Querying ranking_history may be slower
**Mitigation:**
- Add indexes on (team_id, season, week)
- Cache season endpoints
- Monitor query performance

### Risk 3: Breaking Changes
**Risk:** Changing API responses breaks frontend
**Mitigation:**
- Version API endpoints if needed
- Gradual rollout (rankings first, then teams)
- Comprehensive testing

---

## Success Metrics

**Immediate (Post-24.1):**
- ✅ 2025 rankings show correct records
- ✅ Zero teams with impossible records (>14 games in Week 14)

**Short-term (Post-24.2):**
- ✅ Can browse 2024 season accurately
- ✅ All historical seasons display correctly
- ✅ Current season isolated from past data

**Long-term (Post-24.3):**
- ✅ Automated season transitions
- ✅ No manual intervention needed for new seasons
- ✅ Historical data integrity maintained

---

## Related Work

**Dependencies:**
- EPIC-022 (Story 22.2) exposed this issue
- Affects all ranking displays

**Follow-up Work:**
- Season comparison features
- Historical analytics dashboard
- Year-over-year team analysis

---

## Documentation

**To Create:**
- `docs/SEASON-MANAGEMENT.md` - Season lifecycle
- `docs/DATA-MODEL.md` - Updated architecture
- `docs/API-SEASON-ENDPOINTS.md` - API changes

**To Update:**
- `README.md` - Season browsing feature
- `docs/WEEKLY-WORKFLOW.md` - Season transitions

---

## Timeline Estimate

**Story 24.1:** 2-3 hours (Critical - Do first)
**Story 24.2:** 4-6 hours (High priority)
**Story 24.3:** 3-4 hours (Medium priority)
**Story 24.4:** 2-3 hours (Nice to have)

**Total:** 11-16 hours (~2-3 days)

**Recommended Approach:**
1. **Immediate:** Fix Story 24.1 (current season records) - ~2 hours
2. **This week:** Complete Story 24.2 (refactor to ranking_history) - ~6 hours
3. **Next week:** Stories 24.3 & 24.4 (season management + UI) - ~6 hours

---

## Decision Log

**2025-11-30:** Created EPIC based on discovery during Story 22.2
**Architectural Decision:** Use ranking_history (Option A) for season-specific data
**Priority:** Critical - Affects core functionality

---

## Questions and Answers

**Q: Should we delete wins/losses from teams table?**
A: Not immediately. Deprecate first, ensure all displays work, then remove in future version.

**Q: What about preseason ratings?**
A: Store in teams table (not season-specific) or in ranking_history week 0.

**Q: How to handle teams that change conferences between seasons?**
A: Conference stored per-season in ranking_history or team_seasons.

---

**Epic Owner:** Development Team
**Stakeholders:** All users (critical bug affects everyone)
**Status:** Ready for implementation
