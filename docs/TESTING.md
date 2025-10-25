# Testing Documentation

## Overview

This project uses a comprehensive testing strategy with three levels of testing:

1. **Unit Tests** - Fast, isolated tests for individual functions and classes
2. **Integration Tests** - API + database integration tests
3. **E2E Tests** - End-to-end browser-based tests for complete user workflows

**Total Test Coverage:** 124 tests
- 78 unit/integration tests
- 46 end-to-end tests

---

## Quick Start

### Running All Tests

```bash
# Run all tests (unit + integration, skips E2E by default)
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# View coverage report in browser
open htmlcov/index.html
```

### Running Specific Test Categories

```bash
# Run only unit tests (fastest)
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run E2E tests (requires browser, slower)
pytest -m e2e -v

# Skip slow tests
pytest -m "not slow" -v

# Skip E2E tests (default for quick runs)
pytest -m "not e2e" -v
```

### Running Specific Test Files

```bash
# Run tests for a specific module
pytest tests/test_ranking_service.py -v

# Run tests for API endpoints
pytest tests/test_api_endpoints.py -v

# Run all E2E tests
pytest tests/e2e/ -v

# Run specific E2E test file
pytest tests/e2e/test_rankings_page.py -v
```

---

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                      # Shared fixtures and configuration
├── factories.py                     # Test data factories
│
├── test_update_games.py            # Update script tests (10 tests)
├── test_cfbd_client.py             # CFBD API client tests (19 tests)
├── test_ranking_service.py         # Ranking/prediction logic tests (19 tests)
├── test_api_endpoints.py           # FastAPI endpoint tests (30 tests)
│
└── e2e/                            # End-to-end tests (46 tests)
    ├── __init__.py
    ├── test_rankings_page.py       # Rankings page E2E tests (11 tests)
    ├── test_team_detail.py         # Team detail page E2E tests (10 tests)
    ├── test_predictions_workflow.py # Predictions page E2E tests (12 tests)
    └── test_comparison_page.py     # AP Poll comparison E2E tests (13 tests)
```

### Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - API + database integration tests
- `@pytest.mark.e2e` - End-to-end browser-based tests
- `@pytest.mark.slow` - Tests that take more than 1 second

**Usage:**
```bash
# Run only fast unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

---

## Test Files Overview

### Unit/Integration Tests

#### `test_update_games.py` (10 tests)
Tests the `scripts/update_games.py` script that imports future games from CFBD API.

**Key Tests:**
- camelCase field parsing validation (prevents regression of field name bug)
- Null team name handling
- Duplicate game detection
- FCS team creation
- Date parsing (ISO 8601)
- Future game processing

**Why Important:** Validates the critical camelCase bug fix that was causing database errors.

```bash
pytest tests/test_update_games.py -v
```

#### `test_cfbd_client.py` (19 tests)
Tests the College Football Data API client.

**Key Tests:**
- Client initialization (API key handling)
- Current week detection from completed games
- Season estimation (Labor Day calculation)
- API endpoint methods (get_teams, get_games, get_ap_poll)
- camelCase field naming documentation
- Error handling (network failures, HTTP errors)

```bash
pytest tests/test_cfbd_client.py -v
```

#### `test_ranking_service.py` (19 tests)
Tests core business logic for predictions and rankings.

**Key Tests:**
- Prediction generation with various filters
- Week filtering (next_week parameter)
- Team ID filtering
- Validation constants (MIN/MAX bounds)
- Empty game list edge cases
- Invalid teams handling

```bash
pytest tests/test_ranking_service.py -v
```

#### `test_api_endpoints.py` (30 tests)
Tests FastAPI HTTP endpoints.

**Key Tests:**
- Health check endpoint
- Predictions endpoint (6 tests) - filtering, validation, error handling
- Rankings endpoint (4 tests) - limits, validation
- Stats endpoint
- Prediction accuracy endpoints
- Error responses (422, 404, 500 status codes)
- Response format validation

```bash
pytest tests/test_api_endpoints.py -v
```

### End-to-End Tests

#### `test_rankings_page.py` (11 tests)
E2E tests for the rankings page workflow.

**Tests:**
- Page loads with correct title
- Rankings table displays with API data
- Teams sorted by ELO rating
- Click team navigates to detail page
- API integration verification

```bash
pytest tests/e2e/test_rankings_page.py -v
```

#### `test_team_detail.py` (10 tests)
E2E tests for team detail page workflow.

**Tests:**
- Team detail page loads
- Team stats display correctly
- Schedule shows games and opponents
- Navigation back to rankings
- Invalid team ID handling

```bash
pytest tests/e2e/test_team_detail.py -v
```

#### `test_predictions_workflow.py` (12 tests)
E2E tests for predictions/games page workflow.

**Tests:**
- Predictions page loads
- Upcoming games display
- Completed games show scores
- Prediction cards show team names
- API integration

```bash
pytest tests/e2e/test_predictions_workflow.py -v
```

#### `test_comparison_page.py` (13 tests)
E2E tests for AP Poll comparison page workflow.

**Tests:**
- Comparison page loads
- ELO vs AP Poll stats display
- Accuracy metrics shown
- Chart rendering
- Season filtering

```bash
pytest tests/e2e/test_comparison_page.py -v
```

---

## Writing New Tests

### Unit Test Example

```python
import pytest
from unittest.mock import Mock

def test_calculate_elo_rating():
    """Test ELO rating calculation for a game"""
    # Arrange
    winner_rating = 1800.0
    loser_rating = 1750.0

    # Act
    new_winner_rating, new_loser_rating = calculate_elo_change(
        winner_rating, loser_rating, k_factor=32
    )

    # Assert
    assert new_winner_rating > winner_rating
    assert new_loser_rating < loser_rating
```

### Integration Test Example

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_get_rankings_endpoint(test_client, test_db):
    """Test /api/rankings endpoint returns data"""
    # Arrange
    from models import Team, Season, ConferenceType

    season = Season(year=2025, current_week=10, is_active=True)
    test_db.add(season)

    team = Team(
        name="Ohio State",
        conference=ConferenceType.POWER_5,
        elo_rating=1850.0
    )
    test_db.add(team)
    test_db.commit()

    # Act
    response = test_client.get("/api/rankings")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["rankings"]) > 0
```

### E2E Test Example

```python
import pytest
from playwright.sync_api import expect

@pytest.mark.e2e
@pytest.mark.slow
def test_user_can_view_rankings(browser_page, test_db):
    """Test complete user workflow for viewing rankings"""
    # Arrange
    page, base_url = browser_page
    from models import Team, Season, ConferenceType

    season = Season(year=2025, is_active=True)
    test_db.add(season)

    team = Team(
        name="Alabama",
        conference=ConferenceType.POWER_5,
        elo_rating=1850.0
    )
    test_db.add(team)
    test_db.commit()

    # Act - Navigate to rankings page
    page.goto(f"{base_url}/frontend/index.html")
    page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

    # Assert - Team appears in table
    first_row = page.locator("#rankings-table tbody tr").first
    expect(first_row).to_contain_text("Alabama")
```

---

## Test Fixtures

### Available Fixtures

The following pytest fixtures are available in `tests/conftest.py`:

#### `test_db`
Provides an in-memory SQLite database for testing.

```python
def test_example(test_db):
    from models import Team

    team = Team(name="Test Team")
    test_db.add(team)
    test_db.commit()

    assert team.id is not None
```

#### `test_client`
Provides a FastAPI TestClient with test database override.

```python
def test_api_endpoint(test_client):
    response = test_client.get("/api/teams")
    assert response.status_code == 200
```

#### `browser_page`
Provides a Playwright browser page for E2E tests.

```python
@pytest.mark.e2e
def test_page_loads(browser_page):
    page, base_url = browser_page
    page.goto(f"{base_url}/frontend/index.html")
    assert page.title() == "College Football Rankings"
```

#### `factories`
Provides Factory Boy factories for creating test data.

```python
def test_with_factory(factories):
    team = factories['team'](name="Alabama", elo_rating=1850.0)
    assert team.name == "Alabama"
```

#### `mock_cfbd_client`
Mocks the CFBD API client to avoid rate limits.

```python
def test_with_mock_api(mock_cfbd_client):
    teams = mock_cfbd_client.get_teams(2025)
    assert len(teams) > 0
```

---

## Mocking Strategy

### Why Mock the CFBD API?

The College Football Data API has rate limits (1000 calls/month). To avoid hitting limits during testing:

1. **Unit tests** - Mock all CFBD API calls
2. **Integration tests** - Use test database, mock external APIs
3. **E2E tests** - Use test database and mock API where possible

### Mocking CFBD API Calls

```python
from unittest.mock import Mock, patch

def test_update_games_script():
    """Test game update without calling real API"""

    # Mock CFBD client
    with patch('update_games.CFBDClient') as MockClient:
        mock_client = Mock()
        mock_client.get_games.return_value = [
            {
                'homeTeam': 'Alabama',
                'awayTeam': 'Georgia',
                'homePoints': None,
                'awayPoints': None,
                'week': 10
            }
        ]
        MockClient.return_value = mock_client

        # Test your code that uses CFBD client
        result = update_games(week=10)

        # Verify mock was called correctly
        mock_client.get_games.assert_called_once()
```

---

## Coverage Requirements

### Current Coverage

Run coverage report to see current metrics:

```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Coverage Goals

- **Overall:** 80%+ coverage
- **Critical modules:** 90%+ coverage
  - `ranking_service.py`
  - `cfbd_client.py`
  - `main.py` (API endpoints)

### Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html
```

The HTML report shows:
- Line-by-line coverage (green = covered, red = not covered)
- Missing lines
- Branch coverage
- Per-file statistics

---

## Running Tests in CI/CD

Tests run automatically in GitHub Actions on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

### CI Test Workflow

1. **Unit Tests** - Run first (fastest)
2. **Integration Tests** - Run after unit tests pass
3. **E2E Tests** - Run in separate job (slower, uses headless browser)

See [CI-CD-PIPELINE.md](CI-CD-PIPELINE.md) for detailed workflow documentation.

---

## Troubleshooting

### Tests Failing Locally

**Issue:** Tests pass in CI but fail locally

**Solution:** Ensure you have the latest dependencies:
```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
```

**Issue:** E2E tests fail with "Port already in use"

**Solution:** Kill process using test port:
```bash
lsof -ti:8765 | xargs kill -9
```

**Issue:** `import` errors

**Solution:** Ensure you're running from project root:
```bash
cd "/Users/bryandailey/Stat-urday Synthesis"
pytest -v
```

### Slow Test Runs

**Issue:** Tests take too long

**Solution:** Skip E2E tests for quick iteration:
```bash
pytest -m "not e2e" -v
```

**Solution:** Run specific test file:
```bash
pytest tests/test_ranking_service.py -v
```

### Database Issues

**Issue:** Tests failing with "table doesn't exist"

**Solution:** Database is automatically created/destroyed per test. Check that you're using `test_db` fixture.

**Issue:** Tests affecting each other

**Solution:** Each test gets a fresh database. Ensure you're using function-scoped fixtures (`scope="function"`).

---

## Best Practices

### Test Naming

- Use descriptive names: `test_user_can_view_rankings`
- Follow pattern: `test_<what>_<expected_outcome>`
- Include context: `test_api_returns_404_when_team_not_found`

### Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange - Set up test data and conditions
    team = Team(name="Test Team", elo_rating=1500.0)

    # Act - Perform the action being tested
    result = calculate_expected_score(team, opponent_rating=1600.0)

    # Assert - Verify the outcome
    assert 0 < result < 1
    assert result < 0.5  # Underdog has less than 50% chance
```

### Test Independence

- Each test should be independent
- Don't rely on test execution order
- Use fixtures for shared setup
- Clean up after yourself (fixtures handle this automatically)

### Documentation

- Add docstrings to test functions
- Explain *why* you're testing something, not just *what*
- Document edge cases and assumptions

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [Playwright documentation](https://playwright.dev/python/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Factory Boy documentation](https://factoryboy.readthedocs.io/)

---

## Contact

For questions about testing:
- Check this documentation first
- Review existing tests for examples
- Open an issue on GitHub
