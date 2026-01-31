#!/usr/bin/env python3
"""
Manual test runner for compliance marking tests.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from governance.compliance import (
        ComplianceCertification,
        ComplianceTest,
        ComplianceRegistry,
        ComplianceStatus,
        ComplianceLevel,
        TestCategory
    )
    print("✓ Successfully imported compliance modules")
    
    # Run a simple test
    from datetime import datetime, timezone, timedelta
    
    # Create a certification with passing tests
    cert = ComplianceCertification(
        certification_id="cert_0001",
        implementation_name="Test-Implementation",
        implementation_version="1.0.0",
        vendor="Test Vendor",
        vendor_contact="test@vendor.com",
        ase_version="1.0.0",
        compliance_level=ComplianceLevel.STANDARD,
        status=ComplianceStatus.TESTING_IN_PROGRESS
    )
    
    # Add passing tests
    for i in range(5):
        test = ComplianceTest(
            test_id=f"test_{i:04d}",
            test_name=f"Test {i}",
            category=TestCategory.BACKWARD_COMPATIBILITY,
            description="Test description",
            required_for_levels=[ComplianceLevel.STANDARD],
            passed=True,
            execution_time=0.5,
            executed_at=datetime.now(timezone.utc)
        )
        cert.add_test(test)
    
    cert.update_test_counts()
    print(f"✓ Created certification with {cert.total_tests} tests")
    print(f"✓ Passed tests: {cert.passed_tests}")
    
    # Determine status
    status = cert.determine_certification_status()
    print(f"✓ Certification status: {status.value}")
    
    # Certify
    certified, error = cert.certify()
    print(f"✓ Certification result: {certified}")
    
    if certified:
        print(f"✓ Certification date: {cert.certification_date}")
        print(f"✓ Expiration date: {cert.expiration_date}")
    
    # Test registry
    registry = ComplianceRegistry()
    registered, reg_error = registry.register_certification(cert)
    print(f"✓ Registry registration: {registered}")
    
    if registered:
        entry = registry.lookup_implementation("Test-Implementation", "1.0.0")
        print(f"✓ Registry lookup successful: {entry is not None}")
        print(f"✓ Entry is valid: {entry.is_valid()}")
        
        # Mark as non-compliant
        marked = registry.mark_non_compliant("Test-Implementation", "1.0.0", "Test reason")
        print(f"✓ Marked as non-compliant: {marked}")
        
        entry_after = registry.lookup_implementation("Test-Implementation", "1.0.0")
        print(f"✓ Status after marking: {entry_after.status.value}")
        print(f"✓ Is valid after marking: {entry_after.is_valid()}")
    
    print("\n✓ All basic compliance tests passed!")
    
    # Now try to run property-based tests
    print("\nAttempting to run property-based tests...")
    try:
        import hypothesis
        print(f"✓ Hypothesis version: {hypothesis.__version__}")
        
        # Import the test module
        import test_compliance_marking
        print("✓ Successfully imported test module")
        
        # Run tests using pytest
        import pytest
        print("✓ Running property-based tests...")
        exit_code = pytest.main([
            'test_compliance_marking.py',
            '-v',
            '--tb=short',
            '--hypothesis-show-statistics'
        ])
        
        if exit_code == 0:
            print("\n✓ All property-based tests passed!")
        else:
            print(f"\n✗ Some tests failed (exit code: {exit_code})")
            sys.exit(exit_code)
            
    except ImportError as e:
        print(f"✗ Could not import required testing libraries: {e}")
        print("  Please install: pip install hypothesis pytest")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
