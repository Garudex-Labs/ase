#!/usr/bin/env python3
"""Run all ASE tests and write results to file"""

import subprocess
import sys

def run_tests():
    """Run all tests and capture output"""
    
    # Write to file
    with open('test_results.txt', 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("ASE Test Suite Results\n")
        f.write("=" * 70 + "\n\n")
        
        # Run pytest
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
            capture_output=True,
            text=True
        )
        
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\n\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\n\nReturn code: {result.returncode}\n")
        
        print(f"Tests completed with return code: {result.returncode}")
        print(f"Results written to test_results.txt")
        
        return result.returncode

if __name__ == '__main__':
    sys.exit(run_tests())
