
import sys
import os

# Ensure we're testing the local source, not installed packages
sys.path.insert(0, os.path.abspath("src"))

try:
    print("Testing ASE imports...")
    from ase.protocol import MeteringEvent
    from ase.core.validation import validate_message
    print("SUCCESS: Imported MeteringEvent and validate_message")
    
    # Test instantiation
    from decimal import Decimal
    from datetime import datetime
    
    event = MeteringEvent(
        agent_id="test",
        resource_type="cpu",
        quantity=Decimal("1.0"),
        timestamp=datetime.now()
    )
    print("SUCCESS: Instantiated MeteringEvent")
    
    # Test validation function existence
    if not callable(validate_message):
        raise ImportError("validate_message is not callable")
    print("SUCCESS: validate_message is callable")
    
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
