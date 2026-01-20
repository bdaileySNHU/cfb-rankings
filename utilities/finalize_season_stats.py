#!/usr/bin/env python3
"""Final Season Statistics Calculation

This script calculates comprehensive final statistics for a completed season,
including frozen rankings, prediction accuracy, AP Poll comparison, and
conference performance metrics.

Usage:
    python utilities/finalize_season_stats.py --season 2025
    python utilities/finalize_season_stats.py --season 2025 --output docs/season-2025-summary.md

Part of EPIC-SEASON-END-2025: Story 2 - Final Season Statistics Calculation
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
from src.core.ap_poll_service import calculate_comparison_stats
from src.core.ranking_service import RankingService
from src.models.database import SessionLocal
from src.models.models import APPollRanking, Game, Prediction, RankingHistory, Season, Team


class SeasonStatistics:
    """Collects and stores season statistics."""

    def __init__(self, season: int):
        self.season = season
        self.final_rankings: List[Dict[str, Any]] = []
        self.prediction_stats: Dict[str, Any] = {}
        self.ap_comparison: Dict[str, Any] = {}
        self.conference_stats: List[Dict[str, Any]] = []
        self.top_performers: Dict[str, List[Dict[str, Any]]] = {}

    def to_markdown(self) -> str:
        """Generate comprehensive markdown summary."""
        lines = [
            f"# Season {self.season} Summary Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Season:** {self.season}",
            "",
            "---",
            "",
            "## Season Overview",
            "",
        ]

        # Final Top 10
        if self.final_rankings:
            lines.append("### Final Top 10 Rankings")
            lines.append("")
            lines.append("| Rank | Team | ELO Rating | Record | SOS |")
            lines.append("|------|------|------------|--------|-----|")
            for team in self.final_rankings[:10]:
                lines.append(
                    f"| {team['rank']} | {team['name']} | {team['elo_rating']:.2f} | "
                    f"{team['wins']}-{team['losses']} | {team['sos']:.2f} |"
                )
            lines.append("")

        # Prediction Performance
        lines.append("## Prediction Performance")
        lines.append("")
        if self.prediction_stats:
            total = self.prediction_stats.get("total_predictions", 0)
            correct = self.prediction_stats.get("correct_predictions", 0)
            accuracy = self.prediction_stats.get("accuracy", 0.0)

            lines.append(f"- **Total Predictions:** {total}")
            lines.append(f"- **Correct Predictions:** {correct}")
            lines.append(f"- **Overall Accuracy:** {accuracy:.2%}")
            lines.append("")

            # By week breakdown
            if "by_week" in self.prediction_stats:
                lines.append("### Weekly Accuracy")
                lines.append("")
                lines.append("| Week | Predictions | Correct | Accuracy |")
                lines.append("|------|-------------|---------|----------|")
                for week_data in self.prediction_stats["by_week"][:15]:  # First 15 weeks
                    week = week_data["week"]
                    count = week_data["count"]
                    correct_w = week_data["correct"]
                    acc = week_data["accuracy"]
                    lines.append(f"| {week} | {count} | {correct_w} | {acc:.2%} |")
                lines.append("")

            # Regular season vs postseason
            if "regular_season_accuracy" in self.prediction_stats:
                rs_acc = self.prediction_stats["regular_season_accuracy"]
                ps_acc = self.prediction_stats.get("postseason_accuracy", 0.0)
                lines.append("### Regular Season vs Postseason")
                lines.append("")
                lines.append(f"- **Regular Season Accuracy:** {rs_acc:.2%}")
                lines.append(f"- **Postseason Accuracy:** {ps_acc:.2%}")
                lines.append("")

        # AP Poll Comparison
        lines.append("## ELO vs AP Poll Comparison")
        lines.append("")
        if self.ap_comparison:
            elo_acc = self.ap_comparison.get("elo_accuracy", 0.0)
            ap_acc = self.ap_comparison.get("ap_accuracy", 0.0)
            games_compared = self.ap_comparison.get("games_compared", 0)

            lines.append(f"- **Games Compared:** {games_compared}")
            lines.append(f"- **ELO System Accuracy:** {elo_acc:.2%}")
            lines.append(f"- **AP Poll Accuracy:** {ap_acc:.2%}")
            lines.append(f"- **ELO Advantage:** {(elo_acc - ap_acc):.2%}")
            lines.append("")

        # Conference Performance
        lines.append("## Conference Analysis")
        lines.append("")
        if self.conference_stats:
            lines.append("| Conference | Avg ELO | Teams in Top 25 | Win % |")
            lines.append("|------------|---------|------------------|-------|")
            for conf in self.conference_stats[:10]:
                lines.append(
                    f"| {conf['name']} | {conf['avg_elo']:.2f} | "
                    f"{conf['top_25_count']} | {conf['win_pct']:.1%} |"
                )
            lines.append("")

        # Notable Achievements
        lines.append("## Notable Achievements")
        lines.append("")

        if self.top_performers.get("biggest_risers"):
            lines.append("### Biggest Risers (ELO Gain from Preseason)")
            lines.append("")
            for team in self.top_performers["biggest_risers"][:5]:
                gain = team["elo_gain"]
                lines.append(
                    f"- **{team['name']}**: {gain:+.1f} points "
                    f"({team['initial_rating']:.1f} → {team['final_rating']:.1f})"
                )
            lines.append("")

        if self.top_performers.get("biggest_fallers"):
            lines.append("### Biggest Fallers (ELO Loss from Preseason)")
            lines.append("")
            for team in self.top_performers["biggest_fallers"][:5]:
                loss = team["elo_gain"]  # Will be negative
                lines.append(
                    f"- **{team['name']}**: {loss:+.1f} points "
                    f"({team['initial_rating']:.1f} → {team['final_rating']:.1f})"
                )
            lines.append("")

        if self.top_performers.get("toughest_schedule"):
            lines.append("### Toughest Schedules (Highest SOS)")
            lines.append("")
            for team in self.top_performers["toughest_schedule"][:5]:
                lines.append(
                    f"- **{team['name']}**: SOS {team['sos']:.2f} "
                    f"(Record: {team['wins']}-{team['losses']})"
                )
            lines.append("")

        # System Insights
        lines.append("## System Insights")
        lines.append("")
        lines.append("### Key Findings")
        lines.append("")
        if self.prediction_stats:
            accuracy = self.prediction_stats.get("accuracy", 0.0)
            if accuracy >= 0.75:
                lines.append(f"- 🎯 ELO system achieved strong prediction accuracy ({accuracy:.1%})")
            elif accuracy >= 0.65:
                lines.append(f"- ✓ ELO system achieved solid prediction accuracy ({accuracy:.1%})")
            else:
                lines.append(f"- ⚠ ELO system prediction accuracy was lower than expected ({accuracy:.1%})")

        if self.ap_comparison:
            elo_acc = self.ap_comparison.get("elo_accuracy", 0.0)
            ap_acc = self.ap_comparison.get("ap_accuracy", 0.0)
            if elo_acc > ap_acc:
                diff = elo_acc - ap_acc
                lines.append(f"- 📊 ELO system outperformed AP Poll by {diff:.1%}")
            elif ap_acc > elo_acc:
                diff = ap_acc - elo_acc
                lines.append(f"- 📊 AP Poll outperformed ELO system by {diff:.1%}")
            else:
                lines.append("- 📊 ELO system and AP Poll had equivalent accuracy")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Report generated by College Football Rankings System - Season {self.season}*")

        return "\n".join(lines)


def calculate_final_rankings(db: Any, season: int) -> List[Dict[str, Any]]:
    """Calculate final frozen rankings for all teams."""
    print("Calculating final rankings...")

    ranking_service = RankingService(db)

    # Get all FBS teams sorted by ELO rating
    teams = (
        db.query(Team)
        .filter(Team.is_fcs == False)
        .order_by(Team.elo_rating.desc())
        .all()
    )

    final_rankings = []
    for rank, team in enumerate(teams, 1):
        # Calculate SOS for each team (pass team_id, not team object)
        sos = ranking_service.calculate_sos(team.id, season)

        final_rankings.append({
            "rank": rank,
            "team_id": team.id,
            "name": team.name,
            "elo_rating": team.elo_rating,
            "initial_rating": team.initial_rating,
            "wins": team.wins,
            "losses": team.losses,
            "sos": sos,
            "conference": team.conference_name or team.conference.value,
        })

    print(f"✓ Calculated rankings for {len(final_rankings)} teams")
    return final_rankings


def store_final_snapshot(db: Any, season: int, rankings: List[Dict[str, Any]]) -> None:
    """Store final rankings snapshot in ranking_history table."""
    print("Storing final rankings snapshot...")

    # Use week 20 for final snapshot
    final_week = 20

    # Delete existing final snapshot if it exists
    db.query(RankingHistory).filter(
        RankingHistory.season == season,
        RankingHistory.week == final_week
    ).delete()

    # Calculate SOS ranks
    sorted_by_sos = sorted(rankings, key=lambda x: x["sos"], reverse=True)
    sos_ranks = {team["team_id"]: rank for rank, team in enumerate(sorted_by_sos, 1)}

    # Create final ranking history entries
    for team_data in rankings:
        history_entry = RankingHistory(
            team_id=team_data["team_id"],
            week=final_week,
            season=season,
            rank=team_data["rank"],
            elo_rating=team_data["elo_rating"],
            wins=team_data["wins"],
            losses=team_data["losses"],
            sos=team_data["sos"],
            sos_rank=sos_ranks.get(team_data["team_id"]),
        )
        db.add(history_entry)

    db.commit()
    print(f"✓ Stored final snapshot for week {final_week}")


def calculate_prediction_accuracy(db: Any, season: int) -> Dict[str, Any]:
    """Calculate overall prediction accuracy statistics."""
    print("Calculating prediction accuracy...")

    # Get all predictions for the season
    predictions = (
        db.query(Prediction)
        .join(Game, Prediction.game_id == Game.id)
        .filter(Game.season == season, Prediction.was_correct != None)
        .all()
    )

    if not predictions:
        print("⚠ No predictions found for accuracy calculation")
        return {}

    total = len(predictions)
    correct = sum(1 for p in predictions if p.was_correct)
    accuracy = correct / total if total > 0 else 0.0

    # Calculate by week
    predictions_by_week = {}
    for pred in predictions:
        week = pred.game.week
        if week not in predictions_by_week:
            predictions_by_week[week] = {"count": 0, "correct": 0}
        predictions_by_week[week]["count"] += 1
        if pred.was_correct:
            predictions_by_week[week]["correct"] += 1

    by_week = []
    for week in sorted(predictions_by_week.keys()):
        data = predictions_by_week[week]
        by_week.append({
            "week": week,
            "count": data["count"],
            "correct": data["correct"],
            "accuracy": data["correct"] / data["count"] if data["count"] > 0 else 0.0,
        })

    # Calculate regular season vs postseason
    regular_season = [p for p in predictions if p.game.week <= 15]
    postseason = [p for p in predictions if p.game.week > 15]

    rs_correct = sum(1 for p in regular_season if p.was_correct)
    ps_correct = sum(1 for p in postseason if p.was_correct)

    rs_accuracy = rs_correct / len(regular_season) if regular_season else 0.0
    ps_accuracy = ps_correct / len(postseason) if postseason else 0.0

    print(f"✓ Overall accuracy: {accuracy:.2%} ({correct}/{total})")

    return {
        "total_predictions": total,
        "correct_predictions": correct,
        "accuracy": accuracy,
        "by_week": by_week,
        "regular_season_accuracy": rs_accuracy,
        "postseason_accuracy": ps_accuracy,
        "regular_season_count": len(regular_season),
        "postseason_count": len(postseason),
    }


def calculate_ap_comparison(db: Any, season: int) -> Dict[str, Any]:
    """Calculate AP Poll comparison statistics."""
    print("Calculating AP Poll comparison...")

    try:
        comparison = calculate_comparison_stats(db, season)
        print(f"✓ ELO accuracy: {comparison.get('elo_accuracy', 0):.2%}, AP accuracy: {comparison.get('ap_accuracy', 0):.2%}")
        return comparison
    except Exception as e:
        print(f"⚠ Error calculating AP comparison: {e}")
        return {}


def calculate_conference_stats(db: Any, season: int, rankings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate conference-level performance metrics."""
    print("Calculating conference statistics...")

    # Group teams by conference
    conferences = {}
    for team_data in rankings:
        conf_name = team_data["conference"]
        if conf_name not in conferences:
            conferences[conf_name] = {
                "name": conf_name,
                "teams": [],
                "total_elo": 0.0,
                "top_25_count": 0,
                "total_wins": 0,
                "total_losses": 0,
            }

        conf = conferences[conf_name]
        conf["teams"].append(team_data)
        conf["total_elo"] += team_data["elo_rating"]
        conf["total_wins"] += team_data["wins"]
        conf["total_losses"] += team_data["losses"]

        if team_data["rank"] <= 25:
            conf["top_25_count"] += 1

    # Calculate averages and percentages
    conference_stats = []
    for conf_name, conf_data in conferences.items():
        team_count = len(conf_data["teams"])
        avg_elo = conf_data["total_elo"] / team_count if team_count > 0 else 0.0
        total_games = conf_data["total_wins"] + conf_data["total_losses"]
        win_pct = conf_data["total_wins"] / total_games if total_games > 0 else 0.0

        conference_stats.append({
            "name": conf_name,
            "team_count": team_count,
            "avg_elo": avg_elo,
            "top_25_count": conf_data["top_25_count"],
            "win_pct": win_pct,
            "total_wins": conf_data["total_wins"],
            "total_losses": conf_data["total_losses"],
        })

    # Sort by average ELO
    conference_stats.sort(key=lambda x: x["avg_elo"], reverse=True)

    print(f"✓ Calculated stats for {len(conference_stats)} conferences")
    return conference_stats


def identify_top_performers(db: Any, season: int, rankings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Identify top performers in various categories."""
    print("Identifying top performers...")

    top_performers = {}

    # Biggest risers (largest ELO gain from preseason)
    risers = []
    for team_data in rankings:
        elo_gain = team_data["elo_rating"] - team_data["initial_rating"]
        risers.append({
            "name": team_data["name"],
            "elo_gain": elo_gain,
            "initial_rating": team_data["initial_rating"],
            "final_rating": team_data["elo_rating"],
            "rank": team_data["rank"],
        })
    risers.sort(key=lambda x: x["elo_gain"], reverse=True)
    top_performers["biggest_risers"] = risers[:10]

    # Biggest fallers (largest ELO loss from preseason)
    fallers = sorted(risers, key=lambda x: x["elo_gain"])
    top_performers["biggest_fallers"] = fallers[:10]

    # Toughest schedule (highest SOS)
    by_sos = sorted(rankings, key=lambda x: x["sos"], reverse=True)
    top_performers["toughest_schedule"] = [
        {
            "name": t["name"],
            "sos": t["sos"],
            "wins": t["wins"],
            "losses": t["losses"],
            "rank": t["rank"],
        }
        for t in by_sos[:10]
    ]

    print("✓ Identified top performers")
    return top_performers


def main():
    """Main entry point for statistics calculation script."""
    parser = argparse.ArgumentParser(
        description="Calculate final season statistics and generate summary report"
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year to finalize (e.g., 2025)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for markdown summary (e.g., docs/season-2025-summary.md)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Finalizing Season {args.season} Statistics")
    print(f"{'='*60}\n")

    # Create database session
    db = SessionLocal()

    try:
        # Check if season exists
        season = db.query(Season).filter(Season.year == args.season).first()
        if not season:
            print(f"✗ Season {args.season} not found in database")
            sys.exit(1)

        # Create statistics collector
        stats = SeasonStatistics(args.season)

        # Calculate final rankings
        stats.final_rankings = calculate_final_rankings(db, args.season)

        # Store final snapshot in database
        store_final_snapshot(db, args.season, stats.final_rankings)

        # Calculate prediction accuracy
        stats.prediction_stats = calculate_prediction_accuracy(db, args.season)

        # Calculate AP Poll comparison
        stats.ap_comparison = calculate_ap_comparison(db, args.season)

        # Calculate conference statistics
        stats.conference_stats = calculate_conference_stats(db, args.season, stats.final_rankings)

        # Identify top performers
        stats.top_performers = identify_top_performers(db, args.season, stats.final_rankings)

        # Generate markdown summary
        markdown_summary = stats.to_markdown()

        # Save or print summary
        if args.output:
            with open(args.output, "w") as f:
                f.write(markdown_summary)
            print(f"\n✓ Season summary written to: {args.output}")
        else:
            print("\nSeason Summary:")
            print(markdown_summary)

        print(f"\n{'='*60}")
        print("Statistics Finalization Complete")
        print(f"{'='*60}\n")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error finalizing statistics: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
