"""
Compliance Certification Framework

This module defines ASE compliance test requirements, certification criteria,
and implementation tracking mechanisms.

Validates: Requirements 10.2, 10.5, 10.6
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal


class ComplianceStatus(Enum):
    """Compliance certification status."""
    NOT_TESTED = "not_tested"
    TESTING_IN_PROGRESS = "testing_in_progress"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    CONDITIONALLY_COMPLIANT = "conditionally_compliant"
    CERTIFICATION_EXPIRED = "certification_expired"
    CERTIFICATION_REVOKED = "certification_revoked"


class ComplianceLevel(Enum):
    """Compliance certification levels."""
    BASIC = "basic"  # Core protocol compliance
    STANDARD = "standard"  # Full feature compliance
    ADVANCED = "advanced"  # Advanced features and optimizations
    ENTERPRISE = "enterprise"  # Enterprise-grade compliance


class TestCategory(Enum):
    """Test categories for compliance validation."""
    BACKWARD_COMPATIBILITY = "backward_compatibility"
    MESSAGE_STRUCTURE = "message_structure"
    ECONOMIC_METADATA = "economic_metadata"
    CHARGE_MANAGEMENT = "charge_management"
    DELEGATION_TOKENS = "delegation_tokens"
    DISPUTE_RESOLUTION = "dispute_resolution"
    AUDIT_BUNDLES = "audit_bundles"
    VERSION_NEGOTIATION = "version_negotiation"
    FRAMEWORK_INTEGRATION = "framework_integration"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class ComplianceTest:
    """
    Individual compliance test specification.
    
    Defines a single test that must pass for compliance certification.
    """
    test_id: str
    test_name: str
    category: TestCategory
    description: str
    required_for_levels: List[ComplianceLevel]
    
    # Test execution
    test_function: Optional[str] = None  # Reference to test function
    test_file: Optional[str] = None  # Test file path
    
    # Test results
    passed: Optional[bool] = None
    execution_time: Optional[float] = None  # Seconds
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    
    # Metadata
    property_reference: Optional[str] = None  # Reference to design property
    requirement_reference: Optional[str] = None  # Reference to requirement
    
    def execute_test(self) -> Tuple[bool, Optional[str]]:
        """
        Execute the compliance test.
        
        Returns:
            Tuple of (passed, error_message)
        """
        # This is a placeholder - actual test execution would be implemented
        # by the test framework integration
        if self.test_function is None:
            return False, "Test function not specified"
        
        self.executed_at = datetime.now(timezone.utc)
        return True, None
    
    def mark_result(self, passed: bool, execution_time: float, error_message: Optional[str] = None):
        """Mark test result after execution."""
        self.passed = passed
        self.execution_time = execution_time
        self.error_message = error_message
        self.executed_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test to dictionary for serialization."""
        return {
            "testId": self.test_id,
            "testName": self.test_name,
            "category": self.category.value,
            "description": self.description,
            "requiredForLevels": [level.value for level in self.required_for_levels],
            "testFunction": self.test_function,
            "testFile": self.test_file,
            "passed": self.passed,
            "executionTime": self.execution_time,
            "errorMessage": self.error_message,
            "executedAt": self.executed_at.isoformat() if self.executed_at else None,
            "propertyReference": self.property_reference,
            "requirementReference": self.requirement_reference
        }


@dataclass
class ComplianceCertification:
    """
    Compliance certification for an ASE implementation.
    
    Tracks compliance test results and certification status for a specific
    implementation of the ASE protocol.
    """
    certification_id: str
    implementation_name: str
    implementation_version: str
    vendor: str
    vendor_contact: str
    
    # Certification details
    ase_version: str  # ASE protocol version
    compliance_level: ComplianceLevel
    status: ComplianceStatus
    
    # Test results
    tests: List[ComplianceTest] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    
    # Certification lifecycle
    certification_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    last_tested: Optional[datetime] = None
    
    # Metadata
    test_environment: Optional[str] = None
    test_framework: Optional[str] = None
    notes: Optional[str] = None
    
    def add_test(self, test: ComplianceTest):
        """Add a compliance test to the certification."""
        self.tests.append(test)
        self.total_tests = len(self.tests)
    
    def update_test_counts(self):
        """Update test pass/fail counts based on test results."""
        self.passed_tests = sum(1 for test in self.tests if test.passed is True)
        self.failed_tests = sum(1 for test in self.tests if test.passed is False)
        self.total_tests = len(self.tests)
    
    def calculate_compliance_score(self) -> float:
        """
        Calculate compliance score as percentage of passed tests.
        
        Returns:
            Compliance score between 0.0 and 1.0
        """
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    def get_required_tests_for_level(self, level: ComplianceLevel) -> List[ComplianceTest]:
        """Get all tests required for a specific compliance level."""
        return [
            test for test in self.tests
            if level in test.required_for_levels
        ]
    
    def validate_compliance_for_level(self, level: ComplianceLevel) -> Tuple[bool, List[str]]:
        """
        Validate compliance for a specific level.
        
        Returns:
            Tuple of (is_compliant, list of failed tests)
        """
        required_tests = self.get_required_tests_for_level(level)
        failed_test_names = []
        
        for test in required_tests:
            if test.passed is None:
                failed_test_names.append(f"{test.test_name} (not executed)")
            elif not test.passed:
                failed_test_names.append(f"{test.test_name} (failed)")
        
        return len(failed_test_names) == 0, failed_test_names
    
    def determine_certification_status(self) -> ComplianceStatus:
        """
        Determine certification status based on test results.
        
        Returns:
            Updated compliance status
        """
        self.update_test_counts()
        
        # Check if certification is expired
        if self.expiration_date and datetime.now(timezone.utc) > self.expiration_date:
            return ComplianceStatus.CERTIFICATION_EXPIRED
        
        # Check if all tests have been executed
        untested_count = sum(1 for test in self.tests if test.passed is None)
        if untested_count > 0:
            return ComplianceStatus.TESTING_IN_PROGRESS
        
        # Check compliance for the target level
        is_compliant, failed_tests = self.validate_compliance_for_level(self.compliance_level)
        
        if is_compliant:
            return ComplianceStatus.COMPLIANT
        else:
            # Check if compliant at a lower level
            lower_levels = {
                ComplianceLevel.ENTERPRISE: [ComplianceLevel.ADVANCED, ComplianceLevel.STANDARD, ComplianceLevel.BASIC],
                ComplianceLevel.ADVANCED: [ComplianceLevel.STANDARD, ComplianceLevel.BASIC],
                ComplianceLevel.STANDARD: [ComplianceLevel.BASIC],
                ComplianceLevel.BASIC: []
            }
            
            for lower_level in lower_levels.get(self.compliance_level, []):
                is_lower_compliant, _ = self.validate_compliance_for_level(lower_level)
                if is_lower_compliant:
                    return ComplianceStatus.CONDITIONALLY_COMPLIANT
            
            return ComplianceStatus.NON_COMPLIANT
    
    def certify(self, validity_days: int = 365) -> Tuple[bool, Optional[str]]:
        """
        Certify the implementation if all required tests pass.
        
        Args:
            validity_days: Number of days the certification is valid
        
        Returns:
            Tuple of (certified, error_message)
        """
        # Update status
        self.status = self.determine_certification_status()
        
        if self.status == ComplianceStatus.COMPLIANT:
            self.certification_date = datetime.now(timezone.utc)
            self.expiration_date = self.certification_date + timedelta(days=validity_days)
            return True, None
        elif self.status == ComplianceStatus.CONDITIONALLY_COMPLIANT:
            return False, "Implementation is only compliant at a lower level"
        elif self.status == ComplianceStatus.NON_COMPLIANT:
            is_compliant, failed_tests = self.validate_compliance_for_level(self.compliance_level)
            return False, f"Failed tests: {', '.join(failed_tests)}"
        else:
            return False, f"Cannot certify with status: {self.status.value}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert certification to dictionary for serialization."""
        return {
            "certificationId": self.certification_id,
            "implementationName": self.implementation_name,
            "implementationVersion": self.implementation_version,
            "vendor": self.vendor,
            "vendorContact": self.vendor_contact,
            "aseVersion": self.ase_version,
            "complianceLevel": self.compliance_level.value,
            "status": self.status.value,
            "tests": [test.to_dict() for test in self.tests],
            "totalTests": self.total_tests,
            "passedTests": self.passed_tests,
            "failedTests": self.failed_tests,
            "complianceScore": self.calculate_compliance_score(),
            "certificationDate": self.certification_date.isoformat() if self.certification_date else None,
            "expirationDate": self.expiration_date.isoformat() if self.expiration_date else None,
            "lastTested": self.last_tested.isoformat() if self.last_tested else None,
            "testEnvironment": self.test_environment,
            "testFramework": self.test_framework,
            "notes": self.notes
        }


@dataclass
class ComplianceRegistryEntry:
    """Entry in the compliance registry."""
    implementation_name: str
    implementation_version: str
    vendor: str
    ase_version: str
    compliance_level: ComplianceLevel
    status: ComplianceStatus
    certification_id: str
    certification_date: Optional[datetime]
    expiration_date: Optional[datetime]
    registry_url: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if certification is currently valid."""
        if self.status != ComplianceStatus.COMPLIANT:
            return False
        if self.expiration_date and datetime.now(timezone.utc) > self.expiration_date:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry entry to dictionary."""
        return {
            "implementationName": self.implementation_name,
            "implementationVersion": self.implementation_version,
            "vendor": self.vendor,
            "aseVersion": self.ase_version,
            "complianceLevel": self.compliance_level.value,
            "status": self.status.value,
            "certificationId": self.certification_id,
            "certificationDate": self.certification_date.isoformat() if self.certification_date else None,
            "expirationDate": self.expiration_date.isoformat() if self.expiration_date else None,
            "registryUrl": self.registry_url,
            "isValid": self.is_valid()
        }


class ComplianceRegistry:
    """
    Registry of compliant ASE implementations.
    
    Maintains a registry of implementations that have passed compliance
    certification and tracks their certification status.
    """
    
    def __init__(self):
        self.entries: Dict[str, ComplianceRegistryEntry] = {}
    
    def register_certification(self, certification: ComplianceCertification) -> Tuple[bool, Optional[str]]:
        """
        Register a compliant implementation in the registry.
        
        Returns:
            Tuple of (registered, error_message)
        """
        # Validate certification status
        if certification.status != ComplianceStatus.COMPLIANT:
            return False, f"Cannot register non-compliant implementation (status: {certification.status.value})"
        
        # Create registry entry
        entry_key = f"{certification.implementation_name}:{certification.implementation_version}"
        entry = ComplianceRegistryEntry(
            implementation_name=certification.implementation_name,
            implementation_version=certification.implementation_version,
            vendor=certification.vendor,
            ase_version=certification.ase_version,
            compliance_level=certification.compliance_level,
            status=certification.status,
            certification_id=certification.certification_id,
            certification_date=certification.certification_date,
            expiration_date=certification.expiration_date
        )
        
        self.entries[entry_key] = entry
        return True, None
    
    def mark_non_compliant(self, implementation_name: str, implementation_version: str, reason: str) -> bool:
        """
        Mark an implementation as non-compliant.
        
        This is used when compatibility tests fail for a previously
        compliant implementation.
        
        Returns:
            True if implementation was found and marked, False otherwise
        """
        entry_key = f"{implementation_name}:{implementation_version}"
        
        if entry_key not in self.entries:
            return False
        
        entry = self.entries[entry_key]
        entry.status = ComplianceStatus.NON_COMPLIANT
        
        return True
    
    def get_compliant_implementations(self, ase_version: Optional[str] = None) -> List[ComplianceRegistryEntry]:
        """
        Get list of compliant implementations.
        
        Args:
            ase_version: Optional filter by ASE version
        
        Returns:
            List of compliant registry entries
        """
        compliant = [
            entry for entry in self.entries.values()
            if entry.is_valid()
        ]
        
        if ase_version:
            compliant = [entry for entry in compliant if entry.ase_version == ase_version]
        
        return compliant
    
    def lookup_implementation(self, implementation_name: str, implementation_version: str) -> Optional[ComplianceRegistryEntry]:
        """Look up an implementation in the registry."""
        entry_key = f"{implementation_name}:{implementation_version}"
        return self.entries.get(entry_key)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for serialization."""
        return {
            "entries": [entry.to_dict() for entry in self.entries.values()],
            "totalEntries": len(self.entries),
            "compliantCount": len(self.get_compliant_implementations())
        }


# Import timedelta for certify method
from datetime import timedelta
