"""
Property-based tests for framework integration convention adherence.

Feature: ase, Property 19: Framework Integration Convention Adherence

Validates: Requirements 8.6
"""

import json
from typing import Any, Dict
from datetime import datetime, timezone

import hypothesis.strategies as st
from hypothesis import given, settings, assume

from adapters.base import AdapterConfig, FrameworkType
from adapters.langchain import LangChainAdapter
from adapters.autogpt import AutoGPTAdapter


# Test data generators

@st.composite
def economic_metadata(draw):
    """Generate valid ASE economic metadata."""
    return {
        "version": "1.0.0",
        "agentIdentity": {
            "agentId": draw(st.text(min_size=5, max_size=20)),
            "agentType": draw(st.sampled_from(["autonomous", "human", "service"]))
        },
        "costDeclaration": {
            "amount": {
                "value": str(draw(st.decimals(min_value=0.01, max_value=999.99, places=2))),
                "currency": draw(st.sampled_from(["USD", "EUR", "GBP"]))
            },
            "description": draw(st.text(min_size=10, max_size=100))
        }
    }


@st.composite
def langchain_message(draw):
    """Generate LangChain-style message."""
    return {
        "content": draw(st.text(min_size=1, max_size=200)),
        "type": draw(st.sampled_from(["human", "ai", "system", "function", "tool"])),
        "additional_kwargs": {}
    }


@st.composite
def autogpt_message(draw):
    """Generate AutoGPT-style message."""
    return {
        "role": draw(st.sampled_from(["system", "user", "assistant", "function"])),
        "content": draw(st.text(min_size=1, max_size=200)),
        "metadata": {}
    }


@st.composite
def delegation_token(draw):
    """Generate mock delegation token."""
    return f"eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.{draw(st.text(min_size=20, max_size=50))}.{draw(st.text(min_size=20, max_size=50))}"


# Property tests

@given(
    message=langchain_message(),
    metadata=economic_metadata()
)
@settings(max_examples=100)
def test_property_19_langchain_convention_adherence(
    message: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """
    Property 19: Framework Integration Convention Adherence (LangChain)
    
    For any framework integration, the adapter interface should maintain
    framework-specific conventions and patterns.
    
    This test validates that:
    1. LangChain messages maintain required structure (content, type)
    2. ASE metadata is placed in additional_kwargs following LangChain conventions
    3. Message wrapping preserves original message content
    4. Message unwrapping correctly extracts ASE metadata
    5. Wrapped messages remain valid LangChain messages
    """
    # Create adapter
    adapter = LangChainAdapter()
    
    # Validate original message structure
    assert "content" in message, "LangChain message must have 'content' field"
    assert "type" in message, "LangChain message must have 'type' field"
    
    # Wrap message with ASE metadata
    wrapped = adapter.wrap_message(message, metadata)
    
    # Validate wrapped message maintains LangChain structure
    assert "content" in wrapped, "Wrapped message must preserve 'content' field"
    assert "type" in wrapped, "Wrapped message must preserve 'type' field"
    assert "additional_kwargs" in wrapped, "Wrapped message must have 'additional_kwargs'"
    
    # Validate ASE metadata placement follows LangChain conventions
    assert "aseMetadata" in wrapped["additional_kwargs"], \
        "ASE metadata must be in additional_kwargs['aseMetadata']"
    
    # Validate original content is preserved
    assert wrapped["content"] == message["content"], \
        "Message content must be preserved during wrapping"
    assert wrapped["type"] == message["type"], \
        "Message type must be preserved during wrapping"
    
    # Validate ASE metadata is correctly placed
    assert wrapped["additional_kwargs"]["aseMetadata"] == metadata, \
        "ASE metadata must match provided metadata"
    
    # Unwrap message
    unwrapped_message, extracted_metadata = adapter.unwrap_message(wrapped)
    
    # Validate unwrapping extracts metadata correctly
    assert extracted_metadata == metadata, \
        "Unwrapped metadata must match original metadata"
    
    # Validate unwrapped message matches original structure
    assert unwrapped_message["content"] == message["content"], \
        "Unwrapped message content must match original"
    assert unwrapped_message["type"] == message["type"], \
        "Unwrapped message type must match original"
    
    # Validate framework conventions are maintained
    is_valid = adapter.validate_framework_conventions(wrapped)
    assert is_valid, "Wrapped message must follow LangChain conventions"


@given(
    message=autogpt_message(),
    metadata=economic_metadata()
)
@settings(max_examples=100)
def test_property_19_autogpt_convention_adherence(
    message: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """
    Property 19: Framework Integration Convention Adherence (AutoGPT)
    
    For any framework integration, the adapter interface should maintain
    framework-specific conventions and patterns.
    
    This test validates that:
    1. AutoGPT messages maintain required structure (role, content)
    2. ASE metadata is placed in metadata field following AutoGPT conventions
    3. Message wrapping preserves original message content
    4. Message unwrapping correctly extracts ASE metadata
    5. Wrapped messages remain valid AutoGPT messages
    """
    # Create adapter
    adapter = AutoGPTAdapter()
    
    # Validate original message structure
    assert "role" in message, "AutoGPT message must have 'role' field"
    assert "content" in message, "AutoGPT message must have 'content' field"
    
    # Wrap message with ASE metadata
    wrapped = adapter.wrap_message(message, metadata)
    
    # Validate wrapped message maintains AutoGPT structure
    assert "role" in wrapped, "Wrapped message must preserve 'role' field"
    assert "content" in wrapped, "Wrapped message must preserve 'content' field"
    assert "metadata" in wrapped, "Wrapped message must have 'metadata' field"
    
    # Validate ASE metadata placement follows AutoGPT conventions
    assert "aseMetadata" in wrapped["metadata"], \
        "ASE metadata must be in metadata['aseMetadata']"
    
    # Validate original content is preserved
    assert wrapped["role"] == message["role"], \
        "Message role must be preserved during wrapping"
    assert wrapped["content"] == message["content"], \
        "Message content must be preserved during wrapping"
    
    # Validate ASE metadata is correctly placed
    assert wrapped["metadata"]["aseMetadata"] == metadata, \
        "ASE metadata must match provided metadata"
    
    # Unwrap message
    unwrapped_message, extracted_metadata = adapter.unwrap_message(wrapped)
    
    # Validate unwrapping extracts metadata correctly
    assert extracted_metadata == metadata, \
        "Unwrapped metadata must match original metadata"
    
    # Validate unwrapped message matches original structure
    assert unwrapped_message["role"] == message["role"], \
        "Unwrapped message role must match original"
    assert unwrapped_message["content"] == message["content"], \
        "Unwrapped message content must match original"
    
    # Validate framework conventions are maintained
    is_valid = adapter.validate_framework_conventions(wrapped)
    assert is_valid, "Wrapped message must follow AutoGPT conventions"


@given(
    message=langchain_message(),
    token=delegation_token()
)
@settings(max_examples=100)
def test_langchain_delegation_token_attachment(
    message: Dict[str, Any],
    token: str
):
    """
    Test that delegation tokens are correctly attached to LangChain messages
    following framework conventions.
    """
    adapter = LangChainAdapter()
    
    # Attach token
    message_with_token = adapter.attach_delegation_token(message, token)
    
    # Validate token is in correct location
    assert "additional_kwargs" in message_with_token
    assert "aseMetadata" in message_with_token["additional_kwargs"]
    assert "delegationToken" in message_with_token["additional_kwargs"]["aseMetadata"]
    
    # Validate token value
    assert message_with_token["additional_kwargs"]["aseMetadata"]["delegationToken"] == token
    
    # Extract token
    extracted_token = adapter.extract_delegation_token(message_with_token)
    assert extracted_token == token, "Extracted token must match original"
    
    # Validate message structure is preserved
    assert message_with_token["content"] == message["content"]
    assert message_with_token["type"] == message["type"]


@given(
    message=autogpt_message(),
    token=delegation_token()
)
@settings(max_examples=100)
def test_autogpt_delegation_token_attachment(
    message: Dict[str, Any],
    token: str
):
    """
    Test that delegation tokens are correctly attached to AutoGPT messages
    following framework conventions.
    """
    adapter = AutoGPTAdapter()
    
    # Attach token
    message_with_token = adapter.attach_delegation_token(message, token)
    
    # Validate token is in correct location
    assert "metadata" in message_with_token
    assert "aseMetadata" in message_with_token["metadata"]
    assert "delegationToken" in message_with_token["metadata"]["aseMetadata"]
    
    # Validate token value
    assert message_with_token["metadata"]["aseMetadata"]["delegationToken"] == token
    
    # Extract token
    extracted_token = adapter.extract_delegation_token(message_with_token)
    assert extracted_token == token, "Extracted token must match original"
    
    # Validate message structure is preserved
    assert message_with_token["role"] == message["role"]
    assert message_with_token["content"] == message["content"]


@given(
    message=langchain_message(),
    metadata=economic_metadata()
)
@settings(max_examples=100)
def test_langchain_charge_event_creation(
    message: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """
    Test that charge events are created in LangChain-compatible format.
    """
    adapter = LangChainAdapter()
    
    # Extract cost declaration from metadata
    cost_declaration = metadata.get("costDeclaration", {})
    amount = cost_declaration.get("amount", {"value": "10.00", "currency": "USD"})
    agent_id = metadata["agentIdentity"]["agentId"]
    description = cost_declaration.get("description", "Test charge")
    
    # Create provisional charge event
    prov_event = adapter.create_charge_event(
        event_type="provisional",
        amount=amount,
        agent_id=agent_id,
        description=description
    )
    
    # Validate charge event structure
    assert "eventId" in prov_event
    assert prov_event["eventId"].startswith("evt_prov_")
    assert prov_event["eventType"] == "provisional"
    assert prov_event["agentId"] == agent_id
    assert prov_event["amount"] == amount
    assert prov_event["description"] == description
    assert prov_event["status"] == "pending"
    
    # Create final charge event
    final_event = adapter.create_charge_event(
        event_type="final",
        amount=amount,
        agent_id=agent_id,
        description=description
    )
    
    # Validate final charge event
    assert final_event["eventId"].startswith("evt_final_")
    assert final_event["eventType"] == "final"
    assert final_event["status"] == "confirmed"


@given(
    message=autogpt_message(),
    metadata=economic_metadata()
)
@settings(max_examples=100)
def test_autogpt_charge_event_creation(
    message: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """
    Test that charge events are created in AutoGPT-compatible format.
    """
    adapter = AutoGPTAdapter()
    
    # Extract cost declaration from metadata
    cost_declaration = metadata.get("costDeclaration", {})
    amount = cost_declaration.get("amount", {"value": "10.00", "currency": "USD"})
    agent_id = metadata["agentIdentity"]["agentId"]
    description = cost_declaration.get("description", "Test charge")
    
    # Create provisional charge event
    prov_event = adapter.create_charge_event(
        event_type="provisional",
        amount=amount,
        agent_id=agent_id,
        description=description
    )
    
    # Validate charge event structure
    assert "eventId" in prov_event
    assert prov_event["eventId"].startswith("evt_prov_")
    assert prov_event["eventType"] == "provisional"
    assert prov_event["agentId"] == agent_id
    assert prov_event["amount"] == amount
    assert prov_event["description"] == description
    assert prov_event["status"] == "pending"
    
    # Create final charge event
    final_event = adapter.create_charge_event(
        event_type="final",
        amount=amount,
        agent_id=agent_id,
        description=description
    )
    
    # Validate final charge event
    assert final_event["eventId"].startswith("evt_final_")
    assert final_event["eventType"] == "final"
    assert final_event["status"] == "confirmed"


@given(
    message=langchain_message()
)
@settings(max_examples=100)
def test_langchain_roundtrip_consistency(message: Dict[str, Any]):
    """
    Test that wrapping and unwrapping preserves message integrity for LangChain.
    """
    adapter = LangChainAdapter()
    
    # Create metadata
    metadata = {
        "version": "1.0.0",
        "agentIdentity": {
            "agentId": "test_agent",
            "agentType": "autonomous"
        }
    }
    
    # Wrap message
    wrapped = adapter.wrap_message(message, metadata)
    
    # Unwrap message
    unwrapped, extracted_metadata = adapter.unwrap_message(wrapped)
    
    # Validate roundtrip consistency
    assert unwrapped["content"] == message["content"]
    assert unwrapped["type"] == message["type"]
    assert extracted_metadata == metadata


@given(
    message=autogpt_message()
)
@settings(max_examples=100)
def test_autogpt_roundtrip_consistency(message: Dict[str, Any]):
    """
    Test that wrapping and unwrapping preserves message integrity for AutoGPT.
    """
    adapter = AutoGPTAdapter()
    
    # Create metadata
    metadata = {
        "version": "1.0.0",
        "agentIdentity": {
            "agentId": "test_agent",
            "agentType": "autonomous"
        }
    }
    
    # Wrap message
    wrapped = adapter.wrap_message(message, metadata)
    
    # Unwrap message
    unwrapped, extracted_metadata = adapter.unwrap_message(wrapped)
    
    # Validate roundtrip consistency
    assert unwrapped["role"] == message["role"]
    assert unwrapped["content"] == message["content"]
    assert extracted_metadata == metadata


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
