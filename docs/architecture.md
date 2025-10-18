# College Football Ranking System - Brownfield Architecture Document

## Introduction

This document captures the **CURRENT STATE** of the College Football Ranking System codebase. It serves as a comprehensive reference for AI agents and developers working on enhancements, documenting the actual implementation, technical patterns, constraints, and known technical debt.

### Document Scope

This document provides comprehensive documentation of the entire system, covering backend services, frontend application, database architecture, algorithms, deployment configuration, and integration points.

### Change Log

| Date       | Version | Description                 | Author   |
|------------|---------|----------------------------|----------|
| 2025-10-06 | 1.0     | Initial brownfield analysis | Winston  |

---

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

**Backend Core:**
- **Main API Application**: `main.py` - All FastAPI endpoints and application initialization
- **Ranking Engine**: `ranking_service.py` - Modified ELO algorithm implementation and business logic
- **Database Models**: `models.py` - SQLAlchemy ORM models for Team, Game, RankingHistory, Season
- **API Schemas**: `schemas.py` - Pydantic validation models for request/response
- **Database Connection**: `database.py` - SQLAlchemy engine and session management

**Data Integration:**
- **API Client**: `cfbd_client.py` - College Football Data API integration client
- **Data Import**: `import_real_data.py` - Script to populate database with real game data
- **Sample Data**: `seed_data.py` - Development data generator

**Frontend:**
- **Rankings Page**: `frontend/index.html` + `frontend/js/app.js`
- **Team Detail Page**: `frontend/team.html` + `frontend/js/team.js`
- **Teams Browser**: `frontend/teams.html`
- **Games List**: `frontend/games.html`
- **AP Comparison**: `frontend/comparison.html` + `frontend/js/comparison.js`
- **API Client**: `frontend/js/api.js` - Frontend API wrapper
- **Styles**: `frontend/css/style.css` - All CSS styling

**Deployment:**
- **Gunicorn Config**: `gunicorn_config.py` - Production server settings (4 workers, uvicorn worker class)
- **Setup Script**: `deploy/setup.sh` - Initial VPS deployment automation
- **Update Script**: `deploy/deploy.sh` - Git pull and restart workflow
- **Nginx Config**: `deploy/nginx.conf` - Reverse proxy and static file serving
- **Systemd Service**: `deploy/cfb-rankings.service` - Process management

**Configuration:**
- **Dependencies**: `requirements.txt` - Python packages (FastAPI, SQLAlchemy, Pydantic, etc.)
- **Environment**: `.env` (not in git) - CFBD_API_KEY, DATABASE_URL

---

## High Level Architecture

### System Context

The College Football Ranking System is a full-stack web application that calculates and displays alternative rankings for college football teams using a modified ELO algorithm. The system integrates real game data, preseason metrics (recruiting, transfers, returning production), and provides a REST API with a responsive frontend.

```
┌─────────────────────────────────────────────────────────────┐
│                   External Dependencies                      │
│  ┌──────────────────────────┐  ┌────────────────────────┐  │
│  │ CollegeFootballData API  │  │  Let's Encrypt (SSL)   │  │
│  │ - Game data              │  │  - TLS certificates    │  │
│  │ - Recruiting rankings    │  │  - Auto-renewal        │  │
│  │ - Team information       │  │                        │  │
│  └──────────────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │                           │
                      └───────────┬───────────────┘
                                  │ HTTPS
┌─────────────────────────────────▼───────────────────────────┐
│                         Nginx (Web Server)                   │
│  ┌────────────────────┬────────────────────────────────┐    │
│  │ Static File Server │  Reverse Proxy to Gunicorn     │    │
│  │ /frontend/*        │  /api/*                        │    │
│  └────────────────────┴────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost:8000)
┌──────────────────────────▼──────────────────────────────────┐
│                  Gunicorn + Uvicorn Workers                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Application (main.py)                       │   │
│  │  - REST API endpoints                                │   │
│  │  - Pydantic validation                               │   │
│  │  - Dependency injection (DB sessions)                │   │
│  └────────────────────┬─────────────────────────────────┘   │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  RankingService (ranking_service.py)                 │   │
│  │  - Modified ELO algorithm                            │   │
│  │  - Preseason rating calculation                      │   │
│  │  - Game processing and rating updates                │   │
│  │  - Strength of Schedule (SOS) calculation            │   │
│  └────────────────────┬─────────────────────────────────┘   │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  SQLAlchemy ORM (models.py)                          │   │
│  │  - Team, Game, RankingHistory, Season models         │   │
│  │  - Relationships and constraints                     │   │
│  └────────────────────┬─────────────────────────────────┘   │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    SQLite Database                           │
│  cfb_rankings.db (file-based, single-writer)                │
│  - teams, games, ranking_history, seasons tables            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  Frontend (Browser - SPA)                     │
│  ┌──────────┬──────────┬──────────┬──────────┬───────────┐  │
│  │Rankings  │  Teams   │  Games   │  Team    │Comparison │  │
│  │  Page    │   Page   │   Page   │  Detail  │   Page    │  │
│  │(index)   │          │          │          │ (vs AP)   │  │
│  └──────────┴──────────┴──────────┴──────────┴───────────┘  │
│             Fetch API (frontend/js/api.js)                   │
└──────────────────────────────────────────────────────────────┘
```

### Actual Tech Stack

| Category              | Technology                  | Version     | Notes                                          |
|-----------------------|-----------------------------|-------------|------------------------------------------------|
| **Backend Runtime**   | Python                      | 3.11+       | Required for FastAPI and type hints            |
| **Backend Framework** | FastAPI                     | 0.104.1     | Modern async API framework                     |
| **ASGI Server**       | Uvicorn                     | 0.24.0      | Production ASGI server (via Gunicorn)          |
| **Database**          | SQLite                      | 3.x         | File-based, single-writer (migration ready)    |
| **ORM**               | SQLAlchemy                  | 2.0.23      | Declarative ORM with relationship support      |
| **Validation**        | Pydantic                    | 2.5.0       | Request/response validation                    |
| **Environment**       | python-dotenv               | 1.0.0       | .env file management                           |
| **HTTP Client**       | requests                    | 2.31.0+     | External API integration                       |
| **WSGI Server**       | Gunicorn                    | 21.2.0      | Process manager for Uvicorn workers            |
| **Web Server**        | Nginx                       | Latest      | Reverse proxy + static file serving            |
| **Process Manager**   | systemd                     | System      | Service management and auto-restart            |
| **SSL**               | Let's Encrypt (Certbot)     | Latest      | Free TLS certificates with auto-renewal        |
| **Frontend**          | Vanilla JS (ES6+), HTML, CSS| Native      | No frameworks, lightweight and fast            |
| **External API**      | CollegeFootballData.com API | Free tier   | 100 requests/hour, requires API key            |

### Repository Structure Reality Check

- **Type**: Monorepo (single repository for backend + frontend)
- **Package Manager**: pip (Python) / No JS package manager (vanilla)
- **Database**: File-based SQLite (`cfb_rankings.db` in project root)
- **Environment Config**: `.env` file (gitignored)
- **Deployment**: VPS-based with subdomain support

---

## Source Tree and Module Organization

### Project Structure (Actual)

```
/
├── .env                        # Environment variables (CFBD_API_KEY, DATABASE_URL)
├── .gitignore                  # Ignores .env, *.db, __pycache__
├── requirements.txt            # Python dependencies
├── cfb_rankings.db             # SQLite database (created at runtime)
│
├── main.py                     # FastAPI app + all API endpoints (450 lines)
├── ranking_service.py          # ELO algorithm + business logic (363 lines)
├── models.py                   # SQLAlchemy ORM models (146 lines)
├── schemas.py                  # Pydantic validation schemas (200 lines)
├── database.py                 # DB connection and session management (48 lines)
├── gunicorn_config.py          # Gunicorn production config (33 lines)
│
├── cfbd_client.py              # College Football Data API client (150 lines)
├── import_real_data.py         # Data import script (uses cfbd_client)
├── seed_data.py                # Development sample data generator
├── demo.py                     # Standalone ELO algorithm demo
├── cfb_elo_ranking.py          # Standalone ELO implementation (demo only)
├── compare_rankings.py         # ELO vs AP Poll comparison utility
│
├── frontend/
│   ├── index.html              # Rankings page (main landing)
│   ├── teams.html              # All teams browser
│   ├── games.html              # Games list page
│   ├── team.html               # Team detail page
│   ├── comparison.html         # ELO vs AP Poll comparison
│   │
│   ├── css/
│   │   └── style.css           # All styling (dark mode friendly)
│   │
│   └── js/
│       ├── api.js              # API client abstraction
│       ├── app.js              # Rankings page logic
│       ├── team.js             # Team detail page logic
│       └── comparison.js       # Comparison page logic
│
├── deploy/
│   ├── setup.sh                # Initial VPS setup (installs deps, configures services)
│   ├── deploy.sh               # Update script (git pull + restart)
│   ├── nginx.conf              # Nginx reverse proxy config template
│   └── cfb-rankings.service    # systemd service definition
│
├── docs/
│   └── architecture.md         # This document
│
├── BROWNFIELD_PRD.md           # Comprehensive product requirements
├── PROJECT_DOCUMENTATION.md    # Original project documentation
└── README.md                   # Quick start guide
```

### Key Modules and Their Purpose

**Backend Core (12 Python files, ~2,700 lines total):**

- **`main.py:1-450`** - FastAPI Application
  - All REST API endpoints (teams, games, rankings, seasons, stats)
  - CORS middleware (currently allows all origins - TODO: production restriction)
  - Dependency injection for database sessions
  - Automatic OpenAPI documentation generation (Swagger UI at `/docs`)

- **`ranking_service.py:1-363`** - Ranking Engine
  - `calculate_preseason_rating()` - Factors recruiting, transfers, returning production
  - `process_game()` - Game result processing and ELO updates
  - `calculate_expected_score()` - Win probability calculation
  - `calculate_mov_multiplier()` - Margin of victory weighting
  - `get_conference_multiplier()` - P5/G5/FCS matchup adjustments
  - `calculate_sos()` - Strength of schedule averaging
  - `get_current_rankings()` - Ordered rankings with SOS

- **`models.py:1-146`** - Database Schema
  - `Team` - 13 fields including ELO rating, record, preseason factors
  - `Game` - 15 fields including scores, week, season, rating changes
  - `RankingHistory` - Weekly snapshots (rank, rating, SOS)
  - `Season` - Season metadata (year, current_week, is_active)
  - Relationships: Team 1-to-many Game (home/away), Team 1-to-many RankingHistory

- **`database.py:1-48`** - Database Connection
  - SQLAlchemy engine creation
  - Session factory with context manager
  - `init_db()` - Create tables if not exists
  - `get_db()` - FastAPI dependency for session injection
  - **GOTCHA**: `check_same_thread=False` required for SQLite + FastAPI

**Data Integration:**

- **`cfbd_client.py:1-150`** - External API Client
  - `get_teams()` - Fetch FBS teams for a season
  - `get_games()` - Fetch game results by week/season
  - `get_recruiting_rankings()` - 247Sports recruiting class data
  - `get_transfer_rankings()` - Transfer portal rankings
  - `get_returning_production()` - Returning production percentages
  - Bearer token authentication via `CFBD_API_KEY` env variable

- **`import_real_data.py`** - Data Import Script
  - Sequential import: teams → recruiting/transfers/production → games
  - Creates/updates Season record
  - Processes games in chronological order (critical for ELO accuracy)
  - **Usage**: `export CFBD_API_KEY='key' && python3 import_real_data.py`

**Frontend (5 HTML pages, 4 JS modules):**

- **`frontend/index.html` + `js/app.js`** - Rankings Page
  - Fetches `/api/rankings` and `/api/stats`
  - Sortable table with rank badges (top 5/10/25 color-coded)
  - Conference badges (P5/G5/FCS)
  - SOS indicators (elite/hard/average/easy with emoji)
  - Filter dropdown (top 10/25/50/all)

- **`frontend/team.html` + `js/team.js`** - Team Detail
  - URL param: `?id={team_id}`
  - Fetches `/api/teams/{id}` and `/api/teams/{id}/schedule`
  - Displays: team header, preseason factors, full schedule, weekly ranking chart
  - Chart.js for ranking history visualization

- **`frontend/js/api.js`** - API Client
  - Base URL: `window.location.origin` (same-origin policy)
  - Wraps fetch API with error handling
  - Methods: `getRankings()`, `getTeams()`, `getTeam()`, `getGames()`, etc.

**Deployment:**

- **`gunicorn_config.py`** - Production Server
  - 4 Uvicorn workers (configurable)
  - Bind: `127.0.0.1:8000` (Nginx proxies to this)
  - Timeout: 60s
  - Logs to stdout/stderr (systemd captures via journald)

- **`deploy/setup.sh`** - VPS Setup Automation
  - Installs: Python 3.11+, Nginx, Certbot
  - Creates virtual environment at `/var/www/cfb-rankings/venv`
  - Installs Python dependencies
  - Configures systemd service
  - Sets up Nginx with SSL (prompts for domain)
  - Initializes database and optionally imports data

- **`deploy/cfb-rankings.service`** - systemd Service
  - Runs as `www-data` user
  - Working directory: `/var/www/cfb-rankings`
  - Executes: `gunicorn -c gunicorn_config.py main:app`
  - Auto-restart on failure
  - Environment variables loaded from `/var/www/cfb-rankings/.env`

---

## Data Models and APIs

### Data Models

All models defined in `models.py` using SQLAlchemy ORM.

**Team Model** (`models.py:22-52`):
```python
class Team(Base):
    __tablename__ = "teams"

    # Identity
    id: Integer (PK)
    name: String(100) (Unique, Indexed)
    conference: Enum(ConferenceType)  # P5, G5, FCS

    # Preseason Factors
    recruiting_rank: Integer (default: 999)
    transfer_rank: Integer (default: 999)
    returning_production: Float (default: 0.5)

    # Current Season Stats
    elo_rating: Float (default: 1500.0)
    initial_rating: Float (default: 1500.0)
    wins: Integer (default: 0)
    losses: Integer (default: 0)

    # Timestamps
    created_at: DateTime
    updated_at: DateTime

    # Relationships
    home_games: List[Game]
    away_games: List[Game]
    ranking_history: List[RankingHistory]
```

**Game Model** (`models.py:54-100`):
```python
class Game(Base):
    __tablename__ = "games"

    id: Integer (PK)

    # Teams (Foreign Keys)
    home_team_id: Integer (FK -> teams.id)
    away_team_id: Integer (FK -> teams.id)

    # Scores
    home_score: Integer
    away_score: Integer

    # Context
    week: Integer
    season: Integer
    is_neutral_site: Boolean (default: False)
    game_date: DateTime

    # Processing
    is_processed: Boolean (default: False)
    home_rating_change: Float (default: 0.0)
    away_rating_change: Float (default: 0.0)

    created_at: DateTime

    # Computed Properties
    @property winner_id, loser_id
```

**RankingHistory Model** (`models.py:102-130`):
```python
class RankingHistory(Base):
    __tablename__ = "ranking_history"

    id: Integer (PK)
    team_id: Integer (FK -> teams.id)
    week: Integer
    season: Integer
    rank: Integer
    elo_rating: Float
    wins: Integer
    losses: Integer
    sos: Float
    sos_rank: Integer
    created_at: DateTime
```

**Season Model** (`models.py:132-146`):
```python
class Season(Base):
    __tablename__ = "seasons"

    id: Integer (PK)
    year: Integer (Unique)
    current_week: Integer (default: 0)
    is_active: Boolean (default: True)
    created_at: DateTime
    updated_at: DateTime
```

### API Specifications

Full API documentation available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

**API Endpoint Summary** (see `main.py` for full implementations):

| Endpoint                        | Method | Purpose                      | Auth Required | Location         |
|---------------------------------|--------|------------------------------|---------------|------------------|
| `/`                             | GET    | Health check                 | No            | `main.py:45`     |
| `/api/teams`                    | GET    | List teams (paginated)       | No            | `main.py:59`     |
| `/api/teams/{id}`               | GET    | Get team details + SOS       | No            | `main.py:76`     |
| `/api/teams`                    | POST   | Create team                  | **No** (TODO) | `main.py:124`    |
| `/api/teams/{id}`               | PUT    | Update team                  | **No** (TODO) | `main.py:155`    |
| `/api/teams/{id}/schedule`      | GET    | Team schedule for season     | No            | `main.py:191`    |
| `/api/games`                    | GET    | List games (filtered)        | No            | `main.py:213`    |
| `/api/games/{id}`               | GET    | Get game details             | No            | `main.py:237`    |
| `/api/games`                    | POST   | Add game (auto-processes)    | **No** (TODO) | `main.py:253`    |
| `/api/rankings`                 | GET    | Current rankings             | No            | `main.py:290`    |
| `/api/rankings/history`         | GET    | Team ranking history         | No            | `main.py:314`    |
| `/api/rankings/save`            | POST   | Save rankings snapshot       | **No** (TODO) | `main.py:332`    |
| `/api/seasons`                  | GET    | List all seasons             | No            | `main.py:353`    |
| `/api/seasons`                  | POST   | Create new season            | **No** (TODO) | `main.py:361`    |
| `/api/seasons/{year}/reset`     | POST   | Reset season ratings         | **No** (TODO) | `main.py:375`    |
| `/api/stats`                    | GET    | System statistics            | No            | `main.py:391`    |
| `/api/calculate`                | POST   | Recalculate season rankings  | **No** (TODO) | `main.py:423`    |

**CRITICAL SECURITY GAP**: No authentication/authorization on POST/PUT/DELETE endpoints. Anyone can modify data via API.

---

## Technical Debt and Known Issues

### Critical Technical Debt

**1. No Authentication or Authorization** (`main.py:1-450`)
- **Impact**: HIGH - Anyone can POST/PUT/DELETE teams, games, seasons
- **Location**: All write endpoints lack auth checks
- **Workaround**: Currently rely on obscurity (unlisted API)
- **Fix Required**: Implement API key system or JWT authentication

**2. SQLite Single-Writer Bottleneck** (`database.py:11-17`)
- **Impact**: MEDIUM - Cannot scale horizontally, file-locking limits concurrency
- **Location**: `DATABASE_URL = "sqlite:///./cfb_rankings.db"`
- **Constraint**: SQLite not suitable for high-traffic production
- **Migration Path**: PostgreSQL ready (SQLAlchemy abstracts DB)
- **Gotcha**: `check_same_thread=False` required for FastAPI compatibility

**3. No Caching Layer** (entire backend)
- **Impact**: MEDIUM - Rankings recalculated on every `/api/rankings` request
- **Location**: `ranking_service.py:273-317` - `get_current_rankings()` queries all teams
- **Performance**: SOS calculated per team on every ranking request
- **Fix Needed**: Redis cache with invalidation on game processing

**4. CORS Allows All Origins** (`main.py:28-34`)
- **Impact**: MEDIUM - Security risk, allows any domain to call API
- **Location**: `allow_origins=["*"]`
- **Comment**: Code includes TODO: "In production, specify actual domains"
- **Fix Required**: Whitelist specific frontend domains

**5. No Rate Limiting** (entire backend)
- **Impact**: MEDIUM - Vulnerable to abuse, no request throttling
- **Location**: Missing middleware in `main.py`
- **Risk**: External API key could be exhausted by malicious requests
- **Fix Needed**: Implement rate limiting middleware (e.g., slowapi)

### Workarounds and Gotchas

**Environment Variables - Manual systemd Configuration** (`deploy/cfb-rankings.service`)
- **Gotcha**: Environment variables must be set in systemd service file directly
- **Location**: Service file uses `Environment=CFBD_API_KEY=...` and `Environment=DATABASE_URL=...`
- **Reason**: systemd doesn't auto-load `.env` files
- **Workaround**: `deploy/setup.sh` prompts for API key and injects into service file
- **Fix**: Use `EnvironmentFile=/var/www/cfb-rankings/.env` (requires systemd 229+)

**Gunicorn Worker Class Must Be Uvicorn** (`gunicorn_config.py:9`)
- **Gotcha**: `worker_class = "uvicorn.workers.UvicornWorker"` is **required**
- **Reason**: FastAPI is ASGI, not WSGI - needs Uvicorn worker
- **Breaks If Changed**: Gunicorn default workers cannot run FastAPI
- **Note**: This is documented in config but critical for deployment

**Frontend API Base URL Assumption** (`frontend/js/api.js`)
- **Gotcha**: `const API_BASE_URL = window.location.origin`
- **Constraint**: Frontend and API must be served from same origin
- **Deployment Requirement**: Nginx must serve frontend at `/` and proxy API at `/api/*`
- **Breaks If**: Separate domains for frontend/backend

**Game Processing Must Be Chronological** (`import_real_data.py`, `main.py:253`)
- **Critical**: Games MUST be processed in chronological order (week 1 → 14)
- **Reason**: ELO ratings are cumulative; out-of-order processing corrupts ratings
- **Location**: `import_real_data.py` sorts games by date before processing
- **Risk**: Manual game addition via API can violate this constraint
- **No Protection**: API doesn't enforce chronological processing

**SQLite File Permissions** (deployment)
- **Gotcha**: `cfb_rankings.db` must be writable by `www-data` user
- **Location**: Database file in `/var/www/cfb-rankings/`
- **Deployment**: `deploy/setup.sh` sets ownership to `www-data:www-data`
- **Breaks If**: Permissions incorrect → 500 errors on write operations

### Performance Bottlenecks

**1. N+1 Query Problem in SOS Calculation** (`ranking_service.py:237-271`)
- **Issue**: `calculate_sos()` queries games individually per team
- **Location**: Loop over teams in `get_current_rankings()` calls `calculate_sos()`
- **Impact**: For 133 teams, this generates 133+ queries
- **Fix Needed**: Eager loading or batch SOS calculation

**2. No Pagination on Frontend Teams Page** (`frontend/teams.html`)
- **Issue**: Loads all teams (133+) at once
- **Impact**: Large payload, slow rendering on mobile
- **Location**: Calls `/api/teams` with default limit (100)
- **Fix Needed**: Virtual scrolling or pagination UI

**3. Chart.js Loaded on Every Page** (all HTML files)
- **Issue**: CDN script loaded even on pages without charts
- **Impact**: Unnecessary bandwidth and parse time
- **Location**: `<script src="https://cdn.jsdelivr.net/npm/chart.js">` in all HTML
- **Fix**: Lazy load Chart.js only on team detail page

### Code Quality Issues

**1. No Unit Tests**
- **Coverage**: 0%
- **Risk**: Refactoring ELO algorithm is risky without test coverage
- **Critical Areas Untested**:
  - `ranking_service.py:23-361` (all algorithms)
  - `main.py:253-283` (game processing endpoint)
  - Conference multiplier logic

**2. No Integration Tests**
- **Risk**: API contract changes could break frontend
- **Missing**: End-to-end tests for critical workflows (add game → update rankings)

**3. Minimal Error Handling** (`cfbd_client.py:30-39`)
- **Issue**: API errors print to console but don't raise exceptions
- **Location**: `_get()` method returns `None` on error
- **Impact**: Silent failures in data import
- **Fix Needed**: Proper exception hierarchy

**4. No Structured Logging**
- **Issue**: Using `print()` statements for debugging
- **Location**: `database.py:26`, `cfbd_client.py:38`, etc.
- **Fix Needed**: Python `logging` module with log levels

---

## Integration Points and External Dependencies

### External Services

| Service                      | Purpose                     | Integration Type | Auth Method      | Rate Limits     | Key Files                |
|------------------------------|-----------------------------|------------------|------------------|-----------------|--------------------------|
| CollegeFootballData.com API  | Real game data, recruiting  | REST API         | Bearer token     | 100 req/hour    | `cfbd_client.py`         |
| Let's Encrypt (Certbot)      | SSL/TLS certificates        | ACME protocol    | Domain validation| N/A             | `deploy/nginx.conf`      |

**CollegeFootballData.com API Details** (`cfbd_client.py`):
- **Base URL**: `https://api.collegefootballdata.com`
- **Authentication**: `Authorization: Bearer <CFBD_API_KEY>` header
- **Endpoints Used**:
  - `/teams/fbs` - FBS teams for a season
  - `/games` - Game results (scores, dates, venues)
  - `/recruiting/teams` - 247Sports recruiting class rankings
  - `/recruiting/transfer-portal` - Transfer portal rankings
  - `/teams/talent` - Returning production data
- **Rate Limit**: 100 requests/hour on free tier
- **Error Handling**: Returns `None` on failure (prints error message)
- **Retry Logic**: None (TODO)

**Let's Encrypt Integration** (`deploy/nginx.conf`, `deploy/setup.sh`):
- **Certbot Command**: `certbot --nginx -d <domain>`
- **Auto-Renewal**: systemd timer (certbot.timer)
- **Certificate Location**: `/etc/letsencrypt/live/<domain>/`
- **Nginx Config**: SSL directives in `deploy/nginx.conf` template

### Internal Integration Points

**Backend ↔ Database** (`database.py`):
- **Connection**: SQLAlchemy engine with `SessionLocal` factory
- **Session Management**: FastAPI dependency injection via `get_db()`
- **Pattern**: Context manager (auto-commit/rollback)
- **Location**: All endpoints use `db: Session = Depends(get_db)`

**Backend ↔ Frontend** (`frontend/js/api.js` → `main.py`):
- **Protocol**: REST API over HTTP(S)
- **Data Format**: JSON (Pydantic serialization)
- **CORS**: Enabled for all origins (TODO: restrict)
- **Error Format**: `{"detail": "error message"}` (FastAPI standard)
- **Base URL**: Same origin (`window.location.origin`)

**Nginx ↔ Gunicorn** (`deploy/nginx.conf`):
- **Proxy**: `proxy_pass http://127.0.0.1:8000;`
- **Headers**: X-Forwarded-For, X-Forwarded-Proto, Host
- **Routing**:
  - `/` → Static files from `frontend/`
  - `/api/` → Gunicorn backend
  - `/docs`, `/redoc` → FastAPI documentation

**systemd ↔ Gunicorn** (`deploy/cfb-rankings.service`):
- **Service Name**: `cfb-rankings.service`
- **User**: `www-data`
- **Working Directory**: `/var/www/cfb-rankings`
- **ExecStart**: `venv/bin/gunicorn -c gunicorn_config.py main:app`
- **Restart**: `on-failure`
- **Logs**: journalctl (`journalctl -u cfb-rankings -f`)

---

## Development and Deployment

### Local Development Setup

**Prerequisites**:
- Python 3.11+
- pip

**Setup Steps**:
1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file (optional for dev, required for real data):
   ```
   CFBD_API_KEY=your_api_key_here
   DATABASE_URL=sqlite:///./cfb_rankings.db
   ```
4. Initialize database with sample data: `python3 seed_data.py`
5. Start server: `python3 main.py` or `uvicorn main:app --reload`
6. Access:
   - API: `http://localhost:8000`
   - Docs: `http://localhost:8000/docs`
   - Frontend: `http://localhost:8000/index.html`

**Import Real Data** (optional):
1. Get API key from `https://collegefootballdata.com/key`
2. Export key: `export CFBD_API_KEY='your-key'`
3. Run import: `python3 import_real_data.py`
4. Select season when prompted

### Build and Deployment Process

**Production Stack**:
- **OS**: Ubuntu/Debian VPS
- **Path**: `/var/www/cfb-rankings/`
- **User**: `www-data`
- **Python**: Virtual environment at `venv/`

**Initial Deployment** (`deploy/setup.sh`):
1. SSH to VPS
2. Clone repository to `/var/www/cfb-rankings`
3. Run: `sudo bash deploy/setup.sh`
4. Script performs:
   - Install system packages (Python 3.11, Nginx, Certbot)
   - Create virtual environment
   - Install Python dependencies
   - Prompt for CFBD_API_KEY and domain
   - Configure Nginx reverse proxy
   - Set up systemd service
   - Obtain SSL certificate (Certbot)
   - Initialize database
   - Start service

**Update Deployment** (`deploy/deploy.sh`):
1. SSH to VPS
2. Navigate to `/var/www/cfb-rankings`
3. Run: `sudo bash deploy/deploy.sh`
4. Script performs:
   - Git pull latest changes
   - Activate virtual environment
   - Install new dependencies
   - Restart Gunicorn service
   - Reload Nginx config

**Service Management**:
```bash
sudo systemctl start cfb-rankings    # Start service
sudo systemctl stop cfb-rankings     # Stop service
sudo systemctl restart cfb-rankings  # Restart service
sudo systemctl status cfb-rankings   # Check status
journalctl -u cfb-rankings -f        # View logs (follow)
```

**Nginx Management**:
```bash
sudo nginx -t                        # Test config syntax
sudo systemctl reload nginx          # Reload config (no downtime)
sudo systemctl restart nginx         # Restart Nginx
```

---

## Testing Reality

### Current Test Coverage

- **Unit Tests**: None (0%)
- **Integration Tests**: None
- **E2E Tests**: None
- **Manual Testing**: Primary QA method

### Running Tests

No automated tests currently exist.

**Manual Testing Workflow**:
1. Start dev server: `python3 main.py`
2. Use Swagger UI at `http://localhost:8000/docs`
3. Test endpoints manually
4. Check frontend pages visually

---

## Appendix - Useful Commands and Scripts

### Frequently Used Commands

**Development**:
```bash
# Start dev server with auto-reload
uvicorn main:app --reload

# Start dev server (production mode)
python3 main.py

# Initialize database
python3 database.py

# Generate sample data
python3 seed_data.py

# Import real data (requires CFBD_API_KEY)
export CFBD_API_KEY='your-key'
python3 import_real_data.py

# Run demo ELO algorithm
python3 demo.py
```

**Production**:
```bash
# Service management
sudo systemctl start cfb-rankings
sudo systemctl stop cfb-rankings
sudo systemctl restart cfb-rankings
sudo systemctl status cfb-rankings

# View logs
journalctl -u cfb-rankings -f          # Follow logs
journalctl -u cfb-rankings -n 100      # Last 100 lines

# Nginx
sudo nginx -t                          # Test config
sudo systemctl reload nginx            # Reload config
sudo systemctl restart nginx           # Restart

# SSL certificate renewal (manual)
sudo certbot renew                     # Renew all certs
sudo certbot certificates              # List certs
```

**Database**:
```bash
# SQLite CLI
sqlite3 cfb_rankings.db

# Common queries
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM games WHERE is_processed = 1;
SELECT name, elo_rating, wins, losses FROM teams ORDER BY elo_rating DESC LIMIT 25;

# Backup database
cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d).db
```

### Debugging and Troubleshooting

**Common Issues**:

1. **"Permission denied" on database file**
   - **Fix**: `sudo chown www-data:www-data cfb_rankings.db`

2. **"Address already in use" (port 8000)**
   - **Fix**: `sudo lsof -i :8000` → `sudo kill <PID>`

3. **Gunicorn won't start after deployment**
   - **Check logs**: `journalctl -u cfb-rankings -n 50`
   - **Common causes**:
     - Missing `.env` or environment variables in service file
     - Python dependencies not installed in venv
     - Syntax error in Python code

4. **Nginx 502 Bad Gateway**
   - **Cause**: Gunicorn not running or not listening on 127.0.0.1:8000
   - **Fix**: Check `systemctl status cfb-rankings` and restart

5. **SSL certificate issues**
   - **Renew manually**: `sudo certbot renew`
   - **Check expiration**: `sudo certbot certificates`
   - **Auto-renewal**: Verify `certbot.timer` is active: `systemctl status certbot.timer`

6. **Frontend blank or API errors**
   - **Check CORS**: Verify browser console for CORS errors
   - **Check API**: Test endpoints directly at `http://localhost:8000/docs`
   - **Check Nginx routing**: Verify `/api/*` proxies to Gunicorn

---

## Document Metadata

**Version**: 1.0
**Date**: 2025-10-06
**Author**: Winston (Architect Agent)
**Status**: Complete
**Next Review**: After major feature additions or architecture changes

**Purpose**: This brownfield architecture document serves as the definitive reference for the **actual implementation** of the College Football Ranking System. It documents technical decisions, constraints, workarounds, and technical debt to enable informed development and maintenance by AI agents and human developers.

---

*End of Document*
