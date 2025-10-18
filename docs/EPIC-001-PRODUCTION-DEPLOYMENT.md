# EPIC-001 Production Deployment Guide

**Epic:** Game Schedule Display Feature
**Deployment Date:** TBD
**Version:** 1.0.0
**Risk Level:** 🟢 Low (Frontend-only changes)

---

## Quick Overview

This deployment adds game schedule display functionality to your production College Football Rankings website. The changes are **frontend-only** (no backend/database changes required), making this a **zero-downtime, low-risk deployment**.

**What's changing:**
- 3 frontend files (games.html, team.js, style.css)
- No API changes
- No database migrations
- No server restarts needed

**Estimated deployment time:** 10-15 minutes

---

## Pre-Deployment Checklist

Before starting, verify you have:

- [ ] SSH access to your production VPS
- [ ] Production server URL (e.g., `https://cfb.yourdomain.com`)
- [ ] Git repository set up (if using git deployment method)
- [ ] Backup plan ready (see Step 1)
- [ ] 10-15 minutes of focused time

---

## Deployment Methods

Choose **ONE** of the following deployment methods:

### Method A: Git-Based Deployment (Recommended) ⭐
**Best for:** Teams using version control, easy rollback
**Time:** 5-10 minutes

### Method B: Direct SCP File Transfer
**Best for:** Quick one-time deployments, no git setup
**Time:** 10-15 minutes

### Method C: Manual Copy-Paste via SSH
**Best for:** Emergency fixes, minimal files
**Time:** 15-20 minutes

---

## 🚀 Method A: Git-Based Deployment (Recommended)

### Step 1: Commit and Push Changes (Local Machine)

```bash
# Navigate to your project directory
cd "/Users/bryandailey/Stat-urday Synthesis"

# Verify the modified files
git status

# You should see:
#   modified:   frontend/games.html
#   modified:   frontend/js/team.js
#   modified:   frontend/css/style.css

# Review the changes one more time
git diff frontend/games.html
git diff frontend/js/team.js
git diff frontend/css/style.css

# Stage the files
git add frontend/games.html frontend/js/team.js frontend/css/style.css

# Create commit with descriptive message
git commit -m "feat: Add game schedule display (EPIC-001)

- Enhanced games page to show completed and scheduled games
- Updated team detail page with full season schedules
- Added visual distinction for future games with CSS styling
- Fixed hardcoded season year (2024 → 2025)
- Added defensive null checks for game scores
- Mobile-responsive design improvements

All 236 tests passing. Zero backend changes.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote repository
git push origin main
```

**✅ Checkpoint:** Verify your changes are visible on GitHub/GitLab/Bitbucket

### Step 2: SSH into Production Server

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Example:
# ssh bryan@123.45.67.89
# or
# ssh bryan@cfb.yourdomain.com
```

### Step 3: Create Backup

```bash
# Navigate to application directory
cd /var/www/cfb-rankings

# Create backup directory with timestamp
BACKUP_DIR="backups/epic001_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup the 3 files we're changing
cp frontend/games.html "$BACKUP_DIR/"
cp frontend/js/team.js "$BACKUP_DIR/"
cp frontend/css/style.css "$BACKUP_DIR/"

# Verify backup was created
ls -lh "$BACKUP_DIR"

# Save backup path for potential rollback
echo "Backup location: /var/www/cfb-rankings/$BACKUP_DIR"
```

**✅ Checkpoint:** You should see 3 files in the backup directory

### Step 4: Pull Latest Changes

```bash
# Still in /var/www/cfb-rankings

# Stash any local changes (if any)
sudo git stash

# Pull latest changes from repository
sudo git pull origin main

# Verify the files were updated
git log -1 --stat

# You should see:
#   frontend/games.html
#   frontend/js/team.js
#   frontend/css/style.css
```

**✅ Checkpoint:** Verify commit message shows "EPIC-001"

### Step 5: Fix Permissions (if needed)

```bash
# Ensure Nginx can read the files
sudo chown -R www-data:www-data /var/www/cfb-rankings/frontend

# Verify permissions
ls -la frontend/games.html
ls -la frontend/js/team.js
ls -la frontend/css/style.css
```

### Step 6: Clear Browser Cache (Optional but Recommended)

Since we're updating JavaScript and CSS, browsers may cache old versions:

```bash
# Option 1: Force reload in browser
# Open https://cfb.yourdomain.com
# Press: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)

# Option 2: Configure Nginx cache headers (one-time setup)
# Edit Nginx config to add cache-busting headers
sudo nano /etc/nginx/sites-available/cfb-rankings

# Add inside the location block for frontend files:
# location ~* \.(js|css)$ {
#     expires 1h;
#     add_header Cache-Control "public, must-revalidate, proxy-revalidate";
# }

# Then reload Nginx:
# sudo systemctl reload nginx
```

### Step 7: Test in Production

**Manual Testing Checklist:**

1. **Test Games Page**
   ```
   ✅ Visit: https://cfb.yourdomain.com/games.html
   ✅ Verify: Games list displays (not empty)
   ✅ Verify: Week filter works
   ✅ Verify: No JavaScript errors in browser console (F12)
   ✅ Check: Completed games show scores
   ✅ Check: Future games (if any) show "TBD"
   ```

2. **Test Team Detail Page**
   ```
   ✅ Visit: https://cfb.yourdomain.com/team.html?id=3
   ✅ Verify: Schedule section displays games
   ✅ Verify: Opponent links are clickable
   ✅ Verify: W/L records display correctly
   ✅ Check: No JavaScript errors in console
   ```

3. **Test Mobile Responsiveness**
   ```
   ✅ Resize browser to mobile size (375px width)
   ✅ Verify: Tables remain readable
   ✅ Verify: No horizontal scrolling
   ✅ Verify: All links still clickable
   ```

4. **Cross-Browser Testing** (if possible)
   ```
   ✅ Test in Chrome/Brave
   ✅ Test in Firefox
   ✅ Test in Safari
   ```

### Step 8: Monitor Logs (Optional)

```bash
# Check Nginx access logs for errors
sudo tail -f /var/log/nginx/cfb-rankings-access.log

# Check for any 404s or 500s
sudo tail -f /var/log/nginx/cfb-rankings-error.log

# Press Ctrl+C to stop tailing logs
```

### Step 9: Deployment Complete! 🎉

If all tests pass, you're done! The deployment was successful.

**Document your deployment:**
```bash
# Create deployment log
echo "EPIC-001 deployed successfully on $(date)" | sudo tee -a /var/www/cfb-rankings/deployment-log.txt
```

---

## 🚀 Method B: Direct SCP File Transfer

### Step 1: Create Backup on Production

```bash
# SSH into production server
ssh user@your-vps-ip

# Create backup
cd /var/www/cfb-rankings
BACKUP_DIR="backups/epic001_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp frontend/games.html "$BACKUP_DIR/"
cp frontend/js/team.js "$BACKUP_DIR/"
cp frontend/css/style.css "$BACKUP_DIR/"

# Exit SSH (stay connected in separate terminal)
```

### Step 2: Transfer Files from Local to Production

```bash
# Open a NEW terminal on your local machine
# DO NOT close the SSH session from Step 1

# Navigate to your project
cd "/Users/bryandailey/Stat-urday Synthesis"

# Transfer the 3 files
scp frontend/games.html user@your-vps-ip:/tmp/
scp frontend/js/team.js user@your-vps-ip:/tmp/
scp frontend/css/style.css user@your-vps-ip:/tmp/

# Example:
# scp frontend/games.html bryan@123.45.67.89:/tmp/
```

### Step 3: Move Files to Production Directory

```bash
# Go back to your SSH terminal (from Step 1)

# Move files from /tmp to production
sudo cp /tmp/games.html /var/www/cfb-rankings/frontend/
sudo cp /tmp/team.js /var/www/cfb-rankings/frontend/js/
sudo cp /tmp/style.css /var/www/cfb-rankings/frontend/css/

# Fix permissions
sudo chown www-data:www-data /var/www/cfb-rankings/frontend/games.html
sudo chown www-data:www-data /var/www/cfb-rankings/frontend/js/team.js
sudo chown www-data:www-data /var/www/cfb-rankings/frontend/css/style.css

# Clean up temp files
rm /tmp/games.html /tmp/team.js /tmp/style.css
```

### Step 4: Test in Production

Follow **Step 7** from Method A (Testing Checklist)

---

## 🚀 Method C: Manual Copy-Paste via SSH

**Only use this method if git and scp are not available.**

### Step 1: Backup on Production

```bash
ssh user@your-vps-ip
cd /var/www/cfb-rankings
BACKUP_DIR="backups/epic001_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp frontend/games.html "$BACKUP_DIR/"
cp frontend/js/team.js "$BACKUP_DIR/"
cp frontend/css/style.css "$BACKUP_DIR/"
```

### Step 2: Edit Each File Manually

```bash
# Still on production server

# Edit games.html
sudo nano frontend/games.html
# Copy contents from your local file and paste

# Edit team.js
sudo nano frontend/js/team.js
# Copy contents from your local file and paste

# Edit style.css
sudo nano frontend/css/style.css
# Copy contents from your local file and paste
```

**⚠️ Warning:** This method is error-prone. Double-check your changes!

### Step 3: Test in Production

Follow **Step 7** from Method A (Testing Checklist)

---

## Rollback Plan 🔄

If something goes wrong, you can quickly rollback:

### Rollback Steps

```bash
# SSH into production
ssh user@your-vps-ip

# Navigate to app directory
cd /var/www/cfb-rankings

# List your backups
ls -lh backups/

# You should see: epic001_YYYYMMDD_HHMMSS/

# Copy backup files back to production
BACKUP_DIR="backups/epic001_YYYYMMDD_HHMMSS"  # Replace with actual timestamp
sudo cp "$BACKUP_DIR/games.html" frontend/
sudo cp "$BACKUP_DIR/team.js" frontend/js/
sudo cp "$BACKUP_DIR/style.css" frontend/css/

# Fix permissions
sudo chown -R www-data:www-data frontend/

# Force browser cache clear
# Visit site and press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

**✅ Verify rollback:** Check that the site displays the old behavior

---

## Troubleshooting

### Problem: Games page shows "Loading games..." forever

**Cause:** JavaScript error or hardcoded season year
**Fix:**
```bash
# Check browser console for errors (F12)
# Common fix: Update season year if your data uses a different year

# On production server, check what season your database has
ssh user@your-vps-ip
cd /var/www/cfb-rankings
source venv/bin/activate
python3 -c "from database import SessionLocal; from models import Game; db = SessionLocal(); print('Seasons in DB:', {g.season for g in db.query(Game).all()})"

# If output shows "2024" but your frontend has "2025", update frontend
# Or vice versa - they must match!
```

### Problem: Team schedules show "No games scheduled yet"

**Same as above** - season year mismatch

### Problem: Browser shows old version of files

**Cause:** Browser cache
**Fix:**
```bash
# Hard refresh browser
# Mac: Cmd+Shift+R
# Windows/Linux: Ctrl+Shift+R

# Or open in incognito/private browsing mode
```

### Problem: 404 errors for JavaScript/CSS files

**Cause:** File permissions or paths
**Fix:**
```bash
# Check file existence
ls -lh /var/www/cfb-rankings/frontend/games.html
ls -lh /var/www/cfb-rankings/frontend/js/team.js
ls -lh /var/www/cfb-rankings/frontend/css/style.css

# Fix permissions if needed
sudo chown -R www-data:www-data /var/www/cfb-rankings/frontend
sudo chmod 644 /var/www/cfb-rankings/frontend/games.html
sudo chmod 644 /var/www/cfb-rankings/frontend/js/team.js
sudo chmod 644 /var/www/cfb-rankings/frontend/css/style.css
```

### Problem: JavaScript console shows "Cannot read property 'id' of undefined"

**Cause:** Defensive null checks not applied correctly
**Fix:**
```bash
# This means the deployment didn't complete successfully
# Rollback and re-deploy with correct files

# Or check that games.html and team.js contain the null checks:
# In games.html: if (!winner || !loser) return;
# In team.js: const isPlayed = game.is_played && game.score;
```

---

## Post-Deployment Checklist

After successful deployment:

- [ ] All manual tests passed
- [ ] No JavaScript errors in browser console
- [ ] Games page displays correctly
- [ ] Team detail page displays correctly
- [ ] Mobile view looks good
- [ ] Deployment logged in deployment-log.txt
- [ ] Team notified of successful deployment
- [ ] Documentation updated (if needed)

---

## Useful Commands Reference

```bash
# View production application logs
sudo journalctl -u cfb-rankings -f

# View Nginx access logs
sudo tail -f /var/log/nginx/cfb-rankings-access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/cfb-rankings-error.log

# Test Nginx configuration
sudo nginx -t

# Reload Nginx (if config changed)
sudo systemctl reload nginx

# Restart Nginx (if needed)
sudo systemctl restart nginx

# Check backend API status
sudo systemctl status cfb-rankings

# List all backups
ls -lh /var/www/cfb-rankings/backups/
```

---

## Files Modified in This Deployment

| File | Path | Lines Changed | Risk |
|------|------|---------------|------|
| games.html | `frontend/games.html` | ~47 lines | Low |
| team.js | `frontend/js/team.js` | ~72 lines | Low |
| style.css | `frontend/css/style.css` | ~25 lines | Low |

**Total:** 3 files, ~144 lines changed, 0 API changes, 0 database changes

---

## Expected Results After Deployment

### Games Page (games.html)
- Shows list of all season games
- Completed games display with scores and winner/loser format
- Future games (if any) show "vs" format with "TBD" placeholders
- Week filter works correctly
- No JavaScript errors

### Team Detail Page (team.html)
- Shows complete season schedule for selected team
- Past games show W/L with scores (green/red)
- Future games show "vs Opponent" in grayed-out text
- All opponent links work
- No JavaScript errors

### Visual Styling
- Scheduled games appear with 75% opacity
- Italic font style for future games
- Smooth hover transitions
- Mobile-responsive tables (< 768px)

---

## Support

**If you encounter issues:**

1. Check browser console for JavaScript errors (F12)
2. Review Nginx error logs: `sudo tail -f /var/log/nginx/cfb-rankings-error.log`
3. Verify file permissions: `ls -la /var/www/cfb-rankings/frontend/`
4. Check if season year matches database: See "Troubleshooting" section
5. Rollback using backup if needed (see "Rollback Plan")

**Reference Documentation:**
- Epic Summary: `/docs/EPIC-001-COMPLETION-SUMMARY.md`
- Story Details: `/docs/stories/story-*.md`
- Local Deployment: `/deploy-epic-001.sh`

---

## Deployment Approval

**Ready to deploy?**

Before running the deployment, confirm:

✅ All 236 tests passing locally
✅ Manual testing completed locally
✅ Backup plan understood
✅ Rollback procedure understood
✅ You have 10-15 minutes of focused time
✅ You have SSH access to production

**If all boxes checked, proceed with deployment! 🚀**

---

**Deployment Guide Version:** 1.0
**Created:** 2025-10-17
**Epic:** EPIC-001 - Game Schedule Display
**Risk Level:** 🟢 Low
**Estimated Time:** 10-15 minutes
**Zero Downtime:** ✅ Yes
**Rollback Available:** ✅ Yes
