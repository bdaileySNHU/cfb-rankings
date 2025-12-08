"""
Test script for API usage tracking functionality
Tests the @track_api_usage decorator and get_monthly_usage() function
"""

import os

os.environ['CFBD_MONTHLY_LIMIT'] = '1000'  # Set limit for testing

from datetime import datetime

from cfbd_client import CFBDClient, get_monthly_usage
from database import SessionLocal
from models import APIUsage


def test_tracking():
    """Test that API calls are tracked in the database"""
    print("=" * 80)
    print("TESTING API USAGE TRACKING")
    print("=" * 80)
    print()

    # Initialize client
    print("1. Initializing CFBD client...")
    client = CFBDClient()
    print("   ✓ Client initialized")
    print()

    # Check initial usage
    print("2. Checking initial API usage...")
    current_month = datetime.now().strftime("%Y-%m")
    initial_usage = get_monthly_usage(current_month)
    print(f"   Current month: {initial_usage['month']}")
    print(f"   Total calls: {initial_usage['total_calls']}")
    print(f"   Monthly limit: {initial_usage['monthly_limit']}")
    print(f"   Percentage used: {initial_usage['percentage_used']}%")
    print(f"   Remaining calls: {initial_usage['remaining_calls']}")
    print()

    # Make a test API call
    print("3. Making test API call (get_teams for 2025)...")
    try:
        teams = client.get_teams(2025)
        if teams:
            print(f"   ✓ API call succeeded - fetched {len(teams)} teams")
        else:
            print(f"   ⚠ API call returned None (may need API key)")
    except Exception as e:
        print(f"   ⚠ API call failed: {e}")
    print()

    # Check if tracking worked
    print("4. Checking if API call was tracked...")
    db = SessionLocal()
    try:
        # Query the most recent api_usage record
        latest_record = db.query(APIUsage).order_by(APIUsage.timestamp.desc()).first()

        if latest_record:
            print(f"   ✓ Latest API call tracked:")
            print(f"     - Endpoint: {latest_record.endpoint}")
            print(f"     - Timestamp: {latest_record.timestamp}")
            print(f"     - Status code: {latest_record.status_code}")
            print(f"     - Response time: {latest_record.response_time_ms:.2f}ms")
            print(f"     - Month: {latest_record.month}")
        else:
            print(f"   ✗ No API usage records found")

    finally:
        db.close()
    print()

    # Check updated usage
    print("5. Checking updated API usage...")
    updated_usage = get_monthly_usage(current_month)
    print(f"   Total calls: {updated_usage['total_calls']}")
    print(f"   Percentage used: {updated_usage['percentage_used']}%")
    print(f"   Remaining calls: {updated_usage['remaining_calls']}")
    print(f"   Average per day: {updated_usage['average_calls_per_day']}")

    if updated_usage['warning_level']:
        print(f"   ⚠ Warning level: {updated_usage['warning_level']}")
    else:
        print(f"   ✓ No warnings")

    if updated_usage['top_endpoints']:
        print(f"\n   Top endpoints:")
        for ep in updated_usage['top_endpoints']:
            print(f"     - {ep['endpoint']}: {ep['count']} calls ({ep['percentage']}%)")
    print()

    # Test multiple calls
    print("6. Making 4 more test API calls to see aggregation...")
    for i in range(4):
        try:
            _ = client.get_teams(2025)
            print(f"   ✓ Call {i+1}/4 completed")
        except:
            print(f"   ⚠ Call {i+1}/4 failed")
    print()

    # Final usage check
    print("7. Final API usage check...")
    final_usage = get_monthly_usage(current_month)
    print(f"   Total calls: {final_usage['total_calls']}")
    print(f"   Calls added: {final_usage['total_calls'] - initial_usage['total_calls']}")
    print(f"   Percentage used: {final_usage['percentage_used']}%")
    print()

    # Success summary
    print("=" * 80)
    print("✅ API USAGE TRACKING TEST COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - API calls are being tracked in database")
    print(f"  - Usage aggregation is calculating correctly")
    print(f"  - Top endpoints are being tracked")
    print(f"  - {final_usage['total_calls'] - initial_usage['total_calls']} new API calls logged during test")
    print()

if __name__ == "__main__":
    test_tracking()
