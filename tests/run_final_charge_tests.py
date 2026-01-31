#!/usr/bin/env python3
"""Manual test runner for final charge reconciliation property tests"""

import sys
import traceback
from test_final_charge_reconciliation import (
    test_property_4_final_charge_creation,
    test_property_6_budget_adjustment_consistency
)

def main():
    print("=" * 70)
    print("Running ASE Final Charge Reconciliation Property Tests")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Property 4
    print("\n[TEST 1] Property 4: Final Charge Creation")
    print("-" * 70)
    try:
        test_property_4_final_charge_creation()
        print("✓ Property 4 test PASSED (100 examples)")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Property 4 test FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    # Test 2: Property 6
    print("\n[TEST 2] Property 6: Budget Adjustment Consistency")
    print("-" * 70)
    try:
        test_property_6_budget_adjustment_consistency()
        print("✓ Property 6 test PASSED (100 examples)")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Property 6 test FAILED: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Test Summary: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70)
    
    return 0 if tests_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
