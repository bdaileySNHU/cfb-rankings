# Development Guide

An in-depth look at the Stat-urday Synthesis codebase: architecture, design
patterns, and common development tasks.

> Verified against the tree at commit `eea902b` on 2026-09-02. Earlier revisions
> of this guide described a flat root-level layout (`main.py` holding every
> endpoint, `ranking_service.py` at ~363 lines) that no longer exists — the
> backend now lives under `src/`.

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

A full-stack web application that calculates college football rankings using a
Modified ELO algorithm:

- **Backend:** FastAPI REST API with SQLAlchemy ORM, organized under `src/`
- **Database:** SQLite (file-based, `DATABASE_URL` abstracts a Postgres move)
- **Frontend:** Vanilla JavaScript, 8 static pages, no build step
- **External API:** CollegeFootballData.com integration
- **Deployment:** Nginx reverse proxy + Gunicorn + systemd

For complete architecture documentation, see **[docs/architecture.md](docs/architecture.md)**.

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Backend Framework | FastAPI | 0.125.0 | Modern async REST API |
| ASGI Toolkit | Starlette | 0.50.0 | Pinned to match FastAPI |
| ORM | SQLAlchemy | 2.0.23 | Database abstraction |
| Validation | Pydantic | 2.5.0 | Request/response validation |
| Database | SQLite | 3.x | File-based storage |
| ASGI Server | Uvicorn | 0.24.0 | Development + production worker |
| Process Manager | Gunicorn | 21.2.0 | Production worker supervision |
| Web Server | Nginx | Latest | Reverse proxy, static files |
| Frontend | Vanilla JS | ES6+ | No build process, lightweight |
| Testing | pytest + Playwright | - | 922 tests: unit, integration, E2E |

### System Flow

```
User Browser
    ↓
Nginx (Static Files + Reverse Proxy)
    ↓
Gunicorn + Uvicorn Workers
    ↓
main.py (shim) → src/api/main.py (FastAPI app)
    ↓
src/api/routers/*.py (7 route modules, 48 routes)
    ↓
src/core/*.py (RankingService and friends)
    ↓
src/models/models.py (SQLAlchemy ORM)
    ↓
SQLite Database
```

**External Integration:**
```
src/importers/pipeline.py → src/integrations/cfbd_client.py → CollegeFootballData API
```

---

## Core Module Responsibilities

### main.py (15 lines)
**Purpose:** Entry-point shim only.

Re-exports `src.api.main:app` so `gunicorn -c gunicorn_config.py main:app`
resolves from the project root without an untracked shim on the server. Contains
no application logic. Do not add any.

---

### src/api/main.py (~110 lines)
**Purpose:** FastAPI application construction.

**Responsibilities:**
- Build the `FastAPI` instance (title, description, version)
- CORS middleware configuration
- Mount `frontend/` as static files at `/frontend`
- `init_db()` on startup
- Register the seven route modules (`src/api/main.py:98`)

Routers are included **without a prefix** — each decorator declares its full path
(e.g. `@router.get("/api/teams")`), so URLs are unchanged from the pre-`src/`
layout.

---

### src/api/routers/ (7 modules, 48 routes)
**Purpose:** HTTP layer, one module per domain. Routes stay thin; logic belongs
in `src/core/`.

| Module | Routes | Surface |
|--------|--------|---------|
| `meta.py` | 3 | `/` health, `/api/stats`, `/api/calculate` |
| `teams.py` | 11 | teams, schedule, players, position strength, ELO history, `/api/matchup` |
| `games.py` | 3 | list, detail, `POST /api/games` (auto-processes) |
| `predictions.py` | 6 | slate predictions, accuracy tracking |
| `rankings.py` | 7 | rankings, history, weeks, postseason, playoff projection |
| `seasons.py` | 5 | list, create, detail, active, `/{year}/reset` (destructive) |
| `admin.py` | 13 | imports, config, API usage, manual triggers |

**Example** (`src/api/routers/rankings.py:22`):
```python
@router.get("/api/rankings", response_model=schemas.RankingsResponse, tags=["Rankings"])
def get_rankings(
    season: Optional[int] = None,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    ...
```

---

### src/core/ranking_service.py (~1,900 lines)
**Purpose:** The Modified ELO algorithm and the bulk of the business logic. This
is the product.

**Responsibilities:**
- Preseason ratings from recruiting, transfer portal, returning production, and
  roster-derived position strength
- ELO updates after each game, including margin-of-victory and conference weighting
- The efficiency blend that sits between raw ELO and the displayed rating
- Strength of schedule
- Game predictions and accuracy evaluation
- CFP field selection and bracket projection

**Key entry points:**

| Function | Line | Role |
|----------|------|------|
| `calculate_preseason_rating()` | 366 | Where a team's season begins |
| `_calculate_preseason_bonuses()` | 301 | Recruiting / portal / returning production |
| `_calculate_position_strength_bonus()` | 429 | Roster-derived adjustment |
| `get_k_factor()` | 275 | Progressive K by week |
| `process_game()` | 775 | The core ELO update loop |
| `calculate_expected_score()` | 635 | Win probability |
| `calculate_mov_multiplier()` | 649 | Margin-of-victory weighting |
| `calculate_quarter_weighted_mov()` | 665 | Garbage-time-adjusted MOV |
| `get_conference_multiplier()` | 747 | P5 / G5 / FCS adjustment |
| `calculate_sos()` | 967 | Strength of schedule |
| `get_current_rankings()` | 1009 | Ordered rankings output |
| `generate_predictions()` | 1247 | Upcoming-slate predictions (scoreboard-ordered) |
| `project_playoff_bracket()` | 1635 | CFP projection |

**Slate ordering:** `generate_predictions()` returns games in scoreboard order —
kickoff time ascending, then visiting team A–Z. The `ORDER BY` lives in SQL
(`:1297`), and the stored-prediction path in
`src/api/routers/predictions.py:78` repeats it. Keep it in SQL: `Game.game_date`
is nullable, so a Python `sort()` raises `TypeError` on undated games. The
frontend renders API order without re-sorting.

**Module-level efficiency blend** (defined above the class):
`net_ppa()` `:75`, `efficiency_scale()` `:82`, `efficiency_rating()` `:120`,
`blend_rating()` `:139`, `effective_rating()` `:172`.

**ELO formula:**
```
Rating Change = K(week) × (Actual − Expected) × MOV_Multiplier × Conference_Multiplier

Where:
- K(week)   = 64 for weeks 1–4, 48 for weeks 5–8, 32 for weeks 9+  (EPIC-027)
- Expected  = 1 / (1 + 10^((Opponent_Rating − Team_Rating) / RATING_SCALE))
- RATING_SCALE = 400
- HOME_FIELD_ADVANTAGE = 65 ELO points
- MOV_Multiplier = min(ln(point_diff + 1), 2.5)
```

Progressive K lets preseason ratings correct quickly, then stabilizes. The
constants live at the top of the `RankingService` class (`:218`). Quarter-weighted
MOV additionally discounts Q4 to 25% when a game is already a 21+ point blowout
entering the quarter (`GARBAGE_TIME_THRESHOLD`, `GARBAGE_TIME_Q4_WEIGHT`).

> There is no `calculate_elo_change()` function. The rating update is inlined in
> `process_game()`.

---

### src/core/ — other services

| Module | Purpose |
|--------|---------|
| `season_simulation.py` | Monte Carlo season simulation feeding the playoff projection |
| `position_service.py` | Roster-based position strength (weights in `position_weights.json`) |
| `production_service.py` | Returning production signal |
| `transfer_portal_service.py` | Transfer portal rankings |
| `ap_poll_service.py` | AP poll data for the comparison view |

---

### src/models/models.py (~790 lines, 11 tables)
**Purpose:** SQLAlchemy ORM models.

| Model | Line | Model | Line |
|-------|------|-------|------|
| `Team` | 75 | `APIUsage` | 562 |
| `Player` | 167 | `UpdateTask` | 610 |
| `RosterPlayer` | 236 | `Prediction` | 659 |
| `Game` | 294 | `APPollRanking` | 707 |
| `RankingHistory` | 454 | `PlayoffSimulation` | 754 |
| `Season` | 521 | | |

`ConferenceType` (`:54`) is the P5/G5/FCS enum used by the conference multiplier.

**Relationships:**
```python
Team.home_games      → Game            (one-to-many)
Team.away_games      → Game            (one-to-many)
Team.ranking_history → RankingHistory  (one-to-many)
```

---

### src/models/schemas.py (~920 lines)
**Purpose:** Pydantic validation schemas.

Naming convention: the bare name is the read model, `*Create` / `*Update` are the
write models, `*Detail` extends the read model with computed extras.

- `TeamBase` → `TeamCreate`, `TeamUpdate`, `Team`, `TeamDetail`
- `GameBase` → `GameCreate`, `Game`, `GameDetail`
- `RankingEntry`, `RankingsResponse`, `RankingHistory`
- `GamePrediction`, `HistoricalPrediction`, `PredictionAccuracyStats`
- `SystemStats`, `SystemConfig`, `APIUsageResponse`, `SuccessResponse`

**Example** (`src/models/schemas.py:112`):
```python
class Team(TeamBase):
    """Schema for team response"""

    id: int
    elo_rating: float
    wins: int
    losses: int

    class Config:
        from_attributes = True
```

---

### src/models/database.py (~115 lines)
**Purpose:** Database connection and session management.

**Key functions:**
- `get_db()` — yields a session for FastAPI dependency injection, closes it in a
  `finally`
- `init_db()` — `Base.metadata.create_all()`, run on app startup
- `reset_db()` — drop and recreate all tables (destructive)

**Gotcha:** `check_same_thread=False` is applied for SQLite URLs only; it is
required for SQLite under FastAPI's threadpool.

> The docstrings in this module suggest using Alembic for schema changes. **There
> is no Alembic in this project.** See [Adding a Database Field](#3-adding-a-database-field).

---

### src/integrations/cfbd_client.py (~1,175 lines)
**Purpose:** CollegeFootballData API integration. Roughly one method per CFBD
endpoint, plus season/week inference helpers.

**Key methods:**

| Method | Line | Returns |
|--------|------|---------|
| `get_teams()` | 592 | FBS teams for a year |
| `get_games()` | 604 | Games by season/week |
| `get_current_week()` | 464 | Live week from the CFBD calendar |
| `estimate_current_week()` | 513 | Fallback week from Labor Day arithmetic |
| `get_recruiting_rankings()` | 635 | Team recruiting classes |
| `get_transfer_portal()` | 965 | Transfer portal entries |
| `get_returning_production()` | 948 | Returning production percentages |
| `get_roster()` | 724 | Team rosters (feeds position strength) |
| `get_team_ppa_season()` | 887 | Team PPA (feeds the efficiency blend) |
| `get_ap_poll()` | 977 | AP poll rankings |
| `get_game_line_scores()` | 1049 | Quarter scores (feeds quarter-weighted MOV) |

Auth is `Authorization: Bearer <CFBD_API_KEY>`. Calls are counted against the
free-tier cap and recorded in the `api_usage` table — check
`GET /api/admin/api-usage` before a large backfill.

---

### src/importers/
**Purpose:** Import orchestration, split out of the old monolithic import script.

`pipeline.py` orchestrates; `teams.py`, `games.py`, `polls.py`, `efficiency.py`,
`postseason.py` do the work; `common.py` and `validation.py` are shared helpers.

`import_real_data.py` at the project root is a CLI shim re-exporting this
package, kept so existing callers (`production_import.sh`, `deploy/setup.sh`,
`scripts/weekly_update.py`, tests) keep working.

---

## Key Design Patterns

### 1. Dependency Injection (FastAPI)

```python
from fastapi import Depends
from src.models.database import get_db

@router.get("/api/teams")
def get_teams(db: Session = Depends(get_db)):
    # Session is created before the call, closed after it
    return db.query(Team).all()
```

**Benefits:** automatic cleanup, easy test substitution, clear signatures.

### 2. Service Layer Pattern

Business logic stays out of the routers:

```python
# src/api/routers/games.py  (API layer — thin)
@router.post("/api/games", response_model=schemas.GameResult, status_code=201)
def add_game(game: schemas.GameCreate, db: Session = Depends(get_db)):
    service = RankingService(db)
    return service.process_game(game)

# src/core/ranking_service.py  (business logic — thick)
class RankingService:
    def process_game(self, game: Game) -> dict:
        ...
```

**Benefits:** logic reusable from `scripts/` and `utilities/` without HTTP, and
testable without a client.

### 3. ORM Pattern (SQLAlchemy)

```python
teams = db.query(Team).filter(Team.elo_rating > 1800).all()

team = db.query(Team).first()
home_games = team.home_games  # relationship, joined on access
```

### 4. Pydantic Validation

```python
class GameCreate(GameBase):
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    week: int
    season: int

@router.post("/api/games")
def add_game(game: schemas.GameCreate):  # invalid payload → 422
    ...
```

---

## Common Development Tasks

### 1. Adding a New API Endpoint

1. **Define schemas** in `src/models/schemas.py`:
   ```python
   class TeamStatsResponse(BaseModel):
       wins: int
       losses: int
       avg_rating: float
   ```

2. **Add the route** to the right module in `src/api/routers/` — declare the full
   path, since routers carry no prefix:
   ```python
   # src/api/routers/teams.py
   @router.get("/api/teams/{team_id}/stats", response_model=schemas.TeamStatsResponse, tags=["Teams"])
   def get_team_stats(team_id: int, season: int, db: Session = Depends(get_db)):
       ...
   ```
   A brand-new domain needs a new module plus an `include_router()` line in
   `src/api/main.py`.

3. **Add tests** in `tests/integration/`:
   ```python
   @pytest.mark.integration
   def test_get_team_stats(test_client: TestClient, test_db: Session):
       team = TeamFactory()
       response = test_client.get(f"/api/teams/{team.id}/stats?season=2026")
       assert response.status_code == 200
   ```

4. **Verify manually:**
   ```bash
   uvicorn main:app --reload
   curl "http://localhost:8000/api/teams/1/stats?season=2026"
   ```

### 2. Modifying the ELO Algorithm

**Location:** `src/core/ranking_service.py`

Tunable constants sit at the top of `RankingService` (`:218`):

```python
K_FACTOR_EARLY = 64   # weeks 1-4
K_FACTOR_MID   = 48   # weeks 5-8
K_FACTOR_LATE  = 32   # weeks 9+
RATING_SCALE   = 400
HOME_FIELD_ADVANTAGE = 65
MAX_MOV_MULTIPLIER   = 2.5
```

**Workflow:**
1. Change the constant or the function.
2. Update `tests/unit/test_ranking_service.py` — many tests assert on specific
   rating outcomes and will fail loudly.
3. Reprocess a season to see the effect end to end:
   `python3 utilities/reprocess_season.py --season 2026` (add `--dry-run` first)
4. Compare before/after: `python3 utilities/compare_rankings.py`, or
   `python3 utilities/evaluate_rating_systems.py` for accuracy/calibration
   across systems.

Weight changes to the preseason components are also exposed at runtime via
`PUT /api/admin/preseason-weights` — check whether a code change is even needed.

### 3. Adding a Database Field

There is **no Alembic**. `migrations/` holds hand-applied `.sql` files and one-off
`migrate_add_*.py` scripts, and `init_db()` only creates *missing tables* — it
never alters an existing one. A new column therefore needs a migration script.

**Example: add a `coach` field to Team**

1. **Update the model** (`src/models/models.py`):
   ```python
   class Team(Base):
       # ... existing columns
       coach = Column(String, nullable=True)
   ```

2. **Write a migration** following the existing convention in `migrations/`:
   ```python
   # migrations/migrate_add_coach.py
   import os
   from sqlalchemy import create_engine, text

   engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./cfb_rankings.db"))

   with engine.begin() as conn:
       conn.execute(text("ALTER TABLE teams ADD COLUMN coach VARCHAR"))
   ```

3. **Back up, then run it:**
   ```bash
   cp cfb_rankings.db "cfb_rankings_backup_$(date +%Y%m%d).db"
   python3 migrations/migrate_add_coach.py
   ```

4. **Update schemas** (`src/models/schemas.py`) so the field is exposed:
   ```python
   class Team(TeamBase):
       coach: Optional[str] = None
   ```

5. **Remember production** — the migration has to run on the VPS too, during the
   deploy that ships the model change.

### 4. Adding Tests

Fixtures live in `tests/conftest.py`. The real ones are `test_db`, `test_client`,
`db_session`, `factories`, `mock_cfbd_client`, `live_server`, and `browser_page`.
Each test gets its own database (see `tests/unit/test_db_fixture_isolation.py`).

Test data comes from `tests/factories.py`: `TeamFactory`, `GameFactory`,
`SeasonFactory`, `RankingHistoryFactory`, plus the specialized
`EliteTeamFactory`, `G5ChampionFactory`, `FCSTeamFactory`,
`ProcessedGameFactory`, `NeutralSiteGameFactory`.

**Unit test:**
```python
# tests/unit/test_ranking_service.py
@pytest.mark.unit
def test_mov_multiplier_is_capped(test_db):
    service = RankingService(test_db)
    assert service.calculate_mov_multiplier(100) == service.MAX_MOV_MULTIPLIER
```

**Integration test:**
```python
# tests/integration/test_teams_api.py
@pytest.mark.integration
def test_get_team(test_client: TestClient, test_db: Session):
    team = TeamFactory(name="Ohio State")
    response = test_client.get(f"/api/teams/{team.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Ohio State"
```

**Running them:**
```bash
make test-unit          # fast
make test               # unit + integration — the gate CI enforces
make test-e2e           # Playwright, needs a server on port 8765
make test-fast          # parallel, -n auto
make coverage-html      # → htmlcov/index.html
```

Markers (`unit`, `integration`, `e2e`) are declared in `pytest.ini`. See
[docs/TESTING.md](docs/TESTING.md) for the fuller guide.

### 5. Importing New Data

```bash
# Weekly incremental import
python3 import_real_data.py

# Full reset (first run or clean slate)
python3 import_real_data.py --reset

# Scoped import
python3 import_real_data.py --season 2026 --max-week 4
```

The production cadence is `scripts/weekly_update.py`, driven on the VPS by
`deploy/cfb-weekly-update.timer`. Read that script before writing any new import
tooling — it already handles week detection, ranking snapshots, and prediction
generation.

**Custom data:**
```python
from src.models.database import SessionLocal
from src.models.models import Team, ConferenceType

db = SessionLocal()
db.add(Team(name="New Team", conference=ConferenceType.P5))
db.commit()
```

> **Order matters.** ELO is cumulative, so games must be processed in
> chronological order. The importers sort before processing; `POST /api/games`
> does **not** enforce it. Out-of-order inserts silently corrupt ratings.
> Recovery is `python3 utilities/reprocess_season.py --season <year>` — back up
> the database first, it resets and replays every game in the season.

---

## Troubleshooting Guide

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:** Run from the project root — imports are absolute from `src.`.
```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

**Problem:** `ModuleNotFoundError: No module named 'models'`

**Cause:** a stale import path from before the `src/` restructure. Update it:
`models` → `src.models.models`, `ranking_service` → `src.core.ranking_service`,
`cfbd_client` → `src.integrations.cfbd_client`.

---

### Database Errors

**Problem:** `sqlalchemy.exc.OperationalError: no such table: teams`

**Solution:**
```bash
python3 -c "from src.models.database import init_db; init_db()"
python3 utilities/seed_data.py     # optional sample data
```

**Problem:** `no such column: teams.<something>`

**Cause:** a model gained a column but the migration never ran against this
database. `create_all()` will not add it. Run the matching script in
`migrations/`.

**Problem:** Database is locked

**Cause:** SQLite is single-writer; usually a stale server or an import still
holding the file.
```bash
lsof cfb_rankings.db
```
Stop that process rather than deleting the database.

---

### API Call Failures

**Problem:** `401 Unauthorized` from CFBD

```bash
grep CFBD_API_KEY .env    # verify the key at collegefootballdata.com
```

**Problem:** `429 Too Many Requests` from CFBD

```bash
curl "http://localhost:8000/api/admin/api-usage"
```
Wait for the window to reset. Check usage *before* running a backfill —
`scripts/backfill_historical_predictions.py` has a dry-run mode for this reason.

---

### Test Failures

**Problem:** `fixture 'client' not found` / `fixture 'sample_team' not found`

**Cause:** those fixtures do not exist. Use `test_client` and `test_db`, and
build data with the factories from `tests/factories.py`.
```bash
pytest --fixtures | head -50
```

**Problem:** E2E tests fail with browser errors

```bash
python3 -m playwright install chromium
pytest -m e2e -v --headed
```
E2E needs a server on port 8765 — the `live_server` fixture starts one.

---

### Frontend 404 Errors

**Problem:** Frontend pages return 404

1. Backend running? `uvicorn main:app --reload`
2. Use the `/frontend/` path: `http://localhost:8000/frontend/index.html`
3. Files present? `ls frontend/index.html`

**Problem:** API calls fail with CORS errors

CORS is configured in `src/api/main.py:70` and currently allows all origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Locally, `frontend/js/api.js` derives its base URL from
`window.location`, so frontend and API must be same-origin.

---

## Additional Resources

- **Architecture Documentation:** [docs/architecture.md](docs/architecture.md)
- **Testing Guide:** [docs/TESTING.md](docs/TESTING.md)
- **Coding Standards:** [docs/architecture/coding-standards.md](docs/architecture/coding-standards.md)
- **CI/CD Pipeline:** [docs/CI-CD-PIPELINE.md](docs/CI-CD-PIPELINE.md)
- **Contributing Guide:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **API Documentation:** http://localhost:8000/docs (when running locally)

---

## Need More Help?

- **Code Comments:** most services carry detailed module and function docstrings
- **The tests:** `tests/unit/test_ranking_service.py` is the most accurate
  description of intended algorithm behavior in the repo
- **Epic docs:** `docs/EPIC-*.md` explain *why* a given piece works the way it
  does — grep them, don't read them in sequence

Happy coding! 🚀
