# ASE Protocol Property-Based Tests

This directory contains property-based tests for the Agent Settlement Extension (ASE) protocol using Hypothesis.

## Overview

Property-based testing validates that the ASE protocol maintains correctness properties across all possible inputs, not just specific test cases. Each test runs 100+ randomized examples to ensure robust validation.

## Test Files

### test_ase_to_ase_communication.py

Tests for ASE-to-ASE communication scenarios and message exchange.

**Test Scenarios**:
- ASE message structure validation
- ASE-to-ASE message exchange
- Charge event propagation
- Delegation token exchange
- Cost and budget negotiation
- Audit trail propagation

**Requirements Validated**: 9.1, 9.6

**Test Coverage**:
- Complete ASE message structure validation
- Bidirectional communication between ASE agents
- Economic metadata preservation during transmission
- Charge event correlation and tracking
- Delegation token validation and usage
- Cost declaration and budget request exchange
- Audit reference propagation and tracking
- Currency consistency enforcement
- Message serialization and deserialization

### test_ase_to_non_ase_compatibility.py

Tests for backward compatibility between ASE and non-ASE agents.

**Test Scenarios**:
- ASE message processing by non-ASE agents
- Non-ASE message processing by ASE agents
- ASE field removal preserves functionality
- Graceful degradation on version mismatch
- Batch message processing compatibility
- JSON serialization compatibility
- Error handling for unknown fields
- ASE agent backward compatibility mode

**Requirements Validated**: 9.2, 9.6

**Test Coverage**:
- Base protocol field accessibility
- ASE metadata safe ignorance
- Zero-cost transaction handling
- Message functionality preservation
- Version mismatch handling
- Batch processing without errors
- JSON round-trip consistency
- Unknown field handling
- Compatibility matrix validation
- Support requirements verification

### test_version_management.py

Tests for version negotiation, protocol compliance, and backward compatibility.

**Properties Tested**:
- **Property 1: Backward Compatibility Preservation** - Validates base protocol functionality remains intact
- **Property 17: Version Negotiation** - Validates highest mutually supported version selection
- **Property 18: Version Mismatch Graceful Degradation** - Validates graceful degradation to compatible features
- **Property 20: Test Suite Protocol Compliance Validation** - Validates protocol compliance and backward compatibility

**Requirements Validated**: 1.1, 1.2, 1.5, 7.4, 7.6, 9.6

**Test Coverage**:
- Base protocol field preservation
- ASE metadata optional handling
- Zero-cost transaction processing
- Version negotiation between agents
- Common version identification
- Highest version selection
- Version mismatch detection
- Feature set degradation
- Protocol compliance validation
- JSON serialization compliance
- Batch compliance validation

### test_cross_framework_compatibility.py

Tests for LangChain and AutoGPT integration and cross-framework compatibility.

**Test Scenarios**:
- LangChain message wrapping compatibility
- AutoGPT message wrapping compatibility
- Cross-framework metadata consistency
- LangChain wrapping performance benchmark
- AutoGPT wrapping performance benchmark
- LangChain certification validation
- AutoGPT certification validation

**Requirements Validated**: 9.5, 9.7

**Test Coverage**:
- Framework-specific message structure preservation
- ASE metadata placement following conventions
- Round-trip consistency validation
- Framework convention adherence
- Cross-framework metadata consistency
- Performance benchmarking (< 1ms per operation)
- Throughput measurement (> 1000 msg/s)
- Certification criteria validation
- Error handling robustness
- Compatibility matrix verification

### test_provisional_charge_lifecycle.py

Tests for provisional charge event creation and expiration.

**Properties Tested**:
- **Property 3: Provisional Charge Creation** - Validates that provisional charges are created with proper budget reservation
- **Property 5: Provisional Charge Expiration** - Validates that expired provisional charges release reserved budget

**Requirements Validated**: 3.1, 3.3

**Test Coverage**:
- Provisional charge structure validation
- Event ID format validation
- Expiration time constraints (1 minute to 24 hours)
- Status transitions (pending → reserved → confirmed/expired/cancelled)
- Budget reservation logic
- JSON serialization compatibility

### test_final_charge_reconciliation.py

Tests for final charge creation and reconciliation with provisional charges.

**Properties Tested**:
- **Property 4: Final Charge Creation** - Validates that final charges are created with accurate actual costs
- **Property 6: Budget Adjustment Consistency** - Validates that budget adjustments reflect actual cost differences

**Requirements Validated**: 3.2, 3.6

**Test Coverage**:
- Final charge structure validation
- Provisional charge reference validation
- Agent and currency matching
- Timing validation (final before provisional expiration)
- Budget adjustment calculations (additional charges, refunds, no adjustment)
- Budget invariant maintenance (Total = Reserved + Available + Consumed)
- Variance validation (max 20% overage, min 50% underage)
- Orphaned final charge handling
- Audit trail generation
- Status transitions after reconciliation
- JSON serialization compatibility

### test_delegation_token_validation.py

Tests for delegation token validation and hierarchical delegation support.

**Properties Tested**:
- **Property 7: Delegation Token Validation** - Validates cryptographic signatures and spending limits
- **Property 9: Hierarchical Delegation Support** - Validates delegation chains and constraint inheritance

**Requirements Validated**: 4.3, 4.5

**Test Coverage**:
- JWT token structure validation (header, payload, signature)
- Cryptographic algorithm validation (ES256, RS256)
- Required claims validation (iss, sub, aud, exp, iat, jti, spendingLimit)
- Spending limit format and positivity validation
- Token expiration and lifetime validation
- Allowed operations validation and uniqueness
- Delegation depth constraints (0-5 levels)
- Parent-child relationship validation
- Delegation chain tracking and integrity
- Spending limit monotonic decrease through chain
- Currency consistency through chain
- Operation restriction inheritance (child ⊆ parent)
- Issuer-subject delegation flow validation
- JSON serialization compatibility

### test_delegation_limit_enforcement.py

Tests for delegation limit enforcement and token expiration handling.

**Properties Tested**:
- **Property 8: Delegation Limit Enforcement** - Validates spending limit enforcement and transaction rejection
- **Property 10: Delegation Token Expiration Handling** - Validates expired token rejection and cleanup

**Requirements Validated**: 4.4, 4.6

**Test Coverage**:
- Spending limit enforcement (within/exceeding available amount)
- Spending invariant validation (limit = spent + reserved + available)
- Currency consistency enforcement
- Error information completeness
- Cumulative spending tracking across multiple transactions
- Token expiration detection and validation
- Expired token transaction rejection
- Reserved amount release on expiration
- Operation authorization enforcement
- Spending reservation timeout handling
- Hierarchical spending limit validation (parent-child)
- Expiration warning threshold detection
- Concurrent transaction race condition prevention
- Atomic spending reservation validation

### test_dispute_resolution_workflows.py

Tests for dispute resolution workflows and escalation support.

**Properties Tested**:
- **Property 11: Dispute Event Creation** - Validates dispute events with complete evidence and charge references
- **Property 12: Dispute Resolution Event Creation** - Validates resolution events with final settlement details
- **Property 13: Dispute Escalation Support** - Validates dispute escalation to arbitration agents

**Requirements Validated**: 5.1, 5.3, 5.4

**Test Coverage**:
- Dispute event structure validation
- Dispute ID format validation
- Original charge reference validation
- Agent differentiation (disputing vs responding)
- Evidence item structure and validation
- Evidence type validation (log_entry, transaction_record, screenshot, etc.)
- Content hash integrity validation
- Status lifecycle validation (open, under_review, resolved, escalated, etc.)
- Timestamp ordering validation
- Escrow amount validation
- Resolution event structure validation
- Resolution ID format validation
- Resolution outcome validation (dispute_upheld, dispute_rejected, refunds, etc.)
- Settlement instructions validation
- Adjustment amount validation
- Escalation details validation
- Escalation level constraints (1-5)
- Previous arbitrators tracking
- Escalation timestamp validation
- Dispute lifecycle timing validation
- Escrow management during disputes
- JSON serialization compatibility

### test_audit_bundle_integrity.py

Tests for audit bundle integrity and completeness.

**Properties Tested**:
- **Property 15: Audit Bundle Integrity** - Validates cryptographic signing and tamper-evidence
- **Property 16: Audit Bundle Completeness** - Validates complete transaction history for time periods

**Requirements Validated**: 6.1, 6.2, 6.3, 6.5

**Test Coverage**:
- Audit bundle structure validation
- Bundle ID format validation
- Signature presence and format validation
- Signature algorithm validation (ES256, RS256, ES384, RS384, ES512, RS512)
- Public key ID validation
- Time range validation
- Transaction timestamp validation (within time range)
- Summary statistics accuracy
- Total transaction count validation
- Agent participants list completeness
- Transaction type count validation
- Total amount calculation validation
- Amount by agent calculation validation
- Amount by currency calculation validation
- Duplicate transaction detection
- Previous bundle chain validation
- Previous bundle hash validation
- Merkle root validation
- Transaction hash validation
- Checksum algorithm validation
- Tamper detection validation
- Audit bundle chain integrity
- Sequential time range validation
- Metadata validation (audit purpose, retention period, encryption status)
- Access control list validation
- JSON serialization compatibility

## Running Tests

### Prerequisites

Install required dependencies:

```bash
pip install -r requirements.txt
```

### Run All Tests

Using pytest:

```bash
# Run all tests
python3 -m pytest ase/tests/ -v

# Run specific test file
python3 -m pytest ase/tests/test_provisional_charge_lifecycle.py -v

# Run with hypothesis statistics
python3 -m pytest ase/tests/ -v --hypothesis-show-statistics
```

### Run Manual Test Runners

For environments where pytest output is not visible:

```bash
# Run provisional charge tests
python3 ase/tests/run_tests_manual.py

# Run final charge tests
python3 ase/tests/run_final_charge_tests.py
```

## Test Data Generators

The tests use custom Hypothesis strategies to generate realistic ASE protocol data:

### monetary_amount()
Generates valid monetary amounts with:
- Values between 0.01 and 999,999.99
- Two decimal places
- ISO 4217 currency codes (USD, EUR, GBP, JPY)

### agent_id()
Generates valid agent identifiers with:
- Prefix (agent, service, client)
- Alphanumeric suffix (6-20 characters)

### provisional_charge_event()
Generates complete provisional charge events with:
- Valid event IDs (evt_prov_*)
- Expiration times (1 minute to 24 hours in future)
- Valid status values
- Optional metadata fields

### charge_pair()
Generates matching provisional and final charge pairs with:
- Consistent agent IDs and currencies
- Final charge created before provisional expiration
- Realistic variance (-40% to +15%)
- Proper charge references

### orphaned_final_charge()
Generates final charges without provisional references for testing standalone charge handling.

## Property Test Configuration

All property tests are configured with:
- **max_examples=100**: Each property runs 100 randomized test cases
- **Hypothesis default settings**: Standard shrinking and example generation

## Test Validation Rules

### Provisional Charges

- Event ID must start with `evt_prov_`
- Event type must be `provisional`
- Expiration time must be 1 minute to 24 hours in future
- Status must be valid for provisional charges
- Amount must be positive
- Currency must be 3-character ISO code

### Final Charges

- Event ID must start with `evt_final_`
- Event type must be `final`
- Must reference provisional charge (unless orphaned)
- Agent IDs must match between charges
- Currencies must match between charges
- Must be created before provisional expiration
- Amount must be positive

### Reconciliation

- Provisional charge must exist and be in `reserved` status
- Maximum overage: 20% (final > provisional)
- Minimum underage: 50% (final >= 50% of provisional)
- Budget invariant must be maintained: Total = Reserved + Available + Consumed
- Adjustment amount must equal the difference between charges

## Budget Invariant

All tests validate the fundamental budget invariant:

```
Total Budget = Reserved Budget + Available Budget + Consumed Budget
```

This invariant must hold before and after all charge operations.

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```bash
# Run tests with JUnit XML output
python3 -m pytest ase/tests/ --junitxml=test-results.xml

# Run tests with coverage
python3 -m pytest ase/tests/ --cov=ase --cov-report=html
```

## Troubleshooting

### Tests Not Running

If pytest doesn't discover tests:
1. Ensure `__init__.py` exists in the tests directory
2. Verify test functions start with `test_`
3. Check that hypothesis and pytest are installed

### Hypothesis Errors

If you see hypothesis errors:
1. Update hypothesis: `pip install --upgrade hypothesis`
2. Check for invalid strategy combinations
3. Review assume() statements that might be too restrictive

### Slow Tests

Property-based tests can be slow. To speed up:
1. Reduce max_examples (not recommended for CI)
2. Use hypothesis profiles for different environments
3. Run tests in parallel with pytest-xdist

## Contributing

When adding new property tests:

1. Follow the naming convention: `test_property_N_description`
2. Include docstring with property description and requirements
3. Use appropriate test data generators
4. Validate all relevant invariants
5. Add test to manual runner if needed
6. Update this README with new test coverage

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [ASE Protocol Specification](../../docs/community/ase-protocol/specification.md)
- [Charge Event Lifecycle](../../docs/community/ase-protocol/charge-event-lifecycle.md)
- [Charge Reconciliation](../../docs/community/ase-protocol/charge-reconciliation.md)
