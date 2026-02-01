"""
LangChain framework adapter for ASE protocol.

Integrates ASE economic metadata with LangChain's message and chain abstractions.
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


class LangChainMessageTransformer(MessageTransformer):
    """Transforms messages between LangChain and ASE formats."""
    
    def to_ase_format(self, framework_message: Any) -> Dict[str, Any]:
        """
        Transform LangChain message to ASE format.
        
        LangChain messages typically have:
        - content: str
        - additional_kwargs: dict
        - type: str (human, ai, system, etc.)
        """
        ase_message = {
            "content": getattr(framework_message, "content", ""),
            "type": getattr(framework_message, "type", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Extract additional kwargs
        additional_kwargs = getattr(framework_message, "additional_kwargs", {})
        if additional_kwargs:
            ase_message["metadata"] = additional_kwargs
        
        return ase_message
    
    def from_ase_format(self, ase_message: Dict[str, Any]) -> Any:
        """
        Transform ASE message to LangChain format.
        
        Note: This returns a dictionary that can be used to construct
        LangChain message objects. Actual construction depends on LangChain version.
        """
        return {
            "content": ase_message.get("content", ""),
            "type": ase_message.get("type", "human"),
            "additional_kwargs": ase_message.get("metadata", {}),
        }


class LangChainConventionValidator(ConventionValidator):
    """Validates LangChain-specific conventions."""
    
    def validate_message_structure(self, message: Any) -> tuple[bool, List[str]]:
        """Validate LangChain message structure."""
        errors = []
        
        # Helper to check attribute existence
        def has_attr(obj, attr):
            if isinstance(obj, dict):
                return attr in obj
            return hasattr(obj, attr)
            
        def get_attr(obj, attr):
            if isinstance(obj, dict):
                return obj.get(attr)
            return getattr(obj, attr)
        
        # Check for required attributes
        if not has_attr(message, "content"):
            errors.append("Message missing 'content' attribute")
        
        if not has_attr(message, "type"):
            errors.append("Message missing 'type' attribute")
        
        # Validate type
        valid_types = ["human", "ai", "system", "function", "tool"]
        msg_type = get_attr(message, "type")
        if has_attr(message, "type") and msg_type not in valid_types:
            errors.append(f"Invalid message type: {msg_type}")
        
        return (len(errors) == 0, errors)
    
    def validate_metadata_placement(self, message: Any) -> tuple[bool, List[str]]:
        """Validate metadata placement in LangChain message."""
        errors = []
        
        # Helper to get attribute
        def get_attr(obj, attr, default=None):
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)
        
        # LangChain uses additional_kwargs for metadata
        additional_kwargs = get_attr(message, "additional_kwargs")
        if additional_kwargs:
            # Check if ASE metadata is properly nested
            if "aseMetadata" in additional_kwargs:
                ase_metadata = additional_kwargs["aseMetadata"]
                if not isinstance(ase_metadata, dict):
                    errors.append("aseMetadata must be a dictionary")
        
        return (len(errors) == 0, errors)
    
    def get_convention_guidelines(self) -> Dict[str, str]:
        """Get LangChain convention guidelines."""
        return {
            "message_structure": "Use BaseMessage subclasses (HumanMessage, AIMessage, etc.)",
            "metadata_placement": "Place ASE metadata in additional_kwargs['aseMetadata']",
            "content_format": "Message content should be string or list of content blocks",
            "type_usage": "Use appropriate message type (human, ai, system, function, tool)",
        }


class LangChainAdapter(FrameworkAdapter):
    """
    Adapter for LangChain framework integration.
    
    Provides seamless integration of ASE economic metadata with LangChain's
    message passing and chain execution patterns.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """
        Initialize LangChain adapter.
        
        Args:
            config: Optional adapter configuration
        """
        if config is None:
            config = AdapterConfig(framework_type=FrameworkType.LANGCHAIN)
        super().__init__(config)
        
        self.transformer = LangChainMessageTransformer()
        self.validator = LangChainConventionValidator()
    
    @property
    def framework_type(self) -> FrameworkType:
        """Return framework type."""
        return FrameworkType.LANGCHAIN
    
    def wrap_message(self, message: Any, economic_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """
        Wrap LangChain message with ASE economic metadata.
        
        Places metadata in additional_kwargs following LangChain conventions.
        """
        try:
            # Helper to get attribute or element
            def get_attr(obj, attr, default=None):
                if isinstance(obj, dict):
                    return obj.get(attr, default)
                return getattr(obj, attr, default)
            
            # Get or create additional_kwargs
            additional_kwargs = {}
            if isinstance(message, dict):
                additional_kwargs = message.get("additional_kwargs", {}).copy()
            elif hasattr(message, "additional_kwargs"):
                additional_kwargs = message.additional_kwargs.copy()
            
            # Add ASE metadata
            if economic_metadata:
                additional_kwargs["aseMetadata"] = economic_metadata
            elif self.config.auto_attach_metadata:
                # Attach default metadata
                additional_kwargs["aseMetadata"] = self.get_metadata_defaults()
            
            # Create new message with updated kwargs
            # Note: Actual implementation depends on LangChain version
            # This is a simplified representation
            message_dict = {
                "content": get_attr(message, "content", ""),
                "type": get_attr(message, "type", "human"),
                "additional_kwargs": additional_kwargs,
            }
            
            self.execute_hooks("message_wrapped", message, message_dict)
            
            return message_dict
            
        except Exception as e:
            raise AdapterError(f"Failed to wrap LangChain message: {e}") from e
    
    def unwrap_message(self, wrapped_message: Any) -> tuple[Any, Optional[Dict[str, Any]]]:
        """
        Unwrap LangChain message to extract ASE metadata.
        """
        try:
            # Extract additional_kwargs
            if isinstance(wrapped_message, dict):
                additional_kwargs = wrapped_message.get("additional_kwargs", {})
            else:
                additional_kwargs = getattr(wrapped_message, "additional_kwargs", {})
            
            # Extract ASE metadata
            economic_metadata = additional_kwargs.get("aseMetadata")
            
            # Create clean message without ASE metadata
            if isinstance(wrapped_message, dict):
                clean_message = wrapped_message.copy()
                if "additional_kwargs" in clean_message:
                    clean_kwargs = clean_message["additional_kwargs"].copy()
                    clean_kwargs.pop("aseMetadata", None)
                    clean_message["additional_kwargs"] = clean_kwargs
            else:
                clean_message = wrapped_message
            
            self.execute_hooks("message_unwrapped", wrapped_message, clean_message, economic_metadata)
            
            return (clean_message, economic_metadata)
            
        except Exception as e:
            raise AdapterError(f"Failed to unwrap LangChain message: {e}") from e
    
    def attach_delegation_token(self, message: Any, token: str) -> Any:
        """
        Attach delegation token to LangChain message.
        """
        try:
            # Get or create additional_kwargs
            if isinstance(message, dict):
                additional_kwargs = message.get("additional_kwargs", {}).copy()
            else:
                additional_kwargs = getattr(message, "additional_kwargs", {}).copy()
            
            # Get or create ASE metadata
            ase_metadata = additional_kwargs.get("aseMetadata", {}).copy()
            ase_metadata["delegationToken"] = token
            additional_kwargs["aseMetadata"] = ase_metadata
            
            # Update message
            if isinstance(message, dict):
                message = message.copy()
                message["additional_kwargs"] = additional_kwargs
            else:
                # Create new message dict
                message = {
                    "content": getattr(message, "content", ""),
                    "type": getattr(message, "type", "human"),
                    "additional_kwargs": additional_kwargs,
                }
            
            self.execute_hooks("token_attached", message, token)
            
            return message
            
        except Exception as e:
            raise AdapterError(f"Failed to attach delegation token: {e}") from e
    
    def extract_delegation_token(self, message: Any) -> Optional[str]:
        """
        Extract delegation token from LangChain message.
        """
        try:
            # Extract additional_kwargs
            if isinstance(message, dict):
                additional_kwargs = message.get("additional_kwargs", {})
            else:
                additional_kwargs = getattr(message, "additional_kwargs", {})
            
            # Extract token from ASE metadata
            ase_metadata = additional_kwargs.get("aseMetadata", {})
            token = ase_metadata.get("delegationToken")
            
            return token
            
        except Exception as e:
            raise AdapterError(f"Failed to extract delegation token: {e}") from e
    
    def create_charge_event(self, event_type: str, amount: Dict[str, Any],
                          agent_id: str, description: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create charge event in LangChain-compatible format.
        """
        event_id_prefix = "evt_prov_" if event_type == "provisional" else "evt_final_"
        event_id = f"{event_id_prefix}{uuid.uuid4().hex[:16]}"
        
        # Validate amount structure using MonetaryAmount model
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
        Validate LangChain conventions.
        """
        # Validate message structure
        is_valid, errors = self.validator.validate_message_structure(message)
        if not is_valid:
            return False
        
        # Validate metadata placement
        is_valid, errors = self.validator.validate_metadata_placement(message)
        return is_valid
    
    def create_chain_wrapper(self, chain: Any) -> Any:
        """
        Create a wrapper for LangChain chains that automatically handles ASE metadata.
        
        Args:
            chain: LangChain chain to wrap
            
        Returns:
            Wrapped chain with ASE support
        """
        # This would wrap chain execution to automatically attach/extract metadata
        # Implementation depends on LangChain version and chain type
        class ASEChainWrapper:
            def __init__(self, chain, adapter):
                self.chain = chain
                self.adapter = adapter
            
            def __call__(self, *args, **kwargs):
                # Pre-process: attach metadata
                if "messages" in kwargs:
                    kwargs["messages"] = [
                        self.adapter.wrap_message(msg) for msg in kwargs["messages"]
                    ]
                
                # Execute chain
                result = self.chain(*args, **kwargs)
                
                # Post-process: extract metadata
                return result
        
        return ASEChainWrapper(chain, self)
