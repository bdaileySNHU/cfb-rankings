# EPIC-026 Phase 1 Production Deployment Guide

**Epic:** Transfer Portal Team Rankings - Phase 1 (Core Implementation)
**Version:** 1.0
**Created:** 2025-12-04
**Commit:** 2d9befd

---

## Overview

### What's Being Deployed

EPIC-026 Phase 1 implements star-based transfer portal ranking system to replace hardcoded transfer_rank = 999.

**Key Changes:**
- **Database schema:** 3 new columns on teams table (transfer_portal_points, transfer_portal_rank, transfer_count)
- **New service:** `transfer_portal_service.py` - Star-based scoring algorithm
- **Import integration:** Automatic transfer data fetching and ranking during import
- **Verified data:** 2024 season tested - 297 teams ranked, 3,378 transfers processed

**Impact:**
- Teams will have real transfer portal rankings (1-N) instead of 999
- No user-facing UI changes yet (backend only - Phase 2 will add API/frontend)
- Full backward compatibility maintained (old transfer_rank field deprecated but kept)
- Import time increases by ~30 seconds for transfer portal API fetch

**Completed Stories:**
- ✅ Story 26.2: CFBD Client Method
- ✅ Story 26.3: Scoring Algorithm
- ✅ Story 26.4: Database Schema
- ✅ Story 26.5: Import Integration

---

## Pre-Deployment Checklist

### Requirements
- [ ] SSH access to production server
- [ ] Database backup permissions
- [ ] Application restart permissions
- [ ] CFBD API key configured
- [ ] Verify commit: `2d9befd`

### Pre-Deployment Verification

```bash
# On local machine - verify correct commit
cd "/Users/bryandailey/Stat-urday Synthesis"
git log --oneline -1
# Should show: 2d9befd Complete EPIC-026 Phase 1: Transfer Portal Rankings Core Implementation

# Verify migration script exists
ls -l migrate_add_transfer_portal_fields.py

# Verify new service exists
ls -l transfer_portal_service.py
```

---

## Deployment Steps

### Step 1: Push Code to Repository

**Location:** Local development machine

```bash
cd "/Users/bryandailey/Stat-urday Synthesis"

# Verify current status
git status
git log --oneline -1

# Push to remote
git push origin main

# Verify push successful
git log origin/main --oneline -1
```

**Expected:**
- Commit hash: `2d9befd`
- 3 files changed: import_real_data.py, models.py, transfer_portal_service.py

---

### Step 2: SSH to Production Server

```bash
ssh cfb
# Or use your configured alias: ssh your-production-server
```

---

### Step 3: Navigate to Application Directory

```bash
cd /var/www/cfb-rankings
pwd  # Verify you're in the right place
```

---

### Step 4: Backup Current Database

**CRITICAL - DO NOT SKIP**

```bash
# Check if database exists
if [ -f cfb_rankings.db ]; then
  # Create backup with timestamp
  cp cfb_rankings.db cfb_rankings.db.backup_epic26_$(date +%Y%m%d_%H%M%S)
  echo "✓ Backup created"
  ls -lh cfb_rankings.db.backup_epic26_*
else
  echo "⚠️  Database not found - verify path"
fi
```

**Verify backup:**
- File size similar to original database
- Timestamp in filename is current
- File permissions allow read

---

### Step 5: Stop Application Service

```bash
sudo systemctl stop cfb-rankings
```

**Verify stopped:**
```bash
sudo systemctl status cfb-rankings
# Should show: "inactive (dead)"
```

**Why stop the service:**
- Releases database lock
- Prevents write conflicts during migration
- Ensures clean restart with new code

---

### Step 6: Pull Latest Code

```bash
# Check current branch
git branch
# Should be on: main

# Pull latest changes
git pull origin main

# Verify commit
git log --oneline -1
# Should show: 2d9befd Complete EPIC-026 Phase 1...
```

**Verify new files:**
```bash
ls -l transfer_portal_service.py
ls -l migrate_add_transfer_portal_fields.py
```

**Expected output:**
- Both files exist
- transfer_portal_service.py ~6-8 KB
- migrate_add_transfer_portal_fields.py ~3 KB

---

### Step 7: Run Database Migration

```bash
sudo python3 migrate_add_transfer_portal_fields.py
```

**Expected Output:**
```
================================================================================
MIGRATION: Add transfer portal fields
EPIC-026: Transfer Portal Team Rankings - Phase 1
================================================================================

Adding transfer_portal_points column...
✓ Added transfer_portal_points
Adding transfer_portal_rank column...
✓ Added transfer_portal_rank
Adding transfer_count column...
✓ Added transfer_count

Verifying migration...
✓ Verification: 3 transfer portal columns in teams table
✓ 130 existing teams will have default values:
  - transfer_portal_points: 0
  - transfer_portal_rank: 999 (N/A)
  - transfer_count: 0

================================================================================
MIGRATION COMPLETE
================================================================================

Next steps:
  1. Re-import data to populate transfer portal metrics
     Command: python3 import_real_data.py
  2. The import will automatically:
     - Fetch transfer portal data from CFBD API
     - Calculate star-based rankings
     - Update all teams with portal metrics

Note: Old 'transfer_rank' field is deprecated but kept for compatibility
```

**If migration shows "already exists" warnings:**
- This is OK - means migration was partially run before
- Verify all 3 columns exist (see verification step below)

**Verify migration:**
```bash
sqlite3 cfb_rankings.db "PRAGMA table_info(teams);" | grep -E "transfer_portal|transfer_count"
```

**Expected:**
```
42|transfer_portal_points|INTEGER|0|0|0
43|transfer_portal_rank|INTEGER|0|999|0
44|transfer_count|INTEGER|0|0|0
```

---

### Step 8: Verify CFBD API Key

```bash
# Check if API key is set
echo $CFBD_API_KEY

# If empty, check .env file
cat .env | grep CFBD_API_KEY

# If needed, export it
export CFBD_API_KEY='your-api-key-here'
```

**Important:** Transfer portal data fetch requires CFBD API key.

---

### Step 9: Re-Import Data

This populates the new transfer portal fields for all teams.

```bash
cd /var/www/cfb-rankings

# Run import (answer 'yes' to prompts)
echo "yes" | python3 import_real_data.py
```

**What to expect:**
- Import takes 3-5 minutes
- You'll see: "Fetching transfer portal data..."
- You'll see: "Calculating transfer portal rankings..."
- 2024 season data will be imported
- All teams will have transfer portal metrics

**Look for these log lines:**
```
Fetching transfer portal data...
Calculating transfer portal rankings...
Loaded transfer data for 297 teams
```

**If you see "Error fetching transfer portal data":**
- Verify CFBD_API_KEY is set
- Check network connectivity
- Continue anyway - teams will have default values (rank=999)

---

### Step 10: Verify Data Import

```bash
# Check that teams have transfer portal data
sqlite3 cfb_rankings.db <<EOF
SELECT name, transfer_portal_rank, transfer_portal_points, transfer_count
FROM teams
WHERE transfer_portal_rank != 999
ORDER BY transfer_portal_rank
LIMIT 10;
EOF
```

**Expected output:**
```
Colorado|1|2540|41
Georgia|2|2380|35
Alabama|3|2210|32
...
```

**If all teams show rank=999:**
- Transfer portal data fetch failed
- Check CFBD API key
- Check import logs for errors
- May need to run import again

---

### Step 11: Restart Application Service

```bash
sudo systemctl restart cfb-rankings
```

**Verify service started:**
```bash
sudo systemctl status cfb-rankings
# Should show: "active (running)"
```

**Check for errors:**
```bash
sudo journalctl -u cfb-rankings -n 50 --no-pager
```

**Look for:**
- "Application startup complete" or similar
- No Python tracebacks
- No database errors

---

### Step 12: Smoke Test API

```bash
# Test rankings endpoint
curl http://localhost:8000/api/rankings | head -20

# Should return JSON with rankings
# No errors in response
```

**Expected:**
- Valid JSON response
- Top 25 teams listed
- No error messages

**If API not responding:**
```bash
# Check service status
sudo systemctl status cfb-rankings

# Check error logs
sudo journalctl -u cfb-rankings -n 100
```

---

### Step 13: Verify Transfer Portal Data in Database

```bash
# Get transfer portal stats
sqlite3 cfb_rankings.db <<EOF
SELECT
  COUNT(*) as total_teams,
  COUNT(CASE WHEN transfer_portal_rank != 999 THEN 1 END) as ranked_teams,
  MIN(transfer_portal_rank) as best_rank,
  MAX(transfer_portal_points) as max_points
FROM teams;
EOF
```

**Expected:**
```
total_teams: 130+
ranked_teams: 297 (or similar)
best_rank: 1
max_points: 2540+ (Colorado typically #1)
```

---

### Step 14: Final Verification

```bash
# Quick sanity check - top 5 transfer portal teams
sqlite3 cfb_rankings.db <<EOF
SELECT
  name,
  transfer_portal_rank as rank,
  transfer_portal_points as points,
  transfer_count as transfers
FROM teams
WHERE transfer_portal_rank <= 5
ORDER BY transfer_portal_rank;
EOF
```

**Should see sensible results:**
- Colorado, Georgia, Alabama typically in top 5
- Points range: 2000-2500
- Transfer counts: 30-45

---

## Post-Deployment Monitoring

### First Hour
- [ ] Check service status: `sudo systemctl status cfb-rankings`
- [ ] Monitor logs: `sudo journalctl -u cfb-rankings -f`
- [ ] Test API endpoint: `curl http://localhost:8000/api/rankings`

### First Day
- [ ] Verify no error spikes in logs
- [ ] Check database file size (should be similar, maybe +1-2%)
- [ ] Verify application performance (no slowdown)

### Note
- Transfer portal fields are **not yet exposed via API** (Phase 2)
- No frontend display yet (Phase 2)
- Data is in database and ready for Phase 2 implementation

---

## Rollback Procedures

### If Migration Fails

```bash
# 1. Restore database from backup
sudo systemctl stop cfb-rankings
cp cfb_rankings.db.backup_epic26_TIMESTAMP cfb_rankings.db

# 2. Revert code
git reset --hard HEAD~1  # Back to before EPIC-026

# 3. Restart service
sudo systemctl start cfb-rankings

# 4. Verify
curl http://localhost:8000/api/rankings | head -20
```

### If Import Fails But Migration Succeeded

```bash
# Just re-run import (migration is idempotent)
echo "yes" | python3 import_real_data.py

# Migration will show "already exists" warnings - this is OK
```

---

## Troubleshooting

### Issue: Migration shows "column already exists"

**Cause:** Migration was already run

**Solution:**
```bash
# Verify all 3 columns exist
sqlite3 cfb_rankings.db "PRAGMA table_info(teams);" | grep -E "transfer_portal|transfer_count"

# If all 3 exist, proceed to Step 9 (re-import)
# If only some exist, restore from backup and re-run migration
```

---

### Issue: Import fails with "AttributeError: 'CFBDClient' has no attribute 'get_transfer_portal'"

**Cause:** Old code still loaded, new code not pulled

**Solution:**
```bash
# Verify you're on correct commit
git log --oneline -1

# Should show 2d9befd
# If not, pull again
git pull origin main

# Verify file exists
grep -n "def get_transfer_portal" cfbd_client.py
```

---

### Issue: All teams have transfer_portal_rank = 999

**Cause:** Transfer portal data fetch failed

**Solution:**
```bash
# Check API key
echo $CFBD_API_KEY

# Test API directly
curl -H "Authorization: Bearer $CFBD_API_KEY" \
  "https://api.collegefootballdata.com/player/portal?year=2024" | head -50

# If API works, re-run import
echo "yes" | python3 import_real_data.py
```

---

### Issue: Service won't start after deployment

**Cause:** Python syntax error or import error

**Solution:**
```bash
# Check service logs
sudo journalctl -u cfb-rankings -n 100

# Look for Python tracebacks
# If found, check the specific file/line mentioned

# Test import manually
cd /var/www/cfb-rankings
python3 -c "from transfer_portal_service import TransferPortalService; print('OK')"

# If import fails, code issue - may need to rollback
```

---

## Success Criteria

After deployment, verify:

- [x] Migration completed successfully (3 columns added)
- [x] Service running (`systemctl status cfb-rankings`)
- [x] API responding (`curl http://localhost:8000/api/rankings`)
- [x] Database populated with transfer portal data
- [x] Top teams have sensible transfer rankings (1-300 range)
- [x] No errors in service logs

---

## What's Next (Phase 2)

Phase 1 is complete! Next steps:

**Phase 2 - Should Have:**
- Story 26.6: API Response Updates (expose via REST API)
- Story 26.8: Validation (compare against 247Sports rankings)

**Phase 3 - Nice to Have:**
- Story 26.7: Frontend Display (show on team pages)
- Story 26.9: Preseason ELO Integration (factor into strength calculations)

---

## Reference Files

- Epic Planning: `docs/EPIC-026-TRANSFER-PORTAL-RANKINGS.md`
- Migration Script: `migrate_add_transfer_portal_fields.py`
- Service Implementation: `transfer_portal_service.py`
- Import Integration: `import_real_data.py` (lines 156-189)

---

**Deployment Guide Version:** 1.0
**Created:** 2025-12-04
**Last Updated:** 2025-12-04
