# Stat-urday Synthesis - Comprehensive Codebase Cleanup PRD

**Product Requirements Document**
**Version**: 1.0
**Date**: 2025-12-08
**Author**: John (Product Manager)
**Status**: Draft

---

## 1. Intro Project Analysis and Context

### 1.1 Analysis Source

- **IDE-based fresh analysis** combined with existing architecture documentation

### 1.2 Existing Project Overview

#### Current Project State

The **Stat-urday Synthesis** project is a comprehensive College Football Ranking System that calculates and displays alternative rankings using a Modified ELO algorithm. The system integrates:
- Real-time game data from CollegeFootballData API
- Preseason metrics (recruiting rankings, transfer portal, returning production)
- FastAPI REST backend with SQLAlchemy ORM
- Responsive frontend with vanilla JavaScript
- Production deployment on VPS with Nginx + Gunicorn
- Comprehensive test suite (124 tests: unit, integration, E2E)

The system has been through **26 completed epics** with active development since inception, resulting in significant feature accumulation and organic codebase growth.

### 1.3 Available Documentation Analysis

**Available Documentation:**
- ✅ Tech Stack Documentation (architecture.md includes comprehensive tech stack)
- ✅ Source Tree/Architecture (architecture.md provides high-level overview)
- ⚠️ Coding Standards (partially documented)
- ✅ API Documentation (comprehensive, auto-generated via FastAPI)
- ✅ External API Documentation (CFBD client documented)
- ❌ UX/UI Guidelines (not formalized)
- ⚠️ Technical Debt Documentation (mentioned in architecture.md but not comprehensive)
- ✅ Epic/Story Documentation (extensive: 26 epics documented in docs/)

**Documentation Status:** The project has good high-level documentation but lacks formalized coding standards, UI guidelines, and comprehensive technical debt tracking.

### 1.4 Enhancement Scope Definition

**Enhancement Type:**
- ✅ **Major Feature Modification** (restructuring codebase organization)
- ✅ **Bug Fix and Stability Improvements** (removing obsolete code)
- ✅ **Other: Comprehensive Codebase Cleanup & Documentation**

**Enhancement Description:**

This enhancement will transform the current organically-grown codebase into a well-organized, professionally documented, and maintainable system. The project has accumulated **54 Python files in the root directory** (including many one-off diagnostic, migration, and fix scripts) and **20 scripts in the scripts/ directory**. The cleanup will reorganize file structure, remove obsolete code, add comprehensive inline documentation, create developer guides, and establish coding standards.

**Impact Assessment:**
- ✅ **Significant Impact** (substantial existing code changes across file organization and documentation)

**Key Statistics:**
- **54 Python files** in root directory (many ad-hoc: check_*, fix_*, migrate_*, debug_*)
- **20 Python scripts** in scripts/ directory
- **26 completed epics** with extensive documentation
- **Core modules**: main.py, models.py, ranking_service.py, cfbd_client.py, database.py

### 1.5 Goals and Background Context

#### Goals
- Reorganize scattered scripts into logical directory structure (migrations/, diagnostics/, utilities/)
- Remove obsolete and redundant code files
- Add comprehensive docstrings to all core modules and functions
- Create developer onboarding documentation (CONTRIBUTING.md, DEVELOPMENT.md)
- Establish and document coding standards and best practices
- Standardize naming conventions and code formatting
- Improve codebase maintainability and developer experience

#### Background Context

The Stat-urday Synthesis project has evolved through 26 major epics, each adding significant functionality. This organic growth pattern has resulted in a functional but organizationally challenging codebase. The root directory contains 54 Python files, many of which are one-off diagnostic scripts (check_ranking_history.py, debug_championships.py), migration scripts (migrate_add_*.py), and fix scripts (fix_2025_records.py, fix_playoff_weeks.py) that were created to address specific issues but never archived.

This cleanup is necessary to:
1. **Improve developer productivity** - Reduce time spent navigating cluttered file structure
2. **Enable confident refactoring** - Clear documentation makes changes safer
3. **Facilitate onboarding** - New developers can understand the system faster
4. **Reduce technical debt** - Remove obsolete code before it causes confusion
5. **Establish foundation** - Create organizational patterns for future epics

The cleanup will maintain 100% compatibility with existing functionality while transforming the codebase into a professional, maintainable state.

### 1.6 Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial | 2025-12-08 | 1.0 | Initial PRD creation for comprehensive cleanup | John (PM) |

---

## 2. Requirements

### 2.1 Functional Requirements

**FR1:** The system shall reorganize all root-level Python files into a logical directory structure with categories: `migrations/`, `diagnostics/`, `utilities/`, and `archive/` while maintaining clear documentation of each category's purpose.

**FR2:** The system shall identify and remove all obsolete Python files (one-off diagnostic scripts, superseded migration scripts, and deprecated utilities) after validation that they are no longer needed.

**FR3:** All core modules (main.py, models.py, ranking_service.py, cfbd_client.py, database.py, schemas.py) shall be enhanced with comprehensive Python docstrings following Google or NumPy docstring conventions.

**FR4:** All public functions and methods across the codebase shall include docstrings with parameter descriptions, return value documentation, and usage examples where appropriate.

**FR5:** The system shall create a CONTRIBUTING.md guide documenting: development setup, code organization, testing procedures, and contribution workflow.

**FR6:** The system shall create a DEVELOPMENT.md guide documenting: architecture overview, key design patterns, module relationships, and common development tasks.

**FR7:** The system shall establish and document coding standards covering: naming conventions, code formatting (PEP 8 compliance), import organization, and error handling patterns.

**FR8:** All import statements across Python files shall be reorganized and standardized following the established convention (standard library → third-party → local imports, alphabetically sorted).

**FR9:** The system shall update all existing documentation (README.md, architecture.md, etc.) to reflect the new file organization structure.

### 2.2 Non-Functional Requirements

**NFR1:** The cleanup shall maintain 100% backward compatibility - all existing API endpoints, database schemas, and frontend functionality must continue to work without modification.

**NFR2:** All file reorganization changes shall be completed with zero runtime errors - the test suite (124 tests) must pass with 100% success rate after each phase.

**NFR3:** The enhanced documentation shall improve new developer onboarding time by providing clear entry points and reducing initial codebase comprehension time.

**NFR4:** Code formatting and linting shall be automated using tools (black, flake8, isort) with configuration files committed to the repository.

**NFR5:** The cleanup shall not introduce any new dependencies beyond development tools (linting, formatting) - no runtime dependency changes.

**NFR6:** All file moves and reorganization shall preserve git history by using `git mv` commands to maintain traceability.

**NFR7:** Documentation shall be maintained in Markdown format using consistent formatting, clear hierarchical structure, and practical code examples.

### 2.3 Compatibility Requirements

**CR1: Existing API Compatibility** - All FastAPI endpoints in main.py shall remain at identical paths with identical request/response schemas. No breaking changes to the REST API contract.

**CR2: Database Schema Compatibility** - No database schema changes shall be introduced. All SQLAlchemy models in models.py shall remain unchanged. Existing database files shall work without migration.

**CR3: UI/UX Consistency** - Frontend JavaScript shall continue to work without modification. No changes to API client calls or expected response formats. Static file paths shall remain consistent.

**CR4: Integration Compatibility** - CollegeFootballData API client (cfbd_client.py) integration shall remain unchanged. All external API calls and response handling shall continue to function identically.

**CR5: Deployment Compatibility** - Existing deployment configuration (gunicorn_config.py, nginx.conf, systemd services) shall require minimal or no changes. Production deployment process shall remain consistent.

**CR6: Test Compatibility** - All existing test files shall continue to pass without modification. Test fixtures and factories shall work with reorganized code structure through updated import statements only.

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
- CollegeFootballData.com API (free tier: 100 req/hour, requires CFBD_API_KEY)
- Requests 2.31.0+ (HTTP client for external API)
- python-dotenv 1.0.0 (environment variable management)

**Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 (no frameworks, no build process)

**Testing**: pytest, pytest-cov, Playwright (124 tests: unit, integration, E2E)

**Development Tools** (to be added in this cleanup):
- black (code formatting)
- flake8 (linting)
- isort (import sorting)

### 3.2 Integration Approach

#### Database Integration Strategy
- **No schema changes** - Cleanup is documentation and file organization only
- All SQLAlchemy models (Team, Game, RankingHistory, Season, Prediction, APIUsage, UpdateTask) remain unchanged
- Existing `cfb_rankings.db` file compatibility maintained
- Migration scripts relocated to `migrations/` directory with clear naming

#### API Integration Strategy
- **Zero API contract changes** - All FastAPI endpoints in main.py remain at identical paths
- Request/response schemas (Pydantic models in schemas.py) unchanged
- CORS middleware configuration preserved
- Dependency injection pattern (DB sessions via `get_db()`) maintained

#### Frontend Integration Strategy
- **No frontend code changes** - All HTML/CSS/JS files remain functionally identical
- API client (`frontend/js/api.js`) continues using same endpoints
- Static file serving via Nginx remains at `/frontend/*` path
- Updated documentation will clarify backend file organization but won't affect frontend operation

#### Testing Integration Strategy
- **Import path updates only** - Test files update import statements to reflect new file locations
- Test fixtures and factories (tests/factories.py, tests/conftest.py) adjust imports
- All 124 existing tests must pass after reorganization
- pytest configuration (pytest.ini) may need path adjustments for test discovery

### 3.3 Code Organization and Standards

#### File Structure Approach

**Current State**: 54 Python files in root directory, 20 in scripts/

**Target State**:
```
/
├── src/                          # NEW: Core application code
│   ├── api/                      # NEW: API layer
│   │   └── main.py               # MOVED from root
│   ├── core/                     # NEW: Core business logic
│   │   ├── ranking_service.py   # MOVED from root
│   │   └── cfb_elo_ranking.py   # MOVED from root
│   ├── models/                   # NEW: Data layer
│   │   ├── database.py           # MOVED from root
│   │   ├── models.py             # MOVED from root
│   │   └── schemas.py            # MOVED from root
│   └── integrations/             # NEW: External integrations
│       └── cfbd_client.py        # MOVED from root
│
├── migrations/                   # NEW: Database migrations
│   ├── migrate_add_*.py          # MOVED from root (15+ files)
│   └── run_migration_001.py     # MOVED from migrations/
│
├── diagnostics/                  # NEW: Diagnostic scripts
│   ├── check_*.py                # MOVED from root (10+ files)
│   └── debug_*.py                # MOVED from root
│
├── utilities/                    # NEW: Reusable utilities
│   ├── seed_data.py              # MOVED from root
│   ├── demo.py                   # MOVED from root
│   └── compare_*.py              # MOVED from root
│
├── archive/                      # NEW: Historical one-off scripts
│   ├── fix_*.py                  # MOVED from root (kept for history)
│   └── README.md                 # Explains archive purpose
│
├── scripts/                      # EXISTING: Keep production scripts
│   └── *.py                      # No changes (weekly_update, etc.)
│
├── gunicorn_config.py            # KEEP in root (deployment requirement)
├── import_real_data.py           # KEEP in root (main data import)
├── requirements.txt              # KEEP in root
├── requirements-dev.txt          # KEEP in root
├── pytest.ini                    # KEEP in root
├── .env                          # KEEP in root
└── README.md                     # KEEP in root (update file paths)
```

#### Naming Conventions
- **Files**: snake_case.py (existing standard - maintain)
- **Classes**: PascalCase (existing standard - maintain)
- **Functions/Variables**: snake_case (existing standard - maintain)
- **Constants**: UPPER_SNAKE_CASE (existing standard - maintain)
- **Private methods**: _leading_underscore (existing standard - maintain)

#### Coding Standards
- **PEP 8 compliance** enforced via flake8
- **Black formatting** (line length: 100 characters to match existing code)
- **Import organization**: isort with profile=black
  - Standard library imports
  - Third-party imports (FastAPI, SQLAlchemy, etc.)
  - Local application imports
  - Alphabetically sorted within each group
- **Type hints**: Encouraged for all new functions (existing code has partial coverage)

#### Documentation Standards
- **Docstrings**: Google style (consistent with FastAPI ecosystem)
- **Module docstrings**: Required for all Python files (purpose, main classes/functions)
- **Function docstrings**: Required for public functions (Args, Returns, Raises, Examples)
- **Class docstrings**: Required for all classes (purpose, attributes, usage)
- **Inline comments**: For complex logic only (code should be self-documenting)

### 3.4 Deployment and Operations

#### Build Process Integration
- **No build changes** - Python application runs directly (no compilation)
- Add pre-commit hooks (optional): black, flake8, isort checks
- CI/CD pipeline (if exists) may need path updates for new file locations

#### Deployment Strategy
- **Zero deployment changes required** for file reorganization
- `gunicorn_config.py` remains in root (systemd service expects it there)
- Nginx configuration unchanged (serves static files, proxies API)
- Systemd service file may need WorkingDirectory validation after reorganization
- Deployment script (`deploy/deploy.sh`) may need verification after file moves

#### Monitoring and Logging
- **No changes to logging** - Existing logging configuration preserved
- Log file locations unchanged (`/var/log/cfb-rankings/` in production)
- APIUsage tracking unchanged (monitors CFBD API quota)
- UpdateTask tracking unchanged (monitors weekly update jobs)

#### Configuration Management
- **`.env` file unchanged** - Same environment variables (CFBD_API_KEY, DATABASE_URL, CFBD_MONTHLY_LIMIT)
- Configuration loading via python-dotenv unchanged
- All config references in code remain functional after file reorganization

### 3.5 Risk Assessment and Mitigation

#### Technical Risks

1. **Import Path Breakage** (High Likelihood, High Impact)
   - **Risk**: Moving files breaks imports across the entire codebase
   - **Mitigation**:
     - Comprehensive search/replace of import statements
     - Run full test suite after each file category move
     - Use automated refactoring tools (rope, bowler) where possible

2. **Production Deployment Failure** (Medium Likelihood, High Impact)
   - **Risk**: Systemd service or Gunicorn can't find main.py after reorganization
   - **Mitigation**:
     - Test deployment on staging environment first
     - Keep gunicorn_config.py in root or update systemd WorkingDirectory
     - Maintain rollback plan (git revert strategy)

3. **Test Discovery Failure** (Medium Likelihood, Medium Impact)
   - **Risk**: pytest can't find test files or fixtures after reorganization
   - **Mitigation**:
     - Update pytest.ini with new paths if needed
     - Validate all 124 tests pass before considering phase complete
     - Update conftest.py imports early in process

#### Integration Risks

1. **Frontend API Call Breakage** (Low Likelihood, High Impact)
   - **Risk**: Frontend can't reach API endpoints after backend reorganization
   - **Mitigation**:
     - API endpoints don't change (only file locations change)
     - Test frontend functionality manually after deployment
     - Run E2E tests (Playwright) to validate end-to-end workflows

2. **Database Connection Loss** (Low Likelihood, High Impact)
   - **Risk**: Reorganized database.py can't find cfb_rankings.db file
   - **Mitigation**:
     - DATABASE_URL in .env uses absolute or relative path - validate this works from new location
     - Test database connectivity after each reorganization phase
     - Ensure SQLite file path resolution is explicit, not relative to moved file

#### Deployment Risks

1. **Systemd Service Failure** (Medium Likelihood, High Impact)
   - **Risk**: Service can't start after file reorganization
   - **Mitigation**:
     - Update systemd service WorkingDirectory to project root
     - Update ExecStart command to reference correct main.py path
     - Test service restart before production deployment

2. **Nginx Static File 404s** (Low Likelihood, Low Impact)
   - **Risk**: Nginx can't find static files if frontend/ moves
   - **Mitigation**:
     - Keep frontend/ directory in current location (root level)
     - Only backend Python files will reorganize
     - Validate static file serving after any changes

#### Mitigation Strategies

1. **Phased Rollout**: Move files in categories (migrations → diagnostics → utilities → archive → core) with full test validation between phases

2. **Automated Testing**: Run full test suite (124 tests) after each phase to catch breaking changes immediately

3. **Git Safety**: Use `git mv` for all file moves to preserve history, enable easy rollback via `git revert`

4. **Staging Environment**: Test complete reorganization in development/staging before production deployment

5. **Rollback Plan**: Maintain clean git commits per phase, enabling surgical rollback if needed

6. **Documentation First**: Update README.md and DEVELOPMENT.md with new structure BEFORE moving files, so developers have reference during transition

---

## 4. Epic and Story Structure

### 4.1 Epic Approach

**Epic Structure Decision**: **Single Comprehensive Epic** with 7 sequenced stories

**Rationale**:

This cleanup enhancement should be structured as a **single comprehensive epic** rather than multiple epics because:

1. **Unified Goal**: All cleanup activities share a common objective - transforming the codebase from organically-grown to professionally organized. This is one cohesive enhancement, not separate unrelated features.

2. **Interdependent Changes**: The work has natural dependencies:
   - Documentation standards must be established before adding docstrings
   - File organization structure must be defined before moving files
   - Coding standards must be documented before applying formatting
   - All changes build upon each other sequentially

3. **Risk Management**: A single epic allows us to sequence stories in a risk-minimizing order:
   - Start with low-risk additions (documentation files)
   - Progress to medium-risk changes (adding docstrings)
   - Complete with higher-risk structural changes (file reorganization)
   - Run full test suite validation between each story

4. **Brownfield Best Practice**: For brownfield enhancements, a single epic with carefully sequenced stories ensures existing functionality remains intact throughout the process. Each story includes integration verification steps.

5. **Atomic Deployment**: The cleanup can be deployed as a cohesive unit rather than piecemeal, ensuring the codebase is never in a half-cleaned state in production.

**Story Count**: 7 stories (slightly above typical brownfield epic size, but justified by comprehensive scope)

**Story Sequencing Strategy**: Low-risk → Medium-risk → High-risk, with continuous validation

---

## 5. Epic 1: Comprehensive Codebase Cleanup and Professional Documentation

**Epic Goal**: Transform the Stat-urday Synthesis codebase from an organically-grown system with 54 root-level Python files into a professionally organized, well-documented, and maintainable codebase with clear structure, comprehensive inline documentation, and established coding standards—while maintaining 100% backward compatibility and zero regression in existing functionality.

**Integration Requirements**:
- All 124 existing tests must pass after each story completion
- Zero breaking changes to API endpoints, database schema, or frontend functionality
- Production deployment process must remain functional throughout
- Git history must be preserved for all file reorganizations
- Import statements must be updated comprehensively to reflect new file locations
- Documentation must be updated to reflect new structure before files are moved

---

### Story 1.1: Create Developer Onboarding Documentation

As a **new developer joining the Stat-urday Synthesis project**,
I want **comprehensive onboarding documentation that explains the codebase structure, development setup, and contribution workflow**,
so that **I can quickly understand the system architecture and start contributing effectively without extensive hand-holding**.

#### Acceptance Criteria

1. **CONTRIBUTING.md created** in project root with sections:
   - Development environment setup (Python 3.11+, virtual environment, dependencies)
   - How to run the application locally (backend + frontend)
   - How to run tests (unit, integration, E2E)
   - Code contribution workflow (branching, commits, PRs)
   - Code review checklist

2. **DEVELOPMENT.md created** in project root with sections:
   - High-level architecture overview (referencing docs/architecture.md)
   - Core module responsibilities (main.py, ranking_service.py, models.py, etc.)
   - Key design patterns (dependency injection, service layer, ORM)
   - Common development tasks (adding endpoints, modifying ELO algorithm, adding tests)
   - Troubleshooting guide (common errors, solutions)

3. **Both documents use Markdown** with proper formatting, code examples, and links to relevant existing docs

4. **Documents are referenced in README.md** with a "For Developers" section linking to CONTRIBUTING.md and DEVELOPMENT.md

5. **All content is technically accurate** based on existing codebase analysis

#### Integration Verification

- **IV1: Existing Documentation Integrity** - Verify README.md, architecture.md, and all docs/ files remain unchanged except for new "For Developers" section in README.md
- **IV2: No Code Changes** - Confirm zero changes to Python files, frontend files, or configuration files
- **IV3: Documentation Accessibility** - Verify new documentation renders correctly in GitHub and is discoverable from README.md

#### Rollback Considerations
- **Low Risk**: Only adds new documentation files, no code changes
- **Rollback**: Simple file deletion if needed (git revert of commit)

---

### Story 1.2: Establish Coding Standards and Configure Tooling

As a **developer maintaining the Stat-urday Synthesis codebase**,
I want **documented coding standards and automated formatting/linting tools configured**,
so that **code quality is consistent, reviews focus on logic rather than style, and technical debt is minimized**.

#### Acceptance Criteria

1. **CODING-STANDARDS.md created** in docs/ with sections:
   - Python naming conventions (already used: snake_case functions, PascalCase classes)
   - PEP 8 compliance requirements
   - Import organization standards (standard lib → third-party → local, alphabetically sorted)
   - Docstring style guide (Google style with examples)
   - Type hints policy (encouraged for new code)
   - Error handling patterns (existing patterns documented)

2. **Black configuration** added to pyproject.toml:
   - Line length: 100 (to match existing code style)
   - Target Python version: 3.11

3. **Flake8 configuration** added to .flake8:
   - Max line length: 100 (consistent with Black)
   - Ignore common Black conflicts (E203, W503)
   - Exclude: migrations/, archive/, .venv/

4. **isort configuration** added to pyproject.toml:
   - Profile: black (compatibility)
   - Line length: 100
   - Known first party: src (for future reorganization)

5. **requirements-dev.txt updated** with development tools:
   - black>=23.0.0
   - flake8>=6.0.0
   - isort>=5.12.0

6. **Pre-commit hooks documentation** added to CONTRIBUTING.md (optional usage, not enforced)

#### Integration Verification

- **IV1: Existing Code Compatibility** - Run black, flake8, isort in check mode on existing codebase to establish baseline (expect violations, document count)
- **IV2: No Code Changes** - Configuration only, no code formatting applied in this story
- **IV3: Tool Installation** - Verify all tools install correctly via `pip install -r requirements-dev.txt`

#### Rollback Considerations
- **Very Low Risk**: Only adds configuration files and documentation
- **Rollback**: Remove configuration files and requirements-dev.txt changes (git revert)

---

### Story 1.3: Add Comprehensive Docstrings to Core Modules

As a **developer working with the Stat-urday Synthesis core business logic**,
I want **all core modules and functions to have comprehensive docstrings following Google style**,
so that **I can understand the purpose, parameters, return values, and usage of any function without reading its implementation**.

#### Acceptance Criteria

1. **main.py enhanced** with:
   - Module-level docstring (FastAPI application purpose, key endpoints)
   - Docstring for every route handler function (purpose, params, returns, example response)
   - Minimum 20 function docstrings added

2. **ranking_service.py enhanced** with:
   - Module-level docstring (Modified ELO algorithm, business logic layer)
   - Class docstring for RankingService (purpose, key methods)
   - Docstring for every public method (purpose, args, returns, raises, example)
   - Minimum 15 method docstrings added

3. **models.py enhanced** with:
   - Module-level docstring (SQLAlchemy ORM models)
   - Class docstring for each model (Team, Game, RankingHistory, Season, Prediction, etc.)
   - Docstring for complex model methods/properties
   - Minimum 10 class/method docstrings added

4. **schemas.py enhanced** with:
   - Module-level docstring (Pydantic validation schemas)
   - Class docstring for each schema explaining purpose and usage
   - Minimum 8 schema docstrings added

5. **database.py enhanced** with:
   - Module-level docstring (Database connection and session management)
   - Function docstrings for get_db(), init_db()
   - Minimum 3 function docstrings added

6. **cfbd_client.py enhanced** with:
   - Module-level docstring (CollegeFootballData API integration)
   - Class docstring for client class
   - Method docstrings for all public methods
   - Minimum 8 method docstrings added

7. **All docstrings follow Google style** with sections: Args, Returns, Raises, Examples (where appropriate)

#### Integration Verification

- **IV1: Test Suite Pass** - Run full test suite (124 tests) - all must pass, docstrings don't affect runtime behavior
- **IV2: Import Compatibility** - Verify no import errors introduced (docstrings are comments, shouldn't break imports)
- **IV3: API Functionality** - Start backend server, verify all API endpoints respond correctly (docstrings don't affect FastAPI operation)

#### Rollback Considerations
- **Low Risk**: Docstrings are comments, don't affect runtime behavior
- **Rollback**: Git revert removes docstrings, no functional impact

---

### Story 1.4: Standardize Import Statements Across Codebase

As a **developer navigating the Stat-urday Synthesis codebase**,
I want **all import statements organized consistently following the established standard (standard lib → third-party → local, alphabetically sorted)**,
so that **imports are easy to read, understand dependencies at a glance, and avoid circular import issues**.

#### Acceptance Criteria

1. **isort applied to all Python files** in project root:
   - Core modules: main.py, ranking_service.py, models.py, schemas.py, database.py, cfbd_client.py
   - Utility scripts: import_real_data.py, seed_data.py, demo.py, compare_rankings.py
   - All root-level .py files (54 files)

2. **isort applied to scripts/ directory**:
   - All 20 Python files in scripts/

3. **isort applied to tests/ directory**:
   - All test files, conftest.py, factories.py

4. **Import organization follows standard**:
   - Group 1: Standard library (os, sys, datetime, etc.)
   - Group 2: Third-party (fastapi, sqlalchemy, pydantic, pytest, etc.)
   - Group 3: Local application (models, schemas, database, ranking_service)
   - Each group alphabetically sorted
   - Groups separated by blank line

5. **Automated check added** to CONTRIBUTING.md recommending developers run `isort .` before commits

#### Integration Verification

- **IV1: Full Test Suite Pass** - Run all 124 tests after import reorganization - all must pass
- **IV2: Application Startup** - Start FastAPI backend with `python main.py` (or current startup method) - must start without errors
- **IV3: Import Verification** - Run `python -c "import main; import ranking_service; import models"` - no import errors

#### Rollback Considerations
- **Low-Medium Risk**: Import reordering can expose hidden circular dependencies
- **Mitigation**: Test thoroughly after reorganization, especially import order
- **Rollback**: Git revert to restore original import order if issues arise

---

### Story 1.5: Reorganize Migration and Diagnostic Scripts

As a **developer or operator managing the Stat-urday Synthesis database and troubleshooting issues**,
I want **migration scripts organized in migrations/ directory and diagnostic scripts organized in diagnostics/ directory**,
so that **I can quickly find the right script without searching through 54 root-level files**.

#### Acceptance Criteria

1. **migrations/ directory created** with README.md explaining:
   - Purpose: Database schema migration scripts
   - Naming convention: migrate_add_*.py
   - Usage: Run once per migration, then archive
   - List of all migrations with dates and purposes

2. **All migration scripts moved** from root to migrations/:
   - migrate_add_*.py (15+ files identified during analysis)
   - migrations/run_migration_001.py (already in migrations/, keep there)
   - Use `git mv` to preserve history

3. **diagnostics/ directory created** with README.md explaining:
   - Purpose: Scripts for checking system state and debugging
   - Naming convention: check_*.py, debug_*.py, diagnose_*.py
   - Usage: Run as needed for troubleshooting

4. **All diagnostic scripts moved** from root to diagnostics/:
   - check_*.py files (10+ files: check_ranking_history.py, check_bowl_games.py, etc.)
   - debug_*.py files (debug_championships.py, etc.)
   - diagnose_*.py files (diagnose_missing_games.py)
   - Use `git mv` to preserve history

5. **Import statements updated** in moved files:
   - Update relative imports to work from new locations
   - Test that each script can still import core modules (models, database, etc.)

6. **README.md updated** with new directory structure documented

#### Integration Verification

- **IV1: Full Test Suite Pass** - Run all 124 tests - all must pass (tests may need import updates)
- **IV2: Test Import Updates** - Update test file imports if they reference moved migration scripts
- **IV3: Script Functionality** - Spot-check 3 moved scripts (1 migration, 2 diagnostics) to verify they still import and run without errors

#### Rollback Considerations
- **Medium Risk**: File moves can break imports if not updated comprehensively
- **Mitigation**: Use automated search/replace for import updates, test thoroughly
- **Rollback**: Git revert to restore original file locations

---

### Story 1.6: Reorganize Core Application Code into src/ Structure

As a **developer working on the Stat-urday Synthesis application logic**,
I want **core application code organized into a src/ directory with logical subdirectories (api/, core/, models/, integrations/)**,
so that **the codebase has clear separation of concerns and follows modern Python project structure conventions**.

#### Acceptance Criteria

1. **src/ directory structure created**:
   ```
   src/
   ├── __init__.py
   ├── api/
   │   ├── __init__.py
   │   └── main.py (moved from root)
   ├── core/
   │   ├── __init__.py
   │   ├── ranking_service.py (moved from root)
   │   ├── ap_poll_service.py (moved from root)
   │   └── transfer_portal_service.py (moved from root)
   ├── models/
   │   ├── __init__.py
   │   ├── database.py (moved from root)
   │   ├── models.py (moved from root)
   │   └── schemas.py (moved from root)
   └── integrations/
       ├── __init__.py
       └── cfbd_client.py (moved from root)
   ```

2. **All files moved using `git mv`** to preserve history

3. **Import statements updated comprehensively**:
   - All imports of moved modules updated throughout codebase
   - Example: `from models import Team` → `from src.models.models import Team`
   - Example: `import ranking_service` → `from src.core import ranking_service`
   - Use automated refactoring tools (rope, bowler) or careful search/replace

4. **__init__.py files created** to make directories proper Python packages

5. **gunicorn_config.py updated** if needed (or kept in root with updated import paths)

6. **Import statements in tests/ updated** to reference new src/ structure

7. **pytest.ini updated** if needed for test discovery from new structure

8. **README.md and DEVELOPMENT.md updated** with new directory structure

#### Integration Verification

- **IV1: Full Test Suite Pass** - Run all 124 tests - ALL must pass (critical validation)
- **IV2: Application Startup** - Start backend with updated command (may need `python -m src.api.main` or update gunicorn config) - must start without errors
- **IV3: API Endpoint Functionality** - Test 5 key endpoints (GET /api/rankings, GET /api/teams, POST /api/games, GET /api/predictions, GET /api/admin/api-usage) - all must respond correctly
- **IV4: Frontend Integration** - Load frontend in browser, verify all pages load and API calls work (rankings page, team detail, predictions, comparison)

#### Rollback Considerations
- **Medium-High Risk**: Most complex reorganization, affects many import statements
- **Mitigation**:
  - Comprehensive automated testing after changes
  - Manual verification of key workflows
  - Test in development environment before production
- **Rollback**: Git revert to restore original structure (single commit for this story enables clean rollback)

---

### Story 1.7: Archive Obsolete Scripts and Finalize Documentation

As a **developer or operator maintaining the Stat-urday Synthesis codebase**,
I want **obsolete one-off fix scripts archived with clear documentation, and all project documentation updated to reflect the new clean structure**,
so that **the codebase contains only actively-used code, and documentation accurately guides developers**.

#### Acceptance Criteria

1. **archive/ directory created** with README.md explaining:
   - Purpose: Historical one-off scripts kept for reference only
   - **Do not run these scripts** - they were created for specific past issues
   - List of archived scripts with dates and original purposes

2. **Obsolete scripts identified and moved** to archive/:
   - fix_*.py files (fix_2025_records.py, fix_playoff_weeks.py, fix_championship_week_rankings.py, etc.)
   - One-off historical scripts (count_team_games.py, find_championship_teams.py, etc.)
   - Use `git mv` to preserve history
   - Estimated 15-20 files

3. **utilities/ directory created** for reusable helper scripts:
   - seed_data.py (moved from root)
   - demo.py (moved from root)
   - compare_rankings.py (moved from root)
   - compare_transfer_rankings.py (moved from root)
   - evaluate_rating_systems.py (moved from root)

4. **Root directory cleaned** - only essential files remain:
   - import_real_data.py (main data import entry point)
   - gunicorn_config.py (deployment requirement)
   - requirements.txt, requirements-dev.txt
   - pytest.ini, .env, .gitignore
   - README.md, CONTRIBUTING.md, DEVELOPMENT.md

5. **All documentation updated** to reflect final structure:
   - README.md: Update "Project Structure" section with new directories
   - DEVELOPMENT.md: Update all file path references
   - architecture.md: Update "Source Tree and Module Organization" section
   - CONTRIBUTING.md: Update development workflow with new paths

6. **Black formatting applied** to all Python files (now that reorganization is complete):
   - Run `black .` on entire codebase
   - Commit formatting changes separately from functional changes

7. **Flake8 linting report generated** and major issues documented:
   - Run `flake8 .` and capture output
   - Document known linting issues in DEVELOPMENT.md "Technical Debt" section
   - Fix critical issues (syntax errors, undefined names) if any found

#### Integration Verification

- **IV1: Final Test Suite Pass** - Run all 124 tests - ALL must pass after all reorganization complete
- **IV2: Full Application Workflow Test** - Complete end-to-end workflow:
  - Start backend server
  - Load frontend in browser
  - Navigate all pages (rankings, teams, games, team detail, predictions, comparison)
  - Verify all features work identically to pre-cleanup state
- **IV3: Documentation Accuracy** - Manually verify 5 file paths referenced in documentation actually exist at specified locations
- **IV4: Clean Root Directory** - Verify root directory contains <15 files (down from 54)

#### Rollback Considerations
- **Medium Risk**: Final consolidation of changes, multiple file moves
- **Mitigation**: This is the last story, all previous stories tested individually
- **Rollback**: Git revert sequence can restore original state story-by-story
- **Success Criteria**: If all IV checks pass, cleanup is complete and safe to deploy

---

## 6. Epic Completion Criteria

The epic is successfully completed when:

1. ✅ All 7 stories completed with acceptance criteria met
2. ✅ Full test suite (124 tests) passes with 100% success rate
3. ✅ Root directory reduced from 54 files to <15 files
4. ✅ All core modules have comprehensive docstrings (Google style)
5. ✅ Coding standards documented and tooling configured
6. ✅ Developer onboarding documentation created (CONTRIBUTING.md, DEVELOPMENT.md)
7. ✅ File organization follows modern Python project structure (src/, migrations/, diagnostics/, utilities/, archive/)
8. ✅ All documentation updated to reflect new structure
9. ✅ Zero regression in existing functionality (API, frontend, database, integrations all work identically)
10. ✅ Production deployment tested and verified (if applicable)

---

## 7. Next Steps

After PRD approval:

1. **Review with stakeholders** - Confirm epic scope and story sequencing
2. **Create epic tracking document** - EPIC-028-CODEBASE-CLEANUP.md
3. **Create individual story documents** - docs/stories/28.1.story.md through 28.7.story.md
4. **Begin execution** - Start with Story 1.1 (lowest risk, highest value documentation)
5. **Continuous validation** - Run test suite after each story completion
6. **Production deployment** - After all stories complete and validation passes

---

**END OF PRD**
