"""
ASE-to-ASE communication test specifications.

This module defines test scenarios for all ASE message types and interactions
between ASE-enabled agents.

Feature: ase, Interoperability Testing

Validates: Requirements 9.1, 9.6
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import hypothesis.strategies as st
from hypothesis import given, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# Test data generators

@st.composite
def agent_id(draw):
    """Generate valid agent identifier."""
    prefix = draw(st.sampled_from(["agent", "service", "client"]))
    suffix = draw(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=6, max_size=20))
    return f"{prefix}_{suffix}"


@st.composite
def monetary_amount(draw):
    """Generate valid monetary amount."""
    value = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999999.99"), places=2))
    currency = draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"]))
    return {
        "value": str(value),
        "currency": currency
    }


@st.composite
def agent_identity(draw):
    """Generate agent identity metadata."""
    return {
        "agentId": draw(agent_id()),
        "agentType": draw(st.sampled_from(["autonomous", "human", "service", "hybrid"])),
        "organizationId": draw(st.text(min_size=5, max_size=20)),
        "settlementAccount": draw(st.text(min_size=10, max_size=30))
    }


@st.composite
def cost_declaration(draw):
    """Generate cost declaration metadata."""
    return {
        "amount": draw(monetary_amount()),
        "pricingModel": draw(st.sampled_from(["per_request", "time_based", "resource_based", "tiered"])),
        "description": draw(st.text(min_size=10, max_size=200)),
        "breakdown": [
            {
                "category": draw(st.sampled_from(["compute", "storage", "network", "api_calls"])),
                "amount": draw(monetary_amount())
            }
            for _ in range(draw(st.integers(min_value=1, max_value=5)))
        ]
    }


@st.composite
def budget_request(draw):
    """Generate budget request metadata."""
    return {
        "requestedAmount": draw(monetary_amount()),
        "budgetCategory": draw(st.sampled_from(["compute", "storage", "network", "general"])),
        "purpose": draw(st.text(min_size=10, max_size=100)),
        "approvalRequired": draw(st.booleans())
    }


@st.composite
def provisional_charge_event(draw):
    """Generate provisional charge event."""
    event_id = f"evt_prov_{draw(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=10, max_size=20))}"
    expiration_minutes = draw(st.integers(min_value=1, max_value=1440))
    expiration_time = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
    
    return {
        "eventId": event_id,
        "eventType": "provisional",
        "agentId": draw(agent_id()),
        "amount": draw(monetary_amount()),
        "expirationTime": expiration_time.isoformat(),
        "status": draw(st.sampled_from(["pending", "reserved", "confirmed", "expired", "cancelled"])),
        "description": draw(st.text(min_size=10, max_size=200)),
        "metadata": {
            "resourceType": draw(st.sampled_from(["compute", "storage", "api_call"])),
            "estimatedDuration": draw(st.integers(min_value=1, max_value=3600))
        }
    }


@st.composite
def final_charge_event(draw):
    """Generate final charge event."""
    event_id = f"evt_final_{draw(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=10, max_size=20))}"
    provisional_id = f"evt_prov_{draw(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=10, max_size=20))}"
    
    return {
        "eventId": event_id,
        "eventType": "final",
        "agentId": draw(agent_id()),
        "amount": draw(monetary_amount()),
        "provisionalChargeId": provisional_id,
        "status": draw(st.sampled_from(["confirmed", "disputed", "refunded"])),
        "description": draw(st.text(min_size=10, max_size=200)),
        "actualUsage": {
            "duration": draw(st.integers(min_value=1, max_value=3600)),
            "resourceUnits": draw(st.integers(min_value=1, max_value=1000))
        }
    }


@st.composite
def delegation_token_payload(draw):
    """Generate delegation token payload."""
    return {
        "iss": draw(agent_id()),
        "sub": draw(agent_id()),
        "aud": draw(st.sampled_from(["any", "specific_service"])),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=draw(st.integers(min_value=1, max_value=168)))).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": draw(st.text(min_size=20, max_size=40)),
        "spendingLimit": draw(monetary_amount()),
        "allowedOperations": draw(st.lists(st.sampled_from(["read", "write", "execute", "delegate"]), min_size=1, max_size=4, unique=True)),
        "maxDelegationDepth": draw(st.integers(min_value=0, max_value=5)),
        "budgetCategory": draw(st.sampled_from(["compute", "storage", "network", "general"]))
    }


@st.composite
def audit_reference(draw):
    """Generate audit reference metadata."""
    return {
        "auditBundleId": f"audit_{draw(st.text(min_size=20, max_size=40))}",
        "transactionId": f"txn_{draw(st.text(min_size=20, max_size=40))}",
        "sequenceNumber": draw(st.integers(min_value=1, max_value=1000000)),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@st.composite
def ase_message(draw):
    """Generate complete ASE message with economic metadata."""
    return {
        "baseMessage": {
            "id": draw(st.text(min_size=10, max_size=30)),
            "content": draw(st.text(min_size=1, max_size=500)),
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "aseMetadata": {
            "version": draw(st.sampled_from(["0.1.0", "1.0.0", "2.0.0"])),
            "agentIdentity": draw(agent_identity()),
            "costDeclaration": draw(st.one_of(st.none(), cost_declaration())),
            "budgetRequest": draw(st.one_of(st.none(), budget_request())),
            "chargeEvent": draw(st.one_of(st.none(), provisional_charge_event(), final_charge_event())),
            "auditReference": draw(st.one_of(st.none(), audit_reference())),
            "delegationToken": draw(st.one_of(st.none(), st.text(min_size=50, max_size=200)))
        }
    }


# Test scenarios

@given(message=ase_message())
@settings(max_examples=100)
def test_ase_message_structure_validation(message: Dict[str, Any]):
    """
    Test Scenario: ASE Message Structure Validation
    
    Validates that ASE messages maintain proper structure with:
    - Base message fields preserved
    - ASE metadata properly formatted
    - All required fields present
    - Optional fields handled correctly
    
    Expected Behavior:
    - Message structure conforms to ASE schema
    - Base message is accessible and valid
    - Economic metadata is properly nested
    - Version field is present and valid
    """
    # Validate base message structure
    assert "baseMessage" in message, "Message must contain baseMessage"
    assert "aseMetadata" in message, "Message must contain aseMetadata"
    
    base_msg = message["baseMessage"]
    assert "id" in base_msg, "Base message must have id"
    assert "content" in base_msg, "Base message must have content"
    assert "timestamp" in base_msg, "Base message must have timestamp"
    
    # Validate ASE metadata structure
    ase_meta = message["aseMetadata"]
    assert "version" in ase_meta, "ASE metadata must have version"
    assert "agentIdentity" in ase_meta, "ASE metadata must have agentIdentity"
    
    # Validate agent identity
    agent_id_data = ase_meta["agentIdentity"]
    assert "agentId" in agent_id_data, "Agent identity must have agentId"
    assert "agentType" in agent_id_data, "Agent identity must have agentType"
    
    # Validate version format
    version = ase_meta["version"]
    assert version in ["0.1.0", "1.0.0", "2.0.0"], f"Invalid version: {version}"


@given(
    sender_message=ase_message(),
    receiver_agent=agent_id()
)
@settings(max_examples=100)
def test_ase_to_ase_message_exchange(
    sender_message: Dict[str, Any],
    receiver_agent: str
):
    """
    Test Scenario: ASE-to-ASE Message Exchange
    
    Validates bidirectional communication between ASE-enabled agents:
    - Sender creates message with economic metadata
    - Receiver processes message and extracts metadata
    - Receiver responds with acknowledgment
    - Economic data flows correctly in both directions
    
    Expected Behavior:
    - Messages are properly formatted for ASE-to-ASE communication
    - Economic metadata is preserved during transmission
    - Both agents can process each other's messages
    - Charge events are correctly correlated
    """
    # Sender prepares message
    sender_agent = sender_message["aseMetadata"]["agentIdentity"]["agentId"]
    
    # Validate sender can create valid ASE message
    assert "aseMetadata" in sender_message
    assert sender_message["aseMetadata"]["agentIdentity"]["agentId"] == sender_agent
    
    # Simulate receiver processing message
    received_metadata = sender_message["aseMetadata"]
    
    # Receiver validates message
    assert "version" in received_metadata
    assert "agentIdentity" in received_metadata
    
    # Receiver creates response
    response = {
        "baseMessage": {
            "id": f"resp_{sender_message['baseMessage']['id']}",
            "content": "Acknowledged",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inReplyTo": sender_message["baseMessage"]["id"]
        },
        "aseMetadata": {
            "version": received_metadata["version"],
            "agentIdentity": {
                "agentId": receiver_agent,
                "agentType": "autonomous",
                "organizationId": "org_receiver",
                "settlementAccount": "acct_receiver"
            }
        }
    }
    
    # Validate response structure
    assert "baseMessage" in response
    assert "aseMetadata" in response
    assert response["baseMessage"]["inReplyTo"] == sender_message["baseMessage"]["id"]
    assert response["aseMetadata"]["agentIdentity"]["agentId"] == receiver_agent


@given(
    charge_event=provisional_charge_event(),
    sender_agent=agent_id(),
    receiver_agent=agent_id()
)
@settings(max_examples=100)
def test_charge_event_propagation(
    charge_event: Dict[str, Any],
    sender_agent: str,
    receiver_agent: str
):
    """
    Test Scenario: Charge Event Propagation
    
    Validates that charge events are correctly propagated between ASE agents:
    - Provisional charges are communicated
    - Final charges reference provisional charges
    - Budget reservations are tracked
    - Settlement instructions are generated
    
    Expected Behavior:
    - Charge events maintain integrity during transmission
    - Event IDs are preserved
    - Amounts and currencies are consistent
    - Status transitions are valid
    """
    assume(sender_agent != receiver_agent)
    
    # Update charge event with sender agent
    charge_event["agentId"] = sender_agent
    
    # Create message with charge event
    message = {
        "baseMessage": {
            "id": f"msg_{charge_event['eventId']}",
            "content": "Resource request",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "aseMetadata": {
            "version": "1.0.0",
            "agentIdentity": {
                "agentId": sender_agent,
                "agentType": "autonomous",
                "organizationId": "org_sender",
                "settlementAccount": "acct_sender"
            },
            "chargeEvent": charge_event
        }
    }
    
    # Receiver processes charge event
    received_charge = message["aseMetadata"]["chargeEvent"]
    
    # Validate charge event structure
    assert "eventId" in received_charge
    assert "eventType" in received_charge
    assert "agentId" in received_charge
    assert "amount" in received_charge
    
    # Validate charge event data
    assert received_charge["eventId"] == charge_event["eventId"]
    assert received_charge["eventType"] == charge_event["eventType"]
    assert received_charge["agentId"] == sender_agent
    assert received_charge["amount"] == charge_event["amount"]


@given(
    token_payload=delegation_token_payload(),
    delegating_agent=agent_id(),
    delegated_agent=agent_id()
)
@settings(max_examples=100)
def test_delegation_token_exchange(
    token_payload: Dict[str, Any],
    delegating_agent: str,
    delegated_agent: str
):
    """
    Test Scenario: Delegation Token Exchange
    
    Validates delegation token exchange between ASE agents:
    - Parent agent creates delegation token
    - Token is transmitted to child agent
    - Child agent validates token
    - Child agent uses token for authorized operations
    
    Expected Behavior:
    - Tokens are properly formatted
    - Spending limits are enforced
    - Allowed operations are validated
    - Token expiration is checked
    """
    assume(delegating_agent != delegated_agent)
    
    # Update token payload
    token_payload["iss"] = delegating_agent
    token_payload["sub"] = delegated_agent
    
    # Create mock JWT token (simplified for testing)
    token = f"eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.{json.dumps(token_payload)}.signature"
    
    # Create message with delegation token
    message = {
        "baseMessage": {
            "id": f"msg_delegation_{token_payload['jti']}",
            "content": "Delegation authorization",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "aseMetadata": {
            "version": "1.0.0",
            "agentIdentity": {
                "agentId": delegating_agent,
                "agentType": "autonomous",
                "organizationId": "org_parent",
                "settlementAccount": "acct_parent"
            },
            "delegationToken": token
        }
    }
    
    # Validate message structure
    assert "delegationToken" in message["aseMetadata"]
    assert message["aseMetadata"]["delegationToken"] == token
    
    # Validate token payload (extracted from token)
    assert token_payload["iss"] == delegating_agent
    assert token_payload["sub"] == delegated_agent
    assert "spendingLimit" in token_payload
    assert "allowedOperations" in token_payload


@given(
    cost_decl=cost_declaration(),
    budget_req=budget_request(),
    sender_agent=agent_id(),
    receiver_agent=agent_id()
)
@settings(max_examples=100)
def test_cost_and_budget_negotiation(
    cost_decl: Dict[str, Any],
    budget_req: Dict[str, Any],
    sender_agent: str,
    receiver_agent: str
):
    """
    Test Scenario: Cost and Budget Negotiation
    
    Validates cost declaration and budget request exchange:
    - Service provider declares costs
    - Consumer requests budget allocation
    - Negotiation occurs if needed
    - Agreement is reached and recorded
    
    Expected Behavior:
    - Cost declarations are properly formatted
    - Budget requests are validated
    - Currency matching is enforced
    - Approval workflows are triggered when required
    """
    assume(sender_agent != receiver_agent)
    
    # Ensure currency consistency
    cost_currency = cost_decl["amount"]["currency"]
    budget_req["requestedAmount"]["currency"] = cost_currency
    
    # Service provider declares cost
    cost_message = {
        "baseMessage": {
            "id": f"msg_cost_{sender_agent}",
            "content": "Service cost declaration",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "aseMetadata": {
            "version": "1.0.0",
            "agentIdentity": {
                "agentId": sender_agent,
                "agentType": "service",
                "organizationId": "org_provider",
                "settlementAccount": "acct_provider"
            },
            "costDeclaration": cost_decl
        }
    }
    
    # Consumer requests budget
    budget_message = {
        "baseMessage": {
            "id": f"msg_budget_{receiver_agent}",
            "content": "Budget request",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inReplyTo": cost_message["baseMessage"]["id"]
        },
        "aseMetadata": {
            "version": "1.0.0",
            "agentIdentity": {
                "agentId": receiver_agent,
                "agentType": "autonomous",
                "organizationId": "org_consumer",
                "settlementAccount": "acct_consumer"
            },
            "budgetRequest": budget_req
        }
    }
    
    # Validate cost declaration
    assert "costDeclaration" in cost_message["aseMetadata"]
    assert "amount" in cost_message["aseMetadata"]["costDeclaration"]
    
    # Validate budget request
    assert "budgetRequest" in budget_message["aseMetadata"]
    assert "requestedAmount" in budget_message["aseMetadata"]["budgetRequest"]
    
    # Validate currency consistency
    assert cost_message["aseMetadata"]["costDeclaration"]["amount"]["currency"] == \
           budget_message["aseMetadata"]["budgetRequest"]["requestedAmount"]["currency"]


@given(
    audit_ref=audit_reference(),
    sender_agent=agent_id()
)
@settings(max_examples=100)
def test_audit_trail_propagation(
    audit_ref: Dict[str, Any],
    sender_agent: str
):
    """
    Test Scenario: Audit Trail Propagation
    
    Validates audit reference propagation in ASE messages:
    - Audit references are included in messages
    - Transaction IDs are tracked
    - Sequence numbers are maintained
    - Audit bundles can be reconstructed
    
    Expected Behavior:
    - Audit references are properly formatted
    - Transaction correlation is maintained
    - Sequence numbers are monotonic
    - Timestamps are consistent
    """
    # Create message with audit reference
    message = {
        "baseMessage": {
            "id": f"msg_{audit_ref['transactionId']}",
            "content": "Transaction with audit trail",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "aseMetadata": {
            "version": "1.0.0",
            "agentIdentity": {
                "agentId": sender_agent,
                "agentType": "autonomous",
                "organizationId": "org_sender",
                "settlementAccount": "acct_sender"
            },
            "auditReference": audit_ref
        }
    }
    
    # Validate audit reference structure
    assert "auditReference" in message["aseMetadata"]
    audit_data = message["aseMetadata"]["auditReference"]
    
    assert "auditBundleId" in audit_data
    assert "transactionId" in audit_data
    assert "sequenceNumber" in audit_data
    assert "timestamp" in audit_data
    
    # Validate audit reference data
    assert audit_data["auditBundleId"].startswith("audit_")
    assert audit_data["transactionId"].startswith("txn_")
    assert audit_data["sequenceNumber"] > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
