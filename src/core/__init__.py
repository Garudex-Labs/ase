"""
Core message processing components for ASE protocol.
"""

from .serialization import MessageSerializer, MessageDeserializer
from .validation import ValidationPipeline, ValidationError, ValidationResult
from .extensions import ExtensionRegistry, ExtensionPoint

__all__ = [
    "MessageSerializer",
    "MessageDeserializer",
    "ValidationPipeline",
    "ValidationError",
    "ValidationResult",
    "ExtensionRegistry",
    "ExtensionPoint",
]
