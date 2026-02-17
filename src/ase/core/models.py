"""
Pydantic models for ASE protocol entities.

These models define the data structure and validation rules for identity,
delegation, and audit events. They inherit from SerializableModel to ensure correct
snake_case (internal) <-> camelCase (wire) conversion.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import Field

from .serialization import SerializableModel


class AgentIdentity(SerializableModel):
    """
    Identity information for attribution.
    """
    agent_id: str = Field(..., alias="agentId", description="Unique agent identifier")
    public_key: Optional[str] = Field(None, alias="publicKey", description="Public key for signature verification")
    org_id: Optional[str] = Field(None, alias="orgId", description="Organization identifier")
    role: Optional[str] = Field(None, description="Agent role (e.g., delegate, authority)")


class AuditReference(SerializableModel):
    """
    Reference to an audit trail or bundle.
    """
    audit_id: str = Field(..., alias="auditId", description="Unique audit identifier")
    location: Optional[str] = Field(None, description="URL or storage location")
    hash: Optional[str] = Field(None, description="Cryptographic hash of the audit data")


class DelegationToken(SerializableModel):
    """
    Wrapper for JWT delegation token string.
    """
    token: str = Field(..., description="JWT token string")
    decoded: Optional[Dict[str, Any]] = Field(None, description="Optional decoded claims for convenience")


class AuditEntry(SerializableModel):
    """
    Single entry in an audit trail.
    """
    entry_id: str = Field(..., alias="entryId")
    timestamp: datetime
    event_type: str = Field(..., alias="eventType")
    agent_id: str = Field(..., alias="agentId")
    details: Dict[str, Any]


class AuditBundle(SerializableModel):
    """
    Cryptographically signed collection of audit logs.
    """
    bundle_id: str = Field(..., alias="bundleId")
    generated_by: str = Field(..., alias="generatedBy")
    generated_at: datetime = Field(..., alias="generatedAt")
    time_range: Dict[str, datetime] = Field(..., alias="timeRange")
    entries: List[AuditEntry] = Field(..., alias="entries")
    summary: Dict[str, Any]
    signature: str
    signature_algorithm: str = Field(..., alias="signatureAlgorithm")
    signer_id: Optional[str] = Field(None, alias="signerId")


class EconomicData(SerializableModel):
    """
    Protocol metadata payload containing agent identity and optional components.
    Renamed to maintain structure but stripped of financial fields.
    """
    agent_identity: AgentIdentity = Field(..., alias="agentIdentity")
    audit_reference: Optional[AuditReference] = Field(None, alias="auditReference")
    delegation_token: Optional[str] = Field(None, alias="delegationToken")
    # budget/cost fields removed


class MeteringEvent(SerializableModel):
    """
    A metering event for tracking resource usage.

    Used by Caracal to record client consumption of API resources
    for audit and billing purposes.
    """
    agent_id: str = Field(..., alias="agentId", description="Agent that consumed the resource")
    resource_type: str = Field(..., alias="resourceType", description="Type of resource consumed")
    quantity: Any = Field(..., description="Quantity consumed (typically Decimal)")
    timestamp: Optional[datetime] = Field(None, description="When the event occurred")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")


class EconomicMetadata(SerializableModel):
    """
    Top-level ASE protocol metadata container.
    """
    version: str = Field(..., description="ASE protocol version")
    data: EconomicData = Field(..., alias="economicData")
    signature: Optional[str] = Field(None, description="Optional cryptographic signature")

