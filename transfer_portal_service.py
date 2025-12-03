"""
Transfer Portal Ranking Service

EPIC-026: Calculate team transfer portal rankings from player-level transfer data

Algorithm:
- Use star-based scoring system (stars have 88.7% coverage vs 54.8% for ratings)
- Assign points based on star rating: 5★=100, 4★=80, 3★=60, 2★=40, 1★=20
- Sum points for all incoming transfers per team
- Rank teams by total points (highest = #1)

Author: EPIC-026 Story 26.3
Date: 2025-12-02
"""

from typing import Dict, List, Tuple
from collections import defaultdict


class TransferPortalService:
    """Service for calculating transfer portal team rankings"""

    # Star rating to points mapping
    STAR_POINTS = {
        5: 100,  # 5-star transfer
        4: 80,   # 4-star transfer
        3: 60,   # 3-star transfer
        2: 40,   # 2-star transfer
        1: 20,   # 1-star transfer
        None: 20  # Unrated transfer (default to 1-star equivalent)
    }

    def calculate_team_scores(self, transfers: List[Dict]) -> Dict[str, Dict]:
        """
        Calculate transfer portal scores for all teams

        Args:
            transfers: List of transfer dicts from CFBD API

        Returns:
            Dict mapping team name to score data:
            {
                'Colorado': {
                    'points': 2560,
                    'count': 41,
                    'stars_breakdown': {5: 0, 4: 5, 3: 36, 2: 0, 1: 0}
                }
            }
        """
        team_data = defaultdict(lambda: {
            'points': 0,
            'count': 0,
            'stars_breakdown': {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        })

        for transfer in transfers:
            # Only count transfers with confirmed destinations
            destination = transfer.get('destination')
            if not destination:
                continue

            # Get star rating (default to 1 if missing)
            stars = transfer.get('stars', 1)

            # Calculate points for this transfer
            points = self.STAR_POINTS.get(stars, 20)

            # Update team totals
            team_data[destination]['points'] += points
            team_data[destination]['count'] += 1

            # Track star rating distribution
            if stars in team_data[destination]['stars_breakdown']:
                team_data[destination]['stars_breakdown'][stars] += 1

        return dict(team_data)

    def rank_teams(self, team_scores: Dict[str, Dict]) -> Dict[str, int]:
        """
        Rank teams based on transfer portal points

        Args:
            team_scores: Dict from calculate_team_scores()

        Returns:
            Dict mapping team name to rank (1 = best):
            {'Colorado': 1, 'Indiana': 15, ...}

        Tiebreaker: Teams with same points ranked by transfer count (more = better)
        """
        if not team_scores:
            return {}

        # Sort teams by points (desc), then by count (desc) as tiebreaker
        sorted_teams = sorted(
            team_scores.items(),
            key=lambda x: (x[1]['points'], x[1]['count']),
            reverse=True
        )

        # Assign ranks
        rankings = {}
        for rank, (team, _) in enumerate(sorted_teams, start=1):
            rankings[team] = rank

        return rankings

    def get_team_stats(
        self,
        transfers: List[Dict]
    ) -> Tuple[Dict[str, Dict], Dict[str, int]]:
        """
        Convenience method to calculate both scores and rankings

        Args:
            transfers: List of transfer dicts from CFBD API

        Returns:
            Tuple of (team_scores, team_rankings)
        """
        team_scores = self.calculate_team_scores(transfers)
        team_rankings = self.rank_teams(team_scores)
        return team_scores, team_rankings

    def get_top_teams(
        self,
        transfers: List[Dict],
        limit: int = 25
    ) -> List[Tuple[str, int, int, int]]:
        """
        Get top N teams by transfer portal ranking

        Args:
            transfers: List of transfer dicts from CFBD API
            limit: Number of top teams to return (default 25)

        Returns:
            List of (team_name, rank, points, transfer_count) tuples
            Example: [('Colorado', 1, 2560, 41), ...]
        """
        team_scores, team_rankings = self.get_team_stats(transfers)

        # Create list of (team, rank, points, count)
        team_list = [
            (
                team,
                team_rankings[team],
                team_scores[team]['points'],
                team_scores[team]['count']
            )
            for team in team_rankings
        ]

        # Sort by rank and return top N
        team_list.sort(key=lambda x: x[1])
        return team_list[:limit]


# Example usage (for testing)
if __name__ == "__main__":
    from cfbd_client import CFBDClient

    print("Testing Transfer Portal Service...")
    print("=" * 60)

    # Fetch transfer data
    cfbd = CFBDClient()
    transfers = cfbd.get_transfer_portal(2024)
    print(f"✅ Fetched {len(transfers)} transfers")

    # Calculate scores and rankings
    service = TransferPortalService()
    team_scores, team_rankings = service.get_team_stats(transfers)
    print(f"✅ Calculated scores for {len(team_scores)} teams")

    # Display top 10
    print("\n" + "=" * 60)
    print("Top 10 Transfer Portal Teams (2024)")
    print("=" * 60)
    print(f"{'Rank':<6} {'Team':<25} {'Points':<8} {'Transfers':<10}")
    print("-" * 60)

    top_teams = service.get_top_teams(transfers, limit=10)
    for team, rank, points, count in top_teams:
        print(f"{rank:<6} {team:<25} {points:<8} {count:<10}")

    # Show example breakdown
    print("\n" + "=" * 60)
    print("Example: Colorado Transfer Breakdown")
    print("=" * 60)
    if 'Colorado' in team_scores:
        colorado = team_scores['Colorado']
        print(f"Total Points: {colorado['points']}")
        print(f"Total Transfers: {colorado['count']}")
        print(f"Star Breakdown:")
        for stars in [5, 4, 3, 2, 1]:
            count = colorado['stars_breakdown'][stars]
            points = count * TransferPortalService.STAR_POINTS[stars]
            print(f"  {stars}★: {count} transfers × {TransferPortalService.STAR_POINTS[stars]} pts = {points} pts")
