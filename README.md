# College Football Ranking System

A comprehensive college football ranking system using a **Modified ELO algorithm** that incorporates recruiting rankings, transfer portal activity, and returning production. Includes a REST API backend built with FastAPI.

## Features

### Modified ELO Algorithm
- **Preseason Ratings** based on:
  - 247Sports recruiting class rankings
  - Transfer portal rankings
  - Returning production percentage
- **In-Season Updates** after each game with:
  - Home field advantage (+65 points)
  - Margin of victory multiplier (capped at 2.5)
  - Conference-based multipliers (P5 vs G5, FBS vs FCS)
- **Strength of Schedule** calculations (average opponent ELO rating)

### REST API
- FastAPI backend with automatic OpenAPI documentation
- CORS support for frontend integration
- SQLite database (easily upgradable to PostgreSQL)
- Real-time ranking updates after game processing
- Historical ranking tracking by week

## 🆕 Real Data Integration

**NEW!** Import real 2024 college football data:

```bash
# Get free API key from https://collegefootballdata.com/key
export CFBD_API_KEY='your-key-here'

# Import real teams and games
python3 import_real_data.py
```

See **[REAL_DATA_GUIDE.md](REAL_DATA_GUIDE.md)** for complete instructions.

## API Usage Monitoring

The system automatically tracks all CFBD API calls to help monitor usage against the monthly limit (1000 calls/month on the free tier).

### Features
- **Automatic tracking** of every API call (endpoint, timestamp, response time)
- **Real-time usage statistics** with percentage used and remaining calls
- **Warning thresholds** at 80%, 90%, and 95% usage (logged automatically)
- **Configurable monthly limit** via environment variable
- **Top endpoint analysis** to identify which calls are most frequent

### Configuration

Add to your `.env` file:
```bash
CFBD_MONTHLY_LIMIT=1000  # Default: 1000 (free tier)
```

### Monitoring Endpoint

```bash
# Get current month's usage
curl "http://localhost:8000/api/admin/api-usage"

# Get specific month's usage
curl "http://localhost:8000/api/admin/api-usage?month=2025-01"
```

**Example Response:**
```json
{
  "month": "2025-10",
  "total_calls": 110,
  "monthly_limit": 1000,
  "percentage_used": 11.0,
  "remaining_calls": 890,
  "average_calls_per_day": 5.79,
  "warning_level": null,
  "top_endpoints": [
    {
      "endpoint": "/teams/fbs",
      "count": 105,
      "percentage": 95.5
    }
  ],
  "last_updated": "2025-10-19T23:09:46.108954"
}
```

### Warning Levels
- **80%** - WARNING logged to console
- **90%** - WARNING logged to console
- **95%** - CRITICAL logged to console

Warnings are logged once per threshold per month to prevent spam.

## Automated Weekly Updates

The system can automatically import new game data every Sunday evening during the active football season (August - January).

### Features
- **Scheduled updates** every Sunday at 8:00 PM Eastern Time
- **Active season detection** - automatically skips updates in off-season (February - July)
- **Pre-flight checks** before each update:
  - Verifies we're in active season
  - Detects current week from CFBD API
  - Checks API usage is below 90% threshold
- **Comprehensive logging** to `/var/log/cfb-rankings/weekly-update.log`
- **Graceful error handling** with automatic retries and clear error messages

### Setup (Production)

1. **Copy systemd units to system directory:**
```bash
sudo cp deploy/cfb-weekly-update.timer /etc/systemd/system/
sudo cp deploy/cfb-weekly-update.service /etc/systemd/system/
```

2. **Create log directory:**
```bash
sudo mkdir -p /var/log/cfb-rankings
sudo chown www-data:www-data /var/log/cfb-rankings
```

3. **Enable and start the timer:**
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

### Manual Testing

Run the weekly update script manually:
```bash
python3 scripts/weekly_update.py
```

Trigger the systemd service manually:
```bash
sudo systemctl start cfb-weekly-update.service
sudo journalctl -u cfb-weekly-update -f  # Watch logs in real-time
```

### Monitoring

Check recent update logs:
```bash
sudo tail -f /var/log/cfb-rankings/weekly-update.log
```

Check systemd journal:
```bash
sudo journalctl -u cfb-weekly-update -n 50
```

View next scheduled run:
```bash
systemctl list-timers cfb-weekly-update.timer
```

## Scripts

The project includes several utility scripts for data management and maintenance:

### `scripts/weekly_update.py`

**Automated weekly data import** that runs every Sunday evening to import completed game results and update rankings.

**Purpose:** Keep the system up-to-date with the latest game results during the football season.

**When to run:** Automatically via systemd timer (Sunday 8PM ET) or manually when needed.

**Usage:**
```bash
python3 scripts/weekly_update.py
```

**See:** Automated Weekly Updates section above for setup instructions.

---

### `scripts/generate_predictions.py`

**Generate predictions for upcoming games** using current ELO ratings before games are played.

**Purpose:** Create pre-game predictions for the Prediction Comparison feature.

**When to run:** Every Tuesday/Wednesday before the next weekend's games.

**Usage:**
```bash
python3 scripts/generate_predictions.py
```

**Expected output:** "✅ Successfully saved N predictions to database"

**See:** `docs/WEEKLY-WORKFLOW.md` for integration into weekly maintenance workflow.

---

### `scripts/backfill_historical_predictions.py`

**One-time setup script** that generates predictions for past games using historical ELO ratings that existed before each game was played.

**Purpose:** Populate the Prediction Comparison feature with historically accurate predictions for analysis of prediction algorithm performance.

**When to run:** Once during initial setup, or when historical predictions are missing.

**Usage:**
```bash
# Preview changes (recommended first step)
python3 scripts/backfill_historical_predictions.py --dry-run

# Run actual backfill
python3 scripts/backfill_historical_predictions.py

# Backfill specific season
python3 scripts/backfill_historical_predictions.py --season 2025

# Rollback if needed
python3 scripts/backfill_historical_predictions.py --delete-backfilled \
  --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
```

**Key features:**
- Uses historical ratings from week before each game (not current ratings)
- Automatic duplicate prevention (skips games with existing predictions)
- Dry-run mode for preview without database changes
- Rollback capability for undo operations
- Comprehensive logging and progress tracking

**See:** `docs/WEEKLY-WORKFLOW.md` "One-Time Setup: Historical Prediction Backfill" for detailed instructions and troubleshooting.

---

## Manual Update Trigger

In addition to automated weekly updates, you can manually trigger data imports via the API. This is useful for:
- Testing the update process
- Importing mid-week data after rescheduled games
- Forcing an update outside the normal schedule

### Features
- **Async execution** - Returns immediately with a task_id, update runs in background
- **Pre-flight checks** - Same validation as automated updates:
  - Active season check (August - January)
  - Current week detection from CFBD API
  - API usage threshold check (aborts if >= 90% used)
- **Status tracking** - Poll task status to monitor progress
- **Comprehensive results** - Returns games imported, teams updated, errors
- **Admin dashboard** - View usage statistics and projections

### Usage

**1. Trigger an update:**
```bash
curl -X POST "http://localhost:8000/api/admin/trigger-update"
```

Returns a `task_id` immediately.

**2. Check status:**
```bash
curl "http://localhost:8000/api/admin/update-status/{task_id}"
```

Poll this endpoint until `status` is `completed` or `failed`.

**3. Monitor API usage:**
```bash
curl "http://localhost:8000/api/admin/usage-dashboard"
```

See current month usage, projections, and daily breakdown.

### Error Scenarios

**Off-season (February - July):**
```json
{
  "detail": "Cannot update during off-season (Feb-July)"
}
```

**No current week:**
```json
{
  "detail": "No current week found - season may not be active"
}
```

**API usage too high (>= 90%):**
```json
{
  "detail": "API usage at 92.5% - aborting to prevent quota exhaustion"
}
```

All endpoints are documented in the interactive API docs at `http://localhost:8000/docs`.

## Project Structure

```
.
├── cfb_elo_ranking.py    # Core ELO ranking algorithm (standalone)
├── main.py               # FastAPI application with all endpoints
├── cfbd_client.py        # CollegeFootballData API client
├── import_real_data.py   # Import real teams & games
├── models.py             # SQLAlchemy database models
├── schemas.py            # Pydantic schemas for API validation
├── database.py           # Database configuration
├── ranking_service.py    # Service layer integrating ELO with database
├── seed_data.py          # Sample data population script
├── demo.py               # Standalone demo of ranking algorithm
├── requirements.txt      # Python dependencies
├── requirements-dev.txt  # Development & testing dependencies
├── Makefile              # Convenient test commands
├── cfb_rankings.db       # SQLite database (created on first run)
├── scripts/              # Utility and maintenance scripts
│   ├── weekly_update.py  # Automated weekly data import
│   ├── generate_predictions.py  # Generate predictions for upcoming games
│   └── backfill_historical_predictions.py  # One-time historical prediction backfill
└── tests/                # Comprehensive test suite
    ├── unit/             # Unit tests (149 tests)
    ├── integration/      # Integration tests (87 tests)
    └── e2e/              # End-to-end tests (21 tests)
```

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
Create a `.env` file (see `.env.example`):
```bash
CFBD_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./cfb_rankings.db
CFBD_MONTHLY_LIMIT=1000
```

3. **Initialize database with sample data:**
```bash
python3 seed_data.py
```

This creates 33 teams and 25 games from 2 weeks of a sample season.

## Usage

### Start the API Server

```bash
python3 main.py
```

The server will start at `http://localhost:8000`

### Interactive API Documentation

FastAPI automatically generates interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Test the Standalone Algorithm

```bash
python3 demo.py
```

This runs a simulation showing how the ranking algorithm works without the API.

## Testing

![Tests](https://github.com/anthropics/claude-code/actions/workflows/tests.yml/badge.svg)

### Comprehensive Test Suite

**124 tests** covering all critical functionality with automated CI/CD testing:

- **78 unit/integration tests** - API endpoints, business logic, data import scripts
- **46 E2E tests** - Complete user workflows with browser automation

### Quick Start

```bash
# Run all tests (unit + integration, skips E2E by default)
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# View coverage in browser
open htmlcov/index.html
```

### Running Specific Test Categories

```bash
# Run only unit tests (fastest)
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run E2E tests (requires browser)
pytest -m e2e -v

# Skip E2E tests for quick iteration
pytest -m "not e2e" -v

# Run specific test file
pytest tests/test_ranking_service.py -v
```

### Test Coverage by Module

**Unit/Integration Tests (78 tests):**
- `test_update_games.py` (10 tests) - Game import script validation
- `test_cfbd_client.py` (19 tests) - API client and field naming
- `test_ranking_service.py` (19 tests) - Predictions and ranking logic
- `test_api_endpoints.py` (30 tests) - FastAPI endpoint validation

**End-to-End Tests (46 tests):**
- `test_rankings_page.py` (11 tests) - Rankings page workflow
- `test_team_detail.py` (10 tests) - Team detail page workflow
- `test_predictions_workflow.py` (12 tests) - Predictions page workflow
- `test_comparison_page.py` (13 tests) - AP Poll comparison workflow

### Documentation

📖 **[docs/TESTING.md](docs/TESTING.md)** - Complete testing guide with:
- Test organization and structure
- How to write new tests
- Mocking strategies
- Test fixtures documentation
- Best practices

📖 **[docs/CI-CD-PIPELINE.md](docs/CI-CD-PIPELINE.md)** - CI/CD pipeline documentation with:
- GitHub Actions workflow explanation
- How to view test results
- Troubleshooting guide
- Performance optimization tips

### CI/CD Integration

Tests run automatically in GitHub Actions on:
- ✅ Every push to `main` or `develop` branches
- ✅ Every pull request
- ✅ Manual workflow dispatch

**Workflow:**
1. Unit + Integration tests (~1.5 min)
2. E2E tests with headless browser (~2.5 min)
3. Coverage reports uploaded to artifacts

See [docs/CI-CD-PIPELINE.md](docs/CI-CD-PIPELINE.md) for detailed workflow documentation.

## 🎯 Game Predictions (NEW!)

**NEW!** Predict upcoming game outcomes using ELO-based win probability and score estimation.

### Features
- **Data-driven predictions** using Modified ELO ratings
- **Win probability percentages** for each matchup
- **Score estimates** based on rating difference
- **Confidence levels** (High/Medium/Low)
- **Prediction accuracy tracking** with historical comparison
- **AP Poll comparison** to validate ELO system performance

### Quick Start

```bash
# Get next week's predictions
curl "http://localhost:8000/api/predictions?next_week=true"

# Get predictions for specific week
curl "http://localhost:8000/api/predictions?week=8"

# Get predictions for specific team
curl "http://localhost:8000/api/predictions?team_id=1"

# Get prediction accuracy stats
curl "http://localhost:8000/api/predictions/accuracy"

# Compare ELO vs AP Poll predictions
curl "http://localhost:8000/api/predictions/comparison"
```

### Example Prediction Response

```json
{
  "game_id": 123,
  "home_team": "Georgia",
  "away_team": "Alabama",
  "week": 8,
  "season": 2025,
  "predicted_winner": "Georgia",
  "predicted_home_score": 31,
  "predicted_away_score": 24,
  "home_win_probability": 68.5,
  "away_win_probability": 31.5,
  "confidence": "Medium"
}
```

### How It Works

**Win Probability:**
```
P(home wins) = 1 / (1 + 10^((away_rating - home_rating) / 400))
```

**Score Estimation:**
- Base score: 30 points per team (historical average)
- Adjustment: ±3.5 points per 100 rating difference
- Home field advantage: +65 rating points

**Confidence Determination:**
- **High:** Win probability > 80% or < 20%
- **Medium:** Win probability 65-80% or 20-35%
- **Low:** Win probability 35-65% (close matchup)

### Prediction Accuracy

The system automatically tracks predictions and evaluates accuracy after games complete:

- **Stored predictions:** 9 tracked predictions
- **Accuracy metrics:** Winner prediction success rate
- **Team-specific accuracy:** View accuracy for individual teams
- **AP Poll comparison:** See how ELO predictions compare to AP Poll rankings

📖 See **[docs/PREDICTIONS.md](docs/PREDICTIONS.md)** for complete prediction methodology.

## API Endpoints

### Predictions 🆕
- `GET /api/predictions` - Get game predictions for upcoming games
  - Query params: `next_week` (bool), `week` (0-15), `team_id`, `season`
- `GET /api/predictions/accuracy` - Get overall prediction accuracy statistics
- `GET /api/predictions/accuracy/team/{team_id}` - Get team-specific accuracy
- `GET /api/predictions/stored` - Get all stored predictions
- `GET /api/predictions/comparison` - Compare ELO vs AP Poll accuracy
  - Query params: `season`

### Rankings
- `GET /api/rankings` - Get current rankings (top 25 by default)
  - Query params: `season`, `limit`
- `GET /api/rankings/history?team_id={id}&season={year}` - Get historical rankings for a team
- `POST /api/rankings/save` - Save current rankings to history

### Teams
- `GET /api/teams` - Get all teams
  - Query params: `conference`, `skip`, `limit`
- `GET /api/teams/{id}` - Get team details with current rank and SOS
- `POST /api/teams` - Create a new team
- `PUT /api/teams/{id}` - Update team information
- `GET /api/teams/{id}/schedule?season={year}` - Get team's schedule

### Games
- `GET /api/games` - Get games with optional filters
  - Query params: `season`, `week`, `team_id`, `processed`
- `GET /api/games/{id}` - Get game details
- `POST /api/games` - Add a game (automatically processes and updates rankings)

### Seasons
- `GET /api/seasons` - Get all seasons
- `POST /api/seasons` - Create a new season
- `POST /api/seasons/{year}/reset` - Reset season (recalculates all preseason ratings)

### Utility
- `GET /api/stats` - Get system statistics
- `POST /api/calculate?season={year}` - Recalculate all rankings from scratch
- `GET /` - Health check

### Admin
- `GET /api/admin/api-usage` - Get CFBD API usage statistics
  - Query params: `month` (optional, format: YYYY-MM)
- `POST /api/admin/trigger-update` - Manually trigger a weekly data update
- `GET /api/admin/update-status/{task_id}` - Get status of an update task
- `GET /api/admin/usage-dashboard` - Get comprehensive usage dashboard
  - Query params: `month` (optional, format: YYYY-MM)
- `GET /api/admin/config` - Get system configuration
- `PUT /api/admin/config` - Update system configuration

## Example API Calls

### Get Top 10 Rankings
```bash
curl "http://localhost:8000/api/rankings?limit=10"
```

### Get Team Details
```bash
curl "http://localhost:8000/api/teams/1"
```

### Add a New Game (updates rankings immediately)
```bash
curl -X POST "http://localhost:8000/api/games" \
  -H "Content-Type: application/json" \
  -d '{
    "home_team_id": 1,
    "away_team_id": 2,
    "home_score": 35,
    "away_score": 28,
    "week": 3,
    "season": 2024,
    "is_neutral_site": false
  }'
```

### Get Team Schedule
```bash
curl "http://localhost:8000/api/teams/1/schedule?season=2024"
```

### Manual Update Trigger
```bash
# Trigger a manual data update
curl -X POST "http://localhost:8000/api/admin/trigger-update"
```

**Example Response:**
```json
{
  "status": "started",
  "message": "Update started successfully",
  "task_id": "update-20251019-140523",
  "started_at": "2025-10-19T14:05:23.456789"
}
```

### Check Update Status
```bash
# Poll the status using the task_id from trigger response
curl "http://localhost:8000/api/admin/update-status/update-20251019-140523"
```

**Example Response (in progress):**
```json
{
  "task_id": "update-20251019-140523",
  "status": "running",
  "trigger_type": "manual",
  "started_at": "2025-10-19T14:05:23.456789",
  "completed_at": null,
  "duration_seconds": null,
  "result": null
}
```

**Example Response (completed):**
```json
{
  "task_id": "update-20251019-140523",
  "status": "completed",
  "trigger_type": "manual",
  "started_at": "2025-10-19T14:05:23.456789",
  "completed_at": "2025-10-19T14:08:45.123456",
  "duration_seconds": 201.67,
  "result": {
    "success": true,
    "games_imported": 45,
    "teams_updated": 133,
    "error_message": null
  }
}
```

### Get Usage Dashboard
```bash
# Get comprehensive usage dashboard with projections
curl "http://localhost:8000/api/admin/usage-dashboard"
```

**Example Response:**
```json
{
  "current_month": {
    "month": "2025-10",
    "total_calls": 245,
    "monthly_limit": 1000,
    "percentage_used": 24.5,
    "remaining_calls": 755,
    "average_calls_per_day": 12.89,
    "warning_level": null,
    "days_until_reset": 12,
    "projected_end_of_month": 399
  },
  "top_endpoints": [
    {"endpoint": "/games", "count": 120, "percentage": 48.98},
    {"endpoint": "/teams/fbs", "count": 105, "percentage": 42.86},
    {"endpoint": "/calendar", "count": 20, "percentage": 8.16}
  ],
  "daily_usage": [
    {"date": "2025-10-01", "calls": 15},
    {"date": "2025-10-02", "calls": 18},
    {"date": "2025-10-03", "calls": 12}
  ],
  "last_update": "2025-10-19T14:10:00.000000"
}
```

### Update System Configuration
```bash
# Update monthly API limit (e.g., after upgrading to paid plan)
curl -X PUT "http://localhost:8000/api/admin/config" \
  -H "Content-Type: application/json" \
  -d '{"cfbd_monthly_limit": 5000}'
```

**Example Response:**
```json
{
  "cfbd_monthly_limit": 5000,
  "update_schedule": "Sun 20:00 ET",
  "api_usage_warning_thresholds": [80, 90, 95],
  "active_season_start": "08-01",
  "active_season_end": "01-31"
}
```

## Algorithm Details

### Preseason Rating Formula
```
Preseason Rating = Base + Recruiting Bonus + Transfer Bonus + Returning Bonus

Base:
  FBS: 1500
  FCS: 1300

Recruiting Bonus (247Sports):
  Top 5:  +200
  Top 10: +150
  Top 25: +100
  Top 50: +50
  Top 75: +25

Transfer Portal Bonus:
  Top 5:  +100
  Top 10: +75
  Top 25: +50
  Top 50: +25

Returning Production Bonus:
  80%+:   +40
  60-79%: +25
  40-59%: +10
```

### In-Season ELO Calculation
```
Expected Win Probability = 1 / (1 + 10^((Opponent_Rating - Team_Rating) / 400))

Rating Change = K × (Actual - Expected) × MOV_Multiplier × Conference_Multiplier

Where:
  K = 32 (volatility factor)
  MOV_Multiplier = min(ln(point_diff + 1), 2.5)

Conference Multipliers:
  P5 beats G5: 0.9× (less gain)
  G5 beats P5: 1.1× (upset bonus)
  FBS beats FCS: 0.5× (minimal gain)
  FCS beats FBS: 2.0× (major upset bonus)
```

### Home Field Advantage
- +65 rating points added to home team for calculation only
- Not applied to permanent rating
- Neutral site games ignore this modifier

## Sample Output

After running `seed_data.py`, you'll see rankings like:

```
RANK   TEAM                      RATING     RECORD     CONF   SOS
--------------------------------------------------------------------------------
1      Georgia                   1869.03    2-0        P5     1725.09
2      Ohio State                1850.39    2-0        P5     1649.56
3      Alabama                   1798.92    1-1        P5     1734.07
4      Notre Dame                1772.25    2-0        P5     1648.35
5      Miami                     1747.64    2-0        P5     1658.19
```

Note how Alabama at 1-1 ranks #3 due to:
- High preseason rating (elite recruiting)
- Strong schedule (SOS: 1734.07 - 3rd hardest)
- Loss to #1 Georgia (minimal rating penalty)

## Next Steps

### Frontend Development
To build a web interface, you could use:
- **React/Next.js** for modern SPA
- **Vue.js** for lightweight frontend
- **Vanilla HTML/CSS/JS** for simplicity

The API supports CORS and is ready for frontend integration.

### Production Deployment
- Replace SQLite with PostgreSQL
- Add authentication/authorization
- Deploy backend to Railway/Render/AWS
- Deploy frontend to Vercel/Netlify

### Data Integration
- Integrate with CollegeFootballData API
- Automate weekly game updates
- Pull live recruiting rankings from 247Sports

## License

MIT

## Contributing

Pull requests welcome! Key areas for improvement:
- Frontend web interface
- Additional ranking algorithms (for comparison)
- Playoff probability calculations
- Head-to-head record tracking
- Conference championship predictions
