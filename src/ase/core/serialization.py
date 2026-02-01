"""
Serialization and deserialization interfaces for ASE messages.

This module provides automatic conversion between internal snake_case representation
and wire format camelCase representation using Pydantic models.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T", bound=BaseModel)


class SerializationError(Exception):
    """Raised when serialization or deserialization fails."""
    pass


class MessageSerializer:
    """
    Serializes ASE messages from internal Python models to JSON wire format.
    
    Automatically converts snake_case field names to camelCase for JSON output.
    """
    
    def __init__(self, pretty: bool = False):
        """
        Initialize the serializer.
        
        Args:
            pretty: If True, output formatted JSON with indentation
        """
        self.pretty = pretty
    
    def serialize(self, message: BaseModel) -> str:
        """
        Serialize a Pydantic model to JSON string.
        
        Args:
            message: Pydantic model instance to serialize
            
        Returns:
            JSON string with camelCase field names
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            # Use by_alias=True to output camelCase field names
            json_dict = message.model_dump(by_alias=True, exclude_none=True)
            
            if self.pretty:
                return json.dumps(json_dict, indent=2, sort_keys=False)
            else:
                return json.dumps(json_dict)
        except Exception as e:
            raise SerializationError(f"Failed to serialize message: {e}") from e
    
    def serialize_to_dict(self, message: BaseModel) -> Dict[str, Any]:
        """
        Serialize a Pydantic model to dictionary.
        
        Args:
            message: Pydantic model instance to serialize
            
        Returns:
            Dictionary with camelCase field names
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            return message.model_dump(by_alias=True, exclude_none=True)
        except Exception as e:
            raise SerializationError(f"Failed to serialize message to dict: {e}") from e


class MessageDeserializer:
    """
    Deserializes ASE messages from JSON wire format to internal Python models.
    
    Accepts both camelCase (wire format) and snake_case (internal) field names
    for backward compatibility.
    """
    
    def deserialize(self, json_str: str, model_class: Type[T]) -> T:
        """
        Deserialize JSON string to Pydantic model.
        
        Args:
            json_str: JSON string to deserialize
            model_class: Target Pydantic model class
            
        Returns:
            Instance of model_class
            
        Raises:
            SerializationError: If deserialization fails
        """
        try:
            data = json.loads(json_str)
            return self.deserialize_from_dict(data, model_class)
        except json.JSONDecodeError as e:
            raise SerializationError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise SerializationError(f"Failed to deserialize message: {e}") from e
    
    def deserialize_from_dict(self, data: Dict[str, Any], model_class: Type[T]) -> T:
        """
        Deserialize dictionary to Pydantic model.
        
        Args:
            data: Dictionary to deserialize
            model_class: Target Pydantic model class
            
        Returns:
            Instance of model_class
            
        Raises:
            SerializationError: If deserialization fails
        """
        try:
            # Pydantic will accept both camelCase and snake_case due to populate_by_name=True
            return model_class.model_validate(data)
        except Exception as e:
            raise SerializationError(f"Failed to deserialize from dict: {e}") from e


class SerializableModel(BaseModel):
    """
    Base model for all ASE message types with automatic snake_case/camelCase conversion.
    
    Internal Python code uses snake_case attributes.
    JSON wire format uses camelCase field names.
    """
    
    model_config = ConfigDict(
        # Allow population by both field name and alias
        populate_by_name=True,
        # Use aliases (camelCase) when serializing
        use_enum_values=True,
        # Validate on assignment
        validate_assignment=True,
        # Allow arbitrary types for extensibility
        arbitrary_types_allowed=True,
    )
    
    def to_json(self, pretty: bool = False) -> str:
        """
        Serialize to JSON string with camelCase field names.
        
        Args:
            pretty: If True, output formatted JSON
            
        Returns:
            JSON string
        """
        serializer = MessageSerializer(pretty=pretty)
        return serializer.serialize(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary with camelCase field names.
        
        Returns:
            Dictionary representation
        """
        serializer = MessageSerializer()
        return serializer.serialize_to_dict(self)
    
    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """
        Deserialize from JSON string.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Instance of this model class
        """
        deserializer = MessageDeserializer()
        return deserializer.deserialize(json_str, cls)
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary to deserialize
            
        Returns:
            Instance of this model class
        """
        deserializer = MessageDeserializer()
        return deserializer.deserialize_from_dict(data, cls)
