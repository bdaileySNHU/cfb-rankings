# Development Guide

This guide provides an in-depth look at the Stat-urday Synthesis codebase architecture, design patterns, and common development tasks.

---

## Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [Core Module Responsibilities](#core-module-responsibilities)
- [Key Design Patterns](#key-design-patterns)
- [Common Development Tasks](#common-development-tasks)
- [Troubleshooting Guide](#troubleshooting-guide)

---

## High-Level Architecture

### System Overview

The Stat-urday Synthesis project is a full-stack web application that calculates college football rankings using a Modified ELO algorithm. The system consists of:

- **Backend:** FastAPI REST API with SQLAlchemy ORM
- **Database:** SQLite (file-based, migration-ready for PostgreSQL)
- **Frontend:** Vanilla JavaScript (no frameworks)
- **External API:** CollegeFootballData.com integration
- **Deployment:** Nginx reverse proxy + Gunicorn + systemd

For complete architecture documentation, see **[docs/architecture.md](docs/architecture.md)**.

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Backend Framework | FastAPI | 0.104.1 | Modern async REST API |
| ORM | SQLAlchemy | 2.0.23 | Database abstraction |
| Validation | Pydantic | 2.5.0 | Request/response validation |
| Database | SQLite | 3.x | File-based storage |
| ASGI Server | Uvicorn | 0.24.0 | Development server |
| WSGI Server | Gunicorn | 21.2.0 | Production process manager |
| Web Server | Nginx | Latest | Reverse proxy, static files |
| Frontend | Vanilla JS | ES6+ | No build process, lightweight |
| Testing | pytest | Latest | Unit, integration, E2E tests |

### System Flow

```
User Browser
    ↓
Nginx (Static Files + Reverse Proxy)
    ↓
Gunicorn + Uvicorn Workers
    ↓
FastAPI Application (main.py)
    ↓
RankingService (Business Logic)
    ↓
SQLAlchemy ORM (models.py)
    ↓
SQLite Database
```

**External Integration:**
```
FastAPI → CFBDClient → CollegeFootballData API
```

---

## Core Module Responsibilities

### main.py (~450 lines)
**Purpose:** FastAPI application with all API endpoints

**Responsibilities:**
- Define all REST API routes (`/api/rankings`, `/api/teams`, `/api/games`, etc.)
- Handle HTTP requests/responses
- Dependency injection (database sessions)
- CORS middleware configuration
- Error handling and HTTPException responses

**Key Endpoints:**
- `GET /api/rankings` - Retrieve current rankings
- `GET /api/teams/{id}` - Get team details
- `POST /api/games` - Add game and update rankings
- `GET /api/predictions` - Get game predictions
- `GET /api/admin/api-usage` - Monitor CFBD API usage

**Example:**
```python
@app.get("/api/rankings")
def get_rankings(
    season: Optional[int] = None,
    limit: int = 25,
    db: Session = Depends(get_db)
):
    # Endpoint logic
    pass
```

---

### ranking_service.py (~363 lines)
**Purpose:** Modified ELO algorithm and business logic

**Responsibilities:**
- Calculate ELO rating changes after games
- Generate preseason ratings (recruiting, transfers, returning production)
- Calculate strength of schedule (SOS)
- Generate game predictions
- Calculate prediction accuracy

**Key Classes/Functions:**
- `RankingService` - Main service class
- `calculate_elo_change()` - ELO rating calculation
- `process_game()` - Update ratings after game
- `generate_predictions()` - Predict upcoming games
- `get_overall_prediction_accuracy()` - Track prediction success

**ELO Formula:**
```
Rating Change = K × (Actual - Expected) × MOV_Multiplier × Conference_Multiplier

Where:
- K = 32 (volatility factor)
- Expected = 1 / (1 + 10^((Opponent_Rating - Team_Rating) / 400))
- MOV_Multiplier = min(ln(point_diff + 1), 2.5)
```

---

### models.py (~146 lines)
**Purpose:** SQLAlchemy ORM models

**Responsibilities:**
- Define database schema (tables, columns, relationships)
- Model relationships between entities
- Database constraints and indexes

**Key Models:**
- `Team` - College football teams
- `Game` - Individual games between teams
- `RankingHistory` - Weekly ranking snapshots
- `Season` - Season configurations
- `Prediction` - Game predictions for comparison
- `APIUsage` - CFBD API call tracking
- `UpdateTask` - Async update job tracking

**Relationships:**
```python
Team.home_games → Game (one-to-many)
Team.away_games → Game (one-to-many)
Team.rankings → RankingHistory (one-to-many)
```

---

### schemas.py (~200 lines)
**Purpose:** Pydantic validation schemas

**Responsibilities:**
- Validate incoming API requests
- Format outgoing API responses
- Type safety for data transfer
- Automatic documentation generation

**Key Schemas:**
- `TeamCreate`, `TeamResponse` - Team data validation
- `GameCreate`, `GameResponse` - Game data validation
- `RankingResponse` - Rankings output format
- `PredictionResponse` - Prediction output format

**Example:**
```python
class TeamResponse(BaseModel):
    id: int
    name: str
    conference: ConferenceType
    elo_rating: float

    class Config:
        from_attributes = True
```

---

### database.py (~48 lines)
**Purpose:** Database connection and session management

**Responsibilities:**
- SQLAlchemy engine creation
- Session factory configuration
- Dependency injection for database sessions
- Database initialization

**Key Functions:**
- `get_db()` - Yields database session for FastAPI dependency injection
- `init_db()` - Initialize database schema

**Usage:**
```python
@app.get("/api/teams")
def get_teams(db: Session = Depends(get_db)):
    # db session automatically provided and cleaned up
    teams = db.query(Team).all()
    return teams
```

---

### cfbd_client.py (~150 lines)
**Purpose:** CollegeFootballData API integration

**Responsibilities:**
- HTTP requests to CFBD API
- Response parsing and error handling
- API usage tracking
- Rate limiting awareness

**Key Methods:**
- `get_teams()` - Fetch all FBS teams
- `get_games()` - Fetch games for season/week
- `get_calendar()` - Get current week
- `get_recruiting_rankings()` - Fetch recruiting data
- `get_transfer_portal()` - Fetch transfer data

**API Rate Limit:** 100 requests/hour, 1000 requests/month (free tier)

---

## Key Design Patterns

### 1. Dependency Injection (FastAPI)

FastAPI's `Depends()` pattern provides clean dependency management:

```python
from fastapi import Depends
from database import get_db

@app.get("/api/teams")
def get_teams(db: Session = Depends(get_db)):
    # Database session automatically:
    # - Created before function runs
    # - Passed as 'db' parameter
    # - Closed after function completes
    return db.query(Team).all()
```

**Benefits:**
- Automatic resource cleanup
- Easy testing (mock dependencies)
- Clear function signatures

### 2. Service Layer Pattern

Business logic is separated from API endpoints via `ranking_service.py`:

```python
# main.py (API Layer - thin)
@app.post("/api/games")
def add_game(game: GameCreate, db: Session = Depends(get_db)):
    service = RankingService(db)
    return service.process_game(game)

# ranking_service.py (Business Logic Layer - thick)
class RankingService:
    def process_game(self, game_data):
        # Complex ELO calculation logic here
        pass
```

**Benefits:**
- Business logic reusable outside API context
- Easier to test complex calculations
- Clear separation of concerns

### 3. ORM Pattern (SQLAlchemy)

Data access is abstracted through ORM models:

```python
# Query teams with high ELO
teams = db.query(Team).filter(Team.elo_rating > 1800).all()

# Access relationships
team = db.query(Team).first()
home_games = team.home_games  # Automatic join
```

**Benefits:**
- Database-agnostic (SQLite → PostgreSQL migration easy)
- Type-safe queries
- Automatic relationship loading

### 4. Pydantic Validation

Request/response data is validated automatically:

```python
class GameCreate(BaseModel):
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    week: int
    season: int

# FastAPI automatically validates:
@app.post("/api/games")
def add_game(game: GameCreate):  # Invalid data → 422 error
    # game is guaranteed to be valid here
    pass
```

**Benefits:**
- Input validation without manual checks
- Clear error messages
- Automatic API documentation

---

## Common Development Tasks

### 1. Adding a New API Endpoint

**Step-by-step:**

1. **Define Pydantic schemas** (schemas.py):
   ```python
   class StatsRequest(BaseModel):
       team_id: int
       season: int

   class StatsResponse(BaseModel):
       wins: int
       losses: int
       avg_rating: float
   ```

2. **Add endpoint** (main.py):
   ```python
   @app.get("/api/teams/{team_id}/stats", response_model=StatsResponse)
   def get_team_stats(
       team_id: int,
       season: int,
       db: Session = Depends(get_db)
   ):
       # Implementation
       pass
   ```

3. **Add tests** (tests/test_api_endpoints.py):
   ```python
   def test_get_team_stats(client, sample_team):
       response = client.get(f"/api/teams/{sample_team.id}/stats?season=2024")
       assert response.status_code == 200
       assert "wins" in response.json()
   ```

4. **Test manually:**
   ```bash
   # Start server
   python main.py

   # Test endpoint
   curl "http://localhost:8000/api/teams/1/stats?season=2024"
   ```

### 2. Modifying the ELO Algorithm

**Location:** `ranking_service.py`

**Example: Change K-factor**
```python
class RankingService:
    def calculate_elo_change(self, ...):
        K = 48  # Change from 32 to 48 for more volatility
        # ... rest of calculation
```

**Testing:**
1. Update unit tests in `tests/test_ranking_service.py`
2. Recalculate historical rankings: `python recalculate_season.py`
3. Compare new rankings with old to validate changes

### 3. Adding a Database Field

**Example: Add `coach` field to Team model**

1. **Update model** (models.py):
   ```python
   class Team(Base):
       # ... existing fields
       coach = Column(String, nullable=True)
   ```

2. **Create migration script**:
   ```python
   # migrate_add_coach.py
   from sqlalchemy import create_engine, MetaData, Table, Column, String

   engine = create_engine(DATABASE_URL)
   metadata = MetaData()

   teams_table = Table('teams', metadata, autoload_with=engine)

   with engine.begin() as conn:
       conn.execute('ALTER TABLE teams ADD COLUMN coach VARCHAR')
   ```

3. **Run migration**:
   ```bash
   python migrate_add_coach.py
   ```

4. **Update schemas** (schemas.py):
   ```python
   class TeamResponse(BaseModel):
       # ... existing fields
       coach: Optional[str] = None
   ```

### 4. Adding Tests

**Unit Test Example:**
```python
# tests/unit/test_ranking_service.py
def test_calculate_elo_change():
    service = RankingService(None)
    change = service.calculate_elo_change(
        team_rating=1500,
        opponent_rating=1600,
        actual_score=1.0  # win
    )
    assert change > 0  # Should gain rating from upset
```

**Integration Test Example:**
```python
# tests/integration/test_teams_api.py
def test_get_team(client, db_session, sample_team):
    response = client.get(f"/api/teams/{sample_team.id}")
    assert response.status_code == 200
    assert response.json()["name"] == sample_team.name
```

### 5. Importing New Data

**Real Data:**
```bash
# Weekly import (incremental)
python import_real_data.py

# Full reset (first time or clean slate)
python import_real_data.py --reset
```

**Custom Data:**
```python
# Create custom import script
from database import get_db
from models import Team, Game

db = next(get_db())

team = Team(name="New Team", conference=ConferenceType.P5)
db.add(team)
db.commit()
```

---

## Troubleshooting Guide

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'models'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Database Errors

**Problem:** `sqlalchemy.exc.OperationalError: no such table: teams`

**Solution:**
```bash
# Delete and recreate database
rm cfb_rankings.db
python seed_data.py
```

**Problem:** Database is locked

**Solution:**
```bash
# Close all connections, then:
rm cfb_rankings.db
python seed_data.py
```

---

### API Call Failures

**Problem:** `401 Unauthorized` from CFBD API

**Solution:**
```bash
# Check API key in .env file
cat .env | grep CFBD_API_KEY

# Verify key is valid at collegefootballdata.com
```

**Problem:** `429 Too Many Requests` from CFBD API

**Solution:**
```bash
# Check API usage
curl "http://localhost:8000/api/admin/api-usage"

# Wait for rate limit to reset (hourly or monthly)
```

---

### Test Failures

**Problem:** Tests fail with `fixture 'sample_team' not found`

**Solution:**
```bash
# Check conftest.py is present
ls tests/conftest.py

# Ensure pytest discovers fixtures
pytest --fixtures
```

**Problem:** E2E tests fail with browser errors

**Solution:**
```bash
# Install Playwright browsers
playwright install

# Run E2E tests with headed browser (to see what's happening)
pytest -m e2e -v --headed
```

---

### Frontend 404 Errors

**Problem:** Frontend pages return 404

**Solution:**
1. Ensure backend is running: `python main.py`
2. Check URL has `/frontend/` path: `http://localhost:8000/frontend/`
3. Verify static files exist: `ls frontend/index.html`

**Problem:** API calls fail with CORS errors

**Solution:**
```python
# Check CORS middleware in main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Additional Resources

- **Architecture Documentation:** [docs/architecture.md](docs/architecture.md)
- **Testing Guide:** [docs/TESTING.md](docs/TESTING.md)
- **CI/CD Pipeline:** [docs/CI-CD-PIPELINE.md](docs/CI-CD-PIPELINE.md)
- **Contributing Guide:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **API Documentation:** http://localhost:8000/docs (when running locally)

---

## Need More Help?

- **GitHub Issues:** Report bugs or request features
- **GitHub Discussions:** Ask questions, share ideas
- **Code Comments:** Many functions have detailed docstrings
- **Architecture Docs:** See `docs/` directory for comprehensive guides

Happy coding! 🚀
