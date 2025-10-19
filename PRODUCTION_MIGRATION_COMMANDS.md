# Production Migration Commands - Quick Reference

**Run these commands on your production server as user `bdailey`**

## Step 1: Stop the Application Service
```bash
sudo systemctl stop cfb-rankings
```

## Step 2: Verify Service is Stopped
```bash
sudo systemctl status cfb-rankings
# Should show "inactive (dead)"
```

## Step 3: Run Database Migration
```bash
cd /var/www/cfb-rankings
sudo python3 migrate_add_fcs_fields.py
```

**Expected Output:**
```
Starting migration...
  Adding teams.is_fcs column...
  Adding games.excluded_from_rankings column...
  Creating index on games.excluded_from_rankings...

Verifying migration...
  ✓ teams.is_fcs exists
  ✓ games.excluded_from_rankings exists
  ✓ Index idx_games_excluded_from_rankings exists
  ✓ All existing games have excluded_from_rankings=False
  ✓ All existing teams have is_fcs=False

Migration completed successfully!
```

## Step 4: Restart Application Service
```bash
sudo systemctl restart cfb-rankings
```

## Step 5: Verify Service is Running
```bash
sudo systemctl status cfb-rankings
# Should show "active (running)"

# Check logs for errors
sudo journalctl -u cfb-rankings -n 50 --no-pager
```

## Step 6: Test API Endpoint
```bash
curl http://localhost:8000/api/stats
```

## Step 7: Re-Import Data with FCS Games
```bash
cd /var/www/cfb-rankings

# Make sure CFBD API key is set
export CFBD_API_KEY='your-api-key-here'
# Or verify it's in .env file
cat .env | grep CFBD_API_KEY

# Run import (this will take 5-10 minutes)
echo "yes" | python3 import_real_data.py
```

**Expected to see:**
- FBS vs FBS games imported (processed for rankings)
- FBS vs FCS games imported with "(FCS - not ranked)" notation
- Example: "Ohio State vs Grambling (FCS - not ranked)"

## Step 8: Verify FCS Games in API
```bash
# Check Ohio State's schedule (team ID 82)
curl http://localhost:8000/api/teams/82/schedule?season=2025 | python3 -m json.tool
```

**Look for:**
- Week 2 game against Grambling
- `"excluded_from_rankings": true`
- `"is_fcs": true`

## Step 9: Verify Frontend
Open your production URL in a browser and check:
- Main rankings page shows "FBS" note next to team records
- Info box visible: "Team records and rankings reflect FBS opponents only..."
- Team detail page for Ohio State shows Week 2 Grambling game with gray background and FCS badge

---

## If Migration Fails - Rollback

```bash
# Restore from backup
sudo cp cfb_rankings.db.backup-TIMESTAMP cfb_rankings.db

# Reset to previous commit
sudo git reset --hard HEAD~1

# Restart service
sudo systemctl start cfb-rankings
```

---

## Notes:
- Migration must run with `sudo` because database is owned by `www-data`
- Service must be stopped before migration to release database lock
- Data re-import is required to populate FCS games
- Entire process takes ~15-20 minutes (migration 2 min, import 5-10 min)
