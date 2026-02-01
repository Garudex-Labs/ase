"""
Signing and verification service interfaces for ASE protocol.

Supports ES256 (ECDSA with P-256) and RS256 (RSA with SHA-256) algorithms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SignatureAlgorithm(Enum):
    """Supported signature algorithms."""
    ES256 = "ES256"  # ECDSA with P-256 and SHA-256
    RS256 = "RS256"  # RSA with SHA-256
    ES384 = "ES384"  # ECDSA with P-384 and SHA-384
    RS384 = "RS384"  # RSA with SHA-384
    ES512 = "ES512"  # ECDSA with P-521 and SHA-512
    RS512 = "RS512"  # RSA with SHA-512


@dataclass
class SignatureResult:
    """Result of a signing operation."""
    signature: str
    algorithm: SignatureAlgorithm
    key_id: str
    metadata: Dict[str, Any]


@dataclass
class VerificationResult:
    """Result of a signature verification operation."""
    is_valid: bool
    algorithm: SignatureAlgorithm
    key_id: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CryptographicError(Exception):
    """Base exception for cryptographic operations."""
    pass


class SigningError(CryptographicError):
    """Raised when signing operation fails."""
    pass


class VerificationError(CryptographicError):
    """Raised when verification operation fails."""
    pass


class SigningService(ABC):
    """
    Abstract interface for signing service.
    
    Implementations provide cryptographic signing for delegation tokens
    and audit bundles.
    """
    
    @abstractmethod
    def sign(self, data: bytes, key_id: str,
             algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> SignatureResult:
        """
        Sign data using specified key and algorithm.
        
        Args:
            data: Data to sign
            key_id: Identifier of the signing key
            algorithm: Signature algorithm to use
            
        Returns:
            SignatureResult containing signature and metadata
            
        Raises:
            SigningError: If signing fails
        """
        pass
    
    @abstractmethod
    def sign_json(self, data: Dict[str, Any], key_id: str,
                  algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> SignatureResult:
        """
        Sign JSON data (canonical JSON serialization).
        
        Args:
            data: JSON-serializable data to sign
            key_id: Identifier of the signing key
            algorithm: Signature algorithm to use
            
        Returns:
            SignatureResult containing signature and metadata
            
        Raises:
            SigningError: If signing fails
        """
        pass
    
    @abstractmethod
    def get_supported_algorithms(self) -> list[SignatureAlgorithm]:
        """
        Get list of supported signature algorithms.
        
        Returns:
            List of supported algorithms
        """
        pass


class VerificationService(ABC):
    """
    Abstract interface for signature verification service.
    
    Implementations verify cryptographic signatures on delegation tokens
    and audit bundles.
    """
    
    @abstractmethod
    def verify(self, data: bytes, signature: str, key_id: str,
               algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> VerificationResult:
        """
        Verify signature on data.
        
        Args:
            data: Original data that was signed
            signature: Signature to verify
            key_id: Identifier of the verification key
            algorithm: Signature algorithm used
            
        Returns:
            VerificationResult indicating success or failure
            
        Raises:
            VerificationError: If verification process fails (not invalid signature)
        """
        pass
    
    @abstractmethod
    def verify_json(self, data: Dict[str, Any], signature: str, key_id: str,
                    algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> VerificationResult:
        """
        Verify signature on JSON data (canonical JSON serialization).
        
        Args:
            data: Original JSON data that was signed
            signature: Signature to verify
            key_id: Identifier of the verification key
            algorithm: Signature algorithm used
            
        Returns:
            VerificationResult indicating success or failure
            
        Raises:
            VerificationError: If verification process fails
        """
        pass
    
    @abstractmethod
    def get_supported_algorithms(self) -> list[SignatureAlgorithm]:
        """
        Get list of supported signature algorithms.
        
        Returns:
            List of supported algorithms
        """
        pass


class DefaultSigningService(SigningService):
    """
    Default implementation of signing service using cryptography library.
    
    This is a reference implementation that can be replaced with
    hardware security module (HSM) or key management service (KMS) implementations.
    """
    
    def __init__(self, key_manager):
        """
        Initialize signing service.
        
        Args:
            key_manager: KeyManager instance for key access
        """
        self.key_manager = key_manager
    
    def sign(self, data: bytes, key_id: str,
             algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> SignatureResult:
        """Sign data using specified key and algorithm."""
        try:
            key_pair = self.key_manager.get_key(key_id)
            if key_pair is None:
                raise SigningError(f"Key not found: {key_id}")
            
            # Implementation would use cryptography library here
            # This is a placeholder for the actual signing logic
            signature = self._sign_with_algorithm(data, key_pair.private_key, algorithm)
            
            return SignatureResult(
                signature=signature,
                algorithm=algorithm,
                key_id=key_id,
                metadata={"timestamp": self._get_timestamp()}
            )
        except Exception as e:
            raise SigningError(f"Signing failed: {e}") from e
    
    def sign_json(self, data: Dict[str, Any], key_id: str,
                  algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> SignatureResult:
        """Sign JSON data with canonical serialization."""
        import json
        # Canonical JSON: sorted keys, no whitespace
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return self.sign(canonical_json.encode('utf-8'), key_id, algorithm)
    
    def get_supported_algorithms(self) -> list[SignatureAlgorithm]:
        """Get supported algorithms."""
        return [
            SignatureAlgorithm.ES256,
            SignatureAlgorithm.RS256,
            SignatureAlgorithm.ES384,
            SignatureAlgorithm.RS384,
            SignatureAlgorithm.ES512,
            SignatureAlgorithm.RS512,
        ]
    
    def _sign_with_algorithm(self, data: bytes, private_key: Any,
                            algorithm: SignatureAlgorithm) -> str:
        """
        Internal method to sign data with specific algorithm.
        
        This is a placeholder - actual implementation would use cryptography library.
        """
        # Placeholder implementation
        import base64
        import hashlib
        
        # In real implementation, this would use proper cryptographic signing
        # For now, just return a mock signature
        hash_obj = hashlib.sha256(data)
        return base64.b64encode(hash_obj.digest()).decode('utf-8')
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


class DefaultVerificationService(VerificationService):
    """
    Default implementation of verification service.
    
    This is a reference implementation that can be replaced with
    custom verification logic.
    """
    
    def __init__(self, key_manager):
        """
        Initialize verification service.
        
        Args:
            key_manager: KeyManager instance for key access
        """
        self.key_manager = key_manager
    
    def verify(self, data: bytes, signature: str, key_id: str,
               algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> VerificationResult:
        """Verify signature on data."""
        try:
            key_pair = self.key_manager.get_key(key_id)
            if key_pair is None:
                return VerificationResult(
                    is_valid=False,
                    algorithm=algorithm,
                    key_id=key_id,
                    error_message=f"Key not found: {key_id}"
                )
            
            # Implementation would use cryptography library here
            is_valid = self._verify_with_algorithm(data, signature, key_pair.public_key, algorithm)
            
            return VerificationResult(
                is_valid=is_valid,
                algorithm=algorithm,
                key_id=key_id,
                metadata={"timestamp": self._get_timestamp()}
            )
        except Exception as e:
            raise VerificationError(f"Verification failed: {e}") from e
    
    def verify_json(self, data: Dict[str, Any], signature: str, key_id: str,
                    algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> VerificationResult:
        """Verify signature on JSON data."""
        import json
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return self.verify(canonical_json.encode('utf-8'), signature, key_id, algorithm)
    
    def get_supported_algorithms(self) -> list[SignatureAlgorithm]:
        """Get supported algorithms."""
        return [
            SignatureAlgorithm.ES256,
            SignatureAlgorithm.RS256,
            SignatureAlgorithm.ES384,
            SignatureAlgorithm.RS384,
            SignatureAlgorithm.ES512,
            SignatureAlgorithm.RS512,
        ]
    
    def _verify_with_algorithm(self, data: bytes, signature: str, public_key: Any,
                               algorithm: SignatureAlgorithm) -> bool:
        """
        Internal method to verify signature with specific algorithm.
        
        This is a placeholder - actual implementation would use cryptography library.
        """
        # Placeholder implementation
        # In real implementation, this would use proper cryptographic verification
        return True
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
