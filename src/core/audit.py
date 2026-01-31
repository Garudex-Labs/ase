"""
Audit Logging and Bundle Generation.

Handles converting economic events into cryptographically signed audit bundles.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

from .models import AuditEntry, AuditBundle, ChargeEvent, SerializableModel
from ..crypto.signing import SigningService, SignatureAlgorithm


class AuditManager:
    """
    Manages audit logs and bundle generation.
    """
    
    def __init__(self, signing_service: Optional[SigningService] = None):
        self.signing_service = signing_service
        # In-memory log storage
        self._logs: List[AuditEntry] = []

    def log_event(self, event_type: str, agent_id: str, details: Dict[str, Any]) -> AuditEntry:
        """
        Log an economic event.
        """
        entry_id = f"aud_{uuid.uuid4().hex[:16]}"
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            agent_id=agent_id,
            details=details
        )
        self._logs.append(entry)
        return entry

    def generate_bundle(self, agent_id: str, key_id: Optional[str] = None) -> AuditBundle:
        """
        Create a signed audit bundle from current logs.
        """
        bundle_id = f"bundle_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        # Filter logs? For now, include all (or filtration logic could be added)
        logs_to_include = [log for log in self._logs]
        
        bundle = AuditBundle(
            bundle_id=bundle_id,
            generated_at=now,
            entries=logs_to_include,
            signer_id=agent_id
        )
        
        if self.signing_service and key_id:
            # Sign the bundle content
            # Canonical serialization of the "content" part
            content_dict = bundle.model_dump(include={'bundle_id', 'generated_at', 'entries', 'signer_id'}, mode='json')
            content_str = json.dumps(content_dict, sort_keys=True)
            
            sig = self.signing_service.sign(
                content_str.encode('utf-8'),
                key_id=key_id,
                algorithm=SignatureAlgorithm.ES256
            )
            bundle.signature = sig.signature
            
        return bundle
