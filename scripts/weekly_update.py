#!/usr/bin/env python3
"""
Weekly Update Script for College Football Rankings System

Automatically imports new game data every Sunday evening during the active season.
Performs pre-flight checks before executing data import:
  1. Verify we're in active season (August 1 - January 31)
  2. Detect current week from CFBD API
  3. Check API usage is below 90% threshold
  4. Execute import_real_data.py if all checks pass

Usage:
    python3 scripts/weekly_update.py

Exit Codes:
    0 - Success (data imported or gracefully skipped)
    1 - Failure (check failed or import error)
"""

import sys
import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cfbd_client import CFBDClient, get_monthly_usage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def is_active_season() -> bool:
    """
    Check if current date is during active CFB season.

    Active season runs from August 1 through January 31.
    This accounts for the season spanning two calendar years
    (e.g., 2025 season runs Aug 2025 - Jan 2026).

    Returns:
        bool: True if current month is August through January, False otherwise

    Examples:
        >>> # August 15, 2025 → True
        >>> # December 20, 2025 → True
        >>> # January 10, 2026 → True
        >>> # March 5, 2026 → False
    """
    today = datetime.now()
    month = today.month

    # Active season: August (8) through December (12) OR January (1)
    return month >= 8 or month <= 1


def check_api_usage() -> bool:
    """
    Check if CFBD API usage is below 90% threshold.

    Calls the get_monthly_usage() function from Story 001 to check
    current month's API usage against the configured limit.

    Returns:
        bool: True if usage < 90%, False if usage >= 90%

    Side Effects:
        Logs INFO message with current usage percentage and remaining calls
        Logs CRITICAL message if usage >= 90%
    """
    try:
        usage = get_monthly_usage()
        percentage = usage['percentage_used']
        remaining = usage['remaining_calls']
        total = usage['total_calls']
        limit = usage['monthly_limit']

        if percentage >= 90:
            logger.critical(
                f"API usage at {percentage}% ({total}/{limit} calls) - "
                f"aborting weekly update to prevent quota exhaustion"
            )
            return False

        logger.info(
            f"API usage check passed: {percentage}% used "
            f"({remaining} calls remaining out of {limit})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to check API usage: {e}", exc_info=True)
        logger.warning("Proceeding with caution - could not verify API usage")
        return True  # Proceed anyway if usage check fails


def get_current_week_wrapper() -> int:
    """
    Wrapper to get current week from CFBD API.

    Uses the CFBDClient.get_current_week() method which queries
    the CFBD games endpoint to find the highest week with completed games.

    Returns:
        int: Current week number (1-15), or None if no week detected

    Raises:
        Exception: If CFBD API call fails after retries
    """
    try:
        client = CFBDClient()
        season = client.get_current_season()
        current_week = client.get_current_week(season)

        if current_week:
            logger.info(f"Current week detected: Week {current_week} of {season} season")
            return current_week
        else:
            logger.warning(
                "Could not detect current week - no completed games found. "
                "Season may not have started yet."
            )
            return None

    except Exception as e:
        logger.error(f"Failed to detect current week: {e}", exc_info=True)
        raise


def run_import_script() -> int:
    """
    Execute the import_real_data.py script.

    Runs the existing import script as a subprocess, automatically
    answering "yes" to any confirmation prompts.

    Returns:
        int: Exit code from import script (0 for success, non-zero for failure)

    Side Effects:
        Logs start time, end time, duration, and success/failure status
        Logs stdout/stderr from import script if it fails
    """
    import_script = project_root / "import_real_data.py"

    if not import_script.exists():
        logger.error(f"Import script not found: {import_script}")
        return 1

    logger.info(f"Starting data import: {import_script}")
    start_time = datetime.now()

    try:
        # Run import script with automatic "yes" to prompts
        result = subprocess.run(
            [sys.executable, str(import_script)],
            input="yes\n",
            text=True,
            capture_output=True,
            timeout=1800,  # 30 minute timeout
            cwd=str(project_root)
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if result.returncode == 0:
            logger.info(f"Data import completed successfully in {duration:.1f} seconds")
            logger.debug(f"Import output: {result.stdout[:500]}")  # Log first 500 chars
            return 0
        else:
            logger.error(
                f"Data import failed with exit code {result.returncode} "
                f"after {duration:.1f} seconds"
            )
            logger.error(f"STDOUT:\n{result.stdout}")
            logger.error(f"STDERR:\n{result.stderr}")
            return result.returncode

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"Data import timed out after {duration:.1f} seconds (30 min limit)")
        return 1

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"Unexpected error during data import after {duration:.1f} seconds: {e}",
            exc_info=True
        )
        return 1


def main():
    """
    Main entry point for weekly update script.

    Executes pre-flight checks and runs data import if all checks pass:
      1. Check if we're in active season (Aug-Jan)
      2. Detect current week from CFBD API
      3. Check API usage < 90%
      4. Run import_real_data.py

    Exit Codes:
        0 - Success (data imported or gracefully skipped due to off-season)
        1 - Failure (check failed or import error)
    """
    logger.info("=" * 80)
    logger.info("CFB Rankings Weekly Update Started")
    logger.info("=" * 80)

    # Check 1: Active season
    logger.info("Check 1: Verifying active season (August 1 - January 31)...")
    if not is_active_season():
        logger.info("Off-season detected - skipping weekly update (this is normal)")
        logger.info("Weekly update will resume automatically in August")
        logger.info("=" * 80)
        sys.exit(0)  # Graceful exit - not an error

    logger.info("✓ Active season confirmed")

    # Check 2: Current week detection
    logger.info("Check 2: Detecting current week from CFBD API...")
    try:
        current_week = get_current_week_wrapper()
        if not current_week:
            logger.warning(
                "Could not detect current week - aborting weekly update. "
                "This may indicate the season hasn't started yet."
            )
            logger.info("=" * 80)
            sys.exit(1)
        logger.info(f"✓ Current week: {current_week}")
    except Exception as e:
        logger.error(f"Week detection failed: {e}")
        logger.info("=" * 80)
        sys.exit(1)

    # Check 3: API usage
    logger.info("Check 3: Verifying API usage is below 90% threshold...")
    if not check_api_usage():
        logger.error("API usage threshold exceeded - aborting to prevent quota exhaustion")
        logger.info("=" * 80)
        sys.exit(1)
    logger.info("✓ API usage check passed")

    # Execute import
    logger.info("All pre-flight checks passed - starting data import...")
    logger.info("-" * 80)

    exit_code = run_import_script()

    logger.info("-" * 80)
    if exit_code == 0:
        logger.info("✅ Weekly update completed successfully")
    else:
        logger.error(f"❌ Weekly update failed with exit code {exit_code}")

    logger.info("=" * 80)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
