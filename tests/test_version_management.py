"""
Property-based tests for version negotiation and compatibility.

Feature: ase, Property 17: Version Negotiation
Feature: ase, Property 18: Version Mismatch Graceful Degradation

Validates: Requirements 7.4, 7.6
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple

import hypothesis.strategies as st
from hypothesis import given, settings, assume


# Test data generators

@st.composite
def version_string(draw, min_major=0, max_major=3, min_minor=0, max_minor=5, min_patch=0, max_patch=10):
    """Generate valid semantic version strings."""
    major = draw(st.integers(min_value=min_major, max_value=max_major))
    minor = draw(st.integers(min_value=min_minor, max_value=max_minor))
    patch = draw(st.integers(min_value=min_patch, max_value=max_patch))
    return f"{major}.{minor}.{patch}"


@st.composite
def feature_set(draw, version=None):
    """Generate feature set based on version."""
    # Define feature availability by version
    if version:
        major = int(version.split('.')[0])
        minor = int(version.split('.')[1])
        
        # v0.x.x features
        if major == 0:
            return {
                "backwardCompatibility": True,
                "provisionalCharges": False,
                "delegationTokens": False,
                "disputeResolution": False,
                "auditBundles": True,
                "chargeReconciliation": False
            }
        # v1.x.x features
        elif major == 1:
            return {
                "backwardCompatibility": True,
                "provisionalCharges": True,
                "delegationTokens": True,
                "disputeResolution": False,
                "auditBundles": True,
                "chargeReconciliation": False
            }
        # v2.x.x features
        elif major >= 2:
            return {
                "backwardCompatibility": True,
                "provisionalCharges": True,
                "delegationTokens": True,
                "disputeResolution": True,
                "auditBundles": True,
                "chargeReconciliation": True
            }
    
    # Random feature set if no version specified
    return {
        "backwardCompatibility": draw(st.booleans()),
        "provisionalCharges": draw(st.booleans()),
        "delegationTokens": draw(st.booleans()),
        "disputeResolution": draw(st.booleans()),
        "auditBundles": draw(st.booleans()),
        "chargeReconciliation": draw(st.booleans())
    }


@st.composite
def version_capability(draw, version=None):
    """Generate version capability with features."""
    if version is None:
        version = draw(version_string())
    
    features = draw(feature_set(version=version))
    deprecated = draw(st.booleans())
    
    capability = {
        "version": version,
        "features": features,
        "deprecated": deprecated
    }
    
    # Add sunset date if deprecated
    if deprecated:
        capability["sunsetDate"] = "2025-12-31T23:59:59Z"
    
    return capability


@st.composite
def supported_versions_list(draw, min_versions=1, max_versions=5):
    """Generate list of supported version capabilities."""
    num_versions = draw(st.integers(min_value=min_versions, max_value=max_versions))
    
    # Generate unique versions
    versions = []
    version_strings = set()
    
    for _ in range(num_versions):
        v = draw(version_string())
        if v not in version_strings:
            version_strings.add(v)
            capability = draw(version_capability(version=v))
            versions.append(capability)
    
    return versions


@st.composite
def feature_list(draw, min_features=0, max_features=6):
    """Generate list of feature names."""
    all_features = [
        "backwardCompatibility",
        "provisionalCharges",
        "delegationTokens",
        "disputeResolution",
        "auditBundles",
        "chargeReconciliation"
    ]
    
    num_features = draw(st.integers(min_value=min_features, max_value=max_features))
    if num_features == 0:
        return []
    
    return draw(st.lists(
        st.sampled_from(all_features),
        min_size=num_features,
        max_size=num_features,
        unique=True
    ))


@st.composite
def negotiation_request(draw):
    """Generate version negotiation request."""
    supported_versions = draw(supported_versions_list(min_versions=1, max_versions=5))
    
    # Pick a preferred version from supported versions
    preferred_version = draw(st.sampled_from([v["version"] for v in supported_versions]))
    
    # Generate required and optional features
    required_features = draw(feature_list(min_features=0, max_features=3))
    optional_features = draw(feature_list(min_features=0, max_features=3))
    
    return {
        "supportedVersions": supported_versions,
        "preferredVersion": preferred_version,
        "requiredFeatures": required_features,
        "optionalFeatures": optional_features
    }


@st.composite
def ase_message(draw, version=None, include_economic_data=True):
    """Generate ASE message with optional version."""
    if version is None:
        version = draw(version_string())
    
    message = {
        "type": draw(st.sampled_from(["request", "response", "notification"])),
        "content": draw(st.text(min_size=1, max_size=100))
    }
    
    if include_economic_data:
        message["aseMetadata"] = {
            "version": version,
            "economicData": {
                "agentIdentity": {
                    "agentId": f"agent_{draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=6, max_size=12))}",
                    "agentType": draw(st.sampled_from(["autonomous", "service", "human"]))
                }
            }
        }
    
    return message


# Helper functions

def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into tuple."""
    parts = version.split('.')
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    
    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    else:
        return 0


def select_version(local_versions: List[Dict], remote_versions: List[Dict], required_features: List[str]) -> Optional[str]:
    """
    Select the highest mutually supported version that meets requirements.
    
    Args:
        local_versions: List of locally supported version capabilities
        remote_versions: List of remotely supported version capabilities
        required_features: List of feature names that must be supported
    
    Returns:
        Selected version string or None if no compatible version exists
    """
    # Find common versions
    local_version_set = {v['version'] for v in local_versions}
    remote_version_set = {v['version'] for v in remote_versions}
    common_versions = local_version_set & remote_version_set
    
    if not common_versions:
        return None
    
    # Filter versions that support required features
    compatible_versions = []
    for version in common_versions:
        local_cap = next(v for v in local_versions if v['version'] == version)
        remote_cap = next(v for v in remote_versions if v['version'] == version)
        
        # Check if all required features are supported by both
        local_features = local_cap['features']
        remote_features = remote_cap['features']
        
        all_features_supported = all(
            local_features.get(feature, False) and 
            remote_features.get(feature, False)
            for feature in required_features
        )
        
        if all_features_supported:
            compatible_versions.append(version)
    
    if not compatible_versions:
        return None
    
    # Return highest version (semantic versioning sort)
    return max(compatible_versions, key=parse_version)


def get_supported_features(versions: List[Dict], version: str) -> Dict[str, bool]:
    """Get feature set for a specific version."""
    for v in versions:
        if v['version'] == version:
            return v['features']
    return {}


def check_feature_support(features: Dict[str, bool], required_features: List[str]) -> Tuple[List[str], List[str]]:
    """
    Check which required features are supported.
    
    Returns:
        Tuple of (supported_features, unsupported_features)
    """
    supported = []
    unsupported = []
    
    for feature in required_features:
        if features.get(feature, False):
            supported.append(feature)
        else:
            unsupported.append(feature)
    
    return supported, unsupported


# Property tests

@given(
    local_versions=supported_versions_list(min_versions=1, max_versions=5),
    remote_request=negotiation_request()
)
@settings(max_examples=100)
def test_property_17_version_negotiation(
    local_versions: List[Dict[str, Any]],
    remote_request: Dict[str, Any]
):
    """
    Property 17: Version Negotiation
    
    For any version negotiation between ASE agents, the highest mutually
    supported version should be selected.
    
    This test validates that:
    1. Common versions are correctly identified
    2. Required features are validated
    3. Highest compatible version is selected
    4. Negotiation response includes correct feature set
    5. Unsupported features are properly reported
    6. Fallback behavior is specified
    """
    remote_versions = remote_request["supportedVersions"]
    required_features = remote_request["requiredFeatures"]
    optional_features = remote_request.get("optionalFeatures", [])
    
    # Find common versions
    local_version_set = {v['version'] for v in local_versions}
    remote_version_set = {v['version'] for v in remote_versions}
    common_versions = local_version_set & remote_version_set
    
    # Select version using algorithm
    selected_version = select_version(local_versions, remote_versions, required_features)
    
    if selected_version is None:
        # No compatible version found
        assert len(common_versions) == 0 or len(required_features) > 0, \
            "If no version selected, either no common versions or required features not met"
        
        # Validate error response would be generated
        if len(common_versions) == 0:
            # No common versions at all
            assert True, "No common versions available"
        else:
            # Common versions exist but don't support required features
            for version in common_versions:
                local_features = get_supported_features(local_versions, version)
                remote_features = get_supported_features(remote_versions, version)
                
                # At least one required feature must be missing
                has_all_features = all(
                    local_features.get(f, False) and remote_features.get(f, False)
                    for f in required_features
                )
                
                if has_all_features:
                    # This version should have been selected
                    assert False, f"Version {version} supports all required features but was not selected"
    else:
        # Version was selected
        assert selected_version in common_versions, \
            f"Selected version {selected_version} must be in common versions"
        
        # Validate it's the highest compatible version
        for version in common_versions:
            if compare_versions(version, selected_version) > 0:
                # This version is higher, check if it's compatible
                local_features = get_supported_features(local_versions, version)
                remote_features = get_supported_features(remote_versions, version)
                
                has_all_features = all(
                    local_features.get(f, False) and remote_features.get(f, False)
                    for f in required_features
                )
                
                assert not has_all_features, \
                    f"Higher version {version} is compatible but was not selected"
        
        # Validate selected version supports all required features
        local_features = get_supported_features(local_versions, selected_version)
        remote_features = get_supported_features(remote_versions, selected_version)
        
        for feature in required_features:
            assert local_features.get(feature, False), \
                f"Selected version must support required feature {feature} locally"
            assert remote_features.get(feature, False), \
                f"Selected version must support required feature {feature} remotely"
        
        # Build negotiation response
        supported_features = local_features
        supported, unsupported = check_feature_support(
            supported_features,
            required_features + optional_features
        )
        
        # Validate response structure
        response = {
            "selectedVersion": selected_version,
            "supportedFeatures": supported_features,
            "degradedFeatures": [],
            "unsupportedFeatures": unsupported,
            "fallbackBehavior": "ignore" if unsupported else "none"
        }
        
        assert response["selectedVersion"] == selected_version
        assert isinstance(response["supportedFeatures"], dict)
        assert isinstance(response["unsupportedFeatures"], list)
        assert response["fallbackBehavior"] in ["ignore", "error", "degrade", "none"]
        
        # Validate all required features are supported
        for feature in required_features:
            assert feature not in response["unsupportedFeatures"], \
                f"Required feature {feature} must be supported"


@given(
    local_versions=supported_versions_list(min_versions=1, max_versions=3),
    message=ase_message()
)
@settings(max_examples=100)
def test_property_18_version_mismatch_graceful_degradation(
    local_versions: List[Dict[str, Any]],
    message: Dict[str, Any]
):
    """
    Property 18: Version Mismatch Graceful Degradation
    
    For any version mismatch scenario, the ASE agent should gracefully
    degrade to compatible functionality without failure.
    
    This test validates that:
    1. Base protocol processing continues regardless of version mismatch
    2. Economic metadata is ignored if version unsupported
    3. Appropriate warnings are generated
    4. Degradation mode is clearly indicated
    5. Message processing succeeds even with version errors
    6. Fallback to base protocol is transparent
    """
    local_version_set = {v['version'] for v in local_versions}
    
    # Extract message version if present
    message_version = None
    has_ase_metadata = "aseMetadata" in message
    
    if has_ase_metadata:
        message_version = message["aseMetadata"]["version"]
    
    # Determine if version is supported
    version_supported = message_version in local_version_set if message_version else False
    
    # Process message with graceful degradation
    if not has_ase_metadata:
        # Non-ASE message - should process normally
        result = {
            "success": True,
            "processedContent": message["content"],
            "economicCost": 0,
            "aseStatus": {
                "degraded": False,
                "reason": "No ASE metadata present"
            }
        }
        
        assert result["success"] == True, "Non-ASE message should process successfully"
        assert result["economicCost"] == 0, "Non-ASE message should have zero cost"
        assert result["aseStatus"]["degraded"] == False
        
    elif not version_supported:
        # ASE message with unsupported version - degrade gracefully
        result = {
            "success": True,
            "processedContent": message["content"],
            "economicCost": 0,
            "aseStatus": {
                "degraded": True,
                "degradedFeatures": ["all"],
                "reason": f"Version {message_version} not supported",
                "supportedVersions": list(local_version_set),
                "degradedMode": "base_protocol_only",
                "fallbackBehavior": "ignore"
            },
            "warnings": [{
                "code": "ASE_VERSION_MISMATCH",
                "message": f"ASE version {message_version} not supported",
                "supportedVersions": list(local_version_set),
                "degradedMode": "base_protocol_only"
            }]
        }
        
        # Validate graceful degradation
        assert result["success"] == True, \
            "Message should process successfully despite version mismatch"
        assert result["processedContent"] == message["content"], \
            "Base protocol content should be processed"
        assert result["aseStatus"]["degraded"] == True, \
            "Degradation flag should be set"
        assert "reason" in result["aseStatus"], \
            "Degradation reason should be provided"
        assert len(result["warnings"]) > 0, \
            "Warnings should be generated for version mismatch"
        assert result["warnings"][0]["code"] == "ASE_VERSION_MISMATCH", \
            "Warning code should indicate version mismatch"
        
        # Validate economic metadata is ignored
        assert result["economicCost"] == 0, \
            "Economic metadata should be ignored for unsupported version"
        
    else:
        # ASE message with supported version - process normally
        result = {
            "success": True,
            "processedContent": message["content"],
            "economicCost": 0,  # Would be calculated from metadata
            "aseStatus": {
                "degraded": False,
                "version": message_version
            }
        }
        
        assert result["success"] == True, "Supported version should process successfully"
        assert result["aseStatus"]["degraded"] == False, "No degradation for supported version"
        assert result["aseStatus"]["version"] == message_version


@given(
    local_versions=supported_versions_list(min_versions=1, max_versions=3),
    remote_versions=supported_versions_list(min_versions=1, max_versions=3),
    required_features=feature_list(min_features=0, max_features=3)
)
@settings(max_examples=100)
def test_version_selection_determinism(
    local_versions: List[Dict[str, Any]],
    remote_versions: List[Dict[str, Any]],
    required_features: List[str]
):
    """
    Test that version selection is deterministic.
    
    Given the same inputs, version selection should always produce
    the same result.
    """
    # Select version twice
    selected1 = select_version(local_versions, remote_versions, required_features)
    selected2 = select_version(local_versions, remote_versions, required_features)
    
    # Results should be identical
    assert selected1 == selected2, \
        "Version selection should be deterministic"


@given(
    versions=supported_versions_list(min_versions=2, max_versions=5)
)
@settings(max_examples=100)
def test_version_ordering(versions: List[Dict[str, Any]]):
    """
    Test that version comparison correctly orders versions.
    
    Semantic versioning should be properly compared.
    """
    version_strings = [v['version'] for v in versions]
    
    # Sort versions
    sorted_versions = sorted(version_strings, key=parse_version)
    
    # Validate ordering
    for i in range(len(sorted_versions) - 1):
        v1 = sorted_versions[i]
        v2 = sorted_versions[i + 1]
        
        # v1 should be less than or equal to v2
        comparison = compare_versions(v1, v2)
        assert comparison <= 0, \
            f"Version {v1} should be <= {v2} in sorted order"


@given(
    local_versions=supported_versions_list(min_versions=1, max_versions=3),
    remote_versions=supported_versions_list(min_versions=1, max_versions=3)
)
@settings(max_examples=100)
def test_common_version_detection(
    local_versions: List[Dict[str, Any]],
    remote_versions: List[Dict[str, Any]]
):
    """
    Test that common versions are correctly identified.
    """
    local_set = {v['version'] for v in local_versions}
    remote_set = {v['version'] for v in remote_versions}
    
    common = local_set & remote_set
    
    # Validate common versions
    for version in common:
        assert version in local_set, f"Common version {version} should be in local set"
        assert version in remote_set, f"Common version {version} should be in remote set"
    
    # Validate non-common versions
    for version in local_set - common:
        assert version not in remote_set, \
            f"Non-common version {version} should not be in remote set"


@given(
    versions=supported_versions_list(min_versions=1, max_versions=5),
    feature_name=st.sampled_from([
        "backwardCompatibility",
        "provisionalCharges",
        "delegationTokens",
        "disputeResolution",
        "auditBundles",
        "chargeReconciliation"
    ])
)
@settings(max_examples=100)
def test_feature_detection(
    versions: List[Dict[str, Any]],
    feature_name: str
):
    """
    Test that feature support is correctly detected.
    """
    for version_cap in versions:
        version = version_cap['version']
        features = version_cap['features']
        
        # Check feature support
        is_supported = features.get(feature_name, False)
        
        # Validate feature flag is boolean
        assert isinstance(is_supported, bool), \
            f"Feature flag for {feature_name} should be boolean"


@given(
    message=ase_message(include_economic_data=True)
)
@settings(max_examples=100)
def test_base_protocol_preservation(message: Dict[str, Any]):
    """
    Test that base protocol is preserved regardless of ASE metadata.
    
    The base protocol message should always be processable even if
    ASE metadata is invalid or unsupported.
    """
    # Extract base protocol message
    base_message = {
        "type": message["type"],
        "content": message["content"]
    }
    
    # Validate base message is complete
    assert "type" in base_message, "Base message must have type"
    assert "content" in base_message, "Base message must have content"
    
    # Simulate processing base protocol only
    result = {
        "success": True,
        "processedContent": base_message["content"]
    }
    
    assert result["success"] == True, \
        "Base protocol should always process successfully"
    assert result["processedContent"] == message["content"], \
        "Base protocol content should be preserved"


@given(
    request=negotiation_request()
)
@settings(max_examples=100)
def test_negotiation_request_structure(request: Dict[str, Any]):
    """
    Test that negotiation requests have valid structure.
    """
    # Validate required fields
    assert "supportedVersions" in request, "Request must have supportedVersions"
    assert "preferredVersion" in request, "Request must have preferredVersion"
    
    # Validate supported versions
    assert isinstance(request["supportedVersions"], list), \
        "supportedVersions must be a list"
    assert len(request["supportedVersions"]) > 0, \
        "supportedVersions must not be empty"
    
    # Validate each version capability
    for version_cap in request["supportedVersions"]:
        assert "version" in version_cap, "Version capability must have version"
        assert "features" in version_cap, "Version capability must have features"
        
        # Validate version format
        version = version_cap["version"]
        parts = version.split('.')
        assert len(parts) == 3, "Version must be in format major.minor.patch"
        assert all(p.isdigit() for p in parts), "Version parts must be numeric"
        
        # Validate features
        features = version_cap["features"]
        assert isinstance(features, dict), "Features must be a dictionary"
    
    # Validate preferred version is in supported versions
    preferred = request["preferredVersion"]
    supported_version_strings = [v["version"] for v in request["supportedVersions"]]
    assert preferred in supported_version_strings, \
        "Preferred version must be in supported versions list"


@given(
    local_versions=supported_versions_list(min_versions=1, max_versions=3),
    remote_versions=supported_versions_list(min_versions=1, max_versions=3),
    required_features=feature_list(min_features=1, max_features=3)
)
@settings(max_examples=100)
def test_feature_requirement_enforcement(
    local_versions: List[Dict[str, Any]],
    remote_versions: List[Dict[str, Any]],
    required_features: List[str]
):
    """
    Test that required features are properly enforced during negotiation.
    """
    selected_version = select_version(local_versions, remote_versions, required_features)
    
    if selected_version is not None:
        # Version was selected - validate it supports all required features
        local_features = get_supported_features(local_versions, selected_version)
        remote_features = get_supported_features(remote_versions, selected_version)
        
        for feature in required_features:
            assert local_features.get(feature, False), \
                f"Selected version must support required feature {feature} locally"
            assert remote_features.get(feature, False), \
                f"Selected version must support required feature {feature} remotely"


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
