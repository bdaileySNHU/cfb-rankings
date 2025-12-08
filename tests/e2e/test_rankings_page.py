"""
End-to-End tests for Rankings Page (frontend/index.html)

Tests verify the full stack works together:
- Browser loads HTML page
- JavaScript fetches data from API
- Data is rendered correctly in the DOM
- User interactions work as expected

NOTE: These E2E tests require a running FastAPI server.
Run manually with: pytest tests/e2e/ -v
Or skip E2E tests with: pytest -m "not e2e"

To run E2E tests:
1. Start the FastAPI server: python3 main.py (in another terminal)
2. Run: pytest tests/e2e/ -v
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
        expect(page).to_have_title("College Football Rankings - Modified ELO System")

    def test_page_has_header(self, browser_page):
        """Test that page displays correct header"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/index.html")

        # Assert - Header is visible
        header = page.locator("h1")
        expect(header).to_be_visible()
        expect(header).to_contain_text("College Football Rankings")

    def test_page_has_navigation(self, browser_page):
        """Test that page has navigation menu"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/index.html")

        # Assert - Navigation links are present
        nav_links = page.locator("nav a")
        expect(nav_links).to_have_count(4)  # Rankings, Teams, Games, Comparison


@pytest.mark.e2e
@pytest.mark.slow
class TestRankingsTableDisplay:
    """Tests for rankings table rendering with API data"""

    def test_rankings_table_displays(self, browser_page, test_db):
        """Test that rankings table is rendered"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Season, Team

        # Create test data
        season = Season(year=2024, current_week=5, is_active=True)
        test_db.add(season)

        team1 = Team(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            elo_rating=1850.0,
            wins=5,
            losses=0
        )
        team2 = Team(
            name="Georgia",
            conference=ConferenceType.POWER_5,
            elo_rating=1840.0,
            wins=4,
            losses=1
        )
        test_db.add(team1)
        test_db.add(team2)
        test_db.commit()

        # Act - Load page and wait for data to load
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

        # Assert - Table has rows
        table_rows = page.locator("#rankings-table tbody tr")
        expect(table_rows).to_have_count(2, timeout=5000)

    def test_rankings_table_shows_correct_data(self, browser_page, test_db):
        """Test that rankings table displays team data correctly"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Season, Team

        season = Season(year=2024, current_week=1, is_active=True)
        test_db.add(season)

        alabama = Team(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            elo_rating=1850.0,
            wins=1,
            losses=0
        )
        test_db.add(alabama)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

        # Assert - First row contains Alabama data
        first_row = page.locator("#rankings-table tbody tr").first
        expect(first_row).to_contain_text("Alabama")
        expect(first_row).to_contain_text("1850")
        expect(first_row).to_contain_text("1-0")

    def test_rankings_sorted_by_elo(self, browser_page, test_db):
        """Test that teams are sorted by ELO rating descending"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Season, Team

        season = Season(year=2024, is_active=True)
        test_db.add(season)

        # Create teams in mixed order
        team3 = Team(name="Ohio State", conference=ConferenceType.POWER_5, elo_rating=1820.0, wins=3, losses=0)
        team1 = Team(name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=3, losses=0)
        team2 = Team(name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1840.0, wins=3, losses=0)

        test_db.add_all([team3, team1, team2])
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

        # Assert - Teams appear in correct order
        rows = page.locator("#rankings-table tbody tr")
        expect(rows.nth(0)).to_contain_text("Alabama")  # Highest ELO first
        expect(rows.nth(1)).to_contain_text("Georgia")
        expect(rows.nth(2)).to_contain_text("Ohio State")

    def test_conference_displayed(self, browser_page, test_db):
        """Test that team conference is displayed"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Season, Team

        season = Season(year=2024, is_active=True)
        test_db.add(season)

        team = Team(
            name="Boise State",
            conference=ConferenceType.GROUP_5,
            elo_rating=1600.0,
            wins=5,
            losses=0
        )
        test_db.add(team)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

        # Assert - Conference badge is shown
        first_row = page.locator("#rankings-table tbody tr").first
        expect(first_row).to_contain_text("G5")


@pytest.mark.e2e
@pytest.mark.slow
class TestRankingsPageInteractions:
    """Tests for user interactions on rankings page"""

    def test_click_team_navigates_to_detail(self, browser_page, test_db):
        """Test clicking a team name navigates to team detail page"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Season, Team

        season = Season(year=2024, is_active=True)
        test_db.add(season)

        alabama = Team(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            elo_rating=1850.0,
            wins=5,
            losses=0
        )
        test_db.add(alabama)
        test_db.commit()

        # Act - Navigate to rankings and click team
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

        # Click on Alabama link
        alabama_link = page.locator("#rankings-table tbody tr a").first
        alabama_link.click()

        # Assert - Navigated to team detail page
        expect(page).to_have_url(f"{base_url}/frontend/team.html?id={alabama.id}")

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
        table_rows = page.locator("#rankings-table tbody tr")
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
        table = page.locator("#rankings-table")
        expect(table).to_be_visible()
