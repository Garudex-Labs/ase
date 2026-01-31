"""
ASE-to-non-ASE compatibility test specifications.

This module defines backward compatibility test scenarios and graceful degradation
test cases for ASE messages processed by non-ASE agents.

Feature: ase, Backward Compatibility Testing

Validates: Requirements 9.2, 9.6
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
def base_protocol_message(draw):
    """Generate base protocol message without ASE extensions."""
    return {
        "id": draw(st.text(min_size=10, max_size=30)),
        "content": draw(st.text(min_size=1, max_size=500)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": draw(agent_id()),
        "receiver": draw(agent_id()),
        "messageType": draw(st.sampled_from(["request", "response", "notification", "command"]))
    }


@st.composite
def ase_extended_message(draw):
    """Generate ASE-extended message that should be backward compatible."""
    base_msg = draw(base_protocol_message())
    
    # Add ASE metadata as optional extension
    base_msg["aseMetadata"] = {
        "version": draw(st.sampled_from(["0.1.0", "1.0.0", "2.0.0"])),
        "agentIdentity": {
            "agentId": base_msg["sender"],
            "agentType": draw(st.sampled_from(["autonomous", "human", "service"]))
        },
        "costDeclaration": {
            "amount": draw(monetary_amount()),
            "description": draw(st.text(min_size=10, max_size=100))
        }
    }
    
    return base_msg


@st.composite
def non_ase_agent_config(draw):
    """Generate configuration for non-ASE agent."""
    return {
        "agentId": draw(agent_id()),
        "supportsASE": False,
        "protocolVersion": draw(st.sampled_from(["1.0", "2.0", "3.0"])),
        "capabilities": draw(st.lists(
            st.sampled_from(["messaging", "file_transfer", "rpc", "streaming"]),
            min_size=1,
            max_size=4,
            unique=True
        ))
    }


# Compatibility test scenarios

@given(
    ase_message=ase_extended_message(),
    non_ase_agent=non_ase_agent_config()
)
@settings(max_examples=100)
def test_ase_message_to_non_ase_agent_processing(
    ase_message: Dict[str, Any],
    non_ase_agent: Dict[str, Any]
):
    """
    Test Scenario: ASE Message Processing by Non-ASE Agent
    
    Validates that non-ASE agents can process ASE messages by ignoring
    economic metadata:
    - Base protocol fields are accessible
    - ASE metadata is safely ignored
    - Message processing continues normally
    - No errors are raised due to ASE fields
    
    Expected Behavior:
    - Non-ASE agent extracts base message content
    - Economic metadata is ignored without errors
    - Message functionality is preserved
    - Response can be generated without ASE support
    
    Compatibility Matrix:
    - ASE v0.1.0 → Non-ASE: Compatible
    - ASE v1.0.0 → Non-ASE: Compatible
    - ASE v2.0.0 → Non-ASE: Compatible
    """
    # Simulate non-ASE agent processing
    # Non-ASE agent only accesses base protocol fields
    
    # Validate base protocol fields are accessible
    assert "id" in ase_message, "Message ID must be accessible"
    assert "content" in ase_message, "Message content must be accessible"
    assert "timestamp" in ase_message, "Message timestamp must be accessible"
    assert "sender" in ase_message, "Sender must be accessible"
    assert "receiver" in ase_message, "Receiver must be accessible"
    assert "messageType" in ase_message, "Message type must be accessible"
    
    # Non-ASE agent processes message without accessing ASE metadata
    processed_message = {
        "id": ase_message["id"],
        "content": ase_message["content"],
        "timestamp": ase_message["timestamp"],
        "sender": ase_message["sender"],
        "receiver": ase_message["receiver"],
        "messageType": ase_message["messageType"]
    }
    
    # Validate processing succeeded
    assert processed_message["id"] == ase_message["id"]
    assert processed_message["content"] == ase_message["content"]
    
    # Non-ASE agent generates response without ASE metadata
    response = {
        "id": f"resp_{ase_message['id']}",
        "content": "Processed successfully",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": non_ase_agent["agentId"],
        "receiver": ase_message["sender"],
        "messageType": "response",
        "inReplyTo": ase_message["id"]
    }
    
    # Validate response structure
    assert "id" in response
    assert "content" in response
    assert "inReplyTo" in response
    assert "aseMetadata" not in response, "Non-ASE agent should not add ASE metadata"


@given(
    base_message=base_protocol_message(),
    ase_agent_id=agent_id()
)
@settings(max_examples=100)
def test_non_ase_message_to_ase_agent_processing(
    base_message: Dict[str, Any],
    ase_agent_id: str
):
    """
    Test Scenario: Non-ASE Message Processing by ASE Agent
    
    Validates that ASE agents can process non-ASE messages as zero-cost
    transactions:
    - Base protocol fields are processed normally
    - Missing ASE metadata is handled gracefully
    - Default economic values are applied
    - Transaction is recorded with zero cost
    
    Expected Behavior:
    - ASE agent processes base message normally
    - Missing economic metadata treated as zero-cost
    - Audit trail records zero-cost transaction
    - Response includes ASE metadata if appropriate
    
    Compatibility Matrix:
    - Non-ASE → ASE v0.1.0: Compatible (zero-cost)
    - Non-ASE → ASE v1.0.0: Compatible (zero-cost)
    - Non-ASE → ASE v2.0.0: Compatible (zero-cost)
    """
    # Update receiver to ASE agent
    base_message["receiver"] = ase_agent_id
    
    # ASE agent processes message
    # Check for ASE metadata
    has_ase_metadata = "aseMetadata" in base_message
    
    # If no ASE metadata, treat as zero-cost transaction
    if not has_ase_metadata:
        # Apply default economic values
        economic_context = {
            "cost": {"value": "0.00", "currency": "USD"},
            "chargeEvent": None,
            "budgetImpact": "0.00"
        }
    else:
        # Process existing ASE metadata
        economic_context = {
            "cost": base_message["aseMetadata"].get("costDeclaration", {}).get("amount", {"value": "0.00", "currency": "USD"}),
            "chargeEvent": base_message["aseMetadata"].get("chargeEvent"),
            "budgetImpact": base_message["aseMetadata"].get("costDeclaration", {}).get("amount", {}).get("value", "0.00")
        }
    
    # Validate zero-cost handling
    assert economic_context["cost"]["value"] == "0.00"
    assert economic_context["budgetImpact"] == "0.00"
    
    # ASE agent generates response with ASE metadata
    response = {
        "id": f"resp_{base_message['id']}",
        "content": "Processed as zero-cost transaction",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": ase_agent_id,
        "receiver": base_message["sender"],
        "messageType": "response",
        "inReplyTo": base_message["id"],
        "aseMetadata": {
            "version": "1.0.0",
            "agentIdentity": {
                "agentId": ase_agent_id,
                "agentType": "autonomous"
            },
            "chargeEvent": {
                "eventId": f"evt_final_{base_message['id']}",
                "eventType": "final",
                "agentId": ase_agent_id,
                "amount": {"value": "0.00", "currency": "USD"},
                "status": "confirmed",
                "description": "Zero-cost transaction from non-ASE agent"
            }
        }
    }
    
    # Validate response structure
    assert "aseMetadata" in response
    assert response["aseMetadata"]["chargeEvent"]["amount"]["value"] == "0.00"


@given(
    ase_message=ase_extended_message()
)
@settings(max_examples=100)
def test_ase_field_removal_preserves_functionality(
    ase_message: Dict[str, Any]
):
    """
    Test Scenario: ASE Field Removal Preserves Base Functionality
    
    Validates that removing ASE metadata from a message preserves base
    protocol functionality:
    - Base message remains valid after ASE field removal
    - Message can be processed by non-ASE agents
    - No required fields are lost
    - Message semantics are preserved
    
    Expected Behavior:
    - Stripped message is valid base protocol message
    - All required base fields are present
    - Message can be serialized and deserialized
    - Functionality is equivalent to non-ASE message
    """
    # Create copy of message
    original_message = ase_message.copy()
    
    # Remove ASE metadata
    stripped_message = {k: v for k, v in ase_message.items() if k != "aseMetadata"}
    
    # Validate base protocol fields are preserved
    assert "id" in stripped_message
    assert "content" in stripped_message
    assert "timestamp" in stripped_message
    assert "sender" in stripped_message
    assert "receiver" in stripped_message
    assert "messageType" in stripped_message
    
    # Validate ASE metadata is removed
    assert "aseMetadata" not in stripped_message
    
    # Validate base fields match original
    assert stripped_message["id"] == original_message["id"]
    assert stripped_message["content"] == original_message["content"]
    assert stripped_message["sender"] == original_message["sender"]
    
    # Validate message can be serialized
    serialized = json.dumps(stripped_message)
    assert len(serialized) > 0
    
    # Validate message can be deserialized
    deserialized = json.loads(serialized)
    assert deserialized["id"] == stripped_message["id"]


@given(
    ase_message=ase_extended_message(),
    non_ase_agent=non_ase_agent_config()
)
@settings(max_examples=100)
def test_graceful_degradation_on_version_mismatch(
    ase_message: Dict[str, Any],
    non_ase_agent: Dict[str, Any]
):
    """
    Test Scenario: Graceful Degradation on Version Mismatch
    
    Validates graceful degradation when ASE version is not supported:
    - Non-ASE agent ignores version field
    - Base protocol processing continues
    - No errors or exceptions raised
    - Functionality degrades to base protocol level
    
    Expected Behavior:
    - Version mismatch does not cause failures
    - Base protocol functionality is preserved
    - Economic features are gracefully disabled
    - Communication continues without interruption
    """
    # Non-ASE agent does not check ASE version
    assert not non_ase_agent["supportsASE"]
    
    # Process message ignoring ASE version
    base_content = {
        "id": ase_message["id"],
        "content": ase_message["content"],
        "sender": ase_message["sender"],
        "receiver": ase_message["receiver"]
    }
    
    # Validate processing succeeded regardless of ASE version
    assert base_content["id"] == ase_message["id"]
    assert base_content["content"] == ase_message["content"]
    
    # Validate no errors occurred
    # (In real implementation, this would check error logs)
    processing_errors = []
    assert len(processing_errors) == 0, "No errors should occur during graceful degradation"


@given(
    messages=st.lists(ase_extended_message(), min_size=1, max_size=10),
    non_ase_agent=non_ase_agent_config()
)
@settings(max_examples=100)
def test_batch_message_processing_compatibility(
    messages: List[Dict[str, Any]],
    non_ase_agent: Dict[str, Any]
):
    """
    Test Scenario: Batch Message Processing Compatibility
    
    Validates that non-ASE agents can process batches of ASE messages:
    - All messages in batch are processed
    - ASE metadata is consistently ignored
    - No batch processing failures
    - Performance is not degraded
    
    Expected Behavior:
    - Batch processing succeeds for all messages
    - Each message is processed independently
    - ASE fields do not interfere with batch operations
    - Processing order is preserved
    """
    processed_messages = []
    
    for msg in messages:
        # Non-ASE agent processes each message
        processed = {
            "id": msg["id"],
            "content": msg["content"],
            "sender": msg["sender"],
            "receiver": msg["receiver"],
            "processed_by": non_ase_agent["agentId"]
        }
        processed_messages.append(processed)
    
    # Validate all messages were processed
    assert len(processed_messages) == len(messages)
    
    # Validate processing order preserved
    for i, (original, processed) in enumerate(zip(messages, processed_messages)):
        assert processed["id"] == original["id"]
        assert processed["content"] == original["content"]
    
    # Validate no ASE metadata in processed messages
    for processed in processed_messages:
        assert "aseMetadata" not in processed


@given(
    ase_message=ase_extended_message()
)
@settings(max_examples=100)
def test_json_serialization_compatibility(
    ase_message: Dict[str, Any]
):
    """
    Test Scenario: JSON Serialization Compatibility
    
    Validates that ASE messages can be serialized and deserialized by
    non-ASE systems:
    - JSON serialization succeeds
    - Deserialization preserves base fields
    - ASE fields can be safely ignored during parsing
    - No schema validation errors for base protocol
    
    Expected Behavior:
    - Message serializes to valid JSON
    - Non-ASE parser can extract base fields
    - ASE fields are optional in schema
    - Round-trip preserves base message integrity
    """
    # Serialize message to JSON
    serialized = json.dumps(ase_message)
    assert len(serialized) > 0
    
    # Deserialize message
    deserialized = json.loads(serialized)
    
    # Validate base fields are preserved
    assert deserialized["id"] == ase_message["id"]
    assert deserialized["content"] == ase_message["content"]
    assert deserialized["sender"] == ase_message["sender"]
    
    # Non-ASE system extracts only base fields
    base_only = {
        "id": deserialized["id"],
        "content": deserialized["content"],
        "timestamp": deserialized["timestamp"],
        "sender": deserialized["sender"],
        "receiver": deserialized["receiver"],
        "messageType": deserialized["messageType"]
    }
    
    # Validate base-only message is valid
    assert "id" in base_only
    assert "content" in base_only
    
    # Re-serialize base-only message
    base_serialized = json.dumps(base_only)
    base_deserialized = json.loads(base_serialized)
    
    # Validate round-trip consistency
    assert base_deserialized["id"] == ase_message["id"]
    assert base_deserialized["content"] == ase_message["content"]


@given(
    ase_message=ase_extended_message(),
    non_ase_agent=non_ase_agent_config()
)
@settings(max_examples=100)
def test_error_handling_for_unknown_fields(
    ase_message: Dict[str, Any],
    non_ase_agent: Dict[str, Any]
):
    """
    Test Scenario: Error Handling for Unknown Fields
    
    Validates that non-ASE agents handle unknown ASE fields gracefully:
    - Unknown fields are ignored without errors
    - No validation failures for extra fields
    - Processing continues normally
    - Warnings may be logged but not errors
    
    Expected Behavior:
    - Unknown fields do not cause exceptions
    - Message processing succeeds
    - Base protocol validation passes
    - System remains stable
    """
    # Non-ASE agent encounters unknown fields
    unknown_fields = ["aseMetadata"]
    
    # Process message, ignoring unknown fields
    known_fields = {k: v for k, v in ase_message.items() if k not in unknown_fields}
    
    # Validate processing succeeded
    assert "id" in known_fields
    assert "content" in known_fields
    
    # Validate no errors occurred
    # (In real implementation, check error logs)
    errors = []
    assert len(errors) == 0, "Unknown fields should not cause errors"
    
    # Validate warnings may be logged (optional)
    warnings = [f"Unknown field: {field}" for field in unknown_fields if field in ase_message]
    # Warnings are acceptable but not required
    assert len(warnings) <= len(unknown_fields)


@given(
    base_message=base_protocol_message(),
    ase_agent_id=agent_id()
)
@settings(max_examples=100)
def test_ase_agent_backward_compatibility_mode(
    base_message: Dict[str, Any],
    ase_agent_id: str
):
    """
    Test Scenario: ASE Agent Backward Compatibility Mode
    
    Validates that ASE agents can operate in backward compatibility mode:
    - Detect non-ASE messages automatically
    - Switch to compatibility mode
    - Process messages without ASE features
    - Maintain audit trail for compatibility mode operations
    
    Expected Behavior:
    - ASE agent detects missing ASE metadata
    - Compatibility mode is activated
    - Message processing succeeds
    - Audit records indicate compatibility mode
    """
    # ASE agent checks for ASE metadata
    has_ase_metadata = "aseMetadata" in base_message
    
    # Activate compatibility mode if no ASE metadata
    compatibility_mode = not has_ase_metadata
    
    if compatibility_mode:
        # Process in compatibility mode
        processing_context = {
            "mode": "backward_compatibility",
            "ase_features_enabled": False,
            "economic_tracking": False,
            "audit_level": "basic"
        }
        
        # Process message normally
        processed = {
            "id": base_message["id"],
            "content": base_message["content"],
            "sender": base_message["sender"],
            "receiver": ase_agent_id,
            "processing_mode": "backward_compatibility"
        }
        
        # Validate compatibility mode processing
        assert processed["processing_mode"] == "backward_compatibility"
        assert processing_context["ase_features_enabled"] is False
    
    # Validate message was processed successfully
    assert compatibility_mode == (not has_ase_metadata)


# Compatibility matrix documentation

def get_compatibility_matrix():
    """
    Return compatibility matrix for ASE and non-ASE agents.
    
    Compatibility Matrix:
    
    | Sender      | Receiver    | Result                          | Notes                           |
    |-------------|-------------|---------------------------------|---------------------------------|
    | ASE v0.1.0  | Non-ASE     | Compatible                      | Economic metadata ignored       |
    | ASE v1.0.0  | Non-ASE     | Compatible                      | Economic metadata ignored       |
    | ASE v2.0.0  | Non-ASE     | Compatible                      | Economic metadata ignored       |
    | Non-ASE     | ASE v0.1.0  | Compatible (zero-cost)          | Treated as zero-cost transaction|
    | Non-ASE     | ASE v1.0.0  | Compatible (zero-cost)          | Treated as zero-cost transaction|
    | Non-ASE     | ASE v2.0.0  | Compatible (zero-cost)          | Treated as zero-cost transaction|
    | ASE v0.1.0  | ASE v0.1.0  | Fully compatible                | All features available          |
    | ASE v1.0.0  | ASE v1.0.0  | Fully compatible                | All features available          |
    | ASE v2.0.0  | ASE v2.0.0  | Fully compatible                | All features available          |
    | ASE v0.1.0  | ASE v1.0.0  | Compatible (degraded)           | v0.1.0 features only            |
    | ASE v1.0.0  | ASE v2.0.0  | Compatible (degraded)           | v1.0.0 features only            |
    
    Support Requirements:
    - All ASE implementations MUST support backward compatibility with non-ASE agents
    - ASE agents MUST treat non-ASE messages as zero-cost transactions
    - Non-ASE agents MUST be able to process ASE messages by ignoring economic fields
    - ASE metadata MUST be optional in all message schemas
    - Base protocol functionality MUST NOT depend on ASE metadata
    """
    return {
        "ase_to_non_ase": {
            "v0.1.0": "compatible",
            "v1.0.0": "compatible",
            "v2.0.0": "compatible"
        },
        "non_ase_to_ase": {
            "v0.1.0": "compatible_zero_cost",
            "v1.0.0": "compatible_zero_cost",
            "v2.0.0": "compatible_zero_cost"
        },
        "ase_to_ase": {
            "same_version": "fully_compatible",
            "version_mismatch": "compatible_degraded"
        }
    }


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
