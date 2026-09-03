# College Football Ranking System - Architecture

## Introduction

This document captures the **CURRENT STATE** of the College Football Ranking System
("Stat-urday Synthesis") codebase. It is a reference for developers and AI agents
working on the system: actual structure, algorithms, constraints, and known debt.

### Change Log

| Date       | Version | Description                                                        | Author  |
|------------|---------|--------------------------------------------------------------------|---------|
| 2025-10-06 | 1.0     | Initial brownfield analysis                                        | Winston |
| 2026-09-02 | 2.0     | Rewrite against actual `src/` layout; v1.0 described a monolith that no longer exists | Claude  |

> [!warning] If you have read v1.0 of this document
> Version 1.0 described a flat root-level monolith (`main.py` holding every
> endpoint, `ranking_service.py` at 363 lines, `frontend/js/app.js`,
> `frontend/teams.html`) and claimed 0% test coverage. None of that is true
> today. The backend moved into `src/`, and the suite is 922 tests. The stale
> version is preserved at `docs/archive/architecture-2025-10-06-stale.md`.

---

## Quick Reference - Key Files and Entry Points

**Entry point:**
- `main.py` - 15-line shim re-exporting `src.api.main:app` so
  `gunicorn -c gunicorn_config.py main:app` resolves from the project root.
- `src/api/main.py` - builds the FastAPI app, CORS, static mount, router wiring
  (`src/api/main.py:98`).

**Backend core:**
- `src/core/ranking_service.py` - the ELO engine and the bulk of the business
  logic (~1,900 lines). This is the product.
- `src/models/models.py` - 11 SQLAlchemy tables.
- `src/models/schemas.py` - Pydantic request/response models.
- `src/models/database.py` - engine, `SessionLocal`, `get_db()` dependency.
- `src/api/routers/*.py` - seven per-domain route modules.

**Data integration:**
- `src/integrations/cfbd_client.py` - CollegeFootballData API client.
- `src/importers/pipeline.py` - import orchestration; `games.py`, `teams.py`,
  `polls.py`, `efficiency.py`, `postseason.py` are the workers.
- `scripts/weekly_update.py` - the production weekly cadence.

**Frontend** (static, vanilla JS, no build step):
- `frontend/index.html` + `frontend/js/board.js` - rankings board.
- `frontend/js/api.js` - fetch wrapper, base URL `/api`.

**Deployment:**
- `gunicorn_config.py`, `deploy/cfb-rankings.service`, `deploy/nginx.conf`,
  `deploy/setup.sh`, `deploy/deploy.sh`,
  `deploy/cfb-weekly-update.{service,timer}`.

---

## High Level Architecture

### System Context

```
CollegeFootballData API ─┐
                         │ HTTPS (import scripts, weekly timer)
                         ▼
                  ┌──────────────┐
   Browser ──────▶│    Nginx     │  static /frontend, proxy /api
                  └──────┬───────┘
                         │ 127.0.0.1:8000
                  ┌──────▼─────────────────────────┐
                  │ Gunicorn + Uvicorn workers     │
                  │  src/api/main.py  (FastAPI)    │
                  │    └─ src/api/routers/*.py     │
                  │  src/core/*.py   (services)    │
                  │  src/models/*.py (SQLAlchemy)  │
                  └──────┬─────────────────────────┘
                         │
                  ┌──────▼───────┐
                  │ cfb_rankings │  SQLite, single-writer
                  │     .db      │
                  └──────────────┘
```

### Actual Tech Stack

| Category          | Technology                   | Version   | Notes                                     |
|-------------------|------------------------------|-----------|-------------------------------------------|
| Backend runtime   | Python                       | 3.11+     | CI runs 3.11; local venv is 3.12          |
| Framework         | FastAPI                      | 0.125.0   | pinned in `requirements.txt`              |
| ASGI              | Uvicorn                      | 0.24.0    | `uvicorn[standard]`                       |
| ASGI toolkit      | Starlette                    | 0.50.0    | pinned explicitly to match FastAPI        |
| Database          | SQLite                       | 3.x       | `DATABASE_URL` env can point at Postgres  |
| ORM               | SQLAlchemy                   | 2.0.23    |                                            |
| Validation        | Pydantic                     | 2.5.0     |                                            |
| Process manager   | Gunicorn                     | 21.2.0    | `requirements-prod.txt` only              |
| Web server        | Nginx                        | latest    | reverse proxy + static                    |
| Service manager   | systemd                      | system    | app service + weekly-update timer         |
| TLS               | Let's Encrypt / Certbot      | latest    |                                            |
| Frontend          | Vanilla JS (ES6+), HTML, CSS | native    | no bundler, no JS package manager         |
| Charts            | Chart.js (CDN)               | -         | only on `team`, `comparison`, `matchup`   |
| Tests             | pytest, Playwright           | -         | 922 collected tests                       |
| External data     | CollegeFootballData.com API  | free tier | Bearer token via `CFBD_API_KEY`           |

---

## Source Tree

```
/
├── main.py                       # gunicorn/uvicorn shim -> src.api.main:app
├── gunicorn_config.py
├── Makefile                      # test targets
├── pytest.ini, .coveragerc, .flake8, pyproject.toml
├── requirements{,-dev,-prod}.txt
├── cfb_rankings.db               # SQLite, gitignored
│
├── src/
│   ├── api/
│   │   ├── main.py               # FastAPI app construction + router wiring
│   │   └── routers/
│   │       ├── meta.py           # 3 routes  - health, /api/stats, /api/calculate
│   │       ├── teams.py          # 11 routes - teams, schedule, players, matchup
│   │       ├── games.py          # 3 routes
│   │       ├── predictions.py    # 6 routes
│   │       ├── rankings.py       # 7 routes  - rankings, postseason, playoff projection
│   │       ├── seasons.py        # 5 routes
│   │       └── admin.py          # 13 routes - imports, config, API usage, manual updates
│   ├── core/
│   │   ├── ranking_service.py    # ELO engine, predictions, CFP bracket
│   │   ├── season_simulation.py  # Monte Carlo season sim
│   │   ├── position_service.py   # roster-based position strength
│   │   ├── position_weights.json
│   │   ├── production_service.py # returning production
│   │   ├── transfer_portal_service.py
│   │   └── ap_poll_service.py
│   ├── importers/
│   │   ├── pipeline.py           # orchestration
│   │   ├── games.py, teams.py, polls.py, efficiency.py, postseason.py
│   │   ├── common.py, validation.py
│   ├── integrations/
│   │   └── cfbd_client.py
│   └── models/
│       ├── models.py             # 11 ORM tables
│       ├── schemas.py            # Pydantic
│       └── database.py           # engine, SessionLocal, get_db, init_db, reset_db
│
├── frontend/                     # index, team, games, comparison, matchup,
│   ├── css/ js/ images/ data/    # simulator, elo-formula, admin  (8 pages)
│
├── tests/                        # 922 tests: unit/, integration/, e2e/, frontend/
│   ├── conftest.py, factories.py
│
├── migrations/                   # hand-rolled .sql + one-off python scripts
├── scripts/                      # operational runbook tooling (weekly_update.py et al)
├── utilities/                    # season lifecycle + data-import tooling
├── deploy/                       # systemd units, nginx, setup/deploy scripts
└── docs/                         # this doc, architecture/, epics, archive/
```

### `scripts/` vs `utilities/`

Both hold live runbook tooling; the split is historical rather than principled.
Rough division: `scripts/` is in-season cadence (weekly updates, prediction
generation, backfills), `utilities/` is season lifecycle and bulk data work
(archive, finalize, validate, roster/player imports). Neither is dead code —
check before deleting.

---

## Data Models

All models live in `src/models/models.py`.

| Model              | Table                 | Line  | Purpose                                              |
|--------------------|-----------------------|-------|------------------------------------------------------|
| `Team`             | `teams`               | 75    | Identity, conference, preseason factors, ELO, record |
| `Player`           | `players`             | 167   | Player identity and production metrics               |
| `RosterPlayer`     | `roster_players`      | 236   | Season roster rows feeding position strength         |
| `Game`             | `games`               | 294   | Scores, quarter scores, week/season, rating deltas   |
| `RankingHistory`   | `ranking_history`     | 454   | Weekly rank/rating/SOS snapshots                     |
| `Season`           | `seasons`             | 521   | Year, current week, active flag                      |
| `APIUsage`         | `api_usage`           | 562   | CFBD call accounting against the free-tier cap       |
| `UpdateTask`       | `update_tasks`        | 610   | Async/manual update job tracking                     |
| `Prediction`       | `predictions`         | 659   | Stored predictions and accuracy evaluation           |
| `APPollRanking`    | `ap_poll_rankings`    | 707   | AP poll for the comparison view                      |
| `PlayoffSimulation`| `playoff_simulation`  | 754   | Cached Monte Carlo playoff projection                |

`ConferenceType` (`models.py:54`) is the P5/G5/FCS enum used by the conference
multiplier.

### Schema migrations

There is **no Alembic**, despite docstrings in `src/models/database.py`
suggesting it. `migrations/` holds raw `.sql` files and one-off
`migrate_add_*.py` scripts, applied by hand. `init_db()` runs
`Base.metadata.create_all()` on startup, which creates missing *tables* but
never alters existing ones — a new column on an existing table needs a
migration script.

---

## The Ranking Engine

`src/core/ranking_service.py` is where the actual value lives. Reading order:

**Season start:**
- `calculate_preseason_rating()` (`:366`) - where a team's season begins.
- `_calculate_preseason_bonuses()` (`:301`) - recruiting, transfer portal,
  returning production.
- `_calculate_position_strength_bonus()` (`:429`) - roster-derived adjustment.
- `_get_previous_season_elo()` (`:516`) - carryover regression toward the mean.

**In-season updates:**
- `process_game()` (`:775`) - the core ELO update loop.
- `get_k_factor()` (`:275`) - K decays as the season progresses.
- `calculate_expected_score()` (`:635`) - win probability.
- `calculate_mov_multiplier()` (`:649`) and
  `calculate_quarter_weighted_mov()` (`:665`) - margin-of-victory weighting.
- `get_conference_multiplier()` (`:747`) - P5/G5/FCS matchup adjustment.
- `calculate_sos()` (`:967`), `get_current_rankings()` (`:1009`),
  `save_weekly_rankings()` (`:1071`).

**Efficiency blend** (module-level, above the class):
- `net_ppa()` (`:75`), `efficiency_scale()` (`:82`), `efficiency_rating()` (`:120`),
  `blend_rating()` (`:139`), `effective_rating()` (`:172`) - blends raw ELO with
  opponent-adjusted efficiency into the rating actually displayed.

**Predictions:**
- `generate_predictions()` (`:1247`) -> `_calculate_game_prediction()` (`:1406`)
- `create_and_store_prediction()` (`:1664`),
  `evaluate_prediction_accuracy()` (`:1732`),
  `get_overall_prediction_accuracy()` (`:1771`)

**Postseason:**
- `conference_sizes()` (`:1536`), `top_rated_champions()` (`:1546`),
  `select_cfp_field()` (`:1566`), `run_bracket()` (`:1600`),
  `project_playoff_bracket()` (`:1635`)

The matching tests in `tests/unit/test_ranking_service.py` are the most reliable
documentation of intended behavior.

### Slate ordering

`GET /api/predictions` returns a slate in scoreboard order — **kickoff time
ascending, then the visiting team's name A–Z**, with `Game.id` as a stability
tiebreak. This mirrors how Apple Sports and ESPN present a day's games.

The ordering is applied in SQL, in both code paths that can serve the endpoint:

- stored predictions — `src/api/routers/predictions.py:78`
- on-the-fly generation — `src/core/ranking_service.py:1297`

Both join `Team` on `Game.away_team_id` explicitly, since `Game` carries two
foreign keys to `teams`. Ordering must stay in SQL rather than moving to a Python
sort: `Game.game_date` is nullable (undated future schedules), and SQLite orders
NULLs first without raising, where a Python `sort()` would raise `TypeError` on
the first `None`.

The frontend does not re-sort — `renderPredictions()` in `frontend/js/board.js`
renders API order directly. An earlier frontend sort by team rating (EPIC-020)
was dropped during the board redesign, so ordering is now purely a backend
concern.

Covered by `tests/integration/test_predictions_api.py::TestPredictionSlateOrdering`,
which exercises both paths.

---

## API

Routers are registered with no prefix (`src/api/main.py:98`); each decorator
declares its full path, so URLs are unchanged from the pre-`src/` layout.

| Prefix                 | Router          | Routes | Notes                                          |
|------------------------|-----------------|--------|------------------------------------------------|
| `/`, `/api/stats`, `/api/calculate` | `meta.py`      | 3  | Health, system stats, full recalculation       |
| `/api/teams*`, `/api/matchup`       | `teams.py`     | 11 | Detail, schedule, players, position strength, ELO history |
| `/api/games*`          | `games.py`      | 3      | POST auto-processes the game                   |
| `/api/predictions*`    | `predictions.py`| 6      | Slate predictions and accuracy                 |
| `/api/rankings*`, `/api/postseason`, `/api/playoff-projection` | `rankings.py` | 7 | Current, historical, weeks, CFP projection |
| `/api/seasons*`        | `seasons.py`    | 5      | Includes destructive `/{year}/reset`           |
| `/api/admin/*`         | `admin.py`      | 13     | Imports, config, API usage, manual triggers    |

Interactive docs: `/docs` (Swagger) and `/redoc`.

---

## Technical Debt and Known Issues

### Security

**1. No authentication on any endpoint.** Verified — there is no auth dependency
anywhere in `src/api/`. Every write endpoint is open, including
`POST /api/seasons/{year}/reset` (wipes a season's ratings) and the entire
`/api/admin/*` surface. Currently mitigated only by obscurity. This is the
highest-severity item in the codebase.

**2. CORS allows all origins** (`src/api/main.py:70`). `allow_origins=["*"]`
combined with `allow_credentials=True`. The code carries its own TODO.

**3. No rate limiting.** Nothing throttles requests; an abusive client can drive
CFBD calls against the free-tier cap.

### Correctness constraints

**Game processing must be chronological.** ELO is cumulative, so games have to be
processed in date order. `src/importers/` sorts before processing; the
`POST /api/games` endpoint does **not** enforce it. Out-of-order manual inserts
silently corrupt ratings. Recovery is `utilities/reprocess_season.py`.

**`create_all()` does not alter tables.** See migrations note above.

### Performance

**SOS is recomputed per request.** `get_current_rankings()` (`:1009`) calls
`calculate_sos()` (`:967`) per team, which queries that team's games. For ~136
FBS teams that is a query fan-out on every `/api/rankings` hit. No caching layer
exists. The playoff projection is the exception — it is cached in the
`playoff_simulation` table because the Monte Carlo run is expensive.

**SQLite single-writer.** Fine at current traffic; the ceiling is concurrent
writes during an import while serving reads. `DATABASE_URL` already abstracts the
move to Postgres.

### Deployment gotchas

- `worker_class = "uvicorn.workers.UvicornWorker"` in `gunicorn_config.py` is
  mandatory — FastAPI is ASGI and will not run under default Gunicorn workers.
- `cfb_rankings.db` must be writable by `www-data`, else writes 500.
  `deploy/fix-permissions.sh` exists for this.
- Frontend assumes same-origin: `frontend/js/api.js` uses `/api` in production.
  Splitting frontend and API across domains breaks it.
- systemd does not read `.env` on its own; the service file carries
  `Environment=` lines injected by `deploy/setup.sh`.

---

## Testing Reality

922 tests, markers defined in `pytest.ini`.

```bash
make test              # unit + integration (excludes e2e) - the default gate
make test-unit         # fast
make test-integration
make test-e2e          # needs a server on port 8765
make test-fast         # parallel, -n auto
make coverage-html     # -> htmlcov/index.html
```

Layout:
- `tests/unit/` - 29 files. Algorithm behavior: ELO, preseason components,
  efficiency blend, position strength, predictions, season simulation.
- `tests/integration/` - 8 files. API contract against a real test DB.
- `tests/e2e/` - 4 files. Playwright against a live server.
- `tests/frontend/` - JS-facing checks.
- `tests/conftest.py` + `tests/factories.py` - fixtures and factory-boy builders.
  Each test gets its own database; see `tests/unit/test_db_fixture_isolation.py`.

CI: `.github/workflows/tests.yml` — Python 3.11, installs Playwright Chromium,
runs unit then integration then coverage, with E2E as a follow-on job.

---

## Local Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # add CFBD_API_KEY for real imports
uvicorn main:app --reload     # http://localhost:8000  (/docs, /frontend/index.html)
```

Weekly data refresh: `python3 scripts/weekly_update.py`. See `DEVELOPMENT.md` for
task-level walkthroughs and `docs/architecture/coding-standards.md` for style.

---

## Deployment

Production is a VPS at `/var/www/cfb-rankings` running as `www-data`.

```bash
sudo bash deploy/setup.sh     # first-time: deps, venv, nginx, systemd, certbot
sudo bash deploy/deploy.sh    # updates: git pull, pip install, restart

sudo systemctl status cfb-rankings
journalctl -u cfb-rankings -f
sudo systemctl list-timers cfb-weekly-update.timer
```

`deploy/cfb-weekly-update.timer` drives the automated in-season data refresh.
`deploy/logrotate-cfb-rankings` handles log rotation; `deploy/clear-cache.sh`
clears cached artifacts after a data correction.

---

## Appendix - Database Spot Checks

```bash
sqlite3 cfb_rankings.db
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM games WHERE is_processed = 1;
SELECT name, elo_rating, wins, losses FROM teams ORDER BY elo_rating DESC LIMIT 25;

cp cfb_rankings.db "cfb_rankings_backup_$(date +%Y%m%d).db"
```

---

**Version**: 2.0 · **Date**: 2026-09-02 · **Status**: verified against the tree at
commit `eea902b`
