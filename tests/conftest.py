"""
Shared pytest fixtures for College Football Ranking System tests

This module provides test fixtures for:
- Test database setup (in-memory SQLite)
- FastAPI test client
- Database session management
- Test data factories
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.database import get_db
from src.api.main import app

# Import Base and ALL models AFTER main to ensure models are registered
# Importing main first ensures it has already imported and registered all models
from src.models.models import (
    APIUsage,
    APPollRanking,
    Base,
    Game,
    Prediction,
    RankingHistory,
    Season,
    Team,
    UpdateTask,
)


@pytest.fixture(scope="function")
def test_db():
    """
    Create an in-memory SQLite database for testing.

    This fixture:
    - Creates a fresh database for each test function
    - Sets up all tables using SQLAlchemy models
    - Ensures test isolation (no shared state between tests)
    - Automatically cleans up after the test

    Yields:
        Session: SQLAlchemy database session for test use
    """
    # Create in-memory SQLite engine with shared cache
    # Using file::memory:?cache=shared ensures all connections share the same in-memory database
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true", connect_args={"check_same_thread": False}
    )

    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Ensure all model classes are registered with Base.metadata
    # This explicit reference forces Python to load all model classes
    _models = [Team, Game, RankingHistory, Season, APIUsage, UpdateTask, Prediction, APPollRanking]

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(test_db: Session):
    """
    Create a FastAPI TestClient with test database dependency override.

    This fixture:
    - Provides an HTTP client for testing API endpoints
    - Overrides the get_db() dependency to use test database
    - Ensures all API calls use the isolated test database
    - No need to start actual server (TestClient handles this)

    Args:
        test_db: Test database session from test_db fixture

    Yields:
        TestClient: FastAPI test client for making API requests
    """

    def override_get_db():
        """Override database dependency to use test database"""
        yield test_db

    # Override dependency before creating client
    app.dependency_overrides[get_db] = override_get_db

    # Create test client (will trigger startup event, but should use overridden DB)
    client = TestClient(app)

    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db_session(test_db: Session):
    """
    Alias for test_db fixture for backwards compatibility and clarity.

    Some tests may prefer the name 'db_session' instead of 'test_db'.
    Both fixtures provide the same functionality.

    Args:
        test_db: Test database session

    Yields:
        Session: SQLAlchemy database session
    """
    yield test_db


@pytest.fixture(scope="function")
def factories(test_db: Session):
    """
    Configure Factory Boy factories with test database session.

    This fixture sets up all test data factories to use the test database,
    allowing easy creation of test data with realistic defaults.

    Args:
        test_db: Test database session

    Yields:
        dict: Dictionary of factory classes

    Example:
        def test_with_factories(factories):
            team = factories['team']()
            game = factories['game'](home_team=team)
    """
    import sys

    from factories import (
        EliteTeamFactory,
        FCSTeamFactory,
        G5ChampionFactory,
        GameFactory,
        RankingHistoryFactory,
        SeasonFactory,
        TeamFactory,
        configure_factories,
    )

    # Configure all factories with test database
    configure_factories(test_db)

    yield {
        "team": TeamFactory,
        "game": GameFactory,
        "season": SeasonFactory,
        "history": RankingHistoryFactory,
        "elite_team": EliteTeamFactory,
        "g5_champion": G5ChampionFactory,
        "fcs_team": FCSTeamFactory,
    }


@pytest.fixture(scope="function")
def mock_cfbd_client(monkeypatch):
    """
    Mock CollegeFootballData.com API client for testing.

    This fixture mocks all CFBD API methods to return deterministic test data,
    eliminating external dependencies and ensuring consistent, fast test execution.

    The mock data is based on real API responses but simplified for testing.

    Yields:
        Mock CFBD client with all methods mocked
    """
    from unittest.mock import Mock

    # Create mock client
    mock_client = Mock()

    # Mock get_teams() - Returns realistic FBS team data
    mock_client.get_teams.return_value = [
        {"school": "Alabama", "conference": "SEC", "abbreviation": "ALA"},
        {"school": "Georgia", "conference": "SEC", "abbreviation": "UGA"},
        {"school": "Ohio State", "conference": "Big Ten", "abbreviation": "OSU"},
        {"school": "Michigan", "conference": "Big Ten", "abbreviation": "MICH"},
        {"school": "Boise State", "conference": "Mountain West", "abbreviation": "BSU"},
    ]

    # Mock get_games() - Returns completed game data
    mock_client.get_games.return_value = [
        {
            "homeTeam": "Alabama",
            "awayTeam": "Georgia",
            "homePoints": 27,
            "awayPoints": 24,
            "week": 1,
            "neutralSite": False,
        },
        {
            "homeTeam": "Ohio State",
            "awayTeam": "Michigan",
            "homePoints": 30,
            "awayPoints": 24,
            "week": 1,
            "neutralSite": False,
        },
    ]

    # Mock get_recruiting_rankings() - Returns recruiting class rankings
    mock_client.get_recruiting_rankings.return_value = [
        {"team": "Alabama", "rank": 1},
        {"team": "Georgia", "rank": 2},
        {"team": "Ohio State", "rank": 3},
        {"team": "Michigan", "rank": 5},
        {"team": "Boise State", "rank": 60},
    ]

    # Mock get_team_talent() - Returns talent composite scores
    mock_client.get_team_talent.return_value = [
        {"school": "Alabama", "talent": 95.5},
        {"school": "Georgia", "talent": 94.8},
        {"school": "Ohio State", "talent": 93.2},
        {"school": "Michigan", "talent": 91.5},
        {"school": "Boise State", "talent": 75.0},
    ]

    # Mock get_returning_production() - Returns returning production percentages
    mock_client.get_returning_production.return_value = [
        {"team": "Alabama", "returningProduction": 75.5},
        {"team": "Georgia", "returningProduction": 68.2},
        {"team": "Ohio State", "returningProduction": 82.0},
        {"team": "Michigan", "returningProduction": 55.5},
        {"team": "Boise State", "returningProduction": 70.0},
    ]

    # Mock get_transfer_portal() - Returns transfer portal rankings
    mock_client.get_transfer_portal.return_value = [
        {"team": "Alabama", "rank": 2},
        {"team": "Georgia", "rank": 1},
        {"team": "Ohio State", "rank": 4},
        {"team": "Michigan", "rank": 8},
        {"team": "Boise State", "rank": 25},
    ]

    # Mock get_ap_poll() - Returns AP Poll rankings
    mock_client.get_ap_poll.return_value = [
        {"school": "Alabama", "rank": 1, "firstPlaceVotes": 45, "points": 1500},
        {"school": "Georgia", "rank": 2, "firstPlaceVotes": 10, "points": 1450},
        {"school": "Ohio State", "rank": 3, "firstPlaceVotes": 7, "points": 1400},
        {"school": "Michigan", "rank": 5, "firstPlaceVotes": 0, "points": 1300},
    ]

    return mock_client


@pytest.fixture(scope="session")
def live_server():
    """
    Start a live FastAPI server for E2E tests.

    This fixture starts the FastAPI application on a test port and provides
    the base URL for E2E tests to connect to.

    Yields:
        str: Base URL of the running server (e.g., "http://localhost:8765")
    """
    import threading
    import time

    import uvicorn

    from src.api.main import app

    # Use a different port for E2E tests to avoid conflicts
    test_port = 8765
    base_url = f"http://localhost:{test_port}"

    # Start server in background thread
    config = uvicorn.Config(app, host="127.0.0.1", port=test_port, log_level="error")
    server = uvicorn.Server(config)

    def run_server():
        server.run()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # Wait for server to start
    time.sleep(2)

    yield base_url

    # Server will stop when tests finish (daemon thread)


@pytest.fixture(scope="function")
def browser_page(live_server):
    """
    Provide a Playwright browser page for E2E tests.

    This fixture creates a new browser context and page for each test,
    ensuring test isolation. Screenshots are captured on failure.

    Args:
        live_server: Base URL of the running server

    Yields:
        tuple: (page, base_url) - Playwright page object and server URL
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Launch browser in headless mode for CI/CD compatibility
        browser = p.chromium.launch(headless=True)

        # Create new context for test isolation
        context = browser.new_context(viewport={"width": 1280, "height": 720}, locale="en-US")

        # Create new page
        page = context.new_page()

        yield page, live_server

        # Cleanup
        page.close()
        context.close()
        browser.close()


# Pytest configuration
def pytest_configure(config):
    """
    Configure pytest markers for test categorization.

    Markers:
    - unit: Fast, isolated unit tests
    - integration: API + database integration tests
    - e2e: End-to-end browser-based tests
    - slow: Tests that take more than 1 second
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (API + database)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (browser automation)")
    config.addinivalue_line("markers", "slow: Tests that take more than 1 second")
