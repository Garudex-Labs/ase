#!/usr/bin/env python3
from setuptools import find_packages
import os

print("Checking package structure...")
print(f"Current directory: {os.getcwd()}")
print(f"src directory exists: {os.path.exists('src')}")
print(f"src/__init__.py exists: {os.path.exists('src/__init__.py')}")

packages = find_packages(where='src')
print(f"\nPackages found: {packages}")

for pkg in ['governance', 'adapters', 'core', 'crypto']:
    pkg_path = os.path.join('src', pkg)
    init_path = os.path.join(pkg_path, '__init__.py')
    print(f"\n{pkg}:")
    print(f"  Directory exists: {os.path.exists(pkg_path)}")
    print(f"  __init__.py exists: {os.path.exists(init_path)}")
