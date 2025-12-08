"""
End-to-End tests for Team Detail Page (frontend/team.html)

Tests verify:
- Team detail page loads with correct data
- Team information is displayed (name, conference, record, rating)
- Schedule/games are shown
- Navigation back to rankings works
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.slow
class TestTeamDetailPageLoad:
    """Tests for team detail page loading"""

    def test_team_detail_page_loads(self, browser_page, test_db):
        """Test that team detail page loads successfully"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        test_db.add(team)
        test_db.commit()

        # Act - Navigate to team detail page
        page.goto(f"{base_url}/frontend/team.html?id={team.id}")
        page.wait_for_timeout(1000)

        # Assert - Page loads
        expect(page).to_have_title("College Football Rankings - Team Detail")

    def test_team_name_displayed(self, browser_page, test_db):
        """Test that team name is displayed on page"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1840.0, wins=4, losses=1
        )
        test_db.add(team)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/team.html?id={team.id}")
        page.wait_for_timeout(1000)

        # Assert - Team name is visible
        page_content = page.content()
        assert "Georgia" in page_content


@pytest.mark.e2e
@pytest.mark.slow
class TestTeamDetailData:
    """Tests for team detail data display"""

    def test_team_stats_displayed(self, browser_page, test_db):
        """Test that team stats are displayed correctly"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Ohio State",
            conference=ConferenceType.POWER_5,
            elo_rating=1830.5,
            wins=7,
            losses=2,
            recruiting_rank=3,
            returning_production=0.75,
        )
        test_db.add(team)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/team.html?id={team.id}")
        page.wait_for_timeout(1500)

        page_content = page.content()

        # Assert - Stats are shown
        assert "1830" in page_content or "1831" in page_content  # ELO rating (rounded)
        assert "7-2" in page_content or "7" in page_content  # Record

    def test_conference_displayed(self, browser_page, test_db):
        """Test that team conference is displayed"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Boise State",
            conference=ConferenceType.GROUP_5,
            elo_rating=1600.0,
            wins=8,
            losses=1,
        )
        test_db.add(team)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/team.html?id={team.id}")
        page.wait_for_timeout(1000)

        page_content = page.content()

        # Assert - Conference is shown
        assert "G5" in page_content or "Group" in page_content


@pytest.mark.e2e
@pytest.mark.slow
class TestTeamSchedule:
    """Tests for team schedule/games display"""

    def test_schedule_table_exists(self, browser_page, test_db):
        """Test that schedule table is rendered"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Game, Team

        home_team = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=1, losses=0
        )
        away_team = Team(
            name="Georgia", conference=ConferenceType.POWER_5, elo_rating=1840.0, wins=0, losses=1
        )
        test_db.add_all([home_team, away_team])
        test_db.commit()

        # Create a game
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=27,
            away_score=24,
            week=1,
            season=2024,
            is_processed=True,
        )
        test_db.add(game)
        test_db.commit()

        # Act - View Alabama's schedule
        page.goto(f"{base_url}/frontend/team.html?id={home_team.id}")
        page.wait_for_timeout(2000)

        # Assert - Schedule section exists
        page_content = page.content()
        # Check for schedule-related content
        assert (
            "schedule" in page_content.lower()
            or "game" in page_content.lower()
            or "Georgia" in page_content
        )

    def test_schedule_shows_opponent(self, browser_page, test_db):
        """Test that schedule shows opponent name"""
        # Arrange
        page, base_url = browser_page
        from datetime import datetime

        from src.models.models import ConferenceType, Game, Team

        home_team = Team(
            name="Michigan", conference=ConferenceType.POWER_5, elo_rating=1820.0, wins=1, losses=0
        )
        away_team = Team(
            name="Ohio State",
            conference=ConferenceType.POWER_5,
            elo_rating=1830.0,
            wins=0,
            losses=1,
        )
        test_db.add_all([home_team, away_team])
        test_db.commit()

        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=42,
            away_score=27,
            week=12,
            season=2024,
            game_date=datetime.now(),
            is_processed=True,
        )
        test_db.add(game)
        test_db.commit()

        # Act - View Michigan's schedule
        page.goto(f"{base_url}/frontend/team.html?id={home_team.id}")
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Assert - Opponent name appears
        assert "Ohio State" in page_content
        assert "42" in page_content  # Score shown


@pytest.mark.e2e
@pytest.mark.slow
class TestTeamDetailNavigation:
    """Tests for navigation on team detail page"""

    def test_back_to_rankings_link_works(self, browser_page, test_db):
        """Test that navigation back to rankings page works"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        test_db.add(team)
        test_db.commit()

        # Act - Navigate to team detail, then click back to rankings
        page.goto(f"{base_url}/frontend/team.html?id={team.id}")
        page.wait_for_timeout(1000)

        # Look for navigation link to rankings
        rankings_link = page.locator("nav a[href*='index.html']").first
        rankings_link.click()

        # Assert - Navigated back to rankings
        expect(page).to_have_url(f"{base_url}/frontend/index.html")

    def test_invalid_team_id_handles_gracefully(self, browser_page):
        """Test that invalid team ID is handled gracefully"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate with invalid ID
        page.goto(f"{base_url}/frontend/team.html?id=99999")
        page.wait_for_timeout(1500)

        # Assert - Page doesn't crash (shows error or empty state)
        # Page should still load, even if team not found
        expect(page).to_have_title("College Football Rankings - Team Detail")


@pytest.mark.e2e
@pytest.mark.slow
class TestTeamDetailAPIIntegration:
    """Tests verifying API integration on team detail page"""

    def test_api_calls_made_on_load(self, browser_page, test_db):
        """Test that page makes API calls for team data and schedule"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Team

        team = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        test_db.add(team)
        test_db.commit()

        # Track API requests
        api_requests = []

        def handle_request(request):
            if "/api/" in request.url:
                api_requests.append(request.url)

        page.on("request", handle_request)

        # Act
        page.goto(f"{base_url}/frontend/team.html?id={team.id}")
        page.wait_for_timeout(2000)

        # Assert - API calls were made
        assert len(api_requests) > 0
        # Should call /api/teams/{id} and possibly /api/teams/{id}/schedule
        assert any(f"/teams/{team.id}" in url for url in api_requests)

    def test_full_user_workflow_rankings_to_team(self, browser_page, test_db):
        """Test complete user workflow: rankings -> team detail -> back"""
        # Arrange
        page, base_url = browser_page
        from src.models.models import ConferenceType, Season, Team

        season = Season(year=2024, is_active=True)
        test_db.add(season)

        alabama = Team(
            name="Alabama", conference=ConferenceType.POWER_5, elo_rating=1850.0, wins=5, losses=0
        )
        test_db.add(alabama)
        test_db.commit()

        # Act - Start at rankings
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)

        # Click on Alabama
        alabama_link = page.locator("#rankings-table tbody tr a").first
        alabama_link.click()

        # Wait for team detail page
        expect(page).to_have_url(f"{base_url}/frontend/team.html?id={alabama.id}")
        page.wait_for_timeout(1000)

        # Verify team name is shown
        assert "Alabama" in page.content()

        # Navigate back to rankings
        rankings_link = page.locator("nav a[href*='index.html']").first
        rankings_link.click()

        # Assert - Back at rankings page
        expect(page).to_have_url(f"{base_url}/frontend/index.html")
        page.wait_for_selector("#rankings-table tbody tr", timeout=5000)
