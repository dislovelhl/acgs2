"""Constitutional Hash: cdd01ef066bc6cf2
Cryptographic service for Ed25519 signing and verification
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..models import PolicySignature

logger = logging.getLogger(__name__)


class CryptoService:
    """Service for cryptographic operations using Ed25519"""

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """
        Generate a new Ed25519 key pair

        Returns:
            Tuple of (public_key_b64, private_key_b64)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        private_b64 = base64.b64encode(private_bytes).decode("utf-8")
        public_b64 = base64.b64encode(public_bytes).decode("utf-8")

        return public_b64, private_b64

    @staticmethod
    def sign_policy_content(content: Dict[str, Any], private_key_b64: str) -> str:
        """
        Sign policy content with Ed25519 private key

        Args:
            content: Policy content dictionary
            private_key_b64: Base64 encoded private key

        Returns:
            Base64 encoded signature
        """
        # Create deterministic content hash
        content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
        content_bytes = content_str.encode("utf-8")

        # Load private key
        private_bytes = base64.b64decode(private_key_b64)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)

        # Sign content
        signature = private_key.sign(content_bytes)
        signature_b64 = base64.b64encode(signature).decode("utf-8")

        return signature_b64

    @staticmethod
    def verify_policy_signature(
        content: Dict[str, Any], signature_b64: str, public_key_b64: str
    ) -> bool:
        """
        Verify policy signature with Ed25519 public key

        Args:
            content: Policy content dictionary
            signature_b64: Base64 encoded signature
            public_key_b64: Base64 encoded public key

        Returns:
            True if signature is valid
        """
        try:
            # Create deterministic content hash
            content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
            content_bytes = content_str.encode("utf-8")

            # Load public key
            public_bytes = base64.b64decode(public_key_b64)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)

            # Load signature
            signature_bytes = base64.b64decode(signature_b64)

            # Verify signature
            public_key.verify(signature_bytes, content_bytes)
            return True

        except (InvalidSignature, ValueError, Exception) as e:
            logger.warning(f"Signature verification failed: {e}")
            return False

    @staticmethod
    def generate_public_key_fingerprint(public_key_b64: str) -> str:
        """
        Generate SHA256 fingerprint of public key

        Args:
            public_key_b64: Base64 encoded public key

        Returns:
            Hex string fingerprint
        """
        public_bytes = base64.b64decode(public_key_b64)
        fingerprint = hashlib.sha256(public_bytes).hexdigest()
        return fingerprint

    @staticmethod
    def create_policy_signature(
        policy_id: str,
        version: str,
        content: Dict[str, Any],
        private_key_b64: str,
        public_key_b64: str,
    ) -> PolicySignature:
        """
        Create a policy signature object

        Args:
            policy_id: Policy identifier
            version: Policy version
            content: Policy content
            private_key_b64: Private key for signing
            public_key_b64: Public key for verification

        Returns:
            PolicySignature object
        """
        signature_b64 = CryptoService.sign_policy_content(content, private_key_b64)
        fingerprint = CryptoService.generate_public_key_fingerprint(public_key_b64)
        logger.info(f"Created policy signature with fingerprint: {fingerprint}")

        return PolicySignature(
            policy_id=policy_id,
            version=version,
            public_key=public_key_b64,
            signature=signature_b64,
            key_fingerprint=fingerprint,
        )

    @staticmethod
    def validate_signature_integrity(signature: PolicySignature) -> bool:
        """
        Validate signature object integrity

        Args:
            signature: PolicySignature object

        Returns:
            True if signature data is consistent
        """
        # Verify fingerprint matches public key
        expected_fingerprint = CryptoService.generate_public_key_fingerprint(signature.public_key)
        logger.info(
            f"Validating signature integrity for public key: {signature.public_key[:20]}..."
        )
        return signature.key_fingerprint == expected_fingerprint

    @staticmethod
    def issue_agent_token(
        agent_id: str,
        tenant_id: str,
        capabilities: List[str],
        private_key_b64: str,
        ttl_hours: int = 24,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Issue a SPIFFE-compatible SVID (JWT) for an agent using Ed25519.

        Args:
            agent_id: Unique agent identifier
            tenant_id: Tenant identifier
            capabilities: List of agent capabilities
            private_key_b64: Base64-encoded Ed25519 private key
            ttl_hours: Token time-to-live in hours
            extra_claims: Optional additional claims to include in the token

        Returns:
            JWT token string
        """
        # Load private key
        private_bytes = base64.b64decode(private_key_b64)
        # Handle both raw bytes and PEM if necessary, but here we assume raw from generate_keypair
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)

        # SPIFFE format: spiffe://acgs2/tenant/{tenant_id}/agent/{agent_id}
        sub = f"spiffe://acgs2/tenant/{tenant_id}/agent/{agent_id}"

        now = datetime.now(timezone.utc)
        payload = {
            "iss": "acgs2-identity-service",
            "sub": sub,
            "aud": ["acgs2-agent-bus", "acgs2-deliberation-layer"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "capabilities": capabilities,
            "constitutional_hash": "cdd01ef066bc6cf2",
        }

        # Add extra claims if provided
        if extra_claims:
            payload.update(extra_claims)

        # Use EdDSA (Ed25519) algorithm
        token = jwt.encode(payload, private_key, algorithm="EdDSA")
        return token

    @staticmethod
    def verify_agent_token(token: str, public_key_b64: str) -> Dict[str, Any]:
        """
        Verify an agent token and return its payload.
        """
        # Load public key
        public_bytes = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["EdDSA"],
                audience=["acgs2-agent-bus", "acgs2-deliberation-layer"],
            )
            return payload
        except jwt.ExpiredSignatureError as e:
            raise ValueError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}") from e
        except Exception as e:
            raise ValueError(f"Token verification failed: {e}") from e
