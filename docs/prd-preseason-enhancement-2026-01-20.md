# Stat-urday Synthesis - Preseason Ranking Enhancement with Player Position Metrics

**Product Requirements Document**
**Version**: 1.0
**Date**: 2026-01-20
**Author**: John (Product Manager)
**Status**: Complete - Ready for Review

---

## 1. Intro Project Analysis and Context

### 1.1 Analysis Source

**IDE-based fresh analysis** combined with existing architecture documentation (`docs/architecture.md`)

### 1.2 Existing Project Overview

#### Current Project State

The **Stat-urday Synthesis** project is a comprehensive College Football Ranking System that calculates and displays alternative rankings using a Modified ELO algorithm. The system currently:

- Calculates preseason ratings using three factors:
  - **Recruiting rankings** (247Sports data from CollegeFootballData API)
  - **Transfer portal rankings** (transfer portal impact)
  - **Returning production** (percentage of returning players)
- Processes game results to update ELO ratings throughout the season
- Provides REST API and responsive frontend for rankings display
- Supports full season cycle including playoff games (weeks 1-20)
- Tracks prediction accuracy and compares with AP Poll rankings
- Uses FastAPI backend with SQLAlchemy ORM and SQLite database
- Deployed on VPS with Nginx + Gunicorn production setup

**Current Preseason Rating Calculation** (from `ranking_service.py`):
- Base rating: 1500
- Recruiting bonus: Top 10 (+100-250), Top 25 (+50-99), Top 50 (+25-49)
- Transfer ranking bonus: Top 10 (+50-100), Top 25 (+25-49)
- Returning production bonus: Based on percentage (0-100 points)
- Maximum preseason rating achievable: ~1850

The system has completed **26+ epics** with comprehensive test coverage (124 tests) and is actively tracking the 2024-2025 season.

### 1.3 Available Documentation Analysis

#### Available Documentation

- ✅ **Tech Stack Documentation** - Comprehensive in `docs/architecture.md`
- ✅ **Source Tree/Architecture** - Documented with module organization
- ⚠️ **Coding Standards** - Partially documented (PEP 8 compliance noted)
- ✅ **API Documentation** - Auto-generated via FastAPI Swagger UI
- ✅ **External API Documentation** - CFBD client documented
- ❌ **UX/UI Guidelines** - Not formalized
- ✅ **Technical Debt Documentation** - Captured in architecture.md
- ✅ **Epic/Story Documentation** - Extensive: 26+ epics in docs/

**Documentation Status:** Strong technical foundation with comprehensive architecture documentation. Recent codebase cleanup epic (EPIC-028) reorganized project into modern Python structure with `src/` organization.

### 1.4 Enhancement Scope Definition

#### Enhancement Type
- ✅ **New Feature Addition** - Adding player position ranking data
- ✅ **Major Feature Modification** - Enhancing preseason rating algorithm
- ✅ **Integration with New Systems** - New data source for player metrics

#### Enhancement Description

This enhancement will improve preseason ranking accuracy by incorporating **player-level position rankings** into the preseason rating calculation. Currently, the system uses team-level metrics (recruiting class ranking, transfer portal ranking, returning production percentage). Adding individual player position rankings will provide more granular insight into team strength, particularly for key positions (QB, OL, DL, secondary) that disproportionately impact team performance.

#### Impact Assessment
- ✅ **Significant Impact** - Requires new data models, API integration, algorithm modifications, and calculation logic changes

### 1.5 Goals and Background Context

#### Goals

- Improve preseason ranking accuracy by incorporating player-level position data
- Add new data source for individual player position rankings
- Enhance preseason rating algorithm to weight key positions appropriately
- Maintain backward compatibility with existing preseason calculation
- Provide transparency into how player rankings influence team preseason ratings
- Enable future analysis of position group impact on team success

#### Background Context

The current preseason rating system uses three team-level aggregate metrics: recruiting class rank, transfer portal rank, and returning production percentage. While these provide a reasonable starting point, they treat all players equally and don't account for positional importance.

For example, a team with the #1 recruiting class might have elite offensive linemen but average quarterbacks, while another team might have an elite quarterback but average supporting cast. The current system doesn't distinguish between these scenarios, potentially leading to inaccurate preseason rankings.

Research in football analytics consistently shows that certain positions (particularly quarterback, offensive line, defensive line, and secondary) have outsized impact on team success. By incorporating individual player position rankings, the system can:

1. **Better predict team strength** - Weight critical positions more heavily
2. **Capture transfer portal impact** - Track specific position upgrades/losses
3. **Account for roster composition** - Distinguish between star-heavy vs balanced rosters
4. **Enable position-specific analysis** - Identify correlation between position strength and team success

This enhancement aligns with the system's goal of providing more accurate alternative rankings to traditional polls while maintaining transparency in the calculation methodology.

### 1.6 Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial | 2026-01-20 | 1.0 | Initial PRD creation for preseason enhancement | John (PM) |

---

## 2. Requirements

### 2.1 Functional Requirements

**FR1:** The system shall fetch player-level recruiting rankings from the CollegeFootballData API `/recruiting/players` endpoint, capturing: `athleteId`, `name`, `position`, `stars`, `rating`, `ranking`, `committedTo`, and `year`.

**FR2:** The system shall store player recruiting data in a new `Player` database model with fields: player_id, cfbd_athlete_id, name, team_id, position, stars (1-5 star rating), rating (numerical score), ranking (overall rank), recruiting_year.

**FR3:** The system shall create a new `PositionGroup` enumeration defining major position groups: QB (Quarterback), OL (Offensive Line), RB (Running Back), WR (Wide Receiver), TE (Tight End), DL (Defensive Line), LB (Linebacker), DB (Defensive Back), ST (Special Teams).

**FR4:** The preseason rating calculation shall incorporate a new "Position Strength Bonus" component that evaluates team strength across key position groups based on player rankings within each position.

**FR5:** The Position Strength Bonus shall apply configurable weights to different position groups, with higher weights for positions with greater impact on team success (suggested initial weights: QB=0.30, OL=0.25, DL=0.20, DB=0.15, LB=0.05, RB=0.025, WR=0.025).

**FR6:** The system shall calculate position group strength scores by aggregating player rankings within each position group for a team (e.g., average rating of top 3 QBs, top 5 OL, etc.).

**FR7:** The Position Strength Bonus shall contribute a maximum of 150 points to a team's preseason rating, added to the existing recruiting bonus (max 250), transfer bonus (max 100), and returning production bonus (max 100), for a new maximum preseason rating of ~2000.

**FR8:** The system shall maintain backward compatibility by preserving all existing preseason factors (team recruiting rank, transfer rank, returning production) as independent components in the calculation.

**FR9:** The API shall provide a new endpoint `/api/teams/{id}/players` to retrieve player roster data with positions and recruiting rankings for a specific team.

**FR10:** The API shall provide a new endpoint `/api/teams/{id}/position-strength` to retrieve calculated position group strength scores and overall position strength bonus for a team's preseason rating.

**FR11:** The frontend team detail page shall display position group strength breakdown in the preseason factors section, showing strength scores for each major position group.

**FR12:** The system shall provide an admin utility script (`utilities/import_player_data.py`) to import historical player recruiting data for previous seasons to enable analysis and weight optimization.

**FR13:** The system shall log and track API calls to player-level endpoints separately from team-level endpoints to monitor API quota usage given the increased number of requests.

### 2.2 Non-Functional Requirements

**NFR1:** The enhancement shall maintain existing preseason rating calculation performance, with player position data import completing within 5 minutes for a full season (133 FBS teams × ~85 scholarship players = ~11,305 players maximum).

**NFR2:** Position weight configuration shall be externalized to a configuration file (`src/core/position_weights.json`) to enable tuning without code changes.

**NFR3:** The system shall handle missing player data gracefully, falling back to team-level recruiting rank if position-specific player data is unavailable for a team.

**NFR4:** Player data import shall be idempotent, allowing re-import of the same season without creating duplicate player records (upsert based on cfbd_athlete_id + recruiting_year).

**NFR5:** The enhancement shall not increase database size by more than 50% (player table estimated at ~500KB per season based on 11,305 players × ~50 bytes per record).

**NFR6:** Position strength calculations shall be cached during preseason rating calculation to avoid redundant database queries (calculate once per team, reuse in multiple contexts).

**NFR7:** The system shall provide clear logging during player data import showing progress (e.g., "Imported 85/133 teams") and error handling for teams with missing data.

**NFR8:** API quota impact shall be documented and monitored, with estimated 133 additional API calls per season for player data import (one call per team to `/recruiting/players` endpoint).

### 2.3 Compatibility Requirements

**CR1: Existing Preseason Calculation Compatibility** - The existing preseason rating components (recruiting rank bonus, transfer rank bonus, returning production bonus) shall continue to function identically. The Position Strength Bonus is purely additive and optional. Teams without player data shall still receive preseason ratings based on existing factors.

**CR2: Database Schema Compatibility** - A new `players` table will be added to store player data. All existing tables (teams, games, ranking_history, seasons) remain unchanged. No modifications to existing columns or relationships are required.

**CR3: API Backward Compatibility** - All existing API endpoints shall remain unchanged in request/response structure. New endpoints (`/api/teams/{id}/players`, `/api/teams/{id}/position-strength`) are additive only. Existing `/api/teams/{id}` response may optionally include new fields in a backward-compatible manner (e.g., `position_strength_bonus` added to preseason factors object).

**CR4: Frontend Consistency** - The frontend team detail page shall display position strength as an additional section in the existing preseason factors card, following the same visual design patterns (card layout, color scheme, typography) used for recruiting, transfers, and returning production.

**CR5: Import Script Compatibility** - The existing `import_real_data.py` script shall continue to work without modification. Player data import shall be a separate optional step (`utilities/import_player_data.py`) or an optional flag in the existing import workflow (e.g., `--include-players`).

**CR6: ELO Calculation Compatibility** - The ELO rating updates during season (game processing, margin of victory, strength of schedule) shall remain completely unchanged. Only the initial preseason rating calculation is affected by this enhancement.

---

## 3. Technical Constraints and Integration Requirements

### 3.1 Existing Technology Stack

**Languages**: Python 3.11+ (required for FastAPI and modern type hints)

**Frameworks**:
- FastAPI 0.104.1 (Backend REST API framework)
- SQLAlchemy 2.0.23 (ORM with declarative models)
- Pydantic 2.5.0 (Request/response validation)

**Database**: SQLite 3.x (file-based: `cfb_rankings.db`, migration-ready for PostgreSQL)

**Infrastructure**:
- **Production Server**: Gunicorn 21.2.0 + Uvicorn 0.24.0 workers (4 workers)
- **Web Server**: Nginx (reverse proxy `/api/*` → localhost:8000, static files `/frontend/*`)
- **Process Manager**: systemd (auto-restart, logging)
- **SSL/TLS**: Let's Encrypt via Certbot (auto-renewal)
- **Deployment**: VPS-based with subdomain support

**External Dependencies**:
- CollegeFootballData.com API (30,000 req/month tier, requires CFBD_API_KEY)
- Requests 2.31.0+ (HTTP client for external API)
- python-dotenv 1.0.0 (environment variable management)

**Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 (no frameworks, no build process)

**Testing**: pytest, pytest-cov, Playwright (124 tests: unit, integration, E2E)

**Code Organization** (Post-EPIC-028 Cleanup):
```
src/
├── api/main.py              # FastAPI endpoints
├── core/
│   ├── ranking_service.py   # ELO algorithm & preseason calculation
│   └── ap_poll_service.py   # AP Poll comparison
├── models/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic schemas
│   └── database.py          # DB connection
└── integrations/
    └── cfbd_client.py       # CFBD API client
```

### 3.2 Integration Approach

#### Database Integration Strategy

**New Player Model Addition:**
- Add `Player` model to `src/models/models.py` with fields: id, cfbd_athlete_id, name, team_id (FK to teams.id), position, stars, rating, ranking, recruiting_year, created_at
- Add relationship: `Team.players = relationship("Player", back_populates="team")`
- **No modifications to existing models** - purely additive
- Migration script: `migrations/migrate_add_player_table.py` creates new table
- Database remains SQLite (no migration to PostgreSQL required for this enhancement)

**Position Strength Calculation:**
- Position group strengths calculated dynamically during preseason rating, not stored permanently
- May add optional `position_strength_bonus` column to Team model for caching (future optimization)
- Player queries optimized with indexes: `CREATE INDEX idx_players_team_position ON players(team_id, position)`

#### API Integration Strategy

**New CFBD Endpoint Integration:**
- Add `get_recruiting_players(year: int, team: Optional[str] = None)` method to `CFBDClient` class in `src/integrations/cfbd_client.py`
- Endpoint: `/recruiting/players` with params `{year: 2024, team: "Georgia"}`
- Response parsing to extract: player name, position, rating, rank, stars
- API call tracking via existing `@track_api_usage` decorator
- Estimated 133 additional API calls per season import (one per FBS team)

**CFBD API Endpoint Confirmed:**
- **Path:** `GET /recruiting/players`
- **Parameters:** year (int), team (string, optional), position (string, optional), classification (string, default: "HighSchool")
- **Response:** Array of Recruit objects with fields: id, athleteId, name, position, stars, rating, ranking, committedTo, year
- **Source:** [CFBD Swagger Specification](https://github.com/CFBD/cfb-api/blob/main/swagger.json)

**Backend API Endpoints (New):**
- `GET /api/teams/{id}/players` - Returns player roster with recruiting data
  - Response schema: `TeamPlayersResponse` (Pydantic model)
  - Paginated: query params `?limit=50&offset=0`
  - Filter by position: `?position=QB`
- `GET /api/teams/{id}/position-strength` - Returns position group strength breakdown
  - Response schema: `PositionStrengthResponse` with scores per position group
  - Includes overall position_strength_bonus value

**Existing API Modifications (Backward Compatible):**
- `GET /api/teams/{id}` response may optionally add `position_strength_bonus` field to preseason factors object
- No changes to request parameters or existing response fields
- Uses Pydantic schema evolution: add optional field with default value

#### Frontend Integration Strategy

**Team Detail Page Enhancement:**
- Modify `frontend/team.html` and `frontend/js/team.js`
- Add new section "Position Group Strength" below existing preseason factors card
- Display position groups with strength scores as horizontal bar chart or styled cards
- Use existing Chart.js library (already loaded for ranking history chart)
- Follow existing design patterns: card-based layout, gradient backgrounds, responsive grid

**API Client Updates:**
- Add methods to `frontend/js/api.js`:
  - `getTeamPlayers(teamId, position)` - Fetch player roster
  - `getPositionStrength(teamId)` - Fetch position strength data
- Error handling follows existing pattern (display error message in card)

**Styling:**
- Reuse existing CSS classes from `frontend/css/style.css`
- New classes for position strength visualization: `.position-strength-card`, `.position-bar`, `.position-label`
- Mobile responsive: position cards stack vertically on small screens

#### Testing Integration Strategy

**Unit Tests (New):**
- `tests/unit/test_player_model.py` - Player model and relationships
- `tests/unit/test_position_strength.py` - Position strength calculation logic
- `tests/unit/test_cfbd_player_api.py` - Mock CFBD player endpoint responses

**Integration Tests (Modify Existing):**
- `tests/integration/test_preseason_calculation.py` - Update to include position strength scenarios
- Add test cases: team with player data, team without player data (fallback), mixed scenarios

**E2E Tests (Update):**
- `tests/e2e/test_team_detail_page.py` - Verify position strength section renders
- Test player data visibility on frontend

**Test Data:**
- Create fixtures in `tests/factories.py`: `PlayerFactory` for generating test player records
- Mock CFBD player responses in `tests/mocks/cfbd_player_data.json`

### 3.3 Code Organization and Standards

#### File Structure Approach

**New Files to Create:**
```
src/
├── models/
│   └── models.py            # ADD: Player model (existing file, add to it)
│
├── core/
│   ├── position_weights.json     # NEW: Position weight configuration
│   └── position_service.py       # NEW: Position strength calculation logic
│
utilities/
└── import_player_data.py    # NEW: Player data import script

migrations/
└── migrate_add_player_table.py   # NEW: Database migration

tests/
├── unit/
│   ├── test_player_model.py      # NEW
│   ├── test_position_strength.py # NEW
│   └── test_cfbd_player_api.py   # NEW
└── factories.py              # MODIFY: Add PlayerFactory
```

**Files to Modify:**
```
src/integrations/cfbd_client.py   # ADD: get_recruiting_players() method
src/core/ranking_service.py       # MODIFY: calculate_preseason_rating() to include position bonus
src/api/main.py                   # ADD: New endpoints /api/teams/{id}/players, /position-strength
frontend/team.html                # ADD: Position strength section
frontend/js/team.js               # ADD: Position strength rendering logic
frontend/js/api.js                # ADD: API methods for player data
```

#### Naming Conventions

**Follow Existing Standards:**
- Files: `snake_case.py` (e.g., `position_service.py`)
- Classes: `PascalCase` (e.g., `Player`, `PositionStrengthResponse`)
- Functions/Variables: `snake_case` (e.g., `calculate_position_strength()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `POSITION_WEIGHTS`)
- Private methods: `_leading_underscore` (e.g., `_aggregate_position_scores()`)

**Database Naming:**
- Table: `players` (lowercase, plural)
- Columns: `snake_case` (e.g., `recruiting_rank`, `cfbd_athlete_id`)
- Foreign keys: `{table}_id` format (e.g., `team_id`)

#### Coding Standards

**PEP 8 Compliance:**
- Line length: 100 characters (per project standard from EPIC-028)
- Type hints for all new functions (Python 3.11+ syntax)
- Docstrings: Google style (consistent with existing codebase)

**Example New Function:**
```python
def calculate_position_strength(
    team_id: int,
    position_weights: Dict[str, float],
    db: Session
) -> float:
    """Calculate position strength bonus for a team's preseason rating.

    Args:
        team_id: Database ID of the team
        position_weights: Dictionary mapping position group to weight (0.0-1.0)
        db: SQLAlchemy database session

    Returns:
        float: Position strength bonus (0-150 points)

    Raises:
        ValueError: If position_weights don't sum to 1.0

    Example:
        >>> weights = {"QB": 0.30, "OL": 0.25, "DL": 0.20, ...}
        >>> bonus = calculate_position_strength(team_id=5, position_weights=weights, db=session)
        >>> print(f"Position bonus: {bonus}")
        Position bonus: 125.5
    """
```

#### Documentation Standards

**Module Docstrings:**
- All new Python files require module-level docstring explaining purpose
- Include usage example for complex modules

**Inline Comments:**
- Explain "why" for non-obvious logic (e.g., why QB weighted 30%)
- Document magic numbers (e.g., `MAX_POSITION_BONUS = 150  # ~10% of base rating`)

**API Documentation:**
- FastAPI auto-generates OpenAPI docs at `/docs`
- Ensure Pydantic schemas include field descriptions
- Add response examples to endpoint docstrings

### 3.4 Deployment and Operations

#### Build Process Integration

**No Build Changes Required:**
- Python application runs directly (no compilation)
- No new runtime dependencies (uses existing requests, SQLAlchemy, FastAPI)

**Database Migration:**
- Run migration script before deployment: `python migrations/migrate_add_player_table.py`
- Migration is idempotent (safe to re-run)
- No downtime required (new table doesn't affect existing functionality)

**Configuration Update:**
- Add `position_weights.json` to deployment package
- No changes to `.env` file (uses existing CFBD_API_KEY)

#### Deployment Strategy

**Standard Deployment Process (Unchanged):**
1. SSH to VPS: `/var/www/cfb-rankings/`
2. Run: `sudo bash deploy/deploy.sh`
3. Script performs:
   - Git pull latest changes
   - Activate virtual environment
   - Install dependencies (if requirements.txt changed)
   - Run database migration (NEW: check for migration scripts)
   - Restart Gunicorn service
   - Reload Nginx config

**Migration Step Addition:**
```bash
# Add to deploy/deploy.sh after "Install dependencies"
echo "Running database migrations..."
python migrations/migrate_add_player_table.py
```

**Rollback Plan:**
- Git revert to previous commit
- Database rollback: `DROP TABLE players;` (if needed)
- Restart service

#### Monitoring and Logging

**API Usage Monitoring:**
- Existing `APIUsage` table tracks all CFBD calls
- Monitor for increased API usage after player import
- Alert if monthly usage exceeds 80% (24,000 / 30,000 calls)

**Application Logging:**
- Add logging to position strength calculation:
  - INFO: "Calculating position strength for team {team_name}"
  - DEBUG: "Position QB: score=85.5, weight=0.30, contribution=25.65"
  - WARNING: "No player data for team {team_name}, using fallback"
- Logs captured by systemd: `journalctl -u cfb-rankings -f`

**Performance Monitoring:**
- Track preseason calculation time (should remain under 10 seconds for full season)
- Monitor database query count (ensure position queries are optimized)

#### Configuration Management

**New Configuration File:**
- `src/core/position_weights.json`:
```json
{
  "version": "1.0",
  "enabled": false,
  "weights": {
    "QB": 0.30,
    "OL": 0.25,
    "DL": 0.20,
    "DB": 0.15,
    "LB": 0.05,
    "RB": 0.025,
    "WR": 0.025
  },
  "max_bonus": 150,
  "top_players_per_position": {
    "QB": 3,
    "OL": 5,
    "DL": 5,
    "DB": 4,
    "LB": 3,
    "RB": 2,
    "WR": 3
  }
}
```

**Configuration Loading:**
- Load at application startup (cached in memory)
- Hot-reload not required (restart service to apply changes)
- Validation: ensure weights sum to 1.0, all positions defined

### 3.5 Risk Assessment and Mitigation

#### Technical Risks

**1. CFBD Player Endpoint May Not Exist or Have Different Structure (HIGH Likelihood, HIGH Impact)**
- **Risk**: Assumption that `/recruiting/players` endpoint exists and provides needed data
- **Mitigation**:
  - ✅ **CONFIRMED**: Endpoint exists at `GET /recruiting/players` with documented response structure
  - Verified via [CFBD Swagger Specification](https://github.com/CFBD/cfb-api/blob/main/swagger.json)
  - Response includes: athleteId, name, position, stars, rating, ranking, committedTo, year
  - Have fallback plan: if data incomplete, use existing team-level data only
- **Rollback**: Remove player integration, revert to existing team-level preseason calculation

**2. Player Data Incomplete or Inconsistent (MEDIUM Likelihood, MEDIUM Impact)**
- **Risk**: Some teams may have incomplete player data (e.g., FCS opponents, smaller programs)
- **Mitigation**:
  - Implement graceful degradation (NFR3): fallback to team-level recruiting rank
  - Log teams with missing data for manual review
  - Don't fail preseason calculation if player data unavailable
  - Calculate position strength only for teams with sufficient data (e.g., >50% positions filled)
- **Rollback**: Disable position strength for specific teams via config flag

**3. Position Weight Optimization Unclear (MEDIUM Likelihood, MEDIUM Impact)**
- **Risk**: Initial position weights (QB=30%, OL=25%, etc.) may not correlate with actual team success
- **Mitigation**:
  - Make weights configurable (position_weights.json)
  - Import historical player data for multiple seasons
  - Run correlation analysis: position strength vs end-of-season ELO
  - Start conservatively (150 max bonus) to limit impact if weights are wrong
  - Plan for iterative tuning based on actual season results
- **Rollback**: Reduce max_bonus to 0 in config (effectively disables feature without code changes)

**4. Performance Degradation from Player Queries (LOW Likelihood, MEDIUM Impact)**
- **Risk**: Querying 11,000+ player records during preseason calculation could slow system
- **Mitigation**:
  - Add database indexes: `CREATE INDEX idx_players_team_position ON players(team_id, position)`
  - Cache position strength calculations per team
  - Optimize queries: use `db.query(Player).filter(...).all()` batch queries, not N+1 pattern
  - Profile performance with realistic data volumes before production
- **Rollback**: Remove player queries from preseason calculation, cache results offline

#### Integration Risks

**1. Frontend Display of Position Data Clutters UI (LOW Likelihood, LOW Impact)**
- **Risk**: Adding position strength section to team detail page makes it too busy
- **Mitigation**:
  - Follow existing design patterns (card-based, collapsible sections)
  - Make position strength section collapsible/expandable
  - Test UI on mobile devices to ensure readability
  - Get user feedback before finalizing design
- **Rollback**: Hide position strength section behind "Show Details" toggle

**2. API Quota Exceeded Due to Player Imports (LOW Likelihood, MEDIUM Impact)**
- **Risk**: Multiple player imports (testing, re-imports) consume API quota quickly
- **Mitigation**:
  - Track API usage before/after player import
  - Make player import optional (flag: `--import-players`)
  - Cache player data locally after first import (only re-import on demand)
  - Document API cost: ~133 calls per season import
  - Current quota: 30,000/month, so plenty of headroom
- **Rollback**: Disable automatic player import, use manual import only

#### Deployment Risks

**1. Database Migration Fails in Production (LOW Likelihood, HIGH Impact)**
- **Risk**: Migration script fails on production database due to permissions or existing data
- **Mitigation**:
  - Test migration on production database backup first
  - Make migration idempotent (check if table exists before creating)
  - Backup database before running migration: `cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d).db`
  - Migration script includes rollback instructions in comments
- **Rollback**: Restore database from backup, revert code changes

**2. Position Weights Config File Missing in Production (LOW Likelihood, LOW Impact)**
- **Risk**: `position_weights.json` not deployed, application fails to start
- **Mitigation**:
  - Include config file in git repository (not .gitignored)
  - Application checks for config file at startup, logs error if missing
  - Fallback to hardcoded default weights if config file not found
  - Document config file location in deployment guide
- **Rollback**: Use default weights embedded in code

#### Mitigation Strategies Summary

**1. Phased Rollout:**
- Phase 1: Add database model + API client (no calculation changes)
- Phase 2: Import player data for current season (test data quality)
- Phase 3: Add position strength calculation (disabled by default)
- Phase 4: Enable position strength in preseason rating (low max_bonus initially)
- Phase 5: Tune weights based on correlation analysis

**2. Feature Flags:**
- Config option: `"enable_position_strength": true/false`
- Allows disabling feature without code changes
- Gradual rollout: enable for subset of teams first

**3. Comprehensive Testing:**
- Unit tests for position calculation logic (isolated)
- Integration tests with mock player data
- E2E tests on staging environment with real CFBD data
- Performance testing with full player dataset (11K+ records)

**4. Documentation First:**
- ✅ CFBD player endpoint format documented and confirmed
- Write migration guide before running migration
- Create troubleshooting guide for common issues (missing data, API errors)

**5. Monitoring and Alerts:**
- Log player import progress and errors
- Alert if API quota exceeds 80%
- Monitor preseason calculation time (alert if >15 seconds)
- Track teams with missing player data (manual review)

---

## 4. Epic and Story Structure

### 4.1 Epic Approach

**Epic Structure Decision**: **Single Comprehensive Epic** with 6 sequenced stories

**Rationale:**

This preseason ranking enhancement should be structured as a **single comprehensive epic** because:

1. **Unified Goal**: All work shares a common objective - improving preseason ranking accuracy through player position data. This is one cohesive enhancement to the existing preseason calculation system, not multiple unrelated features.

2. **Interdependent Components**: The work has natural dependencies:
   - Database model must exist before API integration can store data
   - API client must fetch data before calculation logic can use it
   - Calculation logic must be implemented before API endpoints can expose it
   - API endpoints must work before frontend can display results
   - All components build upon each other sequentially

3. **Risk Management via Phased Rollout**: A single epic allows us to sequence stories from low-risk to high-risk:
   - Start with database foundation (no behavior changes)
   - Add data fetching capability (disabled, no calculation impact)
   - Implement calculation logic (feature-flagged off by default)
   - Expose via API (optional endpoints, no automatic use)
   - Display in UI (shows data only if available)
   - Enable configuration (opt-in activation)
   - Full test suite validation between each story

4. **Brownfield Best Practice**: For brownfield enhancements, a single epic with carefully sequenced stories ensures existing functionality remains intact throughout the process. Each story includes integration verification steps to confirm no regression.

5. **Opt-In Deployment Strategy**: The epic structure supports the requirement for opt-in enablement. Feature remains disabled by default until final story when configuration is explicitly set to enable it.

**Story Count**: 6 stories (appropriate for significant brownfield enhancement with phased rollout)

**Story Sequencing Strategy**: Foundation → Data Integration → Calculation Logic → API Exposure → UI Display → Activation, with continuous validation

---

## 5. Epic 1: Preseason Ranking Enhancement with Player Position Metrics

**Epic Goal**: Enhance the preseason rating calculation system by incorporating player-level position rankings from CollegeFootballData API, enabling more accurate team strength assessment through position-weighted analysis of roster composition—while maintaining 100% backward compatibility with existing preseason factors (recruiting rank, transfer rank, returning production) and defaulting to opt-in disabled state for safe production rollout.

**Integration Requirements**:
- All existing preseason calculation components must continue working identically
- New Player database model integrates with existing Team model via foreign key
- CFBD API client extends with new `get_recruiting_players()` method using existing patterns
- Position strength calculation is feature-flagged and disabled by default
- Zero breaking changes to existing API endpoints or response schemas
- Frontend displays position strength only when data is available
- Full test suite (124 tests) must pass after each story completion
- Database migration is idempotent and includes rollback instructions
- Configuration file enables/disables feature without code changes

---

### Story 1.1: Create Player Database Model and Migration

As a **system architect**,
I want **a new Player database model to store individual player recruiting data with positions and rankings**,
so that **the system has the foundational data structure needed to incorporate player-level metrics into preseason calculations without affecting existing team-level data**.

#### Acceptance Criteria

1. **Player model created** in `src/models/models.py` with fields:
   - `id` (Integer, PK)
   - `cfbd_athlete_id` (Integer, unique, indexed)
   - `name` (String(100))
   - `team_id` (Integer, FK to teams.id)
   - `position` (String(10)) - position abbreviation (QB, OL, DL, etc.)
   - `stars` (Integer) - star rating 1-5
   - `rating` (Float) - numerical recruiting rating
   - `ranking` (Integer) - overall recruit ranking
   - `recruiting_year` (Integer)
   - `created_at` (DateTime)

2. **Relationship added** to Team model: `players = relationship("Player", back_populates="team")`

3. **Database indexes created**:
   - `idx_players_team_position` on `(team_id, position)` for efficient position queries
   - `idx_players_recruiting_year` on `recruiting_year` for season filtering
   - Unique constraint on `cfbd_athlete_id`

4. **Migration script created**: `migrations/migrate_add_player_table.py`
   - Checks if table already exists (idempotent)
   - Creates players table with all columns and indexes
   - Includes rollback instructions in comments
   - Logs success/failure messages

5. **Migration tested** in development environment:
   - Script runs successfully on empty database
   - Script runs successfully on existing database (no-op if already migrated)
   - Rollback instructions verified

6. **Pydantic schemas created** in `src/models/schemas.py`:
   - `PlayerCreate` (for import operations)
   - `PlayerResponse` (for API responses)
   - `PlayerBase` with common fields

#### Integration Verification

- **IV1: Existing Models Unchanged** - Verify Team, Game, RankingHistory, Season models remain unchanged except for Player relationship addition
- **IV2: Existing Tests Pass** - Run full test suite (124 tests) - all must pass after migration
- **IV3: Database Integrity** - Query existing teams table, verify all data intact and relationships work
- **IV4: No Application Impact** - Start application, verify all existing endpoints work without errors

#### Rollback Considerations

- **Risk Level**: Very Low - Only adds new table, no modifications to existing data
- **Rollback Steps**:
  ```sql
  -- Remove relationship from Team model in code
  -- Drop players table
  DROP TABLE IF EXISTS players;
  ```
- **Data Loss**: None (no existing player data to lose)
- **Rollback Time**: < 1 minute

---

### Story 1.2: Add CFBD API Client Method for Player Recruiting Data

As a **data integration engineer**,
I want **a new method in CFBDClient to fetch player recruiting rankings from the CFBD API**,
so that **the system can import individual player data by team and season without impacting existing data import workflows**.

#### Acceptance Criteria

1. **New method added** to `CFBDClient` class in `src/integrations/cfbd_client.py`:
   ```python
   def get_recruiting_players(
       self,
       year: int,
       team: Optional[str] = None,
       position: Optional[str] = None,
       classification: str = "HighSchool"
   ) -> List[Dict]
   ```

2. **Method implementation**:
   - Calls `/recruiting/players` endpoint with parameters
   - Uses existing `@track_api_usage` decorator for quota monitoring
   - Returns list of player dictionaries with fields: athleteId, name, position, stars, rating, ranking, committedTo, year
   - Handles API errors gracefully (returns empty list on failure, logs error)
   - Includes docstring with usage example

3. **API response parsing** extracts relevant fields:
   - Maps `athleteId` to `cfbd_athlete_id`
   - Maps `committedTo` to team name for team_id lookup
   - Filters to HighSchool classification by default (excludes JUCO/PrepSchool)
   - Validates required fields present (name, position, committedTo)

4. **Error handling implemented**:
   - HTTP errors logged with endpoint and parameters
   - Invalid response structure handled (missing fields)
   - Empty results logged as warning (team may have no data)
   - No exceptions raised (graceful degradation)

5. **API usage tracking**:
   - Endpoint logged as `/recruiting/players` in APIUsage table
   - Response time tracked
   - Success/failure status recorded

6. **Unit tests created**: `tests/unit/test_cfbd_player_api.py`
   - Test successful API response parsing
   - Test error handling (HTTP 404, 500, timeout)
   - Test empty results handling
   - Test filtering by position
   - Mock API responses using existing patterns

#### Integration Verification

- **IV1: Existing CFBD Methods Unchanged** - Verify all existing methods (get_teams, get_games, get_recruiting_rankings, etc.) work identically
- **IV2: API Usage Tracking Works** - Verify new method calls are logged in api_usage table
- **IV3: No Import Script Impact** - Run existing `import_real_data.py`, verify it works without modification
- **IV4: Manual Test with Real API** - Call new method with test API key, verify returns expected data structure

#### Rollback Considerations

- **Risk Level**: Very Low - Only adds new method, no changes to existing methods
- **Rollback Steps**: Remove `get_recruiting_players()` method from CFBDClient class
- **Data Loss**: None (no data stored yet, only fetching capability added)
- **Rollback Time**: < 1 minute (git revert)

---

### Story 1.3: Create Position Strength Calculation Service

As a **ranking algorithm developer**,
I want **a dedicated service module that calculates position group strength scores based on player rankings**,
so that **position-weighted team strength can be computed independently from the main ranking service and feature-flagged for safe testing**.

#### Acceptance Criteria

1. **New module created**: `src/core/position_service.py` with functions:
   - `calculate_position_strength(team_id: int, weights: Dict[str, float], db: Session) -> float`
   - `get_position_group_scores(team_id: int, db: Session) -> Dict[str, float]`
   - `aggregate_player_ratings(players: List[Player], position: str) -> float`
   - `load_position_weights(config_path: str = "src/core/position_weights.json") -> Dict`

2. **Position group enumeration** defined in module:
   ```python
   POSITION_GROUPS = {
       "QB": ["QB"],
       "OL": ["OL", "OT", "OG", "C"],
       "RB": ["RB", "FB"],
       "WR": ["WR"],
       "TE": ["TE"],
       "DL": ["DL", "DT", "DE"],
       "LB": ["LB", "OLB", "ILB"],
       "DB": ["DB", "CB", "S", "FS", "SS"],
       "ST": ["K", "P", "LS"]
   }
   ```

3. **Configuration file created**: `src/core/position_weights.json`
   ```json
   {
     "version": "1.0",
     "enabled": false,
     "weights": {
       "QB": 0.30,
       "OL": 0.25,
       "DL": 0.20,
       "DB": 0.15,
       "LB": 0.05,
       "RB": 0.025,
       "WR": 0.025,
       "TE": 0.0,
       "ST": 0.0
     },
     "max_bonus": 150,
     "top_players_per_position": {
       "QB": 3,
       "OL": 5,
       "DL": 5,
       "DB": 4,
       "LB": 3,
       "RB": 2,
       "WR": 3,
       "TE": 2,
       "ST": 1
     }
   }
   ```

4. **Calculation logic implemented**:
   - For each position group, fetch top N players for team (based on config)
   - Calculate average rating for top players in position group
   - Normalize to 0-100 score per position
   - Apply position weight from config
   - Sum weighted scores to get overall position strength bonus (0-max_bonus)

5. **Graceful degradation** for missing data:
   - If team has no players in database, return 0.0 (no bonus)
   - If position group has insufficient players, use available players only
   - Log warning when falling back due to missing data

6. **Comprehensive docstrings** following Google style:
   - Module-level docstring explaining position strength methodology
   - Function-level docstrings with Args, Returns, Raises, Examples
   - Inline comments for calculation steps

7. **Unit tests created**: `tests/unit/test_position_strength.py`
   - Test position group score calculation with mock players
   - Test overall position strength with different configurations
   - Test graceful degradation (no players, partial data)
   - Test configuration loading and validation
   - Test weight normalization (weights sum to 1.0)

#### Integration Verification

- **IV1: No Impact on Existing Rankings** - Verify position service is not called by ranking_service.py yet (feature disabled)
- **IV2: Configuration Validation** - Load config file, verify weights sum to 1.0 and enabled=false
- **IV3: Unit Tests Pass** - All position strength tests pass with 100% coverage of new code
- **IV4: Import Works Without Position Data** - Run import without player data, verify no errors

#### Rollback Considerations

- **Risk Level**: Low - New isolated module, not integrated into ranking calculation yet
- **Rollback Steps**: Remove `src/core/position_service.py` and `src/core/position_weights.json`
- **Data Loss**: None (calculation logic only, no data storage)
- **Rollback Time**: < 1 minute (git revert)

---

### Story 1.4: Create Player Data Import Utility Script

As a **system administrator**,
I want **a standalone utility script to import player recruiting data from CFBD API into the database**,
so that **player data can be imported independently from the main season import workflow, enabling testing and historical data population**.

#### Acceptance Criteria

1. **Import script created**: `utilities/import_player_data.py` with:
   - Command-line arguments: `--year`, `--team`, `--dry-run`
   - Progress logging (e.g., "Importing players for Georgia (1/133)")
   - Error handling for API failures (continue with next team)
   - Summary report (teams imported, players added, errors encountered)

2. **Import logic implemented**:
   - Fetch all FBS teams for specified year
   - For each team, call `cfbd_client.get_recruiting_players(year, team=team_name)`
   - Parse response and create/update Player records
   - Use upsert logic: update if `cfbd_athlete_id` exists, insert if new
   - Lookup team_id from team name (case-insensitive match)
   - Batch commit every 100 players for performance

3. **Dry-run mode** (`--dry-run` flag):
   - Fetches and parses data but doesn't write to database
   - Prints summary of what would be imported
   - Useful for testing before actual import

4. **Progress reporting**:
   - Log: "Fetching players for {team_name}..."
   - Log: "Imported {count} players for {team_name}"
   - Log: "Warning: No player data for {team_name}"
   - Log: "Error fetching data for {team_name}: {error}"
   - Final summary: "Total: {teams} teams, {players} players, {errors} errors"

5. **API quota awareness**:
   - Estimate total API calls before import (133 teams)
   - Check current month's usage via `get_monthly_usage()`
   - Warn if import would exceed 90% of monthly quota
   - Provide `--force` flag to proceed anyway

6. **Error resilience**:
   - Continue with remaining teams if one team fails
   - Log all errors to `import_player_data_errors.log`
   - Return non-zero exit code if any errors occurred
   - Include team list with errors in final summary

7. **Usage documentation** in script header:
   ```python
   """
   Usage:
     python utilities/import_player_data.py --year 2024
     python utilities/import_player_data.py --year 2024 --team Georgia --dry-run
     python utilities/import_player_data.py --year 2024 --force
   """
   ```

#### Integration Verification

- **IV1: No Impact on Existing Import** - Verify `import_real_data.py` works unchanged (doesn't call player import)
- **IV2: Database Integrity** - After import, verify teams table unchanged, players table populated correctly
- **IV3: Dry-Run Mode** - Run with `--dry-run`, verify no database changes but logs show expected data
- **IV4: API Usage Tracking** - Verify API calls logged in api_usage table, quota calculations correct

#### Rollback Considerations

- **Risk Level**: Low - Separate utility script, no changes to existing workflows
- **Rollback Steps**: Delete `utilities/import_player_data.py`, optionally truncate players table
- **Data Loss**: Player data can be re-imported from CFBD API (data source preserved)
- **Rollback Time**: < 5 minutes (delete script + optional data cleanup)

---

### Story 1.5: Add API Endpoints for Player and Position Strength Data

As a **frontend developer**,
I want **REST API endpoints to retrieve player rosters and position strength calculations for teams**,
so that **I can display player data and position group analysis in the team detail page without modifying existing team endpoints**.

#### Acceptance Criteria

1. **New endpoint added** to `src/api/main.py`:
   ```python
   @app.get("/api/teams/{team_id}/players", response_model=TeamPlayersResponse)
   def get_team_players(
       team_id: int,
       position: Optional[str] = None,
       limit: int = 50,
       offset: int = 0,
       db: Session = Depends(get_db)
   )
   ```
   - Returns paginated list of players for team
   - Optional position filter
   - Includes player fields: name, position, stars, rating, ranking, recruiting_year
   - Response format: `{"team_id": int, "team_name": str, "total": int, "players": [...]}`

2. **New endpoint added** to `src/api/main.py`:
   ```python
   @app.get("/api/teams/{team_id}/position-strength", response_model=PositionStrengthResponse)
   def get_position_strength(
       team_id: int,
       db: Session = Depends(get_db)
   )
   ```
   - Returns position group strength breakdown
   - Includes overall position_strength_bonus value
   - Response format: `{"team_id": int, "position_groups": {"QB": 85.5, ...}, "total_bonus": 125.3, "enabled": false}`
   - Returns `enabled: false` if feature disabled in config

3. **Pydantic response schemas** created in `src/models/schemas.py`:
   - `TeamPlayersResponse` with players list and metadata
   - `PositionStrengthResponse` with position scores and total
   - `PlayerResponse` for individual player data

4. **Error handling**:
   - 404 if team_id doesn't exist
   - Empty list if no player data for team (not an error)
   - 500 with details if calculation fails

5. **OpenAPI documentation** auto-generated:
   - Endpoints appear in Swagger UI at `/docs`
   - Example responses included
   - Parameter descriptions clear

6. **Integration tests created**: `tests/integration/test_player_api.py`
   - Test GET /api/teams/{id}/players with pagination
   - Test position filter
   - Test GET /api/teams/{id}/position-strength
   - Test 404 for invalid team_id
   - Test empty response for team without player data

#### Integration Verification

- **IV1: Existing Endpoints Unchanged** - Verify all existing `/api/teams` endpoints work identically (no response schema changes)
- **IV2: Swagger UI Updated** - Check `/docs`, verify new endpoints appear with correct documentation
- **IV3: API Tests Pass** - Run integration test suite, all existing + new tests pass
- **IV4: CORS Headers Work** - Test endpoints from frontend origin, verify CORS allows access

#### Rollback Considerations

- **Risk Level**: Very Low - New endpoints only, no modifications to existing endpoints
- **Rollback Steps**: Remove endpoint functions from `src/api/main.py`, remove schemas from `schemas.py`
- **Data Loss**: None (read-only endpoints)
- **Rollback Time**: < 2 minutes (git revert)

---

### Story 1.6: Integrate Position Strength into Preseason Calculation with Feature Flag

As a **ranking system administrator**,
I want **position strength bonus to be calculated and added to preseason ratings when explicitly enabled via configuration**,
so that **the enhanced preseason calculation can be tested in production with controlled opt-in enablement while maintaining existing behavior as default**.

#### Acceptance Criteria

1. **Modify `calculate_preseason_rating()`** in `src/core/ranking_service.py`:
   - Load position weights config at function start
   - Check `enabled` flag in config
   - If enabled=false, skip position strength calculation (existing behavior)
   - If enabled=true, call `position_service.calculate_position_strength()`
   - Add position bonus to preseason rating
   - Log when position strength is enabled/disabled

2. **Updated preseason calculation formula** (when enabled):
   ```
   Preseason Rating = Base (1500)
                    + Recruiting Bonus (0-250)
                    + Transfer Bonus (0-100)
                    + Returning Production Bonus (0-100)
                    + Position Strength Bonus (0-150)  [NEW]
   Maximum = ~2100
   ```

3. **Configuration update**:
   - Set `"enabled": false` in `position_weights.json` (default off)
   - Document how to enable: change to `"enabled": true`
   - Add comment explaining opt-in nature

4. **Logging added**:
   - INFO: "Position strength calculation: ENABLED" or "DISABLED"
   - DEBUG: "Team {name} position bonus: {bonus}" (when enabled)
   - WARNING: "Team {name} has no player data, position bonus = 0"

5. **Backward compatibility maintained**:
   - If `position_weights.json` missing, feature disabled automatically
   - If Player table empty, feature works but all bonuses = 0
   - Existing tests pass with feature disabled

6. **Frontend display** in `frontend/team.html` and `frontend/js/team.js`:
   - Add "Position Group Strength" section below preseason factors
   - Only display if position strength data available (API returns non-zero)
   - Show position group breakdown (QB, OL, DL, etc.) with scores
   - Use horizontal bar chart or styled cards following existing design
   - Indicate if feature is disabled: "Position strength analysis: Not enabled"

7. **Integration tests updated**: `tests/integration/test_preseason_calculation.py`
   - Test preseason calculation with feature disabled (existing behavior)
   - Test preseason calculation with feature enabled (includes position bonus)
   - Test team with no player data (falls back gracefully)
   - Test maximum preseason rating achievable

8. **E2E tests updated**: `tests/e2e/test_team_detail_page.py`
   - Verify position strength section renders when data available
   - Verify appropriate message when feature disabled

#### Integration Verification

- **IV1: Existing Preseason Ratings Unchanged** - With feature disabled, verify all teams have identical preseason ratings to previous calculation
- **IV2: Full Test Suite Pass** - Run all 124 tests with feature disabled, all pass
- **IV3: Test with Feature Enabled** - Enable feature in test config, verify calculation includes position bonus correctly
- **IV4: Frontend Display** - Load team detail page, verify position strength section displays appropriately based on config
- **IV5: No Breaking Changes** - Verify all existing API endpoints return expected responses

#### Rollback Considerations

- **Risk Level**: Medium - Modifies core ranking calculation logic
- **Mitigation**: Feature disabled by default, requires explicit opt-in
- **Rollback Steps**:
  1. Set `"enabled": false` in position_weights.json (instant disable, no deployment)
  2. If needed, git revert changes to ranking_service.py
  3. Re-import season data to recalculate preseason ratings without position bonus
- **Data Loss**: Preseason ratings change when enabled/disabled, requires recalculation
- **Rollback Time**: < 1 minute (config change), or < 10 minutes (full code revert + data recalculation)

---

## 6. Epic Completion Criteria

The epic is successfully completed when:

1. ✅ All 6 stories completed with acceptance criteria met
2. ✅ Player database model created with proper relationships and indexes
3. ✅ CFBD API client successfully fetches player recruiting data
4. ✅ Position strength calculation service implemented with configurable weights
5. ✅ Player data import utility script functional and tested
6. ✅ API endpoints expose player and position strength data
7. ✅ Position strength integrated into preseason calculation with feature flag
8. ✅ Feature disabled by default (`"enabled": false` in position_weights.json)
9. ✅ Full test suite (124 existing + new tests) passes with 100% success rate
10. ✅ Zero regression in existing functionality (all existing preseason ratings identical when feature disabled)
11. ✅ Frontend displays position strength section appropriately (shows data when available, indicates when disabled)
12. ✅ Documentation updated (API docs, configuration guide, deployment guide)
13. ✅ Database migration tested and rolled out successfully
14. ✅ Import script successfully imports player data for at least one season (2024 or 2025)
15. ✅ Comprehensive testing completed: unit tests, integration tests, E2E tests all pass

---

## 7. Validation and Testing Strategy

### 7.1 Unit Testing

**New Test Files Required:**
- `tests/unit/test_player_model.py` - Player model and relationships (Story 1.1)
- `tests/unit/test_cfbd_player_api.py` - CFBD player endpoint integration (Story 1.2)
- `tests/unit/test_position_strength.py` - Position strength calculations (Story 1.3)

**Existing Test Files to Update:**
- `tests/integration/test_preseason_calculation.py` - Add position strength scenarios (Story 1.6)
- `tests/e2e/test_team_detail_page.py` - Verify position strength display (Story 1.6)

**Test Coverage Goals:**
- 100% coverage of new position_service.py module
- 100% coverage of new API endpoints
- 90%+ coverage of player data import utility

### 7.2 Integration Testing

**Critical Integration Points to Test:**
1. **Database Integration**: Player ↔ Team relationships, foreign key constraints
2. **API Integration**: CFBD player endpoint response parsing, error handling
3. **Calculation Integration**: Position strength within preseason rating formula
4. **Frontend Integration**: API calls from frontend, data display
5. **Configuration Integration**: Config file loading, feature flag behavior

**Test Scenarios:**
- Team with complete player data (all positions filled)
- Team with partial player data (some positions missing)
- Team with no player data (graceful degradation)
- Feature enabled vs disabled states
- API failures and error handling
- Large data volumes (133 teams, 11K+ players)

### 7.3 Performance Testing

**Performance Benchmarks:**
- Player data import: < 5 minutes for full season (133 teams)
- Position strength calculation: < 100ms per team
- Preseason rating calculation: < 10 seconds for all teams (including position strength)
- API endpoint response time: < 200ms for player list, < 100ms for position strength

**Load Testing:**
- Query 1000 players with various filters (position, team, year)
- Calculate position strength for all 133 teams sequentially
- Verify database indexes improve query performance

### 7.4 User Acceptance Testing

**Manual Test Plan:**

1. **Data Import Validation:**
   - Run import script for 2024 season
   - Verify player data appears in database
   - Check for any teams with missing data (log warnings)
   - Validate player counts match expectations (~85 players per team)

2. **Calculation Verification:**
   - Enable position strength feature
   - Recalculate preseason ratings
   - Verify top teams (Alabama, Georgia, Ohio State) have expected bonuses
   - Compare with feature disabled (should match original ratings)

3. **Frontend Display:**
   - Navigate to team detail page (e.g., Georgia)
   - Verify position strength section appears
   - Check position group breakdown displays correctly
   - Test with feature disabled (should show appropriate message)

4. **API Testing:**
   - Call `/api/teams/{id}/players` for various teams
   - Test pagination (limit, offset parameters)
   - Test position filter
   - Call `/api/teams/{id}/position-strength` endpoint
   - Verify response formats match documentation

---

## 8. Deployment Plan

### 8.1 Pre-Deployment Checklist

- [ ] All 6 stories completed and tested
- [ ] Full test suite passes (124+ tests)
- [ ] Database migration script tested in staging
- [ ] Database backup created before migration
- [ ] `position_weights.json` config file reviewed and set to `"enabled": false`
- [ ] Import script tested with sample data
- [ ] API documentation updated in Swagger UI
- [ ] Deployment guide updated with migration steps
- [ ] Rollback procedures documented

### 8.2 Deployment Steps

**Phase 1: Database Migration (5 minutes)**
1. SSH to production VPS: `/var/www/cfb-rankings/`
2. Backup database: `cp cfb_rankings.db cfb_rankings_backup_$(date +%Y%m%d).db`
3. Run migration: `python migrations/migrate_add_player_table.py`
4. Verify migration: `sqlite3 cfb_rankings.db "SELECT name FROM sqlite_master WHERE type='table' AND name='players';"`

**Phase 2: Code Deployment (10 minutes)**
1. Pull latest code: `git pull origin main`
2. Review changes: `git log --oneline -10`
3. Install dependencies: `pip install -r requirements.txt` (if changed)
4. Verify config file exists: `ls src/core/position_weights.json`
5. Confirm feature disabled: `grep '"enabled": false' src/core/position_weights.json`
6. Restart service: `sudo systemctl restart cfb-rankings`
7. Check logs: `journalctl -u cfb-rankings -n 50`

**Phase 3: Smoke Testing (5 minutes)**
1. Test existing endpoints: `curl https://your-domain.com/api/teams`
2. Test new endpoints: `curl https://your-domain.com/api/teams/1/players`
3. Load frontend: verify no JavaScript errors
4. Check team detail page: position strength section should show "Not enabled"

**Phase 4: Optional Player Data Import (30-60 minutes)**
1. Import player data (optional): `python utilities/import_player_data.py --year 2024`
2. Monitor progress and check for errors
3. Verify data imported: `sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM players;"`

### 8.3 Post-Deployment Validation

- [ ] All existing pages load without errors
- [ ] Rankings page displays correctly
- [ ] Team detail pages load successfully
- [ ] New API endpoints return expected responses
- [ ] No 500 errors in logs
- [ ] Position strength section shows "Not enabled" message
- [ ] Existing preseason ratings unchanged (verify spot-check of 5 teams)

### 8.4 Feature Enablement (When Ready)

**When to Enable:**
- After 1-2 weeks of production monitoring with feature disabled
- After player data successfully imported for current season
- After manual validation of position strength calculations
- After stakeholder review of sample calculations

**Enablement Steps:**
1. Edit config: `vim src/core/position_weights.json`
2. Change: `"enabled": false` → `"enabled": true`
3. Restart service: `sudo systemctl restart cfb-rankings`
4. Trigger preseason recalculation or wait for next season initialization
5. Monitor logs for position strength calculations
6. Verify frontend displays position strength data

---

## 9. Success Metrics and Monitoring

### 9.1 Success Metrics

**Before Epic (Current State):**
- Preseason rating uses 3 factors: recruiting rank, transfer rank, returning production
- Maximum preseason rating: ~1850
- No player-level data available
- No position-specific analysis
- No way to differentiate roster composition quality

**After Epic (Target State):**
- Preseason rating uses 4 factors (when enabled): recruiting, transfers, returning production, **position strength**
- Maximum preseason rating: ~2100
- Player-level data for 11,000+ recruits stored in database
- Position group strength calculated with configurable weights
- Ability to analyze correlation between position strength and team success
- Feature safely deployed and disabled by default, ready for opt-in enablement

**Quantitative Metrics:**
- Database size increase: < 50% (target: +500KB per season)
- API quota usage: +133 calls per season import (< 0.5% of monthly quota)
- Preseason calculation time: remains < 10 seconds for all teams
- Test coverage: 90%+ for new code
- Zero regression: 100% of existing tests pass

**Qualitative Metrics:**
- Improved preseason ranking accuracy (to be measured after season completion)
- Better correlation between preseason prediction and end-of-season performance
- Enhanced transparency into how roster composition impacts preseason ratings
- Ability to identify position group weaknesses/strengths for each team

### 9.2 Monitoring and Observability

**Application Logs to Monitor:**
- Position strength calculation events (enabled/disabled state)
- Teams with missing player data (warnings)
- API errors fetching player data
- Configuration file load failures
- Position strength bonus values per team (when enabled)

**Database Metrics:**
- Player table row count (should grow by ~11K per season)
- Query performance for position group aggregations
- Foreign key constraint violations (should be zero)

**API Usage Monitoring:**
- `/recruiting/players` endpoint call count
- Monthly quota consumption percentage
- API response times for player endpoint

**System Health Indicators:**
- All existing tests continue passing
- No increase in error rates after deployment
- Preseason calculation completes successfully
- Frontend loads without JavaScript errors

---

## 10. Risk Register

### High-Priority Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| CFBD API player data incomplete for some teams | High | Medium | Graceful degradation, fall back to team-level data | Dev Team |
| Position weights don't correlate with actual performance | Medium | Medium | Make weights configurable, plan for iterative tuning | PM / Data Analyst |
| Import script exceeds API quota during testing | Low | Low | Track usage, implement dry-run mode, cache results | Dev Team |

### Medium-Priority Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Database migration fails in production | Low | Medium | Test in staging, backup before migration, idempotent script | Dev Team |
| Performance degradation from player queries | Low | Medium | Add database indexes, optimize queries, profile performance | Dev Team |
| Feature accidentally enabled in production | Low | Medium | Default disabled, require explicit config change, monitor logs | Ops Team |

### Low-Priority Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Frontend display clutters UI | Low | Low | Follow existing design patterns, make collapsible | Frontend Dev |
| Configuration file missing after deployment | Low | Low | Include in git repo, validate at startup, fallback to defaults | Dev Team |

---

## 11. Next Steps

After PRD approval:

1. **✅ Epic and Story Documents Created** - This PRD serves as the comprehensive epic document

2. **Validate CFBD API Access** - Before Story 1.2 implementation:
   - ✅ Confirmed: `/recruiting/players` endpoint exists and is documented
   - Test endpoint with current API key
   - Verify response structure matches swagger.json specification
   - Confirm player data available for target season (2024/2025)
   - Document any discrepancies or missing data

3. **Create Individual Story Tracking** (Optional):
   - Create story documents: `docs/stories/preseason-1.1.story.md` through `preseason-1.6.story.md`
   - Or track stories in project management tool (GitHub Issues, Jira, etc.)

4. **Begin Execution** - Start with Story 1.1 (lowest risk, foundation):
   - Create Player database model
   - Run database migration in development
   - Verify all existing tests pass

5. **Continuous Validation** - After each story:
   - Run full test suite (124+ tests)
   - Manual smoke testing of existing functionality
   - Integration verification steps from story acceptance criteria

6. **Production Deployment** - After all stories complete:
   - Follow deployment plan (Section 8)
   - Feature remains disabled by default
   - Monitor for 1-2 weeks before considering enablement

7. **Feature Enablement Planning** (Future):
   - Import player data for current season
   - Analyze position strength calculations manually
   - Correlate with historical team performance
   - Tune position weights based on analysis
   - Enable feature when confident in accuracy

8. **Future Enhancements** (Out of Scope for This Epic):
   - Transfer portal player tracking (position-specific gains/losses)
   - Historical analysis: position strength vs end-of-season ELO
   - Advanced position weighting based on coaching scheme
   - Integration with returning production at position level
   - Player development tracking season-over-season

---

## 12. Appendix

### A. Position Weight Research Notes

Initial position weights (QB=30%, OL=25%, DL=20%, DB=15%, LB=5%, RB/WR/TE=2.5% each) are based on:

1. **Football Analytics Consensus:**
   - Quarterback is most valuable position (30% weight)
   - Line play (OL + DL) accounts for ~45% of team success
   - Secondary coverage quality critical in modern passing game (15%)
   - Skill positions less predictive at college level (RB/WR interchangeable in many schemes)

2. **Trade-offs in Weighting:**
   - Higher QB weight recognizes outsized impact but may overvalue teams with elite QB and weak supporting cast
   - OL/DL weighting acknowledges "games won in trenches" philosophy
   - Lower skill position weights reflect scheme-dependency and coaching impact

3. **Tuning Strategy:**
   - Start conservatively with research-based weights
   - Import 3-5 seasons of historical data
   - Calculate position strength for past seasons
   - Correlate with end-of-season ELO rankings
   - Adjust weights to maximize correlation
   - Consider conference-specific variations (e.g., SEC DL vs Pac-12 offense)

### B. API Rate Limit Analysis

**Current CFBD API Usage:**
- Monthly quota: 30,000 calls
- Typical usage: ~5,000 calls/month (existing imports)
- Headroom: 25,000 calls (83% available)

**New Usage from This Enhancement:**
- Player import: 133 calls per season (one per FBS team)
- Testing/development: ~500 calls (estimate for development phase)
- Production re-imports: minimal (player data rarely changes after import)

**Total Impact:**
- One-time development: ~633 calls (2% of quota)
- Ongoing: ~133 calls per season (~0.4% of monthly quota)
- **Risk Level: Very Low** - Plenty of quota headroom

### C. Database Schema Diagram

```
┌─────────────────────────┐
│         teams           │
│─────────────────────────│
│ id (PK)                 │
│ name                    │
│ conference              │
│ recruiting_rank         │
│ transfer_rank           │
│ returning_production    │
│ elo_rating              │
│ ...                     │
└─────────────────────────┘
           │ 1
           │
           │ M
           ▼
┌─────────────────────────┐
│        players          │  [NEW]
│─────────────────────────│
│ id (PK)                 │
│ cfbd_athlete_id (UNIQUE)│
│ name                    │
│ team_id (FK)            │
│ position                │
│ stars                   │
│ rating                  │
│ ranking                 │
│ recruiting_year         │
│ created_at              │
└─────────────────────────┘

Indexes:
- idx_players_team_position (team_id, position)
- idx_players_recruiting_year (recruiting_year)
- UNIQUE constraint on cfbd_athlete_id
```

### D. Configuration File Reference

**File:** `src/core/position_weights.json`

**Purpose:** Controls position strength calculation behavior and weighting factors

**Key Fields:**
- `enabled` (boolean) - Feature flag, default: false
- `weights` (object) - Position group weights (must sum to 1.0)
- `max_bonus` (number) - Maximum position strength bonus points
- `top_players_per_position` (object) - How many players to consider per position

**Example:**
```json
{
  "version": "1.0",
  "enabled": false,
  "weights": {
    "QB": 0.30,
    "OL": 0.25,
    "DL": 0.20,
    "DB": 0.15,
    "LB": 0.05,
    "RB": 0.025,
    "WR": 0.025
  },
  "max_bonus": 150,
  "top_players_per_position": {
    "QB": 3,
    "OL": 5,
    "DL": 5,
    "DB": 4,
    "LB": 3,
    "RB": 2,
    "WR": 3
  }
}
```

### E. CFBD API Endpoint Reference

**Endpoint Confirmation:**

- **Path:** `GET /recruiting/players`
- **Base URL:** `https://api.collegefootballdata.com`
- **Authentication:** Bearer token (CFBD_API_KEY)

**Parameters:**
- `year` (integer, required if team not specified) - Recruiting class year (minimum: 2000)
- `team` (string, required if year not specified) - Committed team filter
- `position` (string, optional) - Position abbreviation filter
- `classification` (string, optional, default: "HighSchool") - Type of recruit
- `state` (string, optional) - State/province abbreviation filter

**Response Structure:**
Array of Recruit objects containing:
- `id` (integer) - Recruit ID
- `athleteId` (integer) - Athlete identifier
- `name` (string) - Player name
- `position` (string) - Position abbreviation
- `stars` (integer) - Star rating (1-5)
- `rating` (number) - Numerical recruiting rating
- `ranking` (integer) - Overall recruit ranking
- `committedTo` (string) - Team committed to
- `year` (integer) - Recruiting class year
- `school` (string) - High school attended
- `city`, `state`, `county` (strings) - Location information
- `height` (string), `weight` (integer) - Physical attributes

**Sources:**
- [CFBD Swagger Specification](https://github.com/CFBD/cfb-api/blob/main/swagger.json)
- [CFBD Python Client Documentation](https://github.com/CFBD/cfbd-python/blob/master/docs/RecruitingApi.md)
- [CFBD JavaScript SDK](https://github.com/CFBD/cfb.js/blob/master/docs/RecruitingApi.md)

---

**END OF PRD**
