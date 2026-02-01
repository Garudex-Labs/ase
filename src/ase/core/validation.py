"""
Validation pipeline architecture for ASE messages.

Provides a flexible validation framework with error handling and extensibility.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: ValidationSeverity
    code: str
    message: str
    field_path: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
        }
        if self.field_path:
            result["fieldPath"] = self.field_path
        if self.context:
            result["context"] = self.context
        return result


@dataclass
class ValidationResult:
    """Result of validation pipeline execution."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False
    
    def add_error(self, code: str, message: str, field_path: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None) -> None:
        """Add an error issue."""
        self.add_issue(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code=code,
            message=message,
            field_path=field_path,
            context=context or {}
        ))
    
    def add_warning(self, code: str, message: str, field_path: Optional[str] = None,
                    context: Optional[Dict[str, Any]] = None) -> None:
        """Add a warning issue."""
        self.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code=code,
            message=message,
            field_path=field_path,
            context=context or {}
        ))
    
    def has_errors(self) -> bool:
        """Check if result contains any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if result contains any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "isValid": self.is_valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": self.metadata,
        }


class ValidationError(Exception):
    """Raised when validation fails with errors."""
    
    def __init__(self, result: ValidationResult):
        self.result = result
        error_messages = [issue.message for issue in result.get_errors()]
        super().__init__(f"Validation failed: {'; '.join(error_messages)}")


class Validator(ABC):
    """Abstract base class for validators."""
    
    @abstractmethod
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate data and return result.
        
        Args:
            data: Data to validate
            context: Optional validation context
            
        Returns:
            ValidationResult with any issues found
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return validator name for identification."""
        pass


class ValidationPipeline:
    """
    Orchestrates multiple validators in a pipeline.
    
    Validators are executed in order, and all validators run even if
    earlier ones fail (unless fail_fast is enabled).
    """
    
    def __init__(self, validators: Optional[List[Validator]] = None, fail_fast: bool = False):
        """
        Initialize validation pipeline.
        
        Args:
            validators: List of validators to execute
            fail_fast: If True, stop on first error
        """
        self.validators = validators or []
        self.fail_fast = fail_fast
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []
    
    def add_validator(self, validator: Validator) -> None:
        """Add a validator to the pipeline."""
        self.validators.append(validator)
    
    def remove_validator(self, validator_name: str) -> bool:
        """
        Remove a validator by name.
        
        Returns:
            True if validator was removed, False if not found
        """
        for i, validator in enumerate(self.validators):
            if validator.name == validator_name:
                self.validators.pop(i)
                return True
        return False
    
    def add_pre_hook(self, hook: Callable[[Any, Dict[str, Any]], None]) -> None:
        """Add a pre-validation hook."""
        self._pre_hooks.append(hook)
    
    def add_post_hook(self, hook: Callable[[ValidationResult], None]) -> None:
        """Add a post-validation hook."""
        self._post_hooks.append(hook)
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None,
                 raise_on_error: bool = False) -> ValidationResult:
        """
        Execute validation pipeline.
        
        Args:
            data: Data to validate
            context: Optional validation context
            raise_on_error: If True, raise ValidationError on failure
            
        Returns:
            Combined ValidationResult from all validators
            
        Raises:
            ValidationError: If raise_on_error is True and validation fails
        """
        context = context or {}
        combined_result = ValidationResult(is_valid=True)
        
        # Execute pre-hooks
        for hook in self._pre_hooks:
            hook(data, context)
        
        # Execute validators
        for validator in self.validators:
            try:
                result = validator.validate(data, context)
                
                # Merge results
                for issue in result.issues:
                    combined_result.add_issue(issue)
                
                # Update metadata
                combined_result.metadata[validator.name] = result.metadata
                
                # Fail fast if enabled and errors found
                if self.fail_fast and result.has_errors():
                    break
                    
            except Exception as e:
                # Catch validator exceptions and convert to validation errors
                combined_result.add_error(
                    code="VALIDATOR_EXCEPTION",
                    message=f"Validator '{validator.name}' raised exception: {str(e)}",
                    context={"validator": validator.name, "exception": str(e)}
                )
                if self.fail_fast:
                    break
        
        # Execute post-hooks
        for hook in self._post_hooks:
            hook(combined_result)
        
        # Raise exception if requested and validation failed
        if raise_on_error and combined_result.has_errors():
            raise ValidationError(combined_result)
        
        return combined_result


class SchemaValidator(Validator):
    """Validates data against a JSON schema."""
    
    def __init__(self, schema: Dict[str, Any], name: str = "schema"):
        """
        Initialize schema validator.
        
        Args:
            schema: JSON schema to validate against
            name: Validator name
        """
        self.schema = schema
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name
    
    def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate data against JSON schema."""
        result = ValidationResult(is_valid=True)
        
        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=self.schema)
        except ImportError:
            result.add_warning(
                code="SCHEMA_VALIDATOR_UNAVAILABLE",
                message="jsonschema library not available, skipping schema validation"
            )
        except jsonschema.ValidationError as e:
            result.add_error(
                code="SCHEMA_VALIDATION_FAILED",
                message=str(e.message),
                field_path=".".join(str(p) for p in e.path) if e.path else None,
                context={"schema_path": list(e.schema_path)}
            )
        except Exception as e:
            result.add_error(
                code="SCHEMA_VALIDATION_ERROR",
                message=f"Schema validation error: {str(e)}"
            )
        
        return result


class SemanticValidator(Validator):
    """Base class for semantic validation rules."""
    
    def __init__(self, name: str):
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name


def validate_message(
    data: Any,
    schema: Optional[Dict[str, Any]] = None,
    validators: Optional[List[Validator]] = None
) -> ValidationResult:
    """
    Validate a message using standard pipeline.
    
    Args:
        data: Message data to validate
        schema: Optional JSON schema
        validators: Optional additional validators
        
    Returns:
        ValidationResult
    """
    pipeline = ValidationPipeline(validators=validators)
    if schema:
        pipeline.add_validator(SchemaValidator(schema))
    
    return pipeline.validate(data)
