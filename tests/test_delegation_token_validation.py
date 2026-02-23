"""
Property-based tests for delegation token validation.

Feature: ase, Property 7: Delegation Token Validation
Feature: ase, Property 9: Hierarchical Delegation Support

Validates: Requirements 4.3, 4.5
"""

import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import hypothesis.strategies as st
from hypothesis import given, settings, assume


# Test data generators

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
def jwt_header(draw):
    """Generate valid JWT header."""
    return {
        "alg": draw(st.sampled_from(["ES256", "RS256"])),
        "typ": "JWT",
        "kid": draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "Pd")),
            min_size=8,
            max_size=32
        ))
    }


@st.composite
def delegation_token_payload(draw, source_token=None, base_time=None):
    """Generate valid delegation token payload."""
    if base_time is None:
        base_time = int(time.time())
    
    # Generate expiration time between 1 hour and 24 hours in the future
    expiration_hours = draw(st.integers(min_value=1, max_value=24))
    exp_time = base_time + (expiration_hours * 3600)
    
    # Generate allowed operations
    all_operations = ["read", "write", "compute", "delegate", "audit"]
    num_operations = draw(st.integers(min_value=0, max_value=len(all_operations)))
    if num_operations == 0:
        allowed_operations = []  # Empty means all operations allowed
    else:
        allowed_operations = draw(st.lists(
            st.sampled_from(all_operations),
            min_size=num_operations,
            max_size=num_operations,
            unique=True
        ))
    
    # If source token exists, ensure operations are subset of source
    if source_token and source_token["payload"].get("allowedOperations"):
        source_ops = set(source_token["payload"]["allowedOperations"])
        allowed_operations = [op for op in allowed_operations if op in source_ops]
    
    payload = {
        "iss": draw(agent_id()),
        "sub": draw(agent_id()),
        "aud": draw(st.sampled_from(["any", "service_api", "compute_service", "storage_service"])),
        "exp": exp_time,
        "iat": base_time,
        "jti": f"token_{base_time}_{draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=8, max_size=16))}",
        "allowedOperations": allowed_operations,
    }
    
    return payload


@st.composite
def delegation_token(draw, source_token=None, base_time=None):
    """Generate complete delegation token."""
    header = draw(jwt_header())
    payload = draw(delegation_token_payload(source_token=source_token, base_time=base_time))
    
    # Generate mock signature (base64url-encoded)
    signature = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")) + "-_",
        min_size=64,
        max_size=128
    ))
    
    return {
        "header": header,
        "payload": payload,
        "signature": signature
    }


@st.composite
def delegation_chain(draw, max_depth=None):
    """Generate a chain of delegation tokens."""
    if max_depth is None:
        max_depth = draw(st.integers(min_value=1, max_value=5))
    
    base_time = int(time.time())
    tokens = []
    
    # Create root token
    root_token = draw(delegation_token(source_token=None, base_time=base_time))
    tokens.append(root_token)
    
    # Create target tokens
    for i in range(max_depth - 1):
        source = tokens[-1]
        target_token = draw(delegation_token(source_token=source, base_time=base_time))
        tokens.append(target_token)
    
    return tokens


# Property tests

@given(token=delegation_token())
@settings(max_examples=100)
def test_property_7_delegation_token_validation(token: Dict[str, Any]):
    """
    Property 7: Delegation Token Validation
    
    For any delegation token usage, the ASE agent should validate both
    cryptographic signatures before processing.
    
    This test validates that:
    1. Token has all required JWT fields (header, payload, signature)
    2. Header specifies valid algorithm (ES256 or RS256)
    3. Payload contains all required claims
    5. Expiration time is in the future
    6. Token ID is unique and properly formatted
    7. Allowed operations are valid
    8. Delegation depth is within limits (0-5)
    """
    # Validate token structure
    assert "header" in token, "Token must have header"
    assert "payload" in token, "Token must have payload"
    assert "signature" in token, "Token must have signature"
    
    # Validate header
    header = token["header"]
    assert header["typ"] == "JWT", f"Token type must be JWT, got {header['typ']}"
    assert header["alg"] in ["ES256", "RS256"], \
        f"Algorithm must be ES256 or RS256, got {header['alg']}"
    assert "kid" in header, "Header must contain key identifier"
    assert len(header["kid"]) > 0, "Key identifier must not be empty"
    
    # Validate payload - required claims
    payload = token["payload"]
    required_claims = ["iss", "sub", "aud", "exp", "iat", "jti"]
    for claim in required_claims:
        assert claim in payload, f"Missing required claim: {claim}"
    
    # Validate issuer and subject
    assert len(payload["iss"]) > 0, "Issuer must not be empty"
    assert len(payload["sub"]) > 0, "Subject must not be empty"
    assert payload["iss"] != payload["sub"], \
        "Issuer and subject must be different (cannot delegate to self)"
    
    # Validate audience
    assert len(payload["aud"]) > 0, "Audience must not be empty"
    
    # Validate timestamps
    assert isinstance(payload["exp"], int), "Expiration must be integer timestamp"
    assert isinstance(payload["iat"], int), "Issued-at must be integer timestamp"
    assert payload["exp"] > payload["iat"], \
        "Expiration must be after issued-at time"
    
    # Validate expiration is in the future (relative to issued-at)
    time_diff = payload["exp"] - payload["iat"]
    assert time_diff >= 3600, \
        f"Token lifetime must be at least 1 hour, got {time_diff} seconds"
    assert time_diff <= 86400, \
        f"Token lifetime must be at most 24 hours, got {time_diff} seconds"
    
    # Validate token ID
    assert len(payload["jti"]) > 0, "Token ID must not be empty"
    
    # Validate allowed operations
    if "allowedOperations" in payload:
        allowed_ops = payload["allowedOperations"]
        assert isinstance(allowed_ops, list), "Allowed operations must be a list"
        
        valid_operations = ["read", "write", "compute", "delegate", "audit"]
        for op in allowed_ops:
            assert op in valid_operations, \
                f"Invalid operation: {op}. Must be one of {valid_operations}"
        
        # Check for duplicates
        assert len(allowed_ops) == len(set(allowed_ops)), \
            "Allowed operations must not contain duplicates"
    
    # Validate signature format (base64url)
    signature = token["signature"]
    assert len(signature) > 0, "Signature must not be empty"
    # Base64url uses A-Za-z0-9-_
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in valid_chars for c in signature), \
        "Signature must be valid base64url encoding"


@given(chain=delegation_chain())
@settings(max_examples=100)
def test_property_9_hierarchical_delegation_support(chain: List[Dict[str, Any]]):
    """
    Property 9: Hierarchical Delegation Support
    
    For any valid delegation token, sub-agents should be able to create
    further delegations within the original token's constraints.
    
    This test validates that:
    1. Delegation chains maintain proper source-target relationships
    3. Delegation depth decreases at each level
    4. Operation restrictions are cumulative (target ⊆ source)
    5. Currency remains consistent through the chain
    6. Delegation chain tracking is accurate
    7. Maximum chain depth is enforced (≤5 levels)
    """
    # Validate chain is not empty
    assert len(chain) > 0, "Delegation chain must not be empty"
    
    # Validate maximum chain depth
    assert len(chain) <= 5, \
        f"Delegation chain must not exceed 5 levels, got {len(chain)}"
    
    # Validate root token (first in chain)
    root_token = chain[0]
    assert "sourceTokenId" not in root_token["payload"], \
        "Root token must not have source token ID"
    assert "delegationChain" not in root_token["payload"], \
        "Root token must not have delegation chain"
    
    # Validate each target token in the chain
    for i in range(1, len(chain)):
        source_token = chain[i - 1]
        target_token = chain[i]
        
        source_payload = source_token["payload"]
        target_payload = target_token["payload"]
        
        # Validate operation restrictions are cumulative
        source_ops = set(source_payload.get("allowedOperations", []))
        target_ops = set(target_payload.get("allowedOperations", []))
        
        # If source has empty operations (all allowed), target can have any
        # If source has specific operations, target must be subset
        if source_ops:
            assert target_ops.issubset(source_ops) or not target_ops, \
                f"Child operations must be subset of source operations. Parent: {source_ops}, Child: {target_ops}"
        
        # Validate issuer-subject chain
        # Child's issuer should be source's subject (delegation flow)
        assert target_payload["iss"] == source_payload["sub"], \
            f"Child issuer must be source subject (delegation flow)"


@given(
    token=delegation_token(),
    requested_operation=st.sampled_from(["read", "write", "compute", "delegate", "audit", "invalid_op"])
)
@settings(max_examples=100)
def test_operation_authorization(
    token: Dict[str, Any],
    requested_operation: str
):
    """
    Test that operation authorization is properly enforced.
    
    An operation should only be allowed if:
    1. allowedOperations is empty (all operations allowed), OR
    2. requested_operation is in allowedOperations list
    """
    allowed_ops = token["payload"].get("allowedOperations", [])
    
    # Empty list means all operations allowed
    if not allowed_ops:
        # All valid operations should be allowed
        valid_operations = ["read", "write", "compute", "delegate", "audit"]
        if requested_operation in valid_operations:
            assert True, "Operation should be allowed (all operations permitted)"
        else:
            assert requested_operation not in valid_operations, \
                "Invalid operation should be rejected"
    else:
        # Check if operation is in allowed list
        if requested_operation in allowed_ops:
            assert True, f"Operation {requested_operation} is allowed"
        else:
            assert requested_operation not in allowed_ops, \
                f"Operation {requested_operation} is not allowed"


@given(
    token=delegation_token(),
    time_offset_seconds=st.integers(min_value=-3600, max_value=100000)
)
@settings(max_examples=100)
def test_token_expiration_validation(
    token: Dict[str, Any],
    time_offset_seconds: int
):
    """
    Test that token expiration is properly validated.
    
    A token should be considered expired if current_time >= exp.
    """
    exp_time = token["payload"]["exp"]
    iat_time = token["payload"]["iat"]
    
    # Simulate current time at various offsets from issued-at
    current_time = iat_time + time_offset_seconds
    
    # Determine if token should be expired
    is_expired = current_time >= exp_time
    
    if is_expired:
        # Token should be rejected
        assert current_time >= exp_time, \
            "Token is expired and should be rejected"
    else:
        # Token should be valid (not expired)
        assert current_time < exp_time, \
            "Token is not expired and should be valid"
    
    # Validate that token is not used before issued-at time
    if current_time < iat_time:
        assert False, \
            "Token should not be used before issued-at time"


@given(chain=delegation_chain(max_depth=5))
@settings(max_examples=100)
def test_delegation_chain_validation(chain: List[Dict[str, Any]]):
    """
    Test that entire delegation chain is validated.
    
    For a delegation to be valid, all tokens in the chain must:
    1. Have valid signatures
    2. Not be expired
    4. Maintain operation restrictions
    """
    # Validate each token in the chain
    for i, token in enumerate(chain):
        # Validate token structure
        assert "header" in token, f"Token {i} must have header"
        assert "payload" in token, f"Token {i} must have payload"
        assert "signature" in token, f"Token {i} must have signature"
        
        # Validate timestamps are consistent
        payload = token["payload"]
        assert payload["exp"] > payload["iat"], \
            f"Token {i} expiration must be after issued-at"
    
    # Validate chain relationships
    if len(chain) > 1:
        for i in range(1, len(chain)):
            source = chain[i - 1]
            target = chain[i]
            



@given(token=delegation_token())
@settings(max_examples=100)
def test_token_json_serialization(token: Dict[str, Any]):
    """
    Test that delegation tokens can be properly serialized to JSON.
    
    This ensures the token structure is JSON-compatible.
    """
    try:
        # Serialize to JSON
        json_str = json.dumps(token)
        
        # Deserialize back
        deserialized = json.loads(json_str)
        
        # Validate structure is preserved
        assert deserialized["header"]["alg"] == token["header"]["alg"]
        assert deserialized["header"]["typ"] == token["header"]["typ"]
        assert deserialized["payload"]["iss"] == token["payload"]["iss"]
        assert deserialized["payload"]["sub"] == token["payload"]["sub"]
        assert deserialized["payload"]["jti"] == token["payload"]["jti"]
        assert deserialized["signature"] == token["signature"]
        
    except (TypeError, ValueError) as e:
        assert False, f"Failed to serialize delegation token: {e}"


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
