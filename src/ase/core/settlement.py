"""
Settlement operations and charge lifecycle management.

Handles provisional charge creation, expiration, and finalization.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from .models import ChargeEvent, MonetaryAmount


class ChargeNotFoundError(Exception):
    """Raised when a referenced charge is not found."""
    pass


class ChargeManager:
    """
    Manages the lifecycle of economic charges per ASE spec.
    
    Note: This is a reference implementation for charge lifecycle state management.
    Actual budget enforcement and balance tracking is the responsibility of the
    system using ASE (e.g., Caracal Core), not ASE itself.
    """

    def __init__(self):
        # In-memory storage for reference implementation
        self._charges: Dict[str, ChargeEvent] = {}
        self._escrow: Dict[str, ChargeEvent] = {}  # Disputed charges

    def create_provisional_charge(self, agent_id: str, amount: MonetaryAmount, 
                                description: str, expires_in_seconds: int = 3600) -> ChargeEvent:
        """
        Create a provisional charge to reserve budget.
        """
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(now.timestamp() + expires_in_seconds, tz=timezone.utc)
        
        event_id = f"evt_prov_{uuid.uuid4().hex[:16]}"
        
        charge = ChargeEvent(
            event_id=event_id,
            event_type="provisional",
            timestamp=now,
            agent_id=agent_id,
            amount=amount,
            description=description,
            status="reserved",
            expires_at=expires_at
        )
        
        self._charges[event_id] = charge
        return charge

    def confirm_charge(self, provisional_charge_id: str, final_amount: Optional[MonetaryAmount] = None) -> ChargeEvent:
        """
        Confirm a provisional charge, creating a final charge event.
        
        Per ASE Requirement 3.6: When final charges differ from provisional charges,
        budget adjustments should be made by the system using ASE.
        """
        if provisional_charge_id not in self._charges:
            raise ChargeNotFoundError(f"Provisional charge {provisional_charge_id} not found")
            
        provisional = self._charges[provisional_charge_id]
        
        if provisional.event_type != "provisional":
            raise ValueError(f"Event {provisional_charge_id} is not a provisional charge")
            
        if provisional.status != "reserved":
            raise ValueError(f"Provisional charge {provisional_charge_id} is {provisional.status}, cannot confirm")
            
        # Check expiration
        now = datetime.now(timezone.utc)
        if provisional.expires_at and provisional.expires_at < now:
            provisional.status = "expired"
            raise ValueError(f"Provisional charge {provisional_charge_id} has expired")
            
        # Create final charge
        final_event_id = f"evt_final_{uuid.uuid4().hex[:16]}"
        amount = final_amount if final_amount else provisional.amount
        
        final_charge = ChargeEvent(
            event_id=final_event_id,
            event_type="final",
            timestamp=now,
            agent_id=provisional.agent_id,
            amount=amount,
            description=f"Confirmed: {provisional.description}",
            status="confirmed",
            provisional_charge_id=provisional_charge_id
        )
        
        # Update provisional status
        provisional.status = "confirmed"
        
        self._charges[final_event_id] = final_charge
        return final_charge

    def hold_in_escrow(self, charge_id: str):
        """
        Move charge to escrow during dispute (ASE Requirement 5.5).
        
        Note: This tracks charge state semantics. Actual fund freezing
        is the responsibility of the system using ASE (e.g., Caracal Core).
        """
        if charge_id not in self._charges:
             raise ChargeNotFoundError(f"Charge {charge_id} not found")
        charge = self._charges[charge_id]
        self._escrow[charge_id] = charge
        charge.status = "disputed"

    def release_escrow(self, charge_id: str, accepted: bool):
        """
        Release escrowed charge after dispute resolution.
        
        Args:
            charge_id: The charge ID
            accepted: True if dispute was accepted (refund), False if rejected (charge stands)
        """
        if charge_id not in self._escrow:
             return
        charge = self._escrow.pop(charge_id)
        charge.status = "refunded" if accepted else "confirmed"

    def release_expired_charges(self) -> List[str]:
        """
        Check all reserved charges and release any that have expired (ASE Requirement 3.3).
        Returns list of released event IDs.
        """
        now = datetime.now(timezone.utc)
        released = []
        
        for charge_id, charge in self._charges.items():
            if charge.event_type == "provisional" and charge.status == "reserved":
                if charge.expires_at and charge.expires_at < now:
                    charge.status = "expired"
                    released.append(charge_id)
                    
        return released

    def get_charge(self, event_id: str) -> Optional[ChargeEvent]:
        """Retrieve a charge by ID."""
        return self._charges.get(event_id)
