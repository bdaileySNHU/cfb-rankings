#!/usr/bin/env python3
"""
Test EPIC-024 refactored rankings
"""

from database import SessionLocal
from ranking_service import RankingService

def test_rankings():
    db = SessionLocal()
    ranking_service = RankingService(db)
    
    print("="*80)
    print("EPIC-024: Testing Season-Specific Rankings")
    print("="*80)
    print()
    
    # Test 2025 season rankings
    print("Testing 2025 Season Rankings (Week 8):")
    print("-" * 80)
    
    rankings_2025 = ranking_service.get_current_rankings(season=2025, limit=10)
    
    if rankings_2025:
        print(f"Found {len(rankings_2025)} teams")
        print()
        print(f"{'Rank':<6} {'Team':<30} {'Record':<12} {'ELO':<10} {'SOS':<10}")
        print("-" * 80)
        
        for team in rankings_2025:
            record = f"{team['wins']}-{team['losses']}"
            print(f"{team['rank']:<6} {team['team_name']:<30} {record:<12} "
                  f"{team['elo_rating']:<10.2f} {team['sos']:<10.2f}")
    else:
        print("❌ No rankings found for 2025!")
    
    print()
    print("="*80)
    print("✅ Test complete!")
    print("="*80)
    
    db.close()

if __name__ == "__main__":
    test_rankings()
