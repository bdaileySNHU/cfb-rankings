#!/usr/bin/env python3
"""
Verify conference championship games are processed correctly in rankings
For Story 22.3 acceptance criteria verification
"""

import sys

from database import SessionLocal
from models import Game, RankingHistory, Team


def verify_championship_processing(team_id, season=2024):
    """
    Verify a team's conference championship game was processed correctly
    """

    db = SessionLocal()

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        print(f"Team ID {team_id} not found")
        return 1

    print("="*80)
    print(f"CHAMPIONSHIP PROCESSING VERIFICATION: {team.name} - {season}")
    print("="*80)
    print()

    # Find their conference championship game
    conf_champ_game = db.query(Game).filter(
        ((Game.home_team_id == team_id) | (Game.away_team_id == team_id)),
        Game.season == season,
        Game.game_type == 'conference_championship'
    ).first()

    if not conf_champ_game:
        print(f"⚠️  No conference championship game found for {team.name} in {season}")
        print()
        db.close()
        return 1

    print("Conference Championship Game:")
    print(f"  Week: {conf_champ_game.week}")
    print(f"  Matchup: {conf_champ_game.away_team.name} @ {conf_champ_game.home_team.name}")
    print(f"  Score: {conf_champ_game.away_score}-{conf_champ_game.home_score}")
    print(f"  Processed: {conf_champ_game.is_processed}")
    print()

    # Determine if team won
    is_home = conf_champ_game.home_team_id == team_id
    if is_home:
        won = conf_champ_game.home_score > conf_champ_game.away_score
        team_score = conf_champ_game.home_score
        opp_score = conf_champ_game.away_score
        rating_change = conf_champ_game.home_rating_change
    else:
        won = conf_champ_game.away_score > conf_champ_game.home_score
        team_score = conf_champ_game.away_score
        opp_score = conf_champ_game.home_score
        rating_change = conf_champ_game.away_rating_change

    result = "Won" if won else "Lost"
    print(f"  Result: {result} ({team_score}-{opp_score})")
    print(f"  ELO Change: {rating_change:+.2f}")
    print()

    # Get ranking history for championship week
    champ_week = conf_champ_game.week

    # Get ranking before championship (previous week)
    before_ranking = db.query(RankingHistory).filter(
        RankingHistory.team_id == team_id,
        RankingHistory.season == season,
        RankingHistory.week == champ_week - 1
    ).first()

    # Get ranking after championship
    after_ranking = db.query(RankingHistory).filter(
        RankingHistory.team_id == team_id,
        RankingHistory.season == season,
        RankingHistory.week == champ_week
    ).first()

    print("ELO Rating Changes:")
    if before_ranking:
        print(f"  Before (Week {champ_week - 1}): {before_ranking.elo_rating:.2f}")
        print(f"    Record: {before_ranking.wins}-{before_ranking.losses}")
    else:
        print(f"  Before (Week {champ_week - 1}): No data")

    if after_ranking:
        print(f"  After (Week {champ_week}): {after_ranking.elo_rating:.2f}")
        print(f"    Record: {after_ranking.wins}-{after_ranking.losses}")

        if before_ranking:
            elo_diff = after_ranking.elo_rating - before_ranking.elo_rating
            wins_diff = after_ranking.wins - before_ranking.wins
            losses_diff = after_ranking.losses - before_ranking.losses

            print()
            print(f"  ELO Change: {elo_diff:+.2f}")
            print(f"  Record Change: +{wins_diff} wins, +{losses_diff} losses")
    else:
        print(f"  After (Week {champ_week}): No data")

    print()

    # Verification checks
    print("="*80)
    print("VERIFICATION CHECKS")
    print("="*80)
    print()

    checks_passed = 0
    checks_total = 0

    # Check 1: Game is processed
    checks_total += 1
    if conf_champ_game.is_processed:
        print("✓ Championship game is marked as processed")
        checks_passed += 1
    else:
        print("✗ Championship game is NOT processed")

    # Check 2: Rating change recorded
    checks_total += 1
    if rating_change != 0:
        print(f"✓ ELO rating change recorded: {rating_change:+.2f}")
        checks_passed += 1
    else:
        print("✗ ELO rating change is 0 (unexpected)")

    # Check 3: Ranking history updated
    checks_total += 1
    if after_ranking:
        print(f"✓ Ranking history saved for Week {champ_week}")
        checks_passed += 1
    else:
        print(f"✗ No ranking history for Week {champ_week}")

    # Check 4: Win/loss record updated
    checks_total += 1
    if after_ranking and before_ranking:
        if won:
            expected_wins = before_ranking.wins + 1
            if after_ranking.wins == expected_wins:
                print(f"✓ Win count increased: {before_ranking.wins} → {after_ranking.wins}")
                checks_passed += 1
            else:
                print(f"✗ Win count incorrect: expected {expected_wins}, got {after_ranking.wins}")
        else:
            expected_losses = before_ranking.losses + 1
            if after_ranking.losses == expected_losses:
                print(f"✓ Loss count increased: {before_ranking.losses} → {after_ranking.losses}")
                checks_passed += 1
            else:
                print(f"✗ Loss count incorrect: expected {expected_losses}, got {after_ranking.losses}")
    else:
        print("✗ Cannot verify record update (missing ranking history)")

    print()
    print(f"Checks Passed: {checks_passed}/{checks_total}")
    print()

    db.close()

    return 0 if checks_passed == checks_total else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_championship_processing.py <team_id> [season]")
        print()
        print("Examples:")
        print("  python verify_championship_processing.py 87 2024  (Oregon)")
        print("  python verify_championship_processing.py 107 2024 (Texas)")
        sys.exit(1)

    team_id = int(sys.argv[1])
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 2024

    sys.exit(verify_championship_processing(team_id, season))
