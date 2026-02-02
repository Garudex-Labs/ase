from setuptools import setup, find_packages

setup(
    name="ase-protocol",
    version="1.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
