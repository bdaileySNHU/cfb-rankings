"""CLI entry-point shim for the CFBD data import pipeline.

The implementation lives in ``src/importers/`` (restructure phase 5). This
module re-exports the package's public names so existing callers keep working
unchanged:

- ``python import_real_data.py [--reset --season --max-week ...]`` from the
  project root (production_import.sh, deploy/setup.sh, utilities/weekly_update.sh,
  scripts/weekly_update.py)
- ``from import_real_data import import_teams, import_games, ...`` (tests)
"""

import sys
from pathlib import Path

# Allow running from outside the project root
sys.path.insert(0, str(Path(__file__).parent))

from src.importers import (  # noqa: F401,E402
    CONFERENCE_MAP,
    apply_quarter_scores,
    check_for_duplicates,
    find_existing_game,
    get_or_create_fcs_team,
    get_week_statistics,
    import_ap_poll_rankings,
    import_bowl_games,
    import_conference_championships,
    import_games,
    import_playoff_games,
    import_teams,
    main,
    parse_game_date,
    print_duplicate_report,
    validate_api_connection,
    validate_import_results,
)

if __name__ == "__main__":
    main()
