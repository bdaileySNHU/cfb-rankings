# Deployment Guide - VPS Subdomain

This guide walks through deploying the College Football Rankings system to a VPS with a subdomain.

## Prerequisites

- Ubuntu/Debian VPS with root access
- Domain with DNS control (to create subdomain)
- Basic Linux/SSH knowledge
- CollegeFootballData.com API key

## Architecture

```
Internet → Nginx (cfb.yourdomain.com:443)
              ├─> Static Files (frontend/)
              └─> Gunicorn (FastAPI) → SQLite Database
```

## Step 1: DNS Configuration

Before deploying, set up your subdomain DNS:

1. Log into your domain registrar/DNS provider
2. Create an **A Record**:
   - Name: `cfb` (or your chosen subdomain)
   - Type: `A`
   - Value: Your VPS IP address
   - TTL: 3600 (or default)

3. Wait for DNS propagation (5-30 minutes)
4. Test: `ping cfb.yourdomain.com` should return your VPS IP

## Step 2: Transfer Files to VPS

### Option A: Using SCP (Simple)

```bash
# From your local machine
cd "/Users/bryandailey/Stat-urday Synthesis"
scp -r * user@your-vps-ip:/tmp/cfb-rankings/

# Then on VPS
ssh user@your-vps-ip
sudo mkdir -p /var/www/cfb-rankings
sudo cp -r /tmp/cfb-rankings/* /var/www/cfb-rankings/
```

### Option B: Using Git (Recommended)

```bash
# On your local machine, create git repository
cd "/Users/bryandailey/Stat-urday Synthesis"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/cfb-rankings.git
git push -u origin main

# On VPS
ssh user@your-vps-ip
cd /var/www
sudo git clone https://github.com/yourusername/cfb-rankings.git
```

## Step 3: Run Initial Setup

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Navigate to setup script
cd /var/www/cfb-rankings

# Edit setup script with your domain
sudo nano deploy/setup.sh
# Change: DOMAIN="cfb.yourdomain.com"

# Run setup (this installs everything)
sudo bash deploy/setup.sh
```

The setup script will:
- ✅ Install Python, Nginx, Certbot, dependencies
- ✅ Create virtual environment
- ✅ Install Python packages
- ✅ Configure systemd service
- ✅ Set up Nginx with SSL
- ✅ Create database
- ✅ Optionally import real data

## Step 4: Configure Environment

The setup script will prompt you to edit `.env`:

```bash
CFBD_API_KEY=your_actual_api_key_here
DATABASE_URL=sqlite:///./cfb_rankings.db
```

## Step 5: Import Data

If you didn't import during setup:

```bash
cd /var/www/cfb-rankings
source venv/bin/activate
python3 import_real_data.py
```

## Step 6: Verify Deployment

1. **Check service status:**
```bash
sudo systemctl status cfb-rankings
```

2. **Check Nginx:**
```bash
sudo nginx -t
sudo systemctl status nginx
```

3. **View logs:**
```bash
# Application logs
sudo journalctl -u cfb-rankings -f

# Nginx logs
sudo tail -f /var/log/nginx/cfb-rankings-access.log
sudo tail -f /var/log/nginx/cfb-rankings-error.log
```

4. **Test in browser:**
   - Visit: `https://cfb.yourdomain.com`
   - API Docs: `https://cfb.yourdomain.com/docs`

## Deployment Updates

After making changes locally, deploy updates:

```bash
# Push changes to git
git add .
git commit -m "Update description"
git push

# On VPS, run deploy script
ssh user@your-vps-ip
cd /var/www/cfb-rankings
sudo ./deploy/deploy.sh
```

## Useful Commands

### Service Management
```bash
# Restart application
sudo systemctl restart cfb-rankings

# View status
sudo systemctl status cfb-rankings

# View logs (follow)
sudo journalctl -u cfb-rankings -f

# Stop/Start
sudo systemctl stop cfb-rankings
sudo systemctl start cfb-rankings
```

### Nginx
```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx
```

### Database
```bash
# Backup database
cd /var/www/cfb-rankings
cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d).db

# Re-import fresh data
source venv/bin/activate
python3 import_real_data.py
```

## Scheduled Updates (Optional)

To automatically update rankings weekly:

```bash
# Edit crontab
sudo crontab -e

# Add this line to run every Monday at 2 AM
0 2 * * 1 cd /var/www/cfb-rankings && /var/www/cfb-rankings/venv/bin/python3 import_real_data.py >> /var/log/cfb-rankings/cron.log 2>&1
```

## Troubleshooting

### Application won't start
```bash
# Check logs
sudo journalctl -u cfb-rankings -n 50

# Check if port 8000 is in use
sudo netstat -tulpn | grep 8000

# Restart service
sudo systemctl restart cfb-rankings
```

### SSL Certificate Issues
```bash
# Renew certificate manually
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

### Database Permission Issues
```bash
# Fix permissions
sudo chown -R www-data:www-data /var/www/cfb-rankings
```

### Nginx 502 Bad Gateway
```bash
# Check if Gunicorn is running
sudo systemctl status cfb-rankings

# Check Gunicorn logs
sudo journalctl -u cfb-rankings -f

# Restart both services
sudo systemctl restart cfb-rankings
sudo systemctl restart nginx
```

## Security Checklist

- ✅ SSL/TLS enabled (Let's Encrypt)
- ✅ Firewall configured (allow 80, 443, SSH)
- ✅ SSH key authentication (disable password auth)
- ✅ Regular security updates: `sudo apt-get update && sudo apt-get upgrade`
- ✅ Database backups scheduled
- ✅ Application logs monitored

## Performance Optimization

### For High Traffic

1. **Upgrade to PostgreSQL:**
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb cfb_rankings

# Update .env
DATABASE_URL=postgresql://user:password@localhost/cfb_rankings
```

2. **Add Redis caching:**
```bash
# Install Redis
sudo apt-get install redis-server

# Update application to cache API responses
```

3. **Increase Gunicorn workers:**
Edit `gunicorn_config.py`:
```python
workers = 8  # 2-4 per CPU core
```

## Monitoring

### Set up basic monitoring:

```bash
# Install htop for resource monitoring
sudo apt-get install htop

# Create monitoring script
cat > /usr/local/bin/cfb-monitor.sh << 'EOF'
#!/bin/bash
echo "=== Service Status ==="
systemctl status cfb-rankings --no-pager
echo ""
echo "=== Nginx Status ==="
systemctl status nginx --no-pager
echo ""
echo "=== Disk Usage ==="
df -h /var/www/cfb-rankings
echo ""
echo "=== Memory Usage ==="
free -h
EOF

chmod +x /usr/local/bin/cfb-monitor.sh
```

## Support

For issues:
1. Check logs: `sudo journalctl -u cfb-rankings -f`
2. Check Nginx: `sudo nginx -t`
3. Check database: `ls -lh /var/www/cfb-rankings/*.db`
4. Review this deployment guide

## Directory Structure on VPS

```
/var/www/cfb-rankings/
├── main.py                 # FastAPI application
├── models.py               # Database models
├── database.py             # Database configuration
├── ranking_service.py      # ELO ranking logic
├── cfbd_client.py          # API client
├── import_real_data.py     # Data import script
├── gunicorn_config.py      # Gunicorn configuration
├── requirements-prod.txt   # Python dependencies
├── .env                    # Environment variables (API key)
├── cfb_rankings.db         # SQLite database
├── venv/                   # Python virtual environment
├── frontend/               # Static web files
│   ├── index.html
│   ├── teams.html
│   ├── games.html
│   ├── team.html
│   ├── comparison.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js
│       ├── app.js
│       ├── team.js
│       └── comparison.js
└── deploy/
    ├── setup.sh            # Initial setup script
    ├── deploy.sh           # Update deployment script
    ├── nginx.conf          # Nginx configuration
    └── cfb-rankings.service # Systemd service file

/etc/nginx/sites-available/
└── cfb-rankings            # Nginx config (copied from deploy/)

/etc/systemd/system/
└── cfb-rankings.service    # Systemd service (copied from deploy/)

/var/log/cfb-rankings/
├── access.log              # Gunicorn access logs
└── error.log               # Gunicorn error logs

/var/log/nginx/
├── cfb-rankings-access.log # Nginx access logs
└── cfb-rankings-error.log  # Nginx error logs
```

## Optional: Automated Weekly Updates

The system includes automated weekly updates that run every Sunday at 8:00 PM ET during the active season (August - January).

### Installing Weekly Update Timer

1. **Create log directory:**
```bash
sudo mkdir -p /var/log/cfb-rankings
sudo chown www-data:www-data /var/log/cfb-rankings
```

2. **Copy systemd units:**
```bash
sudo cp /var/www/cfb-rankings/deploy/cfb-weekly-update.timer /etc/systemd/system/
sudo cp /var/www/cfb-rankings/deploy/cfb-weekly-update.service /etc/systemd/system/
```

3. **Enable and start timer:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable cfb-weekly-update.timer
sudo systemctl start cfb-weekly-update.timer
```

4. **Verify timer is active:**
```bash
sudo systemctl status cfb-weekly-update.timer
sudo systemctl list-timers --all | grep cfb
```

### Managing Weekly Updates

**View recent update logs:**
```bash
sudo tail -f /var/log/cfb-rankings/weekly-update.log
```

**View systemd journal:**
```bash
sudo journalctl -u cfb-weekly-update -n 50
```

**Manually trigger an update:**
```bash
sudo systemctl start cfb-weekly-update.service
```

**Disable automatic updates:**
```bash
sudo systemctl stop cfb-weekly-update.timer
sudo systemctl disable cfb-weekly-update.timer
```

**Re-enable automatic updates:**
```bash
sudo systemctl enable cfb-weekly-update.timer
sudo systemctl start cfb-weekly-update.timer
```

### How Weekly Updates Work

The weekly update script (`scripts/weekly_update.py`) performs these pre-flight checks:

1. **Active Season Check** - Verifies current date is August 1 - January 31
2. **Current Week Detection** - Queries CFBD API to find the current week
3. **API Usage Check** - Ensures API usage is below 90% of monthly limit

If all checks pass, it runs `import_real_data.py` to import new game data.

If any check fails, the update is skipped and logged (not considered an error for off-season).

### Troubleshooting

**Timer not triggering:**
```bash
# Check timer status
sudo systemctl status cfb-weekly-update.timer

# Reload systemd if units were modified
sudo systemctl daemon-reload
sudo systemctl restart cfb-weekly-update.timer
```

**Update failing:**
```bash
# Check logs
sudo journalctl -u cfb-weekly-update -n 100

# Check weekly update log
sudo cat /var/log/cfb-rankings/weekly-update.log

# Run manually for debugging
cd /var/www/cfb-rankings
sudo -u www-data /var/www/cfb-rankings/venv/bin/python scripts/weekly_update.py
```

**API usage warnings:**
If you see "API usage at 90% - aborting" messages:
1. Check current usage: `curl http://localhost:8000/api/admin/api-usage`
2. Consider upgrading to a paid CFBD API plan
3. Adjust `CFBD_MONTHLY_LIMIT` in `.env` if you upgrade
```
