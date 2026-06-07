"""Unit tests for production_service (EPIC-040).

Covers compute_percentiles() and blend_quality().
"""

import pytest

from src.core.production_service import blend_quality, compute_percentiles


@pytest.mark.unit
class TestComputePercentiles:
    def test_empty(self):
        assert compute_percentiles([]) == []

    def test_single(self):
        assert compute_percentiles([0.7]) == [50.0]

    def test_orders_low_to_high(self):
        scores = compute_percentiles([0.1, 0.5, 0.9])
        # middle value sits at 50; ordering preserved; bounded 0–100
        assert scores[0] < scores[1] < scores[2]
        assert abs(scores[1] - 50.0) < 0.01
        assert all(0.0 <= s <= 100.0 for s in scores)

    def test_ties_share_percentile(self):
        scores = compute_percentiles([0.5, 0.5, 0.9])
        assert scores[0] == scores[1]
        assert scores[2] > scores[0]

    def test_preserves_input_order(self):
        # highest value is last in input; should get the highest score there
        scores = compute_percentiles([0.9, 0.1, 0.5])
        assert scores[0] == max(scores)
        assert scores[1] == min(scores)


@pytest.mark.unit
class TestBlendQuality:
    def test_none_production_returns_recruiting(self):
        assert blend_quality(80.0, None, 0.5) == 80.0

    def test_even_blend(self):
        assert blend_quality(80.0, 40.0, 0.5) == 60.0

    def test_weight_zero_is_recruiting(self):
        assert blend_quality(80.0, 40.0, 0.0) == 80.0

    def test_weight_one_is_production(self):
        assert blend_quality(80.0, 40.0, 1.0) == 40.0

    def test_weight_clamped(self):
        # weight > 1 clamps to production-only
        assert blend_quality(80.0, 40.0, 5.0) == 40.0
        # weight < 0 clamps to recruiting-only
        assert blend_quality(80.0, 40.0, -1.0) == 80.0
