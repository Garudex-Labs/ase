"""
Key management and certificate handling for ASE protocol.

Provides interfaces for managing cryptographic keys used in signing and verification.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone


class KeyType(Enum):
    """Types of cryptographic keys."""
    EC_P256 = "EC_P256"  # Elliptic Curve P-256
    EC_P384 = "EC_P384"  # Elliptic Curve P-384
    EC_P521 = "EC_P521"  # Elliptic Curve P-521
    RSA_2048 = "RSA_2048"  # RSA 2048-bit
    RSA_3072 = "RSA_3072"  # RSA 3072-bit
    RSA_4096 = "RSA_4096"  # RSA 4096-bit


@dataclass
class KeyPair:
    """Represents a cryptographic key pair."""
    key_id: str
    key_type: KeyType
    public_key: Any  # Actual key object (implementation-specific)
    private_key: Optional[Any] = None  # None for public-only keys
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    def has_private_key(self) -> bool:
        """Check if private key is available."""
        return self.private_key is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding private key)."""
        return {
            "keyId": self.key_id,
            "keyType": self.key_type.value,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }


@dataclass
class Certificate:
    """Represents a certificate for key verification."""
    cert_id: str
    key_id: str
    subject: str
    issuer: str
    valid_from: datetime
    valid_until: datetime
    certificate_data: Any  # Actual certificate object
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        now = datetime.now(timezone.utc)
        return self.valid_from <= now <= self.valid_until
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "certId": self.cert_id,
            "keyId": self.key_id,
            "subject": self.subject,
            "issuer": self.issuer,
            "validFrom": self.valid_from.isoformat(),
            "validUntil": self.valid_until.isoformat(),
            "metadata": self.metadata,
        }


class KeyManagementError(Exception):
    """Base exception for key management operations."""
    pass


class KeyNotFoundError(KeyManagementError):
    """Raised when a key is not found."""
    pass


class KeyExpiredError(KeyManagementError):
    """Raised when attempting to use an expired key."""
    pass


class KeyManager(ABC):
    """
    Abstract interface for key management.
    
    Implementations can use local storage, HSM, or cloud KMS.
    """
    
    @abstractmethod
    def generate_key(self, key_id: str, key_type: KeyType,
                    metadata: Optional[Dict[str, Any]] = None) -> KeyPair:
        """
        Generate a new key pair.
        
        Args:
            key_id: Unique identifier for the key
            key_type: Type of key to generate
            metadata: Optional metadata to attach to key
            
        Returns:
            Generated KeyPair
            
        Raises:
            KeyManagementError: If key generation fails
        """
        pass
    
    @abstractmethod
    def import_key(self, key_id: str, key_type: KeyType, public_key: Any,
                  private_key: Optional[Any] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> KeyPair:
        """
        Import an existing key pair.
        
        Args:
            key_id: Unique identifier for the key
            key_type: Type of key
            public_key: Public key object
            private_key: Optional private key object
            metadata: Optional metadata to attach to key
            
        Returns:
            Imported KeyPair
            
        Raises:
            KeyManagementError: If key import fails
        """
        pass
    
    @abstractmethod
    def get_key(self, key_id: str) -> Optional[KeyPair]:
        """
        Retrieve a key pair by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            KeyPair if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """
        Delete a key pair.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if key was deleted, False if not found
        """
        pass
    
    @abstractmethod
    def list_keys(self) -> List[KeyPair]:
        """
        List all available keys.
        
        Returns:
            List of KeyPair objects (may exclude private keys)
        """
        pass
    
    @abstractmethod
    def rotate_key(self, old_key_id: str, new_key_id: str,
                  overlap_period_days: int = 30) -> KeyPair:
        """
        Rotate a key with overlapping validity period.
        
        Args:
            old_key_id: ID of key to rotate
            new_key_id: ID for new key
            overlap_period_days: Days of overlap for gradual migration
            
        Returns:
            New KeyPair
            
        Raises:
            KeyManagementError: If rotation fails
        """
        pass


class InMemoryKeyManager(KeyManager):
    """
    Simple in-memory key manager for testing and development.
    
    WARNING: Not suitable for production use. Keys are not persisted.
    """
    
    def __init__(self):
        self._keys: Dict[str, KeyPair] = {}
    
    def generate_key(self, key_id: str, key_type: KeyType,
                    metadata: Optional[Dict[str, Any]] = None) -> KeyPair:
        """Generate a new key pair (placeholder implementation)."""
        # Placeholder - real implementation would generate actual keys
        key_pair = KeyPair(
            key_id=key_id,
            key_type=key_type,
            public_key=f"public_key_{key_id}",
            private_key=f"private_key_{key_id}",
            metadata=metadata or {}
        )
        self._keys[key_id] = key_pair
        return key_pair
    
    def import_key(self, key_id: str, key_type: KeyType, public_key: Any,
                  private_key: Optional[Any] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> KeyPair:
        """Import an existing key pair."""
        key_pair = KeyPair(
            key_id=key_id,
            key_type=key_type,
            public_key=public_key,
            private_key=private_key,
            metadata=metadata or {}
        )
        self._keys[key_id] = key_pair
        return key_pair
    
    def get_key(self, key_id: str) -> Optional[KeyPair]:
        """Retrieve a key pair by ID."""
        return self._keys.get(key_id)
    
    def delete_key(self, key_id: str) -> bool:
        """Delete a key pair."""
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False
    
    def list_keys(self) -> List[KeyPair]:
        """List all available keys."""
        return list(self._keys.values())
    
    def rotate_key(self, old_key_id: str, new_key_id: str,
                  overlap_period_days: int = 30) -> KeyPair:
        """Rotate a key with overlapping validity period."""
        old_key = self.get_key(old_key_id)
        if old_key is None:
            raise KeyNotFoundError(f"Key not found: {old_key_id}")
        
        # Generate new key with same type
        new_key = self.generate_key(new_key_id, old_key.key_type)
        
        # Set expiration on old key
        from datetime import timedelta
        old_key.expires_at = datetime.now(timezone.utc) + timedelta(days=overlap_period_days)
        
        return new_key


class CertificateManager(ABC):
    """
    Abstract interface for certificate management.
    
    Handles certificate storage, validation, and chain verification.
    """
    
    @abstractmethod
    def add_certificate(self, certificate: Certificate) -> None:
        """
        Add a certificate to the store.
        
        Args:
            certificate: Certificate to add
            
        Raises:
            KeyManagementError: If certificate cannot be added
        """
        pass
    
    @abstractmethod
    def get_certificate(self, cert_id: str) -> Optional[Certificate]:
        """
        Retrieve a certificate by ID.
        
        Args:
            cert_id: Certificate identifier
            
        Returns:
            Certificate if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_certificates_for_key(self, key_id: str) -> List[Certificate]:
        """
        Get all certificates for a specific key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            List of certificates
        """
        pass
    
    @abstractmethod
    def verify_certificate_chain(self, cert_id: str) -> bool:
        """
        Verify certificate chain up to trusted root.
        
        Args:
            cert_id: Certificate identifier
            
        Returns:
            True if chain is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def revoke_certificate(self, cert_id: str) -> bool:
        """
        Revoke a certificate.
        
        Args:
            cert_id: Certificate identifier
            
        Returns:
            True if certificate was revoked, False if not found
        """
        pass


class InMemoryCertificateManager(CertificateManager):
    """Simple in-memory certificate manager for testing."""
    
    def __init__(self):
        self._certificates: Dict[str, Certificate] = {}
        self._revoked: set = set()
    
    def add_certificate(self, certificate: Certificate) -> None:
        """Add a certificate to the store."""
        self._certificates[certificate.cert_id] = certificate
    
    def get_certificate(self, cert_id: str) -> Optional[Certificate]:
        """Retrieve a certificate by ID."""
        return self._certificates.get(cert_id)
    
    def get_certificates_for_key(self, key_id: str) -> List[Certificate]:
        """Get all certificates for a specific key."""
        return [cert for cert in self._certificates.values() if cert.key_id == key_id]
    
    def verify_certificate_chain(self, cert_id: str) -> bool:
        """Verify certificate chain (placeholder)."""
        cert = self.get_certificate(cert_id)
        if cert is None:
            return False
        if cert_id in self._revoked:
            return False
        return cert.is_valid()
    
    def revoke_certificate(self, cert_id: str) -> bool:
        """Revoke a certificate."""
        if cert_id in self._certificates:
            self._revoked.add(cert_id)
            return True
        return False
