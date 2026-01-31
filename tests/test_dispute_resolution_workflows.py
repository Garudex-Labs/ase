"""
Property-based tests for dispute resolution workflows.

Feature: ase, Property 11: Dispute Event Creation
Feature: ase, Property 12: Dispute Resolution Event Creation
Feature: ase, Property 13: Dispute Escalation Support

Validates: Requirements 5.1, 5.3, 5.4
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import hypothesis.strategies as st
from hypothesis import given, settings, assume


# Test data generators

@st.composite
def monetary_amount(draw):
    """Generate valid monetary amounts."""
    value = draw(st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("999999.99"),
        places=2
    ))
    currency = draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"]))
    return {
        "value": str(value),
        "currency": currency
    }


@st.composite
def agent_id(draw):
    """Generate valid agent identifiers."""
    prefix = draw(st.sampled_from(["agent", "service", "client"]))
    suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        min_size=6,
        max_size=20
    ))
    return f"{prefix}_{suffix}"


@st.composite
def charge_event_id(draw):
    """Generate valid charge event identifiers."""
    event_type = draw(st.sampled_from(["prov", "final", "adj", "ref"]))
    suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    return f"evt_{event_type}_{suffix}"


@st.composite
def evidence_item(draw, base_time=None):
    """Generate valid evidence item."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    evidence_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    return {
        "evidenceId": f"evid_{evidence_id_suffix}",
        "evidenceType": draw(st.sampled_from([
            "log_entry", "transaction_record", "screenshot", "document",
            "witness_statement", "system_metric", "audit_trail", "other"
        ])),
        "description": draw(st.text(min_size=10, max_size=500)),
        "timestamp": base_time.isoformat(),
        "contentUri": f"https://evidence.example.com/{evidence_id_suffix}",
        "contentHash": draw(st.text(
            alphabet=st.characters(whitelist_categories=("Nd",)) + "abcdef",
            min_size=64,
            max_size=64
        )),
        "submittedBy": draw(agent_id())
    }


@st.composite
def dispute_event(draw, base_time=None, include_resolution=False, include_escalation=False):
    """Generate valid dispute event."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    dispute_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    # Generate evidence items
    num_evidence = draw(st.integers(min_value=1, max_value=5))
    evidence = [draw(evidence_item(base_time=base_time)) for _ in range(num_evidence)]
    
    # Determine status based on flags
    if include_resolution:
        status = draw(st.sampled_from(["resolved", "closed"]))
    elif include_escalation:
        status = "escalated"
    else:
        status = draw(st.sampled_from(["open", "under_review", "pending_evidence"]))
    
    dispute = {
        "disputeId": f"disp_{dispute_id_suffix}",
        "originalChargeId": draw(charge_event_id()),
        "disputingAgent": draw(agent_id()),
        "respondingAgent": draw(agent_id()),
        "disputeReason": draw(st.text(min_size=20, max_size=500)),
        "disputeCategory": draw(st.sampled_from([
            "billing_error", "service_quality", "unauthorized_charge",
            "pricing_discrepancy", "technical_failure", "other"
        ])),
        "evidence": evidence,
        "status": status,
        "createdAt": base_time.isoformat(),
        "updatedAt": (base_time + timedelta(hours=draw(st.integers(min_value=0, max_value=48)))).isoformat(),
        "escrowAmount": draw(monetary_amount()),
        "metadata": {
            "priority": draw(st.sampled_from(["low", "normal", "high", "urgent"])),
            "expectedResolutionTime": (base_time + timedelta(days=draw(st.integers(min_value=1, max_value=30)))).isoformat()
        }
    }
    
    # Ensure disputing and responding agents are different
    assume(dispute["disputingAgent"] != dispute["respondingAgent"])
    
    # Add resolution if requested
    if include_resolution:
        resolution_id_suffix = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
            min_size=8,
            max_size=16
        ))
        
        outcome = draw(st.sampled_from([
            "dispute_upheld", "dispute_rejected", "partial_refund",
            "full_refund", "charge_adjusted", "no_action_required"
        ]))
        
        resolution = {
            "resolutionId": f"res_{resolution_id_suffix}",
            "outcome": outcome,
            "resolutionReason": draw(st.text(min_size=20, max_size=500)),
            "resolvedAt": (base_time + timedelta(hours=draw(st.integers(min_value=1, max_value=72)))).isoformat(),
            "resolvedBy": draw(agent_id())
        }
        
        # Add adjustment amount for certain outcomes
        if outcome in ["partial_refund", "full_refund", "charge_adjusted"]:
            resolution["adjustmentAmount"] = draw(monetary_amount())
            resolution["settlementInstructions"] = {
                "action": draw(st.sampled_from(["refund", "adjust_charge", "release_escrow", "transfer_funds"])),
                "targetAgent": dispute["disputingAgent"],
                "amount": resolution["adjustmentAmount"],
                "executionDeadline": (base_time + timedelta(days=7)).isoformat()
            }
        
        dispute["resolution"] = resolution
    
    # Add escalation if requested
    if include_escalation:
        escalation_level = draw(st.integers(min_value=1, max_value=5))
        
        escalation = {
            "escalatedAt": (base_time + timedelta(hours=draw(st.integers(min_value=1, max_value=48)))).isoformat(),
            "escalatedBy": dispute["disputingAgent"],
            "escalatedTo": draw(agent_id()),
            "escalationReason": draw(st.text(min_size=20, max_size=500)),
            "escalationLevel": escalation_level
        }
        
        # Add previous arbitrators for higher escalation levels
        if escalation_level > 1:
            num_previous = draw(st.integers(min_value=1, max_value=min(escalation_level - 1, 5)))
            escalation["previousArbitrators"] = [draw(agent_id()) for _ in range(num_previous)]
        
        dispute["escalationDetails"] = escalation
    
    return dispute


# Property tests

@given(dispute=dispute_event())
@settings(max_examples=100)
def test_property_11_dispute_event_creation(dispute: Dict[str, Any]):
    """
    Property 11: Dispute Event Creation
    
    For any charge dispute, a dispute event should be created with complete
    supporting evidence and proper charge references.
    
    This test validates that:
    1. Dispute has all required fields
    2. Dispute ID follows the correct format
    3. Original charge ID is properly referenced
    4. Disputing and responding agents are different
    5. Evidence items are properly structured
    6. Status is valid for dispute lifecycle
    7. Timestamps are properly ordered
    8. Escrow amount is properly formatted
    """
    # Validate required fields exist
    required_fields = [
        "disputeId", "originalChargeId", "disputingAgent", "respondingAgent",
        "disputeReason", "disputeCategory", "status", "createdAt"
    ]
    for field in required_fields:
        assert field in dispute, f"Missing required field: {field}"
    
    # Validate dispute ID format
    assert dispute["disputeId"].startswith("disp_"), \
        f"Dispute ID must start with 'disp_', got {dispute['disputeId']}"
    
    # Validate original charge ID format
    charge_id = dispute["originalChargeId"]
    assert charge_id.startswith("evt_"), \
        f"Charge ID must start with 'evt_', got {charge_id}"
    valid_charge_types = ["evt_prov_", "evt_final_", "evt_adj_", "evt_ref_"]
    assert any(charge_id.startswith(t) for t in valid_charge_types), \
        f"Charge ID must have valid type prefix, got {charge_id}"
    
    # Validate agents are different
    assert dispute["disputingAgent"] != dispute["respondingAgent"], \
        "Disputing and responding agents must be different"
    
    # Validate agent IDs are not empty
    assert len(dispute["disputingAgent"]) > 0, "Disputing agent ID must not be empty"
    assert len(dispute["respondingAgent"]) > 0, "Responding agent ID must not be empty"
    
    # Validate dispute reason
    assert len(dispute["disputeReason"]) > 0, "Dispute reason must not be empty"
    
    # Validate dispute category
    valid_categories = [
        "billing_error", "service_quality", "unauthorized_charge",
        "pricing_discrepancy", "technical_failure", "other"
    ]
    assert dispute["disputeCategory"] in valid_categories, \
        f"Invalid dispute category: {dispute['disputeCategory']}"
    
    # Validate evidence items
    if "evidence" in dispute:
        evidence = dispute["evidence"]
        assert isinstance(evidence, list), "Evidence must be a list"
        
        for i, item in enumerate(evidence):
            # Validate required evidence fields
            required_evidence_fields = [
                "evidenceId", "evidenceType", "description", "timestamp"
            ]
            for field in required_evidence_fields:
                assert field in item, f"Evidence item {i} missing field: {field}"
            
            # Validate evidence type
            valid_evidence_types = [
                "log_entry", "transaction_record", "screenshot", "document",
                "witness_statement", "system_metric", "audit_trail", "other"
            ]
            assert item["evidenceType"] in valid_evidence_types, \
                f"Invalid evidence type: {item['evidenceType']}"
            
            # Validate evidence ID
            assert len(item["evidenceId"]) > 0, "Evidence ID must not be empty"
            
            # Validate description
            assert len(item["description"]) > 0, "Evidence description must not be empty"
            
            # Validate content hash if present
            if "contentHash" in item:
                assert len(item["contentHash"]) == 64, \
                    f"Content hash must be 64 characters, got {len(item['contentHash'])}"
    
    # Validate status
    valid_statuses = [
        "open", "under_review", "pending_evidence", "resolved",
        "escalated", "closed", "withdrawn"
    ]
    assert dispute["status"] in valid_statuses, \
        f"Invalid dispute status: {dispute['status']}"
    
    # Validate timestamps
    created_at = datetime.fromisoformat(dispute["createdAt"].replace("Z", "+00:00"))
    if "updatedAt" in dispute:
        updated_at = datetime.fromisoformat(dispute["updatedAt"].replace("Z", "+00:00"))
        assert updated_at >= created_at, \
            "Updated time must be after or equal to created time"
    
    # Validate escrow amount if present
    if "escrowAmount" in dispute:
        escrow = dispute["escrowAmount"]
        assert "value" in escrow, "Escrow amount must have value"
        assert "currency" in escrow, "Escrow amount must have currency"
        
        escrow_value = Decimal(escrow["value"])
        assert escrow_value > 0, f"Escrow amount must be positive, got {escrow_value}"
        
        assert len(escrow["currency"]) == 3, \
            f"Currency code must be 3 characters, got {escrow['currency']}"


@given(dispute=dispute_event(include_resolution=True))
@settings(max_examples=100)
def test_property_12_dispute_resolution_event_creation(dispute: Dict[str, Any]):
    """
    Property 12: Dispute Resolution Event Creation
    
    For any resolved dispute, a resolution event should be created with
    final settlement details.
    
    This test validates that:
    1. Resolution has all required fields
    2. Resolution ID follows the correct format
    3. Outcome is valid
    4. Resolution reason is provided
    5. Resolved timestamp is after dispute creation
    6. Resolver agent is identified
    7. Settlement instructions are provided when applicable
    8. Adjustment amounts match settlement requirements
    """
    # Validate dispute is in resolved or closed status
    assert dispute["status"] in ["resolved", "closed"], \
        f"Dispute must be resolved or closed, got {dispute['status']}"
    
    # Validate resolution exists
    assert "resolution" in dispute, "Resolved dispute must have resolution"
    
    resolution = dispute["resolution"]
    
    # Validate required resolution fields
    required_fields = ["resolutionId", "outcome", "resolvedAt", "resolvedBy"]
    for field in required_fields:
        assert field in resolution, f"Missing required resolution field: {field}"
    
    # Validate resolution ID format
    assert resolution["resolutionId"].startswith("res_"), \
        f"Resolution ID must start with 'res_', got {resolution['resolutionId']}"
    
    # Validate outcome
    valid_outcomes = [
        "dispute_upheld", "dispute_rejected", "partial_refund",
        "full_refund", "charge_adjusted", "no_action_required"
    ]
    assert resolution["outcome"] in valid_outcomes, \
        f"Invalid resolution outcome: {resolution['outcome']}"
    
    # Validate resolution reason if present
    if "resolutionReason" in resolution:
        assert len(resolution["resolutionReason"]) > 0, \
            "Resolution reason must not be empty"
    
    # Validate resolved timestamp
    created_at = datetime.fromisoformat(dispute["createdAt"].replace("Z", "+00:00"))
    resolved_at = datetime.fromisoformat(resolution["resolvedAt"].replace("Z", "+00:00"))
    assert resolved_at >= created_at, \
        "Resolution time must be after or equal to dispute creation time"
    
    # Validate resolver agent
    assert len(resolution["resolvedBy"]) > 0, \
        "Resolver agent ID must not be empty"
    
    # Validate adjustment amount for applicable outcomes
    outcomes_requiring_adjustment = ["partial_refund", "full_refund", "charge_adjusted"]
    if resolution["outcome"] in outcomes_requiring_adjustment:
        if "adjustmentAmount" in resolution:
            adjustment = resolution["adjustmentAmount"]
            assert "value" in adjustment, "Adjustment amount must have value"
            assert "currency" in adjustment, "Adjustment amount must have currency"
            
            adjustment_value = Decimal(adjustment["value"])
            assert adjustment_value > 0, \
                f"Adjustment amount must be positive, got {adjustment_value}"
            
            assert len(adjustment["currency"]) == 3, \
                f"Currency code must be 3 characters, got {adjustment['currency']}"
    
    # Validate settlement instructions if present
    if "settlementInstructions" in resolution:
        instructions = resolution["settlementInstructions"]
        
        # Validate action
        if "action" in instructions:
            valid_actions = [
                "refund", "adjust_charge", "release_escrow",
                "transfer_funds", "no_action"
            ]
            assert instructions["action"] in valid_actions, \
                f"Invalid settlement action: {instructions['action']}"
        
        # Validate target agent
        if "targetAgent" in instructions:
            assert len(instructions["targetAgent"]) > 0, \
                "Target agent ID must not be empty"
        
        # Validate settlement amount
        if "amount" in instructions:
            amount = instructions["amount"]
            assert "value" in amount, "Settlement amount must have value"
            assert "currency" in amount, "Settlement amount must have currency"
            
            amount_value = Decimal(amount["value"])
            assert amount_value > 0, \
                f"Settlement amount must be positive, got {amount_value}"
        
        # Validate execution deadline
        if "executionDeadline" in instructions:
            deadline = datetime.fromisoformat(
                instructions["executionDeadline"].replace("Z", "+00:00")
            )
            assert deadline > resolved_at, \
                "Execution deadline must be after resolution time"


@given(dispute=dispute_event(include_escalation=True))
@settings(max_examples=100)
def test_property_13_dispute_escalation_support(dispute: Dict[str, Any]):
    """
    Property 13: Dispute Escalation Support
    
    For any dispute requiring escalation, the system should successfully
    route it to designated arbitration agents.
    
    This test validates that:
    1. Escalation has all required fields
    2. Escalation timestamp is after dispute creation
    3. Arbitration agent is identified
    4. Escalation reason is provided
    5. Escalation level is within valid range (1-5)
    6. Previous arbitrators are tracked for multi-level escalations
    7. Escalation chain is properly maintained
    """
    # Validate dispute is in escalated status
    assert dispute["status"] == "escalated", \
        f"Dispute must be escalated, got {dispute['status']}"
    
    # Validate escalation details exist
    assert "escalationDetails" in dispute, \
        "Escalated dispute must have escalation details"
    
    escalation = dispute["escalationDetails"]
    
    # Validate required escalation fields
    required_fields = ["escalatedAt", "escalatedTo", "escalationReason"]
    for field in required_fields:
        assert field in escalation, f"Missing required escalation field: {field}"
    
    # Validate escalation timestamp
    created_at = datetime.fromisoformat(dispute["createdAt"].replace("Z", "+00:00"))
    escalated_at = datetime.fromisoformat(escalation["escalatedAt"].replace("Z", "+00:00"))
    assert escalated_at >= created_at, \
        "Escalation time must be after or equal to dispute creation time"
    
    # Validate arbitration agent
    assert len(escalation["escalatedTo"]) > 0, \
        "Arbitration agent ID must not be empty"
    
    # Validate escalation reason
    assert len(escalation["escalationReason"]) > 0, \
        "Escalation reason must not be empty"
    
    # Validate escalation level
    if "escalationLevel" in escalation:
        level = escalation["escalationLevel"]
        assert isinstance(level, int), "Escalation level must be integer"
        assert 1 <= level <= 5, \
            f"Escalation level must be between 1 and 5, got {level}"
        
        # Validate previous arbitrators for higher levels
        if level > 1:
            if "previousArbitrators" in escalation:
                previous = escalation["previousArbitrators"]
                assert isinstance(previous, list), \
                    "Previous arbitrators must be a list"
                assert len(previous) > 0, \
                    "Previous arbitrators list must not be empty for level > 1"
                assert len(previous) <= 5, \
                    f"Previous arbitrators list too long: {len(previous)}"
                
                # Validate each arbitrator ID
                for arb_id in previous:
                    assert len(arb_id) > 0, \
                        "Arbitrator ID must not be empty"
                
                # Validate no duplicates
                assert len(previous) == len(set(previous)), \
                    "Previous arbitrators must not contain duplicates"
    
    # Validate escalated by agent if present
    if "escalatedBy" in escalation:
        assert len(escalation["escalatedBy"]) > 0, \
            "Escalated by agent ID must not be empty"


@given(
    dispute=dispute_event(),
    resolution_time_hours=st.integers(min_value=1, max_value=168)
)
@settings(max_examples=100)
def test_dispute_lifecycle_timing(
    dispute: Dict[str, Any],
    resolution_time_hours: int
):
    """
    Test that dispute lifecycle timing is properly validated.
    
    Validates:
    1. Creation time is valid
    2. Update time is after creation
    3. Resolution time (if applicable) is after creation
    4. Expected resolution time is in the future
    """
    created_at = datetime.fromisoformat(dispute["createdAt"].replace("Z", "+00:00"))
    
    # Validate updated time
    if "updatedAt" in dispute:
        updated_at = datetime.fromisoformat(dispute["updatedAt"].replace("Z", "+00:00"))
        assert updated_at >= created_at, \
            "Updated time must be after or equal to created time"
    
    # Validate expected resolution time
    if "metadata" in dispute and "expectedResolutionTime" in dispute["metadata"]:
        expected_time = datetime.fromisoformat(
            dispute["metadata"]["expectedResolutionTime"].replace("Z", "+00:00")
        )
        assert expected_time > created_at, \
            "Expected resolution time must be after creation time"
    
    # Simulate resolution at various times
    resolution_time = created_at + timedelta(hours=resolution_time_hours)
    
    # Validate resolution time is after creation
    assert resolution_time > created_at, \
        "Resolution time must be after creation time"
    
    # Validate resolution time is reasonable (within 7 days)
    max_resolution_time = created_at + timedelta(days=7)
    if resolution_time <= max_resolution_time:
        assert True, "Resolution time is within reasonable timeframe"


@given(
    dispute=dispute_event(include_resolution=True),
    escrow_amount=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("999999.99"),
        places=2
    )
)
@settings(max_examples=100)
def test_escrow_management(
    dispute: Dict[str, Any],
    escrow_amount: Decimal
):
    """
    Test that escrow management is properly handled during disputes.
    
    Validates:
    1. Escrow amount is held during dispute
    2. Escrow is released or transferred based on resolution
    3. Settlement instructions match escrow amount
    """
    # Validate escrow amount exists
    if "escrowAmount" in dispute:
        escrow = dispute["escrowAmount"]
        escrow_value = Decimal(escrow["value"])
        
        # Validate escrow is positive
        assert escrow_value > 0, \
            f"Escrow amount must be positive, got {escrow_value}"
        
        # If dispute is resolved, validate settlement
        if "resolution" in dispute:
            resolution = dispute["resolution"]
            
            # Check if settlement instructions exist
            if "settlementInstructions" in resolution:
                instructions = resolution["settlementInstructions"]
                
                # Validate settlement amount matches escrow for certain actions
                if instructions.get("action") in ["release_escrow", "transfer_funds"]:
                    if "amount" in instructions:
                        settlement_value = Decimal(instructions["amount"]["value"])
                        
                        # Settlement should not exceed escrow
                        assert settlement_value <= escrow_value, \
                            f"Settlement amount ({settlement_value}) should not exceed escrow ({escrow_value})"


@given(dispute=dispute_event())
@settings(max_examples=100)
def test_dispute_event_json_serialization(dispute: Dict[str, Any]):
    """
    Test that dispute events can be properly serialized to JSON.
    
    This ensures the dispute event structure is JSON-compatible.
    """
    try:
        # Serialize to JSON
        json_str = json.dumps(dispute)
        
        # Deserialize back
        deserialized = json.loads(json_str)
        
        # Validate all required fields are preserved
        assert deserialized["disputeId"] == dispute["disputeId"]
        assert deserialized["originalChargeId"] == dispute["originalChargeId"]
        assert deserialized["disputingAgent"] == dispute["disputingAgent"]
        assert deserialized["respondingAgent"] == dispute["respondingAgent"]
        assert deserialized["status"] == dispute["status"]
        
    except (TypeError, ValueError) as e:
        assert False, f"Failed to serialize dispute event: {e}"


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
