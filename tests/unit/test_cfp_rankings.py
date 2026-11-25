"""EPIC-046: CFP committee rankings beside the AP Poll on the comparison page."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.ap_poll_service import calculate_comparison_stats
from src.importers.polls import import_ap_poll_rankings
from src.integrations.cfbd_client import CFBDClient
from src.models.models import (
    APPollRanking,
    CFPRanking,
    Game,
    Prediction,
    RankingHistory,
    Season,
    Team,
)

CFP = "Playoff Committee Rankings"


def _rankings_response(*polls):
    return [
        {
            "season": 2026,
            "seasonType": "regular",
            "week": 11,
            "polls": [
                {"poll": name, "ranks": [{"rank": r, "school": s} for r, s in ranks]}
                for name, ranks in polls
            ],
        }
    ]


@pytest.mark.unit
def test_client_returns_requested_polls_from_one_call():
    client = CFBDClient()
    response = _rankings_response(
        ("AP Top 25", [(1, "Georgia")]), (CFP, [(1, "Utah")]), ("Coaches Poll", [(1, "Texas")])
    )
    with patch.object(client, "_get", return_value=response) as get:
        rows = client.get_ap_poll(2026, 11, polls=("AP Top 25", CFP))
    assert get.call_count == 1
    assert sorted((r["poll"], r["school"]) for r in rows) == [
        ("AP Top 25", "Georgia"),
        (CFP, "Utah"),
    ]


@pytest.mark.unit
def test_client_default_is_still_ap_only():
    client = CFBDClient()
    response = _rankings_response(("AP Top 25", [(1, "Georgia")]), (CFP, [(1, "Utah")]))
    with patch.object(client, "_get", return_value=response):
        rows = client.get_ap_poll(2026, 11)
    assert [r["school"] for r in rows] == ["Georgia"]


@pytest.mark.unit
def test_import_stores_cfp_beside_ap_without_collision(test_db):
    georgia, utah = Team(name="Georgia", conference="P5"), Team(name="Utah", conference="P5")
    test_db.add_all([georgia, utah])
    test_db.commit()
    teams = {"Georgia": georgia, "Utah": utah}
    cfbd = MagicMock()

    # Same team ranked by both polls in the same week: the case the AP table's
    # UNIQUE(season, week, team_id) would reject.
    cfbd.get_ap_poll.return_value = [
        {"poll": "AP Top 25", "rank": 1, "school": "Georgia"},
        {"poll": "AP Top 25", "rank": 2, "school": "Utah"},
        {"poll": CFP, "rank": 1, "school": "Utah"},
        {"poll": CFP, "rank": 2, "school": "Georgia"},
    ]
    import_ap_poll_rankings(cfbd, test_db, teams, 2026, 11)

    # Committee re-ranks later in the week: re-import updates in place.
    cfbd.get_ap_poll.return_value = [
        {"poll": "AP Top 25", "rank": 1, "school": "Georgia"},
        {"poll": CFP, "rank": 3, "school": "Utah"},
    ]
    import_ap_poll_rankings(cfbd, test_db, teams, 2026, 11)

    assert {(r.team_id, r.rank) for r in test_db.query(APPollRanking)} == {
        (georgia.id, 1),
        (utah.id, 2),
    }
    assert {(r.team_id, r.rank) for r in test_db.query(CFPRanking)} == {
        (utah.id, 3),
        (georgia.id, 2),
    }
    assert cfbd.get_ap_poll.call_count == 2  # one API call per import, not one per poll


@pytest.mark.unit
def test_comparison_grades_cfp_only_on_committee_weeks(test_db):
    a, b, c, d = (Team(name=n, conference="P5") for n in "ABCD")
    test_db.add_all([a, b, c, d])
    test_db.flush()
    # Week 5: no committee rankings exist yet, so CFP makes no pick.
    early = Game(
        season=2026,
        week=5,
        home_team_id=a.id,
        away_team_id=b.id,
        home_score=10,
        away_score=20,
        is_processed=True,
    )
    # Week 11: CFP has C #1 over D #4; D wins. ELO picked D.
    late = Game(
        season=2026,
        week=11,
        home_team_id=c.id,
        away_team_id=d.id,
        home_score=7,
        away_score=14,
        is_processed=True,
    )
    test_db.add_all([early, late])
    test_db.flush()
    test_db.add_all(
        [
            Prediction(
                game_id=early.id,
                predicted_winner_id=b.id,
                win_probability=0.6,
                was_correct=True,
                predicted_home_score=20,
                predicted_away_score=24,
                home_elo_at_prediction=1500,
                away_elo_at_prediction=1500,
            ),
            Prediction(
                game_id=late.id,
                predicted_winner_id=d.id,
                win_probability=0.6,
                was_correct=True,
                predicted_home_score=20,
                predicted_away_score=24,
                home_elo_at_prediction=1500,
                away_elo_at_prediction=1500,
            ),
            CFPRanking(season=2026, week=11, team_id=c.id, rank=1),
            CFPRanking(season=2026, week=11, team_id=d.id, rank=4),
        ]
    )
    test_db.commit()

    stats = calculate_comparison_stats(test_db, 2026)

    assert stats["cfp_games_compared"] == 1
    assert stats["cfp_correct"] == 0
    assert stats["elo_correct_vs_cfp"] == 1
    assert stats["elo_advantage_vs_cfp"] == 1.0


@pytest.mark.unit
def test_rankings_compare_includes_cfp(test_client, test_db):
    test_db.add(Season(year=2026, current_week=12, is_active=True))
    a = Team(name="Alpha", conference="P5")
    test_db.add(a)
    test_db.flush()
    test_db.add(
        RankingHistory(
            team_id=a.id,
            season=2026,
            week=12,
            rank=1,
            elo_rating=1700,
            wins=0,
            losses=0,
            sos=0,
            sos_rank=1,
        )
    )
    test_db.add(CFPRanking(season=2026, week=11, team_id=a.id, rank=5))
    test_db.add(CFPRanking(season=2026, week=13, team_id=a.id, rank=9))  # future: ignored
    test_db.commit()

    data = test_client.get("/api/rankings/compare?season=2026").json()

    assert data["cfp_week"] == 11
    assert data["teams"][0]["cfp_rank"] == 5
