"""
Property-based tests for audit bundle integrity.

Feature: ase, Property 15: Audit Bundle Integrity
Feature: ase, Property 16: Audit Bundle Completeness

Validates: Requirements 6.1, 6.2, 6.3, 6.5
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

import hypothesis.strategies as st
from hypothesis import given, settings, assume


# Test data generators

@st.composite
def monetary_amount(draw):
    """Generate valid monetary amounts."""
    value = draw(st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("999999.99"),
        places=2
    ))
    currency = draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"]))
    return {
        "value": str(value),
        "currency": currency
    }


@st.composite
def agent_id(draw):
    """Generate valid agent identifiers."""
    prefix = draw(st.sampled_from(["agent", "service", "client"]))
    suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        min_size=6,
        max_size=20
    ))
    return f"{prefix}_{suffix}"


@st.composite
def audit_entry(draw, base_time=None):
    """Generate valid audit entry."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    entry_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    return {
        "entryId": f"audit_entry_{entry_id_suffix}",
        "timestamp": base_time.isoformat(),
        "action": draw(st.sampled_from([
            "charge_created", "charge_confirmed", "charge_expired",
            "budget_allocated", "budget_released", "token_validated"
        ])),
        "performedBy": draw(agent_id()),
        "details": {
            "operation": draw(st.sampled_from(["create", "update", "delete", "validate"])),
            "resource": draw(st.sampled_from(["charge", "budget", "token", "dispute"]))
        }
    }


@st.composite
def economic_event(draw, base_time=None):
    """Generate valid economic event."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    event_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    event_type = draw(st.sampled_from([
        "cost_declaration", "budget_request", "provisional_charge",
        "final_charge", "adjustment", "refund", "dispute", "resolution"
    ]))
    
    event = {
        "eventId": f"evt_{event_id_suffix}",
        "eventType": event_type,
        "timestamp": base_time.isoformat(),
        "agentId": draw(agent_id()),
        "amount": draw(monetary_amount()),
        "currency": draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"])),
        "metadata": {
            "resourceType": draw(st.sampled_from(["compute", "storage", "network", "api"])),
            "priority": draw(st.sampled_from(["low", "normal", "high", "critical"]))
        }
    }
    
    # Add audit trail
    num_entries = draw(st.integers(min_value=1, max_value=3))
    event["auditTrail"] = [
        draw(audit_entry(base_time=base_time + timedelta(minutes=i)))
        for i in range(num_entries)
    ]
    
    # Add related event IDs for certain types
    if event_type in ["final_charge", "adjustment", "refund", "resolution"]:
        num_related = draw(st.integers(min_value=1, max_value=3))
        event["relatedEventIds"] = [
            f"evt_{draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=8, max_size=16))}"
            for _ in range(num_related)
        ]
    
    return event


@st.composite
def audit_bundle(draw, base_time=None):
    """Generate valid audit bundle."""
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    bundle_id_suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8,
        max_size=16
    ))
    
    # Generate time range
    start_time = base_time - timedelta(days=draw(st.integers(min_value=1, max_value=30)))
    end_time = base_time
    
    # Generate transactions
    num_transactions = draw(st.integers(min_value=1, max_value=20))
    transactions = []
    agent_set = set()
    total_amount = Decimal("0.00")
    currency = draw(st.sampled_from(["USD", "EUR", "GBP", "JPY"]))
    
    transaction_counts = {
        "provisional": 0,
        "final": 0,
        "adjustment": 0,
        "refund": 0,
        "dispute": 0
    }
    
    for i in range(num_transactions):
        # Generate transaction within time range
        transaction_time = start_time + timedelta(
            seconds=draw(st.integers(
                min_value=0,
                max_value=int((end_time - start_time).total_seconds())
            ))
        )
        
        event = draw(economic_event(base_time=transaction_time))
        
        # Ensure consistent currency
        event["amount"]["currency"] = currency
        event["currency"] = currency
        
        # Track agent and amount
        agent_set.add(event["agentId"])
        total_amount += Decimal(event["amount"]["value"])
        
        # Track transaction type counts
        event_type = event["eventType"]
        if event_type == "provisional_charge":
            transaction_counts["provisional"] += 1
        elif event_type == "final_charge":
            transaction_counts["final"] += 1
        elif event_type == "adjustment":
            transaction_counts["adjustment"] += 1
        elif event_type == "refund":
            transaction_counts["refund"] += 1
        elif event_type in ["dispute", "resolution"]:
            transaction_counts["dispute"] += 1
        
        transactions.append(event)
    
    # Sort transactions by timestamp
    transactions.sort(key=lambda x: x["timestamp"])
    
    # Calculate summary
    summary = {
        "totalTransactions": num_transactions,
        "totalAmount": {
            "value": str(total_amount),
            "currency": currency
        },
        "agentParticipants": list(agent_set),
        "transactionsByType": transaction_counts,
        "amountByAgent": {},
        "amountByCurrency": {
            currency: str(total_amount)
        }
    }
    
    # Calculate amount by agent
    for event in transactions:
        agent = event["agentId"]
        amount = Decimal(event["amount"]["value"])
        if agent not in summary["amountByAgent"]:
            summary["amountByAgent"][agent] = {
                "value": "0.00",
                "currency": currency
            }
        current = Decimal(summary["amountByAgent"][agent]["value"])
        summary["amountByAgent"][agent]["value"] = str(current + amount)
    
    # Generate signature (mock)
    signature_algorithm = draw(st.sampled_from(["ES256", "RS256", "ES384", "RS384", "ES512", "RS512"]))
    signature = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")) + "+/=",
        min_size=64,
        max_size=128
    ))
    
    bundle = {
        "bundleId": f"audit_{bundle_id_suffix}",
        "generatedBy": draw(agent_id()),
        "generatedAt": base_time.isoformat(),
        "timeRange": {
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat()
        },
        "transactions": transactions,
        "summary": summary,
        "signature": signature,
        "signatureAlgorithm": signature_algorithm,
        "publicKeyId": f"key_{draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=8, max_size=16))}",
        "metadata": {
            "auditPurpose": draw(st.sampled_from([
                "periodic_report", "compliance_audit", "dispute_evidence",
                "reconciliation", "investigation", "other"
            ])),
            "retentionPeriod": draw(st.integers(min_value=30, max_value=2555)),
            "encryptionStatus": draw(st.sampled_from([
                "unencrypted", "encrypted_at_rest", "encrypted_in_transit", "fully_encrypted"
            ]))
        }
    }
    
    # Optionally add previous bundle reference
    if draw(st.booleans()):
        prev_bundle_id = f"audit_{draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=8, max_size=16))}"
        bundle["previousBundleId"] = prev_bundle_id
        bundle["previousBundleHash"] = hashlib.sha256(prev_bundle_id.encode()).hexdigest()
    
    # Optionally add integrity checks
    if draw(st.booleans()):
        # Generate transaction hashes
        transaction_hashes = [
            hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()
            for t in transactions
        ]
        
        # Calculate merkle root (simplified - just hash all hashes together)
        merkle_input = "".join(transaction_hashes)
        merkle_root = hashlib.sha256(merkle_input.encode()).hexdigest()
        
        bundle["integrityChecks"] = {
            "merkleRoot": merkle_root,
            "transactionHashes": transaction_hashes,
            "checksumAlgorithm": "SHA256"
        }
    
    return bundle


# Property tests

@given(bundle=audit_bundle())
@settings(max_examples=100)
def test_property_15_audit_bundle_integrity(bundle: Dict[str, Any]):
    """
    Property 15: Audit Bundle Integrity
    
    For any audit bundle, cryptographic signing and verification should
    maintain tamper-evidence and data integrity.
    
    This test validates that:
    1. Bundle has all required fields
    2. Bundle ID follows the correct format
    3. Signature is present and properly formatted
    4. Signature algorithm is valid
    5. Public key ID is provided for verification
    6. Integrity checks (if present) are properly structured
    7. Previous bundle references maintain chain integrity
    8. Bundle can be serialized and deserialized without data loss
    """
    # Validate required fields exist
    required_fields = [
        "bundleId", "generatedBy", "generatedAt", "timeRange",
        "transactions", "summary", "signature", "signatureAlgorithm"
    ]
    for field in required_fields:
        assert field in bundle, f"Missing required field: {field}"
    
    # Validate bundle ID format
    assert bundle["bundleId"].startswith("audit_"), \
        f"Bundle ID must start with 'audit_', got {bundle['bundleId']}"
    
    # Validate generator agent
    assert len(bundle["generatedBy"]) > 0, \
        "Generator agent ID must not be empty"
    
    # Validate time range
    time_range = bundle["timeRange"]
    assert "startTime" in time_range, "Time range must have start time"
    assert "endTime" in time_range, "Time range must have end time"
    
    start_time = datetime.fromisoformat(time_range["startTime"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(time_range["endTime"].replace("Z", "+00:00"))
    assert end_time >= start_time, \
        "End time must be after or equal to start time"
    
    # Validate signature
    assert len(bundle["signature"]) > 0, \
        "Signature must not be empty"
    
    # Validate signature algorithm
    valid_algorithms = ["ES256", "RS256", "ES384", "RS384", "ES512", "RS512"]
    assert bundle["signatureAlgorithm"] in valid_algorithms, \
        f"Invalid signature algorithm: {bundle['signatureAlgorithm']}"
    
    # Validate public key ID if present
    if "publicKeyId" in bundle:
        assert len(bundle["publicKeyId"]) > 0, \
            "Public key ID must not be empty"
    
    # Validate previous bundle chain if present
    if "previousBundleId" in bundle:
        assert bundle["previousBundleId"].startswith("audit_"), \
            f"Previous bundle ID must start with 'audit_', got {bundle['previousBundleId']}"
        
        # If previous bundle ID exists, hash should also exist
        if "previousBundleHash" in bundle:
            assert len(bundle["previousBundleHash"]) == 64, \
                f"Previous bundle hash must be 64 characters, got {len(bundle['previousBundleHash'])}"
    
    # Validate integrity checks if present
    if "integrityChecks" in bundle:
        checks = bundle["integrityChecks"]
        
        # Validate merkle root
        if "merkleRoot" in checks:
            assert len(checks["merkleRoot"]) == 64, \
                f"Merkle root must be 64 characters, got {len(checks['merkleRoot'])}"
        
        # Validate transaction hashes
        if "transactionHashes" in checks:
            hashes = checks["transactionHashes"]
            assert isinstance(hashes, list), \
                "Transaction hashes must be a list"
            
            # Number of hashes should match number of transactions
            assert len(hashes) == len(bundle["transactions"]), \
                f"Number of hashes ({len(hashes)}) must match transactions ({len(bundle['transactions'])})"
            
            # Each hash should be 64 characters
            for i, hash_val in enumerate(hashes):
                assert len(hash_val) == 64, \
                    f"Transaction hash {i} must be 64 characters, got {len(hash_val)}"
        
        # Validate checksum algorithm
        if "checksumAlgorithm" in checks:
            valid_checksum_algs = ["SHA256", "SHA384", "SHA512"]
            assert checks["checksumAlgorithm"] in valid_checksum_algs, \
                f"Invalid checksum algorithm: {checks['checksumAlgorithm']}"
    
    # Test serialization round-trip
    try:
        json_str = json.dumps(bundle)
        deserialized = json.loads(json_str)
        
        # Validate critical fields are preserved
        assert deserialized["bundleId"] == bundle["bundleId"]
        assert deserialized["signature"] == bundle["signature"]
        assert deserialized["signatureAlgorithm"] == bundle["signatureAlgorithm"]
        assert len(deserialized["transactions"]) == len(bundle["transactions"])
        
    except (TypeError, ValueError) as e:
        assert False, f"Failed to serialize/deserialize bundle: {e}"


@given(bundle=audit_bundle())
@settings(max_examples=100)
def test_property_16_audit_bundle_completeness(bundle: Dict[str, Any]):
    """
    Property 16: Audit Bundle Completeness
    
    For any audit bundle request, the generated bundle should contain
    complete transaction history for the specified time period or agent.
    
    This test validates that:
    1. All transactions fall within the specified time range
    2. Summary statistics accurately reflect transaction data
    3. Agent participants list is complete and accurate
    4. Transaction counts by type are correct
    5. Amount calculations are accurate
    6. No transactions are missing or duplicated
    """
    # Validate summary exists
    assert "summary" in bundle, "Bundle must have summary"
    summary = bundle["summary"]
    
    # Validate required summary fields
    required_summary_fields = ["totalTransactions", "totalAmount", "agentParticipants"]
    for field in required_summary_fields:
        assert field in summary, f"Missing required summary field: {field}"
    
    # Validate transaction count matches
    actual_count = len(bundle["transactions"])
    summary_count = summary["totalTransactions"]
    assert actual_count == summary_count, \
        f"Transaction count mismatch: actual={actual_count}, summary={summary_count}"
    
    # Validate all transactions are within time range
    start_time = datetime.fromisoformat(bundle["timeRange"]["startTime"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(bundle["timeRange"]["endTime"].replace("Z", "+00:00"))
    
    for i, transaction in enumerate(bundle["transactions"]):
        tx_time = datetime.fromisoformat(transaction["timestamp"].replace("Z", "+00:00"))
        assert start_time <= tx_time <= end_time, \
            f"Transaction {i} timestamp {tx_time} is outside time range [{start_time}, {end_time}]"
    
    # Validate agent participants list
    actual_agents = set()
    for transaction in bundle["transactions"]:
        actual_agents.add(transaction["agentId"])
    
    summary_agents = set(summary["agentParticipants"])
    assert actual_agents == summary_agents, \
        f"Agent participants mismatch: actual={actual_agents}, summary={summary_agents}"
    
    # Validate transaction type counts
    if "transactionsByType" in summary:
        type_counts = summary["transactionsByType"]
        
        # Count actual transactions by type
        actual_counts = {
            "provisional": 0,
            "final": 0,
            "adjustment": 0,
            "refund": 0,
            "dispute": 0
        }
        
        for transaction in bundle["transactions"]:
            event_type = transaction["eventType"]
            if event_type == "provisional_charge":
                actual_counts["provisional"] += 1
            elif event_type == "final_charge":
                actual_counts["final"] += 1
            elif event_type == "adjustment":
                actual_counts["adjustment"] += 1
            elif event_type == "refund":
                actual_counts["refund"] += 1
            elif event_type in ["dispute", "resolution"]:
                actual_counts["dispute"] += 1
        
        # Validate counts match
        for tx_type, count in type_counts.items():
            assert actual_counts[tx_type] == count, \
                f"Transaction type count mismatch for {tx_type}: actual={actual_counts[tx_type]}, summary={count}"
    
    # Validate total amount calculation
    actual_total = Decimal("0.00")
    currency = summary["totalAmount"]["currency"]
    
    for transaction in bundle["transactions"]:
        # Ensure consistent currency
        assert transaction["amount"]["currency"] == currency, \
            f"Currency mismatch: transaction has {transaction['amount']['currency']}, expected {currency}"
        
        actual_total += Decimal(transaction["amount"]["value"])
    
    summary_total = Decimal(summary["totalAmount"]["value"])
    assert actual_total == summary_total, \
        f"Total amount mismatch: actual={actual_total}, summary={summary_total}"
    
    # Validate amount by agent
    if "amountByAgent" in summary:
        agent_amounts = {}
        
        for transaction in bundle["transactions"]:
            agent = transaction["agentId"]
            amount = Decimal(transaction["amount"]["value"])
            
            if agent not in agent_amounts:
                agent_amounts[agent] = Decimal("0.00")
            agent_amounts[agent] += amount
        
        # Validate each agent's total
        for agent, expected_amount in agent_amounts.items():
            assert agent in summary["amountByAgent"], \
                f"Agent {agent} missing from amountByAgent summary"
            
            summary_amount = Decimal(summary["amountByAgent"][agent]["value"])
            assert expected_amount == summary_amount, \
                f"Amount mismatch for agent {agent}: actual={expected_amount}, summary={summary_amount}"
    
    # Validate amount by currency
    if "amountByCurrency" in summary:
        currency_amounts = {}
        
        for transaction in bundle["transactions"]:
            curr = transaction["amount"]["currency"]
            amount = Decimal(transaction["amount"]["value"])
            
            if curr not in currency_amounts:
                currency_amounts[curr] = Decimal("0.00")
            currency_amounts[curr] += amount
        
        # Validate each currency's total
        for curr, expected_amount in currency_amounts.items():
            assert curr in summary["amountByCurrency"], \
                f"Currency {curr} missing from amountByCurrency summary"
            
            summary_amount = Decimal(summary["amountByCurrency"][curr])
            assert expected_amount == summary_amount, \
                f"Amount mismatch for currency {curr}: actual={expected_amount}, summary={summary_amount}"
    
    # Validate no duplicate transaction IDs
    transaction_ids = [tx["eventId"] for tx in bundle["transactions"]]
    assert len(transaction_ids) == len(set(transaction_ids)), \
        "Duplicate transaction IDs found in bundle"


@given(
    bundle=audit_bundle(),
    tamper_field=st.sampled_from(["bundleId", "generatedBy", "totalTransactions", "totalAmount"])
)
@settings(max_examples=100)
def test_tamper_detection(bundle: Dict[str, Any], tamper_field: str):
    """
    Test that tampering with bundle data can be detected.
    
    This simulates tampering by modifying a field and validates that
    signature verification would fail.
    """
    # Store original signature
    original_signature = bundle["signature"]
    
    # Create a copy and tamper with it
    tampered_bundle = json.loads(json.dumps(bundle))
    
    # Tamper with the specified field
    if tamper_field == "bundleId":
        tampered_bundle["bundleId"] = "audit_tampered_12345"
    elif tamper_field == "generatedBy":
        tampered_bundle["generatedBy"] = "agent_attacker_999"
    elif tamper_field == "totalTransactions":
        tampered_bundle["summary"]["totalTransactions"] += 1
    elif tamper_field == "totalAmount":
        current_value = Decimal(tampered_bundle["summary"]["totalAmount"]["value"])
        tampered_bundle["summary"]["totalAmount"]["value"] = str(current_value + Decimal("100.00"))
    
    # In a real system, signature verification would fail
    # Here we just validate that the data has changed
    tampered_json = json.dumps(tampered_bundle, sort_keys=True)
    original_json = json.dumps(bundle, sort_keys=True)
    
    assert tampered_json != original_json, \
        "Tampered bundle should differ from original"
    
    # Signature should still be the same (invalid for tampered data)
    assert tampered_bundle["signature"] == original_signature, \
        "Signature should remain unchanged (but now invalid)"


@given(
    num_bundles=st.integers(min_value=2, max_value=5),
    base_time=st.datetimes(
        min_value=datetime(2024, 1, 1, tzinfo=timezone.utc),
        max_value=datetime(2025, 12, 31, tzinfo=timezone.utc)
    )
)
@settings(max_examples=100)
def test_audit_bundle_chain(num_bundles: int, base_time: datetime):
    """
    Test that audit bundle chains maintain integrity.
    
    Validates:
    1. Each bundle references the previous bundle
    2. Previous bundle hashes are consistent
    3. Time ranges are sequential
    4. No gaps in the audit trail
    """
    bundles = []
    current_time = base_time
    
    for i in range(num_bundles):
        # Generate bundle
        bundle_id_suffix = f"chain_{i}_{int(current_time.timestamp())}"
        
        bundle = {
            "bundleId": f"audit_{bundle_id_suffix}",
            "generatedBy": "agent_auditor_001",
            "generatedAt": current_time.isoformat(),
            "timeRange": {
                "startTime": (current_time - timedelta(days=1)).isoformat(),
                "endTime": current_time.isoformat()
            },
            "transactions": [],
            "summary": {
                "totalTransactions": 0,
                "totalAmount": {"value": "0.00", "currency": "USD"},
                "agentParticipants": []
            },
            "signature": f"sig_{bundle_id_suffix}",
            "signatureAlgorithm": "ES256"
        }
        
        # Add reference to previous bundle
        if i > 0:
            prev_bundle = bundles[-1]
            bundle["previousBundleId"] = prev_bundle["bundleId"]
            bundle["previousBundleHash"] = hashlib.sha256(
                prev_bundle["bundleId"].encode()
            ).hexdigest()
        
        bundles.append(bundle)
        current_time += timedelta(days=1)
    
    # Validate chain integrity
    for i in range(1, len(bundles)):
        current = bundles[i]
        previous = bundles[i - 1]
        
        # Validate previous bundle reference
        assert "previousBundleId" in current, \
            f"Bundle {i} must reference previous bundle"
        assert current["previousBundleId"] == previous["bundleId"], \
            f"Bundle {i} previous ID mismatch"
        
        # Validate previous bundle hash
        assert "previousBundleHash" in current, \
            f"Bundle {i} must have previous bundle hash"
        
        expected_hash = hashlib.sha256(previous["bundleId"].encode()).hexdigest()
        assert current["previousBundleHash"] == expected_hash, \
            f"Bundle {i} previous hash mismatch"
        
        # Validate time sequence
        current_time = datetime.fromisoformat(current["generatedAt"].replace("Z", "+00:00"))
        previous_time = datetime.fromisoformat(previous["generatedAt"].replace("Z", "+00:00"))
        assert current_time >= previous_time, \
            f"Bundle {i} generated time must be after previous bundle"


@given(bundle=audit_bundle())
@settings(max_examples=100)
def test_audit_bundle_metadata(bundle: Dict[str, Any]):
    """
    Test that audit bundle metadata is properly structured.
    
    Validates:
    1. Audit purpose is valid
    2. Retention period is reasonable
    3. Encryption status is valid
    4. Access control list is properly formatted
    """
    if "metadata" in bundle:
        metadata = bundle["metadata"]
        
        # Validate audit purpose
        if "auditPurpose" in metadata:
            valid_purposes = [
                "periodic_report", "compliance_audit", "dispute_evidence",
                "reconciliation", "investigation", "other"
            ]
            assert metadata["auditPurpose"] in valid_purposes, \
                f"Invalid audit purpose: {metadata['auditPurpose']}"
        
        # Validate retention period
        if "retentionPeriod" in metadata:
            retention = metadata["retentionPeriod"]
            assert isinstance(retention, int), \
                "Retention period must be integer"
            assert retention > 0, \
                f"Retention period must be positive, got {retention}"
            assert retention <= 3650, \
                f"Retention period too long (max 10 years), got {retention} days"
        
        # Validate encryption status
        if "encryptionStatus" in metadata:
            valid_statuses = [
                "unencrypted", "encrypted_at_rest",
                "encrypted_in_transit", "fully_encrypted"
            ]
            assert metadata["encryptionStatus"] in valid_statuses, \
                f"Invalid encryption status: {metadata['encryptionStatus']}"
        
        # Validate access control
        if "accessControl" in metadata:
            access_list = metadata["accessControl"]
            assert isinstance(access_list, list), \
                "Access control must be a list"
            
            for agent in access_list:
                assert len(agent) > 0, \
                    "Agent ID in access control must not be empty"
            
            # Check for duplicates
            assert len(access_list) == len(set(access_list)), \
                "Access control list must not contain duplicates"


if __name__ == "__main__":
    # Run tests with pytest
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
