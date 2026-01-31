# ASE Protocol Reference

## Overview

The Agent Settlement Extension (ASE) is an economic metadata layer that extends existing agent-to-agent (A2A) and Model Control Protocol (MCP) communication protocols with economic semantics. This document provides a comprehensive reference for the ASE protocol specification.

## Quick Start

### Basic ASE Message

```json
{
  "message": {
    "type": "request",
    "content": "Process this data",
    "extensions": {
      "urn:ase:economic-metadata:v1": {
        "version": "1.0.0",
        "economicData": {
          "agentIdentity": {
            "agentId": "agent_abc123",
            "agentType": "autonomous"
          },
          "costDeclaration": {
            "costId": "cost_001",
            "amount": {
              "value": "50.00",
              "currency": "USD"
            },
            "pricingModel": "per_request"
          }
        }
      }
    }
  }
}
```

### Key Concepts

1. **Extension, Not Replacement**: ASE adds optional economic fields to existing protocols
2. **Backward Compatible**: Non-ASE agents can process ASE messages by ignoring economic fields
3. **Graceful Degradation**: Invalid economic metadata doesn't prevent message processing
4. **Protocol Agnostic**: Works with any A2A or MCP implementation

## Protocol Components

### 1. Economic Metadata Container

Top-level container for all ASE economic data:

```typescript
interface AseMetadata {
  version: string;              // ASE protocol version
  economicData: EconomicData;   // Economic metadata payload
  signature?: string;           // Optional cryptographic signature
}
```

### 2. Agent Identity

Required identification for cost attribution:

```typescript
interface AgentIdentity {
  agentId: string;              // Unique agent identifier
  agentType: AgentType;         // Agent classification
  organizationId?: string;      // Optional organization context
  settlementAccount?: string;   // Optional settlement account
  publicKey?: string;           // Optional public key
}
```

### 3. Cost Declaration

Declares costs for services or resources:

```typescript
interface CostDeclaration {
  costId: string;               // Unique cost identifier
  amount: MonetaryAmount;       // Cost amount
  pricingModel: PricingModel;   // Pricing model type
  description?: string;         // Optional description
  breakdown?: CostBreakdown[];  // Optional itemization
}
```

### 4. Budget Request

Requests budget allocation:

```typescript
interface BudgetRequest {
  requestId: string;            // Unique request identifier
  requestedAmount: MonetaryAmount;  // Requested amount
  budgetCategory: string;       // Budget category
  purpose: string;              // Purpose description
  timeframe?: Timeframe;        // Optional time constraints
}
```

### 5. Charge Event

Records provisional or final charges:

```typescript
interface ChargeEvent {
  eventId: string;              // Unique event identifier
  eventType: ChargeEventType;   // provisional | final | adjustment | refund
  timestamp: string;            // ISO 8601 timestamp
  agentId: string;              // Charged agent
  amount: MonetaryAmount;       // Charge amount
  description: string;          // Charge description
  provisionalChargeId?: string; // Reference to provisional charge
  expiresAt?: string;           // Expiration (provisional only)
  status: ChargeStatus;         // Charge status
}
```

### 6. Delegation Token

JWT-based hierarchical authorization:

```typescript
interface DelegationTokenPayload {
  // Standard JWT claims
  iss: string;                  // Issuer (delegating agent)
  sub: string;                  // Subject (delegated agent)
  exp: number;                  // Expiration timestamp
  
  // ASE-specific claims
  spendingLimit: MonetaryAmount;    // Maximum spending
  allowedOperations: string[];      // Permitted operations
  maxDelegationDepth: number;       // Max chain depth (1-5)
  budgetCategory: string;           // Budget category
}
```

### 7. Audit Reference

References audit bundles for compliance:

```typescript
interface AuditReference {
  auditBundleId: string;        // Audit bundle identifier
  bundleUri?: string;           // Optional retrieval URI
  transactionId: string;        // Transaction identifier
  timestamp: string;            // ISO 8601 timestamp
  signature: string;            // Cryptographic signature
  signatureAlgorithm: string;   // ES256 | RS256
}
```

## Protocol Extension Mechanisms

### A2A Protocol Integration

ASE uses the A2A extension framework:

```json
{
  "message": {
    "type": "request",
    "content": "...",
    "extensions": {
      "urn:ase:economic-metadata:v1": {
        "version": "1.0.0",
        "economicData": { ... }
      }
    }
  }
}
```

**Extension URI**: `urn:ase:economic-metadata:v1`

### MCP Protocol Integration

ASE adds optional fields to MCP messages:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "example_tool",
    "arguments": { ... },
    "aseMetadata": {
      "version": "1.0.0",
      "economicData": { ... }
    }
  }
}
```

## Validation Pipeline

Messages are validated in this order:

1. **Base Protocol Validation**: Ensure valid A2A/MCP message
2. **Structural Validation**: Verify ASE metadata structure
3. **Type Validation**: Check field types and formats
4. **Semantic Validation**: Enforce business rules
5. **Cryptographic Validation**: Verify signatures and tokens

**Critical Rule**: Validation errors NEVER prevent base protocol processing.

## Common Workflows

### Workflow 1: Simple Cost Declaration

```json
// Agent declares cost for service
{
  "aseMetadata": {
    "version": "1.0.0",
    "economicData": {
      "agentIdentity": {
        "agentId": "service_agent",
        "agentType": "service"
      },
      "costDeclaration": {
        "costId": "cost_001",
        "amount": { "value": "10.00", "currency": "USD" },
        "pricingModel": "per_request",
        "description": "API call processing"
      }
    }
  }
}
```

### Workflow 2: Provisional and Final Charges

```json
// Step 1: Create provisional charge (budget reservation)
{
  "chargeEvent": {
    "eventId": "evt_prov_001",
    "eventType": "provisional",
    "timestamp": "2024-01-31T10:00:00Z",
    "agentId": "client_agent",
    "amount": { "value": "100.00", "currency": "USD" },
    "description": "Provisional charge for ML inference",
    "expiresAt": "2024-01-31T11:00:00Z",
    "status": "reserved"
  }
}

// Step 2: Create final charge (actual consumption)
{
  "chargeEvent": {
    "eventId": "evt_final_001",
    "eventType": "final",
    "timestamp": "2024-01-31T10:30:00Z",
    "agentId": "client_agent",
    "amount": { "value": "95.50", "currency": "USD" },
    "description": "Final charge for ML inference",
    "provisionalChargeId": "evt_prov_001",
    "status": "confirmed"
  }
}
```

### Workflow 3: Delegation Token Usage

```json
// Parent agent creates delegation token
{
  "delegationToken": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJwYXJlbnRfYWdlbnQiLCJzdWIiOiJjaGlsZF9hZ2VudCIsImV4cCI6MTcwNjcxNjgwMCwic3BlbmRpbmdMaW1pdCI6eyJ2YWx1ZSI6IjEwMDAuMDAiLCJjdXJyZW5jeSI6IlVTRCJ9LCJhbGxvd2VkT3BlcmF0aW9ucyI6WyJyZWFkIiwid3JpdGUiXSwibWF4RGVsZWdhdGlvbkRlcHRoIjozLCJidWRnZXRDYXRlZ29yeSI6Im1sX2luZmVyZW5jZSJ9.signature"
}

// Child agent uses token in request
{
  "aseMetadata": {
    "version": "1.0.0",
    "economicData": {
      "agentIdentity": {
        "agentId": "child_agent",
        "agentType": "autonomous"
      },
      "delegationToken": "eyJhbGc...",
      "chargeEvent": {
        "eventId": "evt_001",
        "eventType": "final",
        "timestamp": "2024-01-31T10:00:00Z",
        "agentId": "child_agent",
        "amount": { "value": "50.00", "currency": "USD" },
        "description": "Charge under delegation",
        "status": "confirmed"
      }
    }
  }
}
```

## Security Considerations

### Rate Limiting

Delegation token validation is rate limited:
- Maximum 100 validation requests per minute per agent
- Maximum 50 validation requests per minute per IP
- Burst allowance of 10 requests within 10 seconds
- HTTP 429 response when limits exceeded

### Cryptographic Requirements

- **Signature Algorithms**: ES256 (ECDSA) or RS256 (RSA 2048-bit minimum)
- **Key Management**: Secure storage (HSM recommended)
- **Transport Security**: TLS 1.2 or higher required
- **Token Expiration**: All delegation tokens must have expiration

### Input Validation

- All monetary amounts validated for reasonable ranges
- Currency codes validated against ISO 4217
- Timestamps validated for reasonable time ranges
- String inputs sanitized to prevent injection attacks

## Error Handling

### Error Response Format

```json
{
  "aseError": {
    "code": "ASE_INVALID_MONETARY_AMOUNT",
    "message": "Invalid monetary amount format in cost declaration",
    "field": "economicData.costDeclaration.amount.value",
    "details": "Amount value must be a decimal string"
  }
}
```

### Common Error Codes

- `ASE_INVALID_VERSION`: Invalid version format
- `ASE_INVALID_STRUCTURE`: Invalid metadata structure
- `ASE_INVALID_AGENT_IDENTITY`: Invalid agent identity
- `ASE_INVALID_MONETARY_AMOUNT`: Invalid monetary amount
- `ASE_NEGATIVE_AMOUNT`: Negative amount where positive required
- `ASE_TOKEN_EXPIRED`: Delegation token expired
- `ASE_RATE_LIMIT_EXCEEDED`: Rate limit exceeded

## Version Compatibility

### Supported Versions

- **v1.0.0**: Current version with full feature set
- **v2.0.0**: Future version (planned)

### Version Negotiation

Agents should negotiate the highest mutually supported version:

```python
def negotiate_version(local_versions, remote_versions):
    common = set(local_versions) & set(remote_versions)
    return max(common) if common else None
```

### Backward Compatibility

- All ASE messages are valid base protocol messages
- Non-ASE agents can process ASE messages
- Invalid economic metadata doesn't prevent processing
- Newer versions support all features from older versions

## Implementation Checklist

- [ ] Parse ASE metadata from extension fields
- [ ] Validate message structure and types
- [ ] Enforce semantic validation rules
- [ ] Handle missing/invalid metadata gracefully
- [ ] Support delegation token validation
- [ ] Implement rate limiting for token validation
- [ ] Generate audit trails for economic events
- [ ] Support version negotiation
- [ ] Pass compatibility test suite
- [ ] Meet performance benchmarks (< 10% overhead)

## Resources

### Documentation

- [Full Specification](../docs/community/ase-protocol/specification.md)
- [Message Schema](../docs/community/ase-protocol/message-schema.md)
- [Validation Rules](../docs/community/ase-protocol/validation-rules.md)
- [Compatibility Guide](../docs/community/ase-protocol/compatibility.md)
- [Versioning](../docs/community/ase-protocol/versioning.md)

### JSON Schemas

- Located in `schemas/` directory
- Use for automated validation
- See `schemas/README.md` for usage examples

### Examples

- [LangChain Adapter](../docs/community/ase-protocol/examples/langchain-adapter.md)
- [AutoGPT Adapter](../docs/community/ase-protocol/examples/autogpt-adapter.md)

## Support

For questions, issues, or contributions:

- GitHub Issues: [ASE Protocol Issues](https://github.com/ase-protocol/ase/issues)
- Documentation: [ASE Protocol Docs](https://ase-protocol.org/docs)
- RFC Process: [ASE RFC Process](../docs/community/governance/ase-rfc-process.md)

## License

ASE Protocol is open source. See [LICENSE](LICENSE) for details.
