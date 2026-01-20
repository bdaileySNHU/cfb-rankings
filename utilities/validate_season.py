#!/usr/bin/env python3
"""Season Data Validation and Integrity Check

This script performs comprehensive validation of season data to ensure
all games are imported, processed correctly, and data integrity is maintained.

Usage:
    python utilities/validate_season.py --season 2025
    python utilities/validate_season.py --season 2025 --verbose
    python utilities/validate_season.py --season 2025 --output docs/season-2025-validation-report.md

Part of EPIC-SEASON-END-2025: Story 1 - Season Data Validation
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import func

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import database and models
from src.models.database import SessionLocal
from src.models.models import APPollRanking, Game, RankingHistory, Season, Team


class ValidationReport:
    """Collects validation findings and generates markdown report."""

    def __init__(self, season: int):
        self.season = season
        self.status = "PASS"
        self.summary: Dict[str, Any] = {}
        self.findings: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def add_finding(self, message: str) -> None:
        """Add a general finding to the report."""
        self.findings.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning to the report."""
        self.warnings.append(message)
        print(f"⚠ {message}")

    def add_error(self, message: str) -> None:
        """Add an error to the report and mark status as FAIL."""
        self.errors.append(message)
        self.status = "FAIL"
        print(f"✗ {message}")

    def generate_markdown(self) -> str:
        """Generate markdown report from collected findings."""
        lines = [
            f"# Season {self.season} Validation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Season:** {self.season}",
            f"**Status:** {'✅' if self.status == 'PASS' else '❌'} {self.status}",
            "",
            "## Summary",
            "",
        ]

        # Add summary statistics
        for key, value in self.summary.items():
            lines.append(f"- **{key}:** {value}")

        lines.append("")
        lines.append("## Detailed Findings")
        lines.append("")

        # Game completeness
        lines.append("### Game Completeness")
        lines.append("")
        game_findings = [f for f in self.findings if "games" in f.lower() or "week" in f.lower()]
        if game_findings:
            for finding in game_findings[:10]:  # Limit to first 10
                lines.append(f"- {finding}")
        else:
            lines.append("- ✅ No issues found")
        lines.append("")

        # ELO integrity
        lines.append("### ELO Rating Integrity")
        lines.append("")
        elo_findings = [f for f in self.findings if "elo" in f.lower() or "rating" in f.lower()]
        if elo_findings:
            for finding in elo_findings[:10]:
                lines.append(f"- {finding}")
        else:
            lines.append("- ✅ All ELO calculations verified")
        lines.append("")

        # AP Poll data
        lines.append("### AP Poll Data")
        lines.append("")
        ap_findings = [f for f in self.findings if "ap" in f.lower() or "poll" in f.lower()]
        if ap_findings:
            for finding in ap_findings[:10]:
                lines.append(f"- {finding}")
        else:
            lines.append("- ✅ AP Poll data complete")
        lines.append("")

        # Warnings
        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in self.warnings:
                lines.append(f"- ⚠ {warning}")
            lines.append("")

        # Errors
        if self.errors:
            lines.append("## Errors")
            lines.append("")
            for error in self.errors:
                lines.append(f"- ✗ {error}")
            lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if self.status == "PASS":
            lines.append("✅ **Ready for Finalization** - All critical data validated")
            lines.append("- Proceed with statistics calculation (Story 2)")
            lines.append("- Proceed with season archival (Story 3)")
        else:
            lines.append("❌ **Not Ready for Finalization** - Issues must be resolved")
            lines.append("- Review and fix errors listed above")
            lines.append("- Re-run validation after fixes")
            lines.append("- Do not proceed with archival until validation passes")
        lines.append("")

        # Actions required
        lines.append("## Actions Required")
        lines.append("")
        if self.errors:
            lines.append("The following actions are required before finalization:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"{i}. {error}")
        else:
            lines.append("- None - validation successful")

        return "\n".join(lines)


def validate_game_completeness(db: Any, season: int, report: ValidationReport, verbose: bool) -> None:
    """Validate that all games for the season are imported and processed."""
    print("Validating game completeness...")

    # Count total games
    total_games = db.query(Game).filter(Game.season == season).count()
    report.summary["Total Games"] = total_games

    if total_games == 0:
        report.add_error(f"No games found for season {season}")
        return

    # Count games by week
    games_by_week = (
        db.query(Game.week, func.count(Game.id))
        .filter(Game.season == season)
        .group_by(Game.week)
        .order_by(Game.week)
        .all()
    )

    week_counts = {week: count for week, count in games_by_week}

    # Check for missing weeks (should have data for weeks 1-20)
    for week in range(1, 21):
        count = week_counts.get(week, 0)
        if count == 0:
            # Week 16-20 might not have games every week (postseason)
            if week >= 16:
                report.add_warning(f"Week {week} has no games (postseason week - may be expected)")
            else:
                report.add_error(f"Week {week} has no games (missing data)")
        elif count < 10 and week <= 15:  # Regular season should have many games
            report.add_warning(f"Week {week} has only {count} games (expected more)")
        elif verbose:
            print(f"  Week {week}: {count} games")

    # Check for unprocessed games
    unprocessed_count = db.query(Game).filter(Game.season == season, Game.is_processed == False).count()
    report.summary["Games Processed"] = f"{total_games - unprocessed_count}/{total_games} ({100 * (total_games - unprocessed_count) / total_games:.1f}%)"

    if unprocessed_count > 0:
        report.add_error(f"{unprocessed_count} games are not processed")
        # List some unprocessed games
        unprocessed_games = (
            db.query(Game)
            .filter(Game.season == season, Game.is_processed == False)
            .limit(5)
            .all()
        )
        for game in unprocessed_games:
            home = db.query(Team).filter(Team.id == game.home_team_id).first()
            away = db.query(Team).filter(Team.id == game.away_team_id).first()
            report.add_finding(
                f"Unprocessed game: Week {game.week} - {home.name if home else 'Unknown'} vs {away.name if away else 'Unknown'}"
            )
    else:
        print(f"✓ All {total_games} games processed correctly")

    # Check for teams with 0 games
    teams_with_games = (
        db.query(Team.id)
        .join(Game, (Game.home_team_id == Team.id) | (Game.away_team_id == Team.id))
        .filter(Game.season == season)
        .distinct()
        .all()
    )
    teams_with_games_ids = {t[0] for t in teams_with_games}

    # Get all FBS teams (excluding FCS)
    all_fbs_teams = db.query(Team).filter(Team.is_fcs == False).all()
    teams_without_games = [t for t in all_fbs_teams if t.id not in teams_with_games_ids]

    if teams_without_games:
        report.add_warning(f"{len(teams_without_games)} FBS teams have no games in season {season}")
        for team in teams_without_games[:5]:  # List first 5
            report.add_finding(f"Team with no games: {team.name}")


def validate_elo_integrity(db: Any, season: int, report: ValidationReport, verbose: bool) -> None:
    """Validate ELO rating changes are zero-sum and correctly calculated."""
    print("Validating ELO rating integrity...")

    # Get all processed games
    games = db.query(Game).filter(Game.season == season, Game.is_processed == True).all()

    if not games:
        report.add_error("No processed games found for ELO validation")
        return

    elo_imbalances = []
    suspicious_changes = []

    for game in games:
        # Check zero-sum property (home_rating_change + away_rating_change ≈ 0)
        rating_sum = game.home_rating_change + game.away_rating_change
        if abs(rating_sum) > 0.01:  # Allow small floating-point tolerance
            elo_imbalances.append((game, rating_sum))

        # Check for suspicious large rating changes (>200 points)
        if abs(game.home_rating_change) > 200 or abs(game.away_rating_change) > 200:
            suspicious_changes.append(game)

    # Report ELO imbalances
    if elo_imbalances:
        report.add_error(f"{len(elo_imbalances)} games have ELO rating imbalances")
        for game, imbalance in elo_imbalances[:5]:  # Show first 5
            home = db.query(Team).filter(Team.id == game.home_team_id).first()
            away = db.query(Team).filter(Team.id == game.away_team_id).first()
            report.add_finding(
                f"ELO imbalance in Week {game.week}: {home.name if home else 'Unknown'} vs {away.name if away else 'Unknown'} (imbalance: {imbalance:.4f})"
            )
    else:
        print(f"✓ All {len(games)} games pass zero-sum ELO check")

    # Report suspicious changes
    if suspicious_changes:
        report.add_warning(f"{len(suspicious_changes)} games have large rating changes (>200 points)")
        for game in suspicious_changes[:3]:  # Show first 3
            home = db.query(Team).filter(Team.id == game.home_team_id).first()
            away = db.query(Team).filter(Team.id == game.away_team_id).first()
            report.add_finding(
                f"Large rating change in Week {game.week}: {home.name if home else 'Unknown'} ({game.home_rating_change:+.1f}) vs {away.name if away else 'Unknown'} ({game.away_rating_change:+.1f})"
            )

    # Verify team current ELO = initial_rating + sum(all rating changes)
    # This is a more complex check - sample a few teams
    teams_to_check = db.query(Team).filter(Team.is_fcs == False).limit(10).all()
    elo_calculation_errors = []

    for team in teams_to_check:
        # Get all games for this team
        home_games = db.query(Game).filter(
            Game.season == season,
            Game.home_team_id == team.id,
            Game.is_processed == True
        ).all()
        away_games = db.query(Game).filter(
            Game.season == season,
            Game.away_team_id == team.id,
            Game.is_processed == True
        ).all()

        # Sum rating changes
        total_change = sum(g.home_rating_change for g in home_games) + sum(g.away_rating_change for g in away_games)
        expected_current = team.initial_rating + total_change

        # Check if current rating matches expected
        if abs(team.elo_rating - expected_current) > 1.0:  # Allow 1 point tolerance
            elo_calculation_errors.append((team, expected_current, team.elo_rating))

    if elo_calculation_errors:
        report.add_error(f"{len(elo_calculation_errors)} teams have ELO calculation mismatches")
        for team, expected, actual in elo_calculation_errors[:5]:
            report.add_finding(
                f"ELO mismatch for {team.name}: expected {expected:.2f}, actual {actual:.2f} (diff: {abs(expected - actual):.2f})"
            )
    elif verbose:
        print(f"  Spot-checked {len(teams_to_check)} teams - ELO calculations verified")


def validate_ap_poll_completeness(db: Any, season: int, report: ValidationReport, verbose: bool) -> None:
    """Validate AP Poll data completeness for the season."""
    print("Validating AP Poll data...")

    # Count total AP Poll entries
    total_ap_entries = db.query(APPollRanking).filter(APPollRanking.season == season).count()
    report.summary["AP Poll Entries"] = total_ap_entries

    if total_ap_entries == 0:
        report.add_warning(f"No AP Poll data found for season {season}")
        return

    # Count entries by week
    ap_by_week = (
        db.query(APPollRanking.week, func.count(APPollRanking.id))
        .filter(APPollRanking.season == season)
        .group_by(APPollRanking.week)
        .order_by(APPollRanking.week)
        .all()
    )

    week_counts = {week: count for week, count in ap_by_week}

    # Check for missing weeks
    missing_weeks = []
    for week in range(1, 21):
        count = week_counts.get(week, 0)
        if count == 0:
            missing_weeks.append(week)
        elif count < 25:  # AP Poll typically has 25 teams
            if week >= 16:  # Postseason may have incomplete polls
                if verbose:
                    print(f"  Week {week}: {count} AP Poll entries (postseason)")
            else:
                report.add_warning(f"Week {week} has only {count} AP Poll entries (expected 25)")
        elif verbose:
            print(f"  Week {week}: {count} AP Poll entries")

    if missing_weeks:
        # Filter to regular season missing weeks (more concerning)
        regular_season_missing = [w for w in missing_weeks if w <= 15]
        postseason_missing = [w for w in missing_weeks if w > 15]

        if regular_season_missing:
            report.add_warning(f"AP Poll data missing for regular season weeks: {regular_season_missing}")
        if postseason_missing and verbose:
            print(f"  Note: AP Poll not published for postseason weeks: {postseason_missing} (expected)")

    # Verify we have ~25 teams per week for regular season
    regular_season_weeks = [w for w in range(1, 16) if w in week_counts]
    if regular_season_weeks:
        avg_teams_per_week = sum(week_counts[w] for w in regular_season_weeks) / len(regular_season_weeks)
        report.summary["Avg AP Poll Teams/Week"] = f"{avg_teams_per_week:.1f}"

        if avg_teams_per_week < 20:
            report.add_warning(f"Average AP Poll entries per week is low: {avg_teams_per_week:.1f} (expected ~25)")
    else:
        report.add_warning("No AP Poll data for regular season weeks")


def validate_missing_data(db: Any, season: int, report: ValidationReport, verbose: bool) -> None:
    """Check for duplicate games, unusual records, and data anomalies."""
    print("Checking for data anomalies...")

    # Check for duplicate games (same teams, same week, same season)
    duplicates = (
        db.query(
            Game.home_team_id,
            Game.away_team_id,
            Game.week,
            func.count(Game.id).label("count")
        )
        .filter(Game.season == season)
        .group_by(Game.home_team_id, Game.away_team_id, Game.week)
        .having(func.count(Game.id) > 1)
        .all()
    )

    if duplicates:
        report.add_error(f"{len(duplicates)} duplicate game entries found")
        for home_id, away_id, week, count in duplicates[:5]:
            home = db.query(Team).filter(Team.id == home_id).first()
            away = db.query(Team).filter(Team.id == away_id).first()
            report.add_finding(
                f"Duplicate game in Week {week}: {home.name if home else 'Unknown'} vs {away.name if away else 'Unknown'} ({count} entries)"
            )
    elif verbose:
        print("  No duplicate games found")

    # Check for teams with unusual records (0-0, 20-0, etc.)
    unusual_records = []
    all_teams = db.query(Team).filter(Team.is_fcs == False).all()

    for team in all_teams:
        total_games = team.wins + team.losses
        if total_games == 0:
            unusual_records.append((team, "0-0"))
        elif total_games > 17:  # Max ~15 games typically
            unusual_records.append((team, f"{team.wins}-{team.losses}"))

    if unusual_records:
        report.add_warning(f"{len(unusual_records)} teams have unusual records")
        for team, record in unusual_records[:5]:
            report.add_finding(f"Unusual record: {team.name} ({record})")

    # Check for teams with missing preseason data (recruiting_rank = 999)
    missing_preseason = db.query(Team).filter(
        Team.is_fcs == False,
        Team.recruiting_rank == 999
    ).count()

    if missing_preseason > 0:
        report.add_warning(f"{missing_preseason} FBS teams missing preseason recruiting data")


def main():
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate season data integrity and completeness"
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to validate (e.g., 2025)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output during validation"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for markdown report (e.g., docs/season-2025-validation-report.md)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Season {args.season} Validation")
    print(f"{'='*60}\n")

    # Create database session
    db = SessionLocal()

    try:
        # Check if season exists
        season = db.query(Season).filter(Season.year == args.season).first()
        if not season:
            print(f"✗ Season {args.season} not found in database")
            sys.exit(1)

        # Create validation report
        report = ValidationReport(args.season)

        # Run validation checks
        validate_game_completeness(db, args.season, report, args.verbose)
        validate_elo_integrity(db, args.season, report, args.verbose)
        validate_ap_poll_completeness(db, args.season, report, args.verbose)
        validate_missing_data(db, args.season, report, args.verbose)

        # Calculate data quality score
        total_checks = 4
        passed_checks = total_checks - len(report.errors)
        quality_score = (passed_checks / total_checks) * 100
        report.summary["Data Quality Score"] = f"{quality_score:.1f}%"

        # Print summary
        print(f"\n{'='*60}")
        print("Validation Summary")
        print(f"{'='*60}")
        for key, value in report.summary.items():
            print(f"{key}: {value}")
        print(f"\nStatus: {report.status}")
        print(f"Warnings: {len(report.warnings)}")
        print(f"Errors: {len(report.errors)}")
        print(f"{'='*60}\n")

        # Generate and save markdown report
        markdown_report = report.generate_markdown()

        if args.output:
            with open(args.output, "w") as f:
                f.write(markdown_report)
            print(f"✓ Validation report written to: {args.output}")
        else:
            print("Validation report:")
            print(markdown_report)

        # Exit with appropriate code
        sys.exit(0 if report.status == "PASS" else 1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
