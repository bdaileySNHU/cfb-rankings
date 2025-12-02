# Season Management Guide

**EPIC-024 Story 24.3** - Process and procedures for managing college football seasons

---

## Overview

This document describes how to manage season transitions in the CFB Rankings system. Each season must be properly initialized and archived to maintain data integrity and prevent cross-season contamination.

## Season Lifecycle

```
[Preseason] → [Active Season] → [Archived Season]
     ↓              ↓                   ↓
  Week 0        Weeks 1-15           Read-only
ELO reset    Games processed      Historical data
```

### Season States

| State | `is_active` | Description |
|-------|-------------|-------------|
| **Preseason** | True | Season created, no games yet |
| **Active** | True | Games being played and processed |
| **Archived** | False | Season complete, data frozen |

---

## Starting a New Season

### Prerequisites

Before starting a new season, ensure:
- [ ] Previous season is complete (all games processed)
- [ ] Team metadata is up to date (conferences, recruiting ranks)
- [ ] Database backup created
- [ ] Previous season archived (optional)

### Initialization Script

Use the `start_new_season.py` script to initialize a new season:

```bash
# Dry run first (recommended)
python scripts/start_new_season.py --season 2026 --dry-run

# Actual initialization
python scripts/start_new_season.py --season 2026
```

### What the Script Does

1. **Validates** that new season doesn't already exist
2. **Archives** previous season (sets `is_active=False`)
3. **Creates** new season record (year, current_week=1, is_active=True)
4. **Resets** team ELO ratings to preseason values
5. **Saves** preseason rankings (Week 0) to ranking_history

### Manual Steps After Initialization

After running the initialization script:

1. **Import games for the new season:**
   ```bash
   python import_real_data.py --season 2026
   ```

2. **Verify preseason rankings:**
   ```bash
   curl https://cfb.bdailey.com/api/rankings?season=2026
   ```

3. **Update production:**
   ```bash
   # On production server
   cd /var/www/cfb-rankings
   git pull origin main
   sudo -u www-data /var/www/cfb-rankings/venv/bin/python scripts/start_new_season.py --season 2026
   sudo systemctl restart cfb-rankings
   ```

---

## Weekly Workflow

### Processing Weekly Results

```bash
# 1. Import new games for the week
python import_real_data.py --season 2025

# 2. Process completed games
python scripts/weekly_update.py --season 2025 --week 5

# 3. Verify rankings
curl https://cfb.bdailey.com/api/rankings?season=2025
```

### Automated Weekly Updates

The system uses a systemd timer for automated updates:

```bash
# Check timer status
sudo systemctl status cfb-rankings-weekly.timer

# View recent runs
sudo journalctl -u cfb-rankings-weekly.service -n 50

# Manual trigger
sudo systemctl start cfb-rankings-weekly.service
```

**Schedule:** Sundays at 5:00 PM ET

---

## Archiving a Season

### When to Archive

Archive a season when:
- All regular season games complete
- All bowl games complete
- Playoff/championship games complete
- No more updates needed

### How to Archive

```bash
# Option 1: Automatic (during new season initialization)
python scripts/start_new_season.py --season 2026
# This automatically archives 2025

# Option 2: Manual
python -c "
from database import SessionLocal
from models import Season

db = SessionLocal()
season = db.query(Season).filter(Season.year == 2025).first()
season.is_active = False
db.commit()
print(f'Archived season {season.year}')
"
```

### Verification

```bash
# Check season status
python -c "
from database import SessionLocal
from models import Season

db = SessionLocal()
seasons = db.query(Season).order_by(Season.year.desc()).limit(3).all()
for s in seasons:
    status = 'ACTIVE' if s.is_active else 'ARCHIVED'
    print(f'{s.year}: Week {s.current_week} - {status}')
"
```

---

## Data Integrity

### Season Isolation

**Critical:** Each season's data must be isolated:

- ✅ **Wins/Losses:** Season-specific (from `ranking_history`, not `teams`)
- ✅ **ELO Ratings:** Reset at season start, tracked in `ranking_history`
- ✅ **Games:** Filtered by `season` field
- ✅ **Rankings:** Queried from `ranking_history` by season/week

### Validation Checks

Run these checks after season operations:

```bash
# 1. Check for duplicate rankings
python scripts/check_ranking_duplicates.py

# 2. Verify season-specific records
python scripts/validate_season_data.py --season 2025

# 3. Check team record accuracy
python -c "
from database import SessionLocal
from ranking_service import RankingService

db = SessionLocal()
rs = RankingService(db)

# Check specific team
team_id = 82  # Ohio State
wins, losses = rs.get_season_record(team_id, 2025)
print(f'Team {team_id} 2025 record: {wins}-{losses}')
"
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **Cumulative records** | Querying `teams.wins/losses` | Use `ranking_history` or `get_season_record()` |
| **Duplicate rankings** | `save_weekly_rankings()` run twice | Run `cleanup_ranking_duplicates.py --execute` |
| **Wrong season showing** | Missing season filter | Add `?season=YYYY` to API calls |
| **ELO not reset** | Forgot to run `start_new_season.py` | Manually reset with script |

---

## API Endpoints

### Season Information

```bash
# Get current active season
GET /api/seasons/current
Response: {"year": 2025, "current_week": 8, "is_active": true}

# Get specific season
GET /api/seasons/2024
Response: {"year": 2024, "current_week": 15, "is_active": false}

# List all seasons
GET /api/seasons
Response: [
  {"year": 2025, "current_week": 8, "is_active": true},
  {"year": 2024, "current_week": 15, "is_active": false}
]
```

### Rankings by Season

```bash
# Current season rankings
GET /api/rankings?season=2025

# Historical season rankings
GET /api/rankings?season=2024

# Specific week
GET /api/rankings?season=2024&week=10
```

---

## Troubleshooting

### Season Won't Initialize

**Error:** "Season 2025 already exists"

**Solution:**
```bash
# Check existing seasons
python -c "
from database import SessionLocal
from models import Season
db = SessionLocal()
seasons = db.query(Season).all()
for s in seasons:
    print(f'{s.year}: Week {s.current_week}, Active: {s.is_active}')
"

# Delete incorrect season if needed
python -c "
from database import SessionLocal
from models import Season
db = SessionLocal()
season = db.query(Season).filter(Season.year == 2025).first()
db.delete(season)
db.commit()
print('Deleted season 2025')
"
```

### Rankings Show Wrong Season

**Problem:** Rankings API returns data from wrong season

**Check:**
1. Verify season parameter in API call
2. Check current_week is set correctly
3. Ensure ranking_history has data for that season/week

```bash
# Check ranking_history data
python -c "
from database import SessionLocal
from models import RankingHistory
from sqlalchemy import func

db = SessionLocal()
counts = db.query(
    RankingHistory.season,
    RankingHistory.week,
    func.count(RankingHistory.id)
).group_by(
    RankingHistory.season,
    RankingHistory.week
).order_by(
    RankingHistory.season.desc(),
    RankingHistory.week.desc()
).limit(10).all()

for season, week, count in counts:
    print(f'Season {season}, Week {week}: {count} rankings')
"
```

---

## Best Practices

### Before Season Start
1. ✅ Backup production database
2. ✅ Update team metadata (conferences, recruiting)
3. ✅ Run initialization in dry-run mode first
4. ✅ Test on local/staging before production

### During Season
1. ✅ Monitor weekly update logs
2. ✅ Verify rankings after each update
3. ✅ Check for duplicate entries weekly
4. ✅ Backup database before major games

### After Season
1. ✅ Process all remaining games
2. ✅ Verify final rankings
3. ✅ Archive season
4. ✅ Create season summary/report

---

## Emergency Procedures

### Rollback Season Initialization

If season initialization goes wrong:

```bash
# 1. Restore database from backup
cp cfb_rankings.db.backup cfb_rankings.db

# 2. Or manually undo changes
python -c "
from database import SessionLocal
from models import Season

db = SessionLocal()

# Delete new season
new_season = db.query(Season).filter(Season.year == 2026).first()
if new_season:
    db.delete(new_season)

# Reactivate previous season
prev_season = db.query(Season).filter(Season.year == 2025).first()
if prev_season:
    prev_season.is_active = True

db.commit()
print('Rolled back season initialization')
"
```

### Force Season Reset

If team records are corrupted:

```bash
# Reset all teams for a season
python scripts/reset_season_records.py --season 2025 --reprocess-games
```

---

## Monitoring

### Health Checks

Regular checks to run:

```bash
# 1. Active season check
curl https://cfb.bdailey.com/api/seasons/current

# 2. Rankings API check
curl https://cfb.bdailey.com/api/rankings?limit=5

# 3. Duplicate check
python scripts/check_ranking_duplicates.py

# 4. Database size
ls -lh cfb_rankings.db
```

### Logs to Monitor

- `/var/log/cfb-rankings/weekly_update.log`
- `sudo journalctl -u cfb-rankings.service`
- `sudo journalctl -u cfb-rankings-weekly.service`

---

## Related Documentation

- [EPIC-024: Season-Specific Records](EPIC-024-SEASON-SPECIFIC-RECORDS.md)
- [Weekly Workflow](WEEKLY-WORKFLOW.md)
- [Production Deployment](PRODUCTION-DEPLOYMENT.md)

---

**Last Updated:** 2025-12-02
**EPIC:** EPIC-024 Story 24.3
**Maintained By:** Development Team
