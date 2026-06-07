"""Unit tests for production_service (EPIC-040).

Covers compute_percentiles() and blend_quality().
"""

import pytest

from src.core.production_service import (
    DEFENSIVE_STAT_WEIGHTS,
    blend_quality,
    compute_percentiles,
    defensive_impact,
)


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


@pytest.mark.unit
class TestDefensiveImpact:
    def test_weighted_sum(self):
        stats = {"TOT": "10", "TFL": "2", "SACKS": "1", "PD": "3", "QB HUR": "2", "TD": "1"}
        expected = (
            10 * DEFENSIVE_STAT_WEIGHTS["TOT"]
            + 2 * DEFENSIVE_STAT_WEIGHTS["TFL"]
            + 1 * DEFENSIVE_STAT_WEIGHTS["SACKS"]
            + 3 * DEFENSIVE_STAT_WEIGHTS["PD"]
            + 2 * DEFENSIVE_STAT_WEIGHTS["QB HUR"]
            + 1 * DEFENSIVE_STAT_WEIGHTS["TD"]
        )
        assert defensive_impact(stats) == expected

    def test_parses_float_strings(self):
        # TFL often comes as "6.0"
        assert defensive_impact({"TFL": "6.0"}) == 6.0 * DEFENSIVE_STAT_WEIGHTS["TFL"]

    def test_ignores_missing_blank_and_unknown(self):
        stats = {"TOT": "5", "SACKS": "", "BOGUS": "9", "PD": None}
        assert defensive_impact(stats) == 5 * DEFENSIVE_STAT_WEIGHTS["TOT"]

    def test_empty_is_zero(self):
        assert defensive_impact({}) == 0.0

    def test_disruptive_plays_outweigh_volume(self):
        # A player with sacks/TFL beats a pure-tackle compiler with the same TOT
        compiler = defensive_impact({"TOT": "20"})
        playmaker = defensive_impact({"TOT": "20", "SACKS": "5", "TFL": "8"})
        assert playmaker > compiler
