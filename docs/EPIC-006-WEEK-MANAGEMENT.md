# Week Management Guide - EPIC-006

## Overview

The current week for each season is tracked in the `seasons.current_week` field and displayed on the frontend rankings page. This guide covers how week tracking works, how to manually correct it, and how to troubleshoot issues.

**Related Documentation:**
- [EPIC-006 Overview](EPIC-006-CURRENT-WEEK-ACCURACY.md)
- [Story 001: Investigation](EPIC-006-STORY-001.md)
- [Story 002: Implementation](EPIC-006-STORY-002.md)
- [Story 003: Validation & Monitoring](EPIC-006-STORY-003.md)

---

## Automatic Week Tracking

### How It Works

The weekly update script (`scripts/weekly_update.py`) automatically updates `Season.current_week` through two mechanisms:

1. **Primary:** `import_real_data.py` updates the week based on imported game data (import_real_data.py:533)
2. **Redundancy:** `update_current_week()` function provides a safety net (weekly_update.py:200-275)

### Week Detection Logic

```python
# Find max week from processed games
max_week = db.query(func.max(Game.week)).filter(
    Game.season == season_year,
    Game.is_processed == True
).scalar()

# Default to 0 if no games processed
max_week = max_week or 0

# Validate week is in range 0-15
if validate_week_number(max_week, season_year):
    season.current_week = max_week
```

### Validation Rules

Week numbers must pass these validation checks:

- **Type:** Must be an integer
- **Minimum:** 0 (preseason/Week 0 games)
- **Maximum:** 15 (includes bowl season and playoffs)

Invalid week numbers are logged and rejected, preserving the previous valid value.

---

## Manual Week Correction

If the current week is incorrect, use one of these methods:

### Option 1: Admin API Endpoint (Recommended)

**Endpoint:** `POST /api/admin/update-current-week`

**Parameters:**
- `year` (int): Season year (e.g., 2025)
- `week` (int): Week number to set (0-15)

**Example:**

```bash
curl -X POST "http://your-domain.com/api/admin/update-current-week?year=2025&week=8"
```

**Response (Success):**

```json
{
  "success": true,
  "season": 2025,
  "old_week": 7,
  "new_week": 8,
  "message": "Current week updated from 7 to 8"
}
```

**Response (Invalid Week):**

```json
{
  "detail": "Week must be between 0 and 15, got 20"
}
```

**Advantages:**
- Validates week number automatically
- Logs changes for audit trail
- Returns clear success/error messages
- No need for database access or server restart

### Option 2: Direct Database Update

**Use when:** Admin endpoint is unavailable or you have direct database access

**Steps:**

```bash
# SSH to server
ssh user@your-vps-server

# Navigate to project directory
cd /var/www/cfb-rankings

# Update database
sqlite3 cfb_rankings.db "UPDATE seasons SET current_week = 8 WHERE year = 2025;"

# Restart server to pick up changes
sudo systemctl restart gunicorn

# Verify change
curl http://your-domain.com/api/stats | jq .current_week
```

**Advantages:**
- Works even if API server is down
- Direct control over database

**Disadvantages:**
- Requires database access and restart
- No automatic validation
- No automatic logging

---

## Monitoring

### Check Current Week

**Via API:**

```bash
curl http://your-domain.com/api/stats | jq '.current_week'
```

**Via Database:**

```bash
sqlite3 cfb_rankings.db "SELECT year, current_week, is_active FROM seasons WHERE year = 2025;"
```

### Check Week History

**View recent week changes from logs:**

```bash
# If using systemd/journalctl
journalctl -u gunicorn | grep "current week"

# If using log files
tail -100 /var/log/cfb-rankings/weekly-update.log | grep "current week"
```

**Example log output:**

```
[2025-10-20 07:41:25] INFO: Manual current week update: 7 → 8 for season 2025
[2025-10-20 07:35:10] INFO: ✓ Updated current week: 6 → 7 for season 2025
```

### Verify Processed Games

Check what games have been processed to understand why week is at a certain value:

```bash
sqlite3 cfb_rankings.db "
SELECT
    week,
    COUNT(*) as total_games,
    SUM(CASE WHEN is_processed = 1 THEN 1 ELSE 0 END) as processed_games
FROM games
WHERE season = 2025
GROUP BY week
ORDER BY week;
"
```

---

## Troubleshooting

### Problem: Week Not Updating Automatically

**Symptoms:**
- Weekly update runs but current_week doesn't change
- Week stuck at old value despite new games

**Diagnosis:**

1. Check if games are being imported:
   ```bash
   sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season=2025 AND is_processed=1;"
   ```

2. Check weekly update logs:
   ```bash
   tail -f /var/log/cfb-rankings/weekly-update.log
   ```

3. Look for validation errors:
   ```bash
   grep "validation failed" /var/log/cfb-rankings/weekly-update.log
   ```

**Solutions:**

- **If no games imported:** Check if CFBD API has the games, run `import_real_data.py` manually
- **If validation failed:** Check logs for specific error, verify week number is 0-15
- **If import script failed:** Check import logs, verify API key and connectivity

### Problem: Week Shows Incorrect Value

**Symptoms:**
- Week displays 7 but should be 8
- Week doesn't match actual current week of season

**Diagnosis:**

1. Verify actual current week:
   ```bash
   # Check max processed week in database
   sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season=2025 AND is_processed=1;"
   ```

2. Check if the expected week's games exist:
   ```bash
   sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE season=2025 AND week=8;"
   ```

**Solutions:**

- **If games don't exist:** Import them using `import_real_data.py`
- **If games exist but unprocessed:** Process them, they'll update the week
- **If immediate fix needed:** Use admin endpoint to manually set correct week

### Problem: Validation Rejecting Valid Week

**Symptoms:**
- Week 8 being rejected as invalid
- Logs show "Week validation failed"

**Diagnosis:**

Check validation logic in weekly_update.py:196:

```python
def validate_week_number(week: int, season_year: int) -> bool:
    MIN_WEEK = 0
    MAX_WEEK = 15
    # ...
```

**Solutions:**

- Verify week is actually 0-15 (not 16+)
- Check if week is an integer (not string or float)
- Review logs for specific validation error message

### Problem: Frontend Shows Old Week After Update

**Symptoms:**
- Database shows week 8
- API returns week 8
- Frontend still displays week 7

**Diagnosis:**

1. Hard refresh browser (Cmd+Shift+R or Ctrl+F5)
2. Check browser console for JavaScript errors
3. Verify API actually returns new week:
   ```bash
   curl http://your-domain.com/api/stats | jq .current_week
   ```

**Solutions:**

- Clear browser cache
- Restart frontend server if applicable
- Check frontend JavaScript is loading new data from API

---

## Code References

### Functions

- `validate_week_number()` - scripts/weekly_update.py:139-197
- `update_current_week()` - scripts/weekly_update.py:200-275
- `update_current_week_manual()` - main.py:743-797

### Database Schema

**seasons table:**
```sql
CREATE TABLE seasons (
    year INTEGER PRIMARY KEY,
    current_week INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);
```

**games table:**
```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    season INTEGER,
    week INTEGER,
    is_processed BOOLEAN DEFAULT 0,
    -- other fields...
);
```

### API Endpoints

- `GET /api/stats` - Returns current week (along with other stats)
- `POST /api/admin/update-current-week` - Manually update current week

---

## Testing

### Run Week Validation Tests

```bash
# Run all weekly update tests
pytest tests/test_weekly_update.py -v

# Run only week validation tests
pytest tests/test_weekly_update.py::TestValidateWeekNumber -v

# Run only update_current_week tests
pytest tests/test_weekly_update.py::TestUpdateCurrentWeek -v
```

### Manual Testing Checklist

- [ ] Valid week (0-15) accepted by admin endpoint
- [ ] Invalid week (-1, 16+) rejected by admin endpoint
- [ ] Non-integer week rejected by admin endpoint
- [ ] Week change logged correctly
- [ ] Frontend displays updated week
- [ ] API returns correct current_week value

---

## Common Scenarios

### Scenario 1: New Week of Games Released

**What happens:**
1. CFBD API gets new week of games (e.g., Week 8)
2. Weekly update cron job runs (Sunday evening)
3. `import_real_data.py` imports Week 8 games
4. Import script sets current_week = 8
5. `update_current_week()` redundantly confirms week = 8
6. Frontend displays "Current Week: 8"

**No manual action needed** - automatic!

### Scenario 2: Import Failed, Week Stuck

**What happens:**
1. Weekly update runs
2. Import fails due to API error
3. Week remains at old value (7)

**Manual fix:**
```bash
# Option A: Re-run import
python3 import_real_data.py

# Option B: Use admin endpoint
curl -X POST "http://your-domain.com/api/admin/update-current-week?year=2025&week=8"
```

### Scenario 3: Pre-Season (No Games Yet)

**What happens:**
1. Season created with current_week = 0
2. No games processed yet
3. Week detection returns 0
4. Frontend shows "Current Week: 0" (or "Pre-season")

**Expected behavior** - no action needed

### Scenario 4: Bowl Season (Week 15+)

**What happens:**
1. Bowl games are Week 15
2. Week detection sets current_week = 15
3. Validation accepts (15 is max valid)

**Expected behavior** - works correctly within 0-15 range

---

## Best Practices

### For System Administrators

1. **Monitor weekly updates:** Check logs after each Sunday update runs
2. **Verify week changes:** Compare database week to actual calendar week
3. **Use admin endpoint:** Prefer API over direct database updates
4. **Document manual changes:** Note why manual correction was needed

### For Developers

1. **Always validate weeks:** Use `validate_week_number()` before setting
2. **Log week changes:** Include old_week → new_week in log messages
3. **Handle errors gracefully:** Don't crash if week detection fails
4. **Test edge cases:** Week 0, Week 15, invalid weeks

### For End Users

1. **Report discrepancies:** If week looks wrong, notify admin
2. **Hard refresh:** Try Cmd+Shift+R before reporting issues
3. **Check multiple sources:** Verify against official CFB schedules

---

## Emergency Procedures

### Critical: Week Completely Wrong (Off by Multiple Weeks)

1. **Immediate Action:**
   ```bash
   curl -X POST "http://your-domain.com/api/admin/update-current-week?year=2025&week=8"
   ```

2. **Investigation:**
   - Check what games are in database
   - Review import logs for errors
   - Verify CFBD API has correct data

3. **Prevention:**
   - Run import_real_data.py weekly
   - Monitor API usage limits
   - Set up alerts for week changes

### Critical: Frontend Shows Week But Games Missing

1. **Verify games exist:**
   ```bash
   sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE season=2025 AND week=8;"
   ```

2. **If no games:**
   ```bash
   python3 import_real_data.py
   ```

3. **If games exist but unprocessed:**
   - Check ranking calculation logs
   - Verify game processing logic

---

## Changelog

**2025-10-20 - EPIC-006 Story 003**
- Added `validate_week_number()` function
- Enhanced `update_current_week()` with validation
- Created comprehensive test suite
- Documented manual correction procedures

**2025-10-20 - EPIC-006 Story 002**
- Implemented automatic week detection
- Added admin endpoint for manual updates
- Integrated week tracking into weekly_update.py

**2025-10-20 - EPIC-006 Story 001**
- Investigated week display discrepancy
- Identified root cause and solution approach
- Documented current state and recommendations

---

## Support

**Questions or Issues?**
- Check this documentation first
- Review EPIC-006 story documents
- Check GitHub issues
- Contact system administrator

**Useful Commands Reference:**

```bash
# Check current week
curl http://your-domain.com/api/stats | jq .current_week

# Manually set week
curl -X POST "http://your-domain.com/api/admin/update-current-week?year=2025&week=8"

# Check processed games
sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season=2025 AND is_processed=1;"

# View logs
tail -f /var/log/cfb-rankings/weekly-update.log

# Run import
python3 import_real_data.py

# Test validation
pytest tests/test_weekly_update.py::TestValidateWeekNumber -v
```

---

**Document Version:** 1.0
**Last Updated:** 2025-10-20
**Epic:** EPIC-006 Current Week Display Accuracy
**Story:** Story 003 - Validation and Monitoring
