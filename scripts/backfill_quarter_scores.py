"""
Backfill quarter scores for existing games from CFBD API

Usage:
    python scripts/backfill_quarter_scores.py [--dry-run] [--season YEAR] [--limit N]

Options:
    --dry-run: Preview changes without writing to database
    --season YEAR: Only backfill games from specific season
    --limit N: Limit to N games (for testing)
"""

import sys
import os
import time
import argparse
from typing import List, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from models import Game
from cfbd_client import CFBDClient
from database import SessionLocal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuarterScoreBackfiller:
    """Backfills quarter scores for existing games"""

    def __init__(self, db: Session, cfbd_client: CFBDClient, dry_run: bool = False):
        self.db = db
        self.cfbd_client = cfbd_client
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'backfilled': 0,
            'failed': 0,
            'unavailable': 0,
            'already_filled': 0
        }

    def get_games_needing_backfill(self, season: int = None, limit: int = None) -> List[Game]:
        """Fetch games with NULL quarter scores"""
        query = self.db.query(Game).filter(Game.q1_home.is_(None))

        if season:
            query = query.filter(Game.season == season)

        query = query.order_by(Game.season.desc(), Game.week.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def backfill_game(self, game: Game) -> bool:
        """
        Backfill quarter scores for a single game

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch quarter scores from CFBD API
            # Note: game_id parameter is for logging only; API uses year/week/team names to find the game
            line_scores = self.cfbd_client.get_game_line_scores(
                game_id=game.id,  # Local database ID (for logging purposes only)
                year=game.season,
                week=game.week,
                home_team=game.home_team.name,
                away_team=game.away_team.name
            )

            if line_scores is None:
                logger.debug(f"No line scores available for game {game.id}")
                self.stats['unavailable'] += 1
                return False

            # Update game with quarter scores
            game.q1_home = line_scores['home'][0]
            game.q1_away = line_scores['away'][0]
            game.q2_home = line_scores['home'][1]
            game.q2_away = line_scores['away'][1]
            game.q3_home = line_scores['home'][2]
            game.q3_away = line_scores['away'][2]
            game.q4_home = line_scores['home'][3]
            game.q4_away = line_scores['away'][3]

            # Validate quarter scores
            try:
                game.validate_quarter_scores()
            except ValueError as e:
                logger.warning(f"Validation failed for game {game.id}: {e}")
                # Reset quarters to NULL
                game.q1_home = game.q1_away = game.q2_home = game.q2_away = None
                game.q3_home = game.q3_away = game.q4_home = game.q4_away = None
                self.stats['failed'] += 1
                return False

            # Commit if not dry-run
            if not self.dry_run:
                self.db.commit()
                logger.info(f"Backfilled game {game.id}: {game.home_team.name} vs {game.away_team.name}")
            else:
                logger.info(f"[DRY RUN] Would backfill game {game.id}")

            self.stats['backfilled'] += 1
            return True

        except Exception as e:
            logger.error(f"Error backfilling game {game.id}: {e}")
            self.db.rollback()
            self.stats['failed'] += 1
            return False

    def run(self, season: int = None, limit: int = None, batch_size: int = 100):
        """
        Run backfill process

        Args:
            season: Optional season to filter
            limit: Optional limit on number of games
            batch_size: Commit after this many games (if not dry-run)
        """
        logger.info("Starting quarter score backfill...")
        if self.dry_run:
            logger.info("DRY RUN MODE - No changes will be saved")

        # Fetch games needing backfill
        games = self.get_games_needing_backfill(season, limit)
        self.stats['total'] = len(games)

        logger.info(f"Found {len(games)} games needing backfill")

        # Process in batches
        for i, game in enumerate(games, 1):
            logger.info(f"Processing game {i}/{len(games)}: Season {game.season}, Week {game.week}")

            # Backfill game
            self.backfill_game(game)

            # Rate limiting: Sleep between requests to respect CFBD API limits
            if i % 10 == 0:
                logger.info(f"Processed {i} games, sleeping 2s for rate limiting...")
                time.sleep(2)

            # Periodic commit (batch)
            if not self.dry_run and i % batch_size == 0:
                self.db.commit()
                logger.info(f"Committed batch {i // batch_size}")

        # Final commit
        if not self.dry_run:
            self.db.commit()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print backfill summary statistics"""
        logger.info("\n" + "="*60)
        logger.info("BACKFILL SUMMARY")
        logger.info("="*60)
        logger.info(f"Total games: {self.stats['total']}")
        logger.info(f"Backfilled: {self.stats['backfilled']}")
        logger.info(f"Already filled: {self.stats['already_filled']}")
        logger.info(f"Unavailable (no data): {self.stats['unavailable']}")
        logger.info(f"Failed (errors): {self.stats['failed']}")

        if self.stats['total'] > 0:
            success_rate = (self.stats['backfilled'] / self.stats['total']) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        logger.info("="*60 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Backfill quarter scores from CFBD API')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--season', type=int, help='Only backfill specific season')
    parser.add_argument('--limit', type=int, help='Limit number of games')

    args = parser.parse_args()

    # Initialize dependencies
    db = SessionLocal()
    cfbd_client = CFBDClient()

    try:
        backfiller = QuarterScoreBackfiller(db, cfbd_client, dry_run=args.dry_run)
        backfiller.run(season=args.season, limit=args.limit)
    finally:
        db.close()


if __name__ == '__main__':
    main()
