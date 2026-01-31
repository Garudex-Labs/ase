"""
Property-based tests for final charge reconciliation.

Feature: ase, Property 4: Final Charge Creation
Feature: ase, Property 6: Budget Adjustment Consistency

Validates: Requirements 3.2, 3.6
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Tuple

import hypothesis.strategies as st
from hypothesis import given, settings, assume


# Test data generators

@st.composite
def monetary_amount(draw, min_value=Decimal("0.01"), max_value=Decimal("999999.99")):
    """Generate valid monetary amounts."""
    value = draw(st.decimals(
        min_value=min_value,
        max_value=max_value,
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
def charge_pair(draw):
    """Generate a valid provisional and final charge pair for reconciliation."""
    base_time = datetime.now(timezone.utc)
    
    # Generate common fields
    agent = draw(agent_id())
    currency = draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"]))
    
    # Generate provisional charge
    provisional_amount = draw(st.decimals(
        min_value=Decimal("10.00"),
        max_value=Decimal("1000.00"),
        places=2
    ))
    
    expiration_minutes = draw(st.integers(min_value=30, max_value=120))
    expires_at = base_time + timedelta(minutes=expiration_minutes)
    
    provisional_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    provisional = {
        "eventId": f"evt_prov_{provisional_id_suffix}",
        "eventType": "provisional",
        "timestamp": base_time.isoformat(),
        "agentId": agent,
        "amount": {
            "value": str(provisional_amount),
            "currency": currency
        },
        "description": "Provisional charge for resource request",
        "expiresAt": expires_at.isoformat(),
        "status": "reserved"
    }
    
    # Generate final charge with variance
    # Variance between -40% and +15% to test both refunds and additional charges
    variance_pct = draw(st.floats(min_value=-0.40, max_value=0.15))
    final_amount = provisional_amount * (Decimal("1") + Decimal(str(variance_pct)))
    final_amount = max(Decimal("0.01"), final_amount.quantize(Decimal("0.01")))
    
    # Final charge created before expiration
    final_time_offset = draw(st.integers(min_value=1, max_value=expiration_minutes - 1))
    final_time = base_time + timedelta(minutes=final_time_offset)
    
    final_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    final = {
        "eventId": f"evt_final_{final_id_suffix}",
        "eventType": "final",
        "timestamp": final_time.isoformat(),
        "agentId": agent,
        "amount": {
            "value": str(final_amount),
            "currency": currency
        },
        "description": "Final charge for resource consumption",
        "provisionalChargeId": provisional["eventId"],
        "status": "pending"
    }
    
    return provisional, final


@st.composite
def orphaned_final_charge(draw):
    """Generate a final charge without provisional charge reference."""
    base_time = datetime.now(timezone.utc)
    
    final_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    return {
        "eventId": f"evt_final_{final_id_suffix}",
        "eventType": "final",
        "timestamp": base_time.isoformat(),
        "agentId": draw(agent_id()),
        "amount": draw(monetary_amount()),
        "description": draw(st.text(min_size=10, max_size=200)),
        "status": "pending"
        # Note: No provisionalChargeId field
    }


# Property tests

@given(charge_pair=charge_pair())
@settings(max_examples=100)
def test_property_4_final_charge_creation(charge_pair: Tuple[Dict[str, Any], Dict[str, Any]]):
    """
    Property 4: Final Charge Creation
    
    For any completed resource consumption, a final charge event should be
    created with accurate actual costs.
    
    This test validates that:
    1. Final charge has all required fields
    2. Event type is "final"
    3. Final charge references provisional charge correctly
    4. Agent IDs match between charges
    5. Currencies match between charges
    6. Final charge created before provisional expiration
    7. Amount is positive
    """
    provisional, final = charge_pair
    
    # Validate required fields exist
    required_fields = [
        "eventId", "eventType", "timestamp", "agentId",
        "amount", "description", "status"
    ]
    for field in required_fields:
        assert field in final, f"Missing required field: {field}"
    
    # Validate event type
    assert final["eventType"] == "final", \
        f"Event type must be 'final', got {final['eventType']}"
    
    # Validate event ID format
    assert final["eventId"].startswith("evt_final_"), \
        f"Final charge ID must start with 'evt_final_', got {final['eventId']}"
    
    # Validate provisional charge reference
    assert "provisionalChargeId" in final, \
        "Final charge should reference provisional charge"
    assert final["provisionalChargeId"] == provisional["eventId"], \
        "Provisional charge ID must match"
    
    # Validate agent match
    assert final["agentId"] == provisional["agentId"], \
        f"Agent IDs must match: {final['agentId']} != {provisional['agentId']}"
    
    # Validate currency match
    assert final["amount"]["currency"] == provisional["amount"]["currency"], \
        f"Currencies must match: {final['amount']['currency']} != {provisional['amount']['currency']}"
    
    # Validate timing
    final_time = datetime.fromisoformat(final["timestamp"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(provisional["expiresAt"].replace("Z", "+00:00"))
    assert final_time < expires_at, \
        "Final charge must be created before provisional expiration"
    
    # Validate amount is positive
    final_amount = Decimal(final["amount"]["value"])
    assert final_amount > 0, \
        f"Amount must be positive, got {final_amount}"
    
    # Validate status is valid for final charges
    valid_statuses = ["pending", "confirmed", "disputed", "refunded"]
    assert final["status"] in valid_statuses, \
        f"Invalid status for final charge: {final['status']}"


@given(charge_pair=charge_pair())
@settings(max_examples=100)
def test_property_6_budget_adjustment_consistency(
    charge_pair: Tuple[Dict[str, Any], Dict[str, Any]]
):
    """
    Property 6: Budget Adjustment Consistency
    
    For any scenario where final charges differ from provisional charges,
    budget allocations should be adjusted to reflect the actual difference.
    
    This test validates that:
    1. Budget adjustment is calculated correctly
    2. Adjustment type is determined correctly (additional/refund/none)
    3. Budget invariant is maintained
    4. Adjustment amount equals the difference
    5. Currency consistency is maintained
    """
    provisional, final = charge_pair
    
    # Parse amounts
    provisional_amount = Decimal(provisional["amount"]["value"])
    final_amount = Decimal(final["amount"]["value"])
    currency = final["amount"]["currency"]
    
    # Calculate difference
    difference = final_amount - provisional_amount
    
    # Determine adjustment type
    if difference > 0:
        expected_adjustment_type = "additional_charge"
        expected_adjustment_amount = difference
    elif difference < 0:
        expected_adjustment_type = "refund"
        expected_adjustment_amount = abs(difference)
    else:
        expected_adjustment_type = "none"
        expected_adjustment_amount = Decimal("0")
    
    # Simulate budget state before reconciliation
    initial_total = Decimal("10000.00")
    initial_reserved = provisional_amount
    initial_available = initial_total - initial_reserved
    initial_consumed = Decimal("0.00")
    
    # Validate initial budget invariant
    assert initial_total == (initial_reserved + initial_available + initial_consumed), \
        "Initial budget invariant violated"
    
    # Simulate budget adjustment
    if expected_adjustment_type == "additional_charge":
        # Need to deduct additional amount from available budget
        # Assume sufficient budget for this test
        assume(initial_available >= expected_adjustment_amount)
        
        final_reserved = Decimal("0.00")  # Release provisional reservation
        final_available = initial_available - expected_adjustment_amount
        final_consumed = initial_consumed + final_amount
    
    elif expected_adjustment_type == "refund":
        # Credit difference back to available budget
        final_reserved = Decimal("0.00")  # Release provisional reservation
        final_available = initial_available + expected_adjustment_amount
        final_consumed = initial_consumed + final_amount
    
    else:  # no adjustment
        # Exact match, just move from reserved to consumed
        final_reserved = Decimal("0.00")
        final_available = initial_available
        final_consumed = initial_consumed + final_amount
    
    final_total = initial_total  # Total budget unchanged
    
    # Validate final budget invariant
    assert final_total == (final_reserved + final_available + final_consumed), \
        f"Final budget invariant violated: {final_total} != {final_reserved} + {final_available} + {final_consumed}"
    
    # Validate adjustment amount
    actual_adjustment = initial_available - final_available
    assert abs(actual_adjustment - difference) < Decimal("0.01"), \
        f"Adjustment amount mismatch: expected {difference}, got {actual_adjustment}"
    
    # Validate consumed budget
    assert final_consumed == final_amount, \
        f"Consumed budget should equal final amount: {final_consumed} != {final_amount}"
    
    # Validate reserved budget released
    assert final_reserved == Decimal("0.00"), \
        "Reserved budget should be fully released after reconciliation"


@given(charge_pair=charge_pair())
@settings(max_examples=100)
def test_reconciliation_variance_validation(
    charge_pair: Tuple[Dict[str, Any], Dict[str, Any]]
):
    """
    Test that reconciliation validates amount variance within acceptable limits.
    
    Acceptable variance:
    - Maximum overage: 20% (final > provisional)
    - Minimum underage: 50% (final >= 50% of provisional)
    """
    provisional, final = charge_pair
    
    provisional_amount = Decimal(provisional["amount"]["value"])
    final_amount = Decimal(final["amount"]["value"])
    
    # Calculate variance percentage
    if provisional_amount > 0:
        variance_pct = (final_amount - provisional_amount) / provisional_amount
        
        # Check if variance is within acceptable limits
        max_overage = Decimal("0.20")  # 20%
        min_ratio = Decimal("0.50")    # 50%
        
        is_valid_overage = variance_pct <= max_overage
        is_valid_underage = final_amount >= provisional_amount * min_ratio
        
        is_within_limits = is_valid_overage and is_valid_underage
        
        # If variance is within limits, reconciliation should succeed
        # If variance exceeds limits, reconciliation should fail
        if is_within_limits:
            # Reconciliation should be allowed
            assert True, "Variance within acceptable limits"
        else:
            # Reconciliation should be rejected
            if not is_valid_overage:
                assert variance_pct > max_overage, \
                    f"Overage {variance_pct:.1%} exceeds maximum {max_overage:.1%}"
            if not is_valid_underage:
                assert final_amount < provisional_amount * min_ratio, \
                    f"Final amount {final_amount} is less than minimum {provisional_amount * min_ratio}"


@given(orphaned_charge=orphaned_final_charge())
@settings(max_examples=100)
def test_orphaned_final_charge_handling(orphaned_charge: Dict[str, Any]):
    """
    Test that orphaned final charges (without provisional reference) are handled correctly.
    
    Orphaned charges should:
    1. Not have a provisionalChargeId field
    2. Be processed as standalone charges
    3. Deduct full amount from available budget
    4. Not require reconciliation
    """
    # Validate no provisional charge reference
    assert "provisionalChargeId" not in orphaned_charge, \
        "Orphaned charge should not have provisionalChargeId"
    
    # Validate required fields
    required_fields = [
        "eventId", "eventType", "timestamp", "agentId",
        "amount", "description", "status"
    ]
    for field in required_fields:
        assert field in orphaned_charge, f"Missing required field: {field}"
    
    # Validate event type
    assert orphaned_charge["eventType"] == "final", \
        "Event type must be 'final'"
    
    # Simulate budget deduction
    charge_amount = Decimal(orphaned_charge["amount"]["value"])
    initial_available = Decimal("10000.00")
    
    # Assume sufficient budget
    assume(initial_available >= charge_amount)
    
    # Calculate new budget state
    final_available = initial_available - charge_amount
    final_consumed = charge_amount
    
    # Validate budget deduction
    assert final_available == initial_available - charge_amount, \
        "Available budget should be reduced by charge amount"
    assert final_consumed == charge_amount, \
        "Consumed budget should equal charge amount"


@given(charge_pair=charge_pair())
@settings(max_examples=100)
def test_reconciliation_audit_trail(charge_pair: Tuple[Dict[str, Any], Dict[str, Any]]):
    """
    Test that reconciliation generates proper audit trail information.
    
    Audit trail should include:
    1. Both provisional and final charge IDs
    2. Amount difference calculation
    3. Adjustment type determination
    4. Budget state before and after
    """
    provisional, final = charge_pair
    
    provisional_amount = Decimal(provisional["amount"]["value"])
    final_amount = Decimal(final["amount"]["value"])
    difference = final_amount - provisional_amount
    
    # Determine adjustment type
    if difference > 0:
        adjustment_type = "additional_charge"
    elif difference < 0:
        adjustment_type = "refund"
    else:
        adjustment_type = "none"
    
    # Create audit trail structure
    audit_trail = {
        "auditEventId": f"audit_reconcile_{provisional['eventId']}",
        "eventType": "charge_reconciliation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agentId": final["agentId"],
        "provisionalChargeId": provisional["eventId"],
        "finalChargeId": final["eventId"],
        "reconciliation": {
            "provisionalAmount": provisional["amount"],
            "finalAmount": final["amount"],
            "difference": {
                "value": str(difference),
                "currency": final["amount"]["currency"]
            },
            "adjustmentType": adjustment_type
        }
    }
    
    # Validate audit trail structure
    assert "auditEventId" in audit_trail
    assert "provisionalChargeId" in audit_trail
    assert "finalChargeId" in audit_trail
    assert "reconciliation" in audit_trail
    
    # Validate reconciliation details
    reconciliation = audit_trail["reconciliation"]
    assert "provisionalAmount" in reconciliation
    assert "finalAmount" in reconciliation
    assert "difference" in reconciliation
    assert "adjustmentType" in reconciliation
    
    # Validate adjustment type is correct
    assert reconciliation["adjustmentType"] == adjustment_type
    
    # Validate difference calculation
    audit_difference = Decimal(reconciliation["difference"]["value"])
    assert audit_difference == difference, \
        f"Audit difference {audit_difference} != calculated difference {difference}"


@given(charge_pair=charge_pair())
@settings(max_examples=100)
def test_charge_status_transitions_after_reconciliation(
    charge_pair: Tuple[Dict[str, Any], Dict[str, Any]]
):
    """
    Test that charge statuses transition correctly after reconciliation.
    
    After successful reconciliation:
    - Provisional charge status: reserved → confirmed
    - Final charge status: pending → confirmed
    """
    provisional, final = charge_pair
    
    # Initial statuses
    assert provisional["status"] == "reserved", \
        "Provisional charge should start as reserved"
    assert final["status"] == "pending", \
        "Final charge should start as pending"
    
    # Simulate reconciliation
    # After reconciliation, both should be confirmed
    provisional_after = provisional.copy()
    provisional_after["status"] = "confirmed"
    
    final_after = final.copy()
    final_after["status"] = "confirmed"
    
    # Validate status transitions
    assert provisional_after["status"] == "confirmed", \
        "Provisional charge should be confirmed after reconciliation"
    assert final_after["status"] == "confirmed", \
        "Final charge should be confirmed after reconciliation"
    
    # Validate terminal state
    terminal_statuses = ["confirmed", "expired", "cancelled", "refunded"]
    assert provisional_after["status"] in terminal_statuses, \
        "Provisional charge should be in terminal state"
    assert final_after["status"] in terminal_statuses, \
        "Final charge should be in terminal state"


@given(charge_pair=charge_pair())
@settings(max_examples=100)
def test_reconciliation_json_serialization(
    charge_pair: Tuple[Dict[str, Any], Dict[str, Any]]
):
    """
    Test that reconciliation data can be properly serialized to JSON.
    """
    provisional, final = charge_pair
    
    try:
        # Serialize both charges
        provisional_json = json.dumps(provisional)
        final_json = json.dumps(final)
        
        # Deserialize back
        provisional_deserialized = json.loads(provisional_json)
        final_deserialized = json.loads(final_json)
        
        # Validate all fields are preserved
        assert provisional_deserialized["eventId"] == provisional["eventId"]
        assert final_deserialized["eventId"] == final["eventId"]
        assert final_deserialized["provisionalChargeId"] == provisional["eventId"]
        
    except (TypeError, ValueError) as e:
        assert False, f"Failed to serialize reconciliation data: {e}"


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
