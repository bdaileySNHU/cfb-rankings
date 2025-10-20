# EPIC-006: Current Week Display Accuracy - Summary

## Epic Overview

**Goal:** Fix the current week display showing "Week 7" instead of "Week 8" and implement automatic week tracking

**Priority:** High
**Estimated Total Effort:** 6-10 hours
**Status:** Ready for Development

---

## Problem Statement

The rankings page displays "Current Week: 7" but the actual current week of the 2025 college football season is Week 8. The `Season.current_week` field in the database is not being automatically updated when new games are processed.

---

## Solution: 3-Story Epic

### Story 001: Investigate Current Week Data Source and Update Mechanism ✅

**Purpose:** Understand why the week is wrong and identify root cause

**Key Tasks:**
- Check database: `SELECT current_week FROM seasons WHERE year = 2025`
- Review `import_real_data.py` for initial week setting
- Review `scripts/weekly_update.py` to see if week is updated
- Identify root cause and recommend fix approach

**Effort:** 2-3 hours

**Deliverables:**
- Root cause analysis
- Recommendation for Story 002 implementation

---

### Story 002: Implement Automatic Current Week Detection from CFBD API ✅

**Purpose:** Fix the week display and add automatic updates

**Key Changes:**
- **Immediate fix:** `UPDATE seasons SET current_week = 8 WHERE year = 2025`
- **Automatic detection:** Add logic to detect max week from processed games
- **Manual override:** New endpoint `/api/admin/update-current-week`
- **Integration:** Update `scripts/weekly_update.py` to set week automatically

**Effort:** 3-4 hours

**Deliverables:**
- Database shows Week 8
- Frontend displays "Current Week: 8"
- Automatic week updates during weekly job
- Admin endpoint for emergency corrections

---

### Story 003: Add Current Week Validation and Monitoring ✅

**Purpose:** Ensure week tracking stays accurate long-term

**Key Changes:**
- **Validation:** Week must be 0-15 (reject invalid values)
- **Logging:** Track week changes in UpdateTask metadata
- **Tests:** Comprehensive coverage for week detection
- **Documentation:** Manual correction procedures

**Effort:** 2-3 hours

**Deliverables:**
- Week validation prevents errors
- UpdateTask logs track week changes
- Tests verify week detection works
- Documentation for troubleshooting

---

## Technical Approach

### Immediate Fix (Story 002)
```sql
UPDATE seasons SET current_week = 8 WHERE year = 2025;
```

### Automatic Detection (Story 002)
```python
# Find max week from processed games
max_week = db.query(func.max(Game.week)).filter(
    Game.season == 2025,
    Game.is_processed == True
).scalar()

season.current_week = max_week
```

### Validation (Story 003)
```python
def validate_week_number(week: int) -> bool:
    return 0 <= week <= 15
```

---

## Implementation Sequence

**Recommended order:**

1. **Story 001 first** → Investigation and root cause analysis
2. **Story 002 second** → Fix database + implement automatic updates
3. **Story 003 third** → Add validation and monitoring

**Each story can be deployed independently** for incremental value delivery.

---

## Files Modified Summary

**Story 001:**
- None (read-only investigation)

**Story 002:**
- `scripts/weekly_update.py` (~40 lines)
- `main.py` (~30 lines for admin endpoint)
- Database: Manual UPDATE

**Story 003:**
- `scripts/weekly_update.py` (~30 lines for validation)
- `tests/test_weekly_update.py` (~100 lines)
- `docs/EPIC-006-WEEK-MANAGEMENT.md` (new)

---

## Deployment Plan

### Story 002 Deployment

```bash
# 1. Pull latest code
cd /var/www/cfb-rankings
git pull origin main

# 2. Update database
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"

# 3. Restart server
sudo systemctl restart gunicorn

# 4. Verify
curl http://your-domain.com/api/stats | jq .current_week
# Should return: 8
```

### Rollback Procedure

```sql
-- Emergency rollback: Manually set correct week
UPDATE seasons SET current_week = 8 WHERE year = 2025;
```

Or use admin endpoint:
```bash
curl -X POST http://your-domain.com/api/admin/update-current-week \
  -H "Content-Type: application/json" \
  -d '{"year": 2025, "week": 8}'
```

---

## Success Metrics

### Quantitative
- ✅ Frontend displays "Week 8" (or actual current week)
- ✅ Weekly update job successfully updates week on next run
- ✅ Zero manual interventions needed after initial fix
- ✅ All tests pass

### Qualitative
- ✅ Users no longer confused about current week
- ✅ System appears up-to-date and accurate
- ✅ Team has confidence in automatic week tracking

---

## Risk Assessment

### Low Risk Epic

**Why low risk:**
- Database-only changes (no schema modifications)
- Simple validation logic (week 0-15 range)
- Manual override available if automatic detection fails
- No frontend changes required
- Easy rollback (manual SQL UPDATE)

**Mitigation strategies:**
- Thorough investigation in Story 001
- Validation prevents invalid weeks
- Logging provides audit trail
- Manual admin endpoint for corrections

---

## Documentation Updates

### EPIC-006-WEEK-MANAGEMENT.md (Story 003)
- Manual correction procedures
- Validation rules
- Troubleshooting guide
- Monitoring queries

### README.md
- No changes needed (internal fix)

### Code Comments
- Week validation logic explained
- Automatic detection approach documented
- Admin endpoint usage examples

---

## Future Enhancements (Out of Scope)

1. **CFBD Calendar API Integration** - Use calendar endpoint for more authoritative week detection
2. **Week Countdown Widget** - Show weeks remaining until postseason
3. **Historical Week Timeline** - Track week-by-week changes over time
4. **Week-Based Navigation** - Filter rankings by specific weeks

---

## Story Documents

- **Epic:** `docs/EPIC-006-CURRENT-WEEK-ACCURACY.md`
- **Story 001:** `docs/EPIC-006-STORY-001.md`
- **Story 002:** `docs/EPIC-006-STORY-002.md`
- **Story 003:** `docs/EPIC-006-STORY-003.md`
- **Summary:** `docs/EPIC-006-SUMMARY.md` (this document)

---

**Epic Created:** 2025-10-20
**Epic Owner:** Product Manager (John)
**Ready for Development:** ✅

---

## Quick Start for Developers

### To implement Story 001 (Investigation):

```bash
# 1. Check database
sqlite3 cfb_rankings.db "SELECT year, current_week, is_active FROM seasons WHERE year = 2025;"

# 2. Review import script
grep -n "current_week" import_real_data.py

# 3. Review weekly update
grep -n "current_week" scripts/weekly_update.py

# 4. Check CFBD API for latest games
# Look at max week in database
sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season = 2025 AND is_processed = 1;"

# 5. Document findings in Story 001 template
```

### To implement Story 002 (Fix + Automation):

```bash
# 1. Immediate database fix (local)
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"

# 2. Add update_current_week() function to scripts/weekly_update.py

# 3. Add admin endpoint to main.py

# 4. Test locally
python3 main.py
curl http://localhost:8000/api/stats | jq .current_week

# 5. Commit and deploy
git add scripts/weekly_update.py main.py
git commit -m "Implement automatic current week detection (EPIC-006 Story 002)"
git push

# 6. Deploy to production
ssh user@vps
cd /var/www/cfb-rankings
git pull
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"
sudo systemctl restart gunicorn
```

### To implement Story 003 (Validation + Monitoring):

```bash
# 1. Add validate_week_number() to scripts/weekly_update.py

# 2. Add test cases to tests/test_weekly_update.py

# 3. Create documentation
touch docs/EPIC-006-WEEK-MANAGEMENT.md

# 4. Run tests
pytest tests/test_weekly_update.py -v

# 5. Commit
git add scripts/weekly_update.py tests/test_weekly_update.py docs/EPIC-006-WEEK-MANAGEMENT.md
git commit -m "Add week validation and monitoring (EPIC-006 Story 003)"
git push
```

---

**Let's ship it!** 🚀
