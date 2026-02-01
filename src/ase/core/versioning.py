"""
Version negotiation and compatibility management.

Handles ASE protocol version negotiation and feature capability detection.
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .serialization import SerializableModel


class VersionMismatchReason(Enum):
    NOT_SUPPORTED = "version_not_supported"
    REQUIRED_FEATURES_UNAVAILABLE = "required_features_unavailable"
    DEPRECATED = "version_deprecated"
    INCOMPATIBLE_MAJOR = "incompatible_major_version"


@dataclass
class VersionCapability:
    version: str
    features: Dict[str, bool]
    deprecated: bool = False


class VersionManager:
    """
    Manages protocol version negotiation between agents.
    """

    SUPPORTED_VERSIONS = ["1.0.0"]
    
    DEFAULT_FEATURES = {
        "backwardCompatibility": True,
        "provisionalCharges": True,
        "delegationTokens": True,
        "disputeResolution": True,
        "auditBundles": True,
        "chargeReconciliation": True
    }

    def __init__(self, supported_versions: Optional[List[str]] = None, 
                 features: Optional[Dict[str, bool]] = None):
        self.supported_versions = supported_versions or self.SUPPORTED_VERSIONS
        self.features = features or self.DEFAULT_FEATURES

    def negotiate(self, other_versions: List[str], 
                 required_features: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[VersionMismatchReason]]:
        """
        Negotiate the highest mutually supported version.
        """
        # Parse logic to strict semver would be better, but for now string matching 
        # as per reference implementation scope.
        # Check for intersection
        common_versions = set(self.supported_versions).intersection(set(other_versions))
        
        if not common_versions:
            return None, VersionMismatchReason.NOT_SUPPORTED
            
        # Select highest (simple string sort works for major.minor.patch if padded, 
        # strict semver recommended for prod)
        # We'll use a semantic sort helper
        sorted_versions = sorted(list(common_versions), key=lambda v: [int(p) for p in v.split('.')], reverse=True)
        selected_version = sorted_versions[0]
        
        # Check major version compatibility (simplified: assumes exact match for 1.x)
        if selected_version.startswith("0."):
             # 0.x versions often change breakingly
             pass
        
        # Check required features (if we had version-specific feature maps, we'd check here)
        if required_features:
            missing = [f for f in required_features if not self.features.get(f, False)]
            if missing:
                return None, VersionMismatchReason.REQUIRED_FEATURES_UNAVAILABLE
                
        return selected_version, None

    def get_negotiation_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construct a negotiation response based on a request dict (from schema).
        """
        # Extract supported versions from request (assuming 'supportedVersions' is list of objects or strings)
        # Schema says list of versionCapability objects
        req_versions = []
        if "supportedVersions" in request:
            for v_cap in request["supportedVersions"]:
                if isinstance(v_cap, dict) and "version" in v_cap:
                    req_versions.append(v_cap["version"])
        
        selected_version, mismatch_reason = self.negotiate(req_versions, request.get("requiredFeatures"))
        
        if selected_version:
            return {
                "selectedVersion": selected_version,
                "supportedFeatures": self.features,
                "fallbackBehavior": "degrade"
            }
        else:
            return {
                "error": {
                    "reason": mismatch_reason.value if mismatch_reason else "unknown",
                    "supportedVersions": self.supported_versions
                }
            }
