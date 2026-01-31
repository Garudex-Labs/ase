#!/usr/bin/env python3
"""
Manual test runner for governance process tests.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from governance.rfc_process import (
        RFCProposal,
        RFCStatus,
        RFCCategory,
        RFCValidator,
        ProofOfConceptRequirement
    )
    print("✓ Successfully imported governance modules")
    
    # Run a simple test
    from datetime import datetime, timezone
    
    rfc = RFCProposal(
        rfc_id="RFC-0001",
        title="Test RFC for POC Requirement",
        author="Test Author",
        author_email="author@example.com",
        category=RFCCategory.PROTOCOL_EXTENSION,
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
    
    print(f"✓ Created RFC: {rfc.rfc_id}")
    print(f"✓ RFC requires POC: {rfc.requires_poc()}")
    
    can_approve, issues = rfc.can_approve()
    print(f"✓ Can approve (should be False): {can_approve}")
    print(f"✓ Blocking issues: {len(issues)}")
    
    # Complete POC
    rfc.poc_requirement.completed = True
    rfc.poc_requirement.repository_url = "https://github.com/ase/rfc-0001-poc"
    rfc.poc_requirement.test_results_url = "https://ci.ase/rfc-0001/results"
    rfc.poc_requirement.completion_date = datetime.now(timezone.utc)
    
    # Add reviewers
    rfc.reviewers = ["reviewer1@example.com", "reviewer2@example.com"]
    rfc.approval_votes = {
        "reviewer1@example.com": True,
        "reviewer2@example.com": True
    }
    rfc.status = RFCStatus.POC_COMPLETED
    
    can_approve_now, issues_now = rfc.can_approve()
    print(f"✓ Can approve after POC (should be True): {can_approve_now}")
    
    if can_approve_now:
        print("\n✓ All basic governance tests passed!")
    else:
        print(f"\n✗ Approval still blocked: {issues_now}")
        sys.exit(1)
    
    # Now try to import and run hypothesis tests
    print("\nAttempting to run property-based tests...")
    try:
        import hypothesis
        print(f"✓ Hypothesis version: {hypothesis.__version__}")
        
        # Import the test module
        import test_governance_process
        print("✓ Successfully imported test module")
        
        # Run tests using pytest
        import pytest
        print("✓ Running property-based tests...")
        exit_code = pytest.main([
            'test_governance_process.py',
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
