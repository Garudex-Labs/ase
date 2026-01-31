"""Test that writes to a file to verify execution"""

def test_write_to_file():
    """Test that writes to a file"""
    with open('/tmp/ase_test_ran.txt', 'w') as f:
        f.write('Test executed successfully!\n')
    assert True

if __name__ == "__main__":
    test_write_to_file()
