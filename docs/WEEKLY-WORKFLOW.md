# Weekly Workflow for College Football Rankings System

This document outlines the weekly maintenance workflow for the College Football Rankings System, including when to generate predictions and update game data.

## Overview

The system requires weekly updates during the college football season (August through January) to:
1. **Generate predictions** for upcoming games BEFORE they are played
2. **Import game results** AFTER games complete
3. **Update rankings** based on new results

**IMPORTANT:** Predictions must be generated BEFORE games are played to populate the Prediction Comparison feature.

---

## One-Time Setup: Historical Prediction Backfill

### Overview

The backfill script generates predictions for past games using the ELO ratings that existed **before each game was played**. This populates the Prediction Comparison feature with historically accurate prediction data.

**Key Concept:** The script doesn't use current ratings - it looks up what the ratings were before each game, ensuring predictions reflect what the system would have actually predicted at that time.

### When to Run

Run this script **once** when:
- Setting up the system for the first time and you have historical game data
- You notice missing predictions on the Prediction Comparison page (showing "--")
- Historical ELO ratings have been recalculated and you want updated predictions

**Note:** The script automatically skips games that already have predictions (no duplicates).

### Prerequisites

Before running backfill:
- ✓ Game data imported (`python3 import_real_data.py`)
- ✓ Rankings calculated (ELO ratings exist in database)
- ✓ Historical ratings saved in `ranking_history` table

### Quick Start

```bash
cd "/path/to/Stat-urday Synthesis"

# Step 1: Preview (always do this first)
python3 scripts/backfill_historical_predictions.py --dry-run

# Step 2: Run if preview looks correct
python3 scripts/backfill_historical_predictions.py

# Step 3: Verify
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
```

**Expected duration:** ~10 seconds for a full season (~350 games)

### What It Does

For each completed game:
1. Looks up team ELO ratings from the week **before** the game
2. Calculates win probability using historical ratings
3. Saves prediction with timestamp 2 days before game
4. Logs progress and any issues

### Expected Output

**Dry Run:**
```
================================================================================
Retrospective Prediction Backfill - DRY RUN MODE
================================================================================
Season: 2025
Found 350 processed games without predictions

Week 1: Processing 48 games...
  [DRY RUN] Would create 48 predictions

Week 2: Processing 50 games...
  [DRY RUN] Would create 50 predictions

...

Summary:
  Total games processed: 350
  Predictions that would be created: 350
  Warnings: 1
  Errors: 0

DRY RUN - No changes written to database
Run without --dry-run to commit changes
================================================================================
```

**Actual Run:**
```
================================================================================
Retrospective Prediction Backfill
================================================================================
Season: 2025
Found 350 processed games without predictions

Week 1: Processing 48 games...
  ✓ Generated 48 predictions

Week 2: Processing 50 games...
  ✓ Generated 50 predictions

...

Summary:
  Total games processed: 350
  Predictions created: 350
  Warnings: 1
  Errors: 0
  Duration: 8.3 seconds

✅ Backfill completed successfully
================================================================================
```

### Verifying Backfill Accuracy

**Check 1: Prediction Count**

Verify prediction count matches processed game count:

```bash
# Count processed games
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE is_processed = 1;"

# Count predictions
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
```

These numbers should match (or predictions may be slightly higher if some predictions existed before backfill).

**Check 2: Historical Ratings Used**

Verify predictions used historical ratings (not current ratings):

```bash
sqlite3 cfb_rankings.db "
SELECT
  g.week,
  t1.school as home_team,
  t2.school as away_team,
  p.home_elo_at_prediction,
  p.away_elo_at_prediction,
  p.win_probability
FROM predictions p
JOIN games g ON p.game_id = g.id
JOIN teams t1 ON g.home_team_id = t1.id
JOIN teams t2 ON g.away_team_id = t2.id
LIMIT 5;
"
```

**Check 3: Prediction Timestamps**

Verify predictions have realistic timestamps (2 days before game):

```bash
sqlite3 cfb_rankings.db "
SELECT
  g.game_date,
  p.created_at,
  julianday(g.game_date) - julianday(p.created_at) as days_before
FROM predictions p
JOIN games g ON p.game_id = g.id
LIMIT 5;
"
```

`days_before` should be approximately 2.0 for most games.

**Check 4: Website Display**

Visit the Prediction Comparison page to see predictions:
- Navigate to `/team/{team_id}/predictions`
- Verify all weeks show prediction data (not "--")
- Check that accuracy percentages are calculated

### Troubleshooting Backfill Issues

**Issue: "Found 0 games to process"**

Symptoms:
```
Found 0 processed games without predictions
✅ Backfill completed successfully (no work needed)
```

Causes:
1. All games already have predictions (script was already run)
2. No games in database (need to run `import_real_data.py` first)
3. No games marked as `is_processed = True`

Solutions:
```bash
# Check prediction count
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"

# Check game count
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE is_processed = 1;"
```

---

**Issue: "No historical rating found, using default 1500"**

Symptoms:
```
Week 1: Processing 48 games...
  ⚠ Team ID 42 missing historical rating for week 0, using default 1500
  ✓ Generated 48 predictions (1 warning)
```

Causes:
1. Historical ratings not saved in `ranking_history` table (expected for Week 1)
2. Team is new and has no rating history yet
3. Data import didn't populate `ranking_history`

Solutions:
- **For Week 1 games:** This is normal - Week 1 uses week 0 or default ratings
- **For other weeks:** Run data import again to populate `ranking_history`:
  ```bash
  python3 import_real_data.py
  ```
- **If persistent:** Check that ranking calculations are being saved:
  ```bash
  sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM ranking_history;"
  ```

---

**Issue: "Predictions look wrong"**

Symptoms:
- Win probabilities don't match expectations
- Predicted scores seem off
- Accuracy percentage is lower than expected

Solutions:

1. **Rollback incorrect predictions:**
   ```bash
   # Note the start/end times from backfill run log
   python3 scripts/backfill_historical_predictions.py --delete-backfilled \
     --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
   ```

2. **Verify historical ratings are correct:**
   ```bash
   sqlite3 cfb_rankings.db "
   SELECT team_id, season, week, elo_rating
   FROM ranking_history
   WHERE season = 2025 AND week = 5
   ORDER BY elo_rating DESC
   LIMIT 10;
   "
   ```

3. **Re-run backfill with dry-run to spot-check:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --dry-run --season 2025
   ```

---

**Issue: "Need to undo backfill"**

Symptoms:
- Realized historical ratings were wrong
- Want to re-run with corrected data
- Accidentally ran backfill twice

Solutions:

1. **Find timestamp range from backfill log:**
   Look for log output like:
   ```
   [2025-10-27 10:00:15] INFO: Retrospective Prediction Backfill
   ...
   [2025-10-27 10:00:23] INFO: ✅ Backfill completed successfully
   ```

2. **Run rollback command:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --delete-backfilled \
     --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:01:00"
   ```

3. **Confirm deletion:**
   Script will prompt: `Delete 350 predictions? (yes/no):`
   Type `yes` and press Enter

4. **Verify deletion:**
   ```bash
   sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
   ```

### Integration with Regular Workflow

The backfill script is **separate** from the regular weekly workflow:

**One-Time Backfill** (EPIC-017):
- Run once to populate predictions for past games
- Uses historical ratings from before each game
- Creates predictions with past timestamps

**Weekly Prediction Generation** (Existing):
- Run every Tuesday/Wednesday for upcoming games
- Uses current ratings
- Creates predictions with current timestamp

**Timeline:**
```
Setup (once):
  1. Import historical data → import_real_data.py
  2. Backfill predictions → backfill_historical_predictions.py

Weekly (ongoing):
  Tuesday: Generate predictions for upcoming games → generate_predictions.py
  Sunday: Import weekend results → weekly_update.py
```

After initial backfill, you only use the regular weekly workflow.

---

## Weekly Timeline

### Tuesday-Wednesday: Prediction Generation

**When:** Early in the week, after the previous weekend's games but BEFORE the next weekend

**Purpose:** Generate predictions for next week's games while they are still unprocessed

**Script:** `scripts/generate_predictions.py`

```bash
cd "/path/to/Stat-urday Synthesis"
python3 scripts/generate_predictions.py
```

**What it does:**
- Queries all unprocessed games for the upcoming week
- Calculates win probabilities based on current ELO ratings
- Saves predictions to database
- Predictions are preserved even after games are played

**Expected output:**
```
Generating predictions for upcoming games...
📊 Generated 52 prediction calculations
💾 Saving predictions to database...
✅ Successfully saved 52 predictions to database
```

---

### Sunday Evening: Data Import

**When:** Sunday evening or Monday morning, after weekend games complete

**Purpose:** Import completed game results and update rankings

**Script:** `scripts/weekly_update.py` (automated) or `import_real_data.py` (manual)

#### Automated (Recommended)

The system has a cron job scheduled for Sunday evenings that runs in **incremental mode** (does not reset database):

```bash
# Configured in crontab or scheduled task
# Runs incremental update - preserves all existing data and manual corrections
0 20 * * 0 cd "/path/to/Stat-urday Synthesis" && python3 scripts/weekly_update.py
```

**The automated update uses incremental mode**, which safely adds new data without resetting the database or losing manual corrections.

#### Manual

```bash
cd "/path/to/Stat-urday Synthesis"
# Incremental update (default) - preserves all existing data
python3 import_real_data.py

# OR for full reset (rarely needed - wipes all data)
python3 import_real_data.py --reset
```

**What it does (Incremental Mode - Default):**
- ✅ Fetches new completed game results from CFBD API
- ✅ Updates future games that now have scores
- ✅ Marks games as processed
- ✅ Updates team ELO ratings
- ✅ Updates season current_week
- ✅ **PRESERVES existing predictions** (does not overwrite them)
- ✅ **PRESERVES manual corrections** (like current_week adjustments)
- ✅ **PRESERVES historical data** (does not reset database)

**Note:** Incremental mode is now the default. Use `--reset` only when you need to completely rebuild the database from scratch.

---

## Complete Weekly Checklist

### Monday/Tuesday (After Games Complete)

- [ ] Run data import to get weekend results: `python3 import_real_data.py`
- [ ] Verify game results were imported correctly
- [ ] Check that rankings updated properly
- [ ] Review Prediction Comparison page to see how predictions performed

### Wednesday/Thursday (Before Next Weekend)

- [ ] Run prediction generation for next week: `python3 scripts/generate_predictions.py`
- [ ] Verify predictions were created (check count in output)
- [ ] Spot-check a few predictions on website

### Saturday (Game Day)

- [ ] No action required - predictions are already in database
- [ ] Users can view predictions on Rankings page and Prediction Comparison page

---

## API Endpoints for Manual Operations

The system also provides API endpoints for these operations:

### Generate Predictions (POST)
```
POST /api/admin/generate-predictions
```

### Trigger Weekly Update (POST)
```
POST /api/admin/trigger-update
```

### Check Update Status (GET)
```
GET /api/admin/update-status/{task_id}
```

---

## Troubleshooting

### No Predictions Generated

**Symptom:** `generate_predictions.py` returns "No upcoming games to predict"

**Causes:**
1. All games for next week are already processed (games were played)
2. No games exist in database for next week
3. Current week setting is incorrect

**Solutions:**
1. Check if games need to be imported first: `python3 import_real_data.py`
2. Verify season's `current_week` value is correct
3. Check CFBD API for available game schedules

### Predictions Missing from Website

**Symptom:** Prediction Comparison page shows "--" for some weeks

**Cause:** Predictions were not generated before games were played

**Solution:**
- For past weeks: Predictions cannot be retroactively created (by design)
- For future weeks: Run `python3 scripts/generate_predictions.py`

### Import Fails Due to API Limit

**Symptom:** `weekly_update.py` exits with "API usage at 90%"

**Solution:** This is intentional safety measure. Wait until next month when API quota resets.

---

## Prediction Comparison Feature

The Prediction Comparison page (`/team/{team_id}/predictions`) shows:

- **Prediction**: Win probability calculated BEFORE game
- **Result**: Actual game outcome
- **Accuracy**: Whether prediction was correct

**How It Works:**
1. Predictions generated Tuesday/Wednesday → Stored with `game_id`
2. Games played Saturday → Results imported Sunday
3. Games marked `is_processed = True`
4. Predictions remain in database unchanged
5. Website compares `predicted_winner_id` to actual winner

---

## Automation with Cron

### Recommended Cron Schedule

```cron
# Generate predictions every Tuesday at 10 AM
0 10 * * 2 cd /path/to/project && python3 scripts/generate_predictions.py >> logs/predictions.log 2>&1

# Import data every Sunday at 8 PM
0 20 * * 0 cd /path/to/project && python3 scripts/weekly_update.py >> logs/weekly_update.log 2>&1
```

### Setup Instructions

1. Open crontab: `crontab -e`
2. Add the schedules above (adjust paths and times as needed)
3. Save and exit
4. Verify with: `crontab -l`

---

## Database Tables Involved

### predictions
- Stores pre-game predictions
- Fields: `game_id`, `predicted_winner_id`, `win_probability`, `created_at`
- **Never modified** after creation

### games
- Stores game information and results
- Field `is_processed` indicates if game has been played
- Predictions query: `is_processed = False`
- Results query: `is_processed = True`

### seasons
- Tracks `current_week` for each season
- Used to determine which week's predictions to generate

---

## Best Practices

1. **Always generate predictions BEFORE games are played**
   - Tuesday/Wednesday is ideal timing
   - Gives buffer if script fails

2. **Monitor API usage**
   - Check `/api/admin/usage-dashboard` regularly
   - Weekly updates use ~50-100 API calls per week

3. **Keep logs**
   - Redirect script output to log files
   - Review logs after each run
   - Helps debug issues

4. **Test predictions after generation**
   - Spot-check a few games on website
   - Verify win probabilities look reasonable
   - Confirm count matches expected games

5. **Don't re-run import unnecessarily**
   - `import_real_data.py` is safe to run multiple times
   - But uses API calls each time
   - Only run if data is missing or incorrect

---

## Season Start Procedure

At the beginning of each season (August):

1. Run initial data import to get all teams and early games:
   ```bash
   python3 import_real_data.py
   ```

2. Generate predictions for Week 0/Week 1:
   ```bash
   python3 scripts/generate_predictions.py
   ```

3. Set up automated cron jobs (if not already configured)

4. Verify website is accessible and showing correct data

---

## Season End Procedure

At the end of the season (January):

1. Run final data import to get bowl games and playoff results

2. Optionally archive the season data:
   ```bash
   # Backup database
   cp cfb_rankings.db backups/cfb_rankings_2025_season.db
   ```

3. Generate final statistics and reports

4. System will automatically skip updates during off-season (February-July)

---

## Related Documentation

- **API Usage Tracking:** See `EPIC-001-API-USAGE-DASHBOARD.md`
- **Current Week Detection:** See `EPIC-006-CURRENT-WEEK-DISPLAY.md`
- **Prediction System:** See `EPIC-007-PREDICTIONS-STORAGE.md`
- **Weekly Update Script:** See `scripts/weekly_update.py`
- **Prediction Comparison:** See `EPIC-010-AP-POLL-PREDICTION-COMPARISON.md`

---

**Last Updated:** 2025-10-27
**Maintained By:** Development Team
