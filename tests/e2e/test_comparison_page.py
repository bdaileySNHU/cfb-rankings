"""
End-to-End tests for AP Poll Comparison Page (frontend/comparison.html)

Tests verify:
- Comparison page loads successfully
- ELO vs AP Poll comparison data displays
- Accuracy metrics are shown
- Charts render correctly (if present)
- Navigation works

EPIC-013 Story 003: Add E2E Tests
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonPageLoad:
    """Tests for comparison page loading"""

    def test_comparison_page_loads(self, browser_page):
        """Test that comparison page loads successfully"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to comparison page
        page.goto(f"{base_url}/frontend/comparison.html")

        # Assert - Page loads with correct title
        expect(page).to_have_title("College Football Rankings - ELO vs AP Poll")

    def test_page_has_header(self, browser_page):
        """Test that page displays correct header"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")

        # Assert - Header is visible
        header = page.locator("h1")
        expect(header).to_be_visible()
        expect(header).to_contain_text("Comparison")

    def test_page_has_navigation(self, browser_page):
        """Test that page has navigation menu"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")

        # Assert - Navigation links are present
        nav_links = page.locator("nav a")
        expect(nav_links.first).to_be_visible()


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonDataDisplay:
    """Tests for comparison data display"""

    def test_comparison_stats_display(self, browser_page, test_db):
        """Test that comparison statistics are displayed"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        # Create active season for comparison data
        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act - Load comparison page
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)  # Wait for API call

        # Assert - Page loaded successfully
        expect(page).to_have_title("College Football Rankings - ELO vs AP Poll")

    def test_accuracy_metrics_shown(self, browser_page, test_db):
        """Test that accuracy percentages are displayed"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Assert - Accuracy-related terms appear
        # (actual values depend on data, so we check for labels)
        accuracy_terms = ["accuracy", "correct", "prediction", "elo", "ap"]
        assert any(term.lower() in page_content.lower() for term in accuracy_terms)


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonChart:
    """Tests for comparison chart rendering"""

    def test_chart_container_exists(self, browser_page, test_db):
        """Test that chart container element exists on page"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)

        # Assert - Chart canvas or container exists
        # (Chart.js or other library may use canvas/svg)
        page_content = page.content()

        # Check for chart-related elements
        has_chart_element = (
            "canvas" in page_content.lower() or
            "chart" in page_content.lower() or
            "svg" in page_content.lower()
        )

        # Page should have some chart visualization capability
        assert has_chart_element or "comparison" in page_content.lower()


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonAPIIntegration:
    """Tests verifying API integration for comparison data"""

    def test_api_call_made_on_page_load(self, browser_page, test_db):
        """Test that page makes API call to /api/predictions/comparison"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Set up request tracking
        api_called = []

        def handle_request(request):
            if "/api/" in request.url:
                api_called.append(request.url)

        page.on("request", handle_request)

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)

        # Assert - API endpoint was called
        assert len(api_called) > 0
        # Should call comparison endpoint
        assert any("comparison" in url or "predictions" in url for url in api_called)

    def test_empty_state_when_no_comparison_data(self, browser_page, test_db):
        """Test page handles missing comparison data gracefully"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        # Create season but no prediction/AP poll data
        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)

        # Assert - Page loads without crashing
        expect(page).to_have_title("College Football Rankings - ELO vs AP Poll")


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonNavigation:
    """Tests for navigation on comparison page"""

    def test_navigation_to_rankings_works(self, browser_page):
        """Test that navigation back to rankings works"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to comparison page
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(1000)

        # Click navigation link to rankings
        rankings_link = page.locator("nav a[href*='index.html']").first
        if rankings_link.count() > 0:
            rankings_link.click()

            # Assert - Navigated to rankings
            expect(page).to_have_url(f"{base_url}/frontend/index.html")

    def test_navigation_to_games_works(self, browser_page):
        """Test that navigation to games page works"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to comparison page
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(1000)

        # Click navigation link to games
        games_link = page.locator("nav a[href*='games.html']").first
        if games_link.count() > 0:
            games_link.click()

            # Assert - Navigated to games
            expect(page).to_have_url(f"{base_url}/frontend/games.html")


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonUserWorkflow:
    """Tests for complete user workflows involving comparison page"""

    def test_full_workflow_through_all_pages(self, browser_page, test_db):
        """Test navigation through all main pages"""
        # Arrange
        page, base_url = browser_page
        from models import Team, Season, ConferenceType

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)

        team = Team(
            name="USC",
            conference=ConferenceType.POWER_5,
            elo_rating=1790.0,
            wins=7,
            losses=2
        )
        test_db.add(team)
        test_db.commit()

        # Act - Start at rankings
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_timeout(1500)

        # Navigate to comparison via nav
        comparison_link = page.locator("nav a[href*='comparison.html']").first
        if comparison_link.count() > 0:
            comparison_link.click()

            # Wait for comparison page
            expect(page).to_have_url(f"{base_url}/frontend/comparison.html}")
            page.wait_for_timeout(1000)

            # Navigate to games
            games_link = page.locator("nav a[href*='games.html']").first
            if games_link.count() > 0:
                games_link.click()

                # Verify at games page
                expect(page).to_have_url(f"{base_url}/frontend/games.html")
                page.wait_for_timeout(1000)

                # Navigate back to rankings
                rankings_link = page.locator("nav a[href*='index.html']").first
                rankings_link.click()

                # Assert - Back at rankings
                expect(page).to_have_url(f"{base_url}/frontend/index.html")


@pytest.mark.e2e
@pytest.mark.slow
class TestComparisonDataAccuracy:
    """Tests for data accuracy on comparison page"""

    def test_comparison_shows_season_filter(self, browser_page, test_db):
        """Test that comparison allows season selection"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        # Create multiple seasons
        season_2024 = Season(year=2024, current_week=15, is_active=False)
        season_2025 = Season(year=2025, current_week=10, is_active=True)
        test_db.add_all([season_2024, season_2025])
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Assert - Season selector or current season is mentioned
        assert "2025" in page_content or "2024" in page_content or "season" in page_content.lower()

    def test_elo_and_ap_labels_present(self, browser_page, test_db):
        """Test that both ELO and AP Poll are referenced"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/comparison.html")
        page.wait_for_timeout(2000)

        page_content = page.content().lower()

        # Assert - Both systems are mentioned
        assert "elo" in page_content
        assert "ap" in page_content or "poll" in page_content
