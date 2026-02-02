"""
Pydantic models for ASE protocol entities.

These models define the data structure and validation rules for economic metadata
and associated events. They inherit from SerializableModel to ensure correct
snake_case (internal) <-> camelCase (wire) conversion.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import Field, field_validator

from .serialization import SerializableModel


class MonetaryAmount(SerializableModel):
    """
    Monetary value with currency specification.
    """
    value: str = Field(..., description="Decimal string representation of amount", pattern=r"^\d+(\.\d{1,10})?$")
    currency: str = Field(..., description="ISO 4217 currency code", pattern=r"^[A-Z]{3}$")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        try:
            Decimal(v)
        except Exception:
            raise ValueError("Invalid decimal format")
        return v


class AgentIdentity(SerializableModel):
    """
    Identity information for cost attribution.
    """
    agent_id: str = Field(..., alias="agentId", description="Unique agent identifier")
    public_key: Optional[str] = Field(None, alias="publicKey", description="Public key for signature verification")
    org_id: Optional[str] = Field(None, alias="orgId", description="Organization identifier")
    role: Optional[str] = Field(None, description="Agent role (e.g., buyer, seller)")


class CostDeclaration(SerializableModel):
    """
    Service pricing information.
    """
    base_cost: MonetaryAmount = Field(..., alias="baseCost", description="Base cost for the operation")
    cost_model: str = Field(..., alias="costModel", description="Pricing model (e.g., per-token, per-request)")
    currency: str = Field(..., description="ISO 4217 currency code")
    estimated_cost: Optional[MonetaryAmount] = Field(None, alias="estimatedCost", description="Estimated total cost")


class BudgetRequest(SerializableModel):
    """
    Resource allocation request.
    """
    amount: MonetaryAmount = Field(..., description="Requested budget amount")
    category: str = Field(..., description="Budget category")
    purpose: Optional[str] = Field(None, description="Reason for request")
    request_id: Optional[str] = Field(None, alias="requestId", description="Unique request identifier")


class ChargeEvent(SerializableModel):
    """
    Provisional or final charge event.
    """
    event_id: str = Field(..., alias="eventId", description="Unique event identifier")
    event_type: str = Field(..., alias="eventType", description="provisional, final, adjustment, or refund")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp")
    agent_id: str = Field(..., alias="agentId", description="Identifier of the agent being charged")
    amount: MonetaryAmount = Field(..., description="Monetary amount")
    description: str = Field(..., description="Charge description")
    status: str = Field(..., description="pending, reserved, confirmed, etc.")
    
    # Optional / Conditional
    provisional_charge_id: Optional[str] = Field(None, alias="provisionalChargeId", description="Ref to provisional charge")
    expires_at: Optional[datetime] = Field(None, alias="expiresAt", description="Expiration for provisional charges")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")


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


class EconomicEvent(SerializableModel):
    """
    General economic event for audit logs.
    """
    event_id: str = Field(..., alias="eventId")
    event_type: str = Field(..., alias="eventType", description="cost_declaration, budget_request, provisional_charge, final_charge, dispute")
    timestamp: datetime
    agent_id: str = Field(..., alias="agentId")
    amount: Optional[MonetaryAmount] = None
    currency: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    audit_trail: Optional[List["AuditEntry"]] = Field(None, alias="auditTrail")


class AuditBundle(SerializableModel):
    """
    Cryptographically signed collection of audit logs.
    """
    bundle_id: str = Field(..., alias="bundleId")
    generated_by: str = Field(..., alias="generatedBy")
    generated_at: datetime = Field(..., alias="generatedAt")
    time_range: Dict[str, datetime] = Field(..., alias="timeRange")
    transactions: List[EconomicEvent]
    summary: Dict[str, Any]
    signature: str
    signature_algorithm: str = Field(..., alias="signatureAlgorithm")
    signer_id: Optional[str] = Field(None, alias="signerId")


class DisputeEvent(SerializableModel):
    """
    Structure for a dispute event.
    """
    dispute_id: str = Field(..., alias="disputeId")
    original_charge_id: str = Field(..., alias="originalChargeId")
    disputing_agent: str = Field(..., alias="disputingAgent")
    reason: str
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    evidence: Optional[List[Dict[str, Any]]] = Field(None)


class EconomicData(SerializableModel):
    """
    Economic metadata payload containing agent identity and optional components.
    """
    agent_identity: AgentIdentity = Field(..., alias="agentIdentity")
    cost_declaration: Optional[CostDeclaration] = Field(None, alias="costDeclaration")
    budget_request: Optional[BudgetRequest] = Field(None, alias="budgetRequest")
    charge_event: Optional[ChargeEvent] = Field(None, alias="chargeEvent")
    audit_reference: Optional[AuditReference] = Field(None, alias="auditReference")
    delegation_token: Optional[str] = Field(None, alias="delegationToken")


class EconomicMetadata(SerializableModel):
    """
    Top-level ASE economic metadata container.
    """
    version: str = Field(..., description="ASE protocol version")
    economic_data: EconomicData = Field(..., alias="economicData")
    signature: Optional[str] = Field(None, description="Optional cryptographic signature")


class MeteringEvent(SerializableModel):
    """
    Event representing resource usage for metering.
    """
    event_id: Optional[str] = Field(None, alias="eventId", description="Unique event identifier")
    agent_id: str = Field(..., alias="agentId", description="Agent identifier")
    resource_type: str = Field(..., alias="resourceType", description="Type of resource consumed")
    quantity: Decimal = Field(..., description="Amount of resource consumed")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow(), description="ISO 8601 timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Quantity must be non-negative")
        return v


class FeatureSet(SerializableModel):
    """Feature capabilities for a specific version."""
    backward_compatibility: bool = Field(True, alias="backwardCompatibility")
    provisional_charges: bool = Field(False, alias="provisionalCharges")
    delegation_tokens: bool = Field(False, alias="delegationTokens")
    dispute_resolution: bool = Field(False, alias="disputeResolution")
    audit_bundles: bool = Field(False, alias="auditBundles")
    charge_reconciliation: bool = Field(False, alias="chargeReconciliation")


class VersionCapability(SerializableModel):
    """Version with its supported features."""
    version: str
    features: FeatureSet
    deprecated: bool = False
    sunset_date: Optional[datetime] = Field(None, alias="sunsetDate")


class NegotiationRequest(SerializableModel):
    """Version negotiation request from initiating agent."""
    supported_versions: List[VersionCapability] = Field(..., alias="supportedVersions")
    preferred_version: str = Field(..., alias="preferredVersion")
    required_features: Optional[List[str]] = Field(None, alias="requiredFeatures")
    optional_features: Optional[List[str]] = Field(None, alias="optionalFeatures")


class NegotiationResponse(SerializableModel):
    """Version negotiation response from receiving agent."""
    selected_version: str = Field(..., alias="selectedVersion")
    supported_features: FeatureSet = Field(..., alias="supportedFeatures")
    degraded_features: Optional[List[str]] = Field(None, alias="degradedFeatures")
    unsupported_features: Optional[List[str]] = Field(None, alias="unsupportedFeatures")
    fallback_behavior: str = Field("degrade", alias="fallbackBehavior")
