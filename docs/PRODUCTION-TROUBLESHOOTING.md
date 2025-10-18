# Production Server Troubleshooting Guide

**Server:** cfb.bdailey.com
**Issue:** "Error loading rankings. Load failed"
**Date:** 2025-10-17

---

## Quick Diagnostic Commands

Run these commands in order to identify the issue:

### Step 1: Check if Backend API is Running

```bash
# SSH into your production server
ssh user@cfb.bdailey.com

# Check if the cfb-rankings service is running
sudo systemctl status cfb-rankings

# Expected output: "active (running)"
# If not running, see "Backend Not Running" section below
```

### Step 2: Check Backend Logs

```bash
# View recent application logs
sudo journalctl -u cfb-rankings -n 50 --no-pager

# Look for errors like:
# - "ModuleNotFoundError"
# - "Database locked"
# - "Permission denied"
# - "Address already in use"

# For live log monitoring:
sudo journalctl -u cfb-rankings -f
# Press Ctrl+C to stop
```

### Step 3: Test API Health Endpoint

```bash
# Test if the API is responding
curl http://localhost:8000/

# Expected response: {"message":"Hello from the CFB Rankings API!"}

# If this fails, the backend is not working properly
```

### Step 4: Test Rankings Endpoint Directly

```bash
# Test the rankings endpoint (what the frontend calls)
curl http://localhost:8000/api/rankings

# Expected: JSON array of team rankings

# If you get an error, note the error message
```

### Step 5: Check Database

```bash
# Navigate to app directory
cd /var/www/cfb-rankings

# Check if database file exists
ls -lh cfb_rankings.db

# Check database size (should be > 0 bytes)
du -h cfb_rankings.db

# Check database tables
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM teams;"
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games;"

# Expected: Non-zero counts
```

### Step 6: Check Nginx Configuration

```bash
# Test Nginx configuration
sudo nginx -t

# Expected: "syntax is ok" and "test is successful"

# View Nginx error log
sudo tail -50 /var/log/nginx/cfb-rankings-error.log

# Check for CORS errors or proxy issues
```

### Step 7: Check Frontend JavaScript Console

This you can do from your browser:

1. Open: https://cfb.bdailey.com
2. Press F12 (or Cmd+Option+I on Mac)
3. Click "Console" tab
4. Look for errors in red

Common errors:
- `Failed to fetch` → Backend not responding
- `CORS error` → Nginx/Backend CORS config issue
- `404 Not Found` → API endpoint path wrong
- `500 Internal Server Error` → Backend crashed

---

## Common Issues and Fixes

### Issue 1: Backend Service Not Running

**Symptoms:**
- `systemctl status cfb-rankings` shows "inactive (dead)"
- API curl commands fail

**Fix:**
```bash
# Start the service
sudo systemctl start cfb-rankings

# Check status
sudo systemctl status cfb-rankings

# If it fails to start, check logs:
sudo journalctl -u cfb-rankings -n 50

# Enable auto-start on boot
sudo systemctl enable cfb-rankings
```

### Issue 2: Database Doesn't Exist or Empty

**Symptoms:**
- `ls cfb_rankings.db` shows "No such file or directory"
- Database exists but queries return 0 rows

**Fix:**
```bash
cd /var/www/cfb-rankings

# Check if database exists
ls -lh cfb_rankings.db

# If missing, create it
source venv/bin/activate
python3 -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"

# Import data
export CFBD_API_KEY='your-api-key-here'
python3 import_real_data.py

# Verify data was imported
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM teams;"
```

### Issue 3: Permission Denied Errors

**Symptoms:**
- Logs show "Permission denied" for database file
- Backend can't write to database

**Fix:**
```bash
cd /var/www/cfb-rankings

# Fix ownership
sudo chown -R www-data:www-data .

# Fix database file permissions specifically
sudo chmod 664 cfb_rankings.db
sudo chown www-data:www-data cfb_rankings.db

# Restart service
sudo systemctl restart cfb-rankings
```

### Issue 4: Port 8000 Already in Use

**Symptoms:**
- Logs show "Address already in use"
- Service fails to start

**Fix:**
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process (use PID from lsof output)
sudo kill -9 <PID>

# Or kill all processes on port 8000
sudo lsof -ti:8000 | xargs sudo kill -9

# Restart service
sudo systemctl restart cfb-rankings
```

### Issue 5: CORS Errors in Browser

**Symptoms:**
- Browser console shows CORS error
- Frontend can't fetch from API

**Fix:**
```bash
# Edit main.py to ensure CORS is enabled
cd /var/www/cfb-rankings
nano main.py

# Verify these lines exist (around line 20-30):
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, specify your domain
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Restart service after any changes
sudo systemctl restart cfb-rankings
```

### Issue 6: Nginx Not Proxying to Backend

**Symptoms:**
- Nginx is running but API calls fail
- 502 Bad Gateway errors

**Fix:**
```bash
# Check Nginx config
sudo nano /etc/nginx/sites-available/cfb-rankings

# Verify proxy_pass line exists:
# location /api {
#     proxy_pass http://localhost:8000;
#     ...
# }

# Test config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Issue 7: Python Dependencies Missing

**Symptoms:**
- Logs show "ModuleNotFoundError"
- Service won't start

**Fix:**
```bash
cd /var/www/cfb-rankings

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Or if you have requirements-prod.txt
pip install -r requirements-prod.txt

# Restart service
deactivate
sudo systemctl restart cfb-rankings
```

### Issue 8: Environment Variables Not Set

**Symptoms:**
- API key errors in logs
- Database URL errors

**Fix:**
```bash
cd /var/www/cfb-rankings

# Check if .env file exists
ls -lh .env

# Create or edit .env
nano .env

# Add required variables:
# CFBD_API_KEY=your_actual_key_here
# DATABASE_URL=sqlite:///./cfb_rankings.db

# Edit systemd service to load .env
sudo nano /etc/systemd/system/cfb-rankings.service

# Ensure EnvironmentFile line exists:
# [Service]
# EnvironmentFile=/var/www/cfb-rankings/.env
# ...

# Reload systemd and restart
sudo systemctl daemon-reload
sudo systemctl restart cfb-rankings
```

---

## Diagnostic Script

Run this comprehensive diagnostic script:

```bash
#!/bin/bash
# Save as: diagnose-cfb.sh
# Run with: bash diagnose-cfb.sh

echo "=== CFB Rankings Diagnostic Report ==="
echo "Generated: $(date)"
echo ""

echo "=== 1. Service Status ==="
sudo systemctl status cfb-rankings --no-pager | head -20
echo ""

echo "=== 2. Port 8000 Check ==="
sudo lsof -i :8000 || echo "Nothing listening on port 8000"
echo ""

echo "=== 3. API Health Check ==="
curl -s http://localhost:8000/ || echo "API not responding"
echo ""

echo "=== 4. Database Check ==="
cd /var/www/cfb-rankings
ls -lh cfb_rankings.db 2>/dev/null || echo "Database file not found"
echo ""

echo "=== 5. Database Row Counts ==="
sqlite3 cfb_rankings.db "SELECT 'Teams:', COUNT(*) FROM teams; SELECT 'Games:', COUNT(*) FROM games;" 2>/dev/null || echo "Can't query database"
echo ""

echo "=== 6. Recent Logs (Last 20 lines) ==="
sudo journalctl -u cfb-rankings -n 20 --no-pager
echo ""

echo "=== 7. Nginx Status ==="
sudo systemctl status nginx --no-pager | head -10
echo ""

echo "=== 8. Nginx Error Log (Last 10 lines) ==="
sudo tail -10 /var/log/nginx/cfb-rankings-error.log 2>/dev/null || echo "No Nginx error log"
echo ""

echo "=== 9. File Permissions ==="
ls -lh /var/www/cfb-rankings/cfb_rankings.db 2>/dev/null
echo ""

echo "=== 10. Environment File ==="
if [ -f /var/www/cfb-rankings/.env ]; then
    echo ".env file exists"
    echo "Size: $(wc -l < /var/www/cfb-rankings/.env) lines"
else
    echo ".env file NOT FOUND"
fi
echo ""

echo "=== Diagnostic Complete ==="
```

Copy this script to your server and run it to get a full diagnostic report.

---

## Step-by-Step Troubleshooting Workflow

Follow this exact sequence:

### Phase 1: Identify the Problem

```bash
# 1. SSH into server
ssh user@cfb.bdailey.com

# 2. Check service status
sudo systemctl status cfb-rankings

# 3a. If service is RUNNING → Go to Phase 2
# 3b. If service is NOT RUNNING → Go to Phase 3
```

### Phase 2: Service Running, But API Failing

```bash
# 1. Test API locally
curl http://localhost:8000/

# 2a. If API responds → Go to Phase 4 (Nginx issue)
# 2b. If API doesn't respond → Check logs

# 3. Check logs for errors
sudo journalctl -u cfb-rankings -n 50

# 4. Common errors:
#    - Database locked → Restart service
#    - Permission denied → Fix permissions (see Issue 3)
#    - Module not found → Reinstall dependencies (see Issue 7)
```

### Phase 3: Service Not Running

```bash
# 1. Try to start service
sudo systemctl start cfb-rankings

# 2. Check if it started
sudo systemctl status cfb-rankings

# 3a. If started → Go to Phase 2
# 3b. If failed → Check logs

# 4. View startup errors
sudo journalctl -u cfb-rankings -n 50

# 5. Fix the error from logs, then retry
```

### Phase 4: API Working Locally, But Not From Browser

```bash
# 1. Test API from outside
curl https://cfb.bdailey.com/api/rankings

# 2a. If works → Frontend JavaScript issue
# 2b. If fails → Nginx configuration issue

# 3. Check Nginx config
sudo nginx -t

# 4. Check Nginx error log
sudo tail -50 /var/log/nginx/cfb-rankings-error.log

# 5. Verify proxy_pass is correct
sudo nano /etc/nginx/sites-available/cfb-rankings
# Should have: proxy_pass http://localhost:8000;
```

---

## Quick Fixes Summary

| Symptom | Quick Fix Command |
|---------|------------------|
| Service not running | `sudo systemctl restart cfb-rankings` |
| Port already in use | `sudo lsof -ti:8000 \| xargs sudo kill -9 && sudo systemctl restart cfb-rankings` |
| Permission denied | `sudo chown -R www-data:www-data /var/www/cfb-rankings && sudo systemctl restart cfb-rankings` |
| Database missing | `cd /var/www/cfb-rankings && source venv/bin/activate && python3 import_real_data.py` |
| Nginx 502 error | `sudo systemctl restart cfb-rankings && sudo systemctl reload nginx` |
| Module not found | `cd /var/www/cfb-rankings && source venv/bin/activate && pip install -r requirements.txt && deactivate && sudo systemctl restart cfb-rankings` |

---

## Emergency Restart Procedure

If nothing else works, try a full restart:

```bash
# 1. Stop everything
sudo systemctl stop cfb-rankings
sudo systemctl stop nginx

# 2. Kill any lingering processes
sudo lsof -ti:8000 | xargs sudo kill -9 2>/dev/null || true

# 3. Fix permissions
cd /var/www/cfb-rankings
sudo chown -R www-data:www-data .

# 4. Start backend
sudo systemctl start cfb-rankings

# 5. Wait 5 seconds
sleep 5

# 6. Check backend started
sudo systemctl status cfb-rankings

# 7. Start Nginx
sudo systemctl start nginx

# 8. Test API
curl http://localhost:8000/api/rankings

# 9. Test from outside
curl https://cfb.bdailey.com/api/rankings
```

---

## Contact Information

If you're still stuck after trying these steps, gather the following information:

1. Output of: `sudo systemctl status cfb-rankings`
2. Output of: `sudo journalctl -u cfb-rankings -n 50`
3. Output of: `curl http://localhost:8000/`
4. Browser console errors (screenshot)
5. Output of: `sudo nginx -t`

Then provide this information for further assistance.

---

**Last Updated:** 2025-10-17
**Server:** cfb.bdailey.com
**Application:** College Football Rankings System
