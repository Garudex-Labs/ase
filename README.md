Agent Settlement Extension (ASE)
=================================

Agent Settlement Extension (ASE) is an economic metadata layer that extends agent-to-agent (A2A) and Model Control Protocol (MCP) communications with economic semantics. ASE provides standardized schemas, validation, and reference implementations to enable agents to express economic intents, settlements, audit bundles, and related metadata in interoperable ways.

Key goals
- Make economic semantics first-class in agent messaging.
- Provide machine-readable schemas and validators for settlement, audit, and delegation tokens.
- Offer lightweight reference code to integrate ASE with agent frameworks.

Package (Pypi): https://pypi.org/project/ase-protocol/1.0.1 (Latest Version)

Repository layout
- `schemas/` — JSON Schema files describing ASE data structures (audit bundles, delegation tokens, monetary amounts, etc.).
- `src/` — Reference Python implementation and adapters. Key modules:
  - `core/` — ASE core models, validation, serialization, and business logic.
  - `adapters/` — Integration adapters (e.g. LangChain, AutoGPT helpers).
  - `crypto/` — Key handling, signing, and token utilities.
  - `governance/` — Compliance helpers and RFC-style governance workflows.
- `tests/` — Test suites and example scenarios validating cross-framework compatibility and protocol behavior.
- `GET_STARTED.md` and `PROTOCOL.md` — Design notes and protocol specifics.

Quick start (developer)
1. Create a Python virtual environment and install test/dev dependencies from `tests/requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt
```

2. Run the test suite to confirm everything passes:

```bash
pytest -q
```

Using the schemas
- The `schemas/` directory contains canonical JSON Schema files. Use your preferred validator (e.g., `jsonschema` Python package) to validate ASE messages.
- See `src/serialization.py` and `src/validation.py` for examples of programmatic validation and serialization.

Development notes
- Keep schema changes backward compatible where possible. Use a versioning scheme when introducing breaking changes and update `version-migration.schema.json` accordingly.
- Follow existing module patterns in `src/core` when adding new models or validators.

Tests
- Unit and integration tests live in `tests/`. They include interoperability scenarios between ASE-aware and non-ASE agents.
- To run a specific test file:

```bash
pytest tests/test_simple.py -q
```

License
- This project is licensed under the Apache License 2.0. See `LICENSE` for the full text.

Contributing
- Open issues for bugs and feature requests.
- For changes to schemas, include upgrade guidance and migration examples.
- Follow the existing code style and add tests for new behaviors.

Contact / Author
- RAWx18 (rawx18.dev@gmail.com)

Acknowledgements
- ASE aims to be framework-agnostic; adapters demonstrate integration patterns with popular agent frameworks.