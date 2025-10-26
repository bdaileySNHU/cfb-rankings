"""
Unit tests for admin endpoints

Tests the manual update trigger, status tracking, usage dashboard,
and configuration endpoints added in Story 003.

NOTE: These tests use SessionLocal() and require a production database.
They are skipped in CI and should be refactored to use test fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import patch, MagicMock
import json

from main import app
from database import SessionLocal, Base, engine
from models import UpdateTask, APIUsage


# Create test client
client = TestClient(app)

# Skip all tests in this file in CI - they need production database
pytestmark = pytest.mark.skip(reason="Requires production database - needs refactoring to use test fixtures")


class TestUsageDashboardEndpoint:
    """Tests for GET /api/admin/usage-dashboard"""

    def test_usage_dashboard_returns_200(self):
        """Dashboard endpoint should return 200 OK"""
        response = client.get("/api/admin/usage-dashboard")
        assert response.status_code == 200

    def test_usage_dashboard_has_required_fields(self):
        """Dashboard response should have all required fields"""
        response = client.get("/api/admin/usage-dashboard")
        data = response.json()

        assert "current_month" in data
        assert "top_endpoints" in data
        assert "daily_usage" in data
        assert "last_update" in data

    def test_usage_dashboard_current_month_fields(self):
        """Current month stats should have all required fields"""
        response = client.get("/api/admin/usage-dashboard")
        current_month = response.json()["current_month"]

        assert "month" in current_month
        assert "total_calls" in current_month
        assert "monthly_limit" in current_month
        assert "percentage_used" in current_month
        assert "remaining_calls" in current_month
        assert "average_calls_per_day" in current_month
        assert "days_until_reset" in current_month
        assert "projected_end_of_month" in current_month

    def test_usage_dashboard_with_month_parameter(self):
        """Dashboard should accept month parameter"""
        response = client.get("/api/admin/usage-dashboard?month=2025-10")
        assert response.status_code == 200
        assert response.json()["current_month"]["month"] == "2025-10"

    def test_usage_dashboard_calculates_projections(self):
        """Dashboard should calculate end-of-month projections"""
        response = client.get("/api/admin/usage-dashboard")
        data = response.json()

        # Projected usage should be calculated
        assert "projected_end_of_month" in data["current_month"]
        assert isinstance(data["current_month"]["projected_end_of_month"], int)


class TestConfigEndpoints:
    """Tests for GET/PUT /api/admin/config"""

    def test_get_config_returns_200(self):
        """Config GET endpoint should return 200 OK"""
        response = client.get("/api/admin/config")
        assert response.status_code == 200

    def test_get_config_has_all_fields(self):
        """Config should have all required fields"""
        response = client.get("/api/admin/config")
        data = response.json()

        assert "cfbd_monthly_limit" in data
        assert "update_schedule" in data
        assert "api_usage_warning_thresholds" in data
        assert "active_season_start" in data
        assert "active_season_end" in data

    def test_get_config_default_values(self):
        """Config should return expected default values"""
        response = client.get("/api/admin/config")
        data = response.json()

        assert data["cfbd_monthly_limit"] == 1000
        assert data["update_schedule"] == "Sun 20:00 ET"
        assert data["api_usage_warning_thresholds"] == [80, 90, 95]
        assert data["active_season_start"] == "08-01"
        assert data["active_season_end"] == "01-31"

    def test_put_config_updates_limit(self):
        """PUT config should update monthly limit"""
        response = client.put(
            "/api/admin/config",
            json={"cfbd_monthly_limit": 2000}
        )
        assert response.status_code == 200
        assert response.json()["cfbd_monthly_limit"] == 2000

    def test_put_config_returns_updated_config(self):
        """PUT config should return full updated config"""
        response = client.put(
            "/api/admin/config",
            json={"cfbd_monthly_limit": 1500}
        )
        data = response.json()

        assert data["cfbd_monthly_limit"] == 1500
        assert "update_schedule" in data
        assert "api_usage_warning_thresholds" in data


class TestTriggerUpdateEndpoint:
    """Tests for POST /api/admin/trigger-update"""

    @patch('main.is_active_season')
    def test_trigger_update_fails_in_off_season(self, mock_is_active):
        """Trigger should fail with 400 if in off-season"""
        mock_is_active.return_value = False

        response = client.post("/api/admin/trigger-update")

        assert response.status_code == 400
        assert "off-season" in response.json()["detail"].lower()

    @patch('main.is_active_season')
    @patch('main.get_current_week_wrapper')
    def test_trigger_update_fails_with_no_week(self, mock_get_week, mock_is_active):
        """Trigger should fail with 400 if no current week"""
        mock_is_active.return_value = True
        mock_get_week.return_value = None

        response = client.post("/api/admin/trigger-update")

        assert response.status_code == 400
        assert "no current week" in response.json()["detail"].lower()

    @patch('main.is_active_season')
    @patch('main.get_current_week_wrapper')
    @patch('main.check_api_usage')
    def test_trigger_update_fails_at_90_percent_usage(
        self, mock_check_usage, mock_get_week, mock_is_active
    ):
        """Trigger should fail with 429 if API usage >= 90%"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = False

        response = client.post("/api/admin/trigger-update")

        assert response.status_code == 429
        assert "usage" in response.json()["detail"].lower()

    @patch('main.is_active_season')
    @patch('main.get_current_week_wrapper')
    @patch('main.check_api_usage')
    def test_trigger_update_succeeds_with_valid_conditions(
        self, mock_check_usage, mock_get_week, mock_is_active
    ):
        """Trigger should succeed with 200 when all checks pass"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = True

        response = client.post("/api/admin/trigger-update")

        assert response.status_code == 200
        assert response.json()["status"] == "started"
        assert "task_id" in response.json()
        assert "started_at" in response.json()

    @patch('main.is_active_season')
    @patch('main.get_current_week_wrapper')
    @patch('main.check_api_usage')
    def test_trigger_update_creates_task_record(
        self, mock_check_usage, mock_get_week, mock_is_active
    ):
        """Trigger should create UpdateTask record in database"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = True

        response = client.post("/api/admin/trigger-update")
        task_id = response.json()["task_id"]

        # Verify task was created in database
        db = SessionLocal()
        try:
            task = db.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()
            assert task is not None
            assert task.status in ["started", "running"]
            assert task.trigger_type == "manual"
        finally:
            db.close()


class TestUpdateStatusEndpoint:
    """Tests for GET /api/admin/update-status/{task_id}"""

    def test_update_status_404_for_unknown_task(self):
        """Status endpoint should return 404 for unknown task_id"""
        response = client.get("/api/admin/update-status/unknown-task-123")
        assert response.status_code == 404

    def test_update_status_returns_task_info(self):
        """Status endpoint should return task information"""
        # Create a test task
        db = SessionLocal()
        task = UpdateTask(
            task_id="test-task-12345",
            status="completed",
            trigger_type="manual",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=120.5,
            result_json=json.dumps({
                "success": True,
                "games_imported": 45,
                "error_message": None
            })
        )
        db.add(task)
        db.commit()
        db.close()

        # Query the status
        response = client.get("/api/admin/update-status/test-task-12345")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-12345"
        assert data["status"] == "completed"
        assert data["trigger_type"] == "manual"
        assert data["duration_seconds"] == 120.5
        assert data["result"]["success"] is True

    def test_update_status_handles_null_result(self):
        """Status endpoint should handle tasks with no result yet"""
        # Create task without result
        db = SessionLocal()
        task = UpdateTask(
            task_id="test-task-no-result",
            status="running",
            trigger_type="manual",
            started_at=datetime.utcnow()
        )
        db.add(task)
        db.commit()
        db.close()

        response = client.get("/api/admin/update-status/test-task-no-result")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["result"] is None


class TestUpdateTaskModel:
    """Tests for UpdateTask database model"""

    def test_create_update_task(self):
        """Should be able to create UpdateTask record"""
        db = SessionLocal()

        task = UpdateTask(
            task_id="model-test-123",
            status="started",
            trigger_type="manual",
            started_at=datetime.utcnow()
        )
        db.add(task)
        db.commit()

        # Verify it was saved
        saved_task = db.query(UpdateTask).filter(
            UpdateTask.task_id == "model-test-123"
        ).first()

        assert saved_task is not None
        assert saved_task.status == "started"
        assert saved_task.trigger_type == "manual"

        db.close()

    def test_update_task_status(self):
        """Should be able to update task status"""
        db = SessionLocal()

        # Create task
        task = UpdateTask(
            task_id="update-test-456",
            status="started",
            trigger_type="manual",
            started_at=datetime.utcnow()
        )
        db.add(task)
        db.commit()

        # Update to completed
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.duration_seconds = 95.3
        db.commit()

        # Verify update
        updated_task = db.query(UpdateTask).filter(
            UpdateTask.task_id == "update-test-456"
        ).first()

        assert updated_task.status == "completed"
        assert updated_task.completed_at is not None
        assert updated_task.duration_seconds == 95.3

        db.close()


class TestAPIIntegration:
    """Integration tests for admin API endpoints"""

    def test_full_dashboard_workflow(self):
        """Test complete dashboard data retrieval workflow"""
        # Get dashboard
        response = client.get("/api/admin/usage-dashboard")
        assert response.status_code == 200

        # Get config
        config_response = client.get("/api/admin/config")
        assert config_response.status_code == 200

        # Verify they're consistent
        dashboard_limit = response.json()["current_month"]["monthly_limit"]
        config_limit = config_response.json()["cfbd_monthly_limit"]
        assert dashboard_limit == config_limit

    @patch('main.is_active_season')
    @patch('main.get_current_week_wrapper')
    @patch('main.check_api_usage')
    def test_trigger_and_check_status_workflow(
        self, mock_check_usage, mock_get_week, mock_is_active
    ):
        """Test trigger update and check status workflow"""
        mock_is_active.return_value = True
        mock_get_week.return_value = 8
        mock_check_usage.return_value = True

        # Trigger update
        trigger_response = client.post("/api/admin/trigger-update")
        assert trigger_response.status_code == 200

        task_id = trigger_response.json()["task_id"]

        # Check status
        status_response = client.get(f"/api/admin/update-status/{task_id}")
        assert status_response.status_code == 200
        assert status_response.json()["task_id"] == task_id
        assert status_response.json()["status"] in ["started", "running", "completed", "failed"]
