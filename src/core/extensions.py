"""
Extension point mechanisms for protocol customization.

Provides a plugin architecture for extending ASE functionality.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type


class ExtensionPointType(Enum):
    """Types of extension points in the ASE protocol."""
    PRE_SERIALIZATION = "pre_serialization"
    POST_DESERIALIZATION = "post_deserialization"
    PRE_VALIDATION = "pre_validation"
    POST_VALIDATION = "post_validation"
    CHARGE_EVENT_CREATED = "charge_event_created"
    DELEGATION_TOKEN_VALIDATED = "delegation_token_validated"
    AUDIT_BUNDLE_GENERATED = "audit_bundle_generated"
    DISPUTE_EVENT_CREATED = "dispute_event_created"
    CUSTOM = "custom"


class Extension(ABC):
    """Abstract base class for extensions."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return extension name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Return extension version."""
        pass
    
    @abstractmethod
    def execute(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute extension logic.
        
        Args:
            data: Input data for the extension
            context: Optional execution context
            
        Returns:
            Modified data or result
        """
        pass


class ExtensionPoint:
    """
    Represents a point in the system where extensions can be registered.
    """
    
    def __init__(self, point_type: ExtensionPointType, name: str):
        """
        Initialize extension point.
        
        Args:
            point_type: Type of extension point
            name: Unique name for this extension point
        """
        self.point_type = point_type
        self.name = name
        self._extensions: List[Extension] = []
        self._hooks: List[Callable] = []
    
    def register_extension(self, extension: Extension) -> None:
        """Register an extension at this point."""
        self._extensions.append(extension)
    
    def unregister_extension(self, extension_name: str) -> bool:
        """
        Unregister an extension by name.
        
        Returns:
            True if extension was removed, False if not found
        """
        for i, ext in enumerate(self._extensions):
            if ext.name == extension_name:
                self._extensions.pop(i)
                return True
        return False
    
    def register_hook(self, hook: Callable[[Any, Dict[str, Any]], Any]) -> None:
        """Register a simple hook function."""
        self._hooks.append(hook)
    
    def execute(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute all registered extensions and hooks.
        
        Args:
            data: Input data
            context: Optional execution context
            
        Returns:
            Modified data after all extensions
        """
        context = context or {}
        result = data
        
        # Execute extensions
        for extension in self._extensions:
            result = extension.execute(result, context)
        
        # Execute hooks
        for hook in self._hooks:
            result = hook(result, context)
        
        return result
    
    def has_extensions(self) -> bool:
        """Check if any extensions are registered."""
        return len(self._extensions) > 0 or len(self._hooks) > 0
    
    def get_extensions(self) -> List[Extension]:
        """Get all registered extensions."""
        return self._extensions.copy()


class ExtensionRegistry:
    """
    Central registry for managing extension points.
    """
    
    def __init__(self):
        self._extension_points: Dict[str, ExtensionPoint] = {}
        self._initialize_default_points()
    
    def _initialize_default_points(self) -> None:
        """Initialize default extension points."""
        default_points = [
            (ExtensionPointType.PRE_SERIALIZATION, "pre_serialization"),
            (ExtensionPointType.POST_DESERIALIZATION, "post_deserialization"),
            (ExtensionPointType.PRE_VALIDATION, "pre_validation"),
            (ExtensionPointType.POST_VALIDATION, "post_validation"),
            (ExtensionPointType.CHARGE_EVENT_CREATED, "charge_event_created"),
            (ExtensionPointType.DELEGATION_TOKEN_VALIDATED, "delegation_token_validated"),
            (ExtensionPointType.AUDIT_BUNDLE_GENERATED, "audit_bundle_generated"),
            (ExtensionPointType.DISPUTE_EVENT_CREATED, "dispute_event_created"),
        ]
        
        for point_type, name in default_points:
            self.register_point(ExtensionPoint(point_type, name))
    
    def register_point(self, point: ExtensionPoint) -> None:
        """Register an extension point."""
        self._extension_points[point.name] = point
    
    def get_point(self, name: str) -> Optional[ExtensionPoint]:
        """Get an extension point by name."""
        return self._extension_points.get(name)
    
    def register_extension(self, point_name: str, extension: Extension) -> None:
        """
        Register an extension at a specific point.
        
        Args:
            point_name: Name of the extension point
            extension: Extension to register
            
        Raises:
            ValueError: If extension point doesn't exist
        """
        point = self.get_point(point_name)
        if point is None:
            raise ValueError(f"Extension point '{point_name}' not found")
        point.register_extension(extension)
    
    def register_hook(self, point_name: str, hook: Callable) -> None:
        """
        Register a hook function at a specific point.
        
        Args:
            point_name: Name of the extension point
            hook: Hook function to register
            
        Raises:
            ValueError: If extension point doesn't exist
        """
        point = self.get_point(point_name)
        if point is None:
            raise ValueError(f"Extension point '{point_name}' not found")
        point.register_hook(hook)
    
    def execute_point(self, point_name: str, data: Any,
                     context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute all extensions at a specific point.
        
        Args:
            point_name: Name of the extension point
            data: Input data
            context: Optional execution context
            
        Returns:
            Modified data after all extensions
        """
        point = self.get_point(point_name)
        if point is None:
            return data
        return point.execute(data, context)
    
    def list_points(self) -> List[str]:
        """List all registered extension point names."""
        return list(self._extension_points.keys())
    
    def clear_point(self, point_name: str) -> None:
        """Clear all extensions from a specific point."""
        point = self.get_point(point_name)
        if point:
            point._extensions.clear()
            point._hooks.clear()


# Global extension registry instance
_global_registry: Optional[ExtensionRegistry] = None


def get_global_registry() -> ExtensionRegistry:
    """Get the global extension registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ExtensionRegistry()
    return _global_registry


def register_extension(point_name: str, extension: Extension) -> None:
    """Register an extension at the global registry."""
    get_global_registry().register_extension(point_name, extension)


def register_hook(point_name: str, hook: Callable) -> None:
    """Register a hook at the global registry."""
    get_global_registry().register_hook(point_name, hook)
