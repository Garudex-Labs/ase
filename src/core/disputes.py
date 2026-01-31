"""
Dispute resolution logic.

Handles creation, management, and resolution of billing disputes.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

from .models import DisputeEvent, ChargeEvent


class DisputeManager:
    """
    Manages the lifecycle of billing disputes.
    """

    def __init__(self):
        self._disputes: Dict[str, DisputeEvent] = {}

    def raise_dispute(self, original_charge_id: str, 
                     disputing_agent: str, 
                     reason: str,
                     evidence: Optional[List[Dict[str, Any]]] = None) -> DisputeEvent:
        """
        Raise a new dispute against a charge.
        """
        dispute_id = f"dsp_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        dispute = DisputeEvent(
            dispute_id=dispute_id,
            original_charge_id=original_charge_id,
            disputing_agent=disputing_agent,
            reason=reason,
            status="open",
            created_at=now,
            evidence=evidence or []
        )
        
        self._disputes[dispute_id] = dispute
        return dispute

    def resolve_dispute(self, dispute_id: str, resolution_notes: str, accepted: bool) -> DisputeEvent:
        """
        Resolve a dispute (accept or reject).
        """
        if dispute_id not in self._disputes:
            raise ValueError(f"Dispute {dispute_id} not found")
            
        dispute = self._disputes[dispute_id]
        
        if dispute.status not in ["open", "under_review", "escalated"]:
            raise ValueError(f"Dispute {dispute_id} is already {dispute.status}")
            
        dispute.status = "resolved" if accepted else "rejected"
        # Ideally we would append resolution notes to a history or metadata field
        # For now, simplistic status update
        
        return dispute

    def escalate_dispute(self, dispute_id: str) -> DisputeEvent:
        """
        Escalate a dispute to arbitration.
        """
        if dispute_id not in self._disputes:
            raise ValueError(f"Dispute {dispute_id} not found")
            
        dispute = self._disputes[dispute_id]
        dispute.status = "escalated"
        return dispute

    def get_dispute(self, dispute_id: str) -> Optional[DisputeEvent]:
        """Get dispute by ID."""
        return self._disputes.get(dispute_id)
