"""Quarter scores come off the /games payload, not a second request (EPIC-021)."""

from src.importers.common import line_scores_from_game


def test_reads_line_scores_from_game_payload():
    game = {
        "homeTeam": "Georgia",
        "awayTeam": "Alabama",
        "homeLineScores": [0, 14, 7, 0],
        "awayLineScores": [7, 17, 0, 0],
    }
    assert line_scores_from_game(game) == {
        "home": [0, 14, 7, 0],
        "away": [7, 17, 0, 0],
    }


def test_overtime_games_are_skipped():
    # A fifth period means the four quarters cannot sum to the final score.
    game = {"homeLineScores": [7, 7, 7, 7, 6], "awayLineScores": [7, 7, 7, 7, 3]}
    assert line_scores_from_game(game) is None


def test_missing_or_partial_line_scores_give_none():
    assert line_scores_from_game({}) is None
    assert line_scores_from_game({"homeLineScores": None, "awayLineScores": None}) is None
    # Game still in progress: fewer than four quarters played
    assert line_scores_from_game({"homeLineScores": [7, 3], "awayLineScores": [0, 7]}) is None
