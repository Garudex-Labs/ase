"""Pytest configuration for ASE tests"""

import sys
import os

# Get the absolute path to src directory
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
src_path = os.path.join(project_root, 'src')

# Add src to path if not already there
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Verify modules can be imported
try:
    import governance
    import adapters
    import core
    import crypto
    print(f"✓ ASE modules loaded successfully")
    print(f"  governance: {governance.__file__}")
    print(f"  adapters: {adapters.__file__}")
except ImportError as e:
    print(f"✗ Failed to import ASE modules: {e}")
    print(f"  src_path: {src_path}")
    print(f"  sys.path: {sys.path[:3]}")
    # Don't exit - let pytest handle the error
