# Real Data Integration Guide

This guide shows you how to populate your ranking system with **real 2024 college football data**.

## Quick Start (5 Minutes)

### Step 1: Get a Free API Key

1. Visit **https://collegefootballdata.com/key**
2. Click "Request a Key"
3. Fill out the form (it's free!)
4. You'll receive an API key via email

### Step 2: Set Your API Key

```bash
# Mac/Linux
export CFBD_API_KEY='your-api-key-here'

# Windows PowerShell
$env:CFBD_API_KEY='your-api-key-here'

# Or add to your ~/.bashrc or ~/.zshrc for permanent setup:
echo 'export CFBD_API_KEY="your-key-here"' >> ~/.zshrc
```

### Step 3: Run the Import Script

```bash
# Incremental update (default) - adds new data without resetting database
python3 import_real_data.py

# Full reset - wipe database and reimport everything (first time setup)
python3 import_real_data.py --reset
```

**Incremental Mode (Default):**
- Imports new games and updates existing games
- Preserves manual corrections (like current week adjustments)
- Reuses existing teams and season data
- Safe for weekly updates

**Reset Mode (--reset flag):**
- Wipes the entire database and starts fresh
- Use for first-time setup or when you need a clean slate
- Asks for confirmation before resetting
- Rebuilds everything from scratch

The script will:
1. Auto-detect the current season and week
2. Fetch all FBS teams (~130 teams)
3. Import games with real scores (incremental or full)
4. Calculate ELO ratings based on actual results
5. Display the final rankings

**Example Output:**
```
How many weeks of games would you like to import?
(The 2024 season has games through Week 15+)
Enter max week (1-15): 5

Importing FBS teams for 2024...
Fetching recruiting rankings...
Fetching talent composite...
Fetching returning production...
  Added: Alabama (P5) - Recruiting: #5, Returning: 65%
  Added: Georgia (P5) - Recruiting: #1, Returning: 70%
  ...

✓ Imported 133 teams

Importing games for 2024...

Week 1...
    Georgia defeats Clemson 34-3
    Alabama defeats Middle Tennessee 56-7
    ...
  Imported 47 games for week 1

...

FINAL RANKINGS
================================================================================
RANK   TEAM                           RATING     RECORD     SOS
--------------------------------------------------------------------------------
1      Georgia                        1892.45    5-0        1742.18
2      Texas                          1871.23    5-0        1698.45
3      Ohio State                     1865.90    5-0        1655.32
...
```

## What You Get

### Real Teams
- **~133 FBS teams** from all conferences
- **Actual recruiting rankings** from 247Sports composite
- **Real returning production** percentages
- **Proper conference assignments** (SEC, Big Ten, etc.)

### Real Games
- **Actual game results** from the 2024 season
- **Real scores** for accurate ELO calculations
- **Neutral site indicators**
- **All games through the week you specify**

### Real Rankings
- Rankings based on **actual on-field performance**
- Strength of schedule from **real opponents**
- See how your ELO rankings compare to:
  - AP Poll
  - Coaches Poll
  - CFP Rankings

## API Rate Limits

The free tier includes:
- ✅ **1000 API calls per month**
- ✅ Unlimited data access
- ✅ All historical data

**Typical Usage:**
- Importing 5 weeks: ~10 API calls
- Full season (15 weeks): ~20 API calls
- Plenty of room for updates!

## Updating Your Rankings

### Weekly Updates (Recommended)

The best way to update weekly is to use **incremental mode** (default):

```bash
# Simply run the import script - it will add new data without resetting
python3 import_real_data.py

# Or specify a max week to import through
python3 import_real_data.py --max-week 10
```

**What incremental updates do:**
- ✅ Import new games for the latest week
- ✅ Update future games that now have scores
- ✅ Preserve your manual corrections (like current week adjustments)
- ✅ Keep all historical data and rankings
- ✅ Much faster than full reset

### Manual Game Entry (Alternative)

Or use the API directly to add individual games:
```bash
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{
    "home_team_id": 1,
    "away_team_id": 2,
    "home_score": 35,
    "away_score": 28,
    "week": 6,
    "season": 2024
  }'
```

### When to Use Reset Mode

Only use `--reset` when you need to:
- Start completely fresh with a clean database
- Fix major data corruption issues
- Switch to a different season

**Warning:** Reset mode wipes all data including manual corrections!

## Data Sources

### CollegeFootballData.com API Provides:

1. **Teams**
   - All FBS teams
   - Conference affiliations
   - Team metadata

2. **Games**
   - Real game results
   - Scores
   - Dates
   - Neutral site info

3. **Recruiting**
   - 247Sports composite rankings
   - Team talent ratings
   - Transfer portal data (limited)

4. **Advanced Stats**
   - Returning production percentages
   - SP+ ratings
   - Win probability
   - And much more!

## Customization

### Import Specific Weeks

Edit `import_real_data.py` to import specific weeks:
```python
# Import only weeks 1-3
import_games(cfbd, db, team_objects, year=2024, max_week=3)
```

### Filter by Conference

Edit the import script to only import certain conferences:
```python
# Only import SEC teams
if team_data.get('conference') == 'SEC':
    # ... create team
```

### Adjust Preseason Factors

The script uses real data, but you can adjust weights in `ranking_service.py`:
```python
# Give more weight to recruiting
if self.recruiting_rank <= 5:
    recruiting_bonus = 300.0  # Instead of 200.0
```

## Comparing with Official Rankings

After importing, compare your ELO rankings with:

### AP Poll
- Check https://apnews.com/hub/ap-top-25-college-football-poll

### CFP Rankings
- Check https://www.collegefootballplayoff.com/rankings

### Interesting Insights
Your ELO rankings might reveal:
- **Overrated teams**: High ranking but weak schedule
- **Underrated teams**: Strong performance, tough schedule
- **Quality losses**: Teams with good ELO despite losses

## Troubleshooting

### "API Error: 401 Unauthorized"
- Your API key is missing or invalid
- Make sure you've set `CFBD_API_KEY` environment variable
- Check the key hasn't expired

### "Failed to fetch teams"
- Check your internet connection
- Verify API key is correct
- CFBD might be down (rare)

### "No games found for week X"
- Week hasn't been played yet
- Games haven't been finalized
- Try a lower week number

### "Team not in database"
- Some FCS teams play FBS teams but aren't imported
- The script only imports FBS teams to keep rankings relevant
- You can modify to include FCS if desired

### Database Corruption or Data Issues

If you encounter data corruption or incorrect data that can't be fixed incrementally:

**Option 1: Easy Reset (Recommended)**
```bash
./scripts/reset_and_import.sh
```
This wrapper script:
- Shows a clear warning about data loss
- Asks for confirmation
- Runs the full reset safely

**Option 2: Direct Reset**
```bash
python3 import_real_data.py --reset
```

**Warning:** Reset mode deletes ALL data including:
- All games and results
- All team data and ELO ratings
- All predictions and accuracy data
- All ranking history
- Manual corrections (like current_week adjustments)

Only use reset when absolutely necessary. For most updates, use incremental mode (default).

### Incremental Update Not Working

If incremental updates aren't importing new data:

1. **Check if games exist:** Verify games are available on CFBD for that week
2. **Check current week:** Use `python3 scripts/fix_current_week.py --year 2024 --week X`
3. **Check API usage:** Make sure you haven't hit the monthly limit
4. **Try with specific week:** `python3 import_real_data.py --max-week 10`

If problems persist, the upsert logic should handle duplicate games gracefully.

## Advanced: Automated Updates

### Set up a weekly cron job:

```bash
# Edit crontab
crontab -e

# Add this line to run every Monday at 9 AM
0 9 * * 1 cd /path/to/project && /usr/bin/python3 update_games.py
```

### Create `update_games.py`:
```python
# Automatically fetch and import the latest week's games
# Similar to import_real_data.py but only new games
```

## Production Deployment

### Running Commands on Production Server

**IMPORTANT:** On production servers (e.g., /var/www/cfb-rankings), always run Python scripts as the web server user to ensure proper file permissions:

```bash
# Navigate to project directory
cd /var/www/cfb-rankings

# Pull latest code updates
git pull

# Run import as www-data user (incremental mode - default)
sudo -u www-data /var/www/cfb-rankings/venv/bin/python /var/www/cfb-rankings/import_real_data.py

# OR full reset (rarely needed - wipes all data)
sudo -u www-data /var/www/cfb-rankings/venv/bin/python /var/www/cfb-rankings/import_real_data.py --reset

# Check database status
sudo -u www-data /var/www/cfb-rankings/venv/bin/python /var/www/cfb-rankings/scripts/check_database_status.py

# Check API data for current week
sudo -u www-data /var/www/cfb-rankings/venv/bin/python /var/www/cfb-rankings/scripts/check_week11_api.py
```

### Why `sudo -u www-data`?

Running scripts as the web server user ensures:
- **Proper ownership**: Database and log files are owned by www-data
- **No permission errors**: Web application can read/write database
- **Security**: Follows principle of least privilege
- **Consistency**: All files have consistent ownership

### Common Production Commands

**Check systemd timer status:**
```bash
systemctl list-timers cfb-weekly-update.timer
systemctl status cfb-weekly-update.service
journalctl -u cfb-weekly-update.service -n 50
```

**Manually trigger weekly update:**
```bash
sudo systemctl start cfb-weekly-update.service
```

**Install dependencies:**
```bash
# If you get "ModuleNotFoundError", install missing packages:
sudo /var/www/cfb-rankings/venv/bin/pip install -r /var/www/cfb-rankings/requirements.txt
```

**View recent logs:**
```bash
tail -f /var/www/cfb-rankings/logs/weekly_update.log
```

### Environment Variables on Production

**Set API key for www-data user:**
```bash
# Add to /etc/environment (system-wide)
echo 'CFBD_API_KEY="your-key-here"' | sudo tee -a /etc/environment

# OR add to systemd service file:
# Edit /etc/systemd/system/cfb-weekly-update.service
# Add under [Service]:
# Environment="CFBD_API_KEY=your-key-here"
```

**Verify environment:**
```bash
sudo -u www-data env | grep CFBD
```

## What's Next?

With real data imported:

1. **Analyze trends**: How does your ELO track with polls?
2. **Test predictions**: Use ELO to predict upcoming games
3. **Historical analysis**: Import past seasons for comparison
4. **Playoff predictions**: Calculate playoff probability
5. **Share your rankings**: Deploy to the web!

## API Documentation

Full API docs: https://api.collegefootballdata.com/api/docs/

Popular endpoints:
- `/teams/fbs` - All FBS teams
- `/games` - Game results
- `/recruiting/teams` - Recruiting rankings
- `/player/returning` - Returning production
- `/rankings` - Official poll rankings (for comparison)

## Support

- API Issues: https://github.com/CFBD/cfbd-api
- CFBD Discord: https://discord.gg/cfbdata
- This Project: See README.md

---

**Ready to see real rankings?** Get your API key and run the import! 🏈
