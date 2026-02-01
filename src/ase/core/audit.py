"""
Audit Logging and Bundle Generation.

Handles converting economic events into cryptographically signed audit bundles.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

from .models import AuditEntry, AuditBundle, EconomicEvent, SerializableModel
from ..crypto.signing import SigningService, SignatureAlgorithm


class AuditManager:
    """
    Manages audit logs and bundle generation.
    """
    
    def __init__(self, signing_service: Optional[SigningService] = None):
        self.signing_service = signing_service
        # In-memory log storage
        self._transactions: List[EconomicEvent] = []

    def log_event(self, event: EconomicEvent) -> EconomicEvent:
        """
        Log an economic event.
        """
        self._transactions.append(event)
        return event

    def generate_bundle(self, agent_id: str, key_id: Optional[str] = None) -> AuditBundle:
        """
        Create a signed audit bundle from current logs.
        """
        bundle_id = f"bundle_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        # Filter logs? For now, include all
        transactions_to_include = [tx for tx in self._transactions]
        
        # Calculate time range
        if transactions_to_include:
            start_time = min(tx.timestamp for tx in transactions_to_include)
            end_time = max(tx.timestamp for tx in transactions_to_include)
        else:
            start_time = now
            end_time = now

        # Calculate summary
        total_transactions = len(transactions_to_include)
        
        bundle = AuditBundle(
            bundle_id=bundle_id,
            generated_by=agent_id,
            generated_at=now,
            time_range={"startTime": start_time, "endTime": end_time},
            transactions=transactions_to_include,
            summary={
                "totalTransactions": total_transactions,
                "agentParticipants": list(set(tx.agent_id for tx in transactions_to_include))
            },
            signature="", # Placeholder, to be filled by signing
            signature_algorithm=SignatureAlgorithm.ES256.value, # Default
            signer_id=agent_id
        )
        
        if self.signing_service and key_id:
            # Sign the bundle content
            # Canonical serialization of the "content" part
            content_dict = bundle.model_dump(
                include={'bundle_id', 'generated_by', 'generated_at', 'time_range', 'transactions', 'summary', 'signer_id', 'signature_algorithm'}, 
                mode='json', 
                by_alias=True
            )
            content_str = json.dumps(content_dict, sort_keys=True)
            
            sig = self.signing_service.sign(
                content_str.encode('utf-8'),
                key_id=key_id,
                algorithm=SignatureAlgorithm.ES256
            )
            bundle.signature = sig.signature
            
        return bundle
