# EPIC-003 Production Deployment Guide

**Epic:** FCS Game Display for Schedule Completeness
**Deployment Date:** 2025-10-19
**Version:** 2.0.0
**Risk Level:** 🟡 Medium (Database migration required)

---

## Quick Overview

This deployment adds FCS game visibility to team schedules while maintaining ranking integrity by excluding FCS games from ELO calculations.

**What's changing:**
- Database schema (2 new fields)
- Backend API (3 files modified)
- Frontend (5 files modified)
- Data import logic (handles FCS games)
- **DATABASE MIGRATION REQUIRED**
- **DATA RE-IMPORT REQUIRED**

**Estimated deployment time:** 30-45 minutes (includes migration + data import)

---

## Pre-Deployment Checklist

- [x] Code pushed to GitHub (commit: 183af90)
- [ ] SSH access to production VPS
- [ ] Database backup created
- [ ] CFBD API key configured on server
- [ ] 45 minutes of focused time
- [ ] All 289 tests passing locally ✅

---

## Deployment Steps

### Step 1: Backup Production Database

**CRITICAL:** Always backup before migrations!

```bash
# SSH into production server
ssh user@your-server.com

# Navigate to application directory
cd /var/www/cfb-rankings
# Create backup
sudo cp cfb_rankings.db cfb_rankings.db.backup-$(date +%Y%m%d-%H%M%S)

# Verify backup exists
ls -lh cfb_rankings.db.backup-*
```

**✅ Checkpoint:** Backup file created and size looks reasonable

---

### Step 2: Pull Latest Code

```bash
# Still on production server
cd /var/www/cfb-rankings

# Stop the application service
sudo systemctl stop cfb-rankings

# Pull latest code from main branch
sudo git pull origin main

# Verify correct commit
git log -1 --oneline
# Should show: 183af90 EPIC-003: Complete FCS Game Display Implementation
```

**✅ Checkpoint:** Latest code pulled, correct commit hash visible

---

### Step 3: Run Database Migration

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # or your venv path

# Run migration script
python3 migrate_add_fcs_fields.py

# Expected output:
#   Starting migration...
#     Adding teams.is_fcs column...
#     Adding games.excluded_from_rankings column...
#     Creating index on games.excluded_from_rankings...
#
#   Verifying migration...
#     ✓ teams.is_fcs exists
#     ✓ games.excluded_from_rankings exists
#     ✓ Index idx_games_excluded_from_rankings exists
#     ✓ All existing games have excluded_from_rankings=False
#     ✓ All existing teams have is_fcs=False
#
#   Migration completed successfully!
```

**✅ Checkpoint:** Migration completed with all verification checks passing

**🚨 Rollback Plan (if migration fails):**
```bash
# Restore from backup
sudo cp cfb_rankings.db.backup-TIMESTAMP cfb_rankings.db

# Restart service with old code
sudo git reset --hard HEAD~1
sudo systemctl start cfb-rankings
```

---

### Step 4: Restart Application Service

```bash
# Restart the service to load new code
sudo systemctl restart cfb-rankings

# Check service status
sudo systemctl status cfb-rankings

# Should show: active (running)

# Check application logs
sudo journalctl -u cfb-rankings -n 50 --no-pager

# Look for:
#   "Database initialized successfully!"
#   "Application startup complete."
#   "Uvicorn running on..."
```

**✅ Checkpoint:** Service running, no errors in logs

---

### Step 5: Verify API Endpoints

```bash
# Test basic API endpoint
curl http://localhost:8000/api/stats

# Test team schedule endpoint (pick any team ID)
curl http://localhost:8000/api/teams/82/schedule?season=2025 | python3 -m json.tool

# Look for new fields in response:
#   "excluded_from_rankings": false/true
#   "is_fcs": false/true
#   "opponent_conference": "P5"/"G5"/"FCS"
```

**✅ Checkpoint:** API returning data with new fields

---

### Step 6: Re-Import Game Data with FCS Games

**IMPORTANT:** This step imports FCS games into the database.

```bash
# Ensure CFBD API key is set
export CFBD_API_KEY='your-api-key-here'

# Or verify it's in .env file
cat .env | grep CFBD_API_KEY

# Run import script
echo "yes" | python3 import_real_data.py

# This will:
#   1. Reset the database (keep backup!)
#   2. Import all FBS teams
#   3. Import FBS vs FBS games (processed for rankings)
#   4. Import FBS vs FCS games (excluded from rankings)
#   5. Skip FCS vs FCS games
#
# Expected output:
#   ✓ Imported 136 teams
#   Week 1...
#     Team A defeats Team B 35-21
#     Team C vs FCS Opponent (FCS - not ranked)
#   ...
#   Final Summary:
#     - XXX FBS games imported
#     - YYY FCS games imported (not ranked)
```

**⏱️ This step takes 5-10 minutes** depending on API response times.

**✅ Checkpoint:** Import completed, FCS games visible in output

---

### Step 7: Verify Frontend Changes

```bash
# Test from local machine
# Replace with your actual production URL

# Main rankings page
curl https://your-domain.com/frontend/index.html | grep "info-box"
# Should find the FCS info box HTML

# Team detail page (Ohio State as example)
curl https://your-domain.com/frontend/team.html | grep "FCS"
# Should find FCS badge styling and info box
```

**✅ Checkpoint:** Frontend files deployed correctly

---

### Step 8: Manual UI Verification

**Open your browser and test:**

1. **Main Rankings Page** (`https://your-domain.com/frontend/`)
   - [ ] Info box visible: "Team records and rankings reflect FBS opponents only..."
   - [ ] Team records show "FBS" note (e.g., "5-0 FBS")
   - [ ] Hover shows tooltip: "Record includes FBS opponents only"

2. **Team Detail Page** (pick a team with FCS games, e.g., Ohio State)
   - [ ] Schedule shows ALL weeks (no gaps)
   - [ ] FCS games have gray background
   - [ ] FCS badge appears next to opponent name
   - [ ] FCS badge tooltip: "FCS opponent - not included in rankings"
   - [ ] Team record shows "FBS Only" note
   - [ ] Info box above schedule explains FCS exclusion

3. **Test Specific Examples:**
   - Ohio State Week 2 vs Grambling (should be gray with FCS badge)
   - Georgia Week 2 vs Austin Peay (should be gray with FCS badge)
   - Any team's FBS games (should have normal styling)

**✅ Checkpoint:** All UI elements displaying correctly

---

### Step 9: Verify Ranking Integrity

**Critical verification that FCS games don't affect rankings:**

```bash
# Get Ohio State's record and ranking
curl http://localhost:8000/api/teams/82 | python3 -m json.tool

# Check:
#   "wins": should reflect FBS games only (not include Grambling)
#   "losses": should reflect FBS games only
#   "elo_rating": should be calculated from FBS games only

# Verify SOS calculation excludes FCS games
curl http://localhost:8000/api/rankings/current?season=2025 | python3 -m json.tool | grep -A5 "Ohio State"

# "sos": should be average of FBS opponents only (not include FCS)
```

**✅ Checkpoint:** Rankings unchanged, FCS games properly excluded

---

## Post-Deployment Monitoring

### First 24 Hours

**Monitor these logs:**
```bash
# Application errors
sudo journalctl -u cfb-rankings -f

# Nginx access logs (if using nginx)
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

**Watch for:**
- ❌ 500 errors in API calls
- ❌ Database lock errors
- ❌ Missing FCS games in schedules
- ❌ Incorrect team records (including FCS games)

---

## Rollback Procedure

**If critical issues are found:**

```bash
# Step 1: SSH into server
ssh user@your-server.com
cd /var/www/cfb-rankings

# Step 2: Stop service
sudo systemctl stop cfb-rankings

# Step 3: Restore database backup
sudo cp cfb_rankings.db.backup-TIMESTAMP cfb_rankings.db

# Step 4: Rollback code to previous commit
sudo git reset --hard a3c1899  # Previous commit before EPIC-003

# Step 5: Restart service
sudo systemctl start cfb-rankings

# Step 6: Verify rollback
curl http://localhost:8000/api/stats
# Should show old version without FCS fields
```

---

## Success Criteria

**Deployment is successful when:**

- ✅ All 289 tests passing on production server
- ✅ Database migration completed without errors
- ✅ API endpoints returning new fields (excluded_from_rankings, is_fcs)
- ✅ Frontend displays FCS games with proper styling
- ✅ Team records show "FBS Only" clarification
- ✅ Info boxes visible on rankings and team pages
- ✅ FCS games excluded from ELO calculations (verify SOS unchanged)
- ✅ No 500 errors in application logs
- ✅ Zero user-facing errors reported

---

## Testing Checklist Post-Deployment

Run these tests to confirm everything works:

```bash
# API Tests
curl http://localhost:8000/api/stats
curl http://localhost:8000/api/teams/82/schedule?season=2025
curl http://localhost:8000/api/rankings/current?season=2025

# Database Tests
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE excluded_from_rankings=1;"
# Should return number of FCS games imported

sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM teams WHERE is_fcs=1;"
# Should return number of FCS teams created
```

---

## Support & Troubleshooting

### Issue: "Migration script not found"
**Solution:** Make sure you pulled latest code with `git pull origin main`

### Issue: "Database is locked"
**Solution:**
```bash
sudo systemctl stop cfb-rankings
# Try migration again
python3 migrate_add_fcs_fields.py
sudo systemctl start cfb-rankings
```

### Issue: "FCS games not showing in UI"
**Solution:**
1. Clear browser cache (Cmd+Shift+R / Ctrl+Shift+R)
2. Check API response: `curl localhost:8000/api/teams/82/schedule?season=2025`
3. Verify data re-import completed successfully

### Issue: "Team records still include FCS games"
**Solution:** This is a DATA issue, not code issue:
1. Re-run import script: `echo "yes" | python3 import_real_data.py`
2. Verify FCS games have `excluded_from_rankings=True`

---

## Contact

**Deployed By:** Claude Code
**Deployment Date:** 2025-10-19
**Commit Hash:** 183af90
**Epic:** EPIC-003

For issues or questions, check:
- GitHub Issues: https://github.com/bdaileySNHU/cfb-rankings/issues
- Application Logs: `sudo journalctl -u cfb-rankings`
