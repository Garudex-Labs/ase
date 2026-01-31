"""
Token signing and verification for delegation tokens.

Implements JWT-based delegation token creation and validation.
"""

import json
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from decimal import Decimal

from .signing import SigningService, VerificationService, SignatureAlgorithm


@dataclass
class TokenClaims:
    """Standard and ASE-specific JWT claims for delegation tokens."""
    # Standard JWT claims
    iss: str  # Issuer (delegating agent ID)
    sub: str  # Subject (delegated agent ID)
    aud: str  # Audience (target service or 'any')
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str  # Unique token ID
    
    # ASE-specific claims
    spending_limit: Dict[str, Any]  # {"value": "100.00", "currency": "USD"}
    allowed_operations: List[str]
    max_delegation_depth: int
    budget_category: str
    
    # Optional claims
    nbf: Optional[int] = None  # Not before timestamp
    parent_token_id: Optional[str] = None  # For hierarchical delegation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JWT payload."""
        result = {
            "iss": self.iss,
            "sub": self.sub,
            "aud": self.aud,
            "exp": self.exp,
            "iat": self.iat,
            "jti": self.jti,
            "spendingLimit": self.spending_limit,
            "allowedOperations": self.allowed_operations,
            "maxDelegationDepth": self.max_delegation_depth,
            "budgetCategory": self.budget_category,
        }
        if self.nbf is not None:
            result["nbf"] = self.nbf
        if self.parent_token_id is not None:
            result["parentTokenId"] = self.parent_token_id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenClaims":
        """Create from dictionary."""
        return cls(
            iss=data["iss"],
            sub=data["sub"],
            aud=data["aud"],
            exp=data["exp"],
            iat=data["iat"],
            jti=data["jti"],
            spending_limit=data["spendingLimit"],
            allowed_operations=data["allowedOperations"],
            max_delegation_depth=data["maxDelegationDepth"],
            budget_category=data["budgetCategory"],
            nbf=data.get("nbf"),
            parent_token_id=data.get("parentTokenId"),
        )


class TokenError(Exception):
    """Base exception for token operations."""
    pass


class TokenSigningError(TokenError):
    """Raised when token signing fails."""
    pass


class TokenVerificationError(TokenError):
    """Raised when token verification fails."""
    pass


class TokenExpiredError(TokenError):
    """Raised when token has expired."""
    pass


class TokenSigner:
    """
    Signs delegation tokens using JWT format.
    
    Creates cryptographically signed tokens for hierarchical agent authorization.
    """
    
    def __init__(self, signing_service: SigningService):
        """
        Initialize token signer.
        
        Args:
            signing_service: SigningService for cryptographic operations
        """
        self.signing_service = signing_service
    
    def create_token(self, claims: TokenClaims, key_id: str,
                    algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> str:
        """
        Create a signed delegation token.
        
        Args:
            claims: Token claims
            key_id: Signing key identifier
            algorithm: Signature algorithm
            
        Returns:
            JWT token string
            
        Raises:
            TokenSigningError: If token creation fails
        """
        try:
            # Create JWT header
            header = {
                "alg": algorithm.value,
                "typ": "JWT",
                "kid": key_id,
            }
            
            # Encode header and payload
            header_b64 = self._base64url_encode(json.dumps(header).encode('utf-8'))
            payload_b64 = self._base64url_encode(json.dumps(claims.to_dict()).encode('utf-8'))
            
            # Create signing input
            signing_input = f"{header_b64}.{payload_b64}"
            
            # Sign
            signature_result = self.signing_service.sign(
                signing_input.encode('utf-8'),
                key_id,
                algorithm
            )
            
            # Encode signature
            signature_b64 = signature_result.signature
            
            # Construct JWT
            token = f"{signing_input}.{signature_b64}"
            
            return token
            
        except Exception as e:
            raise TokenSigningError(f"Failed to create token: {e}") from e
    
    def create_delegation_token(self, delegating_agent_id: str, delegated_agent_id: str,
                               spending_limit_value: str, spending_limit_currency: str,
                               allowed_operations: List[str], budget_category: str,
                               key_id: str, validity_hours: int = 24,
                               max_delegation_depth: int = 5,
                               parent_token_id: Optional[str] = None,
                               algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> str:
        """
        Create a delegation token with standard parameters.
        
        Args:
            delegating_agent_id: Agent creating the delegation
            delegated_agent_id: Agent receiving the delegation
            spending_limit_value: Spending limit amount
            spending_limit_currency: Currency code
            allowed_operations: List of allowed operations
            budget_category: Budget category
            key_id: Signing key identifier
            validity_hours: Token validity in hours
            max_delegation_depth: Maximum delegation chain depth
            parent_token_id: Parent token ID for hierarchical delegation
            algorithm: Signature algorithm
            
        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=validity_hours)).timestamp())
        
        # Generate unique token ID
        import uuid
        jti = f"tok_{uuid.uuid4().hex[:16]}"
        
        claims = TokenClaims(
            iss=delegating_agent_id,
            sub=delegated_agent_id,
            aud="any",
            exp=exp,
            iat=iat,
            jti=jti,
            spending_limit={
                "value": spending_limit_value,
                "currency": spending_limit_currency
            },
            allowed_operations=allowed_operations,
            max_delegation_depth=max_delegation_depth,
            budget_category=budget_category,
            parent_token_id=parent_token_id,
        )
        
        return self.create_token(claims, key_id, algorithm)
    
    def _base64url_encode(self, data: bytes) -> str:
        """Encode data as base64url (JWT standard)."""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


class TokenVerifier:
    """
    Verifies delegation tokens.
    
    Validates JWT signatures, expiration, and delegation constraints.
    """
    
    def __init__(self, verification_service: VerificationService):
        """
        Initialize token verifier.
        
        Args:
            verification_service: VerificationService for cryptographic operations
        """
        self.verification_service = verification_service
    
    def verify_token(self, token: str, expected_algorithm: Optional[SignatureAlgorithm] = None,
                    validate_expiration: bool = True) -> TokenClaims:
        """
        Verify a delegation token.
        
        Args:
            token: JWT token string
            expected_algorithm: Expected signature algorithm (None to accept any)
            validate_expiration: Whether to validate expiration time
            
        Returns:
            TokenClaims if valid
            
        Raises:
            TokenVerificationError: If token is invalid
            TokenExpiredError: If token has expired
        """
        try:
            # Parse JWT
            parts = token.split('.')
            if len(parts) != 3:
                raise TokenVerificationError("Invalid JWT format")
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Decode header and payload
            header = json.loads(self._base64url_decode(header_b64))
            payload = json.loads(self._base64url_decode(payload_b64))
            
            # Validate algorithm
            algorithm = SignatureAlgorithm(header["alg"])
            if expected_algorithm and algorithm != expected_algorithm:
                raise TokenVerificationError(
                    f"Algorithm mismatch: expected {expected_algorithm.value}, got {algorithm.value}"
                )
            
            # Get key ID
            key_id = header.get("kid")
            if not key_id:
                raise TokenVerificationError("Missing key ID in header")
            
            # Verify signature
            signing_input = f"{header_b64}.{payload_b64}"
            verification_result = self.verification_service.verify(
                signing_input.encode('utf-8'),
                signature_b64,
                key_id,
                algorithm
            )
            
            if not verification_result.is_valid:
                raise TokenVerificationError(
                    f"Signature verification failed: {verification_result.error_message}"
                )
            
            # Parse claims
            claims = TokenClaims.from_dict(payload)
            
            # Validate expiration
            if validate_expiration:
                now = int(datetime.now(timezone.utc).timestamp())
                if claims.exp < now:
                    raise TokenExpiredError(f"Token expired at {claims.exp}")
                if claims.nbf and claims.nbf > now:
                    raise TokenVerificationError(f"Token not yet valid (nbf: {claims.nbf})")
            
            return claims
            
        except TokenExpiredError:
            raise
        except TokenVerificationError:
            raise
        except Exception as e:
            raise TokenVerificationError(f"Token verification failed: {e}") from e
    
    def validate_spending_limit(self, claims: TokenClaims, requested_amount: Decimal,
                               requested_currency: str) -> bool:
        """
        Validate that requested amount is within spending limit.
        
        Args:
            claims: Token claims
            requested_amount: Requested spending amount
            requested_currency: Requested currency
            
        Returns:
            True if within limit, False otherwise
        """
        limit_value = Decimal(claims.spending_limit["value"])
        limit_currency = claims.spending_limit["currency"]
        
        # Currency must match
        if requested_currency != limit_currency:
            return False
        
        # Amount must be within limit
        return requested_amount <= limit_value
    
    def validate_operation(self, claims: TokenClaims, operation: str) -> bool:
        """
        Validate that operation is allowed.
        
        Args:
            claims: Token claims
            operation: Operation to validate
            
        Returns:
            True if allowed, False otherwise
        """
        return operation in claims.allowed_operations
    
    def validate_delegation_chain(self, tokens: List[str]) -> bool:
        """
        Validate a chain of delegation tokens.
        
        Args:
            tokens: List of tokens from parent to child
            
        Returns:
            True if chain is valid, False otherwise
        """
        if not tokens:
            return False
        
        # Verify each token
        claims_chain = []
        for token in tokens:
            try:
                claims = self.verify_token(token)
                claims_chain.append(claims)
            except (TokenVerificationError, TokenExpiredError):
                return False
        
        # Validate chain relationships
        for i in range(len(claims_chain) - 1):
            parent = claims_chain[i]
            child = claims_chain[i + 1]
            
            # Child's issuer must be parent's subject
            if child.iss != parent.sub:
                return False
            
            # Child's spending limit must not exceed parent's
            child_limit = Decimal(child.spending_limit["value"])
            parent_limit = Decimal(parent.spending_limit["value"])
            if child_limit > parent_limit:
                return False
            
            # Currency must match
            if child.spending_limit["currency"] != parent.spending_limit["currency"]:
                return False
            
            # Child's operations must be subset of parent's
            if not set(child.allowed_operations).issubset(set(parent.allowed_operations)):
                return False
        
        # Validate depth
        if len(claims_chain) > claims_chain[0].max_delegation_depth:
            return False
        
        return True
    
    def _base64url_decode(self, data: str) -> bytes:
        """Decode base64url data (JWT standard)."""
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
