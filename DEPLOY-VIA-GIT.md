# Deploy Updates via Git

✅ Changes have been committed and pushed to GitHub
📦 Repository: https://github.com/bdaileySNHU/cfb-rankings.git

## What Was Committed:

1. **`update_games.py`** - Smart game data update script
2. **`frontend/js/api.js`** - CORS fix for production (auto-detect API URL)
3. **Documentation** - Complete deployment and update guides

---

## Step-by-Step: Deploy to Production

### Step 1: SSH into Your Server

```bash
ssh your-username@cfb.bdailey.com
```

### Step 2: Navigate to App Directory

```bash
cd /var/www/cfb-rankings
```

### Step 3: Pull Latest Changes from Git

```bash
# Stash any local changes (if needed)
sudo git stash

# Pull latest from main branch
sudo git pull origin main

# You should see:
#   update_games.py
#   frontend/js/api.js
#   docs/UPDATE-GAME-DATA.md
#   docs/EPIC-001-PRODUCTION-DEPLOYMENT.md
#   docs/PRODUCTION-TROUBLESHOOTING.md
#   (and more documentation files)
```

**Expected output:**
```
remote: Enumerating objects: 15, done.
remote: Counting objects: 100% (15/15), done.
remote: Compressing objects: 100% (10/10), done.
remote: Total 13 (delta 2), reused 13 (delta 2), pack-reused 0
Unpacking objects: 100% (13/13), done.
From https://github.com/bdaileySNHU/cfb-rankings
   ec92677..087fdbf  main       -> origin/main
Updating ec92677..087fdbf
Fast-forward
 docs/EPIC-001-COMPLETION-SUMMARY.md        | 429 +++++++++++++++++++++++++++++
 docs/EPIC-001-PRODUCTION-DEPLOYMENT.md     | 588 +++++++++++++++++++++++++++++++++++++
 docs/PRODUCTION-TROUBLESHOOTING.md         | 612 ++++++++++++++++++++++++++++++++++++++
 docs/UPDATE-GAME-DATA.md                   | 481 ++++++++++++++++++++++++++++++
 update_games.py                            | 184 ++++++++++++
 11 files changed, 4531 insertions(+)
```

### Step 4: Fix File Permissions

```bash
# Ensure web server can read files
sudo chown -R www-data:www-data /var/www/cfb-rankings

# Make update script executable
sudo chmod +x update_games.py
```

### Step 5: Update Game Data (Week 6 → Current Week)

```bash
# Activate Python virtual environment
source venv/bin/activate

# Run the update script (auto-detects you're on Week 6 and fetches new weeks)
python3 update_games.py

# The script will:
#   ✓ Check current week (Week 6)
#   ✓ Fetch completed games from Weeks 7-10
#   ✓ Import new games
#   ✓ Recalculate rankings
#   ✓ Show updated Top 25

# Deactivate virtual environment
deactivate
```

### Step 6: Restart Backend Service

```bash
# Restart to ensure fresh data is loaded
sudo systemctl restart cfb-rankings

# Verify it's running
sudo systemctl status cfb-rankings
```

### Step 7: Verify Deployment

```bash
# Check database was updated
sqlite3 cfb_rankings.db "SELECT MAX(week) as current_week FROM games WHERE season = 2025;"

# Should show current week (e.g., 10 instead of 6)

# Test API endpoint
curl http://localhost:8000/api/rankings | python3 -m json.tool | head -30
```

### Step 8: Test in Browser

1. Visit: **https://cfb.bdailey.com**
2. **Hard refresh**: Press `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
3. **Check Rankings tab**: Should show current week data
4. **Check Console (F12)**: No CORS errors (api.js fix)
5. **Check Games tab**: Should display all games including recent weeks

---

## Complete Command Sequence (Copy & Paste)

```bash
# SSH into server
ssh your-username@cfb.bdailey.com

# Navigate and pull changes
cd /var/www/cfb-rankings
sudo git pull origin main
sudo chown -R www-data:www-data .
sudo chmod +x update_games.py

# Update game data
source venv/bin/activate
python3 update_games.py
deactivate

# Restart backend
sudo systemctl restart cfb-rankings

# Verify
sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season = 2025;"
curl http://localhost:8000/api/rankings | head -20

# Exit
exit
```

Then test in browser: **https://cfb.bdailey.com**

---

## Troubleshooting

### Issue: "Permission denied" when pulling

**Fix:**
```bash
# Give yourself ownership temporarily
sudo chown -R your-username:your-username /var/www/cfb-rankings
git pull origin main

# Give it back to web server
sudo chown -R www-data:www-data /var/www/cfb-rankings
```

### Issue: "No API key found" when running update_games.py

**Fix:**
```bash
# Check .env file exists
ls -la /var/www/cfb-rankings/.env

# If missing, create it
sudo nano /var/www/cfb-rankings/.env

# Add this line (with your actual key):
CFBD_API_KEY=your_actual_api_key_here

# Save and exit (Ctrl+X, Y, Enter)
```

### Issue: CORS errors still appear in browser

**Fix:**
```bash
# Clear browser cache with hard refresh
# Chrome/Firefox: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

# Or try incognito/private browsing mode
```

### Issue: Rankings don't update after running script

**Fix:**
```bash
# Restart backend service
sudo systemctl restart cfb-rankings

# Wait 5 seconds then refresh browser
```

---

## What Changed in This Deployment

### 1. API URL Fix (`frontend/js/api.js`)
**Before:**
```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

**After:**
```javascript
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'  // Local development
  : '/api';  // Production (uses same domain via Nginx proxy)
```

**Impact:** Fixes CORS errors on production site

### 2. New Update Script (`update_games.py`)
- Safe incremental updates (doesn't reset database)
- Auto-detects current week
- Imports only new completed games
- Recalculates rankings automatically

**Impact:** Can now update game data weekly without resetting everything

### 3. Comprehensive Documentation
- `docs/UPDATE-GAME-DATA.md` - How to update weekly
- `docs/EPIC-001-PRODUCTION-DEPLOYMENT.md` - Frontend deployment guide
- `docs/PRODUCTION-TROUBLESHOOTING.md` - Common issues and fixes

---

## Post-Deployment Checklist

After running all commands above:

- [ ] Git pull completed successfully
- [ ] update_games.py ran without errors
- [ ] Database shows current week (not Week 6)
- [ ] Backend service is running (`systemctl status cfb-rankings`)
- [ ] Website loads at https://cfb.bdailey.com
- [ ] No CORS errors in browser console (F12)
- [ ] Rankings show current week data
- [ ] Games tab displays recent games
- [ ] Team pages show updated schedules

---

## Future Updates

From now on, to update your game data weekly:

```bash
ssh your-username@cfb.bdailey.com
cd /var/www/cfb-rankings
source venv/bin/activate
python3 update_games.py
deactivate
sudo systemctl restart cfb-rankings
```

**That's it!** 🎉

---

## Questions?

- **Full update guide**: `docs/UPDATE-GAME-DATA.md`
- **Troubleshooting**: `docs/PRODUCTION-TROUBLESHOOTING.md`
- **EPIC-001 deployment**: `docs/EPIC-001-PRODUCTION-DEPLOYMENT.md`

**GitHub Repo**: https://github.com/bdaileySNHU/cfb-rankings
**Latest Commit**: `087fdbf` - "feat: Add game data update script and production deployment docs"
