"""
Token signing and verification for delegation tokens.

Implements JWT-based delegation token creation and validation.
"""

import json
import base64
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from decimal import Decimal
from collections import defaultdict

from .signing import SigningService, VerificationService, SignatureAlgorithm


from ase.core.serialization import SerializableModel
from pydantic import Field


class TokenClaims(SerializableModel):
    """Standard and ASE-specific JWT claims for delegation tokens."""
    # Standard JWT claims
    iss: str  # Issuer (delegating agent ID)
    sub: str  # Subject (delegated agent ID)
    aud: str  # Audience (target service or 'any')
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str  # Unique token ID
    
    # ASE-specific claims
    allowed_operations: List[str] = Field(..., alias="allowedOperations")
    
    # Optional claims
    nbf: Optional[int] = None  # Not before timestamp
    
    # Note: SerializableModel already provides to_dict(), from_dict(), to_json(), from_json()



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


class RateLimitExceededError(TokenError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class SimpleRateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.
    
    Enforces rate limits per agent ID.
    """
    
    def __init__(self, requests_per_minute: int = 100):
        self.rate = requests_per_minute
        self.window = 60.0  # seconds
        # Stores [count, start_time] for each key
        self.buckets: Dict[str, List[float]] = defaultdict(lambda: [0, time.time()])
        
    def check_limit(self, key: str) -> bool:
        """
        Check if request is allowed for key.
        Returns True if allowed, or False if limit exceeded.
        """
        now = time.time()
        bucket = self.buckets[key]
        
        # Reset bucket if window passed
        if now - bucket[1] > self.window:
            bucket[0] = 0
            bucket[1] = now
            
        if bucket[0] < self.rate:
            bucket[0] += 1
            return True
        
        return False

    def get_retry_after(self, key: str) -> int:
        """Get seconds until limit reset."""
        now = time.time()
        bucket = self.buckets[key]
        remaining = self.window - (now - bucket[1])
        return max(1, int(remaining))


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
                               allowed_operations: List[str],
                               key_id: str, validity_hours: int = 24,
                               algorithm: SignatureAlgorithm = SignatureAlgorithm.ES256) -> str:
        """
        Create a delegation token with standard parameters.
        
        Args:
            delegating_agent_id: Agent creating the delegation
            delegated_agent_id: Agent receiving the delegation
            allowed_operations: List of allowed operations
            key_id: Signing key identifier
            validity_hours: Token validity in hours
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
            allowed_operations=allowed_operations,
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
        self.rate_limiter = SimpleRateLimiter(requests_per_minute=100)
    
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
            RateLimitExceededError: If rate limit is exceeded
        """
        try:
            # Parse JWT preliminary to get issuer for rate limiting (unsafe parse)
            parts = token.split('.')
            if len(parts) != 3:
                raise TokenVerificationError("Invalid JWT format")
            
            payload_b64 = parts[1]
            try:
                # We need to decode payload to get issuer for rate limiting
                # NOTE: This is done BEFORE signature verification, so we must be careful.
                # Rate limiting is based on the claimed issuer.
                payload_json = self._base64url_decode(payload_b64)
                payload = json.loads(payload_json)
                issuer = payload.get("iss", "unknown")
                
                # Check rate limit
                if not self.rate_limiter.check_limit(issuer):
                    retry_after = self.rate_limiter.get_retry_after(issuer)
                    raise RateLimitExceededError(
                        f"Rate limit exceeded for agent {issuer}",
                        retry_after=retry_after
                    )
            except (json.JSONDecodeError, UnicodeDecodeError):
                 # If we can't parse payload, strict validation below will catch it.
                 # We can fall back to a global rate limit key or just proceed to fail validation.
                 pass

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
        except RateLimitExceededError:
            raise
        except Exception as e:
            raise TokenVerificationError(f"Token verification failed: {e}") from e
    
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
            tokens: List of tokens from source to target
            
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
            source = claims_chain[i]
            target = claims_chain[i + 1]
            
            # Target's issuer must be source's subject
            if target.iss != source.sub:
                return False
            
            # Target's operations must be subset of source's
            if source.allowed_operations and not set(target.allowed_operations).issubset(set(source.allowed_operations)):
                return False
                
        return True