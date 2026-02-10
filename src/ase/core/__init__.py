"""
Core message processing components for ASE protocol.
"""

from .serialization import MessageSerializer, MessageDeserializer
from .validation import ValidationPipeline, ValidationError, ValidationResult
from .extensions import ExtensionRegistry, ExtensionPoint
from .models import (
    AgentIdentity, AuditReference, DelegationToken, EconomicMetadata,
    EconomicData, AuditEntry, AuditBundle
)
from .audit import AuditManager
from .versioning import VersionManager

__all__ = [
    "MessageSerializer",
    "MessageDeserializer",
    "ValidationPipeline",
    "ValidationError",
    "ValidationResult",
    "ExtensionRegistry",
    "ExtensionPoint",
    "AgentIdentity",
    "AuditReference",
    "DelegationToken",
    "EconomicMetadata",
    "EconomicData",
    "AuditEntry",
    "AuditBundle",
    "AuditManager",
    "VersionManager",
]
