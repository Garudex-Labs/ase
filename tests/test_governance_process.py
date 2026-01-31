"""
Property-based tests for governance process validation.

Feature: ase, Property 21: RFC Proof-of-Concept Requirement

Validates: Requirements 10.4
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from governance.rfc_process import (
    RFCProposal,
    RFCStatus,
    RFCCategory,
    RFCValidator,
    ProofOfConceptRequirement
)


# Test data generators

@st.composite
def rfc_id(draw):
    """Generate valid RFC identifier."""
    number = draw(st.integers(min_value=1, max_value=9999))
    return f"RFC-{number:04d}"


@st.composite
def email_address(draw):
    """Generate valid email address."""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=3,
        max_size=20
    ))
    domain = draw(st.sampled_from(["example.com", "test.org", "ase-protocol.io"]))
    return f"{username}@{domain}"


@st.composite
def rfc_category(draw):
    """Generate RFC category."""
    return draw(st.sampled_from(list(RFCCategory)))


@st.composite
def rfc_status(draw):
    """Generate RFC status."""
    return draw(st.sampled_from(list(RFCStatus)))


@st.composite
def poc_requirement(draw, required=None):
    """Generate proof-of-concept requirement."""
    is_required = required if required is not None else draw(st.booleans())
    
    acceptance_criteria = draw(st.lists(
        st.text(min_size=10, max_size=100),
        min_size=1 if is_required else 0,
        max_size=5
    ))
    
    completed = draw(st.booleans()) if is_required else False
    
    return ProofOfConceptRequirement(
        required=is_required,
        description=draw(st.text(min_size=50, max_size=200)),
        acceptance_criteria=acceptance_criteria,
        implementation_language=draw(st.one_of(
            st.none(),
            st.sampled_from(["Python", "TypeScript", "Java", "Go", "Rust"])
        )),
        repository_url=draw(st.one_of(
            st.none(),
            st.text(min_size=20, max_size=100).map(lambda x: f"https://github.com/ase/{x}")
        )) if completed else None,
        demo_url=draw(st.one_of(
            st.none(),
            st.text(min_size=20, max_size=100).map(lambda x: f"https://demo.ase/{x}")
        )),
        test_results_url=draw(st.one_of(
            st.none(),
            st.text(min_size=20, max_size=100).map(lambda x: f"https://ci.ase/{x}")
        )) if completed else None,
        completed=completed,
        completion_date=datetime.now(timezone.utc) if completed else None,
        reviewer_notes=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200)))
    )


@st.composite
def rfc_proposal(draw, category=None, status=None, poc_required=None):
    """Generate RFC proposal."""
    selected_category = category if category else draw(rfc_category())
    selected_status = status if status else draw(rfc_status())
    
    # Determine if POC is required based on category
    requires_poc = selected_category in {
        RFCCategory.PROTOCOL_EXTENSION,
        RFCCategory.SCHEMA_CHANGE,
        RFCCategory.SECURITY_ENHANCEMENT,
        RFCCategory.BACKWARD_COMPATIBILITY
    }
    
    poc_req = draw(poc_requirement(required=requires_poc if poc_required is None else poc_required))
    
    created_at = datetime.now(timezone.utc) - timedelta(days=draw(st.integers(min_value=1, max_value=90)))
    updated_at = created_at + timedelta(days=draw(st.integers(min_value=0, max_value=30)))
    
    num_reviewers = draw(st.integers(min_value=0, max_value=5))
    reviewers = [f"reviewer_{i}@example.com" for i in range(num_reviewers)]
    
    approval_votes = {}
    if num_reviewers > 0:
        for reviewer in reviewers[:draw(st.integers(min_value=0, max_value=num_reviewers))]:
            approval_votes[reviewer] = draw(st.booleans())
    
    return RFCProposal(
        rfc_id=draw(rfc_id()),
        title=draw(st.text(min_size=10, max_size=100)),
        author=draw(st.text(min_size=5, max_size=50)),
        author_email=draw(email_address()),
        category=selected_category,
        status=selected_status,
        created_at=created_at,
        updated_at=updated_at,
        abstract=draw(st.text(min_size=50, max_size=500)),
        motivation=draw(st.text(min_size=100, max_size=1000)),
        specification=draw(st.text(min_size=200, max_size=2000)),
        backward_compatibility=draw(st.text(min_size=50, max_size=500)),
        security_considerations=draw(st.text(min_size=50, max_size=500)),
        poc_requirement=poc_req,
        reviewers=reviewers,
        approval_votes=approval_votes,
        target_version=draw(st.one_of(
            st.none(),
            st.sampled_from(["1.0.0", "1.1.0", "2.0.0", "2.1.0"])
        ))
    )


# Property 21: RFC Proof-of-Concept Requirement

@given(
    category=st.sampled_from([
        RFCCategory.PROTOCOL_EXTENSION,
        RFCCategory.SCHEMA_CHANGE,
        RFCCategory.SECURITY_ENHANCEMENT,
        RFCCategory.BACKWARD_COMPATIBILITY
    ])
)
@settings(max_examples=100)
def test_property_21_rfc_poc_requirement_for_critical_categories(
    category: RFCCategory
):
    """
    Property 21: RFC Proof-of-Concept Requirement
    
    For any proposed RFC in the governance process that modifies protocol
    behavior, schemas, or security mechanisms, an implementation proof-of-concept
    should be required and validated.
    
    This test validates that:
    1. Critical RFC categories require proof-of-concept
    2. POC must be completed before approval
    3. POC must include repository URL and test results
    4. POC validation enforces acceptance criteria
    5. RFCs cannot be approved without valid POC
    
    Validates: Requirements 10.4
    """
    # Create RFC with category that requires POC
    rfc = RFCProposal(
        rfc_id="RFC-0001",
        title="Test RFC for POC Requirement",
        author="Test Author",
        author_email="author@example.com",
        category=category,
        status=RFCStatus.UNDER_REVIEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        abstract="This is a test RFC to validate POC requirements for critical categories.",
        motivation="Testing POC requirement enforcement in the governance process.",
        specification="Detailed specification of the proposed changes to the ASE protocol.",
        backward_compatibility="This change maintains backward compatibility with existing implementations.",
        security_considerations="Security implications have been thoroughly analyzed and documented.",
        poc_requirement=ProofOfConceptRequirement(
            required=True,
            description="Proof-of-concept implementation demonstrating the proposed changes",
            acceptance_criteria=[
                "Implementation compiles and runs without errors",
                "All unit tests pass",
                "Integration tests demonstrate compatibility"
            ]
        )
    )
    
    # Validate that RFC requires POC
    assert rfc.requires_poc(), \
        f"RFC with category {category.value} must require proof-of-concept"
    
    assert rfc.poc_requirement.required, \
        "POC requirement must be marked as required"
    
    # Validate that RFC cannot be approved without completed POC
    can_approve, issues = rfc.can_approve()
    assert not can_approve, \
        "RFC should not be approvable without completed POC"
    
    # Check that POC completion is mentioned in blocking issues
    poc_mentioned = any("POC" in issue or "proof" in issue.lower() for issue in issues)
    assert poc_mentioned, \
        f"Blocking issues should mention POC requirement: {issues}"
    
    # Complete the POC
    rfc.poc_requirement.completed = True
    rfc.poc_requirement.repository_url = "https://github.com/ase/rfc-0001-poc"
    rfc.poc_requirement.test_results_url = "https://ci.ase/rfc-0001/results"
    rfc.poc_requirement.completion_date = datetime.now(timezone.utc)
    
    # Validate POC completion
    poc_valid, poc_errors = rfc.poc_requirement.validate_completion()
    assert poc_valid, \
        f"Completed POC should be valid: {poc_errors}"
    
    # Add required reviewers and approvals
    rfc.reviewers = ["reviewer1@example.com", "reviewer2@example.com"]
    rfc.approval_votes = {
        "reviewer1@example.com": True,
        "reviewer2@example.com": True
    }
    rfc.status = RFCStatus.POC_COMPLETED
    
    # Now RFC should be approvable
    can_approve_now, issues_now = rfc.can_approve()
    assert can_approve_now, \
        f"RFC with completed POC should be approvable: {issues_now}"


@given(
    category=st.sampled_from([
        RFCCategory.PERFORMANCE_IMPROVEMENT,
        RFCCategory.DOCUMENTATION,
        RFCCategory.GOVERNANCE_PROCESS
    ])
)
@settings(max_examples=100)
def test_property_21_rfc_poc_not_required_for_non_critical_categories(
    category: RFCCategory
):
    """
    Property 21: RFC Proof-of-Concept Requirement (Non-Critical Categories)
    
    For any proposed RFC in non-critical categories (documentation, governance),
    proof-of-concept should not be required.
    
    Validates: Requirements 10.4
    """
    # Create RFC with category that doesn't require POC
    rfc = RFCProposal(
        rfc_id="RFC-0002",
        title="Test RFC for Non-POC Category",
        author="Test Author",
        author_email="author@example.com",
        category=category,
        status=RFCStatus.UNDER_REVIEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        abstract="This is a test RFC for a category that doesn't require POC.",
        motivation="Testing that POC is not required for non-critical categories.",
        specification="Detailed specification of the proposed changes.",
        backward_compatibility="No backward compatibility concerns for this category.",
        security_considerations="No security implications for this category.",
        poc_requirement=ProofOfConceptRequirement(
            required=False,
            description="POC not required for this category",
            acceptance_criteria=[]
        )
    )
    
    # Validate that RFC does not require POC
    assert not rfc.requires_poc(), \
        f"RFC with category {category.value} should not require proof-of-concept"
    
    # Add required reviewers and approvals
    rfc.reviewers = ["reviewer1@example.com", "reviewer2@example.com"]
    rfc.approval_votes = {
        "reviewer1@example.com": True,
        "reviewer2@example.com": True
    }
    
    # RFC should be approvable without POC
    can_approve, issues = rfc.can_approve()
    
    # Check that POC is not blocking approval
    poc_blocking = any("POC" in issue or "proof" in issue.lower() for issue in issues)
    assert not poc_blocking, \
        f"POC should not block approval for category {category.value}: {issues}"


@given(
    rfc=rfc_proposal(
        category=RFCCategory.PROTOCOL_EXTENSION,
        status=RFCStatus.POC_REQUIRED
    )
)
@settings(max_examples=100)
def test_property_21_poc_validation_requirements(
    rfc: RFCProposal
):
    """
    Property 21: RFC Proof-of-Concept Validation Requirements
    
    For any RFC with a proof-of-concept requirement, the POC must meet
    specific validation criteria including repository URL, test results,
    and acceptance criteria.
    
    Validates: Requirements 10.4
    """
    # Ensure RFC requires POC
    assume(rfc.requires_poc())
    assume(rfc.poc_requirement.required)
    
    # Test incomplete POC
    if not rfc.poc_requirement.completed:
        poc_valid, poc_errors = rfc.poc_requirement.validate_completion()
        assert not poc_valid, \
            "Incomplete POC should not be valid"
        assert len(poc_errors) > 0, \
            "Incomplete POC should have validation errors"
    
    # Test POC with missing required fields
    rfc.poc_requirement.completed = True
    rfc.poc_requirement.repository_url = None
    rfc.poc_requirement.test_results_url = None
    
    poc_valid, poc_errors = rfc.poc_requirement.validate_completion()
    assert not poc_valid, \
        "POC without repository URL and test results should not be valid"
    
    # Verify specific error messages
    assert any("repository" in err.lower() for err in poc_errors), \
        "Validation errors should mention missing repository URL"
    assert any("test results" in err.lower() for err in poc_errors), \
        "Validation errors should mention missing test results URL"
    
    # Complete all required fields
    rfc.poc_requirement.repository_url = "https://github.com/ase/poc"
    rfc.poc_requirement.test_results_url = "https://ci.ase/results"
    rfc.poc_requirement.completion_date = datetime.now(timezone.utc)
    
    # Now POC should be valid
    poc_valid, poc_errors = rfc.poc_requirement.validate_completion()
    assert poc_valid, \
        f"POC with all required fields should be valid: {poc_errors}"


@given(
    rfc=rfc_proposal(
        category=RFCCategory.SECURITY_ENHANCEMENT,
        status=RFCStatus.UNDER_REVIEW
    )
)
@settings(max_examples=100)
def test_property_21_rfc_approval_blocked_without_poc(
    rfc: RFCProposal
):
    """
    Property 21: RFC Approval Blocked Without POC
    
    For any RFC that requires proof-of-concept, the approval process
    should be blocked until the POC is completed and validated.
    
    Validates: Requirements 10.4
    """
    # Ensure RFC requires POC
    assume(rfc.requires_poc())
    
    # Set POC as required but not completed
    rfc.poc_requirement.required = True
    rfc.poc_requirement.completed = False
    
    # Add sufficient reviewers and approvals
    rfc.reviewers = ["reviewer1@example.com", "reviewer2@example.com", "reviewer3@example.com"]
    rfc.approval_votes = {
        "reviewer1@example.com": True,
        "reviewer2@example.com": True,
        "reviewer3@example.com": True
    }
    
    # Attempt to approve RFC
    can_approve, issues = rfc.can_approve()
    
    # Approval should be blocked
    assert not can_approve, \
        "RFC approval should be blocked without completed POC"
    
    # Verify POC is mentioned in blocking issues
    poc_mentioned = any("POC" in issue or "proof" in issue.lower() for issue in issues)
    assert poc_mentioned, \
        f"Blocking issues should mention POC: {issues}"
    
    # Attempt status transition to APPROVED
    success, error = rfc.transition_status(RFCStatus.APPROVED)
    assert not success, \
        "Status transition to APPROVED should fail without completed POC"
    assert error is not None, \
        "Error message should be provided for failed transition"


@given(
    rfc=rfc_proposal()
)
@settings(max_examples=100)
def test_rfc_validator_structure_validation(
    rfc: RFCProposal
):
    """
    Test RFC structure validation by RFCValidator.
    
    Validates that RFC proposals meet structural requirements.
    """
    # Validate RFC structure
    is_valid, errors = RFCValidator.validate_rfc_structure(rfc)
    
    # Check RFC ID format
    if not rfc.rfc_id.startswith("RFC-") or not rfc.rfc_id[4:].isdigit():
        assert not is_valid, "Invalid RFC ID should fail validation"
        assert any("RFC ID" in err for err in errors), \
            "Errors should mention RFC ID format"
    
    # Check minimum text lengths
    if len(rfc.title) < 10:
        assert not is_valid, "Short title should fail validation"
    
    if len(rfc.abstract) < 50:
        assert not is_valid, "Short abstract should fail validation"
    
    # Check email format
    if "@" not in rfc.author_email or "." not in rfc.author_email:
        assert not is_valid, "Invalid email should fail validation"
    
    # Check timestamp ordering
    if rfc.updated_at < rfc.created_at:
        assert not is_valid, "Invalid timestamp ordering should fail validation"


@given(
    rfc=rfc_proposal(
        category=RFCCategory.PROTOCOL_EXTENSION,
        status=RFCStatus.POC_COMPLETED
    )
)
@settings(max_examples=100)
def test_rfc_validator_approval_readiness(
    rfc: RFCProposal
):
    """
    Test RFC approval readiness validation.
    
    Validates that all requirements are met before RFC can be approved.
    """
    # Ensure POC is completed
    rfc.poc_requirement.required = True
    rfc.poc_requirement.completed = True
    rfc.poc_requirement.repository_url = "https://github.com/ase/poc"
    rfc.poc_requirement.test_results_url = "https://ci.ase/results"
    rfc.poc_requirement.completion_date = datetime.now(timezone.utc)
    
    # Add reviewers and approvals
    rfc.reviewers = ["reviewer1@example.com", "reviewer2@example.com"]
    rfc.approval_votes = {
        "reviewer1@example.com": True,
        "reviewer2@example.com": True
    }
    
    # Validate approval readiness
    is_ready, issues = RFCValidator.validate_approval_readiness(rfc)
    
    # Should be ready for approval
    assert is_ready, \
        f"RFC with completed POC and approvals should be ready: {issues}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
