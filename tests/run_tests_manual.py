#!/usr/bin/env python3
"""Manual test runner to verify property tests execute correctly"""

import sys
import traceback
from test_provisional_charge_lifecycle import (
    test_property_3_provisional_charge_creation,
    test_property_5_provisional_charge_expiration
)

def main():
    print("=" * 70)
    print("Running ASE Provisional Charge Lifecycle Property Tests")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Property 3
    print("\n[TEST 1] Property 3: Provisional Charge Creation")
    print("-" * 70)
    try:
        test_property_3_provisional_charge_creation()
        print("✓ Property 3 test PASSED (100 examples)")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Property 3 test FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    # Test 2: Property 5
    print("\n[TEST 2] Property 5: Provisional Charge Expiration")
    print("-" * 70)
    try:
        test_property_5_provisional_charge_expiration()
        print("✓ Property 5 test PASSED (100 examples)")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Property 5 test FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Test Summary: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)
    
    return 0 if tests_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
