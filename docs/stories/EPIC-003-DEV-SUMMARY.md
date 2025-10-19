# EPIC-003: FCS Game Display - Development Summary

**Epic**: FCS Game Display for Schedule Completeness
**Created**: 2025-10-18
**Status**: Ready for Development
**Estimated Effort**: 7-10 hours (2-3 development sessions)

---

## 🎯 Epic Goal

Enable users to view complete team schedules including FCS opponent games on the frontend, while maintaining the existing exclusion of FCS games from ELO ranking calculations.

**User Value**: Fans see complete team schedules (no confusing gaps) while understanding which games count toward rankings.

---

## 📊 Current State vs. Desired State

### Current State (Before EPIC-003)

**Ohio State Schedule Display:**
```
Week 1: vs Texas (W 14-7)
Week 3: vs Ohio (W 37-9)          ← Week 2 missing!
Week 5: @ Washington (W 24-6)
Week 6: vs Minnesota (W 42-3)

Record: 4-0
```

**Why Week 2 is missing**: Ohio State played Grambling (FCS) which is excluded from import.

### Desired State (After EPIC-003)

**Ohio State Schedule Display:**
```
ℹ️ Complete schedule shown. FCS opponents excluded from rankings and record.

Week 1: vs Texas (W 14-7)
Week 2: vs Grambling [FCS] (W 70-0)  ← Now visible, clearly marked
Week 3: vs Ohio (W 37-9)
Week 5: @ Washington (W 24-6)
Week 6: vs Minnesota (W 42-3)

Record: 4-0 (FBS Only)
```

---

## 🏗️ Architecture Overview

### What Changes Where

| Component | Current Behavior | New Behavior | Story |
|-----------|-----------------|--------------|-------|
| **Database** | Only FBS games stored | FBS + FCS games (with flag) | 007 |
| **Team Model** | Only FBS teams | FBS + FCS team placeholders | 007 |
| **RankingService** | Implicit filtering | Explicit `excluded=False` filter | 007 |
| **Import Script** | Skips FCS games | Imports FCS with exclusion flag | 008 |
| **Team Schedule API** | Returns FBS games only | Returns FBS + FCS games | 008 |
| **Frontend Display** | Shows FBS games | Shows all games with visual distinction | 009 |

### Data Flow

```
CFBD API
   ↓
import_real_data.py
   ├─→ FBS vs FBS games → excluded_from_rankings=False → Rankings ✓
   └─→ FBS vs FCS games → excluded_from_rankings=True  → Display only
                ↓
          Database (games table)
                ↓
    /api/teams/{id}/schedule
                ↓
          Frontend (team.js)
                ↓
    User sees complete schedule
```

---

## 📋 Story Execution Order

### **CRITICAL**: Stories must be executed in sequence

1. **Story 007** (Database Foundation) - **MUST COMPLETE FIRST**
2. **Story 008** (Backend Import/API) - Depends on 007
3. **Story 009** (Frontend Display) - Depends on 008

**Why this order?**
- 007 creates database schema safety (exclusion filtering)
- 008 imports data using schema from 007
- 009 displays data from API in 008

**DO NOT** skip 007 or start 008/009 before 007 is complete and tested!

---

## 📖 Story Details

### Story 007: Database Schema & Model Updates
**File**: `docs/stories/story-007-game-model-exclusion-flag.md`
**Priority**: P0 (Foundation)
**Effort**: 2-3 hours

#### Key Deliverables
1. Add `excluded_from_rankings` field to `Game` model (boolean, default=False, indexed)
2. Add `is_fcs` field to `Team` model (boolean, default=False)
3. Add `ConferenceType.FCS` enum value
4. Update `RankingService` methods with explicit exclusion filters
5. Database migration (backward compatible)
6. Comprehensive test coverage

#### Critical Implementation Notes
- **NEVER** rely on implicit filtering in ranking calculations
- **ALWAYS** use explicit `WHERE excluded_from_rankings = False`
- All 270+ existing tests must pass unchanged
- ELO calculations must produce identical results for existing data

#### Files to Modify
- `models.py` (Game, Team, ConferenceType)
- `ranking_service.py` (process_game, calculate_sos, get_current_rankings)
- `database.py` (migration if using Alembic)
- `tests/test_models.py` (new tests)
- `tests/test_ranking_service.py` (integration tests)

---

### Story 008: FCS Game Import & API Updates
**File**: `docs/stories/story-008-fcs-game-import-api.md`
**Priority**: P1
**Effort**: 3-4 hours
**Depends on**: Story 007

#### Key Deliverables
1. Import FCS games with `excluded_from_rankings=True`
2. Create FCS team placeholders with `is_fcs=True`
3. Update `/api/teams/{id}/schedule` to return FCS games
4. Add `excluded_from_rankings` and `is_fcs` fields to API response
5. Ensure team W-L records exclude FCS games
6. Import statistics report FCS games separately

#### Critical Implementation Notes
- FCS games are imported but **NEVER** processed by `RankingService.process_game()`
- Team win/loss counts increment ONLY for FBS games
- Create FCS team records (don't use NULL team IDs) for referential integrity

#### Files to Modify
- `import_real_data.py` (import_games function)
- `main.py` (/api/teams/{id}/schedule endpoint)
- `tests/integration/test_cfbd_import.py` (new tests)
- `tests/integration/test_rankings_seasons_api.py` (API tests)

#### New API Response Format
```json
{
  "team_name": "Ohio State",
  "games": [
    {
      "week": 1,
      "opponent_name": "Texas",
      "excluded_from_rankings": false,
      "is_fcs": false,
      ...
    },
    {
      "week": 2,
      "opponent_name": "Grambling",
      "excluded_from_rankings": true,
      "is_fcs": true,
      ...
    }
  ]
}
```

---

### Story 009: Frontend FCS Display
**File**: `docs/stories/story-009-fcs-frontend-display.md`
**Priority**: P2
**Effort**: 2-3 hours
**Depends on**: Story 008

#### Key Deliverables
1. Display FCS games in schedule table with grayed-out styling
2. Add "FCS" badge next to FCS opponent names
3. Add info box explaining FCS exclusion
4. Update team record to show "FBS Only" clarification
5. Ensure accessible design (tooltips, screen readers)
6. Mobile responsive

#### Critical Implementation Notes
- FCS games visually de-emphasized but still readable
- Clear user education via info box and tooltips
- No breaking changes to existing FBS game display
- Maintain responsive design on mobile

#### Files to Modify
- `frontend/js/team.js` (createScheduleRow, populateTeamInfo)
- `frontend/team.html` (add info box)
- `frontend/css/team.css` (new styles for FCS games)

#### Visual Design
**FCS Game Row:**
- Background: `rgba(0,0,0,0.02)`
- Text: Secondary color (grayed)
- Opacity: 0.75
- Badge: "FCS" in small pill badge

**Info Box:**
```
ℹ️ Complete schedule shown. FCS opponents are displayed but
   excluded from rankings and record.
```

---

## 🧪 Testing Strategy

### Story 007 Testing
- **Unit Tests**: Model field defaults and validation
- **Integration Tests**: Ranking calculations with excluded games
- **Regression Tests**: All 270+ existing tests pass unchanged
- **Verification**: ELO ratings unchanged for existing data

### Story 008 Testing
- **Integration Tests**: FCS game import with mock CFBD data
- **API Tests**: Team schedule endpoint returns FCS games
- **Record Tests**: Team W-L counts exclude FCS games
- **Edge Cases**: All FCS opponents, no FCS opponents, mixed schedules

### Story 009 Testing
- **Manual Testing**: Visual verification across teams (Ohio State, Georgia, etc.)
- **Responsive Testing**: Mobile, tablet, desktop layouts
- **Accessibility Testing**: Screen reader, keyboard navigation, color contrast
- **Browser Testing**: Chrome, Firefox, Safari

### Integration Testing (End-to-End)
1. Import fresh data with FCS games
2. Verify database has correct flags
3. Verify API returns complete schedules
4. Verify frontend displays all games correctly
5. Verify team records accurate (FBS only)
6. Verify rankings unchanged

---

## ⚠️ Critical Safety Requirements

### Ranking Integrity (MUST NOT BREAK)
- ✅ ELO calculations MUST explicitly filter `excluded_from_rankings=False`
- ✅ SOS calculations MUST exclude FCS games
- ✅ Team W-L records MUST count FBS games only
- ✅ All 270+ existing tests MUST pass
- ✅ Existing ranking results MUST be identical

### Database Safety
- ✅ Migration MUST be backward compatible
- ✅ Default values MUST be safe (False for existing games)
- ✅ Indexes MUST be created for query performance
- ✅ Rollback plan MUST be tested

### API Compatibility
- ✅ New fields MUST be additive (no breaking changes)
- ✅ Existing API consumers MUST continue to work
- ✅ Error handling MUST be robust
- ✅ Performance MUST remain acceptable

---

## 🚀 Deployment Checklist

### Pre-Deployment (Local/Dev)
- [ ] Story 007: All tests pass (270+ existing + new tests)
- [ ] Story 007: Database migration tested (upgrade + rollback)
- [ ] Story 007: ELO calculations verified unchanged
- [ ] Story 008: FCS games import successfully
- [ ] Story 008: Team schedule API returns correct data
- [ ] Story 008: Team records accurate (FBS only)
- [ ] Story 009: Frontend displays all games correctly
- [ ] Story 009: Visual design matches mockups
- [ ] Story 009: Accessible on all devices
- [ ] Full integration test: Import → API → Display

### Production Deployment
1. **Backup production database** (safety first!)
2. **Deploy Story 007**:
   - Push code to production
   - Run database migration
   - Verify existing functionality unchanged
   - Run smoke tests on rankings
3. **Deploy Story 008**:
   - Push code to production
   - Re-run import script with `--validate-only` first
   - Run full import
   - Verify API returns FCS games
   - Check team records
4. **Deploy Story 009**:
   - Push frontend code
   - Clear browser cache
   - Verify schedule display
   - Test on multiple devices

### Post-Deployment Verification
- [ ] Ohio State shows Week 2 vs Grambling (FCS)
- [ ] Georgia shows Week 2 vs Austin Peay (FCS)
- [ ] All FCS games have "FCS" badge
- [ ] Team records show "FBS Only"
- [ ] Rankings unchanged from previous values
- [ ] No console errors
- [ ] Mobile view works

---

## 🔄 Rollback Plan

### If Story 007 Fails
```bash
# Revert database migration
# (SQL: ALTER TABLE games DROP COLUMN excluded_from_rankings)
git revert <commit-hash>
# Redeploy previous version
# Verify all tests pass
```

### If Story 008 Fails
```bash
# Stop import process
# Revert code changes
git revert <commit-hash>
# Re-run import with previous version
# FCS games simply won't appear (like before)
```

### If Story 009 Fails
```bash
# Revert frontend changes
git revert <commit-hash>
# Clear CDN cache if applicable
# Users see FBS-only schedules (like before)
```

**Good news**: Each story can be rolled back independently!

---

## 📊 Success Metrics

### Immediate Success (Post-Deployment)
- ✅ Complete schedules displayed (no gaps in weeks)
- ✅ FCS games clearly distinguished visually
- ✅ Team records accurate (FBS only)
- ✅ Rankings unchanged (verified numerically)
- ✅ Zero production errors

### User Impact
- ✅ Users see complete season picture
- ✅ No confusion about missing weeks
- ✅ Clear understanding of ranking methodology
- ✅ Improved transparency

### Technical Quality
- ✅ Test coverage maintained (270+ tests passing)
- ✅ Performance acceptable (<100ms API response)
- ✅ Database queries efficient (indexed fields)
- ✅ Code quality high (follows existing patterns)

---

## 🤝 Team Coordination

### Developer Responsibilities
1. Read all three story files completely before starting
2. Execute stories in order (007 → 008 → 009)
3. Run full test suite after each story
4. Don't skip safety checks or tests
5. Ask questions if requirements unclear

### Code Review Focus
- **Story 007**: Verify explicit filtering in ALL ranking methods
- **Story 008**: Verify FCS games never processed for rankings
- **Story 009**: Verify visual distinction is clear and accessible

### Testing Responsibilities
- Unit tests: Developer writes during implementation
- Integration tests: Developer writes during implementation
- Manual testing: QA/Developer after each story
- Accessibility testing: QA before Story 009 completion

---

## 📚 Reference Documents

### Story Files
- `docs/stories/story-007-game-model-exclusion-flag.md` - Database schema
- `docs/stories/story-008-fcs-game-import-api.md` - Backend import/API
- `docs/stories/story-009-fcs-frontend-display.md` - Frontend display

### Epic Document
- `docs/stories/epic-003-fcs-game-display.md` - High-level overview

### Related Documentation
- `BROWNFIELD_PRD.md` - System architecture
- `docs/prd/` - Full product requirements
- `tests/` - Existing test patterns

---

## ❓ FAQ

### Why create FCS teams in the database?
**Answer**: Maintains referential integrity and simplifies queries. Alternative (NULL team IDs) breaks foreign key constraints and complicates joins.

### Will FCS games affect rankings at all?
**Answer**: **NO**. FCS games are explicitly excluded from:
- ELO calculations
- SOS calculations
- Team W-L records
- All ranking-related queries

### What if a user clicks on an FCS team?
**Answer**: Story 008 creates FCS team records, so the team detail page will load (though it will have minimal data). This is acceptable for EPIC-003 scope.

### Can we toggle FCS games on/off in the UI?
**Answer**: Out of scope for EPIC-003. Could be future enhancement. Current implementation shows all games with clear visual distinction.

### What happens to existing production data?
**Answer**: Database migration adds `excluded_from_rankings=False` (default) to all existing games. They remain in rankings as before.

### How long will deployment take?
**Answer**:
- Story 007: ~5 min (migration is fast)
- Story 008: ~10-15 min (re-import takes time)
- Story 009: ~2 min (frontend only)
- **Total**: ~20-25 minutes with verification

---

## 🎉 Expected Outcome

After EPIC-003 completion:

1. **Users** see complete team schedules without confusing gaps
2. **Rankings** remain mathematically identical (FCS games excluded)
3. **Transparency** improves (clear marking of which games count)
4. **Data completeness** achieved (all games stored)
5. **User experience** enhanced (better context for season performance)

**Example**: Ohio State fans see all 5 games (not 4) and understand that Week 2 vs Grambling (FCS) doesn't affect rankings or record.

---

## 📞 Support & Questions

**Questions during development?**
- Check story files for detailed implementation notes
- Review test cases for expected behavior
- Consult BROWNFIELD_PRD.md for system architecture

**Blockers or issues?**
- Document in story file comments
- Flag in team communication
- Consider rollback if critical issues arise

---

**Document Created By**: John (PM Agent)
**Date**: 2025-10-18
**Epic**: EPIC-003
**Status**: Ready for Development

---

**Good luck with the implementation! 🚀**

The stories are well-documented, tested, and ready to execute. Follow the sequence, run tests frequently, and you'll deliver a great feature that enhances user experience while maintaining ranking integrity.
