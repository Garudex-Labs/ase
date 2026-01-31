"""Setup script for ASE (Agent Settlement Extension) protocol implementation"""

from setuptools import setup, find_packages

setup(
    name="ase-protocol",
    version="1.0.0",
    description="Agent Settlement Extension (ASE) Protocol Implementation",
    author="ASE Protocol Team",
    author_email="team@ase-protocol.org",
    url="https://github.com/ase-protocol/ase",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "cryptography>=41.0.0",
        "pyjwt>=2.8.0",
    ],
    extras_require={
        "test": [
            "pytest>=8.0.0",
            "hypothesis>=6.100.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
