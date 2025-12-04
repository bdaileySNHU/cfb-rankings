# EPIC-026 Phase 2 Deployment Guide - Story 26.6

**Story:** API Response Updates
**Version:** 1.0
**Created:** 2025-12-04
**Commit:** fe99fa2

---

## Overview

Phase 2 Story 26.6 exposes transfer portal data via REST API endpoints.

### What's Being Deployed

**Code Changes Only - No Database Migration Required**

- ✅ Schema updates to include transfer portal fields in API responses
- ✅ Rankings endpoint now returns `transfer_portal_rank` and `recruiting_rank`
- ✅ Team detail endpoint returns full transfer portal metrics
- ✅ Backward compatible (old `transfer_rank` field kept as deprecated)

### Impact

- **User-facing:** Transfer portal data now available via API
- **Breaking changes:** None (all fields are optional/nullable)
- **Performance:** No impact (data already in database from Phase 1)

---

## Quick Deployment Steps

This is a **code-only deployment** - much simpler than Phase 1!

### On Production Server

```bash
# 1. SSH to server
ssh cfb
cd /var/www/cfb-rankings

# 2. Pull latest code
sudo git pull origin main

# Expected: fe99fa2 Complete EPIC-026 Phase 2 Story 26.6: API Response Updates

# 3. Restart service
sudo systemctl restart cfb-rankings

# 4. Verify service is running
sudo systemctl status cfb-rankings

# 5. Test API endpoints (see testing section below)
```

**That's it!** No database migration, no data import needed.

---

## Testing the API

### Test 1: Rankings Endpoint

```bash
# Get top 3 teams with transfer portal ranks
curl http://localhost:8000/api/rankings?limit=3 | python3 -m json.tool
```

**Expected Response:**
```json
{
  "week": 14,
  "season": 2025,
  "rankings": [
    {
      "rank": 1,
      "team_name": "Oregon",
      "elo_rating": 1687.45,
      "wins": 12,
      "losses": 0,
      "transfer_portal_rank": 15,
      "recruiting_rank": 12
    },
    ...
  ]
}
```

**Verify:**
- ✓ `transfer_portal_rank` field present
- ✓ `recruiting_rank` field present
- ✓ Values are not 999 (unless team truly has no data)

---

### Test 2: Team Detail Endpoint

```bash
# Get Colorado (team with #1 transfer portal rank)
# Replace {team_id} with actual Colorado team ID
curl http://localhost:8000/api/teams/{team_id} | python3 -m json.tool
```

**Expected Response:**
```json
{
  "id": 38,
  "name": "Colorado",
  "recruiting_rank": 52,
  "transfer_portal_rank": 1,
  "transfer_portal_points": 2540,
  "transfer_count": 41,
  "returning_production": 0.42,
  "elo_rating": 1542.18,
  ...
}
```

**Verify:**
- ✓ `transfer_portal_rank` = 1 (or low number)
- ✓ `transfer_portal_points` > 2000
- ✓ `transfer_count` = 30-45 range

---

### Test 3: All Teams Endpoint

```bash
# Get all teams (check first few)
curl http://localhost:8000/api/teams?limit=5 | python3 -m json.tool
```

**Verify:**
- ✓ All teams have transfer portal fields
- ✓ No HTTP 500 errors
- ✓ Schema matches expected structure

---

## API Response Changes

### Before (Phase 1)
```json
{
  "name": "Ohio State",
  "recruiting_rank": 5,
  "transfer_rank": 999  // Deprecated, always 999
}
```

### After (Phase 2)
```json
{
  "name": "Ohio State",
  "recruiting_rank": 5,
  "transfer_rank": 999,  // Still present (backward compatibility)
  "transfer_portal_rank": 23,  // NEW: Real ranking
  "transfer_portal_points": 1240,  // NEW: Star points
  "transfer_count": 18  // NEW: Number of transfers
}
```

---

## Troubleshooting

### Issue: transfer_portal_rank always shows 999

**Cause:** Phase 1 not deployed, or import didn't run

**Solution:**
```bash
# Check if Phase 1 migration ran
sqlite3 cfb_rankings.db "PRAGMA table_info(teams);" | grep transfer_portal

# Should see:
# transfer_portal_points|INTEGER|...
# transfer_portal_rank|INTEGER|...
# transfer_count|INTEGER|...

# If missing, run Phase 1 deployment first
```

---

### Issue: API returns 500 error

**Cause:** Schema mismatch or missing field

**Solution:**
```bash
# Check service logs
sudo journalctl -u cfb-rankings -n 50

# Look for Python tracebacks
# Common issue: field name mismatch between model and schema

# Verify code is latest
git log --oneline -1
# Should show: fe99fa2 Complete EPIC-026 Phase 2
```

---

### Issue: Fields show in /api/teams but not /api/rankings

**Cause:** Cache or old ranking_history records

**Solution:**
```bash
# Check that rankings endpoint code was updated
grep -n "transfer_portal_rank" ranking_service.py

# Should find it in get_current_rankings() method

# Restart service to clear any caches
sudo systemctl restart cfb-rankings
```

---

## Success Criteria

After deployment, verify:

- [x] Service running without errors
- [x] GET /api/rankings returns transfer_portal_rank
- [x] GET /api/teams/{id} returns all 3 transfer portal fields
- [x] Colorado (or top portal team) shows rank #1
- [x] No 500 errors in logs
- [x] Backward compatibility maintained (old transfer_rank still present)

---

## What's Next

### Completed Phase 2 Stories:
- ✅ Story 26.6: API Response Updates

### Remaining Phase 2 Work:
- ⏳ Story 26.7: Frontend Display (show on team pages)
- ⏳ Story 26.8: Validation (compare with 247Sports)

### Future Phase 3:
- Story 26.9: Preseason ELO Integration

---

## Rollback

If needed (code-only rollback):

```bash
cd /var/www/cfb-rankings
sudo git reset --hard HEAD~1  # Back to 30a813b (Phase 1)
sudo systemctl restart cfb-rankings
```

No database changes to revert - rollback is instant!

---

## Reference

- Epic: `docs/EPIC-026-TRANSFER-PORTAL-RANKINGS.md`
- Phase 1: `docs/EPIC-026-PHASE-1-DEPLOYMENT.md`
- Schema changes: `schemas.py`
- Endpoint logic: `main.py`, `ranking_service.py`

---

**Deployment Time:** 2-3 minutes
**Complexity:** Simple (code-only)
**Risk:** Low (backward compatible)

**Created:** 2025-12-04
**Version:** 1.0
