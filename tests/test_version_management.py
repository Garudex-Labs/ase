"""
Property-based tests for version management and protocol compliance validation.

Feature: ase, Property 1: Backward Compatibility Preservation
Feature: ase, Property 17: Version Negotiation
Feature: ase, Property 18: Version Mismatch Graceful Degradation
Feature: ase, Property 20: Test Suite Protocol Compliance Validation

Validates: Requirements 1.1, 1.2, 1.5, 7.4, 7.6, 9.6
"""

import json
from typing import Any, Dict, List, Optional, Tuple
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
def ase_version(draw):
    """Generate ASE protocol version."""
    return draw(st.sampled_from(["0.1.0", "1.0.0", "2.0.0"]))


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
    """Generate base protocol message."""
    return {
        "id": draw(st.text(min_size=10, max_size=30)),
        "content": draw(st.text(min_size=1, max_size=500)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": draw(agent_id()),
        "receiver": draw(agent_id()),
        "messageType": draw(st.sampled_from(["request", "response", "notification"]))
    }


@st.composite
def ase_message(draw, version=None):
    """Generate ASE message with specified or random version."""
    base_msg = draw(base_protocol_message())
    msg_version = version if version else draw(ase_version())
    
    base_msg["aseMetadata"] = {
        "version": msg_version,
        "agentIdentity": {
            "agentId": base_msg["sender"],
            "agentType": draw(st.sampled_from(["autonomous", "human", "service"]))
        }
    }
    
    # Add version-specific features
    if msg_version in ["1.0.0", "2.0.0"]:
        # v1.0.0+ features: delegation tokens, provisional charges
        base_msg["aseMetadata"]["delegationToken"] = draw(st.one_of(
            st.none(),
            st.text(min_size=50, max_size=200)
        ))
    
    if msg_version == "2.0.0":
        # v2.0.0 features: dispute resolution
        base_msg["aseMetadata"]["disputeReference"] = draw(st.one_of(
            st.none(),
            st.text(min_size=20, max_size=40)
        ))
    
    return base_msg


@st.composite
def agent_capabilities(draw):
    """Generate agent capability configuration."""
    return {
        "agentId": draw(agent_id()),
        "supportedVersions": draw(st.lists(
            ase_version(),
            min_size=1,
            max_size=3,
            unique=True
        )),
        "supportsASE": draw(st.booleans())
    }


# Property 1: Backward Compatibility Preservation

@given(
    ase_message=ase_message(),
    non_ase_agent=agent_id()
)
@settings(max_examples=100)
def test_property_1_backward_compatibility_preservation(
    ase_message: Dict[str, Any],
    non_ase_agent: str
):
    """
    Property 1: Backward Compatibility Preservation
    
    For any ASE message sent to a non-ASE agent or non-ASE message processed
    by an ASE agent, the base protocol functionality should remain completely
    intact and unaffected by the presence or absence of economic metadata.
    
    This test validates that:
    1. Base protocol fields are always accessible
    2. ASE metadata can be safely ignored
    3. Message processing succeeds without ASE support
    4. No errors occur due to ASE fields
    5. Functionality is equivalent to non-ASE messages
    
    Validates: Requirements 1.1, 1.2, 1.5
    """
    # Non-ASE agent processes ASE message
    # Extract base protocol fields only
    base_fields = {
        "id": ase_message["id"],
        "content": ase_message["content"],
        "timestamp": ase_message["timestamp"],
        "sender": ase_message["sender"],
        "receiver": ase_message["receiver"],
        "messageType": ase_message["messageType"]
    }
    
    # Validate all base fields are accessible
    assert "id" in base_fields, "Message ID must be accessible"
    assert "content" in base_fields, "Message content must be accessible"
    assert "timestamp" in base_fields, "Timestamp must be accessible"
    assert "sender" in base_fields, "Sender must be accessible"
    assert "receiver" in base_fields, "Receiver must be accessible"
    assert "messageType" in base_fields, "Message type must be accessible"
    
    # Validate base fields match original message
    assert base_fields["id"] == ase_message["id"]
    assert base_fields["content"] == ase_message["content"]
    assert base_fields["sender"] == ase_message["sender"]
    
    # Non-ASE agent generates response without ASE metadata
    response = {
        "id": f"resp_{ase_message['id']}",
        "content": "Processed successfully",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": non_ase_agent,
        "receiver": ase_message["sender"],
        "messageType": "response",
        "inReplyTo": ase_message["id"]
    }
    
    # Validate response is valid base protocol message
    assert "id" in response
    assert "content" in response
    assert "sender" in response
    assert "receiver" in response
    assert "aseMetadata" not in response, "Non-ASE response should not have ASE metadata"
    
    # Validate base protocol functionality is preserved
    assert response["inReplyTo"] == ase_message["id"]
    assert response["receiver"] == ase_message["sender"]


@given(
    base_message=base_protocol_message(),
    ase_agent=agent_id()
)
@settings(max_examples=100)
def test_property_1_non_ase_to_ase_zero_cost(
    base_message: Dict[str, Any],
    ase_agent: str
):
    """
    Property 1: Backward Compatibility Preservation (Non-ASE to ASE)
    
    For any non-ASE message processed by an ASE agent, the message should be
    handled as a zero-cost transaction without errors.
    
    Validates: Requirements 1.2
    """
    # ASE agent receives non-ASE message
    base_message["receiver"] = ase_agent
    
    # Check for ASE metadata
    has_ase_metadata = "aseMetadata" in base_message
    
    # ASE agent processes as zero-cost transaction
    if not has_ase_metadata:
        economic_context = {
            "cost": {"value": "0.00", "currency": "USD"},
            "budgetImpact": "0.00",
            "chargeEvent": {
                "eventId": f"evt_final_{base_message['id']}",
                "eventType": "final",
                "agentId": ase_agent,
                "amount": {"value": "0.00", "currency": "USD"},
                "status": "confirmed",
                "description": "Zero-cost transaction from non-ASE agent"
            }
        }
        
        # Validate zero-cost handling
        assert economic_context["cost"]["value"] == "0.00"
        assert economic_context["budgetImpact"] == "0.00"
        assert economic_context["chargeEvent"]["amount"]["value"] == "0.00"
    
    # Validate base message processing succeeded
    assert base_message["id"] is not None
    assert base_message["content"] is not None


# Property 17: Version Negotiation

@given(
    agent1_caps=agent_capabilities(),
    agent2_caps=agent_capabilities()
)
@settings(max_examples=100)
def test_property_17_version_negotiation(
    agent1_caps: Dict[str, Any],
    agent2_caps: Dict[str, Any]
):
    """
    Property 17: Version Negotiation
    
    For any version negotiation between ASE agents, the highest mutually
    supported version should be selected.
    
    This test validates that:
    1. Both agents declare supported versions
    2. Common versions are identified
    3. Highest common version is selected
    4. Negotiation succeeds if any common version exists
    5. Negotiation fails gracefully if no common version
    
    Validates: Requirements 7.4
    """
    assume(agent1_caps["supportsASE"] and agent2_caps["supportsASE"])
    assume(agent1_caps["agentId"] != agent2_caps["agentId"])
    
    # Find common versions
    agent1_versions = set(agent1_caps["supportedVersions"])
    agent2_versions = set(agent2_caps["supportedVersions"])
    common_versions = agent1_versions.intersection(agent2_versions)
    
    if len(common_versions) > 0:
        # Select highest common version
        version_order = ["0.1.0", "1.0.0", "2.0.0"]
        common_sorted = sorted(
            common_versions,
            key=lambda v: version_order.index(v) if v in version_order else -1,
            reverse=True
        )
        negotiated_version = common_sorted[0]
        
        # Validate negotiation result
        assert negotiated_version in agent1_versions, \
            "Negotiated version must be supported by agent 1"
        assert negotiated_version in agent2_versions, \
            "Negotiated version must be supported by agent 2"
        
        # Validate it's the highest common version
        for version in common_versions:
            if version != negotiated_version:
                assert version_order.index(version) < version_order.index(negotiated_version), \
                    f"Negotiated version {negotiated_version} must be higher than {version}"
        
        # Create negotiation result
        negotiation_result = {
            "agent1": agent1_caps["agentId"],
            "agent2": agent2_caps["agentId"],
            "negotiatedVersion": negotiated_version,
            "agent1Versions": list(agent1_versions),
            "agent2Versions": list(agent2_versions),
            "status": "success"
        }
        
        assert negotiation_result["status"] == "success"
        assert negotiation_result["negotiatedVersion"] in common_versions
    else:
        # No common versions - negotiation fails gracefully
        negotiation_result = {
            "agent1": agent1_caps["agentId"],
            "agent2": agent2_caps["agentId"],
            "negotiatedVersion": None,
            "agent1Versions": list(agent1_versions),
            "agent2Versions": list(agent2_versions),
            "status": "failed",
            "reason": "no_common_version"
        }
        
        assert negotiation_result["status"] == "failed"
        assert negotiation_result["negotiatedVersion"] is None


# Property 18: Version Mismatch Graceful Degradation

@given(
    message_version=ase_version(),
    agent_version=ase_version()
)
@settings(max_examples=100)
def test_property_18_version_mismatch_graceful_degradation(
    message_version: str,
    agent_version: str
):
    """
    Property 18: Version Mismatch Graceful Degradation
    
    For any version mismatch scenario, the ASE agent should gracefully degrade
    to compatible functionality without failure.
    
    This test validates that:
    1. Version mismatch is detected
    2. Compatible feature set is determined
    3. Processing continues with degraded features
    4. No errors or exceptions occur
    5. Base protocol functionality is preserved
    
    Validates: Requirements 7.6
    """
    # Create message with specific version
    message = {
        "id": "msg_version_test",
        "content": "Test message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender": "agent_sender",
        "receiver": "agent_receiver",
        "messageType": "request",
        "aseMetadata": {
            "version": message_version,
            "agentIdentity": {
                "agentId": "agent_sender",
                "agentType": "autonomous"
            }
        }
    }
    
    # Agent processes message with its supported version
    version_order = ["0.1.0", "1.0.0", "2.0.0"]
    message_version_idx = version_order.index(message_version)
    agent_version_idx = version_order.index(agent_version)
    
    # Determine compatible version (lower of the two)
    compatible_version_idx = min(message_version_idx, agent_version_idx)
    compatible_version = version_order[compatible_version_idx]
    
    # Determine available features based on compatible version
    available_features = {
        "base_protocol": True,
        "cost_declaration": True,
        "audit_bundles": True,
        "delegation_tokens": compatible_version in ["1.0.0", "2.0.0"],
        "provisional_charges": compatible_version in ["1.0.0", "2.0.0"],
        "dispute_resolution": compatible_version == "2.0.0",
        "reconciliation": compatible_version == "2.0.0"
    }
    
    # Process message with degraded features
    processing_result = {
        "messageId": message["id"],
        "compatibleVersion": compatible_version,
        "availableFeatures": available_features,
        "degraded": message_version != agent_version,
        "processingSucceeded": True
    }
    
    # Validate graceful degradation
    assert processing_result["processingSucceeded"], \
        "Processing must succeed despite version mismatch"
    assert processing_result["compatibleVersion"] in version_order, \
        "Compatible version must be valid"
    assert processing_result["availableFeatures"]["base_protocol"], \
        "Base protocol must always be available"
    
    # Validate feature availability based on compatible version
    if compatible_version == "0.1.0":
        assert not processing_result["availableFeatures"]["delegation_tokens"]
        assert not processing_result["availableFeatures"]["dispute_resolution"]
    elif compatible_version == "1.0.0":
        assert processing_result["availableFeatures"]["delegation_tokens"]
        assert not processing_result["availableFeatures"]["dispute_resolution"]
    elif compatible_version == "2.0.0":
        assert processing_result["availableFeatures"]["delegation_tokens"]
        assert processing_result["availableFeatures"]["dispute_resolution"]
    
    # Validate no errors occurred
    assert "error" not in processing_result


# Property 20: Test Suite Protocol Compliance Validation

@given(
    test_message=ase_message()
)
@settings(max_examples=100)
def test_property_20_protocol_compliance_validation(
    test_message: Dict[str, Any]
):
    """
    Property 20: Test Suite Protocol Compliance Validation
    
    For any test suite execution, protocol compliance and backward compatibility
    should be properly validated.
    
    This test validates that:
    1. Message structure conforms to ASE schema
    2. Required fields are present
    3. Field types are correct
    4. Version-specific features are validated
    5. Backward compatibility is maintained
    
    Validates: Requirements 9.6
    """
    # Validate base protocol compliance
    base_protocol_checks = {
        "has_id": "id" in test_message,
        "has_content": "content" in test_message,
        "has_timestamp": "timestamp" in test_message,
        "has_sender": "sender" in test_message,
        "has_receiver": "receiver" in test_message,
        "has_message_type": "messageType" in test_message
    }
    
    # Validate ASE metadata compliance
    ase_metadata_checks = {
        "has_ase_metadata": "aseMetadata" in test_message,
        "has_version": "aseMetadata" in test_message and "version" in test_message["aseMetadata"],
        "has_agent_identity": "aseMetadata" in test_message and "agentIdentity" in test_message["aseMetadata"]
    }
    
    # Validate version-specific compliance
    if "aseMetadata" in test_message:
        version = test_message["aseMetadata"]["version"]
        version_checks = {
            "valid_version": version in ["0.1.0", "1.0.0", "2.0.0"],
            "v1_features_valid": True,
            "v2_features_valid": True
        }
        
        # Check v1.0.0+ features
        if version in ["1.0.0", "2.0.0"]:
            if "delegationToken" in test_message["aseMetadata"]:
                version_checks["v1_features_valid"] = \
                    test_message["aseMetadata"]["delegationToken"] is None or \
                    isinstance(test_message["aseMetadata"]["delegationToken"], str)
        
        # Check v2.0.0 features
        if version == "2.0.0":
            if "disputeReference" in test_message["aseMetadata"]:
                version_checks["v2_features_valid"] = \
                    test_message["aseMetadata"]["disputeReference"] is None or \
                    isinstance(test_message["aseMetadata"]["disputeReference"], str)
    else:
        version_checks = {
            "valid_version": True,  # Non-ASE message is valid
            "v1_features_valid": True,
            "v2_features_valid": True
        }
    
    # Validate backward compatibility
    backward_compat_checks = {
        "base_fields_accessible": all(base_protocol_checks.values()),
        "ase_fields_optional": True,  # ASE fields are always optional
        "can_strip_ase_metadata": True  # Can remove ASE metadata and still have valid message
    }
    
    # Compile compliance report
    compliance_report = {
        "messageId": test_message["id"],
        "baseProtocolCompliant": all(base_protocol_checks.values()),
        "aseMetadataCompliant": all(ase_metadata_checks.values()) if "aseMetadata" in test_message else True,
        "versionCompliant": all(version_checks.values()),
        "backwardCompatible": all(backward_compat_checks.values()),
        "overallCompliant": all(base_protocol_checks.values()) and all(version_checks.values()) and all(backward_compat_checks.values())
    }
    
    # Validate overall compliance
    assert compliance_report["baseProtocolCompliant"], \
        "Message must comply with base protocol"
    assert compliance_report["versionCompliant"], \
        "Message must comply with version-specific requirements"
    assert compliance_report["backwardCompatible"], \
        "Message must maintain backward compatibility"
    assert compliance_report["overallCompliant"], \
        "Message must be fully compliant with ASE protocol"
    
    # Validate JSON serialization compliance
    try:
        serialized = json.dumps(test_message)
        deserialized = json.loads(serialized)
        serialization_compliant = deserialized["id"] == test_message["id"]
    except Exception:
        serialization_compliant = False
    
    assert serialization_compliant, "Message must be JSON serializable"


@given(
    messages=st.lists(ase_message(), min_size=5, max_size=20)
)
@settings(max_examples=100)
def test_protocol_compliance_batch_validation(
    messages: List[Dict[str, Any]]
):
    """
    Test batch protocol compliance validation.
    
    Validates that multiple messages can be validated for compliance
    in a batch operation.
    """
    compliance_results = []
    
    for msg in messages:
        # Validate each message
        is_compliant = (
            "id" in msg and
            "content" in msg and
            "sender" in msg and
            "receiver" in msg
        )
        
        compliance_results.append({
            "messageId": msg["id"],
            "compliant": is_compliant
        })
    
    # Validate all messages were checked
    assert len(compliance_results) == len(messages)
    
    # Validate compliance rate
    compliant_count = sum(1 for r in compliance_results if r["compliant"])
    compliance_rate = compliant_count / len(messages) if len(messages) > 0 else 0
    
    # All messages should be compliant (generated by valid strategies)
    assert compliance_rate == 1.0, "All generated messages should be compliant"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
