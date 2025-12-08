"""
Demo script for College Football ELO Ranking System
Tests the algorithm with sample teams and games
"""

from cfb_elo_ranking import Conference, ELORankingSystem, Team


def create_sample_teams() -> ELORankingSystem:
    """Create a ranking system with sample teams"""
    system = ELORankingSystem()

    # Elite P5 teams with strong recruiting
    system.add_team(Team(
        name="Georgia",
        conference=Conference.POWER_5,
        recruiting_rank=3,
        transfer_rank=5,
        returning_production=0.70
    ))

    system.add_team(Team(
        name="Alabama",
        conference=Conference.POWER_5,
        recruiting_rank=5,
        transfer_rank=8,
        returning_production=0.65
    ))

    system.add_team(Team(
        name="Ohio State",
        conference=Conference.POWER_5,
        recruiting_rank=2,
        transfer_rank=3,
        returning_production=0.60
    ))

    system.add_team(Team(
        name="Texas",
        conference=Conference.POWER_5,
        recruiting_rank=8,
        transfer_rank=12,
        returning_production=0.75
    ))

    # Mid-tier P5 teams
    system.add_team(Team(
        name="Wisconsin",
        conference=Conference.POWER_5,
        recruiting_rank=35,
        transfer_rank=40,
        returning_production=0.72
    ))

    system.add_team(Team(
        name="Iowa",
        conference=Conference.POWER_5,
        recruiting_rank=45,
        transfer_rank=55,
        returning_production=0.80
    ))

    system.add_team(Team(
        name="Michigan State",
        conference=Conference.POWER_5,
        recruiting_rank=50,
        transfer_rank=48,
        returning_production=0.55
    ))

    # Strong G5 teams
    system.add_team(Team(
        name="Boise State",
        conference=Conference.GROUP_5,
        recruiting_rank=85,
        transfer_rank=65,
        returning_production=0.82
    ))

    system.add_team(Team(
        name="Memphis",
        conference=Conference.GROUP_5,
        recruiting_rank=90,
        transfer_rank=75,
        returning_production=0.68
    ))

    # Average G5 teams
    system.add_team(Team(
        name="Toledo",
        conference=Conference.GROUP_5,
        recruiting_rank=110,
        transfer_rank=95,
        returning_production=0.70
    ))

    system.add_team(Team(
        name="UTSA",
        conference=Conference.GROUP_5,
        recruiting_rank=105,
        transfer_rank=88,
        returning_production=0.65
    ))

    # FCS team
    system.add_team(Team(
        name="North Dakota State",
        conference=Conference.FCS,
        recruiting_rank=999,  # Not tracked
        transfer_rank=999,
        returning_production=0.85
    ))

    return system


def run_sample_season(system: ELORankingSystem):
    """Simulate a sample season with various game scenarios"""

    print("\n" + "="*100)
    print("PRESEASON RANKINGS (Based on Recruiting, Transfers, Returning Production)")
    print("="*100)
    system.print_rankings(top_n=12)

    print("\n" + "="*100)
    print("WEEK 1 GAMES")
    print("="*100)

    # Week 1: Mixed matchups
    games = [
        # Elite vs Mid-tier P5
        ("Georgia", "Wisconsin", 42, 10, True, False),
        ("Ohio State", "Iowa", 35, 7, True, False),

        # P5 vs G5
        ("Alabama", "Memphis", 28, 14, True, False),
        ("Texas", "UTSA", 38, 17, False, True),

        # P5 vs FCS
        ("Michigan State", "North Dakota State", 17, 21, True, False),  # FCS upset!

        # G5 matchup
        ("Boise State", "Toledo", 31, 20, True, False),
    ]

    for winner, loser, w_score, l_score, home_winner, neutral in games:
        result = system.process_game(winner, loser, w_score, l_score, home_winner, neutral)
        location = "Neutral" if neutral else ("Home" if home_winner else "Away")
        print(f"\n{result['winner']} defeats {result['loser']} {result['score']} ({location})")
        print(f"  Expected win prob: {result['winner_expected']*100:.1f}%")
        print(f"  MOV multiplier: {result['mov_multiplier']}")
        print(f"  {result['winner']}: {result['winner_rating_change']:+.2f} -> {result['winner_new_rating']}")
        print(f"  {result['loser']}: {result['loser_rating_change']:+.2f} -> {result['loser_new_rating']}")

    print("\n" + "="*100)
    print("RANKINGS AFTER WEEK 1")
    print("="*100)
    system.print_rankings(top_n=12)

    print("\n" + "="*100)
    print("WEEK 2 GAMES")
    print("="*100)

    # Week 2: Top teams face each other
    games = [
        # Elite matchup
        ("Georgia", "Alabama", 27, 24, False, True),  # Close game, neutral site

        # Ranked matchup
        ("Ohio State", "Texas", 31, 28, True, False),

        # Mid-tier games
        ("Wisconsin", "Michigan State", 24, 21, True, False),
        ("Iowa", "UTSA", 20, 17, True, False),

        # G5 games
        ("Memphis", "Toledo", 35, 21, True, False),
        ("North Dakota State", "Boise State", 14, 28, False, False),
    ]

    for winner, loser, w_score, l_score, home_winner, neutral in games:
        result = system.process_game(winner, loser, w_score, l_score, home_winner, neutral)
        location = "Neutral" if neutral else ("Home" if home_winner else "Away")
        print(f"\n{result['winner']} defeats {result['loser']} {result['score']} ({location})")
        print(f"  Expected win prob: {result['winner_expected']*100:.1f}%")
        print(f"  MOV multiplier: {result['mov_multiplier']}")
        print(f"  {result['winner']}: {result['winner_rating_change']:+.2f} -> {result['winner_new_rating']}")
        print(f"  {result['loser']}: {result['loser_rating_change']:+.2f} -> {result['loser_new_rating']}")

    print("\n" + "="*100)
    print("FINAL RANKINGS AFTER WEEK 2")
    print("="*100)
    system.print_rankings(top_n=12)

    # Show detailed stats for top 3 teams
    print("\n" + "="*100)
    print("DETAILED STATS FOR TOP 3 TEAMS")
    print("="*100)

    rankings = system.get_rankings()
    for rank, team, sos in rankings[:3]:
        opponents = ", ".join(team.games_played)
        print(f"\n#{rank} {team.name}")
        print(f"  ELO Rating: {team.elo_rating:.2f}")
        print(f"  Record: {team.get_record()}")
        print(f"  Conference: {team.conference.value}")
        print(f"  Strength of Schedule: {sos:.2f}")
        print(f"  Opponents: {opponents}")
        print(f"  Preseason Factors:")
        print(f"    - Recruiting Rank: {team.recruiting_rank}")
        print(f"    - Transfer Rank: {team.transfer_rank}")
        print(f"    - Returning Production: {team.returning_production*100:.0f}%")


def main():
    """Run the demo"""
    print("\n" + "="*100)
    print("COLLEGE FOOTBALL MODIFIED ELO RANKING SYSTEM - PROTOTYPE DEMO")
    print("="*100)

    system = create_sample_teams()
    run_sample_season(system)

    print("\n" + "="*100)
    print("DEMO COMPLETE")
    print("="*100)
    print("\nKey Features Demonstrated:")
    print("  ✓ Preseason ratings based on recruiting, transfers, and returning production")
    print("  ✓ Home field advantage (+65 points)")
    print("  ✓ Margin of victory multiplier (capped at 2.5)")
    print("  ✓ Conference-based multipliers (P5 vs G5, FBS vs FCS)")
    print("  ✓ Real-time rating updates after each game")
    print("  ✓ Strength of Schedule calculations")
    print("  ✓ Upset handling (NDSU over Michigan State)")
    print("  ✓ Neutral site game support")
    print("\n")


if __name__ == "__main__":
    main()
