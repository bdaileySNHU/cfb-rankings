# EPIC-004 Deployment Guide

This guide walks you through deploying all EPIC-004 changes (API Usage Tracking, Automated Weekly Updates, and Manual Update Triggers) to your production VPS.

## Overview of Changes

### New Features
1. **API Usage Tracking** - Monitors CFBD API calls against monthly limit
2. **Automated Weekly Updates** - Sunday evening updates during football season
3. **Manual Update Trigger** - API endpoint to trigger updates on-demand
4. **Usage Dashboard** - Comprehensive usage statistics and projections
5. **Configuration Management** - Update system settings via API

### Files Changed
- `models.py` - Added APIUsage and UpdateTask models
- `schemas.py` - Added admin endpoint schemas
- `cfbd_client.py` - Added API usage tracking decorator
- `main.py` - Added 6 new admin endpoints
- `.env.example` - Added CFBD_MONTHLY_LIMIT
- `README.md` - Updated documentation
- `DEPLOYMENT.md` - Updated deployment instructions

### New Files
- `scripts/weekly_update.py` - Weekly update script with pre-flight checks
- `deploy/cfb-weekly-update.service` - Systemd service for updates
- `deploy/cfb-weekly-update.timer` - Systemd timer for scheduling
- `tests/test_admin_endpoints.py` - Admin endpoint tests
- `tests/test_weekly_update.py` - Weekly update tests
- Documentation files in `docs/`

---

## Deployment Steps

### Step 1: Commit and Push Changes to Git

**On your local machine:**

```bash
cd "/Users/bryandailey/Stat-urday Synthesis"

# Add all changes
git add .

# Create commit
git commit -m "$(cat <<'EOF'
Add EPIC-004: Automated Updates and API Usage Tracking

Features:
- API usage tracking with monthly limits and warnings
- Automated weekly updates every Sunday at 8 PM ET
- Manual update trigger via admin API
- Usage dashboard with projections
- System configuration management
- Pre-flight checks for all updates

New endpoints:
- POST /api/admin/trigger-update
- GET /api/admin/update-status/{task_id}
- GET /api/admin/usage-dashboard
- GET /api/admin/api-usage
- GET /api/admin/config
- PUT /api/admin/config

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Push to remote
git push origin main
```

---

### Step 2: SSH into Your VPS

```bash
ssh user@your-vps-ip
# Replace 'user' with your actual VPS username
# Replace 'your-vps-ip' with your VPS IP address or domain
```

---

### Step 3: Pull Latest Changes

```bash
cd /var/www/cfb-rankings

# Pull latest code
sudo git pull origin main
```

**Expected output:**
```
Updating abc1234..def5678
Fast-forward
 models.py                              |  35 +++++
 schemas.py                             | 102 +++++++++++++
 cfbd_client.py                         |  98 +++++++++++-
 main.py                                | 400 +++++++++++++++++++++++++++++++++++++++++
 scripts/weekly_update.py               | 271 +++++++++++++++++++++++++++
 deploy/cfb-weekly-update.service       |  24 +++
 deploy/cfb-weekly-update.timer         |  15 ++
 ...
```

---

### Step 4: Update Environment Variables

```bash
# Edit .env file
sudo nano /var/www/cfb-rankings/.env
```

**Add this line if not present:**
```bash
CFBD_MONTHLY_LIMIT=1000
```

Your `.env` should look like:
```bash
CFBD_API_KEY=your_actual_api_key_here
DATABASE_URL=sqlite:///./cfb_rankings.db
CFBD_MONTHLY_LIMIT=1000
```

**Save and exit:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

### Step 5: Activate Virtual Environment and Install Dependencies

```bash
cd /var/www/cfb-rankings

# Activate virtual environment
source venv/bin/activate

# Install any new dependencies (if requirements.txt changed)
pip install -r requirements.txt
```

---

### Step 6: Update Database Schema

The new features require new database tables (`api_usage` and `update_tasks`).

```bash
# Still in virtual environment
cd /var/www/cfb-rankings

# Create a Python script to update the database
python3 << 'PYEOF'
from database import engine, Base
from models import APIUsage, UpdateTask

# Create new tables
print("Creating new database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database updated successfully!")
print("  - api_usage table created")
print("  - update_tasks table created")
PYEOF
```

**Expected output:**
```
Creating new database tables...
✓ Database updated successfully!
  - api_usage table created
  - update_tasks table created
```

---

### Step 7: Set Correct Permissions

```bash
# Ensure www-data user owns everything
sudo chown -R www-data:www-data /var/www/cfb-rankings

# Ensure database is writable
sudo chmod 664 /var/www/cfb-rankings/cfb_rankings.db
```

---

### Step 8: Restart the Application Service

```bash
# Restart the FastAPI application
sudo systemctl restart cfb-rankings

# Check status
sudo systemctl status cfb-rankings
```

**Expected output:**
```
● cfb-rankings.service - CFB Rankings API
   Loaded: loaded (/etc/systemd/system/cfb-rankings.service; enabled)
   Active: active (running) since ...
```

**If you see errors:**
```bash
# View detailed logs
sudo journalctl -u cfb-rankings -n 50 --no-pager
```

---

### Step 9: Verify API is Running

```bash
# Test health check
curl http://localhost:8000/

# Test new admin endpoints
curl http://localhost:8000/api/admin/api-usage
curl http://localhost:8000/api/admin/config
```

**Expected responses:**
- Health check: `{"status":"ok"}`
- API usage: JSON with usage statistics
- Config: JSON with system configuration

---

### Step 10: Install Automated Weekly Update Timer

```bash
cd /var/www/cfb-rankings

# Create log directory
sudo mkdir -p /var/log/cfb-rankings
sudo chown www-data:www-data /var/log/cfb-rankings

# Copy systemd units to system directory
sudo cp deploy/cfb-weekly-update.timer /etc/systemd/system/
sudo cp deploy/cfb-weekly-update.service /etc/systemd/system/

# Reload systemd to recognize new units
sudo systemctl daemon-reload

# Enable the timer (starts on boot)
sudo systemctl enable cfb-weekly-update.timer

# Start the timer
sudo systemctl start cfb-weekly-update.timer

# Verify timer is active
sudo systemctl status cfb-weekly-update.timer
```

**Expected output:**
```
● cfb-weekly-update.timer - CFB Rankings Weekly Update Timer
   Loaded: loaded (/etc/systemd/system/cfb-weekly-update.timer; enabled)
   Active: active (waiting) since ...
  Trigger: Mon 2025-10-20 00:00:00 UTC; 4h 15min left
```

**View next scheduled run:**
```bash
systemctl list-timers cfb-weekly-update.timer
```

---

### Step 11: Test Manual Update Trigger

```bash
# Test the manual update trigger endpoint
curl -X POST http://localhost:8000/api/admin/trigger-update
```

**Expected response (success):**
```json
{
  "status": "started",
  "message": "Update started successfully",
  "task_id": "update-20251019-123456",
  "started_at": "2025-10-19T12:34:56.789012"
}
```

**OR (if off-season - expected February-July):**
```json
{
  "detail": "Cannot update during off-season (Feb-July)"
}
```

**Check the task status:**
```bash
# Replace task_id with the one from the response above
curl http://localhost:8000/api/admin/update-status/update-20251019-123456
```

---

### Step 12: Test Weekly Update Script Manually

```bash
cd /var/www/cfb-rankings
source venv/bin/activate

# Run the weekly update script directly
python3 scripts/weekly_update.py
```

**Expected output (in-season):**
```
2025-10-19 12:35:00 - INFO - Starting weekly update check
2025-10-19 12:35:00 - INFO - ✓ Active season check passed
2025-10-19 12:35:01 - INFO - ✓ Current week: 8
2025-10-19 12:35:01 - INFO - ✓ API usage: 24.5% (245/1000 calls)
2025-10-19 12:35:01 - INFO - All pre-flight checks passed - starting import
2025-10-19 12:35:01 - INFO - Running: python3 import_real_data.py
...
```

**Expected output (off-season):**
```
2025-05-15 12:35:00 - INFO - Starting weekly update check
2025-05-15 12:35:00 - INFO - Off-season detected - skipping update
```

---

### Step 13: Verify All Components

**Check application service:**
```bash
sudo systemctl status cfb-rankings
```

**Check weekly update timer:**
```bash
sudo systemctl status cfb-weekly-update.timer
```

**View application logs:**
```bash
sudo journalctl -u cfb-rankings -f
# Press Ctrl+C to exit
```

**View weekly update logs:**
```bash
sudo tail -f /var/log/cfb-rankings/weekly-update.log
# Press Ctrl+C to exit
```

**Test all new endpoints:**
```bash
# API Usage
curl http://localhost:8000/api/admin/api-usage

# Usage Dashboard
curl http://localhost:8000/api/admin/usage-dashboard

# System Config
curl http://localhost:8000/api/admin/config

# Trigger Update
curl -X POST http://localhost:8000/api/admin/trigger-update

# Check interactive docs
curl http://localhost:8000/docs
```

---

### Step 14: Test from Browser (if accessible)

If your VPS has a public domain (e.g., `https://cfb.yourdomain.com`):

1. **Visit API docs:** `https://cfb.yourdomain.com/docs`
2. **Find Admin section** in the docs
3. **Test endpoints:**
   - Click on `GET /api/admin/api-usage`
   - Click "Try it out"
   - Click "Execute"
   - Verify you get usage statistics

4. **Test manual trigger:**
   - Find `POST /api/admin/trigger-update`
   - Click "Try it out"
   - Click "Execute"
   - Copy the `task_id` from response
   - Use `GET /api/admin/update-status/{task_id}` to check status

---

## Verification Checklist

After deployment, verify:

- ✅ Application service is running: `systemctl status cfb-rankings`
- ✅ Weekly update timer is active: `systemctl status cfb-weekly-update.timer`
- ✅ Database has new tables: `api_usage` and `update_tasks`
- ✅ Environment variable `CFBD_MONTHLY_LIMIT` is set
- ✅ `/api/admin/api-usage` endpoint returns usage data
- ✅ `/api/admin/config` endpoint returns configuration
- ✅ `/api/admin/trigger-update` endpoint works (or correctly rejects if off-season)
- ✅ `/api/admin/usage-dashboard` endpoint returns dashboard data
- ✅ Logs are being written to `/var/log/cfb-rankings/`
- ✅ API docs accessible at `https://your-domain.com/docs`

---

## Monitoring After Deployment

### Watch Real-Time Logs

```bash
# Application logs
sudo journalctl -u cfb-rankings -f

# Weekly update logs
sudo tail -f /var/log/cfb-rankings/weekly-update.log

# Nginx access logs
sudo tail -f /var/log/nginx/cfb-rankings-access.log
```

### Check API Usage

```bash
# Current month usage
curl http://localhost:8000/api/admin/api-usage | jq

# Usage dashboard with projections
curl http://localhost:8000/api/admin/usage-dashboard | jq
```

### Monitor System Resources

```bash
# CPU and memory usage
htop

# Disk usage
df -h /var/www/cfb-rankings

# Database size
ls -lh /var/www/cfb-rankings/cfb_rankings.db
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u cfb-rankings -n 100 --no-pager

# Check if port 8000 is in use
sudo lsof -i :8000

# Restart service
sudo systemctl restart cfb-rankings
```

### Database Permission Errors

```bash
# Fix ownership
sudo chown www-data:www-data /var/www/cfb-rankings/cfb_rankings.db

# Fix permissions
sudo chmod 664 /var/www/cfb-rankings/cfb_rankings.db
```

### Timer Not Running

```bash
# Check timer status
sudo systemctl status cfb-weekly-update.timer

# Reload systemd
sudo systemctl daemon-reload

# Restart timer
sudo systemctl restart cfb-weekly-update.timer

# View logs
sudo journalctl -u cfb-weekly-update.timer -n 50
```

### Manual Update Fails

```bash
# Check if off-season (February - July)
date

# Check API usage
curl http://localhost:8000/api/admin/api-usage | jq '.percentage_used'

# Check logs
sudo journalctl -u cfb-rankings -n 50 --no-pager

# Run weekly_update.py manually for debugging
cd /var/www/cfb-rankings
source venv/bin/activate
python3 scripts/weekly_update.py
```

### Import Errors

```bash
# Check if API key is set
grep CFBD_API_KEY /var/www/cfb-rankings/.env

# Test API connection
cd /var/www/cfb-rankings
source venv/bin/activate
python3 -c "from cfbd_client import CFBDClient; c = CFBDClient(); print(c.get_current_season())"
```

---

## Rolling Back (If Needed)

If something goes wrong and you need to rollback:

```bash
# Stop services
sudo systemctl stop cfb-rankings
sudo systemctl stop cfb-weekly-update.timer

# Restore previous version
cd /var/www/cfb-rankings
sudo git log --oneline  # Find previous commit hash
sudo git reset --hard <previous-commit-hash>

# Restart application
sudo systemctl start cfb-rankings

# Remove timer if desired
sudo systemctl disable cfb-weekly-update.timer
```

---

## Next Steps After Deployment

1. **Monitor for a week** - Watch logs and verify updates run correctly
2. **Check API usage** - Ensure tracking is working properly
3. **Test manual updates** - Trigger a few manual updates to verify functionality
4. **Set up alerts** - Consider email notifications for high API usage
5. **Backup database** - Schedule regular backups of `cfb_rankings.db`

---

## Support Commands Reference

```bash
# Service management
sudo systemctl status cfb-rankings
sudo systemctl restart cfb-rankings
sudo systemctl stop cfb-rankings
sudo systemctl start cfb-rankings

# Timer management
sudo systemctl status cfb-weekly-update.timer
sudo systemctl enable cfb-weekly-update.timer
sudo systemctl disable cfb-weekly-update.timer

# Logs
sudo journalctl -u cfb-rankings -f
sudo journalctl -u cfb-weekly-update -f
sudo tail -f /var/log/cfb-rankings/weekly-update.log

# API testing
curl http://localhost:8000/api/admin/api-usage
curl http://localhost:8000/api/admin/usage-dashboard
curl http://localhost:8000/api/admin/config
curl -X POST http://localhost:8000/api/admin/trigger-update

# Database
sqlite3 /var/www/cfb-rankings/cfb_rankings.db "SELECT * FROM api_usage LIMIT 10;"
sqlite3 /var/www/cfb-rankings/cfb_rankings.db "SELECT * FROM update_tasks;"
```

---

## Success Criteria

Your deployment is successful when:

✅ Application starts without errors
✅ All admin endpoints return valid responses
✅ Weekly update timer shows next scheduled run
✅ Database contains `api_usage` and `update_tasks` tables
✅ API usage tracking is recording calls
✅ Manual update trigger works (or correctly rejects if off-season)
✅ Logs are being written correctly
✅ API documentation shows new admin endpoints

---

**Deployment completed!** 🚀

Your College Football Rankings system now has:
- Automatic weekly updates every Sunday at 8 PM ET
- Real-time API usage monitoring
- Manual update triggers for flexibility
- Comprehensive usage dashboards
- Configurable monthly limits

Questions or issues? Check the troubleshooting section above or review logs.
