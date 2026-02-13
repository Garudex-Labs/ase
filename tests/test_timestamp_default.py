#!/usr/bin/env python3
"""Test that MeteringEvent timestamp defaults to current time."""

from decimal import Decimal
from datetime import datetime
import sys
sys.path.insert(0, 'src')

from ase.protocol import MeteringEvent

# Test 1: Create MeteringEvent without timestamp
print("Test 1: Creating MeteringEvent without timestamp...")
event1 = MeteringEvent(
    agent_id="test-agent-123",
    resource_type="api.call",
    quantity=Decimal("100")
)
print(f"✓ Event created successfully")
print(f"  agent_id: {event1.agent_id}")
print(f"  resource_type: {event1.resource_type}")
print(f"  quantity: {event1.quantity}")
print(f"  timestamp: {event1.timestamp}")
print(f"  timestamp type: {type(event1.timestamp)}")

# Verify timestamp is a datetime
assert isinstance(event1.timestamp, datetime), "Timestamp should be a datetime object"
print("✓ Timestamp is a datetime object")

# Verify timestamp is recent (within last 5 seconds)
now = datetime.utcnow()
time_diff = (now - event1.timestamp).total_seconds()
assert time_diff < 5, f"Timestamp should be recent, but was {time_diff} seconds ago"
print(f"✓ Timestamp is recent ({time_diff:.3f} seconds ago)")

# Test 2: Create MeteringEvent with explicit timestamp
print("\nTest 2: Creating MeteringEvent with explicit timestamp...")
explicit_time = datetime(2025, 1, 1, 12, 0, 0)
event2 = MeteringEvent(
    agent_id="test-agent-456",
    resource_type="api.call",
    quantity=Decimal("200"),
    timestamp=explicit_time
)
print(f"✓ Event created successfully")
print(f"  timestamp: {event2.timestamp}")
assert event2.timestamp == explicit_time, "Explicit timestamp should be preserved"
print("✓ Explicit timestamp preserved")

# Test 3: Create MeteringEvent with metadata
print("\nTest 3: Creating MeteringEvent with metadata and no timestamp...")
event3 = MeteringEvent(
    agent_id="test-agent-789",
    resource_type="openai.gpt4.input_tokens",
    quantity=Decimal("1000"),
    metadata={"model": "gpt-4", "purpose": "test"}
)
print(f"✓ Event created successfully")
print(f"  timestamp: {event3.timestamp}")
print(f"  metadata: {event3.metadata}")
assert isinstance(event3.timestamp, datetime), "Timestamp should be a datetime object"
print("✓ Timestamp defaulted correctly with metadata")

print("\n" + "="*60)
print("ALL TESTS PASSED! ✓")
print("="*60)
print("\nMeteringEvent now supports optional timestamp with automatic default.")
print("Version 1.2.0 is ready for local testing.")
