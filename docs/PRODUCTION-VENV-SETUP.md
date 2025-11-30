# Production Virtual Environment Setup

**Purpose:** Document the Python virtual environment setup for production server
**Last Updated:** 2025-11-30
**Server:** `/var/www/cfb-rankings`

---

## Table of Contents

1. [Why Virtual Environment?](#why-virtual-environment)
2. [Initial Setup](#initial-setup)
3. [Installing Dependencies](#installing-dependencies)
4. [Running Scripts](#running-scripts)
5. [Updating Systemd Services](#updating-systemd-services)
6. [Maintenance](#maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Why Virtual Environment?

Modern Python installations (Python 3.11+) use "externally-managed-environment" protection to prevent pip from installing packages globally. This prevents conflicts between system packages and application dependencies.

**Benefits of using venv:**
- ✅ Isolated Python environment for the application
- ✅ Prevents conflicts with system packages
- ✅ Easy dependency management
- ✅ Better security (runs as www-data user)
- ✅ Reproducible deployments

**Error without venv:**
```
error: externally-managed-environment
× This environment is externally managed
```

---

## Initial Setup

### One-Time Virtual Environment Creation

Run these commands on the production server:

```bash
# Navigate to application directory
cd /var/www/cfb-rankings

# Create virtual environment (owned by www-data)
sudo -u www-data python3 -m venv venv

# Verify venv was created
ls -la venv/
# Should see: bin/ include/ lib/ pyvenv.cfg
```

### Install All Dependencies

```bash
cd /var/www/cfb-rankings

# Install core dependencies
sudo -u www-data venv/bin/pip install \
    python-dotenv \
    requests \
    sqlalchemy \
    fastapi \
    uvicorn \
    pydantic

# Or install from requirements.txt (if available)
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### Verify Installation

```bash
# Check installed packages
sudo -u www-data venv/bin/pip list

# Test Python import
sudo -u www-data venv/bin/python -c "import dotenv, requests, sqlalchemy; print('✓ All imports successful')"
```

---

## Installing Dependencies

### Adding New Dependencies

When deploying new code that requires additional packages:

```bash
cd /var/www/cfb-rankings

# Install new package
sudo -u www-data venv/bin/pip install <package-name>

# Example: Installing pytest for testing
sudo -u www-data venv/bin/pip install pytest
```

### Updating Existing Dependencies

```bash
# Upgrade specific package
sudo -u www-data venv/bin/pip install --upgrade <package-name>

# Upgrade all packages (use with caution)
sudo -u www-data venv/bin/pip list --outdated
sudo -u www-data venv/bin/pip install --upgrade <package-name>
```

### Freezing Dependencies

```bash
# Generate requirements.txt from current venv
sudo -u www-data venv/bin/pip freeze > requirements.txt

# Install from requirements.txt
sudo -u www-data venv/bin/pip install -r requirements.txt
```

---

## Running Scripts

### General Pattern

**Always use the venv Python interpreter:**

```bash
# DON'T use system Python:
python3 script.py                    # ❌ Wrong

# DO use venv Python:
sudo -u www-data venv/bin/python script.py    # ✅ Correct
```

### Common Scripts

#### Data Import

```bash
cd /var/www/cfb-rankings

# Regular import
sudo -u www-data venv/bin/python import_real_data.py

# With flags
sudo -u www-data venv/bin/python import_real_data.py --season 2024 --max-week 14
```

#### Database Migration

```bash
cd /var/www/cfb-rankings

# Run migration script
sudo -u www-data venv/bin/python migrate_add_game_type.py
```

#### Weekly Update Script

```bash
cd /var/www/cfb-rankings

# Manual weekly update
sudo -u www-data venv/bin/python scripts/weekly_update.py
```

#### FastAPI Application

```bash
cd /var/www/cfb-rankings

# Start application
sudo -u www-data venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Updating Systemd Services

### Update Service Files to Use Venv

All systemd service files must be updated to use the venv Python interpreter.

#### Example: Weekly Update Timer

**File:** `/etc/systemd/system/cfb-weekly-update.service`

**BEFORE (incorrect):**
```ini
[Service]
Type=oneshot
User=www-data
WorkingDirectory=/var/www/cfb-rankings
ExecStart=/usr/bin/python3 scripts/weekly_update.py
```

**AFTER (correct):**
```ini
[Service]
Type=oneshot
User=www-data
WorkingDirectory=/var/www/cfb-rankings
ExecStart=/var/www/cfb-rankings/venv/bin/python scripts/weekly_update.py
Environment="PATH=/var/www/cfb-rankings/venv/bin:/usr/bin:/bin"
```

#### Apply Changes

```bash
# After editing service file
sudo systemctl daemon-reload
sudo systemctl restart cfb-weekly-update.service

# Verify service works
sudo systemctl status cfb-weekly-update.service
```

### Services to Update

Check and update these service files:

- [ ] `/etc/systemd/system/cfb-weekly-update.service` - Weekly data import
- [ ] `/etc/systemd/system/cfb-rankings.service` - FastAPI application (if exists)
- [ ] Any other custom services that run Python scripts

---

## Maintenance

### Checking Venv Status

```bash
# Verify venv exists
ls -la /var/www/cfb-rankings/venv/

# Check venv Python version
/var/www/cfb-rankings/venv/bin/python --version

# List installed packages
sudo -u www-data /var/www/cfb-rankings/venv/bin/pip list
```

### Recreating Venv (if needed)

If the venv becomes corrupted or needs to be recreated:

```bash
cd /var/www/cfb-rankings

# Backup current venv (optional)
sudo mv venv venv.backup

# Create new venv
sudo -u www-data python3 -m venv venv

# Reinstall dependencies
sudo -u www-data venv/bin/pip install -r requirements.txt

# Test
sudo -u www-data venv/bin/python -c "import dotenv; print('✓ OK')"

# Remove backup after verification
sudo rm -rf venv.backup
```

### Disk Space

Virtual environments can use significant disk space. Monitor usage:

```bash
# Check venv size
du -sh /var/www/cfb-rankings/venv/

# Typical size: 50-200 MB
```

---

## Troubleshooting

### Error: "No module named 'dotenv'"

**Symptom:**
```
ModuleNotFoundError: No module named 'dotenv'
```

**Cause:** Not using venv Python, or package not installed in venv

**Fix:**
```bash
# Install missing package
sudo -u www-data venv/bin/pip install python-dotenv

# Verify you're using venv Python
which python3  # Should show venv/bin/python if in venv
```

### Error: "externally-managed-environment"

**Symptom:**
```
error: externally-managed-environment
× This environment is externally managed
```

**Cause:** Trying to use system pip instead of venv pip

**Fix:**
```bash
# DON'T use system pip:
pip install python-dotenv  # ❌ Wrong

# DO use venv pip:
sudo -u www-data venv/bin/pip install python-dotenv  # ✅ Correct
```

### Error: "Permission denied"

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/var/www/cfb-rankings/venv'
```

**Cause:** Running commands without `sudo -u www-data`

**Fix:**
```bash
# Always run as www-data user
sudo -u www-data venv/bin/python script.py
```

### Venv Not Found

**Symptom:**
```
bash: venv/bin/python: No such file or directory
```

**Cause:** Venv not created, or created in wrong location

**Fix:**
```bash
cd /var/www/cfb-rankings
sudo -u www-data python3 -m venv venv
```

### Import Works Locally But Not in Venv

**Symptom:** Script runs fine with system Python but fails in venv

**Cause:** Package installed globally but not in venv

**Fix:**
```bash
# Install package in venv specifically
sudo -u www-data venv/bin/pip install <missing-package>
```

### Systemd Service Fails After Venv Setup

**Symptom:** Service worked before, fails after switching to venv

**Cause:** Service file still points to system Python

**Fix:**
```bash
# Update service file to use venv Python
sudo nano /etc/systemd/system/<service-name>.service

# Change ExecStart to use venv/bin/python
ExecStart=/var/www/cfb-rankings/venv/bin/python script.py

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart <service-name>
```

---

## Quick Reference

### Most Common Commands

```bash
# Install new package
sudo -u www-data venv/bin/pip install <package>

# Run script
sudo -u www-data venv/bin/python <script.py>

# Check installed packages
sudo -u www-data venv/bin/pip list

# Upgrade package
sudo -u www-data venv/bin/pip install --upgrade <package>
```

### File Paths

- **Venv location:** `/var/www/cfb-rankings/venv/`
- **Venv Python:** `/var/www/cfb-rankings/venv/bin/python`
- **Venv pip:** `/var/www/cfb-rankings/venv/bin/pip`
- **Application root:** `/var/www/cfb-rankings/`

---

## Related Documentation

- **Production Deployment:** `docs/EPIC-001-PRODUCTION-DEPLOYMENT.md`
- **Troubleshooting:** `docs/PRODUCTION-TROUBLESHOOTING.md`
- **Weekly Updates:** `docs/WEEKLY-WORKFLOW.md`
- **Update Game Data:** `docs/UPDATE-GAME-DATA.md`

---

**Created:** 2025-11-30
**Maintained By:** Development Team
