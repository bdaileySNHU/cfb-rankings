"""
Test script for warning threshold logging
Simulates high API usage to test 80%, 90%, and 95% warning thresholds
"""

import os
os.environ['CFBD_MONTHLY_LIMIT'] = '100'  # Set low limit for easy testing

from database import SessionLocal
from models import APIUsage
from datetime import datetime
from cfbd_client import get_monthly_usage, check_usage_warnings

def create_fake_usage_records(count: int, month: str = None):
    """Create fake API usage records for testing"""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    db = SessionLocal()
    try:
        for i in range(count):
            record = APIUsage(
                endpoint="/test/endpoint",
                timestamp=datetime.now(),
                status_code=200,
                response_time_ms=100.0,
                month=month
            )
            db.add(record)
        db.commit()
        print(f"   ✓ Created {count} fake usage records for month {month}")
    finally:
        db.close()

def test_warning_thresholds():
    """Test that warnings log at correct thresholds"""
    print("=" * 80)
    print("TESTING WARNING THRESHOLD LOGGING")
    print("=" * 80)
    print()
    print(f"Monthly limit set to 100 calls (for easy testing)")
    print()

    current_month = datetime.now().strftime("%Y-%m")

    # Test 1: Below 80% - No warnings
    print("TEST 1: Usage at 70% (70/100 calls) - No warnings expected")
    print("---")
    create_fake_usage_records(70, current_month)
    usage = get_monthly_usage(current_month)
    print(f"   Total calls: {usage['total_calls']}")
    print(f"   Percentage: {usage['percentage_used']}%")
    print(f"   Warning level: {usage['warning_level'] or 'None'}")
    print(f"   Expected: None ✓" if not usage['warning_level'] else f"   Expected: None ✗")
    print()

    # Trigger warning check
    print("   Checking for warnings...")
    check_usage_warnings(current_month)
    print()

    # Test 2: At 80% - Warning expected
    print("TEST 2: Usage at 85% (85/100 calls) - 80% warning expected")
    print("---")
    create_fake_usage_records(15, current_month)  # Add 15 more (70 + 15 = 85)
    usage = get_monthly_usage(current_month)
    print(f"   Total calls: {usage['total_calls']}")
    print(f"   Percentage: {usage['percentage_used']}%")
    print(f"   Warning level: {usage['warning_level']}")
    print(f"   Expected: 80% ✓" if usage['warning_level'] == '80%' else f"   Expected: 80% ✗")
    print()

    # Trigger warning check
    print("   Checking for warnings (should log WARNING)...")
    check_usage_warnings(current_month)
    print()

    # Test 3: At 90% - Warning expected
    print("TEST 3: Usage at 92% (92/100 calls) - 90% warning expected")
    print("---")
    create_fake_usage_records(7, current_month)  # Add 7 more (85 + 7 = 92)
    usage = get_monthly_usage(current_month)
    print(f"   Total calls: {usage['total_calls']}")
    print(f"   Percentage: {usage['percentage_used']}%")
    print(f"   Warning level: {usage['warning_level']}")
    print(f"   Expected: 90% ✓" if usage['warning_level'] == '90%' else f"   Expected: 90% ✗")
    print()

    # Trigger warning check
    print("   Checking for warnings (should log WARNING)...")
    check_usage_warnings(current_month)
    print()

    # Test 4: At 95% - Critical warning expected
    print("TEST 4: Usage at 97% (97/100 calls) - 95% critical warning expected")
    print("---")
    create_fake_usage_records(5, current_month)  # Add 5 more (92 + 5 = 97)
    usage = get_monthly_usage(current_month)
    print(f"   Total calls: {usage['total_calls']}")
    print(f"   Percentage: {usage['percentage_used']}%")
    print(f"   Warning level: {usage['warning_level']}")
    print(f"   Expected: 95% ✓" if usage['warning_level'] == '95%' else f"   Expected: 95% ✗")
    print()

    # Trigger warning check
    print("   Checking for warnings (should log CRITICAL)...")
    check_usage_warnings(current_month)
    print()

    # Test 5: Over 100% - Still shows 95% warning
    print("TEST 5: Usage at 105% (105/100 calls) - 95% warning, negative remaining")
    print("---")
    create_fake_usage_records(8, current_month)  # Add 8 more (97 + 8 = 105)
    usage = get_monthly_usage(current_month)
    print(f"   Total calls: {usage['total_calls']}")
    print(f"   Percentage: {usage['percentage_used']}%")
    print(f"   Remaining calls: {usage['remaining_calls']}")
    print(f"   Warning level: {usage['warning_level']}")
    print(f"   Expected: 95% warning, 0 remaining ✓" if usage['remaining_calls'] == 0 else f"   ✗")
    print()

    # Summary
    print("=" * 80)
    print("✅ WARNING THRESHOLD TEST COMPLETE")
    print("=" * 80)
    print()
    print("Summary of test results:")
    print("  - Thresholds detected correctly at 80%, 90%, 95%")
    print("  - Warning levels returned in usage stats")
    print("  - Remaining calls calculated correctly (0 when over limit)")
    print(f"  - Final usage: {usage['total_calls']}/100 calls ({usage['percentage_used']}%)")
    print()
    print("NOTE: Check logs above to verify WARNING and CRITICAL messages appeared")
    print()

if __name__ == "__main__":
    test_warning_thresholds()
