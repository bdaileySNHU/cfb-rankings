"""Tests for the EPIC-045 CORE-style efficiency blend."""

import pytest

from src.core import ranking_service as rs
from src.core.ranking_service import (
    blend_rating,
    effective_rating,
    efficiency_rating,
    efficiency_scale,
    net_ppa,
)
from src.models.models import ConferenceType, Team

# (mean_elo, stdev_elo, mean_net, stdev_net) — one stdev of efficiency is worth
# one stdev of ELO, i.e. 50 points here.
SCALE = (1500.0, 50.0, 0.0, 0.1)


def make_team(name="Test", elo=1500.0, offense_ppa=None, defense_ppa=None):
    return Team(
        name=name,
        conference=ConferenceType.POWER_5,
        is_fcs=False,
        elo_rating=elo,
        offense_ppa=offense_ppa,
        defense_ppa=defense_ppa,
    )


@pytest.fixture
def blend_on(monkeypatch):
    """Pin the blend weight so tests do not depend on the EFFICIENCY_WEIGHT env var."""
    monkeypatch.setattr(rs, "EFFICIENCY_WEIGHT", 0.25)


class TestNetPPA:
    def test_none_without_both_halves(self):
        assert net_ppa(make_team()) is None
        assert net_ppa(make_team(offense_ppa=0.2)) is None
        assert net_ppa(make_team(defense_ppa=0.0)) is None

    def test_offense_minus_defense(self):
        assert net_ppa(make_team(offense_ppa=0.25, defense_ppa=-0.10)) == pytest.approx(0.35)


class TestBlendRating:
    """The shared formula — production and the backtest harness both go through it."""

    def test_weighted_average(self):
        assert blend_rating(1700.0, 1500.0, weight=0.25, week=10, min_week=4) == pytest.approx(1650.0)

    def test_missing_efficiency_returns_elo(self):
        assert blend_rating(1700.0, None, weight=0.25, week=10, min_week=4) == 1700.0

    def test_zero_weight_returns_elo(self):
        assert blend_rating(1700.0, 1500.0, weight=0.0, week=10, min_week=4) == 1700.0

    def test_week_gate(self):
        assert blend_rating(1700.0, 1500.0, weight=0.25, week=3, min_week=4) == 1700.0
        assert blend_rating(1700.0, 1500.0, weight=0.25, week=4, min_week=4) != 1700.0

    def test_no_week_skips_the_gate(self):
        assert blend_rating(1700.0, 1500.0, weight=0.25, min_week=99) == pytest.approx(1650.0)

    def test_defaults_come_from_module_config(self, monkeypatch):
        monkeypatch.setattr(rs, "EFFICIENCY_WEIGHT", 0.5)
        monkeypatch.setattr(rs, "EFFICIENCY_MIN_WEEK", 7)
        assert blend_rating(1700.0, 1500.0, week=10) == pytest.approx(1600.0)
        assert blend_rating(1700.0, 1500.0, week=6) == 1700.0

    def test_effective_rating_agrees_with_blend_rating(self, blend_on):
        """effective_rating must be blend_rating plus data lookup, nothing more."""
        team = make_team(elo=1700.0, offense_ppa=0.1, defense_ppa=0.0)
        eff = efficiency_rating(team, SCALE)
        assert effective_rating(team, 10, SCALE) == pytest.approx(
            blend_rating(1700.0, eff, rs.EFFICIENCY_WEIGHT, 10, rs.EFFICIENCY_MIN_WEEK)
        )


class TestEfficiencyRating:
    def test_average_efficiency_sits_at_mean_elo(self):
        team = make_team(offense_ppa=0.1, defense_ppa=0.1)  # net 0.0 == mean_net
        assert efficiency_rating(team, SCALE) == pytest.approx(1500.0)

    def test_one_stdev_of_efficiency_is_one_stdev_of_elo(self):
        team = make_team(offense_ppa=0.1, defense_ppa=0.0)  # net +0.1 == +1 sd
        assert efficiency_rating(team, SCALE) == pytest.approx(1550.0)

    def test_bad_efficiency_lands_below_the_mean(self):
        team = make_team(offense_ppa=-0.1, defense_ppa=0.1)  # net -0.2 == -2 sd
        assert efficiency_rating(team, SCALE) == pytest.approx(1400.0)

    def test_returns_none_without_data(self):
        assert efficiency_rating(make_team(), SCALE) is None


class TestEfficiencyScale:
    def test_none_when_too_few_teams(self, db_session):
        for i in range(rs.EFFICIENCY_MIN_TEAMS - 1):
            db_session.add(make_team(name=f"T{i}", elo=1500 + i, offense_ppa=i / 100, defense_ppa=0.0))
        db_session.commit()
        assert efficiency_scale(db_session) is None

    def test_none_when_efficiency_has_no_spread(self, db_session):
        for i in range(rs.EFFICIENCY_MIN_TEAMS + 5):
            db_session.add(make_team(name=f"T{i}", elo=1500 + i, offense_ppa=0.1, defense_ppa=0.0))
        db_session.commit()
        assert efficiency_scale(db_session) is None

    def test_computes_population_stats(self, db_session):
        for i in range(40):
            db_session.add(
                make_team(name=f"T{i}", elo=1500 + i * 10, offense_ppa=i / 100, defense_ppa=0.0)
            )
        db_session.commit()

        mean_elo, stdev_elo, mean_net, stdev_net = efficiency_scale(db_session)
        assert mean_elo == pytest.approx(1695.0)
        assert mean_net == pytest.approx(0.195)
        assert stdev_elo > 0 and stdev_net > 0
        # ELO stdev is 100x the net-PPA stdev here by construction (elo step 10,
        # ppa step 0.01) — the mapping absorbs whatever the real ratio is.
        assert stdev_elo == pytest.approx(stdev_net * 1000)

    def test_ignores_fcs_and_teams_without_data(self, db_session):
        for i in range(30):
            db_session.add(
                make_team(name=f"T{i}", elo=1500 + i * 10, offense_ppa=i / 100, defense_ppa=0.0)
            )
        fcs = make_team(name="FCS U", elo=1000, offense_ppa=-5.0, defense_ppa=5.0)
        fcs.is_fcs = True
        db_session.add(fcs)
        db_session.add(make_team(name="No Data", elo=9999))
        db_session.commit()

        mean_elo, _, mean_net, _ = efficiency_scale(db_session)
        assert mean_elo == pytest.approx(1645.0)  # neither outlier pulled the mean
        assert mean_net == pytest.approx(0.145)


class TestEffectiveRating:
    def test_falls_back_to_elo_without_efficiency_data(self, blend_on):
        team = make_team(elo=1700.0)
        assert effective_rating(team, week=10, scale=SCALE) == 1700.0

    def test_blends_elo_and_efficiency(self, blend_on):
        # elo 1700, efficiency 1550 → 0.75 * 1700 + 0.25 * 1550
        team = make_team(elo=1700.0, offense_ppa=0.1, defense_ppa=0.0)
        assert effective_rating(team, week=10, scale=SCALE) == pytest.approx(1662.5)

    def test_efficiency_can_drag_a_lucky_team_down(self, blend_on):
        """The whole point: a high-ELO team with mediocre efficiency loses ground."""
        lucky = make_team(elo=1800.0, offense_ppa=0.05, defense_ppa=0.05)
        assert effective_rating(lucky, week=10, scale=SCALE) < lucky.elo_rating

    def test_early_season_uses_pure_elo(self, blend_on):
        team = make_team(elo=1700.0, offense_ppa=0.1, defense_ppa=0.0)
        assert effective_rating(team, rs.EFFICIENCY_MIN_WEEK - 1, SCALE) == 1700.0
        assert effective_rating(team, rs.EFFICIENCY_MIN_WEEK, SCALE) != 1700.0

    def test_no_week_skips_the_early_season_gate(self, blend_on):
        team = make_team(elo=1700.0, offense_ppa=0.1, defense_ppa=0.0)
        assert effective_rating(team, scale=SCALE) == pytest.approx(1662.5)

    def test_zero_weight_disables_the_blend(self, monkeypatch):
        monkeypatch.setattr(rs, "EFFICIENCY_WEIGHT", 0.0)
        team = make_team(elo=1700.0, offense_ppa=0.1, defense_ppa=0.0)
        assert effective_rating(team, week=10, scale=SCALE) == 1700.0

    def test_detached_team_without_scale_falls_back_to_elo(self, blend_on):
        """No session to derive population stats from — must not raise."""
        team = make_team(elo=1700.0, offense_ppa=0.1, defense_ppa=0.0)
        assert effective_rating(team, week=10) == 1700.0

    def test_derives_scale_from_the_teams_session(self, blend_on, db_session):
        # efficiency runs opposite to ELO, so the blend must move the rating
        for i in range(40):
            db_session.add(
                make_team(name=f"T{i}", elo=1500 + i * 10, offense_ppa=(40 - i) / 100, defense_ppa=0.0)
            )
        db_session.commit()

        team = db_session.query(Team).filter(Team.name == "T39").first()
        expected = effective_rating(team, 10, efficiency_scale(db_session))
        assert effective_rating(team, week=10) == pytest.approx(expected)
        assert effective_rating(team, week=10) != team.elo_rating

    def test_blend_preserves_the_rating_spread(self, blend_on, db_session):
        """Standardizing means the blend reorders teams without inflating the scale."""
        import statistics

        for i in range(60):
            # ELO and efficiency deliberately disagree (efficiency runs backwards)
            db_session.add(
                make_team(name=f"T{i}", elo=1500 + i, offense_ppa=(60 - i) / 100, defense_ppa=0.0)
            )
        db_session.commit()

        teams = db_session.query(Team).all()
        scale = efficiency_scale(db_session)
        before = statistics.stdev([t.elo_rating for t in teams])
        after = statistics.stdev([effective_rating(t, 10, scale) for t in teams])

        # A fixed points-per-play constant would blow this up; standardizing keeps
        # the blended spread bounded by the inputs' own spread.
        assert after <= before + 1e-6


class TestEfficiencyImport:
    def test_import_populates_ppa_columns(self, db_session):
        from src.importers.efficiency import import_team_efficiency

        db_session.add(make_team(name="Georgia"))
        db_session.commit()

        class FakeClient:
            def get_team_ppa_season(self, year, team=None):
                return [
                    {
                        "team": "Georgia",
                        "offense": {"overall": 0.25},
                        "defense": {"overall": -0.10},
                    },
                    {  # not in our DB — must be skipped, not crash
                        "team": "Nowhere State",
                        "offense": {"overall": 0.1},
                        "defense": {"overall": 0.1},
                    },
                    {"team": "Georgia", "offense": None, "defense": None},  # malformed
                ]

        assert import_team_efficiency(FakeClient(), db_session, year=2025) == 1
        team = db_session.query(Team).filter(Team.name == "Georgia").first()
        assert team.offense_ppa == pytest.approx(0.25)
        assert team.defense_ppa == pytest.approx(-0.10)

    def test_empty_api_response_leaves_existing_values(self, db_session):
        from src.importers.efficiency import import_team_efficiency

        db_session.add(make_team(name="Georgia", offense_ppa=0.2, defense_ppa=0.0))
        db_session.commit()

        class EmptyClient:
            def get_team_ppa_season(self, year, team=None):
                return []

        assert import_team_efficiency(EmptyClient(), db_session, year=2025) == 0
        team = db_session.query(Team).filter(Team.name == "Georgia").first()
        assert team.offense_ppa == pytest.approx(0.2)
