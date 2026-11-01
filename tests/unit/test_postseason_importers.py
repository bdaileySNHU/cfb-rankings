"""Characterization tests for the postseason importers (CCGs, bowls, CFP).

Pins the Game rows each importer writes — which feed games it picks, the
week/game_type/postseason_name it stores, and how it re-tags rows that
already exist — so the three importers can share one loop safely.
"""

from unittest.mock import MagicMock, patch

import pytest
from factories import TeamFactory, configure_factories
from sqlalchemy.orm import Session

from src.importers.postseason import (
    import_bowl_games,
    import_conference_championships,
    import_playoff_games,
)
from src.models.models import Game

TEAMS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]


def feed(home, away, notes, week=1, home_pts=None, away_pts=None):
    return {
        "id": 1,
        "homeTeam": home,
        "awayTeam": away,
        "notes": notes,
        "week": week,
        "homePoints": home_pts,
        "awayPoints": away_pts,
        "completed": home_pts is not None,
        "neutralSite": True,
    }


@pytest.fixture
def teams(test_db: Session):
    configure_factories(test_db)
    return {n: TeamFactory(name=n) for n in TEAMS}


@pytest.fixture
def ranking_service():
    rs = MagicMock()
    rs.process_game.return_value = {"winner_name": "W", "loser_name": "L", "score": "1-0"}
    return rs


def make_cfbd(regular_by_week=None, postseason=None):
    cfbd = MagicMock()

    def get_games(year, week=None, season_type="regular", classification=None):
        if season_type == "postseason":
            return postseason or []
        return (regular_by_week or {}).get(week, [])

    cfbd.get_games.side_effect = get_games
    cfbd.get_game_line_scores.return_value = None
    return cfbd


def rows(db):
    return sorted(
        (g.home_team.name, g.away_team.name, g.week, g.game_type, g.postseason_name,
         g.home_score, g.away_score)
        for g in db.query(Game).all()
    )


@pytest.mark.unit
class TestConferenceChampionships:
    def test_picks_championships_and_stores_rows(self, test_db, teams, ranking_service):
        cfbd = make_cfbd(regular_by_week={
            14: [
                feed("A", "B", "SEC Championship", week=14, home_pts=28, away_pts=21),
                feed("C", "D", "Big Ten Championship", week=14),
                feed("E", "F", None, week=14, home_pts=10, away_pts=7),  # regular game
                feed("G", "H", "CFP Playoff Championship", week=14),  # CFP, excluded
                feed("X", "B", "MAC Championship", week=14),  # unknown team
            ],
            15: [feed("I", "J", "Army-Navy championship", week=15, home_pts=3, away_pts=0)],
        })
        with patch("src.importers.postseason.create_and_store_prediction") as predict:
            predict.return_value = None
            n = import_conference_championships(cfbd, test_db, teams, 2024, ranking_service)

        assert n == 3
        assert rows(test_db) == [
            ("A", "B", 14, "conference_championship", None, 28, 21),
            ("C", "D", 14, "conference_championship", None, 0, 0),
            ("I", "J", 15, "conference_championship", None, 3, 0),
        ]
        assert ranking_service.process_game.call_count == 2
        assert predict.call_count == 1  # only the scheduled game

    def test_existing_row_keeps_its_game_type(self, test_db, teams, ranking_service):
        test_db.add(Game(home_team_id=teams["A"].id, away_team_id=teams["B"].id, week=14,
                         season=2024, home_score=0, away_score=0, game_type="regular"))
        test_db.commit()
        cfbd = make_cfbd(regular_by_week={
            14: [feed("A", "B", "SEC Championship", week=14, home_pts=28, away_pts=21)],
        })
        n = import_conference_championships(cfbd, test_db, teams, 2024, ranking_service)

        assert n == 1  # score update counts as imported
        assert rows(test_db) == [("A", "B", 14, "regular", None, 28, 21)]
        ranking_service.process_game.assert_called_once()


@pytest.mark.unit
class TestBowlGames:
    def test_picks_bowls_and_fixes_week(self, test_db, teams, ranking_service):
        cfbd = make_cfbd(postseason=[
            feed("A", "B", "Rose Bowl Game", week=1, home_pts=35, away_pts=31),
            feed("C", "D", None, week=17),
            feed("E", "F", "SEC Championship", week=16),  # conference champ, excluded
            feed("G", "H", "CFP Semifinal at the Sugar Bowl", week=17),  # playoff, excluded
        ])
        n = import_bowl_games(cfbd, test_db, teams, 2024, ranking_service)

        assert n == 2
        assert rows(test_db) == [
            ("A", "B", 16, "bowl", "Rose Bowl Game", 35, 31),
            ("C", "D", 17, "bowl", "Bowl Game", 0, 0),
        ]
        ranking_service.process_game.assert_called_once()

    def test_existing_row_gets_name_filled(self, test_db, teams, ranking_service):
        test_db.add(Game(home_team_id=teams["A"].id, away_team_id=teams["B"].id, week=16,
                         season=2024, home_score=35, away_score=31, game_type="bowl",
                         is_processed=True))
        test_db.commit()
        cfbd = make_cfbd(postseason=[
            feed("A", "B", "Rose Bowl Game", week=16, home_pts=35, away_pts=31),
        ])
        n = import_bowl_games(cfbd, test_db, teams, 2024, ranking_service)

        assert n == 0
        assert rows(test_db) == [("A", "B", 16, "bowl", "Rose Bowl Game", 35, 31)]
        ranking_service.process_game.assert_not_called()

    def test_processing_error_does_not_abort(self, test_db, teams, ranking_service):
        ranking_service.process_game.side_effect = RuntimeError("boom")
        cfbd = make_cfbd(postseason=[
            feed("A", "B", "Rose Bowl Game", week=16, home_pts=35, away_pts=31),
            feed("C", "D", "Sugar Bowl", week=16, home_pts=20, away_pts=10),
        ])
        assert import_bowl_games(cfbd, test_db, teams, 2024, ranking_service) == 2


@pytest.mark.unit
class TestPlayoffGames:
    def test_rounds_map_to_weeks_12_team(self, test_db, teams, ranking_service):
        cfbd = make_cfbd(postseason=[
            feed("A", "B", "CFP National Championship", week=1, home_pts=34, away_pts=23),
            feed("C", "D", "CFP Semifinal at the Rose Bowl", week=1),
            feed("E", "F", "CFP Quarterfinal", week=1),
            feed("G", "H", "CFP First Round", week=1),
            feed("I", "J", "College Football Playoff", week=5),
        ])
        n = import_playoff_games(cfbd, test_db, teams, 2024, ranking_service)

        assert n == 5
        assert rows(test_db) == [
            ("A", "B", 19, "playoff", "CFP National Championship", 34, 23),
            ("C", "D", 18, "playoff", "CFP Semifinal - Rose Bowl", 0, 0),
            ("E", "F", 17, "playoff", "CFP Quarterfinal", 0, 0),
            ("G", "H", 16, "playoff", "CFP First Round", 0, 0),
            ("I", "J", 17, "playoff", "CFP Game", 0, 0),
        ]

    def test_rounds_map_to_weeks_4_team(self, test_db, teams, ranking_service):
        cfbd = make_cfbd(postseason=[
            feed("A", "B", "CFP National Championship", week=1),
            feed("C", "D", "CFP Semifinal at the Orange Bowl", week=1),
        ])
        import_playoff_games(cfbd, test_db, teams, 2023, ranking_service)

        assert rows(test_db) == [
            ("A", "B", 18, "playoff", "CFP National Championship", 0, 0),
            ("C", "D", 17, "playoff", "CFP Semifinal - Orange Bowl", 0, 0),
        ]

    def test_existing_bowl_row_is_retagged(self, test_db, teams, ranking_service):
        test_db.add(Game(home_team_id=teams["A"].id, away_team_id=teams["B"].id, week=17,
                         season=2024, home_score=0, away_score=0, game_type="bowl",
                         postseason_name="Fiesta Bowl"))
        test_db.commit()
        cfbd = make_cfbd(postseason=[feed("A", "B", "CFP Quarterfinal at the Fiesta Bowl")])
        import_playoff_games(cfbd, test_db, teams, 2024, ranking_service)

        assert rows(test_db) == [("A", "B", 17, "playoff", "CFP Quarterfinal", 0, 0)]
