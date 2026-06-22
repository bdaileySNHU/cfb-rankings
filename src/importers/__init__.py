"""
CFBD data import pipeline.

Split out of the monolithic root-level import_real_data.py (restructure
phase 5). The root module remains as a CLI shim that re-exports this
package's public names.
"""

from src.importers.common import (
    CONFERENCE_MAP,
    apply_quarter_scores,
    find_existing_game,
    get_or_create_fcs_team,
    parse_game_date,
)
from src.importers.games import import_games
from src.importers.pipeline import main
from src.importers.polls import import_ap_poll_rankings
from src.importers.postseason import (
    import_bowl_games,
    import_conference_championships,
    import_playoff_games,
)
from src.importers.teams import import_teams
from src.importers.validation import (
    check_for_duplicates,
    get_week_statistics,
    print_duplicate_report,
    validate_api_connection,
    validate_import_results,
)

__all__ = [
    "CONFERENCE_MAP",
    "apply_quarter_scores",
    "check_for_duplicates",
    "find_existing_game",
    "get_or_create_fcs_team",
    "get_week_statistics",
    "import_ap_poll_rankings",
    "import_bowl_games",
    "import_conference_championships",
    "import_games",
    "import_playoff_games",
    "import_teams",
    "main",
    "parse_game_date",
    "print_duplicate_report",
    "validate_api_connection",
    "validate_import_results",
]
