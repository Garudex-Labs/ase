# ASE Reference Implementation

This directory contains the Python reference implementation of the Agent Settlement Extension (ASE) protocol.

## Overview

The reference implementation provides:

1. **Core Message Processing** - Serialization, deserialization, and validation
2. **Cryptographic Services** - Signing, verification, and key management
3. **Framework Adapters** - Integration with LangChain and AutoGPT

## Contributing

When extending the reference implementation:

1. Follow snake_case for internal Python code
2. Use Pydantic Field aliases for camelCase JSON output
3. Add property-based tests for new functionality
4. Document extension points and interfaces
5. Maintain backward compatibility