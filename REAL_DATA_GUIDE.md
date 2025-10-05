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
python3 import_real_data.py
```

The script will:
1. Ask you to confirm (it will reset your database)
2. Ask how many weeks of games to import
3. Fetch all FBS teams (~130 teams)
4. Import games with real scores
5. Calculate ELO ratings based on actual results
6. Display the final rankings

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

### Add New Week's Games

Once you've imported data, you can update weekly:

```bash
# Just import the latest week
python3 update_games.py --week 6
```

Or use the API directly:
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
