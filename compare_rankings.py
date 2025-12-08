"""
Compare ELO Rankings with Official Polls
Shows how our model compares to AP Poll, Coaches Poll, and CFP Rankings
"""

import os

from cfbd_client import CFBDClient
from database import SessionLocal
from ranking_service import RankingService

# AP Poll Rankings (Week 5, 2024 - as reference)
AP_POLL_WEEK_5 = {
    'Texas': 1,
    'Georgia': 2,
    'Ohio State': 3,
    'Alabama': 4,
    'Ole Miss': 5,
    'Tennessee': 6,
    'Missouri': 7,
    'Miami': 8,
    'Oregon': 9,
    'Penn State': 10,
    'USC': 11,
    'Utah': 12,
    'Oklahoma State': 13,
    'Kansas State': 14,
    'Oklahoma': 15,
    'LSU': 16,
    'Louisville': 17,
    'Clemson': 18,
    'Notre Dame': 19,
    'Michigan': 20,
    'Iowa State': 21,
    'BYU': 22,
    'SMU': 23,
    'Illinois': 24,
    'Nebraska': 25
}


def compare_with_ap_poll():
    """Compare our ELO rankings with AP Poll"""
    db = SessionLocal()
    ranking_service = RankingService(db)

    print("="*100)
    print("ELO RANKINGS vs AP POLL COMPARISON (Week 5, 2024)")
    print("="*100)
    print()

    # Get our rankings
    elo_rankings = ranking_service.get_current_rankings(2024, limit=50)

    # Create lookup dictionaries
    elo_lookup = {r['team_name']: r['rank'] for r in elo_rankings}

    print(f"{'TEAM':<25} {'ELO RANK':<12} {'AP RANK':<12} {'DIFFERENCE':<15}")
    print("-"*100)

    # Track statistics
    exact_matches = 0
    within_5 = 0
    within_10 = 0
    total_compared = 0
    differences = []

    # Compare top 25 from AP Poll
    for team, ap_rank in sorted(AP_POLL_WEEK_5.items(), key=lambda x: x[1]):
        elo_rank = elo_lookup.get(team, None)

        if elo_rank:
            diff = elo_rank - ap_rank
            differences.append(abs(diff))
            total_compared += 1

            # Track accuracy
            if diff == 0:
                exact_matches += 1
                diff_str = "✓ EXACT MATCH"
            elif abs(diff) <= 5:
                within_5 += 1
                diff_str = f"{diff:+d} (Close)"
            elif abs(diff) <= 10:
                within_10 += 1
                diff_str = f"{diff:+d}"
            else:
                diff_str = f"{diff:+d} (Big diff)"

            print(f"{team:<25} #{elo_rank:<11} #{ap_rank:<11} {diff_str:<15}")
        else:
            print(f"{team:<25} {'NOT IN TOP 50':<11} #{ap_rank:<11} {'--':<15}")

    # Calculate statistics
    print()
    print("="*100)
    print("COMPARISON STATISTICS")
    print("="*100)
    print(f"Teams compared: {total_compared}/25")
    print(f"Exact matches: {exact_matches} ({exact_matches/total_compared*100:.1f}%)")
    print(f"Within 5 spots: {within_5} ({within_5/total_compared*100:.1f}%)")
    print(f"Within 10 spots: {within_10} ({within_10/total_compared*100:.1f}%)")
    print(f"Average difference: {sum(differences)/len(differences):.1f} positions")
    print()

    # Show biggest disagreements
    print("="*100)
    print("BIGGEST DISAGREEMENTS")
    print("="*100)

    disagreements = []
    for team, ap_rank in AP_POLL_WEEK_5.items():
        elo_rank = elo_lookup.get(team)
        if elo_rank:
            diff = abs(elo_rank - ap_rank)
            disagreements.append((team, elo_rank, ap_rank, diff))

    disagreements.sort(key=lambda x: x[3], reverse=True)

    print(f"\n{'TEAM':<25} {'ELO RANK':<12} {'AP RANK':<12} {'DIFF':<10}")
    print("-"*100)
    for team, elo_rank, ap_rank, diff in disagreements[:10]:
        direction = "↑" if elo_rank < ap_rank else "↓"
        print(f"{team:<25} #{elo_rank:<11} #{ap_rank:<11} {diff} {direction}")

    # Show ELO's unique picks (teams in our top 25 not in AP)
    print()
    print("="*100)
    print("ELO'S UNIQUE TOP 25 PICKS (Not in AP Poll)")
    print("="*100)

    ap_teams = set(AP_POLL_WEEK_5.keys())
    unique_picks = []

    for r in elo_rankings[:25]:
        if r['team_name'] not in ap_teams:
            unique_picks.append(r)

    if unique_picks:
        print(f"\n{'RANK':<8} {'TEAM':<25} {'RECORD':<10} {'ELO':<10} {'SOS':<10}")
        print("-"*100)
        for r in unique_picks:
            print(f"#{r['rank']:<7} {r['team_name']:<25} {r['wins']}-{r['losses']:<8} {r['elo_rating']:<10.2f} {r['sos']:<10.2f}")
    else:
        print("None - ELO's top 25 matches AP Poll teams")

    db.close()


def analyze_prediction_accuracy():
    """Analyze how well ELO predicted game outcomes"""
    db = SessionLocal()

    from models import Game, Team

    print()
    print("="*100)
    print("ELO PREDICTION ACCURACY ANALYSIS")
    print("="*100)
    print()

    games = db.query(Game).filter(Game.season == 2024, Game.is_processed == True).all()

    correct_predictions = 0
    total_games = len(games)
    upsets = []

    for game in games:
        home_team = game.home_team
        away_team = game.away_team

        # Get ratings before the game (approximate using current - change)
        home_rating_before = home_team.elo_rating - game.home_rating_change
        away_rating_before = away_team.elo_rating - game.away_rating_change

        # Add home field advantage
        home_rating_adj = home_rating_before + 65 if not game.is_neutral_site else home_rating_before

        # Predict winner (higher rating)
        predicted_winner = home_team if home_rating_adj > away_rating_before else away_team
        actual_winner = home_team if game.home_score > game.away_score else away_team

        if predicted_winner.id == actual_winner.id:
            correct_predictions += 1
        else:
            # It's an upset!
            favorite = predicted_winner.name
            underdog = actual_winner.name
            rating_diff = abs(home_rating_before - away_rating_before)
            score = f"{game.home_score}-{game.away_score}" if actual_winner.id == home_team.id else f"{game.away_score}-{game.home_score}"
            upsets.append((game.week, underdog, favorite, rating_diff, score))

    accuracy = (correct_predictions / total_games * 100) if total_games > 0 else 0

    print(f"Total games analyzed: {total_games}")
    print(f"Correct predictions: {correct_predictions}")
    print(f"Prediction accuracy: {accuracy:.1f}%")
    print()

    # Show biggest upsets
    if upsets:
        print("="*100)
        print("BIGGEST UPSETS (ELO's Surprises)")
        print("="*100)
        print(f"\n{'WEEK':<8} {'WINNER':<20} {'OVER':<20} {'RATING DIFF':<15} {'SCORE':<10}")
        print("-"*100)

        upsets.sort(key=lambda x: x[3], reverse=True)
        for week, winner, loser, diff, score in upsets[:15]:
            print(f"Week {week:<3} {winner:<20} {loser:<20} {diff:<15.1f} {score:<10}")

    db.close()


def show_elo_insights():
    """Show interesting ELO insights"""
    db = SessionLocal()
    ranking_service = RankingService(db)

    print()
    print("="*100)
    print("ELO INSIGHTS & ANALYSIS")
    print("="*100)

    rankings = ranking_service.get_current_rankings(2024, limit=50)

    # Find teams that gained/lost most rating
    print("\nBIGGEST RATING CHANGES FROM PRESEASON:")
    print("-"*100)

    from models import Team
    teams = db.query(Team).all()
    changes = [(t.name, t.elo_rating - t.initial_rating, f"{t.wins}-{t.losses}", t.conference.value)
               for t in teams if t.wins + t.losses > 0]

    print("\nBIGGEST GAINERS:")
    changes.sort(key=lambda x: x[1], reverse=True)
    for i, (name, change, record, conf) in enumerate(changes[:10], 1):
        print(f"{i}. {name:<25} {change:+.1f} pts  ({record}, {conf})")

    print("\nBIGGEST DECLINERS:")
    changes.sort(key=lambda x: x[1])
    for i, (name, change, record, conf) in enumerate(changes[:10], 1):
        print(f"{i}. {name:<25} {change:+.1f} pts  ({record}, {conf})")

    # Quality wins/losses
    print()
    print("="*100)
    print("STRENGTH OF SCHEDULE LEADERS (Toughest Schedules)")
    print("="*100)

    sos_leaders = sorted(rankings, key=lambda x: x['sos'], reverse=True)[:10]
    for i, r in enumerate(sos_leaders, 1):
        print(f"{i}. {r['team_name']:<25} SOS: {r['sos']:.1f}  (Rank #{r['rank']}, {r['wins']}-{r['losses']})")

    db.close()


def main():
    """Run all comparisons"""
    print("\n")
    print("█" * 100)
    print("█" + " " * 98 + "█")
    print("█" + "  COLLEGE FOOTBALL ELO RANKINGS - MODEL EVALUATION  ".center(98) + "█")
    print("█" + " " * 98 + "█")
    print("█" * 100)
    print()

    # 1. Compare with AP Poll
    compare_with_ap_poll()

    # 2. Prediction accuracy
    analyze_prediction_accuracy()

    # 3. ELO insights
    show_elo_insights()

    print()
    print("="*100)
    print("CONCLUSIONS")
    print("="*100)
    print("""
The Modified ELO system provides:
1. Objective, math-based rankings
2. Rewards strength of schedule
3. Accounts for margin of victory (capped to prevent running up score)
4. Considers quality of wins/losses
5. Incorporates preseason talent via recruiting

Differences from AP Poll often reveal:
- Overrated teams (high AP rank, weak schedule)
- Underrated teams (strong ELO, tough schedule)
- Quality losses (teams penalized less for losing to strong opponents)
    """)
    print("="*100)
    print()


if __name__ == "__main__":
    main()
