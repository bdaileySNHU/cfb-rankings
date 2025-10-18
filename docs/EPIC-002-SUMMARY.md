# EPIC-002 Planning Summary

**Date Created:** 2025-10-18
**Created By:** John (PM Agent)
**Status:** ✅ Ready for Development

---

## 📋 What Was Created

### Epic Document
**File:** `docs/epic-002-dynamic-season-management.md`

**Epic Goal:** Eliminate hardcoded season years and improve import completeness while maintaining 100% backward compatibility with existing workflows.

### Three User Stories

1. **Story 004:** Add Dynamic Season & Week Detection Utility
   - **File:** `docs/stories/story-004-dynamic-season-detection-utility.md`
   - **Effort:** 3-5 hours
   - **Focus:** Create utility functions for season/week auto-detection

2. **Story 005:** Remove Hardcoded Season Years & Implement Dynamic Detection
   - **File:** `docs/stories/story-005-remove-hardcoded-seasons.md`
   - **Effort:** 4-6 hours
   - **Focus:** Replace all hardcoded `2025` with dynamic detection

3. **Story 006:** Add Import Validation & Completeness Checks
   - **File:** `docs/stories/story-006-import-validation-completeness.md`
   - **Effort:** 5-7 hours
   - **Focus:** Validate imports, detect missing games, report issues

**Total Estimated Effort:** 12-18 hours

---

## 🎯 Problems Being Solved

### Problem 1: Hardcoded Season Year
**Current State:**
- Season year `2025` hardcoded in 6+ locations
- Must manually update code every year
- Easy to miss updates, causing bugs

**After EPIC-002:**
- System automatically detects current season
- No manual updates required
- Works for 2025, 2026, 2027... automatically

### Problem 2: Incomplete Game Imports
**Current State:**
- Ohio State shows 4-0 but should be 6-0
- Games silently skipped with no warning
- No way to verify import completeness

**After EPIC-002:**
- Import scripts report: "Imported 48/50 games (96%)"
- Missing games listed with reasons
- Validation catches issues immediately

### Problem 3: No Current Week Detection
**Current State:**
- User must specify max week: "Enter max week (1-6)"
- Prompt hardcoded to suggest "Week 6"
- No automatic detection of latest week

**After EPIC-002:**
- Scripts automatically detect current week from API
- User sees: "Latest completed week: 8"
- Import proceeds automatically to current week

---

## 📊 Story Sequencing

```
Story 1: Build Utilities
   ↓
Story 2: Use Utilities (Remove Hardcoded Values)
   ↓
Story 3: Add Validation
```

**Why this order?**
1. Story 1 creates foundation (utility functions)
2. Story 2 uses those utilities to remove hardcoded values
3. Story 3 adds polish (validation) on top of working system

---

## 🔧 Technical Changes Summary

### Backend Changes
**Files Modified:**
- `cfbd_client.py` - Add `get_current_season()`, `get_current_week()`, `estimate_current_week()`
- `import_real_data.py` - Remove hardcoded `2025`, add validation
- `update_games.py` - Add auto-detection, add validation
- `main.py` - Add `/api/seasons/active` endpoint

### Frontend Changes
**Files Modified:**
- `frontend/js/api.js` - Add `getActiveSeason()` method
- `frontend/games.html` - Use dynamic season from API
- `frontend/js/comparison.js` - Use dynamic season from API

### New Features
- **CLI Flags:**
  - `--season YYYY` - Override detected season
  - `--max-week N` - Override detected max week
  - `--validate-only` - Dry-run mode
  - `--strict` - Fail on validation warnings

- **API Endpoints:**
  - `GET /api/seasons/active` - Returns currently active season

---

## ✅ Success Criteria

### When EPIC-002 is Complete:

1. **No Hardcoded Years:**
   - Zero instances of `2025` in production code (tests excluded)
   - System works for any year without code changes

2. **Automatic Detection:**
   - Import scripts detect season and week automatically
   - Frontend fetches active season from backend
   - User sees detected values before import starts

3. **Data Quality:**
   - Import validation reports completeness
   - Missing games identified with reasons
   - User can verify 100% import rate

4. **Zero Breaking Changes:**
   - All 236 existing tests pass
   - Existing workflows continue to work
   - New features are opt-in via flags

5. **Documentation:**
   - `docs/UPDATE-GAME-DATA.md` updated
   - Script help text updated
   - Troubleshooting guide for import issues

---

## 🔄 Backward Compatibility

### What Stays the Same:
- ✅ Database schema (no migrations)
- ✅ Existing API endpoints
- ✅ Import script workflow
- ✅ Frontend functionality
- ✅ All 236 tests pass without modification

### What's Added:
- ✨ Dynamic season detection
- ✨ Automatic week detection
- ✨ Import validation
- ✨ New CLI flags (optional)
- ✨ New API endpoint (optional)

### What Changes:
- 🔄 Hardcoded `2025` → Dynamic detection
- 🔄 Manual week input → Auto-detection
- 🔄 Silent failures → Verbose reporting

---

## 📈 User Impact

### Before EPIC-002:
```bash
$ python3 import_real_data.py

How many weeks would you like to import?
(The 2025 season is currently through Week 6)
Enter max week (1-6): 6

Importing games...
Week 1: Ohio State defeats Minnesota 42-3
Week 2: [No games shown - silently skipped]
...
✓ Imported 296 games
```

**User doesn't know:**
- If 296 is all games or just some
- Why Week 2 Ohio State game is missing
- If system will work next year

### After EPIC-002:
```bash
$ python3 import_real_data.py

✓ API Connection: OK
✓ Detected current season: 2025
✓ Latest completed week: 8

Importing Week 1...
✓ Week 1: Imported 50/50 games (100%)

Importing Week 2...
⚠ Week 2: Imported 48/50 games (96%)
  Skipped:
    - Ohio State @ Kent State (Kent State not in database - FCS)
    - Alabama @ Akron (Akron not in database - FCS)

...

================================================================================
IMPORT SUMMARY
================================================================================
Total Games: 384/400 (96%)
Total Skipped: 16 (14 FCS opponents, 2 teams not found)

⚠ WARNING: Some teams not found in database.
See skipped games above for details.
================================================================================
```

**User now knows:**
- Exact import completeness (96%)
- Why games were skipped (FCS opponents)
- System detected current season/week automatically
- System will work next year without code changes

---

## 🎓 Lessons & Best Practices

### Design Decisions Made:

1. **Opt-In Strictness:**
   - Validation warnings by default
   - Errors only with `--strict` flag
   - Prevents blocking existing workflows

2. **Graceful Fallbacks:**
   - Frontend falls back to current year if API fails
   - Scripts use calendar estimation if CFBD API down
   - System never crashes on detection failure

3. **Clear Communication:**
   - Verbose output shows what system detected
   - User confirms before import proceeds
   - Errors explain what went wrong and how to fix

4. **Zero Risk to Existing System:**
   - No database schema changes
   - No breaking API changes
   - All new code is additive only

---

## 📚 Documentation Created

### Epic & Stories
- `docs/epic-002-dynamic-season-management.md` (Main epic document)
- `docs/stories/story-004-dynamic-season-detection-utility.md`
- `docs/stories/story-005-remove-hardcoded-seasons.md`
- `docs/stories/story-006-import-validation-completeness.md`

### Planning Summary
- `docs/EPIC-002-SUMMARY.md` (This document)

### To Be Updated (During Implementation)
- `docs/UPDATE-GAME-DATA.md` (Add validation examples)
- `README.md` (Mention dynamic season management)
- Script help text (`--help` output)

---

## 🚀 Next Steps

### For Dev Agent (James):

1. **Review Epic and Stories:**
   - Read `docs/epic-002-dynamic-season-management.md`
   - Read all 3 story documents

2. **Start with Story 1:**
   - Implement utility functions in `cfbd_client.py`
   - Write unit tests
   - Verify utilities work correctly

3. **Proceed to Story 2:**
   - Use utilities from Story 1
   - Remove hardcoded values
   - Add new API endpoint

4. **Complete with Story 3:**
   - Add validation functions
   - Implement validation modes
   - Create comprehensive import reports

### For Product Owner:

1. **Review and Approve:**
   - Epic scope and goals
   - Story acceptance criteria
   - Estimated effort

2. **Prioritize:**
   - Confirm high priority
   - Allocate dev time

3. **Track Progress:**
   - Monitor story completion
   - Review validation output quality
   - Approve for production deployment

---

## ⏱️ Timeline Estimate

**Sprint Capacity:** Assuming 20 hours/week dev capacity

- **Week 1:** Story 1 + Story 2 (7-11 hours)
- **Week 2:** Story 3 + Testing + Documentation (5-7 hours)

**Total Duration:** 1-2 weeks

---

## ✨ Expected Outcome

After EPIC-002 completion, the College Football Rankings system will:

1. ✅ **Automatically work for future seasons** without code changes
2. ✅ **Detect current week** and import all available games
3. ✅ **Validate completeness** and report missing games
4. ✅ **Identify data issues** before they affect rankings
5. ✅ **Maintain backward compatibility** with existing workflows

**User Confidence:** Users will trust that the system has complete, accurate data because validation proves it.

**Maintenance Burden:** Eliminated annual code updates for season year changes.

**Data Quality:** Improved through validation and completeness checks.

---

**Epic Planning Complete:** ✅
**Ready for Development:** ✅
**All Stories Documented:** ✅
**Success Criteria Defined:** ✅

**Next:** Hand off to Dev Agent for implementation!

---

*Created by: John (PM Agent)*
*Date: 2025-10-18*
*Epic: EPIC-002 - Dynamic Season Management & Complete Game Import*
