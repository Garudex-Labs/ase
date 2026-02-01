
import sys
import os
import json
from datetime import datetime, timezone
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from core.models import EconomicEvent, AuditBundle, MonetaryAmount
from core.audit import AuditManager
from crypto.signing import SigningService, SignatureAlgorithm, SignerResult

# Mock signing service
class MockSigningService(SigningService):
    def sign(self, data: bytes, key_id: str, algorithm: SignatureAlgorithm) -> SignerResult:
        return SignerResult(
            signature="mock_signature",
            algorithm=algorithm,
            key_id=key_id
        )

    def verify(self, data: bytes, signature: str, key_id: str, algorithm: SignatureAlgorithm):
        pass

def test_audit_flow():
    signer = MockSigningService()
    manager = AuditManager(signing_service=signer)

    # Create an event
    event = EconomicEvent(
        eventId="evt_1",
        eventType="cost_declaration",
        timestamp=datetime.now(timezone.utc),
        agentId="agent_1",
        amount=MonetaryAmount(value="10.00", currency="USD"),
        currency="USD",
        metadata={"foo": "bar"}
    )

    manager.log_event(event)

    bundle = manager.generate_bundle(agent_id="agent_1", key_id="key_1")

    print(f"Generated Bundle ID: {bundle.bundle_id}")
    print(f"Transactions: {len(bundle.transactions)}")
    print(f"Summary: {bundle.summary}")
    print(f"Signature: {bundle.signature}")

    # Verify JSON serialization
    json_out = bundle.model_dump_json(by_alias=True)
    print("JSON Output:", json_out)
    
    data = json.loads(json_out)
    assert data["transactions"][0]["eventId"] == "evt_1"
    assert data["summary"]["totalTransactions"] == 1
    assert data["generatedBy"] == "agent_1"

if __name__ == "__main__":
    test_audit_flow()
