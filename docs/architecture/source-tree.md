# Source Tree Structure

## Project Root

```
Stat-urday Synthesis/
├── src/                    # Application source code
├── frontend/               # Static web pages and client-side JavaScript
├── scripts/                # Operational scripts (production use)
├── migrations/             # Database schema migrations
├── diagnostics/            # Debugging and diagnostic tools
├── utilities/              # Development utilities
├── archive/                # Historical scripts (DO NOT RUN)
├── tests/                  # Test suite
├── docs/                   # Documentation
├── deploy/                 # Deployment configurations
├── .bmad-core/             # BMAD framework configurations
├── .github/                # GitHub workflows and templates
├── cfb_rankings.db         # SQLite database (production data)
├── import_real_data.py     # Main data import script
├── requirements.txt        # Python dependencies
├── gunicorn_config.py      # Gunicorn server configuration
├── pytest.ini              # pytest configuration
├── Makefile                # Build automation
├── README.md               # Project documentation
└── .env                    # Environment variables (not committed)
```

---

## Detailed Structure

### `/src/` - Application Source Code

Main application codebase organized by layer:

```
src/
├── api/                    # API endpoints and HTTP layer
│   └── main.py            # FastAPI application, all route definitions
│
├── core/                   # Business logic and algorithms
│   ├── ranking_service.py  # Modified ELO ranking algorithm
│   ├── ap_poll_service.py  # AP Poll comparison logic
│   ├── transfer_portal_service.py  # Transfer portal calculations
│   └── cfb_elo_ranking.py  # Standalone ELO implementation
│
├── models/                 # Data layer
│   ├── models.py          # SQLAlchemy database models (ORM)
│   ├── schemas.py         # Pydantic API validation schemas
│   └── database.py        # Database configuration and session management
│
└── integrations/           # External service clients
    └── cfbd_client.py     # CollegeFootballData.com API client
```

**Key Files:**
- **`api/main.py`** - FastAPI app, all endpoints, dependency injection
- **`core/ranking_service.py`** - Core ELO algorithm, game processing, predictions
- **`models/models.py`** - Database schema (Team, Game, Prediction, Season, etc.)
- **`models/schemas.py`** - API request/response models
- **`integrations/cfbd_client.py`** - CFBD API wrapper, rate limiting, data fetching

---

### `/frontend/` - Client-Side Web Application

Static HTML pages with vanilla JavaScript:

```
frontend/
├── index.html              # Rankings page (main landing page)
├── teams.html              # All teams list page
├── team.html               # Individual team detail page
├── games.html              # Games list page
├── comparison.html         # AP Poll vs ELO comparison page
├── elo-formula.html        # ELO algorithm explanation
│
├── css/
│   └── style.css          # Global styles, CSS variables
│
└── js/
    ├── api.js             # API client wrapper (fetch calls)
    ├── app.js             # Rankings page logic
    ├── team.js            # Team page logic
    ├── comparison.js      # Comparison page logic
    └── date-utils.js      # Date formatting utilities
```

**Page Responsibilities:**
- **`index.html` + `app.js`** - Display current rankings, season selector, filters
- **`comparison.html` + `comparison.js`** - ELO vs AP Poll accuracy comparison
- **`team.html` + `team.js`** - Team details, game history, rating progression
- **`teams.html`** - Sortable table of all teams
- **`games.html`** - Game results and schedules

**JavaScript Architecture:**
- **`api.js`** - Centralized API client (`api.getRankings()`, `api.getTeams()`, etc.)
- **Vanilla JS** - No frameworks (React, Vue, etc.)
- **Client-side rendering** - Fetch data from API, manipulate DOM

---

### `/scripts/` - Production Operational Scripts

Scripts for regular production operations:

```
scripts/
├── weekly_update.py                 # ⭐ Automated weekly data import
├── generate_predictions.py          # Generate predictions for upcoming games
├── backfill_predictions.py          # Backfill predictions for future games
├── backfill_historical_predictions.py  # ⭐ Backfill for processed games
├── check_predictions.py             # Verify prediction data
├── diagnose_predictions.py          # Debug prediction issues
└── reset_and_import.sh              # Full database reset and reimport
```

**Critical Scripts:**
- **`weekly_update.py`** - Runs automatically via systemd timer (Sundays)
- **`backfill_historical_predictions.py`** - Generate predictions using historical ratings
- **`generate_predictions.py`** - Create predictions for upcoming games

---

### `/migrations/` - Database Schema Changes

Python migration scripts for database schema evolution:

```
migrations/
├── README.md                        # Migration history and documentation
├── migrate_add_predictions.py       # Add predictions table
├── migrate_add_ap_poll_rankings.py  # Add AP poll data
├── migrate_add_quarter_scores.py    # Add quarter-by-quarter scores
├── migrate_add_game_type.py         # Add postseason game types
├── migrate_add_transfer_portal_fields.py
├── migrate_add_conference_name.py
├── migrate_add_fcs_fields.py
└── run_migration_*.py               # Migration runners
```

**Convention:**
- **`migrate_add_*.py`** - Additive schema changes (new columns, tables)
- **`run_migration_*.py`** - Orchestration scripts
- **Naming:** Descriptive of change (`migrate_add_<feature>.py`)

---

### `/diagnostics/` - Debugging Tools

Interactive scripts for troubleshooting and data verification:

```
diagnostics/
├── README.md                        # Diagnostic documentation
├── check_*.py                       # Data verification scripts
│   ├── check_prediction_accuracy.py
│   └── check_conference_mapping.py
├── debug_*.py                       # Interactive debugging
│   ├── debug_elo_calculation.py
│   └── debug_game_processing.py
└── diagnose_*.py                    # Problem identification
    └── diagnose_predictions.py
```

**Usage:** Development and troubleshooting only (not for production automation)

---

### `/utilities/` - Development Utilities

Reusable development tools and analysis scripts:

```
utilities/
├── README.md                        # Utility documentation
├── seed_data.py                     # Populate sample data
├── demo.py                          # Standalone ELO demonstration
├── compare_rankings.py              # ELO vs AP Poll analysis
├── compare_transfer_rankings.py     # Transfer portal impact analysis
└── evaluate_rating_systems.py      # Rating system evaluation
```

**Purpose:** Development, research, analysis (not production operations)

---

### `/archive/` - Historical Scripts

⚠️ **DO NOT RUN** - One-time scripts from past development:

```
archive/
├── README.md                        # Archive warnings and context
├── recalculate_*.py                 # Historical recalculations
├── optimize_k_factor.py             # K-factor optimization research
├── fix_*.py                         # One-time data fixes
└── update_games.py                  # Legacy update script
```

**Warning:** These scripts may modify data in unexpected ways. Preserved for reference only.

---

### `/tests/` - Test Suite

Comprehensive test coverage (78 tests):

```
tests/
├── unit/                   # Unit tests (isolated, fast)
│   ├── test_ranking_service.py      # ELO algorithm tests
│   ├── test_predictions.py          # Prediction logic tests
│   ├── test_ap_comparison.py        # AP comparison tests
│   └── test_*.py                    # Component tests
│
├── integration/            # Integration tests (database + API)
│   ├── test_predictions_api.py      # API endpoint tests
│   ├── test_game_processing.py      # Full game flow tests
│   └── test_*.py
│
└── e2e/                    # End-to-end tests (browser simulation)
    ├── test_predictions_workflow.py  # Full user workflows
    ├── test_comparison_page.py       # Page load and display
    └── test_*.py
```

**Test Coverage:**
- **Unit tests:** ~40 tests - Business logic, algorithms
- **Integration tests:** ~25 tests - API endpoints, database
- **E2E tests:** ~13 tests - Frontend workflows

**Running Tests:**
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Specific file
pytest tests/unit/test_ranking_service.py -v
```

---

### `/docs/` - Documentation

Project documentation organized by type:

```
docs/
├── architecture/           # Architecture documentation
│   ├── tech-stack.md      # Technology stack
│   ├── source-tree.md     # This file
│   └── coding-standards.md # Coding conventions
│
├── stories/                # User stories and features
│   ├── story-*.md         # Individual story files
│   └── epic-*.md          # Epic documentation
│
├── prd/                    # Product requirements (sharded)
│   └── *.md               # PRD sections
│
├── qa/                     # QA documentation
│
└── *.md                    # Top-level docs
    ├── PREDICTIONS.md      # Prediction methodology
    ├── WEEKLY-WORKFLOW.md  # Operational procedures
    └── API.md              # API documentation
```

---

### `/deploy/` - Deployment Configurations

Deployment scripts and configurations:

```
deploy/
├── systemd/               # systemd service files
│   ├── cfb-rankings.service
│   └── cfb-weekly-update.timer
├── nginx/                 # Nginx configurations (if applicable)
└── scripts/               # Deployment automation
```

---

### `/.bmad-core/` - BMAD Framework

Agent and task configurations:

```
.bmad-core/
├── core-config.yaml       # Project configuration
├── tasks/                 # PM/Dev task definitions
│   ├── brownfield-create-story.md
│   └── *.md
├── templates/             # Document templates
│   ├── prd-tmpl.yaml
│   └── *.yaml
└── checklists/            # QA and validation checklists
```

---

## Key Configuration Files

### Root Level

- **`import_real_data.py`** - Main script for importing CFBD data (games, teams, etc.)
- **`requirements.txt`** - Python dependencies (FastAPI, SQLAlchemy, etc.)
- **`requirements-dev.txt`** - Development dependencies (pytest, black, flake8)
- **`gunicorn_config.py`** - Gunicorn server configuration
- **`pytest.ini`** - pytest configuration (test paths, markers)
- **`pyproject.toml`** - Python project metadata (Black, isort config)
- **`.flake8`** - Flake8 linter configuration
- **`Makefile`** - Build automation (test, lint, deploy targets)
- **`.env`** - Environment variables (CFBD_API_KEY, etc.) - **NOT COMMITTED**
- **`.env.example`** - Template for environment variables
- **`.gitignore`** - Files to exclude from version control

### Database

- **`cfb_rankings.db`** - Production SQLite database
- **`cfb_rankings.db.backup_*`** - Database backups

---

## Import Paths and Module Structure

### Python Imports

From project root:
```python
# API endpoints
from src.api.main import app

# Business logic
from src.core.ranking_service import RankingService
from src.core.ap_poll_service import calculate_comparison_stats

# Data models
from src.models.models import Team, Game, Prediction
from src.models.schemas import TeamResponse, GameResponse
from src.models.database import SessionLocal, get_db

# External integrations
from src.integrations.cfbd_client import CFBDClient
```

**Convention:** Always use `src.` prefix for application imports.

---

## Entry Points

### Application Entry Points

1. **Web Application:**
   ```bash
   uvicorn src.api.main:app --reload
   ```

2. **Data Import:**
   ```bash
   python3 import_real_data.py
   ```

3. **Weekly Update:**
   ```bash
   python3 scripts/weekly_update.py
   ```

4. **Generate Predictions:**
   ```bash
   python3 scripts/generate_predictions.py
   ```

5. **Tests:**
   ```bash
   pytest
   ```

---

## Naming Conventions

### Directories
- **Lowercase with hyphens** - `cfb-rankings/`
- **Plural for collections** - `scripts/`, `tests/`, `docs/`

### Files
- **Python:** `snake_case.py` - `ranking_service.py`
- **JavaScript:** `kebab-case.js` - `date-utils.js`
- **HTML:** `kebab-case.html` - `elo-formula.html`
- **Markdown:** `kebab-case.md` or `UPPERCASE.md` for key docs

### Scripts
- **Descriptive names:** `weekly_update.py`, `generate_predictions.py`
- **Action-oriented:** `check_*.py`, `diagnose_*.py`, `migrate_add_*.py`

---

## File Organization Principles

1. **Separation of Concerns**
   - API layer (`src/api/`) separate from business logic (`src/core/`)
   - Data models (`src/models/`) isolated from business logic

2. **Single Responsibility**
   - Each file has a clear, focused purpose
   - `ranking_service.py` - ELO algorithm only
   - `ap_poll_service.py` - AP Poll logic only

3. **Discoverability**
   - Logical grouping by function (api/, core/, models/)
   - READMEs in key directories
   - Descriptive file names

4. **Production vs Development**
   - **`scripts/`** - Production operations
   - **`utilities/`** - Development tools
   - **`diagnostics/`** - Troubleshooting
   - **`archive/`** - Historical (do not run)

---

## Adding New Files

### New API Endpoint
➜ Add to `src/api/main.py`

### New Business Logic
➜ Create in `src/core/` (e.g., `src/core/playoff_service.py`)

### New Database Model
➜ Add to `src/models/models.py`

### New API Schema
➜ Add to `src/models/schemas.py`

### New Operational Script
➜ Create in `scripts/` (e.g., `scripts/import_playoffs.py`)

### New Diagnostic Tool
➜ Create in `diagnostics/` (e.g., `diagnostics/debug_playoffs.py`)

### New Migration
➜ Create in `migrations/` (e.g., `migrations/migrate_add_playoff_rounds.py`)

### New Frontend Page
➜ Create in `frontend/` (HTML + JS in `frontend/js/`)

### New Test
➜ Create in appropriate `tests/` subdirectory (unit/integration/e2e)

---

## Summary

**Application Code:** `src/` (api, core, models, integrations)
**Frontend:** `frontend/` (HTML, CSS, JS)
**Operations:** `scripts/` (production automation)
**Development:** `utilities/` + `diagnostics/` + `archive/`
**Data:** `cfb_rankings.db` (SQLite)
**Tests:** `tests/` (unit, integration, e2e)
**Docs:** `docs/` (architecture, stories, PRD)
