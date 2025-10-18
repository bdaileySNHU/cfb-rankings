# Product Requirements Document (PRD)
## College Football Ranking System - Brownfield Analysis

---

## 1. Executive Summary

### Product Overview
The College Football Ranking System is a web-based application that provides an alternative ranking methodology for college football teams using a modified ELO algorithm. Unlike traditional polls based on human votes, this system calculates team strength using mathematical models that incorporate preseason factors (recruiting, transfers, returning production) and in-season performance adjustments.

### Business Value
- **Transparency**: Algorithm-based rankings provide clear, reproducible results
- **Real-time Updates**: Rankings update immediately as games are processed
- **Analytical Depth**: Incorporates recruiting, transfer portal, and returning production data
- **Historical Tracking**: Maintains week-by-week ranking history for trend analysis
- **Strength of Schedule**: Quantifies opponent difficulty objectively

### Target Users
- College football fans seeking analytical rankings
- Sports analysts and journalists
- Fantasy football players
- Betting analysts
- Academic researchers studying ranking systems

---

## 2. System Architecture

### Technology Stack

#### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite (production-ready for PostgreSQL migration)
- **ORM**: SQLAlchemy
- **Validation**: Pydantic schemas
- **Server**: Gunicorn with Uvicorn workers
- **API Style**: RESTful with automatic OpenAPI documentation

#### Frontend
- **Stack**: Vanilla JavaScript (ES6+), HTML5, CSS3
- **Architecture**: Multi-page application (MPA)
- **API Client**: Fetch API
- **Styling**: Custom CSS with CSS Grid and Flexbox

#### Infrastructure
- **Web Server**: Nginx (reverse proxy + static file serving)
- **SSL**: Let's Encrypt (Certbot)
- **Process Management**: systemd
- **Deployment**: VPS-based with subdomain support

#### External Integrations
- **College Football Data API**: Real game data, recruiting rankings, team information

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (SPA)                        │
│  ┌──────────┬──────────┬──────────┬──────────┬───────────┐ │
│  │Rankings  │  Teams   │  Games   │  Team    │Comparison │ │
│  │  Page    │   Page   │   Page   │  Detail  │   Page    │ │
│  └──────────┴──────────┴──────────┴──────────┴───────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS/JSON
┌─────────────────────▼───────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Endpoints (RESTful)                             │   │
│  │  - Rankings  - Teams  - Games  - Seasons  - Stats   │   │
│  └────────────────────┬─────────────────────────────────┘   │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  RankingService (Business Logic)                     │   │
│  │  - ELO Calculations  - SOS  - Preseason Ratings     │   │
│  └────────────────────┬─────────────────────────────────┘   │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  SQLAlchemy ORM                                      │   │
│  │  Team | Game | RankingHistory | Season              │   │
│  └────────────────────┬─────────────────────────────────┘   │
└─────────────────────┬─┴─────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   SQLite Database                            │
│  Tables: teams, games, ranking_history, seasons             │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Core Features (Existing)

### 3.1 Modified ELO Ranking Algorithm

**Feature Description**: Custom ELO rating system adapted for college football's unique characteristics.

**Components**:

#### Preseason Rating Calculation
Teams start each season with calculated ratings based on:

| Factor | Source | Weight | Tier Bonuses |
|--------|--------|--------|--------------|
| **Recruiting Class** | 247Sports | High | Top 5: +200, Top 10: +150, Top 25: +100, Top 50: +50, Top 75: +25 |
| **Transfer Portal** | 247Sports | Medium | Top 5: +100, Top 10: +75, Top 25: +50, Top 50: +25 |
| **Returning Production** | Data API | Medium | 80%+: +40, 60-79%: +25, 40-59%: +10 |
| **Base Rating** | Conference | N/A | FBS: 1500, FCS: 1300 |

#### In-Season Rating Updates
After each game, ratings adjust using:

```
Expected Win % = 1 / (1 + 10^((OpponentRating - TeamRating) / 400))

Rating Change = K × (Actual - Expected) × MOV × ConfMultiplier

Where:
  K = 32 (volatility factor)
  MOV = min(ln(point_diff + 1), 2.5)  // Margin of Victory capped
  ConfMultiplier = Conference-based adjustment
```

#### Modifiers

**Home Field Advantage**: +65 ELO points (applied for calculations only, not permanent)

**Conference Multipliers**:
- P5 beats G5: 0.9× (less gain for expected win)
- G5 beats P5: 1.1× (upset bonus)
- FBS beats FCS: 0.5× (minimal gain)
- FCS beats FBS: 2.0× (major upset bonus)

**Business Logic Location**: `ranking_service.py` (lines 23-234)

---

### 3.2 REST API (FastAPI)

**Feature Description**: Comprehensive RESTful API with automatic OpenAPI documentation.

#### Team Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/teams` | GET | List all teams | Paginated team list with filters |
| `/api/teams/{id}` | GET | Get team details | Full team info + rank + SOS |
| `/api/teams` | POST | Create team | New team with initialized rating |
| `/api/teams/{id}` | PUT | Update team | Updated team (recalculates rating if needed) |
| `/api/teams/{id}/schedule` | GET | Get team schedule | Season schedule with results |

**Query Parameters**:
- `conference`: Filter by P5/G5/FCS
- `skip`, `limit`: Pagination
- `season`: Year filter

**Implementation**: `main.py:59-206`

#### Game Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/games` | GET | List games | Filtered game list |
| `/api/games/{id}` | GET | Get game details | Full game info + context |
| `/api/games` | POST | Add game | Game result + rating changes |

**Query Parameters**:
- `season`, `week`: Time filters
- `team_id`: Team-specific games
- `processed`: Filter by processing status

**Key Feature**: POST to `/api/games` automatically triggers ELO rating updates for both teams.

**Implementation**: `main.py:213-283`

#### Ranking Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/rankings` | GET | Current rankings | Ranked list with SOS |
| `/api/rankings/history` | GET | Historical rankings | Week-by-week history for team |
| `/api/rankings/save` | POST | Save rankings snapshot | Saves current state to history |

**Query Parameters**:
- `limit`: Top N teams (default: 25)
- `season`: Year (defaults to active season)
- `team_id`, `season`: For history endpoint

**Implementation**: `main.py:290-346`

#### Season Management

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/seasons` | GET | List seasons | All seasons with metadata |
| `/api/seasons` | POST | Create season | New season record |
| `/api/seasons/{year}/reset` | POST | Reset season | Recalculates preseason ratings |

**Implementation**: `main.py:353-384`

#### Utility Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/stats` | GET | System statistics | Counts, current week, last update |
| `/api/calculate` | POST | Recalculate season | Reprocesses all games from scratch |
| `/` | GET | Health check | Status confirmation |

**Implementation**: `main.py:391-443`

#### API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: Auto-generated by FastAPI

---

### 3.3 Frontend Web Application

**Feature Description**: Responsive multi-page web application for viewing rankings and team data.

#### Pages

**1. Rankings Page** (`index.html`)
- **Purpose**: Display current top 25/50/all teams
- **Features**:
  - Sortable rankings table with rank badges (top 5/10/25)
  - Conference badges (P5/G5/FCS) with color coding
  - SOS indicators (elite/hard/average/easy)
  - System statistics dashboard (current week, total teams, games played)
  - Filtering by top N teams
  - Click to navigate to team detail
- **Implementation**: `frontend/index.html`, `frontend/js/app.js`

**2. Teams Page** (`teams.html`)
- **Purpose**: Browse all teams with filtering
- **Features**:
  - Grid/card layout of all teams
  - Filter by conference
  - Search by name
  - Team cards show: rank, record, rating, SOS
- **Implementation**: `frontend/teams.html`

**3. Games Page** (`games.html`)
- **Purpose**: View recent games and results
- **Features**:
  - List of games by week
  - Filter by week, season
  - Shows scores, rating changes
  - Winner/loser highlighting
- **Implementation**: `frontend/games.html`

**4. Team Detail Page** (`team.html`)
- **Purpose**: Deep dive into single team
- **Features**:
  - Team header with rank, record, rating
  - Full season schedule
  - Week-by-week ranking chart
  - Preseason factors (recruiting, transfers, production)
  - Opponent strength visualization
- **Implementation**: `frontend/team.html`, `frontend/js/team.js`

**5. Comparison Page** (`comparison.html`)
- **Purpose**: Compare ELO rankings to AP Poll
- **Features**:
  - Side-by-side comparison table
  - Difference highlighting
  - Analysis of biggest divergences
- **Implementation**: `frontend/comparison.html`, `frontend/js/comparison.js`

#### UI/UX Design Patterns
- **Color Scheme**: Dark mode-friendly with accent colors
- **Typography**: Clean, readable fonts optimized for data tables
- **Responsive**: Mobile-first design with breakpoints
- **Loading States**: Spinners for async operations
- **Error Handling**: User-friendly error messages

**Implementation**: `frontend/css/style.css`

---

### 3.4 Database Schema

**Database**: SQLite (ORM: SQLAlchemy)

#### Teams Table
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    conference ENUM('P5', 'G5', 'FCS') NOT NULL,

    -- Preseason Factors
    recruiting_rank INTEGER DEFAULT 999,
    transfer_rank INTEGER DEFAULT 999,
    returning_production FLOAT DEFAULT 0.5,

    -- Current Season Stats
    elo_rating FLOAT DEFAULT 1500.0,
    initial_rating FLOAT DEFAULT 1500.0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,

    -- Metadata
    created_at DATETIME,
    updated_at DATETIME
)
```
**Relationships**: 1-to-many with games (home/away), 1-to-many with ranking_history

**Model**: `models.py:22-52`

#### Games Table
```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY,

    -- Teams
    home_team_id INTEGER FOREIGN KEY -> teams.id,
    away_team_id INTEGER FOREIGN KEY -> teams.id,

    -- Scores
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,

    -- Game Info
    week INTEGER NOT NULL,
    season INTEGER NOT NULL,
    is_neutral_site BOOLEAN DEFAULT FALSE,
    game_date DATETIME,

    -- Processing
    is_processed BOOLEAN DEFAULT FALSE,
    home_rating_change FLOAT DEFAULT 0.0,
    away_rating_change FLOAT DEFAULT 0.0,

    -- Metadata
    created_at DATETIME
)
```
**Relationships**: Many-to-1 with teams (home_team, away_team)

**Model**: `models.py:54-100`

#### Ranking History Table
```sql
CREATE TABLE ranking_history (
    id INTEGER PRIMARY KEY,

    team_id INTEGER FOREIGN KEY -> teams.id,
    week INTEGER NOT NULL,
    season INTEGER NOT NULL,

    -- Snapshot Data
    rank INTEGER NOT NULL,
    elo_rating FLOAT NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    sos FLOAT DEFAULT 0.0,
    sos_rank INTEGER,

    -- Metadata
    created_at DATETIME
)
```
**Purpose**: Week-by-week snapshots for historical analysis

**Model**: `models.py:102-130`

#### Seasons Table
```sql
CREATE TABLE seasons (
    id INTEGER PRIMARY KEY,
    year INTEGER UNIQUE NOT NULL,
    current_week INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at DATETIME,
    updated_at DATETIME
)
```
**Purpose**: Track active season and current week

**Model**: `models.py:132-146`

---

### 3.5 Real Data Integration

**Feature Description**: Import live college football data from external API.

**Data Source**: CollegeFootballData.com API
- **Authentication**: API key (free tier available)
- **Rate Limiting**: Respects API limits
- **Data Coverage**: 2000-present

**Import Script**: `import_real_data.py`

**Capabilities**:
1. **Team Import**
   - Imports all FBS teams
   - Maps to P5/G5 conferences
   - Fetches recruiting rankings (247Sports)
   - Retrieves transfer portal rankings
   - Calculates returning production

2. **Game Import**
   - Fetches completed games by season
   - Imports scores, dates, venues
   - Identifies neutral site games
   - Processes games in chronological order

3. **Season Management**
   - Creates season records
   - Tracks current week
   - Updates week-by-week

**Client**: `cfbd_client.py`
- Clean abstraction over API
- Error handling
- Response parsing

**Usage**:
```bash
export CFBD_API_KEY='your-key-here'
python3 import_real_data.py
```

**Implementation**: `import_real_data.py`, `cfbd_client.py`

---

### 3.6 Strength of Schedule (SOS)

**Feature Description**: Calculate and rank team schedule difficulty.

**Calculation Method**:
```python
SOS = Average(opponent ELO ratings for all played games)
```

**Characteristics**:
- Updates dynamically as opponent ratings change
- Only counts processed games
- Displayed alongside rankings
- Used for SOS ranking (1 = hardest schedule)

**Visual Indicators** (Frontend):
- 🔴 Elite: SOS ≥ 1700
- 🟠 Hard: 1600 ≤ SOS < 1700
- 🟡 Average: 1500 ≤ SOS < 1600
- 🟢 Easy: SOS < 1500

**Implementation**: `ranking_service.py:237-271`

**Use Cases**:
- Contextualize team records (1-loss team with hard SOS vs undefeated with easy SOS)
- Playoff selection debates
- Conference strength comparisons

---

## 4. Data Model Details

### Entity Relationships

```
┌─────────┐              ┌──────────┐              ┌─────────┐
│ Season  │              │   Team   │              │  Game   │
├─────────┤              ├──────────┤              ├─────────┤
│ PK: id  │              │ PK: id   │◄────────────┤│ PK: id  │
│    year │              │    name  │ home_team_id│├─────────┤
│cur_week │              │    conf  │◄────────────┤│ home_id │
│is_active│              │    ...   │ away_team_id││ away_id │
└─────────┘              └────┬─────┘              │  scores │
                              │                     │  week   │
                              │                     │  season │
                              │                     └─────────┘
                              │
                              │
                              ▼
                    ┌──────────────────┐
                    │ RankingHistory   │
                    ├──────────────────┤
                    │ PK: id           │
                    │ FK: team_id      │
                    │     week, season │
                    │     rank, rating │
                    │     wins, losses │
                    │     sos, sos_rank│
                    └──────────────────┘
```

### Enum Types

**ConferenceType**:
- `P5` (Power 5): SEC, Big Ten, Big 12, ACC, Pac-12
- `G5` (Group of 5): AAC, Mountain West, Sun Belt, MAC, C-USA
- `FCS` (FCS Division I)

---

## 5. API Specification

### Request/Response Schemas (Pydantic)

All schemas defined in `schemas.py` with validation.

#### Team Schemas

**TeamCreate**:
```json
{
  "name": "Alabama",
  "conference": "P5",
  "recruiting_rank": 1,
  "transfer_rank": 5,
  "returning_production": 0.65
}
```

**Team Response**:
```json
{
  "id": 1,
  "name": "Alabama",
  "conference": "P5",
  "recruiting_rank": 1,
  "transfer_rank": 5,
  "returning_production": 0.65,
  "elo_rating": 1865.23,
  "initial_rating": 1800.00,
  "wins": 10,
  "losses": 2,
  "created_at": "2024-08-01T00:00:00Z",
  "updated_at": "2024-11-30T15:23:10Z"
}
```

**TeamDetail** (includes SOS and rank):
```json
{
  ...all Team fields...,
  "sos": 1734.56,
  "rank": 3
}
```

#### Game Schemas

**GameCreate**:
```json
{
  "home_team_id": 1,
  "away_team_id": 2,
  "home_score": 35,
  "away_score": 31,
  "week": 5,
  "season": 2024,
  "is_neutral_site": false,
  "game_date": "2024-09-28T19:00:00Z"
}
```

**GameResult** (after processing):
```json
{
  "game_id": 123,
  "winner_name": "Alabama",
  "loser_name": "Georgia",
  "score": "35-31",
  "winner_rating_change": 12.45,
  "loser_rating_change": -12.45,
  "winner_new_rating": 1877.68,
  "loser_new_rating": 1855.82,
  "winner_expected_probability": 0.523,
  "mov_multiplier": 1.48
}
```

#### Rankings Schemas

**RankingsResponse**:
```json
{
  "week": 12,
  "season": 2024,
  "total_teams": 133,
  "rankings": [
    {
      "rank": 1,
      "team_id": 1,
      "team_name": "Georgia",
      "conference": "P5",
      "elo_rating": 1889.45,
      "wins": 11,
      "losses": 1,
      "sos": 1756.23,
      "sos_rank": 2
    },
    ...
  ]
}
```

### Error Handling

**Standard Error Response**:
```json
{
  "detail": "Team not found"
}
```

**HTTP Status Codes**:
- `200 OK`: Successful GET/PUT
- `201 Created`: Successful POST
- `400 Bad Request`: Validation error, business logic violation
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server-side error

---

## 6. Business Logic

### Key Algorithms

#### 1. Preseason Rating Initialization
**Location**: `ranking_service.py:23-72`

**Process**:
1. Start with base (1500 FBS, 1300 FCS)
2. Add recruiting bonus (0-200 pts)
3. Add transfer bonus (0-100 pts)
4. Add returning production bonus (0-40 pts)
5. Set both `elo_rating` and `initial_rating` to calculated value

**Trigger**: Team creation, season reset

#### 2. Game Processing
**Location**: `ranking_service.py:143-235`

**Process**:
1. Verify game not already processed
2. Determine winner/loser
3. Apply home field advantage (+65 to home team rating for calculation)
4. Calculate expected win probabilities
5. Calculate MOV multiplier: `min(ln(point_diff + 1), 2.5)`
6. Apply conference multipliers
7. Calculate rating changes: `K × (actual - expected) × MOV × conf_mult`
8. Update team ratings and records
9. Store rating changes in game record
10. Mark game as processed
11. Commit to database

**Trigger**: POST to `/api/games`

#### 3. SOS Calculation
**Location**: `ranking_service.py:237-271`

**Process**:
1. Query all processed games for team in season
2. Extract opponent for each game
3. Sum opponent ELO ratings
4. Divide by game count
5. Return average

**Trigger**: Displayed on team detail, rankings pages

#### 4. Ranking Generation
**Location**: `ranking_service.py:273-317`

**Process**:
1. Query all teams, order by ELO descending
2. Apply limit if provided
3. For each team:
   - Calculate current rank (1-indexed)
   - Calculate SOS
   - Build ranking dict
4. Sort by SOS to assign SOS ranks
5. Return ranked list

**Trigger**: GET `/api/rankings`

#### 5. Season Reset
**Location**: `ranking_service.py:345-361`

**Process**:
1. Query all teams
2. For each team:
   - Recalculate preseason rating from factors
   - Reset `elo_rating` to preseason value
   - Reset `wins` and `losses` to 0
3. Commit changes

**Trigger**: POST `/api/seasons/{year}/reset`

---

## 7. Deployment Architecture

### Production Stack

**Web Server**: Nginx
- Reverse proxy to Gunicorn
- Serves static files (`/frontend`)
- SSL termination (Let's Encrypt)
- Compression (gzip)
- Caching headers

**Application Server**: Gunicorn
- Workers: 4 (configurable)
- Worker class: `uvicorn.workers.UvicornWorker`
- Bind: `127.0.0.1:8000`
- Timeout: 120s

**Process Manager**: systemd
- Service name: `cfb-rankings.service`
- Auto-restart on failure
- Logs to journald

**SSL**: Let's Encrypt
- Auto-renewal via certbot
- HTTP → HTTPS redirect

### Deployment Files

**Setup Script**: `deploy/setup.sh`
- Installs dependencies (Python, Nginx, Certbot)
- Creates virtual environment
- Installs Python packages
- Configures systemd service
- Sets up Nginx with SSL
- Initializes database
- Prompts for data import

**Update Script**: `deploy/deploy.sh`
- Pulls latest code from git
- Activates virtual environment
- Installs new dependencies
- Restarts Gunicorn service
- Reloads Nginx config

**Nginx Config**: `deploy/nginx.conf`
- Listens on port 80/443
- Routes `/api/*` to Gunicorn
- Serves `/` from static frontend
- Sets security headers

**Systemd Service**: `deploy/cfb-rankings.service`
- Runs as `www-data` user
- Working directory: `/var/www/cfb-rankings`
- Executes Gunicorn with config

### Environment Variables

**`.env` file**:
```
CFBD_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./cfb_rankings.db
```

**Security**: `.env` not committed to git (in `.gitignore`)

### File Structure (Production)
```
/var/www/cfb-rankings/
├── venv/                    # Python virtual environment
├── frontend/                # Static files served by Nginx
├── *.py                     # Python application files
├── cfb_rankings.db          # SQLite database
├── .env                     # Environment variables
├── gunicorn_config.py       # Gunicorn configuration
└── deploy/                  # Deployment scripts
```

---

## 8. Current Limitations & Technical Debt

### Performance
1. **SQLite Bottleneck**
   - Single-writer limitation
   - Not ideal for high concurrency
   - File-based locking

2. **No Caching**
   - Rankings recalculated on every request
   - No Redis or in-memory cache
   - Repeated SOS calculations expensive

3. **Frontend API Calls**
   - No pagination on teams page
   - Loads all teams at once
   - No lazy loading or virtualization

### Scalability
1. **Database**
   - SQLite not horizontally scalable
   - No connection pooling
   - Backup strategy unclear

2. **API Rate Limiting**
   - No rate limiting implemented
   - Vulnerable to abuse
   - No request throttling

3. **Load Balancing**
   - Single Gunicorn instance
   - No horizontal scaling
   - No CDN for static assets

### Security
1. **Authentication**
   - No user accounts
   - No authentication on POST/PUT/DELETE endpoints
   - Anyone can modify data

2. **Authorization**
   - No role-based access control
   - No API key system
   - No audit logging

3. **Input Validation**
   - Pydantic validation present but basic
   - No SQL injection protection beyond ORM
   - No XSS protection on frontend

### Code Quality
1. **Testing**
   - No unit tests
   - No integration tests
   - No CI/CD pipeline

2. **Documentation**
   - API documentation auto-generated but sparse
   - No inline code comments in complex algorithms
   - No architecture decision records

3. **Error Handling**
   - Generic error messages
   - No structured logging
   - No error tracking (Sentry, etc.)

### Features
1. **Data Management**
   - No admin interface
   - No bulk import UI
   - Manual data correction difficult

2. **Analytics**
   - No usage analytics
   - No performance monitoring
   - No dashboards for system health

3. **User Experience**
   - No search functionality
   - No team comparisons
   - No playoff predictor
   - No mobile app

---

## 9. Dependencies

### Backend Python Packages
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-dotenv==1.0.0
requests==2.31.0
gunicorn==21.2.0
```
**File**: `requirements.txt`, `requirements-prod.txt`

### External Services
1. **CollegeFootballData.com API**
   - Free tier: 100 requests/hour
   - Requires API key
   - Used for: teams, games, recruiting data

2. **Let's Encrypt**
   - Free SSL certificates
   - Auto-renewal required (certbot)

### System Dependencies (Production)
- Python 3.11+
- Nginx
- SQLite3
- Certbot
- Git

---

## 10. Data Flow Diagrams

### Game Processing Flow
```
┌──────────────┐
│ POST /games  │
└──────┬───────┘
       │
       ▼
┌────────────────────────┐
│ Validate Game Schema   │
│ (Pydantic)             │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Check Teams Exist      │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Create Game Record     │
│ (is_processed=False)   │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ RankingService         │
│ .process_game()        │
└──────┬─────────────────┘
       │
       ├─► Determine winner/loser
       ├─► Apply home field advantage (+65)
       ├─► Calculate expected win %
       ├─► Calculate MOV multiplier
       ├─► Apply conference multipliers
       ├─► Calculate rating changes
       │
       ▼
┌────────────────────────┐
│ Update Team ELO Ratings│
│ Update Win/Loss Records│
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Store Rating Changes   │
│ in Game Record         │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Mark Game as Processed │
│ Commit to Database     │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Return GameResult JSON │
└────────────────────────┘
```

### Ranking Request Flow
```
┌────────────────┐
│ GET /rankings  │
│ ?limit=25      │
└──────┬─────────┘
       │
       ▼
┌────────────────────────┐
│ Get Active Season      │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ RankingService         │
│ .get_current_rankings()│
└──────┬─────────────────┘
       │
       ├─► Query teams ORDER BY elo_rating DESC
       ├─► LIMIT 25
       │
       ▼
┌────────────────────────┐
│ For Each Team:         │
│ - Assign rank (1-N)    │
│ - Calculate SOS        │
│ - Build ranking dict   │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Calculate SOS Ranks    │
│ (Sort by SOS descending│
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Return Rankings JSON   │
└────────────────────────┘
```

---

## 11. Configuration

### Application Configuration

**FastAPI Settings** (`main.py:21-25`):
```python
app = FastAPI(
    title="College Football Ranking API",
    description="Modified ELO ranking system...",
    version="1.0.0"
)
```

**CORS Settings** (`main.py:28-34`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Gunicorn Config** (`gunicorn_config.py`):
```python
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "127.0.0.1:8000"
timeout = 120
accesslog = "/var/log/cfb-rankings/access.log"
errorlog = "/var/log/cfb-rankings/error.log"
```

### Database Configuration

**Connection** (`database.py`):
```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./cfb_rankings.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
```

### Frontend Configuration

**API Base URL** (`frontend/js/api.js`):
```javascript
const API_BASE_URL = window.location.origin;
```
Automatically uses same origin as frontend.

---

## 12. User Workflows

### Workflow 1: View Current Rankings
1. User navigates to home page (`/`)
2. Frontend loads system stats via `GET /api/stats`
3. Frontend loads rankings via `GET /api/rankings?limit=25`
4. Rankings table populates with top 25 teams
5. User can change limit dropdown (10/25/50/all)
6. User clicks team name → navigates to team detail page

### Workflow 2: View Team Details
1. User clicks team from rankings/teams page
2. Navigate to `team.html?id={team_id}`
3. Frontend loads team data via `GET /api/teams/{id}`
4. Frontend loads team schedule via `GET /api/teams/{id}/schedule?season=2024`
5. Frontend loads ranking history via `GET /api/rankings/history?team_id={id}&season=2024`
6. Page displays:
   - Team header (rank, record, rating, SOS)
   - Preseason factors
   - Full schedule with results
   - Week-by-week ranking chart

### Workflow 3: Browse All Teams
1. User clicks "All Teams" in navigation
2. Navigate to `teams.html`
3. Frontend loads teams via `GET /api/teams`
4. Teams displayed in card grid
5. User can filter by conference dropdown
6. User can search by team name
7. User clicks team card → navigate to team detail

### Workflow 4: View Games
1. User clicks "Games" in navigation
2. Navigate to `games.html`
3. Frontend loads games via `GET /api/games?season=2024`
4. Games grouped by week
5. Each game shows:
   - Teams, scores, date
   - Winner/loser
   - Rating changes
6. User can filter by week
7. User clicks game → shows game detail modal

### Workflow 5: Compare to AP Poll
1. User clicks "vs AP Poll" in navigation
2. Navigate to `comparison.html`
3. Frontend loads ELO rankings and AP Poll data
4. Side-by-side comparison table shows differences
5. Highlights biggest disagreements (e.g., ELO #5 vs AP #15)

### Workflow 6: Add Game (API Only)
1. Admin/script sends `POST /api/games` with game data
2. Backend validates request
3. Backend processes game, updates ratings
4. Returns rating changes
5. Rankings automatically updated

### Workflow 7: Reset Season (API Only)
1. Admin sends `POST /api/seasons/{year}/reset`
2. Backend recalculates all preseason ratings
3. Resets all win/loss records
4. Returns success message

---

## 13. Success Metrics (Hypothetical)

*Note: No analytics currently implemented*

### Performance Metrics
- API response time: < 200ms (p95)
- Page load time: < 2s
- Database query time: < 50ms
- Uptime: > 99.5%

### Usage Metrics
- Daily active users
- Page views per session
- Most viewed teams
- Peak traffic times (game days)

### Engagement Metrics
- Ranking page views during season
- Team detail page depth
- Return visitor rate
- Mobile vs desktop traffic

---

## 14. Future Considerations

### Short-Term Enhancements
1. **Add Authentication**
   - Admin login for POST/PUT/DELETE
   - API key system for external access

2. **Implement Caching**
   - Redis for rankings cache
   - Cache invalidation on game processing
   - Reduce database load

3. **Add Search**
   - Team name search
   - Fuzzy matching
   - Auto-suggest

4. **Mobile Optimization**
   - Touch-friendly UI
   - Responsive tables
   - Swipe gestures

### Medium-Term Enhancements
1. **PostgreSQL Migration**
   - Better concurrency
   - Production-grade
   - Connection pooling

2. **Automated Testing**
   - Unit tests for ELO algorithm
   - Integration tests for API
   - Frontend E2E tests

3. **Admin Dashboard**
   - Manage teams/games via UI
   - Bulk data import
   - System monitoring

4. **Historical Analysis**
   - Multi-season comparisons
   - Team trajectory charts
   - Conference strength trends

### Long-Term Enhancements
1. **Playoff Predictor**
   - Simulate remaining games
   - Calculate playoff probabilities
   - Monte Carlo simulations

2. **Machine Learning Integration**
   - Train on historical data
   - Predict game outcomes
   - Optimize ELO parameters

3. **Mobile Apps**
   - iOS/Android native apps
   - Push notifications for ranking changes
   - Offline mode

4. **Social Features**
   - User accounts
   - Custom rankings
   - Comments/discussions
   - Share to social media

5. **Betting Integration**
   - Point spread predictions
   - Over/under recommendations
   - Confidence ratings

---

## 15. Glossary

**ELO**: Rating system originally for chess, adapted for sports. Measures relative skill.

**SOS (Strength of Schedule)**: Average rating of opponents faced. Higher = harder schedule.

**MOV (Margin of Victory)**: Point differential in a game. Used to weight rating changes.

**K-Factor**: Volatility constant in ELO. Higher K = larger rating swings.

**P5 (Power 5)**: Top tier conferences (SEC, Big Ten, Big 12, ACC, Pac-12).

**G5 (Group of 5)**: Mid-tier FBS conferences (AAC, Mountain West, Sun Belt, MAC, C-USA).

**FCS**: Football Championship Subdivision (formerly Division I-AA).

**FBS**: Football Bowl Subdivision (formerly Division I-A).

**247Sports**: Recruiting and transfer portal data source.

**Preseason Rating**: Initial ELO rating before games, based on recruiting/transfers/production.

**Returning Production**: Percentage of previous year's stats returning to team.

**Home Field Advantage**: Temporary rating boost for home team (65 points).

**Neutral Site**: Game at neither team's home venue (e.g., bowl games).

**Conference Multiplier**: Adjustment factor based on matchup tier (P5 vs G5, etc.).

**FastAPI**: Modern Python web framework for building APIs.

**SQLAlchemy**: Python ORM (Object-Relational Mapping) library.

**Pydantic**: Data validation library using Python type hints.

**Gunicorn**: WSGI HTTP server for Python applications.

**Nginx**: Web server and reverse proxy.

---

## 16. Appendix

### File Inventory

#### Backend Python Files
- `main.py`: FastAPI application, all endpoints
- `models.py`: SQLAlchemy database models
- `schemas.py`: Pydantic request/response schemas
- `database.py`: Database connection and session management
- `ranking_service.py`: ELO algorithm and ranking business logic
- `cfb_elo_ranking.py`: Standalone ELO algorithm (used by demo)
- `cfbd_client.py`: College Football Data API client
- `import_real_data.py`: Data import script
- `seed_data.py`: Sample data generator
- `demo.py`: Standalone algorithm demonstration
- `compare_rankings.py`: Comparison tool
- `gunicorn_config.py`: Gunicorn server configuration

#### Frontend Files
- `frontend/index.html`: Rankings page
- `frontend/teams.html`: All teams page
- `frontend/games.html`: Games page
- `frontend/team.html`: Team detail page
- `frontend/comparison.html`: AP Poll comparison page
- `frontend/css/style.css`: All styles
- `frontend/js/api.js`: API client wrapper
- `frontend/js/app.js`: Rankings page logic
- `frontend/js/team.js`: Team detail page logic
- `frontend/js/comparison.js`: Comparison page logic

#### Deployment Files
- `deploy/setup.sh`: Initial VPS setup script
- `deploy/deploy.sh`: Update deployment script
- `deploy/nginx.conf`: Nginx configuration template
- `deploy/cfb-rankings.service`: Systemd service template

#### Documentation Files
- `README.md`: Quick start guide
- `PROJECT_DOCUMENTATION.md`: Comprehensive project documentation
- `QUICKSTART.md`: Fast setup instructions
- `REAL_DATA_GUIDE.md`: Real data import guide
- `DEPLOYMENT.md`: VPS deployment guide
- `BROWNFIELD_PRD.md`: This document

#### Configuration Files
- `requirements.txt`: Development Python dependencies
- `requirements-prod.txt`: Production Python dependencies
- `.env`: Environment variables (not in git)
- `.gitignore`: Git ignore rules

#### Data Files
- `cfb_rankings.db`: SQLite database (created at runtime)

### API Endpoint Summary Table

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/` | GET | Health check | No |
| `/api/teams` | GET | List teams | No |
| `/api/teams/{id}` | GET | Get team | No |
| `/api/teams` | POST | Create team | **Yes** (future) |
| `/api/teams/{id}` | PUT | Update team | **Yes** (future) |
| `/api/teams/{id}/schedule` | GET | Team schedule | No |
| `/api/games` | GET | List games | No |
| `/api/games/{id}` | GET | Get game | No |
| `/api/games` | POST | Add game | **Yes** (future) |
| `/api/rankings` | GET | Current rankings | No |
| `/api/rankings/history` | GET | Team rank history | No |
| `/api/rankings/save` | POST | Save rankings | **Yes** (future) |
| `/api/seasons` | GET | List seasons | No |
| `/api/seasons` | POST | Create season | **Yes** (future) |
| `/api/seasons/{year}/reset` | POST | Reset season | **Yes** (future) |
| `/api/stats` | GET | System stats | No |
| `/api/calculate` | POST | Recalculate season | **Yes** (future) |

---

## Document Version

**Version**: 1.0
**Date**: 2024-12-06
**Author**: Brownfield Analysis
**Status**: Complete
**Next Review**: After major feature additions

---

*This PRD provides a comprehensive snapshot of the College Football Ranking System as a brownfield project, documenting its current architecture, features, and technical implementation for future development and maintenance.*
