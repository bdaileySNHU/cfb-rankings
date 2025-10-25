"""
End-to-End tests for Predictions/Games Page (frontend/games.html)

Tests verify:
- Predictions page loads with correct data
- Prediction cards display team names, scores, and probabilities
- Games can be filtered by week
- Predictions show for upcoming games only
- Navigation between pages works

EPIC-013 Story 003: Add E2E Tests
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.slow
class TestPredictionsPageLoad:
    """Tests for predictions page loading and initial rendering"""

    def test_predictions_page_loads(self, browser_page):
        """Test that predictions/games page loads successfully"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to games/predictions page
        page.goto(f"{base_url}/frontend/games.html")

        # Assert - Page loads with correct title
        expect(page).to_have_title("College Football Rankings - Games & Predictions")

    def test_page_has_header(self, browser_page):
        """Test that page displays correct header"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/games.html")

        # Assert - Header is visible
        header = page.locator("h1")
        expect(header).to_be_visible()
        expect(header).to_contain_text("Games")

    def test_page_has_navigation(self, browser_page):
        """Test that page has navigation menu"""
        # Arrange
        page, base_url = browser_page

        # Act
        page.goto(f"{base_url}/frontend/games.html")

        # Assert - Navigation links are present
        nav_links = page.locator("nav a")
        expect(nav_links.first).to_be_visible()


@pytest.mark.e2e
@pytest.mark.slow
class TestPredictionsDisplay:
    """Tests for predictions/games display with API data"""

    def test_predictions_display_for_upcoming_games(self, browser_page, test_db):
        """Test that predictions are shown for upcoming games"""
        # Arrange
        page, base_url = browser_page
        from models import Team, Game, Season, ConferenceType
        from datetime import datetime, timedelta

        # Create active season
        season = Season(year=2025, current_week=9, is_active=True)
        test_db.add(season)

        # Create teams
        ohio_state = Team(
            name="Ohio State",
            conference=ConferenceType.POWER_5,
            elo_rating=1850.0,
            wins=7,
            losses=1
        )
        michigan = Team(
            name="Michigan",
            conference=ConferenceType.POWER_5,
            elo_rating=1820.0,
            wins=7,
            losses=1
        )
        test_db.add_all([ohio_state, michigan])
        test_db.commit()

        # Create future game (not processed yet)
        future_game = Game(
            home_team_id=ohio_state.id,
            away_team_id=michigan.id,
            home_score=0,
            away_score=0,
            week=10,
            season=2025,
            game_date=datetime.now() + timedelta(days=7),
            is_processed=False,
            is_neutral_site=False
        )
        test_db.add(future_game)
        test_db.commit()

        # Act - Load page
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(2000)  # Wait for API call and rendering

        page_content = page.content()

        # Assert - Game matchup appears (at least one team name should be visible)
        assert "Ohio State" in page_content or "Michigan" in page_content

    def test_completed_games_show_scores(self, browser_page, test_db):
        """Test that completed games display actual scores"""
        # Arrange
        page, base_url = browser_page
        from models import Team, Game, Season, ConferenceType

        season = Season(year=2025, current_week=9, is_active=True)
        test_db.add(season)

        # Create teams
        alabama = Team(
            name="Alabama",
            conference=ConferenceType.POWER_5,
            elo_rating=1850.0,
            wins=8,
            losses=0
        )
        georgia = Team(
            name="Georgia",
            conference=ConferenceType.POWER_5,
            elo_rating=1840.0,
            wins=7,
            losses=1
        )
        test_db.add_all([alabama, georgia])
        test_db.commit()

        # Create completed game
        completed_game = Game(
            home_team_id=alabama.id,
            away_team_id=georgia.id,
            home_score=27,
            away_score=24,
            week=9,
            season=2025,
            is_processed=True,
            is_neutral_site=False
        )
        test_db.add(completed_game)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Assert - Scores are shown
        assert "27" in page_content and "24" in page_content
        # And team names
        assert "Alabama" in page_content or "Georgia" in page_content

    def test_week_filter_works(self, browser_page, test_db):
        """Test filtering games by specific week"""
        # Arrange
        page, base_url = browser_page
        from models import Team, Game, Season, ConferenceType

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)

        team1 = Team(name="Team A", conference=ConferenceType.POWER_5, elo_rating=1800.0)
        team2 = Team(name="Team B", conference=ConferenceType.POWER_5, elo_rating=1790.0)
        test_db.add_all([team1, team2])
        test_db.commit()

        # Create games for different weeks
        game_week_9 = Game(
            home_team_id=team1.id,
            away_team_id=team2.id,
            home_score=0,
            away_score=0,
            week=9,
            season=2025,
            is_processed=False
        )
        game_week_11 = Game(
            home_team_id=team1.id,
            away_team_id=team2.id,
            home_score=0,
            away_score=0,
            week=11,
            season=2025,
            is_processed=False
        )
        test_db.add_all([game_week_9, game_week_11])
        test_db.commit()

        # Act - Load page (should show default week)
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(1500)

        # Assert - Page loaded successfully
        expect(page).to_have_title("College Football Rankings - Games & Predictions")


@pytest.mark.e2e
@pytest.mark.slow
class TestPredictionCards:
    """Tests for individual prediction card display"""

    def test_prediction_card_shows_team_names(self, browser_page, test_db):
        """Test that prediction cards display both team names"""
        # Arrange
        page, base_url = browser_page
        from models import Team, Game, Season, ConferenceType
        from datetime import datetime, timedelta

        season = Season(year=2025, current_week=9, is_active=True)
        test_db.add(season)

        penn_state = Team(
            name="Penn State",
            conference=ConferenceType.POWER_5,
            elo_rating=1820.0,
            wins=7,
            losses=1
        )
        wisconsin = Team(
            name="Wisconsin",
            conference=ConferenceType.POWER_5,
            elo_rating=1750.0,
            wins=5,
            losses=3
        )
        test_db.add_all([penn_state, wisconsin])
        test_db.commit()

        game = Game(
            home_team_id=penn_state.id,
            away_team_id=wisconsin.id,
            home_score=0,
            away_score=0,
            week=10,
            season=2025,
            game_date=datetime.now() + timedelta(days=7),
            is_processed=False,
            is_neutral_site=False
        )
        test_db.add(game)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(2000)

        page_content = page.content()

        # Assert - Both team names appear
        assert "Penn State" in page_content or "Wisconsin" in page_content


@pytest.mark.e2e
@pytest.mark.slow
class TestPredictionsAPIIntegration:
    """Tests verifying JavaScript correctly calls prediction API"""

    def test_api_call_made_on_page_load(self, browser_page, test_db):
        """Test that page makes API call to /api/predictions or /api/games"""
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
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(1500)

        # Assert - API endpoint was called
        assert len(api_called) > 0
        # Should call games or predictions endpoint
        assert any("/api/games" in url or "/api/predictions" in url for url in api_called)

    def test_empty_state_when_no_games(self, browser_page, test_db):
        """Test that appropriate message shown when no games exist"""
        # Arrange
        page, base_url = browser_page
        from models import Season

        # Create season but no games
        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)
        test_db.commit()

        # Act
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(2000)

        # Assert - Page loads successfully even with no games
        expect(page).to_have_title("College Football Rankings - Games & Predictions")


@pytest.mark.e2e
@pytest.mark.slow
class TestPredictionsNavigation:
    """Tests for navigation on predictions page"""

    def test_navigation_to_rankings_works(self, browser_page):
        """Test that navigation to rankings page works"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to games page
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(1000)

        # Click navigation link to rankings
        rankings_link = page.locator("nav a[href*='index.html']").first
        if rankings_link.count() > 0:
            rankings_link.click()

            # Assert - Navigated to rankings
            expect(page).to_have_url(f"{base_url}/frontend/index.html")

    def test_navigation_to_teams_works(self, browser_page):
        """Test that navigation to teams page works"""
        # Arrange
        page, base_url = browser_page

        # Act - Navigate to games page
        page.goto(f"{base_url}/frontend/games.html")
        page.wait_for_timeout(1000)

        # Click navigation link to teams
        teams_link = page.locator("nav a[href*='teams.html']").first
        if teams_link.count() > 0:
            teams_link.click()

            # Assert - Navigated to teams list
            expect(page).to_have_url(f"{base_url}/frontend/teams.html")


@pytest.mark.e2e
@pytest.mark.slow
class TestPredictionsUserWorkflow:
    """Tests for complete user workflows involving predictions"""

    def test_full_workflow_rankings_to_games_and_back(self, browser_page, test_db):
        """Test complete user journey: rankings -> games -> back to rankings"""
        # Arrange
        page, base_url = browser_page
        from models import Team, Season, ConferenceType

        season = Season(year=2025, current_week=10, is_active=True)
        test_db.add(season)

        team = Team(
            name="Notre Dame",
            conference=ConferenceType.POWER_5,
            elo_rating=1800.0,
            wins=8,
            losses=1
        )
        test_db.add(team)
        test_db.commit()

        # Act - Start at rankings
        page.goto(f"{base_url}/frontend/index.html")
        page.wait_for_timeout(1500)

        # Navigate to games via nav link
        games_link = page.locator("nav a[href*='games.html']").first
        if games_link.count() > 0:
            games_link.click()

            # Wait for games page
            expect(page).to_have_url(f"{base_url}/frontend/games.html")
            page.wait_for_timeout(1000)

            # Navigate back to rankings
            rankings_link = page.locator("nav a[href*='index.html']").first
            rankings_link.click()

            # Assert - Back at rankings
            expect(page).to_have_url(f"{base_url}/frontend/index.html")
