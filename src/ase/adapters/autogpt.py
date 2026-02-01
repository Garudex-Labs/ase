"""
AutoGPT framework adapter for ASE protocol.

Integrates ASE economic metadata with AutoGPT's command and agent abstractions.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from .base import (
    FrameworkAdapter,
    FrameworkType,
    AdapterConfig,
    AdapterError,
    MessageTransformer,
    ConventionValidator,
)
from core.models import EconomicMetadata, ChargeEvent, MonetaryAmount


class AutoGPTMessageTransformer(MessageTransformer):
    """Transforms messages between AutoGPT and ASE formats."""
    
    def to_ase_format(self, framework_message: Any) -> Dict[str, Any]:
        """
        Transform AutoGPT message to ASE format.
        
        AutoGPT messages typically have:
        - role: str (system, user, assistant)
        - content: str
        - metadata: dict (optional)
        """
        if isinstance(framework_message, dict):
            ase_message = {
                "role": framework_message.get("role", "user"),
                "content": framework_message.get("content", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if "metadata" in framework_message:
                ase_message["metadata"] = framework_message["metadata"]
        else:
            ase_message = {
                "role": getattr(framework_message, "role", "user"),
                "content": getattr(framework_message, "content", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if hasattr(framework_message, "metadata"):
                ase_message["metadata"] = framework_message.metadata
        
        return ase_message
    
    def from_ase_format(self, ase_message: Dict[str, Any]) -> Any:
        """
        Transform ASE message to AutoGPT format.
        """
        return {
            "role": ase_message.get("role", "user"),
            "content": ase_message.get("content", ""),
            "metadata": ase_message.get("metadata", {}),
        }


class AutoGPTConventionValidator(ConventionValidator):
    """Validates AutoGPT-specific conventions."""
    
    def validate_message_structure(self, message: Any) -> tuple[bool, List[str]]:
        """Validate AutoGPT message structure."""
        errors = []
        
        # Check for required fields
        if isinstance(message, dict):
            if "role" not in message:
                errors.append("Message missing 'role' field")
            if "content" not in message:
                errors.append("Message missing 'content' field")
            
            # Validate role
            valid_roles = ["system", "user", "assistant", "function"]
            if "role" in message and message["role"] not in valid_roles:
                errors.append(f"Invalid role: {message['role']}")
        else:
            if not hasattr(message, "role"):
                errors.append("Message missing 'role' attribute")
            if not hasattr(message, "content"):
                errors.append("Message missing 'content' attribute")
        
        return (len(errors) == 0, errors)
    
    def validate_metadata_placement(self, message: Any) -> tuple[bool, List[str]]:
        """Validate metadata placement in AutoGPT message."""
        errors = []
        
        # AutoGPT uses metadata field for additional data
        if isinstance(message, dict):
            metadata = message.get("metadata", {})
        else:
            metadata = getattr(message, "metadata", {})
        
        if metadata:
            # Check if ASE metadata is properly nested
            if "aseMetadata" in metadata:
                ase_metadata = metadata["aseMetadata"]
                if not isinstance(ase_metadata, dict):
                    errors.append("aseMetadata must be a dictionary")
        
        return (len(errors) == 0, errors)
    
    def get_convention_guidelines(self) -> Dict[str, str]:
        """Get AutoGPT convention guidelines."""
        return {
            "message_structure": "Use dict with 'role' and 'content' fields",
            "metadata_placement": "Place ASE metadata in metadata['aseMetadata']",
            "role_usage": "Use appropriate role (system, user, assistant, function)",
            "command_format": "Commands should include name, args, and optional metadata",
        }


class AutoGPTAdapter(FrameworkAdapter):
    """
    Adapter for AutoGPT framework integration.
    
    Provides seamless integration of ASE economic metadata with AutoGPT's
    command execution and agent coordination patterns.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """
        Initialize AutoGPT adapter.
        
        Args:
            config: Optional adapter configuration
        """
        if config is None:
            config = AdapterConfig(framework_type=FrameworkType.AUTOGPT)
        super().__init__(config)
        
        self.transformer = AutoGPTMessageTransformer()
        self.validator = AutoGPTConventionValidator()
    
    @property
    def framework_type(self) -> FrameworkType:
        """Return framework type."""
        return FrameworkType.AUTOGPT
    
    def wrap_message(self, message: Any, economic_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """
        Wrap AutoGPT message with ASE economic metadata.
        
        Places metadata in message metadata field following AutoGPT conventions.
        """
        try:
            # Convert to dict if needed
            if isinstance(message, dict):
                message_dict = message.copy()
            else:
                message_dict = {
                    "role": getattr(message, "role", "user"),
                    "content": getattr(message, "content", ""),
                    "metadata": getattr(message, "metadata", {}).copy() if hasattr(message, "metadata") else {},
                }
            
            # Get or create metadata
            metadata = message_dict.get("metadata", {}).copy()
            
            # Add ASE metadata
            if economic_metadata:
                metadata["aseMetadata"] = economic_metadata
            elif self.config.auto_attach_metadata:
                # Attach default metadata
                metadata["aseMetadata"] = self.get_metadata_defaults()
            
            message_dict["metadata"] = metadata
            
            self.execute_hooks("message_wrapped", message, message_dict)
            
            return message_dict
            
        except Exception as e:
            raise AdapterError(f"Failed to wrap AutoGPT message: {e}") from e
    
    def unwrap_message(self, wrapped_message: Any) -> tuple[Any, Optional[Dict[str, Any]]]:
        """
        Unwrap AutoGPT message to extract ASE metadata.
        """
        try:
            # Convert to dict if needed
            if isinstance(wrapped_message, dict):
                message_dict = wrapped_message
            else:
                message_dict = {
                    "role": getattr(wrapped_message, "role", "user"),
                    "content": getattr(wrapped_message, "content", ""),
                    "metadata": getattr(wrapped_message, "metadata", {}),
                }
            
            # Extract metadata
            metadata = message_dict.get("metadata", {})
            economic_metadata = metadata.get("aseMetadata")
            
            # Create clean message without ASE metadata
            clean_message = message_dict.copy()
            if "metadata" in clean_message:
                clean_metadata = clean_message["metadata"].copy()
                clean_metadata.pop("aseMetadata", None)
                clean_message["metadata"] = clean_metadata
            
            self.execute_hooks("message_unwrapped", wrapped_message, clean_message, economic_metadata)
            
            return (clean_message, economic_metadata)
            
        except Exception as e:
            raise AdapterError(f"Failed to unwrap AutoGPT message: {e}") from e
    
    def attach_delegation_token(self, message: Any, token: str) -> Any:
        """
        Attach delegation token to AutoGPT message.
        """
        try:
            # Convert to dict if needed
            if isinstance(message, dict):
                message_dict = message.copy()
            else:
                message_dict = {
                    "role": getattr(message, "role", "user"),
                    "content": getattr(message, "content", ""),
                    "metadata": getattr(message, "metadata", {}).copy() if hasattr(message, "metadata") else {},
                }
            
            # Get or create metadata
            metadata = message_dict.get("metadata", {}).copy()
            ase_metadata = metadata.get("aseMetadata", {}).copy()
            ase_metadata["delegationToken"] = token
            metadata["aseMetadata"] = ase_metadata
            message_dict["metadata"] = metadata
            
            self.execute_hooks("token_attached", message_dict, token)
            
            return message_dict
            
        except Exception as e:
            raise AdapterError(f"Failed to attach delegation token: {e}") from e
    
    def extract_delegation_token(self, message: Any) -> Optional[str]:
        """
        Extract delegation token from AutoGPT message.
        """
        try:
            # Extract metadata
            if isinstance(message, dict):
                metadata = message.get("metadata", {})
            else:
                metadata = getattr(message, "metadata", {})
            
            # Extract token from ASE metadata
            ase_metadata = metadata.get("aseMetadata", {})
            token = ase_metadata.get("delegationToken")
            
            return token
            
        except Exception as e:
            raise AdapterError(f"Failed to extract delegation token: {e}") from e
    
    def create_charge_event(self, event_type: str, amount: Dict[str, Any],
                          agent_id: str, description: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create charge event in AutoGPT-compatible format.
        """
        event_id_prefix = "evt_prov_" if event_type == "provisional" else "evt_final_"
        event_id = f"{event_id_prefix}{uuid.uuid4().hex[:16]}"
        
        # Validate amount using MonetaryAmount model
        monetary_amount = MonetaryAmount(value=amount["value"], currency=amount["currency"])
        
        charge_event = ChargeEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            agent_id=agent_id,
            amount=monetary_amount,
            description=description,
            status="pending" if event_type == "provisional" else "confirmed",
            metadata=metadata
        )
        
        # Serialize to dict (camelCase)
        charge_dict = charge_event.to_dict()
        
        self.execute_hooks("charge_event_created", charge_dict)
        
        return charge_dict
    
    def validate_framework_conventions(self, message: Any) -> bool:
        """
        Validate AutoGPT conventions.
        """
        # Validate message structure
        is_valid, errors = self.validator.validate_message_structure(message)
        if not is_valid:
            return False
        
        # Validate metadata placement
        is_valid, errors = self.validator.validate_metadata_placement(message)
        return is_valid
    
    def wrap_command(self, command: Dict[str, Any],
                    economic_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Wrap AutoGPT command with ASE economic metadata.
        
        Args:
            command: AutoGPT command dict with 'name' and 'args'
            economic_metadata: Optional ASE economic metadata
            
        Returns:
            Wrapped command with ASE metadata
        """
        try:
            wrapped_command = command.copy()
            
            # Get or create metadata
            metadata = wrapped_command.get("metadata", {}).copy()
            
            # Add ASE metadata
            if economic_metadata:
                metadata["aseMetadata"] = economic_metadata
            elif self.config.auto_attach_metadata:
                metadata["aseMetadata"] = self.get_metadata_defaults()
            
            wrapped_command["metadata"] = metadata
            
            self.execute_hooks("command_wrapped", command, wrapped_command)
            
            return wrapped_command
            
        except Exception as e:
            raise AdapterError(f"Failed to wrap AutoGPT command: {e}") from e
    
    def unwrap_command(self, wrapped_command: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Unwrap AutoGPT command to extract ASE metadata.
        
        Args:
            wrapped_command: Wrapped command with ASE metadata
            
        Returns:
            Tuple of (clean_command, economic_metadata)
        """
        try:
            # Extract metadata
            metadata = wrapped_command.get("metadata", {})
            economic_metadata = metadata.get("aseMetadata")
            
            # Create clean command without ASE metadata
            clean_command = wrapped_command.copy()
            if "metadata" in clean_command:
                clean_metadata = clean_command["metadata"].copy()
                clean_metadata.pop("aseMetadata", None)
                clean_command["metadata"] = clean_metadata
            
            self.execute_hooks("command_unwrapped", wrapped_command, clean_command, economic_metadata)
            
            return (clean_command, economic_metadata)
            
        except Exception as e:
            raise AdapterError(f"Failed to unwrap AutoGPT command: {e}") from e
