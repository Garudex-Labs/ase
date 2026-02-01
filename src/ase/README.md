# ASE Reference Implementation

This directory contains the Python reference implementation of the Agent Settlement Extension (ASE) protocol.

## Overview

The reference implementation provides:

1. **Core Message Processing** - Serialization, deserialization, and validation
2. **Cryptographic Services** - Signing, verification, and key management
3. **Framework Adapters** - Integration with LangChain and AutoGPT

## Architecture

### Core Components (`core/`)

#### Serialization (`core/serialization.py`)

Handles automatic conversion between internal snake_case representation and wire format camelCase:

```python
from src.core import MessageSerializer, MessageDeserializer, SerializableModel

# Define a model
class ChargeEvent(SerializableModel):
    event_id: str = Field(..., alias="eventId")
    agent_id: str = Field(..., alias="agentId")

# Serialize to JSON (camelCase)
event = ChargeEvent(event_id="evt_123", agent_id="agent_456")
json_str = event.to_json()  # {"eventId": "evt_123", "agentId": "agent_456"}

# Deserialize from JSON (accepts both formats)
event = ChargeEvent.from_json(json_str)
print(event.event_id)  # Access using snake_case
```

#### Validation (`core/validation.py`)

Provides a flexible validation pipeline with error handling:

```python
from src.core import ValidationPipeline, SchemaValidator, ValidationResult

# Create validation pipeline
pipeline = ValidationPipeline()
pipeline.add_validator(SchemaValidator(schema, name="charge_event"))

# Validate data
result = pipeline.validate(data)
if result.has_errors():
    for error in result.get_errors():
        print(f"{error.code}: {error.message}")
```

#### Extensions (`core/extensions.py`)

Plugin architecture for extending ASE functionality:

```python
from src.core import ExtensionRegistry, Extension, ExtensionPointType

# Create custom extension
class MyExtension(Extension):
    @property
    def name(self) -> str:
        return "my_extension"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def execute(self, data, context=None):
        # Custom logic
        return data

# Register extension
registry = ExtensionRegistry()
registry.register_extension("pre_validation", MyExtension())
```

### Cryptographic Services (`crypto/`)

#### Signing and Verification (`crypto/signing.py`)

Cryptographic signing for delegation tokens and audit bundles:

```python
from src.crypto import SigningService, VerificationService, SignatureAlgorithm

# Sign data
signing_service = DefaultSigningService(key_manager)
result = signing_service.sign(
    data=b"message",
    key_id="key_001",
    algorithm=SignatureAlgorithm.ES256
)

# Verify signature
verification_service = DefaultVerificationService(key_manager)
result = verification_service.verify(
    data=b"message",
    signature=result.signature,
    key_id="key_001",
    algorithm=SignatureAlgorithm.ES256
)
```

#### Key Management (`crypto/keys.py`)

Key and certificate management:

```python
from src.crypto import KeyManager, KeyType

# Generate key
key_manager = InMemoryKeyManager()
key_pair = key_manager.generate_key(
    key_id="key_001",
    key_type=KeyType.EC_P256
)

# Rotate key
new_key = key_manager.rotate_key(
    old_key_id="key_001",
    new_key_id="key_002",
    overlap_period_days=30
)
```

#### Token Operations (`crypto/tokens.py`)

JWT-based delegation token creation and validation:

```python
from src.crypto import TokenSigner, TokenVerifier

# Create delegation token
signer = TokenSigner(signing_service)
token = signer.create_delegation_token(
    delegating_agent_id="agent_001",
    delegated_agent_id="agent_002",
    spending_limit_value="100.00",
    spending_limit_currency="USD",
    allowed_operations=["read", "write"],
    budget_category="compute",
    key_id="key_001",
    validity_hours=24
)

# Verify token
verifier = TokenVerifier(verification_service)
claims = verifier.verify_token(token)
print(f"Delegated to: {claims.sub}")
print(f"Spending limit: {claims.spending_limit}")
```

### Framework Adapters (`adapters/`)

#### LangChain Adapter (`adapters/langchain.py`)

Integration with LangChain framework:

```python
from src.adapters import LangChainAdapter

adapter = LangChainAdapter()

# Wrap message with ASE metadata
wrapped = adapter.wrap_message(
    message=langchain_message,
    economic_metadata={
        "version": "1.0.0",
        "agentIdentity": {"agentId": "agent_001"}
    }
)

# Extract metadata
message, metadata = adapter.unwrap_message(wrapped)

# Attach delegation token
message_with_token = adapter.attach_delegation_token(message, token)

# Create charge event
charge = adapter.create_charge_event(
    event_type="provisional",
    amount={"value": "10.00", "currency": "USD"},
    agent_id="agent_001",
    description="API call"
)
```

#### AutoGPT Adapter (`adapters/autogpt.py`)

Integration with AutoGPT framework:

```python
from src.adapters import AutoGPTAdapter

adapter = AutoGPTAdapter()

# Wrap message with ASE metadata
wrapped = adapter.wrap_message(
    message=autogpt_message,
    economic_metadata={
        "version": "1.0.0",
        "agentIdentity": {"agentId": "agent_001"}
    }
)

# Wrap command
wrapped_command = adapter.wrap_command(
    command={"name": "execute", "args": {}},
    economic_metadata=metadata
)
```

## Naming Conventions

The reference implementation uses a dual naming convention:

- **Internal (Python)**: snake_case for all code, variables, and attributes
- **Wire Format (JSON)**: camelCase for all JSON field names
- **Automatic Conversion**: Pydantic Field aliases handle conversion

Example:
```python
# Internal Python code
charge_event.event_id = "evt_123"
charge_event.agent_id = "agent_456"

# JSON output (automatic)
# {"eventId": "evt_123", "agentId": "agent_456"}
```

## Extension Points

The reference implementation provides several extension points:

1. **Pre-Serialization** - Modify data before JSON serialization
2. **Post-Deserialization** - Process data after JSON deserialization
3. **Pre-Validation** - Custom validation before standard validation
4. **Post-Validation** - Process validation results
5. **Charge Event Created** - React to charge event creation
6. **Delegation Token Validated** - React to token validation
7. **Audit Bundle Generated** - React to audit bundle generation
8. **Dispute Event Created** - React to dispute creation

## Testing

Property-based tests validate correctness properties:

```bash
# Run all tests
python3 -m pytest ase/tests/ -v

# Run specific test
python3 -m pytest ase/tests/test_framework_integration.py -v

# Run with hypothesis statistics
python3 -m pytest ase/tests/ -v --hypothesis-show-statistics
```

## Requirements

- Python 3.8+
- pydantic >= 2.0
- hypothesis >= 6.100.0 (for testing)
- pytest >= 8.0.0 (for testing)

## Usage Examples

### Complete Workflow Example

```python
from src.core import MessageSerializer, ValidationPipeline
from src.crypto import InMemoryKeyManager, DefaultSigningService, TokenSigner
from src.adapters import LangChainAdapter

# Setup
key_manager = InMemoryKeyManager()
key_pair = key_manager.generate_key("key_001", KeyType.EC_P256)
signing_service = DefaultSigningService(key_manager)
token_signer = TokenSigner(signing_service)
adapter = LangChainAdapter()

# Create delegation token
token = token_signer.create_delegation_token(
    delegating_agent_id="parent_agent",
    delegated_agent_id="child_agent",
    spending_limit_value="100.00",
    spending_limit_currency="USD",
    allowed_operations=["read", "write"],
    budget_category="compute",
    key_id="key_001"
)

# Create message with token
message = {"content": "Execute task", "type": "human"}
message_with_token = adapter.attach_delegation_token(message, token)

# Create charge event
charge = adapter.create_charge_event(
    event_type="provisional",
    amount={"value": "5.00", "currency": "USD"},
    agent_id="child_agent",
    description="Task execution"
)

# Wrap message with charge event
wrapped = adapter.wrap_message(
    message_with_token,
    economic_metadata={
        "version": "1.0.0",
        "chargeEvent": charge
    }
)
```

## Contributing

When extending the reference implementation:

1. Follow snake_case for internal Python code
2. Use Pydantic Field aliases for camelCase JSON output
3. Add property-based tests for new functionality
4. Document extension points and interfaces
5. Maintain backward compatibility
