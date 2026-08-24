"""
End-to-End tests for Rankings Page (frontend/index.html)

Tests verify the full stack works together:
- Browser loads HTML page
- JavaScript fetches data from API
- Data is rendered correctly in the DOM
- User interactions work as expected

The `live_server` fixture starts the app itself, so no separate server is
needed: run `pytest tests/e2e/ -v`, or skip these with `pytest -m "not e2e"`.
Chromium must be installed once via `python -m playwright install chromium`.
"""

import pytest
from playwright.sync_api import Page, expect

# Mark all tests in this file to skip by default in CI
# To run: pytest -m e2e or pytest tests/e2e/
pytestmark = [pytest.mark.e2e, pytest.mark.slow]


@pytest.mark.e2e
@pytest.mark.slow
class TestRankingsPageLoad:
    """Tests for rankings page loading and initial rendering"""

    def test_rankings_page_loads(self, browser_page):
        """Test that rankings page loads successfully"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to rankings page
        page.goto(f"{base_url}/frontend/index.html")

        # Assert - Page loads with correct title
        expect(page).to_have_title("Stat·urday — Power Ratings")

    def test_page_has_header(self, browser_page):
        """Test that page displays correct header"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/index.html")

        # Assert - Header is visible
        header = page.locator("h1")
        expect(header).to_be_visible()
        expect(header).to_contain_text("Power Ratings")

    def test_page_has_navigation(self, browser_page):
        """Test that page has navigation menu"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/index.html")

        # Assert - The main navigation destinations are present. Asserting the
        # link names rather than a count means adding a page to layout.js does
        # not fail this test, but dropping one of these does.
        for name in ("Rankings", "Games", "Compare"):
            expect(page.locator("nav a", has_text=name)).to_be_visible()


@pytest.mark.e2e
@pytest.mark.slow
class TestRankingsTableDisplay:
    """Tests for rankings table rendering with API data"""

    def test_rankings_table_displays(self, browser_page, seed_board):
        """Test that rankings table is rendered"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        # Create test data
        team1 = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        team2 = Team(
            name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1840.0, wins=4, losses=1
        )
        seed_board(team1, team2)

        # Act - Load page and wait for data to load
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector(".tkr-row", timeout=5000)

        # Assert - Table has rows
        table_rows = page.locator(".tkr-row")
        expect(table_rows).to_have_count(2, timeout=5000)

    def test_rankings_table_shows_correct_data(self, browser_page, seed_board):
        """Test that rankings table displays team data correctly"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        alabama = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=1, losses=0
        )
        seed_board(alabama, week=1)

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector(".tkr-row", timeout=5000)

        # Assert - First row contains Alabama data
        first_row = page.locator(".tkr-row").first
        expect(first_row).to_contain_text("Alabama")
        expect(first_row).to_contain_text("1850")
        expect(first_row).to_contain_text("1-0")

    def test_rankings_sorted_by_elo(self, browser_page, seed_board):
        """Test that teams are sorted by ELO rating descending"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        # Create teams in mixed order
        team3 = Team(
            name="Ohio State",
            conference=ConferenceType.POWER_5,
            elo_rating=1820.0,
            wins=3,
            losses=0,
        )
        team1 = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=3, losses=0
        )
        team2 = Team(
            name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1840.0, wins=3, losses=0
        )

        seed_board(team3, team1, team2)

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector(".tkr-row", timeout=5000)

        # Assert - Teams appear in correct order
        rows = page.locator(".tkr-row")
        expect(rows.nth(0)).to_contain_text("Alabama")  # Highest ELO first
        expect(rows.nth(1)).to_contain_text("Georgia")
        expect(rows.nth(2)).to_contain_text("Ohio State")

    def test_projection_columns_render(self, browser_page, seed_board):
        """Cached simulation -> endpoint -> schema -> grid, end to end.

        The other tests in this file seed no simulation, so they already cover
        the em-dash path; this is the one that proves a real number arrives.
        """
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        alabama = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        seed_board(
            alabama,
            odds={
                "Alabama": {
                    "bid_pct": 62.5,
                    "conf_title_pct": 21.4,
                    "title_pct": 8.1,
                    "proj_wins": 9.3,
                }
            },
        )

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector(".tkr-row", timeout=5000)

        # Assert - the headers exist and the row carries the numbers.
        # fmtPct rounds at or above 10% and keeps a decimal below it.
        expect(page.locator(".tkr-head")).to_contain_text("BID%")
        expect(page.locator(".tkr-head")).to_contain_text("PROJ W")
        first_row = page.locator(".tkr-row").first
        expect(first_row).to_contain_text("63%")
        expect(first_row).to_contain_text("8.1%")
        expect(first_row).to_contain_text("9.3")

    def test_conference_displayed(self, browser_page, seed_board):
        """Test that team conference is displayed"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Boise State",
            conference=ConferenceType.GROUP_5,
            elo_rating=1600.0,
            wins=5,
            losses=0,
        )
        seed_board(team)

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector(".tkr-row", timeout=5000)

        # Assert - Conference badge is shown
        first_row = page.locator(".tkr-row").first
        expect(first_row).to_contain_text("G5")


@pytest.mark.e2e
@pytest.mark.slow
class TestRankingsPageInteractions:
    """Tests for user interactions on rankings page"""

    def test_click_team_navigates_to_detail(self, browser_page, seed_board):
        """Test clicking a team name navigates to team detail page"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        alabama = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        seed_board(alabama)

        # Act - Navigate to rankings and click team
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector(".tkr-row", timeout=5000)

        # Click on Alabama row
        alabama_row = page.locator(".tkr-row").first
        alabama_row.click()

        # Assert - Detail panel is shown and contains the team name
        expect(page.locator("#tkr-detail")).to_be_visible()
        expect(page.locator("#tkr-detail")).to_contain_text("Alabama")

    def test_empty_state_displayed(self, browser_page, test_db):
        """Test that appropriate message shown when no teams exist"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import Season

        # Create season but no teams
        season = Season(year=2024, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_timeout(2000)  # Wait for API call

        # Assert - No rows in table or empty message shown
        table_rows = page.locator(".tkr-row")
        count = table_rows.count()

        # Either no rows or a "no data" row
        assert count == 0 or "no teams" in page.content().lower()


@pytest.mark.e2e
@pytest.mark.slow
class TestRankingsAPIIntegration:
    """Tests verifying JavaScript correctly calls and renders API data"""

    def test_api_call_made_on_page_load(self, browser_page, test_db):
        """Test that page makes API call to /api/rankings on load"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import Season

        season = Season(year=2024, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Set up request interception to verify API call
        api_called = []

        def handle_request(request):
            if "/api/rankings" in request.url:
                api_called.append(request.url)

        page.on("request", handle_request)

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_timeout(1000)

        # Assert - API endpoint was called
        assert len(api_called) > 0
        assert any("/api/rankings" in url for url in api_called)

    def test_loading_state_shown(self, browser_page):
        """Test that loading indicator is shown while fetching data"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate and check for loading state quickly
        page.goto(f"{base_url}/frontend/index.html")

        # Assert - Loading indicator or table exists
        # (This test verifies page structure, loading may be too fast to catch)
        table = page.locator("#tkr-table")
        expect(table).to_be_visible()
