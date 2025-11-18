"""
Generate before/after ranking comparison report for quarter-weighted ELO

Usage:
    python scripts/generate_ranking_comparison_report.py --season YEAR --output report.md
"""

import sys
import os
import argparse
from typing import List, Tuple, Dict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from models import Team, RankingHistory, Game
from ranking_service import RankingService
from database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RankingComparisonReport:
    """Generates before/after ranking comparison"""

    def __init__(self, db: Session):
        self.db = db
        self.ranking_service = RankingService(db)

    def capture_current_rankings(self, season: int) -> List[Tuple[int, str, float]]:
        """Capture current rankings for a season"""
        teams = self.db.query(Team).order_by(Team.elo_rating.desc()).all()
        return [(i+1, team.name, team.elo_rating) for i, team in enumerate(teams)]

    def recalculate_rankings_from_scratch(self, season: int):
        """Recalculate all rankings for a season"""
        logger.info(f"Recalculating rankings for {season} season...")

        # Reset all team ratings to preseason
        teams = self.db.query(Team).all()
        for team in teams:
            self.ranking_service.initialize_team_rating(team)

        # Process all games in order
        games = (self.db.query(Game)
                 .filter(Game.season == season)
                 .order_by(Game.week, Game.game_date)
                 .all())

        for game in games:
            if not game.excluded_from_rankings:
                self.ranking_service.process_game(game)
                logger.debug(f"Processed: {game.home_team.name} vs {game.away_team.name}")

        self.db.commit()
        logger.info(f"Recalculation complete: {len(games)} games processed")

    def generate_comparison_report(self,
                                   before: List[Tuple[int, str, float]],
                                   after: List[Tuple[int, str, float]],
                                   output_file: str):
        """Generate markdown comparison report"""
        # Create rank change dict
        before_ranks = {name: rank for rank, name, _ in before}
        after_ranks = {name: rank for rank, name, _ in after}

        # Generate report
        with open(output_file, 'w') as f:
            f.write(f"# Quarter-Weighted ELO Ranking Comparison Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"This report compares rankings before and after implementing quarter-weighted ELO with garbage time adjustment.\n\n")

            # Top 25 comparison
            f.write(f"## Top 25 Ranking Changes\n\n")
            f.write("| Rank (After) | Team | Rank (Before) | Change | Rating (After) |\n")
            f.write("|--------------|------|---------------|--------|----------------|\n")

            for rank, team, rating in after[:25]:
                before_rank = before_ranks.get(team, 'NR')
                if before_rank != 'NR':
                    change = before_rank - rank
                    change_str = f"+{change}" if change > 0 else str(change)
                else:
                    change_str = "NEW"

                f.write(f"| {rank} | {team} | {before_rank} | {change_str} | {rating:.2f} |\n")

            # Biggest movers
            f.write(f"\n## Biggest Movers\n\n")
            f.write("Teams with largest ranking changes:\n\n")

            movers = []
            for team in set([name for _, name, _ in before] + [name for _, name, _ in after]):
                before_rank = before_ranks.get(team, 999)
                after_rank = after_ranks.get(team, 999)
                if before_rank != 999 and after_rank != 999:
                    change = before_rank - after_rank
                    movers.append((team, before_rank, after_rank, change))

            movers.sort(key=lambda x: abs(x[3]), reverse=True)

            f.write("| Team | Before | After | Change |\n")
            f.write("|------|--------|-------|--------|\n")

            for team, before, after, change in movers[:20]:
                change_str = f"+{change}" if change > 0 else str(change)
                f.write(f"| {team} | {before} | {after} | {change_str} |\n")

            # Analysis section
            f.write(f"\n## Analysis\n\n")
            f.write("### Algorithm Impact\n\n")
            f.write(f"- Teams that benefited most (moved up): Likely teams with competitive games\n")
            f.write(f"- Teams that dropped (moved down): Likely teams with garbage time inflation\n")
            f.write(f"- Minimal movement: Teams with close games throughout\n\n")

            # Garbage time examples
            f.write("### Garbage Time Detection Examples\n\n")
            f.write("Games where 4th quarter received reduced weight:\n\n")

            # Query games with large Q3 differential
            games_with_garbage_time = (
                self.db.query(Game)
                .filter(Game.q1_home.isnot(None))
                .all()
            )

            garbage_time_games = []
            for game in games_with_garbage_time:
                q3_home = (game.q1_home or 0) + (game.q2_home or 0) + (game.q3_home or 0)
                q3_away = (game.q1_away or 0) + (game.q2_away or 0) + (game.q3_away or 0)
                diff = abs(q3_home - q3_away)

                if diff > 21:  # Garbage time threshold
                    garbage_time_games.append((
                        game.home_team.name,
                        game.away_team.name,
                        f"{game.home_score}-{game.away_score}",
                        diff
                    ))

            if garbage_time_games:
                f.write("| Home Team | Away Team | Final Score | Diff after Q3 |\n")
                f.write("|-----------|-----------|-------------|---------------|\n")

                for home, away, score, diff in garbage_time_games[:10]:
                    f.write(f"| {home} | {away} | {score} | {diff} |\n")
            else:
                f.write("No games detected with garbage time adjustment.\n")

        logger.info(f"Report written to {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate ranking comparison report')
    parser.add_argument('--season', type=int, required=True, help='Season year')
    parser.add_argument('--output', type=str, default='ranking_comparison.md', help='Output file')

    args = parser.parse_args()

    db = SessionLocal()

    try:
        report_gen = RankingComparisonReport(db)

        # Capture current (before) rankings
        logger.info("Capturing current rankings...")
        before = report_gen.capture_current_rankings(args.season)

        # Recalculate rankings (after)
        logger.info("Recalculating rankings with quarter-weighted algorithm...")
        report_gen.recalculate_rankings_from_scratch(args.season)

        # Capture new (after) rankings
        logger.info("Capturing new rankings...")
        after = report_gen.capture_current_rankings(args.season)

        # Generate report
        logger.info("Generating comparison report...")
        report_gen.generate_comparison_report(before, after, args.output)

        logger.info(f"Report complete: {args.output}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
