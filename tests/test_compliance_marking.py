"""
Property-based tests for compliance marking.

Feature: ase, Property 22: Compliance Marking for Failed Tests

Validates: Requirements 10.5
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from governance.compliance import (
    ComplianceCertification,
    ComplianceTest,
    ComplianceRegistry,
    ComplianceStatus,
    ComplianceLevel,
    TestCategory,
    ComplianceRegistryEntry
)


# Test data generators

@st.composite
def implementation_name(draw):
    """Generate implementation name."""
    prefix = draw(st.sampled_from(["ASE", "Agent", "Protocol", "Framework"]))
    suffix = draw(st.sampled_from(["Core", "SDK", "Library", "Implementation"]))
    return f"{prefix}-{suffix}"


@st.composite
def version_string(draw):
    """Generate semantic version string."""
    major = draw(st.integers(min_value=0, max_value=5))
    minor = draw(st.integers(min_value=0, max_value=20))
    patch = draw(st.integers(min_value=0, max_value=50))
    return f"{major}.{minor}.{patch}"


@st.composite
def vendor_name(draw):
    """Generate vendor name."""
    return draw(st.sampled_from([
        "Acme Corp",
        "TechVendor Inc",
        "Protocol Labs",
        "Agent Systems",
        "Open Source Foundation"
    ]))


@st.composite
def email_address(draw):
    """Generate email address."""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=3,
        max_size=20
    ))
    domain = draw(st.sampled_from(["example.com", "test.org", "vendor.io"]))
    return f"{username}@{domain}"


@st.composite
def compliance_test(draw, category=None, required_for_levels=None):
    """Generate compliance test."""
    test_category = category if category else draw(st.sampled_from(list(TestCategory)))
    
    if required_for_levels is None:
        required_for_levels = draw(st.lists(
            st.sampled_from(list(ComplianceLevel)),
            min_size=1,
            max_size=4,
            unique=True
        ))
    
    test_id = f"test_{draw(st.integers(min_value=1, max_value=9999)):04d}"
    
    # Determine if test has been executed
    executed = draw(st.booleans())
    passed = draw(st.booleans()) if executed else None
    
    return ComplianceTest(
        test_id=test_id,
        test_name=f"Test {test_category.value}",
        category=test_category,
        description=draw(st.text(min_size=20, max_size=200)),
        required_for_levels=required_for_levels,
        test_function=f"test_{test_category.value}",
        test_file=f"test_{test_category.value}.py",
        passed=passed,
        execution_time=draw(st.floats(min_value=0.001, max_value=10.0)) if executed else None,
        error_message=draw(st.one_of(st.none(), st.text(min_size=10, max_size=100))) if executed and not passed else None,
        executed_at=datetime.now(timezone.utc) if executed else None,
        property_reference=f"Property {draw(st.integers(min_value=1, max_value=22))}",
        requirement_reference=f"Requirement {draw(st.integers(min_value=1, max_value=10))}.{draw(st.integers(min_value=1, max_value=6))}"
    )


@st.composite
def compliance_certification(draw, status=None, level=None):
    """Generate compliance certification."""
    cert_status = status if status else draw(st.sampled_from(list(ComplianceStatus)))
    cert_level = level if level else draw(st.sampled_from(list(ComplianceLevel)))
    
    impl_name = draw(implementation_name())
    impl_version = draw(version_string())
    
    # Generate tests
    num_tests = draw(st.integers(min_value=5, max_value=20))
    tests = [draw(compliance_test(required_for_levels=[cert_level])) for _ in range(num_tests)]
    
    cert = ComplianceCertification(
        certification_id=f"cert_{draw(st.integers(min_value=1000, max_value=9999))}",
        implementation_name=impl_name,
        implementation_version=impl_version,
        vendor=draw(vendor_name()),
        vendor_contact=draw(email_address()),
        ase_version=draw(st.sampled_from(["1.0.0", "2.0.0"])),
        compliance_level=cert_level,
        status=cert_status,
        test_environment=draw(st.sampled_from(["Linux", "macOS", "Windows", "Docker"])),
        test_framework=draw(st.sampled_from(["pytest", "unittest", "hypothesis"]))
    )
    
    for test in tests:
        cert.add_test(test)
    
    cert.update_test_counts()
    
    # Set certification dates if compliant
    if cert_status == ComplianceStatus.COMPLIANT:
        cert.certification_date = datetime.now(timezone.utc)
        cert.expiration_date = cert.certification_date + timedelta(days=365)
    
    return cert


# Property 22: Compliance Marking for Failed Tests

@given(
    certification=compliance_certification(level=ComplianceLevel.STANDARD)
)
@settings(max_examples=100)
def test_property_22_compliance_marking_for_failed_tests(
    certification: ComplianceCertification
):
    """
    Property 22: Compliance Marking for Failed Tests
    
    For any ASE implementation that fails compatibility tests, it should be
    marked as non-compliant in the registry.
    
    This test validates that:
    1. Failed tests prevent compliance certification
    2. Non-compliant implementations are marked correctly
    3. Registry tracks non-compliant status
    4. Compliance status reflects test results
    5. Failed test details are preserved
    
    Validates: Requirements 10.5
    """
    # Create registry
    registry = ComplianceRegistry()
    
    # Count failed tests
    failed_tests = [test for test in certification.tests if test.passed is False]
    passed_tests = [test for test in certification.tests if test.passed is True]
    untested = [test for test in certification.tests if test.passed is None]
    
    # Determine expected compliance status
    certification.update_test_counts()
    expected_status = certification.determine_certification_status()
    
    # Validate status determination logic
    if len(untested) > 0:
        assert expected_status == ComplianceStatus.TESTING_IN_PROGRESS, \
            "Status should be TESTING_IN_PROGRESS when tests are not executed"
    elif len(failed_tests) > 0:
        # Should be non-compliant or conditionally compliant
        assert expected_status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.CONDITIONALLY_COMPLIANT], \
            f"Status should be NON_COMPLIANT or CONDITIONALLY_COMPLIANT with failed tests, got {expected_status.value}"
    elif len(passed_tests) == len(certification.tests):
        assert expected_status == ComplianceStatus.COMPLIANT, \
            "Status should be COMPLIANT when all tests pass"
    
    # Attempt certification
    certified, error_message = certification.certify()
    
    # Validate certification result
    if len(failed_tests) > 0:
        assert not certified, \
            "Certification should fail when tests fail"
        assert error_message is not None, \
            "Error message should be provided for failed certification"
    
    # Attempt to register in registry
    if certification.status == ComplianceStatus.COMPLIANT:
        registered, reg_error = registry.register_certification(certification)
        assert registered, \
            f"Compliant implementation should be registered: {reg_error}"
        
        # Verify registry entry
        entry = registry.lookup_implementation(
            certification.implementation_name,
            certification.implementation_version
        )
        assert entry is not None, \
            "Registered implementation should be found in registry"
        assert entry.status == ComplianceStatus.COMPLIANT, \
            "Registry entry should have COMPLIANT status"
    else:
        # Non-compliant implementation should not be registered
        registered, reg_error = registry.register_certification(certification)
        assert not registered, \
            "Non-compliant implementation should not be registered"
        assert "non-compliant" in reg_error.lower(), \
            f"Error message should mention non-compliance: {reg_error}"


@given(
    impl_name=implementation_name(),
    impl_version=version_string()
)
@settings(max_examples=100)
def test_property_22_mark_implementation_non_compliant(
    impl_name: str,
    impl_version: str
):
    """
    Property 22: Mark Implementation as Non-Compliant
    
    For any implementation that was previously compliant but fails new tests,
    it should be marked as non-compliant in the registry.
    
    Validates: Requirements 10.5
    """
    # Create a compliant certification
    cert = ComplianceCertification(
        certification_id="cert_0001",
        implementation_name=impl_name,
        implementation_version=impl_version,
        vendor="Test Vendor",
        vendor_contact="test@vendor.com",
        ase_version="1.0.0",
        compliance_level=ComplianceLevel.STANDARD,
        status=ComplianceStatus.COMPLIANT,
        certification_date=datetime.now(timezone.utc),
        expiration_date=datetime.now(timezone.utc) + timedelta(days=365)
    )
    
    # Add passing tests
    for i in range(10):
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
    
    # Register in registry
    registry = ComplianceRegistry()
    registered, _ = registry.register_certification(cert)
    assert registered, "Initial registration should succeed"
    
    # Verify compliant status
    entry = registry.lookup_implementation(impl_name, impl_version)
    assert entry is not None, "Implementation should be in registry"
    assert entry.status == ComplianceStatus.COMPLIANT, "Initial status should be COMPLIANT"
    assert entry.is_valid(), "Certification should be valid"
    
    # Mark as non-compliant (simulating failed re-test)
    marked = registry.mark_non_compliant(
        impl_name,
        impl_version,
        "Failed backward compatibility test after protocol update"
    )
    
    assert marked, "Implementation should be successfully marked as non-compliant"
    
    # Verify non-compliant status
    entry_after = registry.lookup_implementation(impl_name, impl_version)
    assert entry_after is not None, "Implementation should still be in registry"
    assert entry_after.status == ComplianceStatus.NON_COMPLIANT, \
        "Status should be updated to NON_COMPLIANT"
    assert not entry_after.is_valid(), \
        "Non-compliant certification should not be valid"
    
    # Verify it's not in compliant implementations list
    compliant_impls = registry.get_compliant_implementations()
    compliant_names = [e.implementation_name for e in compliant_impls]
    assert impl_name not in compliant_names or \
           not any(e.implementation_version == impl_version for e in compliant_impls if e.implementation_name == impl_name), \
        "Non-compliant implementation should not appear in compliant list"


@given(
    certification=compliance_certification(status=ComplianceStatus.COMPLIANT, level=ComplianceLevel.BASIC)
)
@settings(max_examples=100)
def test_property_22_failed_test_details_preserved(
    certification: ComplianceCertification
):
    """
    Property 22: Failed Test Details Preserved
    
    For any failed compliance test, the test details including error messages
    should be preserved for debugging and remediation.
    
    Validates: Requirements 10.5
    """
    # Add a failing test
    failing_test = ComplianceTest(
        test_id="test_fail_001",
        test_name="Backward Compatibility Test",
        category=TestCategory.BACKWARD_COMPATIBILITY,
        description="Test backward compatibility with non-ASE agents",
        required_for_levels=[ComplianceLevel.BASIC],
        test_function="test_backward_compatibility",
        test_file="test_compatibility.py",
        passed=False,
        execution_time=1.5,
        error_message="AssertionError: Base protocol fields not accessible",
        executed_at=datetime.now(timezone.utc),
        property_reference="Property 1",
        requirement_reference="Requirement 1.1"
    )
    
    certification.add_test(failing_test)
    certification.update_test_counts()
    
    # Determine status
    status = certification.determine_certification_status()
    
    # Should be non-compliant due to failed test
    assert status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.CONDITIONALLY_COMPLIANT], \
        f"Status should indicate non-compliance with failed tests, got {status.value}"
    
    # Verify failed test details are preserved
    failed_tests = [test for test in certification.tests if test.passed is False]
    assert len(failed_tests) > 0, "Failed test should be in certification"
    
    failed_test_found = any(test.test_id == "test_fail_001" for test in failed_tests)
    assert failed_test_found, "Specific failed test should be found"
    
    # Verify error message is preserved
    for test in failed_tests:
        if test.test_id == "test_fail_001":
            assert test.error_message is not None, \
                "Error message should be preserved"
            assert "AssertionError" in test.error_message, \
                "Error message should contain failure details"
            assert test.property_reference is not None, \
                "Property reference should be preserved"
            assert test.requirement_reference is not None, \
                "Requirement reference should be preserved"
    
    # Serialize to dict and verify details are included
    cert_dict = certification.to_dict()
    assert "tests" in cert_dict, "Serialized certification should include tests"
    
    failed_test_dicts = [t for t in cert_dict["tests"] if t["passed"] is False]
    assert len(failed_test_dicts) > 0, "Failed tests should be in serialized data"
    
    for test_dict in failed_test_dicts:
        if test_dict["testId"] == "test_fail_001":
            assert test_dict["errorMessage"] is not None, \
                "Error message should be in serialized data"
            assert test_dict["propertyReference"] is not None, \
                "Property reference should be in serialized data"


@given(
    certification=compliance_certification()
)
@settings(max_examples=100)
def test_compliance_score_calculation(
    certification: ComplianceCertification
):
    """
    Test compliance score calculation.
    
    Validates that compliance score accurately reflects test pass rate.
    """
    certification.update_test_counts()
    score = certification.calculate_compliance_score()
    
    # Validate score range
    assert 0.0 <= score <= 1.0, \
        f"Compliance score should be between 0.0 and 1.0, got {score}"
    
    # Validate score calculation
    if certification.total_tests > 0:
        expected_score = certification.passed_tests / certification.total_tests
        assert abs(score - expected_score) < 0.001, \
            f"Score calculation incorrect: expected {expected_score}, got {score}"
    else:
        assert score == 0.0, \
            "Score should be 0.0 when no tests exist"


@given(
    level=st.sampled_from(list(ComplianceLevel))
)
@settings(max_examples=100)
def test_compliance_level_validation(
    level: ComplianceLevel
):
    """
    Test compliance validation for different levels.
    
    Validates that compliance is correctly determined for each level.
    """
    # Create certification for specific level
    cert = ComplianceCertification(
        certification_id="cert_level_test",
        implementation_name="Test Implementation",
        implementation_version="1.0.0",
        vendor="Test Vendor",
        vendor_contact="test@vendor.com",
        ase_version="1.0.0",
        compliance_level=level,
        status=ComplianceStatus.TESTING_IN_PROGRESS
    )
    
    # Add tests for this level
    for i in range(10):
        test = ComplianceTest(
            test_id=f"test_{i:04d}",
            test_name=f"Test {i}",
            category=TestCategory.BACKWARD_COMPATIBILITY,
            description="Test description",
            required_for_levels=[level],
            passed=True,
            execution_time=0.5,
            executed_at=datetime.now(timezone.utc)
        )
        cert.add_test(test)
    
    # Validate compliance for this level
    is_compliant, failed_tests = cert.validate_compliance_for_level(level)
    
    assert is_compliant, \
        f"All tests passed, should be compliant for level {level.value}: {failed_tests}"
    assert len(failed_tests) == 0, \
        "No failed tests should be reported"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
