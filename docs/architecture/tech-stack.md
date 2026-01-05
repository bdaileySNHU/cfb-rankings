# Technology Stack

## Overview

College Football Rankings System (Stat-urday Synthesis) is a full-stack web application that calculates and displays Modified ELO rankings for college football teams.

---

## Backend Stack

### Core Framework
- **FastAPI 0.125.0** - Modern, async Python web framework
  - Fast (high-performance)
  - Built-in API documentation (Swagger/OpenAPI)
  - Type hints and validation via Pydantic
  - Async/await support

### Python Runtime
- **Python 3.11** - Primary development and production runtime
- **Virtual Environment** - Isolated dependency management

### Web Server
- **Uvicorn 0.24.0** - ASGI server for FastAPI
  - Production deployment with uvloop for performance
  - WebSocket support (if needed)

- **Gunicorn 21.2.0** - Production process manager
  - Multiple worker processes
  - Graceful restarts
  - Worker configuration: `uvicorn.workers.UvicornWorker`

### Database
- **SQLite** - Embedded SQL database
  - File-based: `cfb_rankings.db`
  - No separate database server required
  - Suitable for read-heavy workloads
  - Simple deployment and backup

- **SQLAlchemy 2.0.23** - Python SQL toolkit and ORM
  - Declarative model definitions
  - Relationship mapping
  - Query builder
  - Migration support

### Data Validation
- **Pydantic 2.5.0** - Data validation using Python type annotations
  - Request/response schemas
  - Configuration management
  - Automatic data conversion

### External Integrations
- **CollegeFootballData.com API (CFBD)** - Primary data source
  - Game schedules and results
  - Team information
  - AP Poll rankings
  - Transfer portal data
  - RESTful API with rate limiting

- **Requests 2.31.0+** - HTTP client for API calls

### Configuration
- **python-dotenv 1.0.0** - Environment variable management
  - `.env` file for local development
  - Environment variables for production
  - API key management

---

## Frontend Stack

### Core Technologies
- **Vanilla JavaScript (ES6+)** - No frameworks
  - Modern JavaScript features
  - Async/await for API calls
  - Module pattern for organization

- **HTML5** - Semantic markup
  - Accessible structure
  - SEO-friendly

- **CSS3** - Custom styling
  - CSS variables for theming
  - Responsive design
  - Mobile-first approach

### Libraries
- **Chart.js** - Data visualization
  - Line charts for accuracy over time
  - Responsive and interactive
  - Loaded via CDN

### Architecture Pattern
- **Client-side rendering** - Static HTML pages
  - JavaScript fetches data from API
  - Dynamic DOM manipulation
  - No build process required

---

## Development Tools

### Testing
- **pytest 9.0.1** - Python testing framework
  - Unit tests
  - Integration tests
  - E2E tests
  - Fixtures and parametrization

- **pytest-asyncio 1.3.0** - Async test support

### Code Quality
- **Black** - Python code formatter
  - Consistent code style
  - Automated formatting

- **Flake8** - Python linter
  - Code quality checks
  - PEP 8 compliance

- **isort** - Import sorting
  - Organized imports
  - Consistent ordering

### Development
- **Make** - Build automation
  - Test runner
  - Linting
  - Deployment helpers

---

## Deployment Stack

### Production Environment
- **Linux Server** (Ubuntu/Debian)
- **systemd** - Service management
  - `cfb-rankings.service` - Main application service
  - `cfb-weekly-update.timer` - Scheduled data updates

### Web Server
- **Nginx** (assumed) - Reverse proxy
  - Static file serving (frontend)
  - Proxy to Gunicorn/Uvicorn
  - SSL/TLS termination

### Process Management
- **systemd** for application lifecycle
- **Gunicorn** with multiple Uvicorn workers
- Graceful reloads and restarts

---

## Data Flow Architecture

```
CFBD API
    ↓
Python Scripts (import_real_data.py, weekly_update.py)
    ↓
SQLite Database (cfb_rankings.db)
    ↓
FastAPI Backend (src/api/main.py)
    ↓
REST API Endpoints
    ↓
Frontend JavaScript (fetch API)
    ↓
Browser (HTML/CSS/JS)
```

---

## API Design

### RESTful Endpoints
- **GET /api/rankings** - Current rankings
- **GET /api/teams** - All teams
- **GET /api/games** - Game results
- **GET /api/predictions** - Upcoming game predictions
- **GET /api/predictions/comparison** - ELO vs AP Poll comparison
- **GET /api/seasons** - Available seasons

### Response Format
- JSON responses
- Pydantic schemas for validation
- Consistent error handling
- HTTP status codes (200, 404, 500)

---

## File Storage

### Database
- **cfb_rankings.db** - Main SQLite database
- **Backups** - `cfb_rankings.db.backup_*`

### Configuration
- **.env** - Environment variables (not committed)
- **.env.example** - Template for configuration

### Logs
- **systemd journal** - Application logs
- **Debug logs** - `.ai/debug-log.md` (development)

---

## Third-Party Services

### CFBD API
- **Endpoint:** `api.collegefootballdata.com`
- **Authentication:** API key (Bearer token)
- **Rate Limiting:** Monitored and tracked
- **Data:** Games, teams, rankings, recruiting, transfers

---

## Version Control

### Repository
- **Git** - Version control
- **GitHub** - Remote repository hosting
- **Branches:** `main` (production)

---

## Performance Considerations

### Backend
- **Async I/O** - FastAPI/Uvicorn for concurrent requests
- **Database Indexes** - Optimized queries
- **Caching** - Minimal (database is primary source of truth)

### Frontend
- **Static Assets** - No bundling, direct serving
- **API Calls** - Batched when possible
- **Lazy Loading** - Data fetched on demand

---

## Security

### API Security
- **Environment Variables** - Sensitive data (API keys)
- **No hardcoded secrets**
- **HTTPS** - Production deployment (via Nginx)

### Database
- **SQLite** - Local file access only
- **No public database exposure**

---

## Scalability Notes

### Current Architecture
- **Single-server deployment**
- **Read-heavy workload** - Well-suited for SQLite
- **Writes:** Batch imports (weekly updates)

### Future Considerations
- **PostgreSQL** - If concurrent writes increase
- **Redis** - Caching layer for frequently accessed data
- **CDN** - Static asset delivery
- **Horizontal scaling** - Multiple app servers behind load balancer

---

## Documentation

### Code Documentation
- **Docstrings** - Python functions and classes
- **Comments** - Inline for complex logic
- **Type hints** - Function signatures

### API Documentation
- **OpenAPI/Swagger** - Auto-generated from FastAPI
- **Available at:** `/docs` (Swagger UI)

---

## Dependencies Management

### Python
- **requirements.txt** - Production dependencies
- **requirements-dev.txt** - Development dependencies
- **pip** - Package manager

### Frontend
- **No package manager** - CDN-based libraries
- **Manual updates** - Chart.js versions

---

## Build & Deployment

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start server
uvicorn src.api.main:app --reload
```

### Production
```bash
# Pull latest code
git pull

# Restart service
sudo systemctl restart cfb-rankings.service
```

---

## Monitoring & Observability

### Logging
- **Python logging module**
- **systemd journal**
- **Log levels:** INFO, WARNING, ERROR

### Health Checks
- **API endpoint** - `/health` (assumed)
- **systemd status**

---

## Summary

**Backend:** FastAPI + SQLite + Python 3.11
**Frontend:** Vanilla JS + HTML5 + CSS3
**Data Source:** CFBD API
**Deployment:** Linux + systemd + Gunicorn/Uvicorn
**Testing:** pytest
**Code Quality:** Black + Flake8 + isort
