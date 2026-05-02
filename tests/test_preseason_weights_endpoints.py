"""
Tests for preseason weights admin endpoints and preseason components endpoint.

EPIC-032 Story 32.4 — covers:
  GET  /api/admin/preseason-weights
  PUT  /api/admin/preseason-weights
  GET  /api/preseason/components

Patch notes:
  - GET weights: main.py does `from src.core.position_service import load_position_weights`
    inside the handler, so we patch `src.core.position_service.load_position_weights`.
  - PUT weights: main.py does `from src.core.position_service import DEFAULT_CONFIG_PATH`
    inside the handler, so we patch `src.core.position_service.DEFAULT_CONFIG_PATH`.
  - Components: main.py uses `RankingService(db)` via the module-level import, so we
    patch `src.api.main.RankingService`.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_WEIGHTS_PAYLOAD = {
    "previous_season_weight": 0.40,
    "mean_regression_factor": 0.55,
    "returning_regression_scale": 0.70,
}

DEFAULT_CONFIG = {
    "enabled": True,
    "previous_season_weight": 0.35,
    "mean_regression_factor": 0.60,
    "returning_regression_scale": 0.60,
    "_comments": {},
}


def make_client(test_db):
    """Return a TestClient wired to the in-memory test database."""
    from src.models.database import get_db

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


# ---------------------------------------------------------------------------
# GET /api/admin/preseason-weights
# ---------------------------------------------------------------------------


class TestGetPreseasonWeights:
    """Tests for GET /api/admin/preseason-weights"""

    def test_returns_200(self, test_db):
        client = make_client(test_db)
        with patch(
            "src.core.position_service.load_position_weights",
            return_value=DEFAULT_CONFIG.copy(),
        ):
            response = client.get("/api/admin/preseason-weights")
        assert response.status_code == 200

    def test_response_has_required_fields(self, test_db):
        client = make_client(test_db)
        with patch(
            "src.core.position_service.load_position_weights",
            return_value=DEFAULT_CONFIG.copy(),
        ):
            data = client.get("/api/admin/preseason-weights").json()
        assert "previous_season_weight" in data
        assert "mean_regression_factor" in data
        assert "returning_regression_scale" in data

    def test_returns_current_config_values(self, test_db):
        client = make_client(test_db)
        config = DEFAULT_CONFIG.copy()
        config["previous_season_weight"] = 0.25
        config["mean_regression_factor"] = 0.70
        config["returning_regression_scale"] = 0.50
        with patch(
            "src.core.position_service.load_position_weights", return_value=config
        ):
            data = client.get("/api/admin/preseason-weights").json()
        assert data["previous_season_weight"] == pytest.approx(0.25)
        assert data["mean_regression_factor"] == pytest.approx(0.70)
        assert data["returning_regression_scale"] == pytest.approx(0.50)

    def test_returns_500_when_config_unreadable(self, test_db):
        client = make_client(test_db)
        with patch(
            "src.core.position_service.load_position_weights",
            side_effect=Exception("disk error"),
        ):
            response = client.get("/api/admin/preseason-weights")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# PUT /api/admin/preseason-weights
# ---------------------------------------------------------------------------


class TestPutPreseasonWeights:
    """Tests for PUT /api/admin/preseason-weights"""

    # ---- Success path ----

    def _write_temp_config(self, extra=None):
        """Write a temp config file and return its Path."""
        config = DEFAULT_CONFIG.copy()
        if extra:
            config.update(extra)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(config, tmp)
            return Path(tmp.name)

    def test_returns_200_on_valid_payload(self, test_db):
        client = make_client(test_db)
        tmp_path = self._write_temp_config()
        try:
            with patch("src.core.position_service.DEFAULT_CONFIG_PATH", tmp_path):
                response = client.put(
                    "/api/admin/preseason-weights", json=VALID_WEIGHTS_PAYLOAD
                )
            assert response.status_code == 200
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_response_echoes_saved_values(self, test_db):
        client = make_client(test_db)
        tmp_path = self._write_temp_config()
        try:
            with patch("src.core.position_service.DEFAULT_CONFIG_PATH", tmp_path):
                data = client.put(
                    "/api/admin/preseason-weights", json=VALID_WEIGHTS_PAYLOAD
                ).json()
            assert data["previous_season_weight"] == pytest.approx(0.40)
            assert data["mean_regression_factor"] == pytest.approx(0.55)
            assert data["returning_regression_scale"] == pytest.approx(0.70)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_writes_values_to_config_file(self, test_db):
        client = make_client(test_db)
        tmp_path = self._write_temp_config()
        try:
            with patch("src.core.position_service.DEFAULT_CONFIG_PATH", tmp_path):
                client.put("/api/admin/preseason-weights", json=VALID_WEIGHTS_PAYLOAD)

            saved = json.loads(tmp_path.read_text())
            assert saved["previous_season_weight"] == pytest.approx(0.40)
            assert saved["mean_regression_factor"] == pytest.approx(0.55)
            assert saved["returning_regression_scale"] == pytest.approx(0.70)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_preserves_other_config_keys(self, test_db):
        """PUT should not clobber unrelated config fields."""
        client = make_client(test_db)
        tmp_path = self._write_temp_config(extra={"custom_key": "do not delete"})
        try:
            with patch("src.core.position_service.DEFAULT_CONFIG_PATH", tmp_path):
                client.put("/api/admin/preseason-weights", json=VALID_WEIGHTS_PAYLOAD)

            saved = json.loads(tmp_path.read_text())
            assert saved.get("custom_key") == "do not delete"
            assert saved.get("enabled") is True
        finally:
            tmp_path.unlink(missing_ok=True)

    # ---- Validation ----

    def test_rejects_prev_season_weight_above_1(self, test_db):
        client = make_client(test_db)
        bad_payload = {**VALID_WEIGHTS_PAYLOAD, "previous_season_weight": 1.5}
        response = client.put("/api/admin/preseason-weights", json=bad_payload)
        assert response.status_code == 422

    def test_rejects_prev_season_weight_below_0(self, test_db):
        client = make_client(test_db)
        bad_payload = {**VALID_WEIGHTS_PAYLOAD, "previous_season_weight": -0.1}
        response = client.put("/api/admin/preseason-weights", json=bad_payload)
        assert response.status_code == 422

    def test_rejects_mean_regression_above_1(self, test_db):
        client = make_client(test_db)
        bad_payload = {**VALID_WEIGHTS_PAYLOAD, "mean_regression_factor": 1.1}
        response = client.put("/api/admin/preseason-weights", json=bad_payload)
        assert response.status_code == 422

    def test_rejects_mean_regression_below_0(self, test_db):
        client = make_client(test_db)
        bad_payload = {**VALID_WEIGHTS_PAYLOAD, "mean_regression_factor": -0.01}
        response = client.put("/api/admin/preseason-weights", json=bad_payload)
        assert response.status_code == 422

    def test_rejects_returning_regression_scale_above_2(self, test_db):
        """returning_regression_scale has le=2.0 per schema."""
        client = make_client(test_db)
        bad_payload = {**VALID_WEIGHTS_PAYLOAD, "returning_regression_scale": 2.5}
        response = client.put("/api/admin/preseason-weights", json=bad_payload)
        assert response.status_code == 422

    def test_rejects_returning_regression_scale_below_0(self, test_db):
        client = make_client(test_db)
        bad_payload = {**VALID_WEIGHTS_PAYLOAD, "returning_regression_scale": -0.1}
        response = client.put("/api/admin/preseason-weights", json=bad_payload)
        assert response.status_code == 422

    def test_rejects_missing_fields(self, test_db):
        client = make_client(test_db)
        response = client.put(
            "/api/admin/preseason-weights",
            json={"previous_season_weight": 0.30},
        )
        assert response.status_code == 422

    def test_returns_500_when_config_file_missing(self, test_db):
        client = make_client(test_db)
        missing_path = Path("/tmp/nonexistent_config_xyz.json")
        with patch("src.core.position_service.DEFAULT_CONFIG_PATH", missing_path):
            response = client.put(
                "/api/admin/preseason-weights", json=VALID_WEIGHTS_PAYLOAD
            )
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/preseason/components
# ---------------------------------------------------------------------------


class TestGetPreseasonComponents:
    """Tests for GET /api/preseason/components"""

    def _make_component(self, team_id=1, team_name="Ohio State"):
        return {
            "team_id": team_id,
            "team_name": team_name,
            "conference": "Big Ten",
            "base": 1500.0,
            "current_rating": 1780.0,
            "recruiting_bonus": 45.0,
            "transfer_bonus": 20.0,
            "returning_bonus": 15.0,
            "position_strength_bonus": 10.0,
            "returning_production": 0.65,
            "prev_season_elo": 1900.0,
        }

    def _mock_rs(self, return_value):
        """Return a context manager patching RankingService in main."""
        mock_instance = MagicMock()
        mock_instance.get_preseason_components.return_value = return_value
        mock_cls = MagicMock(return_value=mock_instance)
        return patch("src.api.main.RankingService", mock_cls), mock_instance

    def test_returns_200(self, test_db):
        client = make_client(test_db)
        components = [self._make_component()]
        ctx, _ = self._mock_rs(components)
        with ctx:
            response = client.get("/api/preseason/components")
        assert response.status_code == 200

    def test_returns_list(self, test_db):
        client = make_client(test_db)
        components = [
            self._make_component(1, "Ohio State"),
            self._make_component(2, "Michigan"),
        ]
        ctx, _ = self._mock_rs(components)
        with ctx:
            data = client.get("/api/preseason/components").json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_each_item_has_required_fields(self, test_db):
        client = make_client(test_db)
        components = [self._make_component()]
        ctx, _ = self._mock_rs(components)
        with ctx:
            data = client.get("/api/preseason/components").json()

        required = [
            "team_id", "team_name", "conference", "base", "current_rating",
            "recruiting_bonus", "transfer_bonus", "returning_bonus",
            "position_strength_bonus", "returning_production", "prev_season_elo",
        ]
        for field in required:
            assert field in data[0], f"Missing field: {field}"

    def test_accepts_season_query_param(self, test_db):
        client = make_client(test_db)
        ctx, mock_instance = self._mock_rs([])
        with ctx:
            client.get("/api/preseason/components?season=2025")
        # The endpoint calls get_preseason_components(season) positionally
        mock_instance.get_preseason_components.assert_called_once_with(2025)

    def test_returns_empty_list_when_no_data(self, test_db):
        client = make_client(test_db)
        ctx, _ = self._mock_rs([])
        with ctx:
            data = client.get("/api/preseason/components").json()
        assert data == []

    def test_prev_season_elo_can_be_null(self, test_db):
        """Teams with no previous season data should have null prev_season_elo."""
        client = make_client(test_db)
        comp = self._make_component()
        comp["prev_season_elo"] = None
        ctx, _ = self._mock_rs([comp])
        with ctx:
            data = client.get("/api/preseason/components").json()
        assert data[0]["prev_season_elo"] is None
