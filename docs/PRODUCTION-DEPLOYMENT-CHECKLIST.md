# Production Deployment Checklist

**Quick reference for deploying code to production server**
**Server:** `/var/www/cfb-rankings`

---

## ⚙️ One-Time Setup (if not already done)

### Virtual Environment Setup

✅ **IMPORTANT:** Production uses a Python virtual environment. If not set up:

```bash
cd /var/www/cfb-rankings
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install python-dotenv requests sqlalchemy fastapi uvicorn pydantic
```

📖 **Full guide:** `docs/PRODUCTION-VENV-SETUP.md`

---

## 🚀 Standard Deployment Steps

### 1. Pull Latest Code

```bash
cd /var/www/cfb-rankings
git pull origin main
```

### 2. Install New Dependencies (if needed)

```bash
# If new packages were added
sudo -u www-data venv/bin/pip install <package-name>

# Or from requirements.txt
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### 3. Run Database Migrations (if needed)

```bash
# Check for new migration scripts (migrate_*.py)
ls -la migrate_*.py

# Run migration using venv Python
sudo -u www-data venv/bin/python migrate_<name>.py
```

### 4. Run Import/Update Scripts (if needed)

```bash
# Full import (use with caution)
sudo -u www-data venv/bin/python import_real_data.py

# Weekly update
sudo -u www-data venv/bin/python scripts/weekly_update.py
```

### 5. Restart Services (if needed)

```bash
# Restart application service (if exists)
sudo systemctl restart cfb-rankings.service

# Or restart web server
sudo systemctl restart nginx
```

### 6. Verify Deployment

```bash
# Check service status
sudo systemctl status cfb-rankings.service

# Test import
sudo -u www-data venv/bin/python -c "import dotenv; print('✓ OK')"

# Check logs
sudo journalctl -u cfb-rankings.service -n 50
```

---

## 🔧 Common Commands

### Using Virtual Environment

**Always use venv Python on production:**

```bash
# Run script
sudo -u www-data venv/bin/python script.py

# Install package
sudo -u www-data venv/bin/pip install <package>

# Check packages
sudo -u www-data venv/bin/pip list
```

### Database Operations

```bash
# Run migration
sudo -u www-data venv/bin/python migrate_<name>.py

# Check database
sudo -u www-data sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games;"
```

### Git Operations

```bash
# Check status
git status

# Pull latest
git pull origin main

# View recent commits
git log --oneline -5
```

---

## 📋 Epic-Specific Checklists

### EPIC-022: Conference Championships

```bash
# 1. Pull code
git pull origin main

# 2. Run migration
sudo -u www-data venv/bin/python migrate_add_game_type.py

# 3. Import data (includes conference championships)
sudo -u www-data venv/bin/python import_real_data.py

# 4. Verify
sudo -u www-data venv/bin/python -c "
from database import SessionLocal
from models import Game
db = SessionLocal()
count = db.query(Game).filter(Game.game_type == 'conference_championship').count()
print(f'Conference championships: {count}')
"
```

### EPIC-021: Quarter-Weighted ELO

```bash
# 1. Pull code
git pull origin main

# 2. Run migration
sudo -u www-data venv/bin/python migrate_add_quarter_scores.py

# 3. Backfill quarter scores
sudo -u www-data venv/bin/python scripts/backfill_quarter_scores.py

# 4. Verify
sudo -u www-data sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE q1_home IS NOT NULL;"
```

---

## 🆘 Troubleshooting

### Error: "No module named 'dotenv'"

```bash
# Install missing package
sudo -u www-data venv/bin/pip install python-dotenv
```

### Error: "externally-managed-environment"

```bash
# You're using system pip instead of venv pip
# Use: venv/bin/pip instead of pip3
sudo -u www-data venv/bin/pip install <package>
```

### Error: "Permission denied"

```bash
# Always run as www-data user
sudo -u www-data venv/bin/python script.py
```

### Service Won't Start

```bash
# Check logs
sudo journalctl -u cfb-rankings.service -n 100

# Verify service file uses venv Python
sudo cat /etc/systemd/system/cfb-rankings.service
# Should have: ExecStart=/var/www/cfb-rankings/venv/bin/python

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart cfb-rankings.service
```

---

## 📚 Documentation Links

- **Virtual Environment Setup:** `docs/PRODUCTION-VENV-SETUP.md` (comprehensive guide)
- **Troubleshooting:** `docs/PRODUCTION-TROUBLESHOOTING.md`
- **Weekly Workflow:** `docs/WEEKLY-WORKFLOW.md`
- **Update Game Data:** `docs/UPDATE-GAME-DATA.md`

---

## ⚠️ Important Reminders

- ✅ **Always use venv Python:** `sudo -u www-data venv/bin/python`
- ✅ **Always run as www-data:** `sudo -u www-data`
- ✅ **Test migrations on dev first:** Never run untested migrations on production
- ✅ **Backup before major changes:** Database backups are your friend
- ✅ **Check logs after deployment:** Verify everything is working

---

**Last Updated:** 2025-11-30
**Maintained By:** Development Team
