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
└── cfb_rankings.db       # SQLite database (created on first run)
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

2. **Initialize database with sample data:**
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

## API Endpoints

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
