# EPIC-004 Deployment Checklist

Quick reference checklist for deploying EPIC-004 changes to production.

## Pre-Deployment (Local Machine)

- [ ] All tests passing locally
- [ ] Changes committed to git
- [ ] Changes pushed to remote repository

**Commands:**
```bash
cd "/Users/bryandailey/Stat-urday Synthesis"
git add .
git commit -m "Add EPIC-004: Automated Updates and API Usage Tracking"
git push origin main
```

---

## Deployment (On VPS)

### 1. Pull Latest Code
- [ ] SSH into VPS
- [ ] Navigate to project directory
- [ ] Pull latest changes

```bash
ssh user@your-vps-ip
cd /var/www/cfb-rankings
sudo git pull origin main
```

### 2. Update Environment
- [ ] Add `CFBD_MONTHLY_LIMIT=1000` to `.env`

```bash
sudo nano /var/www/cfb-rankings/.env
# Add: CFBD_MONTHLY_LIMIT=1000
```

### 3. Install Dependencies
- [ ] Activate virtual environment
- [ ] Install requirements

```bash
cd /var/www/cfb-rankings
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Update Database
- [ ] Create new tables (`api_usage`, `update_tasks`)

```bash
python3 << 'PYEOF'
from database import engine, Base
from models import APIUsage, UpdateTask
Base.metadata.create_all(bind=engine)
print("✓ Database updated!")
PYEOF
```

### 5. Fix Permissions
- [ ] Set correct ownership and permissions

```bash
sudo chown -R www-data:www-data /var/www/cfb-rankings
sudo chmod 664 /var/www/cfb-rankings/cfb_rankings.db
```

### 6. Restart Application
- [ ] Restart the FastAPI service
- [ ] Verify it's running

```bash
sudo systemctl restart cfb-rankings
sudo systemctl status cfb-rankings
```

### 7. Install Weekly Update Timer
- [ ] Create log directory
- [ ] Copy systemd units
- [ ] Enable and start timer

```bash
sudo mkdir -p /var/log/cfb-rankings
sudo chown www-data:www-data /var/log/cfb-rankings
sudo cp deploy/cfb-weekly-update.timer /etc/systemd/system/
sudo cp deploy/cfb-weekly-update.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cfb-weekly-update.timer
sudo systemctl start cfb-weekly-update.timer
```

### 8. Verify Timer
- [ ] Check timer status
- [ ] View next scheduled run

```bash
sudo systemctl status cfb-weekly-update.timer
systemctl list-timers cfb-weekly-update.timer
```

---

## Post-Deployment Testing

### Test API Endpoints
- [ ] Health check
- [ ] API usage endpoint
- [ ] System config endpoint
- [ ] Manual update trigger
- [ ] Usage dashboard

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/admin/api-usage
curl http://localhost:8000/api/admin/config
curl http://localhost:8000/api/admin/usage-dashboard
curl -X POST http://localhost:8000/api/admin/trigger-update
```

### Verify Logs
- [ ] Application logs show no errors
- [ ] Weekly update log directory exists

```bash
sudo journalctl -u cfb-rankings -n 50 --no-pager
ls -la /var/log/cfb-rankings/
```

### Test Weekly Update Script
- [ ] Run manually to verify it works

```bash
cd /var/www/cfb-rankings
source venv/bin/activate
python3 scripts/weekly_update.py
```

---

## Verification

- [ ] Application service is running
- [ ] Weekly update timer is active and scheduled
- [ ] New database tables exist
- [ ] Environment variable `CFBD_MONTHLY_LIMIT` is set
- [ ] All admin endpoints return valid responses
- [ ] Logs directory created and accessible
- [ ] No errors in application logs
- [ ] Timer shows next scheduled run time

---

## Quick Commands

```bash
# Service status
sudo systemctl status cfb-rankings
sudo systemctl status cfb-weekly-update.timer

# View logs
sudo journalctl -u cfb-rankings -f
sudo tail -f /var/log/cfb-rankings/weekly-update.log

# Test endpoints
curl http://localhost:8000/api/admin/api-usage | jq
curl http://localhost:8000/api/admin/config | jq

# Restart if needed
sudo systemctl restart cfb-rankings
```

---

## Troubleshooting

**Application won't start:**
```bash
sudo journalctl -u cfb-rankings -n 100 --no-pager
sudo systemctl restart cfb-rankings
```

**Database errors:**
```bash
sudo chown www-data:www-data /var/www/cfb-rankings/cfb_rankings.db
sudo chmod 664 /var/www/cfb-rankings/cfb_rankings.db
```

**Timer not showing:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart cfb-weekly-update.timer
systemctl list-timers --all | grep cfb
```

---

## Rollback (If Needed)

```bash
cd /var/www/cfb-rankings
sudo git log --oneline  # Find previous commit
sudo git reset --hard <commit-hash>
sudo systemctl restart cfb-rankings
```

---

**Deployment Time Estimate:** 15-20 minutes

See **EPIC-004-DEPLOYMENT-GUIDE.md** for detailed instructions.
