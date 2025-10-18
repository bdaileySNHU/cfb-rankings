# College Football Ranking System - Test Suite

## Overview

This test suite provides comprehensive coverage for the College Football Ranking System, including unit tests for the ELO algorithm, integration tests for all API endpoints, and end-to-end tests for critical user workflows.

**Current Coverage Goals:**
- >80% coverage for `ranking_service.py` (ELO algorithm)
- >70% overall code coverage
- All 15 API endpoints tested
- Critical user workflows validated

## Test Organization

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (test_db, test_client, factories)
├── factories.py             # Factory Boy test data generators ✅
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_ranking_service.py  # ELO algorithm tests
│   ├── test_models.py           # Database model tests
│   └── test_schemas.py          # Pydantic schema tests
├── integration/             # Integration tests (API + DB)
│   ├── test_teams_api.py        # Team endpoints
│   ├── test_games_api.py        # Game endpoints
│   ├── test_rankings_seasons_api.py  # Rankings & seasons endpoints
│   └── test_cfbd_import.py      # CFBD data import with mocked API ✅
└── e2e/                     # End-to-end tests (browser)
    ├── test_rankings_page.py    # Rankings page workflow
    └── test_team_detail.py      # Team detail workflow
```

## Installation

### Install Test Dependencies

```bash
# Install all development and test dependencies
pip install -r requirements-dev.txt

# For E2E tests, also install Playwright browsers
playwright install
```

## Running Tests

### Run All Tests

```bash
# Run entire test suite
pytest

# Run with verbose output
pytest -v

# Run with very verbose output (show all test details)
pytest -vv
```

### Run Tests by Category

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only E2E tests (requires running server)
pytest -m e2e

# Run all tests except E2E (default for CI/CD)
pytest -m "not e2e"

# Run all tests including E2E
pytest
```

**Note on E2E Tests:**
E2E tests require a running FastAPI server and are marked with `@pytest.mark.e2e`.
They are skipped by default in quick test runs. To run E2E tests:

```bash
# Option 1: Start server manually in another terminal
python3 main.py

# Then run E2E tests
pytest tests/e2e/ -v

# Option 2: Run all tests (E2E tests will attempt to start server automatically)
pytest -m e2e
```

### Run Tests by Directory

```bash
# Run all unit tests
pytest tests/unit/

# Run all integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_ranking_service.py

# Run specific test function
pytest tests/unit/test_ranking_service.py::test_preseason_rating_calculation
```

### Run Tests in Parallel

```bash
# Run tests in parallel (faster execution)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

## Coverage Reporting

### Generate Coverage Reports

```bash
# Run tests with coverage measurement
pytest --cov=.

# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View HTML report (opens in browser)
open htmlcov/index.html

# Generate terminal coverage report
pytest --cov=. --cov-report=term

# Generate coverage report with missing lines
pytest --cov=. --cov-report=term-missing
```

### Coverage Configuration

Coverage settings are in `.coveragerc`:
- Excludes test files, virtual environments, and scripts
- Measures branch coverage (both True/False paths)
- HTML reports generated in `htmlcov/` directory

## Test Fixtures

### Available Fixtures (from `conftest.py`)

**`test_db`**: In-memory SQLite database
```python
def test_example(test_db):
    # test_db is a SQLAlchemy Session
    team = Team(name="Alabama", conference=ConferenceType.POWER_5)
    test_db.add(team)
    test_db.commit()
```

**`test_client`**: FastAPI TestClient with test database
```python
def test_api_endpoint(test_client):
    # test_client is configured to use test database
    response = test_client.get("/api/teams")
    assert response.status_code == 200
```

**`db_session`**: Alias for `test_db`
```python
def test_with_session(db_session):
    # Same as test_db, alternative name
    pass
```

**`factories`**: Factory Boy test data factories
```python
def test_with_factories(factories):
    # Create test data easily
    team = factories['team']()
    elite_team = factories['elite_team'](name="Alabama")
    game = factories['game'](home_team=team, away_team=elite_team)
```

**`mock_cfbd_client`**: Mocked CollegeFootballData.com API client
```python
def test_with_mock_api(mock_cfbd_client):
    # Use mocked CFBD API client (no network calls)
    teams = mock_cfbd_client.get_teams(2025)
    games = mock_cfbd_client.get_games(2025, week=1)
    recruiting = mock_cfbd_client.get_recruiting_rankings(2025)

    # All methods return deterministic test data
    assert len(teams) == 5
    assert teams[0]['school'] == 'Alabama'
```

## Mocking External APIs

### CFBD API Client Mock

The test suite includes a mock for the CollegeFootballData.com API client to eliminate external dependencies and ensure consistent, fast test execution.

**Why Mock the CFBD API?**
- **No Network Calls**: Tests run offline, no internet required
- **No Rate Limits**: CFBD API has 100 req/hour limit, would block tests
- **Deterministic**: Same data every time, no flaky tests
- **Fast**: Mock responses are instant, no network latency
- **Reliable**: Tests don't fail when external API is down

**Using the Mock Client**

The `mock_cfbd_client` fixture is available in all tests:

```python
def test_import_teams(test_db, mock_cfbd_client):
    """Test importing teams using mocked CFBD data"""
    from import_real_data import import_teams

    # Use mock client instead of real API
    team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

    # Verify teams were created from mock data
    assert len(team_objects) == 5
    assert 'Alabama' in team_objects
    assert 'Georgia' in team_objects
```

**Mock Data Provided**

The mock client returns realistic test data for all CFBD API methods:

- `get_teams(year)`: Returns 5 FBS teams (Alabama, Georgia, Ohio State, Michigan, Boise State)
- `get_games(year, week)`: Returns 2 completed games
- `get_recruiting_rankings(year)`: Returns recruiting rankings (Alabama #1, Georgia #2, etc.)
- `get_team_talent(year)`: Returns talent composite scores (Alabama 95.5, Georgia 94.8, etc.)
- `get_returning_production(year)`: Returns returning production percentages
- `get_transfer_portal(year)`: Returns transfer portal rankings

**Customizing Mock Responses**

You can customize mock responses for specific test scenarios:

```python
def test_import_with_incomplete_game(test_db, mock_cfbd_client):
    """Test handling of incomplete games"""
    # Customize mock response for this test
    mock_cfbd_client.get_games.return_value = [
        {
            'homeTeam': 'Alabama',
            'awayTeam': 'Georgia',
            'homePoints': None,  # Game not completed
            'awayPoints': None,
            'week': 1,
            'neutralSite': False
        }
    ]

    # Test should handle incomplete game gracefully
    from import_real_data import import_games, import_teams
    teams = import_teams(mock_cfbd_client, test_db, year=2025)
    total = import_games(mock_cfbd_client, test_db, teams, year=2025, max_week=1)

    assert total == 0  # Incomplete game skipped
```

**Mock Data Maintenance**

The mock data is based on real API responses and should be updated if:
- CFBD API response format changes
- New fields are added to the API
- Test coverage needs different scenarios

To update mock data:
1. Make a real API call and capture the response
2. Simplify the response to essential fields
3. Update the mock in `tests/conftest.py` (lines 156-258)
4. Run tests to verify: `pytest tests/integration/test_cfbd_import.py -v`

## End-to-End Testing with Playwright

### Overview

E2E tests use Playwright to automate browser interactions and verify the full stack:
- Frontend HTML/CSS/JavaScript
- API endpoints
- Database operations
- Complete user workflows

**Test Files:**
- `tests/e2e/test_rankings_page.py` - Rankings page tests (21 tests)
- `tests/e2e/test_team_detail.py` - Team detail page tests (10 tests)

### Running E2E Tests

**Prerequisites:**
```bash
# Install Playwright (already in requirements-dev.txt)
pip install playwright==1.40.0

# Install Chromium browser
python3 -m playwright install chromium
```

**Run E2E Tests:**
```bash
# Option 1: Manual server (recommended for development)
# Terminal 1: Start server
python3 main.py

# Terminal 2: Run E2E tests
pytest tests/e2e/ -v

# Option 2: Automatic server (uses live_server fixture)
pytest -m e2e -v
```

**Skip E2E Tests (default for fast runs):**
```bash
# Run all tests except E2E
pytest -m "not e2e"
```

### E2E Test Fixtures

**`live_server`** (session scope):
- Starts FastAPI server on port 8765
- Runs in background thread for test duration
- Returns base URL for tests

**`browser_page`** (function scope):
- Creates new Playwright browser page for each test
- Headless mode by default (CI/CD compatible)
- Provides (page, base_url) tuple

**Example E2E Test:**
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_rankings_page_loads(browser_page, test_db):
    """Test that rankings page loads and displays data"""
    # Arrange
    page, base_url = browser_page

    # Create test data
    from models import Team, Season, ConferenceType
    season = Season(year=2024, is_active=True)
    team = Team(name="Alabama", conference=ConferenceType.POWER_5,
                elo_rating=1850.0, wins=5, losses=0)
    test_db.add_all([season, team])
    test_db.commit()

    # Act - Navigate to rankings page
    page.goto(f"{base_url}/frontend/index.html")
    page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

    # Assert - Team appears in table
    assert "Alabama" in page.content()
    assert "1850" in page.content()
```

### E2E Test Coverage

**Rankings Page** (`test_rankings_page.py`):
- ✅ Page loads with correct title and header
- ✅ Navigation menu displays
- ✅ Rankings table renders with API data
- ✅ Teams sorted by ELO rating
- ✅ Conference badges display
- ✅ Clicking team navigates to detail page
- ✅ Empty state handling
- ✅ API integration verification

**Team Detail Page** (`test_team_detail.py`):
- ✅ Page loads with team data
- ✅ Team stats display (name, conference, record, rating)
- ✅ Schedule/games table shows opponents
- ✅ Game scores displayed
- ✅ Navigation back to rankings works
- ✅ Invalid team ID handling
- ✅ API calls made correctly
- ✅ Full user workflow (rankings → team → back)

### Debugging E2E Tests

**View browser during test (headed mode):**
```python
# Modify browser_page fixture in conftest.py temporarily:
browser = p.chromium.launch(headless=False)  # Change to False
```

**Take screenshot on failure:**
```python
def test_example(browser_page):
    page, base_url = browser_page
    try:
        # Test code
        page.goto(f"{base_url}/frontend/index.html")
        assert False  # Force failure for demo
    except AssertionError:
        page.screenshot(path="screenshots/failure.png")
        raise
```

**Enable verbose Playwright logging:**
```bash
DEBUG=pw:api pytest tests/e2e/ -v
```

### E2E Test Best Practices

1. **Use `expect()` from Playwright** - Built-in auto-waiting and retries
2. **Wait for specific elements** - `page.wait_for_selector()` instead of `time.sleep()`
3. **Create test data in database** - Use `test_db` fixture for realistic scenarios
4. **Test user workflows** - Combine multiple interactions (click → navigate → verify)
5. **Headless by default** - Keeps tests fast and CI/CD compatible
6. **Isolate tests** - Each test gets fresh browser page (function scope)
7. **Check page content** - Verify API data rendered in DOM

## Test Data Factories

Factory Boy factories provide convenient test data generation with realistic defaults.

### Available Factories

**TeamFactory** - Create teams with defaults
```python
from factories import TeamFactory, configure_factories

configure_factories(test_db)

# Basic team
team = TeamFactory()

# Custom attributes
elite_team = TeamFactory(name="Alabama", elo_rating=1850.0)

# Using traits
p5_team = TeamFactory(p5=True)
g5_team = TeamFactory(g5=True)
fcs_team = TeamFactory(fcs=True)
elite_team = TeamFactory(elite=True)
struggling_team = TeamFactory(struggling=True)
```

**GameFactory** - Create games with related teams
```python
# Basic game (creates home and away teams automatically)
game = GameFactory()

# With specific teams
game = GameFactory(home_team=team1, away_team=team2)

# Using traits
blowout = GameFactory(home_blowout=True)
upset = GameFactory(away_upset=True)
neutral_game = GameFactory(neutral=True)
processed_game = GameFactory(processed=True)
```

**SeasonFactory** - Create seasons
```python
# Basic season
season = SeasonFactory()

# With traits
mid_season = SeasonFactory(mid_season=True)  # week=6
completed = SeasonFactory(completed=True)     # week=15, is_active=False
```

**RankingHistoryFactory** - Create ranking history
```python
# Basic history
history = RankingHistoryFactory(team=team, week=5)

# Using traits
top_five = RankingHistoryFactory(top_five=True)
unranked = RankingHistoryFactory(unranked=True)
```

### Convenience Factories

Pre-configured factory classes for common scenarios:

- **EliteTeamFactory**: Power 5 elite team (1850 ELO, 10-1 record)
- **G5ChampionFactory**: Strong G5 team (1600 ELO, 11-2 record)
- **FCSTeamFactory**: FCS team (1300 ELO)
- **ProcessedGameFactory**: Game with rating changes already applied
- **NeutralSiteGameFactory**: Neutral site game

### Factory Traits

Traits modify factory behavior:

**Team Traits:**
- `elite=True`: Top recruiting, high rating, winning record
- `struggling=True`: Poor recruiting, low rating, losing record
- `p5=True`: Power 5 conference
- `g5=True`: Group of 5 conference
- `fcs=True`: FCS conference

**Game Traits:**
- `home_blowout=True`: Home wins 42-14
- `away_upset=True`: Away wins 24-17
- `neutral=True`: Neutral site game
- `processed=True`: Game already processed with rating changes

**Season Traits:**
- `mid_season=True`: Week 6, active
- `completed=True`: Week 15, inactive

**RankingHistory Traits:**
- `top_five=True`: Highly ranked team
- `unranked=True`: Outside top 75

### Factory Sequences

Factories use sequences for unique values:
- Teams: "Team 1", "Team 2", "Team 3"...
- Seasons: 2020, 2021, 2022...

### Using Factories in Tests

```python
def test_example_with_factories(test_db):
    from factories import configure_factories, TeamFactory, GameFactory

    # Configure factories with test database
    configure_factories(test_db)

    # Create test data
    team1 = TeamFactory(name="Alabama")
    team2 = TeamFactory(name="Georgia")
    game = GameFactory(
        home_team=team1,
        away_team=team2,
        home_score=27,
        away_score=24
    )

    # Run test assertions
    assert game.home_team.name == "Alabama"
    assert game.winner_id == team1.id
```

## Writing New Tests

### Unit Test Example

```python
# tests/unit/test_example.py
import pytest
from ranking_service import RankingService

@pytest.mark.unit
def test_calculate_preseason_rating():
    """Test that preseason rating calculation is correct"""
    # Arrange
    service = RankingService()
    recruiting_rank = 5
    transfer_rank = 10

    # Act
    rating = service.calculate_preseason_rating(
        recruiting_rank=recruiting_rank,
        transfer_rank=transfer_rank
    )

    # Assert
    assert rating == 1500 + 200 + 75  # Base + recruiting + transfer
```

### Integration Test Example

```python
# tests/integration/test_teams_api.py
import pytest

@pytest.mark.integration
def test_get_teams(test_client, test_db):
    """Test GET /api/teams endpoint"""
    # Arrange - create test data
    team = Team(name="Georgia", conference=ConferenceType.POWER_5)
    test_db.add(team)
    test_db.commit()

    # Act
    response = test_client.get("/api/teams")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Georgia"
```

### Parametrized Test Example

```python
@pytest.mark.parametrize("recruiting_rank,expected_bonus", [
    (1, 200),    # Top 5
    (10, 150),   # Top 10
    (25, 100),   # Top 25
    (50, 50),    # Top 50
    (100, 0),    # Unranked
])
def test_recruiting_bonus(recruiting_rank, expected_bonus):
    """Test recruiting bonus calculation for different ranks"""
    bonus = calculate_recruiting_bonus(recruiting_rank)
    assert bonus == expected_bonus
```

## Test Markers

Tests can be marked for categorization:

```python
@pytest.mark.unit          # Fast, isolated unit test
@pytest.mark.integration   # API + database test
@pytest.mark.e2e           # Browser-based E2E test
@pytest.mark.slow          # Test takes >1 second
```

Run specific markers:
```bash
pytest -m unit          # Only unit tests
pytest -m "not slow"    # Exclude slow tests
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: playwright install
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure you're in the project root directory
cd /path/to/Stat-urday\ Synthesis

# Install dependencies
pip install -r requirements-dev.txt
```

**Database errors:**
- Tests use in-memory SQLite (`:memory:`)
- Each test gets a fresh database
- No need to manage test database files

**Slow tests:**
```bash
# Run only fast unit tests
pytest -m unit

# Run tests in parallel
pytest -n auto
```

**E2E test failures:**
```bash
# Install Playwright browsers
python3 -m playwright install chromium

# Ensure server is running
python3 main.py  # In separate terminal

# Run E2E tests
pytest tests/e2e/ -v
```

**Server not starting:**
- E2E tests use port 8765 by default
- Check if port is already in use: `lsof -i :8765`
- Kill process if needed: `kill -9 $(lsof -t -i:8765)`

## Best Practices

1. **Test Isolation**: Each test should be independent (use fixtures for setup)
2. **AAA Pattern**: Arrange, Act, Assert structure
3. **Descriptive Names**: `test_<what>_<scenario>()` format
4. **One Assertion Focus**: Each test should verify one behavior
5. **Fast Tests**: Keep unit tests fast (<100ms each)
6. **Mock External APIs**: Always use `mock_cfbd_client` fixture instead of real API calls
7. **Deterministic**: Tests should produce same result every time
8. **Database Isolation**: Tests automatically use in-memory SQLite, no shared state
9. **Comprehensive Coverage**: Aim for >80% coverage on critical business logic
10. **Test Error Cases**: Don't just test happy paths, test validation and error handling

## Adding New Tests

1. Choose appropriate directory: `unit/`, `integration/`, or `e2e/`
2. Create file: `test_<module_name>.py`
3. Import necessary fixtures from `conftest.py`
4. Write test function: `def test_<functionality>_<scenario>():`
5. Add appropriate markers: `@pytest.mark.unit`
6. Run test to verify: `pytest tests/path/to/test_file.py -v`

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Playwright Documentation](https://playwright.dev/python/)

## Questions or Issues?

If you encounter issues with the test suite, please:
1. Check this README for common troubleshooting steps
2. Review the test configuration files (pytest.ini, .coveragerc)
3. Open an issue in the project repository
