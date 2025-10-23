# Production Deployment Guide

**Latest Epic:** EPIC-010 AP Poll Prediction Comparison
**Previous Epics:** EPIC-009 Prediction Accuracy, EPIC-006 Current Week Display, EPIC-003 FCS Game Display
**Deployment Date:** 2025-10-23
**Version:** 4.0.0
**Risk Level:** 🟡 Medium (Database migration + data import required)

---

## Quick Overview - EPIC-010

This deployment adds AP Poll prediction comparison to demonstrate the superiority of the ELO system over traditional AP Poll rankings. The system now compares ELO predictions against AP Poll-implied predictions.

**What's changing (EPIC-010):**
- Backend API (1 new endpoint: `/api/predictions/comparison`)
- Backend services (new `ap_poll_service.py` module)
- Database schema (new `ap_poll_rankings` table)
- Data import (AP Poll rankings from CFBD API)
- Frontend (complete rewrite of comparison page)
- **DATABASE MIGRATION REQUIRED** (new ap_poll_rankings table)
- **DATA IMPORT REQUIRED** (AP Poll data + backfill predictions)

**Estimated deployment time:** 20-30 minutes (migration + data import)

**Results:** ELO system achieves 88.3% accuracy vs AP Poll's 73.7% (+14.6pp advantage)

---

## Pre-Deployment Checklist (EPIC-010)

- [ ] All unit tests passing
- [ ] Backend server running locally without errors
- [ ] Frontend displays comparison page correctly
- [ ] Git commit created with comprehensive message
- [ ] Deployment documentation updated

## Deployment Steps (EPIC-010)

### Step 1: Deploy Code to Production Server

```bash
# On production server
cd ~/Stat-urday\ Synthesis
git pull origin main
```

### Step 2: Run Database Migration

```bash
# Create ap_poll_rankings table
python3 migrate_add_ap_poll_rankings.py
```

**Expected output:**
```
✓ Created ap_poll_rankings table
✓ Created indexes
```

### Step 3: Import AP Poll Data

```bash
# Import AP Poll rankings for all weeks
python3 scripts/import_ap_poll_only.py
# When prompted:
# - Season: 2025 (or press Enter for default)
# - Weeks: 1-10 (or whatever weeks you have data for)
```

**Expected output:**
```
Week 1...
  ✓ Imported 25 rankings
Week 2...
  ✓ Imported 25 rankings
...
Total rankings imported: 225
```

### Step 4: Backfill Predictions for Completed Games

```bash
# Create predictions for all completed games
python3 scripts/backfill_historical_predictions.py
```

**Expected output:**
```
  Created 50 predictions...
  Created 100 predictions...
  ...
  Created 800 predictions...

Backfill complete!
  Total games: 806
  Predictions created: 806
```

### Step 5: Restart Backend Service

```bash
# Restart the FastAPI service
sudo systemctl restart cfb-rankings
# Or if using PM2:
pm2 restart cfb-rankings
```

### Step 6: Verify Deployment

1. **Test API endpoint:**
```bash
curl https://your-domain.com/api/predictions/comparison?season=2025
```

Expected: JSON with comparison statistics

2. **Visit comparison page:**
   - Navigate to: `https://your-domain.com/frontend/comparison.html`
   - Or click "Prediction Comparison" in navigation

3. **Verify data displays:**
   - Hero stats show accuracy percentages
   - Chart displays accuracy over time
   - Disagreement table shows games where systems disagreed

### Rollback Plan (If Needed)

If deployment fails:

```bash
# Revert to previous commit
git revert HEAD
sudo systemctl restart cfb-rankings

# Drop new table if needed
sqlite3 cfb_rankings.db "DROP TABLE IF EXISTS ap_poll_rankings;"
```

---

## Previous Deployments

<details>
<summary><strong>EPIC-009: Prediction Accuracy Tracking & Display</strong> (Click to expand)</summary>

**Deployment Date:** 2025-10-23
**Version:** 3.0.0
**Risk Level:** 🟢 Low

This deployment added prediction accuracy tracking and display.

**What changed:**
- Backend API (3 new endpoints)
- Frontend (accuracy displays on rankings/team pages)
- No database migration required
- No data re-import required

</details>

<details>
<summary><strong>EPIC-003: FCS Game Display</strong> (Click to expand)</summary>

**Deployment Date:** 2025-10-19
**Version:** 2.0.0
**Risk Level:** 🟡 Medium (Database migration required)

This deployment added FCS game visibility to team schedules while maintaining ranking integrity by excluding FCS games from ELO calculations.

**What changed:**
- Database schema (2 new fields)
- Backend API (3 files modified)
- Frontend (5 files modified)
- Data import logic (handles FCS games)
- **DATABASE MIGRATION REQUIRED**
- **DATA RE-IMPORT REQUIRED**

**Estimated deployment time:** 30-45 minutes (includes migration + data import)

</details>

---

## Pre-Deployment Checklist (EPIC-009)

- [ ] Code pushed to GitHub (all EPIC-009 commits)
- [ ] SSH access to production VPS
- [ ] Database backup created (optional for EPIC-009, but recommended)
- [ ] 10 minutes of focused time
- [ ] All tests passing locally ✅
- [ ] Frontend tested locally (prediction accuracy displays correctly)

---

## Deployment Steps (EPIC-009)

### Step 1: Pull Latest Code

```bash
# SSH into production server
ssh user@your-server.com

# Navigate to application directory
cd /var/www/cfb-rankings

# Stop the application service
sudo systemctl stop cfb-rankings

# Pull latest code from main branch
sudo git pull origin main

# Verify correct commit (should show EPIC-009 commits)
git log --oneline -5
```

**✅ Checkpoint:** Latest code pulled, EPIC-009 commits visible

---

### Step 2: Restart Application Service

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

### Step 3: Verify EPIC-009 API Endpoints

```bash
# Test prediction accuracy endpoints
curl http://localhost:8000/api/predictions/accuracy?season=2024 | python3 -m json.tool

# Expected response:
# {
#   "season": 2024,
#   "evaluated_predictions": X,
#   "correct_predictions": Y,
#   "accuracy_percentage": Z.Z
# }

# Test team-specific accuracy (Ohio State example)
curl http://localhost:8000/api/predictions/accuracy/team/82?season=2024 | python3 -m json.tool

# Test stored predictions endpoint
curl "http://localhost:8000/api/predictions/stored?season=2024&evaluated_only=true" | python3 -m json.tool
```

**✅ Checkpoint:** All three EPIC-009 endpoints returning data

---

### Step 4: Verify Frontend Changes (EPIC-009)

**Open your browser and test:**

1. **Main Rankings Page** (`https://your-domain.com/frontend/`)
   - [ ] Prediction accuracy banner visible (if predictions exist)
   - [ ] Banner shows overall accuracy percentage
   - [ ] Banner shows "X correct out of Y predictions"
   - [ ] Banner only appears if evaluated_predictions > 0

2. **Team Detail Page** (pick any team with predictions)
   - [ ] Prediction accuracy stat card visible
   - [ ] Shows team-specific accuracy percentage
   - [ ] Shows "X/Y correct" format
   - [ ] Color coded: green (≥70%), blue (≥50%), red (<50%)

3. **Team Schedule Table:**
   - [ ] "Prediction" column added to schedule
   - [ ] Shows "W (65%)" or "L (35%)" format for each game
   - [ ] Completed games: green background if correct, red if incorrect
   - [ ] Future games: gray/italic styling
   - [ ] Hover tooltip shows "Correct prediction" or "Incorrect prediction"

**✅ Checkpoint:** All EPIC-009 UI elements displaying correctly

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
