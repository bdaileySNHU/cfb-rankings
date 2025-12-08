#!/usr/bin/env python3
"""Test script to verify returning production import - EPIC-025 Story 25.3"""

from src.models.database import SessionLocal
from src.models.models import Team

db = SessionLocal()

# Check specific teams
teams_to_check = ['Ohio State', 'Georgia', 'App State', "Hawai'i", 'Alabama']

print('Database Verification:')
print('=' * 60)
for team_name in teams_to_check:
    team = db.query(Team).filter(Team.name == team_name).first()
    if team:
        print(f'{team_name:20} | Returning: {team.returning_production*100:.1f}% | Recruiting: #{team.recruiting_rank}')
    else:
        print(f'{team_name:20} | NOT FOUND')

# Count teams with non-default values
non_default = db.query(Team).filter(Team.returning_production != 0.5).count()
total = db.query(Team).count()

print('=' * 60)
print(f'Teams with non-default returning production: {non_default}/{total}')
print(f'Success rate: {non_default/total*100:.1f}%')

# Show distribution
print('\n' + '=' * 60)
print('Distribution of Returning Production:')
print('=' * 60)
teams = db.query(Team).order_by(Team.returning_production.desc()).limit(10).all()
print('\nTop 10 Highest Returning Production:')
for i, team in enumerate(teams, 1):
    print(f'{i:2}. {team.name:25} {team.returning_production*100:.1f}%')

teams = db.query(Team).order_by(Team.returning_production.asc()).limit(10).all()
print('\nTop 10 Lowest Returning Production:')
for i, team in enumerate(teams, 1):
    print(f'{i:2}. {team.name:25} {team.returning_production*100:.1f}%')

db.close()
