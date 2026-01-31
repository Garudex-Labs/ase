# ASE JSON Schema Definitions

This directory contains formal JSON Schema definitions for all ASE protocol message types. These schemas are used for validation and documentation purposes.

## Schema Files

- `ase-metadata.schema.json` - Top-level ASE metadata container
- `economic-data.schema.json` - Economic data payload
- `agent-identity.schema.json` - Agent identification
- `monetary-amount.schema.json` - Monetary value representation
- `cost-declaration.schema.json` - Cost declarations
- `budget-request.schema.json` - Budget requests
- `charge-event.schema.json` - Charge events (provisional and final)
- `audit-reference.schema.json` - Audit bundle references
- `delegation-token.schema.json` - Delegation tokens for hierarchical authorization

## Usage

### Validation with Python

```python
import json
import jsonschema

# Load schema
with open('ase-metadata.schema.json') as f:
    schema = json.load(f)

# Load message
message = {
    "version": "1.0.0",
    "economicData": {
        "agentIdentity": {
            "agentId": "agent_001",
            "agentType": "autonomous"
        }
    }
}

# Validate
try:
    jsonschema.validate(instance=message, schema=schema)
    print("Valid ASE metadata")
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

### Validation with JavaScript

```javascript
const Ajv = require('ajv');
const ajv = new Ajv();

// Load schema
const schema = require('./ase-metadata.schema.json');

// Compile schema
const validate = ajv.compile(schema);

// Validate message
const message = {
    version: "1.0.0",
    economicData: {
        agentIdentity: {
            agentId: "agent_001",
            agentType: "autonomous"
        }
    }
};

const valid = validate(message);
if (!valid) {
    console.log('Validation errors:', validate.errors);
} else {
    console.log('Valid ASE metadata');
}
```

## Schema Versioning

Schemas are versioned alongside the ASE protocol:

- Version 1.0.0: Initial schema definitions
- Future versions will be added as separate files (e.g., `ase-metadata-v2.schema.json`)

## Schema References

Schemas use JSON Schema `$ref` to reference other schemas. When validating, ensure all referenced schemas are available in the same directory or provide a custom resolver.

## Validation Rules

These schemas enforce structural and type validation. For complete validation including semantic rules (e.g., non-negative amounts, timeframe consistency), use the validation pipeline defined in the ASE specification.

See [Validation Rules](../../docs/community/ase-protocol/validation-rules.md) for complete validation requirements.

## Contributing

When adding new schemas:

1. Follow JSON Schema Draft 07 specification
2. Use descriptive titles and descriptions
3. Include examples where helpful
4. Reference existing schemas for common types (e.g., monetary-amount)
5. Update this README with the new schema file
6. Add validation tests for the new schema

## References

- [JSON Schema Specification](https://json-schema.org/specification.html)
- [ASE Protocol Specification](../../docs/community/ase-protocol/specification.md)
- [ASE Message Schema](../../docs/community/ase-protocol/message-schema.md)
