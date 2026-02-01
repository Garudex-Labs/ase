# ASE Reference Implementation Architecture

## Overview

This document describes the reference implementation architecture for the Agent Settlement Extension (ASE) protocol. The implementation provides a complete Python reference that demonstrates how to integrate ASE economic metadata with existing agent frameworks while maintaining protocol compatibility.

## Implementation Structure

```
ase/
├── src/
│   ├── core/                    # Core message processing
│   │   ├── serialization.py     # Snake_case ↔ camelCase conversion
│   │   ├── validation.py        # Validation pipeline
│   │   └── extensions.py        # Plugin architecture
│   ├── crypto/                  # Cryptographic services
│   │   ├── signing.py           # Signing and verification
│   │   ├── keys.py              # Key management
│   │   └── tokens.py            # JWT delegation tokens
│   └── adapters/                # Framework adapters
│       ├── base.py              # Base adapter interface
│       ├── langchain.py         # LangChain integration
│       └── autogpt.py           # AutoGPT integration
├── tests/
│   └── test_framework_integration.py  # Property-based tests
└── schemas/                     # JSON schemas
```

## Key Design Decisions

### 1. Dual Naming Convention

**Problem**: Python ecosystem uses snake_case, but JSON APIs typically use camelCase.

**Solution**: Automatic conversion using Pydantic Field aliases:
- Internal Python code: `event_id`, `agent_id`, `spending_limit`
- JSON wire format: `eventId`, `agentId`, `spendingLimit`
- Bidirectional mapping ensures consistency

### 2. Validation Pipeline Architecture

**Problem**: Need flexible validation with error handling and extensibility.

**Solution**: Pipeline pattern with composable validators:
- Schema validation (JSON Schema)
- Semantic validation (business rules)
- Custom validators via extension points
- Detailed error reporting with field paths

### 3. Extension Point Mechanism

**Problem**: Need to support protocol customization without modifying core code.

**Solution**: Plugin architecture with predefined extension points:
- Pre/post serialization hooks
- Pre/post validation hooks
- Event-specific hooks (charge created, token validated, etc.)
- Custom extension registration

### 4. Framework Adapter Pattern

**Problem**: Different frameworks have different conventions for message structure and metadata.

**Solution**: Adapter pattern with framework-specific implementations:
- Base adapter interface defines common operations
- Framework-specific adapters maintain conventions
- Convention validators ensure compliance
- Message transformers handle format conversion

## Core Components

### Serialization Layer

**Purpose**: Handle conversion between internal and wire formats.

**Key Features**:
- Automatic snake_case ↔ camelCase conversion
- Pydantic-based model validation
- JSON serialization with proper formatting
- Support for both formats during deserialization

**Implementation Highlights**:
```python
class SerializableModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # Accept both formats
        use_enum_values=True,
        validate_assignment=True,
    )
```

### Validation Pipeline

**Purpose**: Provide flexible, composable validation.

**Key Features**:
- Multiple validators in sequence
- Fail-fast or collect-all-errors modes
- Pre/post validation hooks
- Detailed error reporting with severity levels

**Implementation Highlights**:
```python
class ValidationPipeline:
    def validate(self, data, context=None, raise_on_error=False):
        # Execute validators in sequence
        # Merge results
        # Execute hooks
        # Return combined result
```

### Extension Registry

**Purpose**: Enable protocol customization through plugins.

**Key Features**:
- Predefined extension points
- Custom extension registration
- Hook function support
- Global registry for convenience

**Implementation Highlights**:
```python
class ExtensionPoint:
    def execute(self, data, context=None):
        # Execute all registered extensions
        # Execute all registered hooks
        # Return modified data
```

## Cryptographic Services

### Signing Service

**Purpose**: Cryptographic signing for tokens and audit bundles.

**Supported Algorithms**:
- ES256 (ECDSA with P-256 and SHA-256)
- RS256 (RSA with SHA-256)
- ES384, RS384, ES512, RS512

**Key Features**:
- Abstract interface for implementation flexibility
- Support for HSM/KMS integration
- Canonical JSON serialization
- Signature metadata tracking

### Key Manager

**Purpose**: Manage cryptographic keys and certificates.

**Key Features**:
- Key generation and import
- Key rotation with overlap periods
- Certificate management
- In-memory implementation for testing

**Security Considerations**:
- Private keys should be stored securely (HSM recommended)
- Key rotation should be automated
- Certificate chain validation required
- Revocation checking supported

### Token Signer/Verifier

**Purpose**: Create and validate JWT delegation tokens.

**Key Features**:
- JWT-based token format
- Hierarchical delegation support
- Spending limit validation
- Operation authorization checking
- Delegation chain validation

## Framework Adapters

### Base Adapter Interface

**Purpose**: Define common interface for all framework adapters.

**Key Operations**:
- `wrap_message()` - Add ASE metadata to framework message
- `unwrap_message()` - Extract ASE metadata from message
- `attach_delegation_token()` - Add token to message
- `extract_delegation_token()` - Get token from message
- `create_charge_event()` - Create framework-compatible charge event
- `validate_framework_conventions()` - Ensure compliance

### LangChain Adapter

**Purpose**: Integrate ASE with LangChain framework.

**Convention**: Place ASE metadata in `additional_kwargs['aseMetadata']`

**Key Features**:
- Maintains LangChain message structure (content, type)
- Supports all LangChain message types
- Chain wrapper for automatic metadata handling
- Convention validation

### AutoGPT Adapter

**Purpose**: Integrate ASE with AutoGPT framework.

**Convention**: Place ASE metadata in `metadata['aseMetadata']`

**Key Features**:
- Maintains AutoGPT message structure (role, content)
- Supports all AutoGPT message roles
- Command wrapping for economic metadata
- Convention validation

## Testing Strategy

### Property-Based Testing

**Purpose**: Validate universal correctness properties.

**Test Coverage**:
- Framework convention adherence (Property 19)
- Message wrapping/unwrapping consistency
- Delegation token attachment/extraction
- Charge event creation
- Roundtrip consistency

**Configuration**:
- 100 examples per property
- Custom generators for ASE data types
- Hypothesis for randomized testing

### Test Data Generators

**Custom Strategies**:
- `economic_metadata()` - Valid ASE metadata
- `langchain_message()` - LangChain-style messages
- `autogpt_message()` - AutoGPT-style messages
- `delegation_token()` - Mock JWT tokens

## Implementation Guidelines

### For Protocol Implementers

1. **Use the serialization layer** for automatic naming conversion
2. **Extend the validation pipeline** for custom validation rules
3. **Register extensions** at appropriate extension points
4. **Follow framework conventions** when creating adapters
5. **Write property-based tests** for new functionality

### For Framework Integrators

1. **Create a framework adapter** extending `FrameworkAdapter`
2. **Implement message transformer** for format conversion
3. **Implement convention validator** for compliance checking
4. **Register hooks** for framework-specific behavior
5. **Test convention adherence** with property-based tests

### For Security-Conscious Deployments

1. **Replace InMemoryKeyManager** with HSM/KMS implementation
2. **Implement proper key rotation** procedures
3. **Enable certificate validation** for all signatures
4. **Use rate limiting** for token validation
5. **Audit all cryptographic operations**

## Performance Considerations

### Serialization

- Pydantic models are optimized for performance
- Caching can be added for frequently serialized objects
- Lazy validation can reduce overhead

### Validation

- Schema validation can be expensive for large messages
- Consider caching compiled schemas
- Use fail-fast mode when appropriate

### Cryptographic Operations

- Signature verification is CPU-intensive
- Consider caching verification results
- Use async operations for high-throughput scenarios

## Future Enhancements

### Planned Features

1. **Async support** - Async versions of all interfaces
2. **Caching layer** - Cache validation results and signatures
3. **Metrics collection** - Built-in metrics for monitoring
4. **Additional adapters** - Support for more frameworks
5. **HSM integration** - Production-ready key management

### Extension Opportunities

1. **Custom validators** - Domain-specific validation rules
2. **Custom extensions** - Protocol customization
3. **Custom adapters** - Framework-specific integration
4. **Custom key managers** - Cloud KMS integration

## References

- [ASE Protocol Specification](../docs/community/ase-protocol/specification.md)
- [Design Document](../.kiro/specs/ase/design.md)
- [Requirements Document](../.kiro/specs/ase/requirements.md)
- [Test Documentation](tests/README.md)
- [Implementation README](src/README.md)

## Compliance

This reference implementation validates:

- **Requirement 8.1**: Core message serialization and deserialization
- **Requirement 8.2**: Validation pipeline architecture and error handling
- **Requirement 8.3**: Cryptographic signing for tokens and audit bundles
- **Requirement 8.4**: LangChain adapter interface
- **Requirement 8.5**: AutoGPT adapter interface
- **Requirement 8.6**: Framework-specific convention adherence
- **Requirement 8.7**: Snake_case/camelCase conversion
- **Requirement 8.8**: Pydantic Field aliases for serialization
- **Requirement 8.9**: Bidirectional format support
- **Requirement 8.10**: JSON wire format compatibility

## Version

Reference Implementation Version: 1.0.1
ASE Protocol Version: 1.0.0

## Installation

The ASE protocol package is published on PyPI and can be installed using pip:

```bash
pip install ase-protocol==1.0.1
```

For development and testing, you can install from source:

```bash
git clone <repository-url>
cd ase
pip install -e .
```

Package URL: https://pypi.org/project/ase-protocol/1.0.1
