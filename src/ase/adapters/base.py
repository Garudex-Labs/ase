"""
Base adapter interface for framework integration.

Defines the common interface that all framework adapters must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class FrameworkType(Enum):
    """Supported agent frameworks."""
    LANGCHAIN = "langchain"
    AUTOGPT = "autogpt"
    CUSTOM = "custom"


@dataclass
class AdapterConfig:
    """Configuration for framework adapters."""
    framework_type: FrameworkType
    enable_economic_metadata: bool = True
    enable_delegation_tokens: bool = True
    enable_audit_trails: bool = True
    auto_attach_metadata: bool = True
    metadata_defaults: Dict[str, Any] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "frameworkType": self.framework_type.value,
            "enableEconomicMetadata": self.enable_economic_metadata,
            "enableDelegationTokens": self.enable_delegation_tokens,
            "enableAuditTrails": self.enable_audit_trails,
            "autoAttachMetadata": self.auto_attach_metadata,
            "metadataDefaults": self.metadata_defaults,
            "customSettings": self.custom_settings,
        }


class AdapterError(Exception):
    """Base exception for adapter operations."""
    pass


class FrameworkAdapter(ABC):
    """
    Abstract base class for framework adapters.
    
    Framework adapters translate between ASE protocol and framework-specific
    conventions, ensuring seamless integration while maintaining framework idioms.
    """
    
    def __init__(self, config: AdapterConfig):
        """
        Initialize adapter.
        
        Args:
            config: Adapter configuration
        """
        self.config = config
        self._hooks: Dict[str, List[Callable]] = {}
    
    @property
    @abstractmethod
    def framework_type(self) -> FrameworkType:
        """Return the framework type this adapter supports."""
        pass
    
    @abstractmethod
    def wrap_message(self, message: Any, economic_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """
        Wrap a framework message with ASE economic metadata.
        
        Args:
            message: Framework-specific message object
            economic_metadata: Optional ASE economic metadata
            
        Returns:
            Wrapped message with ASE metadata
            
        Raises:
            AdapterError: If wrapping fails
        """
        pass
    
    @abstractmethod
    def unwrap_message(self, wrapped_message: Any) -> tuple[Any, Optional[Dict[str, Any]]]:
        """
        Unwrap a message to extract framework message and ASE metadata.
        
        Args:
            wrapped_message: Wrapped message with ASE metadata
            
        Returns:
            Tuple of (framework_message, economic_metadata)
            
        Raises:
            AdapterError: If unwrapping fails
        """
        pass
    
    @abstractmethod
    def attach_delegation_token(self, message: Any, token: str) -> Any:
        """
        Attach a delegation token to a message.
        
        Args:
            message: Framework message
            token: Delegation token JWT
            
        Returns:
            Message with attached token
            
        Raises:
            AdapterError: If attachment fails
        """
        pass
    
    @abstractmethod
    def extract_delegation_token(self, message: Any) -> Optional[str]:
        """
        Extract delegation token from a message.
        
        Args:
            message: Framework message
            
        Returns:
            Delegation token if present, None otherwise
        """
        pass
    
    @abstractmethod
    def create_charge_event(self, event_type: str, amount: Dict[str, Any],
                          agent_id: str, description: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a charge event in framework-appropriate format.
        
        Args:
            event_type: Type of charge event (provisional, final)
            amount: Monetary amount {"value": "100.00", "currency": "USD"}
            agent_id: Agent identifier
            description: Event description
            metadata: Optional additional metadata
            
        Returns:
            Charge event dictionary
        """
        pass
    
    @abstractmethod
    def validate_framework_conventions(self, message: Any) -> bool:
        """
        Validate that message follows framework-specific conventions.
        
        Args:
            message: Framework message to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def register_hook(self, hook_name: str, hook_func: Callable) -> None:
        """
        Register a hook function for adapter events.
        
        Args:
            hook_name: Name of the hook point
            hook_func: Function to call at hook point
        """
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(hook_func)
    
    def execute_hooks(self, hook_name: str, *args, **kwargs) -> None:
        """
        Execute all registered hooks for a hook point.
        
        Args:
            hook_name: Name of the hook point
            *args: Positional arguments for hooks
            **kwargs: Keyword arguments for hooks
        """
        if hook_name in self._hooks:
            for hook_func in self._hooks[hook_name]:
                hook_func(*args, **kwargs)
    
    def get_metadata_defaults(self) -> Dict[str, Any]:
        """Get default metadata values from config."""
        return self.config.metadata_defaults.copy()
    
    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled in config.
        
        Args:
            feature: Feature name (economic_metadata, delegation_tokens, audit_trails)
            
        Returns:
            True if enabled, False otherwise
        """
        feature_map = {
            "economic_metadata": self.config.enable_economic_metadata,
            "delegation_tokens": self.config.enable_delegation_tokens,
            "audit_trails": self.config.enable_audit_trails,
        }
        return feature_map.get(feature, False)


class MessageTransformer(ABC):
    """
    Abstract base class for message transformation.
    
    Handles bidirectional transformation between framework formats and ASE format.
    """
    
    @abstractmethod
    def to_ase_format(self, framework_message: Any) -> Dict[str, Any]:
        """
        Transform framework message to ASE format.
        
        Args:
            framework_message: Framework-specific message
            
        Returns:
            ASE-formatted message dictionary
        """
        pass
    
    @abstractmethod
    def from_ase_format(self, ase_message: Dict[str, Any]) -> Any:
        """
        Transform ASE message to framework format.
        
        Args:
            ase_message: ASE-formatted message dictionary
            
        Returns:
            Framework-specific message
        """
        pass


class ConventionValidator(ABC):
    """
    Abstract base class for framework convention validation.
    
    Ensures messages follow framework-specific patterns and idioms.
    """
    
    @abstractmethod
    def validate_message_structure(self, message: Any) -> tuple[bool, List[str]]:
        """
        Validate message structure follows framework conventions.
        
        Args:
            message: Framework message
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass
    
    @abstractmethod
    def validate_metadata_placement(self, message: Any) -> tuple[bool, List[str]]:
        """
        Validate metadata is placed according to framework conventions.
        
        Args:
            message: Framework message
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass
    
    @abstractmethod
    def get_convention_guidelines(self) -> Dict[str, str]:
        """
        Get framework-specific convention guidelines.
        
        Returns:
            Dictionary of guideline descriptions
        """
        pass
