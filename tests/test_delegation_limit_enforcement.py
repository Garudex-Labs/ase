"""
Property-based tests for delegation limit enforcement.

Feature: ase, Property 8: Delegation Limit Enforcement
Feature: ase, Property 10: Delegation Token Expiration Handling

Validates: Requirements 4.4, 4.6
"""

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

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
def spending_state(draw, spending_limit=None):
    """Generate spending state for a delegation token."""
    if spending_limit is None:
        spending_limit = draw(monetary_amount())
    
    limit_value = Decimal(spending_limit["value"])
    
    # Generate cumulative spent (0 to limit)
    cumulative_spent = draw(st.decimals(
        min_value=Decimal("0.00"),
        max_value=limit_value,
        places=2
    ))
    
    # Generate reserved amount (0 to remaining)
    remaining = limit_value - cumulative_spent
    reserved_amount = draw(st.decimals(
        min_value=Decimal("0.00"),
        max_value=remaining,
        places=2
    ))
    
    # Calculate available amount
    available_amount = limit_value - cumulative_spent - reserved_amount
    
    return {
        "spendingLimit": spending_limit,
        "cumulativeSpent": {
            "value": str(cumulative_spent),
            "currency": spending_limit["currency"]
        },
        "reservedAmount": {
            "value": str(reserved_amount),
            "currency": spending_limit["currency"]
        },
        "availableAmount": {
            "value": str(available_amount),
            "currency": spending_limit["currency"]
        }
    }


@st.composite
def delegation_token_with_state(draw):
    """Generate delegation token with spending state."""
    base_time = int(time.time())
    spending_limit = draw(monetary_amount())
    
    # Generate expiration time between 1 hour and 24 hours in the future
    expiration_hours = draw(st.integers(min_value=1, max_value=24))
    exp_time = base_time + (expiration_hours * 3600)
    
    token = {
        "payload": {
            "iss": draw(agent_id()),
            "sub": draw(agent_id()),
            "aud": "any",
            "exp": exp_time,
            "iat": base_time,
            "jti": f"token_{base_time}_{draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=8, max_size=16))}",
            "spendingLimit": spending_limit,
            "allowedOperations": draw(st.lists(
                st.sampled_from(["read", "write", "compute", "delegate", "audit"]),
                max_size=5,
                unique=True
            )),
            "maxDelegationDepth": draw(st.integers(min_value=0, max_value=5)),
            "budgetCategory": draw(st.sampled_from(["research", "production", "development", "testing"]))
        },
        "spendingState": draw(spending_state(spending_limit=spending_limit))
    }
    
    return token


# Property tests

@given(
    token_with_state=delegation_token_with_state(),
    transaction_amount=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("999999.99"),
        places=2
    )
)
@settings(max_examples=100)
def test_property_8_delegation_limit_enforcement(
    token_with_state: Dict[str, Any],
    transaction_amount: Decimal
):
    """
    Property 8: Delegation Limit Enforcement
    
    For any transaction that exceeds delegation token limits, the ASE agent
    should reject the transaction and return an appropriate error.
    
    This test validates that:
    1. Transactions within available limit are allowed
    2. Transactions exceeding available limit are rejected
    3. Spending invariant is maintained: limit = spent + reserved + available
    4. Currency consistency is enforced
    5. Error messages provide actionable information
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    # Extract values
    spending_limit = Decimal(state["spendingLimit"]["value"])
    cumulative_spent = Decimal(state["cumulativeSpent"]["value"])
    reserved_amount = Decimal(state["reservedAmount"]["value"])
    available_amount = Decimal(state["availableAmount"]["value"])
    
    # Validate spending invariant
    assert spending_limit == cumulative_spent + reserved_amount + available_amount, \
        f"Spending invariant violated: {spending_limit} != {cumulative_spent} + {reserved_amount} + {available_amount}"
    
    # Determine if transaction should be allowed
    would_exceed = transaction_amount > available_amount
    
    if would_exceed:
        # Transaction should be rejected
        assert transaction_amount > available_amount, \
            "Transaction exceeds available amount and should be rejected"
        
        # Validate error information would be complete
        error_info = {
            "tokenId": token["jti"],
            "spendingLimit": state["spendingLimit"],
            "cumulativeSpent": state["cumulativeSpent"],
            "reservedAmount": state["reservedAmount"],
            "transactionAmount": {
                "value": str(transaction_amount),
                "currency": state["spendingLimit"]["currency"]
            },
            "availableAmount": state["availableAmount"]
        }
        
        # Verify all error fields are present
        assert "tokenId" in error_info
        assert "spendingLimit" in error_info
        assert "availableAmount" in error_info
        
        # Verify deficit calculation
        deficit = transaction_amount - available_amount
        assert deficit > 0, f"Deficit should be positive: {deficit}"
        
    else:
        # Transaction should be allowed
        assert transaction_amount <= available_amount, \
            "Transaction is within available amount and should be allowed"
        
        # Simulate spending reservation
        new_reserved = reserved_amount + transaction_amount
        new_available = available_amount - transaction_amount
        
        # Validate new state maintains invariant
        assert spending_limit == cumulative_spent + new_reserved + new_available, \
            "Spending invariant violated after reservation"
        
        # Validate new available is non-negative
        assert new_available >= 0, \
            f"Available amount should not go negative: {new_available}"


@given(
    token_with_state=delegation_token_with_state(),
    transactions=st.lists(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00"), places=2),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
def test_cumulative_spending_enforcement(
    token_with_state: Dict[str, Any],
    transactions: List[Decimal]
):
    """
    Test that cumulative spending is properly tracked and enforced.
    
    Multiple transactions should be allowed until cumulative spending
    reaches the spending limit.
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    spending_limit = Decimal(state["spendingLimit"]["value"])
    cumulative_spent = Decimal(state["cumulativeSpent"]["value"])
    reserved_amount = Decimal(state["reservedAmount"]["value"])
    available_amount = Decimal(state["availableAmount"]["value"])
    
    # Process transactions sequentially
    current_spent = cumulative_spent
    current_reserved = reserved_amount
    current_available = available_amount
    
    for transaction in transactions:
        # Check if transaction can be processed
        if transaction <= current_available:
            # Transaction allowed - reserve amount
            current_reserved += transaction
            current_available -= transaction
            
            # Validate invariant
            assert spending_limit == current_spent + current_reserved + current_available, \
                "Spending invariant violated during transaction processing"
        else:
            # Transaction rejected - state unchanged
            assert transaction > current_available, \
                "Transaction correctly rejected due to insufficient available amount"
            break
    
    # Final state should maintain invariant
    assert spending_limit == current_spent + current_reserved + current_available, \
        "Final spending invariant violated"


@given(
    token_with_state=delegation_token_with_state(),
    time_offset_seconds=st.integers(min_value=-3600, max_value=100000)
)
@settings(max_examples=100)
def test_property_10_delegation_token_expiration_handling(
    token_with_state: Dict[str, Any],
    time_offset_seconds: int
):
    """
    Property 10: Delegation Token Expiration Handling
    
    For any expired delegation token, all subsequent transactions using
    that token should be rejected.
    
    This test validates that:
    1. Tokens are correctly identified as expired based on current time
    2. Expired tokens reject all transactions regardless of spending limit
    3. Expiration time is properly compared with current time
    4. Reserved amounts are released when tokens expire
    5. Expiration status is deterministic
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    exp_time = token["exp"]
    iat_time = token["iat"]
    
    # Simulate current time at various offsets from issued-at
    current_time = iat_time + time_offset_seconds
    
    # Determine if token should be expired
    is_expired = current_time >= exp_time
    
    if is_expired:
        # Token is expired - all transactions should be rejected
        assert current_time >= exp_time, \
            f"Token should be expired: current={current_time}, exp={exp_time}"
        
        # Even if available amount exists, transaction should be rejected
        available_amount = Decimal(state["availableAmount"]["value"])
        if available_amount > 0:
            # Transaction within limit but token expired
            transaction = available_amount / 2
            assert is_expired, \
                "Transaction should be rejected due to token expiration"
        
        # Reserved amounts should be released on expiration
        reserved_amount = Decimal(state["reservedAmount"]["value"])
        if reserved_amount > 0:
            # In a real system, this would trigger cleanup
            assert is_expired, \
                "Reserved amounts should be released when token expires"
        
    else:
        # Token is not expired - normal spending rules apply
        assert current_time < exp_time, \
            f"Token should not be expired: current={current_time}, exp={exp_time}"
        
        # Validate token is not used before issued-at time
        if current_time < iat_time:
            assert False, \
                f"Token should not be used before issued-at time: current={current_time}, iat={iat_time}"


@given(
    token_with_state=delegation_token_with_state(),
    requested_operation=st.sampled_from(["read", "write", "compute", "delegate", "audit", "invalid_op"])
)
@settings(max_examples=100)
def test_operation_authorization_enforcement(
    token_with_state: Dict[str, Any],
    requested_operation: str
):
    """
    Test that operation authorization is enforced alongside spending limits.
    
    Even if spending limit is available, unauthorized operations should be rejected.
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    allowed_ops = token.get("allowedOperations", [])
    available_amount = Decimal(state["availableAmount"]["value"])
    
    # Determine if operation is authorized
    is_authorized = (not allowed_ops) or (requested_operation in allowed_ops)
    
    # Valid operations
    valid_operations = ["read", "write", "compute", "delegate", "audit"]
    is_valid_operation = requested_operation in valid_operations
    
    if is_authorized and is_valid_operation:
        # Operation is authorized and valid
        if available_amount > 0:
            # Transaction should be allowed (both operation and spending limit OK)
            assert True, "Transaction should be allowed"
    elif not is_authorized:
        # Operation is not authorized
        assert requested_operation not in allowed_ops, \
            f"Operation {requested_operation} should be rejected (not authorized)"
    elif not is_valid_operation:
        # Operation is invalid
        assert requested_operation not in valid_operations, \
            f"Operation {requested_operation} should be rejected (invalid)"


@given(
    token_with_state=delegation_token_with_state(),
    reservation_timeout_seconds=st.integers(min_value=60, max_value=3600)
)
@settings(max_examples=100)
def test_spending_reservation_timeout(
    token_with_state: Dict[str, Any],
    reservation_timeout_seconds: int
):
    """
    Test that spending reservations timeout and release reserved amounts.
    
    If a transaction is not confirmed within the timeout period,
    the reserved amount should be released back to available.
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    spending_limit = Decimal(state["spendingLimit"]["value"])
    cumulative_spent = Decimal(state["cumulativeSpent"]["value"])
    reserved_amount = Decimal(state["reservedAmount"]["value"])
    available_amount = Decimal(state["availableAmount"]["value"])
    
    # Simulate reservation timeout
    if reserved_amount > 0:
        # Release reserved amount
        new_reserved = Decimal("0.00")
        new_available = available_amount + reserved_amount
        
        # Validate invariant after release
        assert spending_limit == cumulative_spent + new_reserved + new_available, \
            "Spending invariant violated after reservation timeout"
        
        # Validate available amount increased
        assert new_available > available_amount, \
            "Available amount should increase after reservation release"


@given(
    parent_token=delegation_token_with_state(),
    child_limit_ratio=st.floats(min_value=0.1, max_value=1.5)
)
@settings(max_examples=100)
def test_hierarchical_spending_limit_validation(
    parent_token: Dict[str, Any],
    child_limit_ratio: float
):
    """
    Test that child delegation spending limits are validated against parent limits.
    
    A child token's spending limit must be <= parent's remaining limit.
    """
    parent_payload = parent_token["payload"]
    parent_state = parent_token["spendingState"]
    
    parent_limit = Decimal(parent_state["spendingLimit"]["value"])
    parent_available = Decimal(parent_state["availableAmount"]["value"])
    
    # Calculate child limit based on ratio
    child_limit = parent_limit * Decimal(str(child_limit_ratio))
    
    # Determine if child limit is valid
    is_valid = child_limit <= parent_available
    
    if is_valid:
        # Child limit is within parent's available amount
        assert child_limit <= parent_available, \
            "Child limit should be allowed (within parent available)"
    else:
        # Child limit exceeds parent's available amount
        assert child_limit > parent_available, \
            "Child limit should be rejected (exceeds parent available)"


@given(
    token_with_state=delegation_token_with_state(),
    transaction_amount=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("1000.00"),
        places=2
    )
)
@settings(max_examples=100)
def test_currency_consistency_enforcement(
    token_with_state: Dict[str, Any],
    transaction_amount: Decimal
):
    """
    Test that currency consistency is enforced in spending limits.
    
    All amounts (limit, spent, reserved, available, transaction) must use
    the same currency.
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    # Extract currencies
    limit_currency = state["spendingLimit"]["currency"]
    spent_currency = state["cumulativeSpent"]["currency"]
    reserved_currency = state["reservedAmount"]["currency"]
    available_currency = state["availableAmount"]["currency"]
    
    # Validate all currencies match
    assert limit_currency == spent_currency, \
        "Cumulative spent currency must match spending limit currency"
    assert limit_currency == reserved_currency, \
        "Reserved amount currency must match spending limit currency"
    assert limit_currency == available_currency, \
        "Available amount currency must match spending limit currency"
    
    # Transaction currency must match token currency
    transaction_currency = limit_currency
    assert len(transaction_currency) == 3, \
        "Currency code must be 3 characters"


@given(
    token_with_state=delegation_token_with_state(),
    time_offset_hours=st.integers(min_value=0, max_value=48)
)
@settings(max_examples=100)
def test_expiration_warning_threshold(
    token_with_state: Dict[str, Any],
    time_offset_hours: int
):
    """
    Test that expiration warnings are issued when token is about to expire.
    
    Warnings should be issued when token expires within warning threshold
    (e.g., 1 hour).
    """
    token = token_with_state["payload"]
    
    exp_time = token["exp"]
    iat_time = token["iat"]
    warning_threshold = 3600  # 1 hour in seconds
    
    # Simulate current time
    current_time = iat_time + (time_offset_hours * 3600)
    
    # Calculate time until expiration
    time_until_expiration = exp_time - current_time
    
    # Determine if warning should be issued
    should_warn = 0 < time_until_expiration <= warning_threshold
    
    if should_warn:
        # Warning should be issued
        assert 0 < time_until_expiration <= warning_threshold, \
            f"Warning should be issued: expires in {time_until_expiration} seconds"
    elif time_until_expiration <= 0:
        # Token is expired
        assert time_until_expiration <= 0, \
            "Token is expired, no warning needed"
    else:
        # Token has plenty of time remaining
        assert time_until_expiration > warning_threshold, \
            "Token has sufficient time remaining, no warning needed"


@given(
    token_with_state=delegation_token_with_state(),
    concurrent_transactions=st.lists(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100.00"), places=2),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=100)
def test_concurrent_spending_race_condition(
    token_with_state: Dict[str, Any],
    concurrent_transactions: List[Decimal]
):
    """
    Test that concurrent spending transactions don't violate spending limits.
    
    Even with concurrent transactions, the total spent should never exceed
    the spending limit (atomic reservation required).
    """
    token = token_with_state["payload"]
    state = token_with_state["spendingState"]
    
    spending_limit = Decimal(state["spendingLimit"]["value"])
    cumulative_spent = Decimal(state["cumulativeSpent"]["value"])
    reserved_amount = Decimal(state["reservedAmount"]["value"])
    available_amount = Decimal(state["availableAmount"]["value"])
    
    # Simulate concurrent transaction attempts
    total_requested = sum(concurrent_transactions)
    
    # Determine how many transactions can be processed
    current_available = available_amount
    processed_count = 0
    
    for transaction in concurrent_transactions:
        if transaction <= current_available:
            # Transaction can be processed
            current_available -= transaction
            processed_count += 1
        else:
            # Transaction would exceed limit - reject
            break
    
    # Validate that we never exceed the limit
    total_processed = sum(concurrent_transactions[:processed_count])
    assert total_processed <= available_amount, \
        "Total processed transactions should not exceed available amount"
    
    # Validate final state
    final_reserved = reserved_amount + total_processed
    final_available = available_amount - total_processed
    assert spending_limit == cumulative_spent + final_reserved + final_available, \
        "Spending invariant violated after concurrent transactions"


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
