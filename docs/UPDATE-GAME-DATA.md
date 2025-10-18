# How to Update Game Data

Your website is currently showing **Week 6** data. This guide shows you how to update it to the latest week.

---

## Quick Update (Production Server)

### Step 1: SSH into Server

```bash
ssh your-username@cfb.bdailey.com
```

### Step 2: Navigate to App Directory

```bash
cd /var/www/cfb-rankings
```

### Step 3: Activate Virtual Environment

```bash
source venv/bin/activate
```

### Step 4: Run Update Script

```bash
# This will automatically detect where you left off and import new games
python3 update_games.py

# Or specify a week range:
# python3 update_games.py --start-week 7 --end-week 10
```

The script will:
- ✅ Check what week you're currently on (Week 6)
- ✅ Fetch new completed games from CollegeFootballData.com API
- ✅ Add new games to database
- ✅ Recalculate rankings
- ✅ Update the current week

### Step 5: Verify Update

```bash
# Check the database was updated
sqlite3 cfb_rankings.db "SELECT season, MAX(week) as latest_week FROM games GROUP BY season;"

# Should show: 2025|10 (or whatever the current week is)

# Exit virtual environment
deactivate
```

### Step 6: Restart Backend (Optional)

If the API needs refreshing:

```bash
sudo systemctl restart cfb-rankings
```

### Step 7: Test in Browser

Visit: https://cfb.bdailey.com

The rankings should now show updated data!

---

## What the Update Script Does

**`update_games.py`** is different from `import_real_data.py`:

| Feature | import_real_data.py | update_games.py |
|---------|-------------------|----------------|
| **Purpose** | Initial setup | Weekly updates |
| **Database** | **RESETS** everything | **Preserves** existing data |
| **Use case** | First-time import | Regular updates |
| **Risk** | ⚠️ Deletes all data | ✅ Safe, additive only |

**Always use `update_games.py` for weekly updates!**

---

## Testing Locally First

Before updating production, test locally:

```bash
# On your local machine
cd "/Users/bryandailey/Stat-urday Synthesis"

# Ensure you have API key
export CFBD_API_KEY='your-api-key-here'

# Run update script
python3 update_games.py

# Check what week you now have
sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season = 2025;"
```

If it works locally, proceed with production update.

---

## Automated Weekly Updates

To automatically update every week, set up a cron job:

### Step 1: Create Update Script

On your production server:

```bash
# Create script directory
sudo mkdir -p /var/www/cfb-rankings/scripts

# Create update script
sudo nano /var/www/cfb-rankings/scripts/weekly-update.sh
```

**Paste this:**

```bash
#!/bin/bash
# Weekly Game Data Update Script

# Set paths
APP_DIR="/var/www/cfb-rankings"
VENV_DIR="$APP_DIR/venv"
LOG_FILE="/var/log/cfb-rankings/weekly-update.log"

# Create log directory if needed
sudo mkdir -p /var/log/cfb-rankings

# Log with timestamp
echo "========================================" >> "$LOG_FILE"
echo "Weekly Update: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Navigate to app directory
cd "$APP_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run update script
python3 update_games.py >> "$LOG_FILE" 2>&1

# Deactivate virtual environment
deactivate

# Restart backend to refresh cache (optional)
sudo systemctl restart cfb-rankings >> "$LOG_FILE" 2>&1

echo "Update completed: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

Save and exit (Ctrl+X, Y, Enter)

### Step 2: Make Script Executable

```bash
sudo chmod +x /var/www/cfb-rankings/scripts/weekly-update.sh
```

### Step 3: Set Up Cron Job

```bash
# Edit crontab
sudo crontab -e

# Add this line to run every Monday at 2 AM:
0 2 * * 1 /var/www/cfb-rankings/scripts/weekly-update.sh

# Or run every day at 2 AM (checks for new games daily):
0 2 * * * /var/www/cfb-rankings/scripts/weekly-update.sh
```

### Step 4: Verify Cron Job

```bash
# List cron jobs
sudo crontab -l

# Check logs after first run
sudo tail -50 /var/log/cfb-rankings/weekly-update.log
```

---

## Manual Update from Scratch (Nuclear Option)

⚠️ **Only use this if you need to completely reset your database**

### On Production Server:

```bash
cd /var/www/cfb-rankings
source venv/bin/activate

# Set your API key
export CFBD_API_KEY='your-api-key-here'

# Run full import (THIS DELETES ALL DATA!)
python3 import_real_data.py

# When prompted, type: yes

# When asked for max week, enter current week (e.g., 10)

deactivate
sudo systemctl restart cfb-rankings
```

---

## How to Check Current Week

### Option 1: Query Database

```bash
# SSH into server
ssh your-username@cfb.bdailey.com

cd /var/www/cfb-rankings

# Check season info
sqlite3 cfb_rankings.db "SELECT year, current_week FROM seasons WHERE is_active = 1;"

# Check latest game week
sqlite3 cfb_rankings.db "SELECT MAX(week) as latest_week FROM games WHERE season = 2025;"
```

### Option 2: Check API

```bash
# From any machine
curl https://cfb.bdailey.com/api/stats | python3 -m json.tool
```

Look for the `current_week` field.

---

## Troubleshooting

### Issue 1: "No API key found"

**Fix:**
```bash
# Edit .env file on server
sudo nano /var/www/cfb-rankings/.env

# Add this line (with your actual key):
CFBD_API_KEY=your_actual_api_key_here

# Save and exit
```

### Issue 2: "Season 2025 not found in database"

**Fix:**
```bash
# You need to run initial import first
cd /var/www/cfb-rankings
source venv/bin/activate
python3 import_real_data.py
```

### Issue 3: Update script runs but rankings don't change

**Fix:**
```bash
# Restart the backend service
sudo systemctl restart cfb-rankings

# Clear browser cache
# Visit site and press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

### Issue 4: "Permission denied" on database

**Fix:**
```bash
# Fix database permissions
cd /var/www/cfb-rankings
sudo chown www-data:www-data cfb_rankings.db
sudo chmod 664 cfb_rankings.db
```

---

## Update Script Command Reference

```bash
# Auto-detect and update to latest
python3 update_games.py

# Update specific week range
python3 update_games.py --start-week 7 --end-week 10

# Update specific year
python3 update_games.py --year 2024

# Update just one week
python3 update_games.py --start-week 10 --end-week 10

# Show help
python3 update_games.py --help
```

---

## Step-by-Step: Update Production to Current Week

### Complete Workflow:

```bash
# 1. SSH into server
ssh your-username@cfb.bdailey.com

# 2. Navigate to app
cd /var/www/cfb-rankings

# 3. Check current status
sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season = 2025;"
# Output: 6 (you're on week 6)

# 4. Activate virtual environment
source venv/bin/activate

# 5. Run update (auto-detects and fetches weeks 7-10)
python3 update_games.py

# 6. Verify update
sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season = 2025;"
# Output: 10 (or current week)

# 7. Exit virtual environment
deactivate

# 8. Restart backend
sudo systemctl restart cfb-rankings

# 9. Exit SSH
exit

# 10. Test in browser
# Visit: https://cfb.bdailey.com
# Rankings should show current week data!
```

---

## Backup Before Major Updates

Always backup before updating:

```bash
# Create backup
cd /var/www/cfb-rankings
cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d_%H%M%S).db

# Verify backup
ls -lh cfb_rankings_backup*.db
```

If something goes wrong:

```bash
# Restore from backup
cp cfb_rankings_backup_YYYYMMDD_HHMMSS.db cfb_rankings.db
sudo systemctl restart cfb-rankings
```

---

## When to Update

**Update weekly after these events:**

- ✅ Saturday games complete (Sunday morning)
- ✅ Monday Night games complete (Tuesday morning)
- ✅ Midweek games complete (next day)

**Best time to update:** Sunday mornings or Monday mornings after all weekend games are complete.

---

## Summary

**For Weekly Updates:**
1. SSH into server
2. `cd /var/www/cfb-rankings`
3. `source venv/bin/activate`
4. `python3 update_games.py`
5. `deactivate`
6. `sudo systemctl restart cfb-rankings`

**That's it!** Your site will show the latest data.

---

**Questions?** Check the troubleshooting section or review logs:
- Application logs: `sudo journalctl -u cfb-rankings -f`
- Update logs (if using cron): `sudo tail -f /var/log/cfb-rankings/weekly-update.log`
