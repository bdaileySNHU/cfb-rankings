# Production Deployment Guide

**Latest Epic:** EPIC-009 Prediction Accuracy Tracking & Display
**Previous Epics:** EPIC-003 FCS Game Display, EPIC-006 Current Week Display
**Deployment Date:** 2025-10-23
**Version:** 3.0.0
**Risk Level:** 🟢 Low (No database migration required for EPIC-009)

---

## Quick Overview - EPIC-009

This deployment adds prediction accuracy tracking and display to the ranking system. Users can now see how well the system predicts game outcomes.

**What's changing (EPIC-009):**
- Backend API (3 new endpoints for prediction accuracy)
- Frontend (prediction accuracy displays on rankings and team pages)
- **NO DATABASE MIGRATION REQUIRED** (predictions table already exists)
- **NO DATA RE-IMPORT REQUIRED**

**Estimated deployment time:** 5-10 minutes (code deploy only)

---

## Previous Deployments

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
