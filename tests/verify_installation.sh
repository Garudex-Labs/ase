#!/bin/bash

echo "=========================================="
echo "ASE Package Installation Verification"
echo "=========================================="
echo ""

echo "1. Checking Python version..."
python --version
echo ""

echo "2. Installing package in editable mode..."
pip install -e . > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Package installed successfully"
else
    echo "✗ Package installation failed"
    exit 1
fi
echo ""

echo "3. Verifying package imports..."
python -c "
try:
    import governance
    print('✓ governance module imported')
except ImportError as e:
    print(f'✗ governance module failed: {e}')

try:
    import adapters
    print('✓ adapters module imported')
except ImportError as e:
    print(f'✗ adapters module failed: {e}')

try:
    import core
    print('✓ core module imported')
except ImportError as e:
    print(f'✗ core module failed: {e}')

try:
    import crypto
    print('✓ crypto module imported')
except ImportError as e:
    print(f'✗ crypto module failed: {e}')
"
echo ""

echo "4. Running simple test..."
python -m pytest tests/test_simple.py -v > /tmp/simple_test.log 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Simple test passed"
else
    echo "✗ Simple test failed"
    cat /tmp/simple_test.log
fi
echo ""

echo "5. Running property-based tests (sample)..."
python -m pytest tests/test_provisional_charge_lifecycle.py::test_property_3_provisional_charge_creation -v > /tmp/pbt_test.log 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Property-based test passed"
else
    echo "✗ Property-based test failed"
    cat /tmp/pbt_test.log
fi
echo ""

echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "To run all tests:"
echo "  python -m pytest tests/ -v"
echo ""
echo "To run specific test categories:"
echo "  python -m pytest tests/ -v -k 'test_property'"
echo ""
