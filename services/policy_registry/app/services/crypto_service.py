"""
Cryptographic service for Ed25519 signing and verification
"""

import base64
import hashlib
import json
from typing import Dict, Any, Tuple, List
import logging
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
import jwt

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
            encryption_algorithm=serialization.NoEncryption()
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        private_b64 = base64.b64encode(private_bytes).decode('utf-8')
        public_b64 = base64.b64encode(public_bytes).decode('utf-8')
        
        return public_b64, private_b64

    @staticmethod
    def sign_policy_content(
        content: Dict[str, Any], 
        private_key_b64: str
    ) -> str:
        """
        Sign policy content with Ed25519 private key
        
        Args:
            content: Policy content dictionary
            private_key_b64: Base64 encoded private key
            
        Returns:
            Base64 encoded signature
        """
        # Create deterministic content hash
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        content_bytes = content_str.encode('utf-8')
        
        # Load private key
        private_bytes = base64.b64decode(private_key_b64)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        
        # Sign content
        signature = private_key.sign(content_bytes)
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return signature_b64

    @staticmethod
    def verify_policy_signature(
        content: Dict[str, Any],
        signature_b64: str,
        public_key_b64: str
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
            content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
            content_bytes = content_str.encode('utf-8')
            
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
    def generate_fingerprint(public_key_b64: str) -> str:
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
        public_key_b64: str
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
        fingerprint = CryptoService.generate_fingerprint(public_key_b64)
        
        return PolicySignature(
            policy_id=policy_id,
            version=version,
            public_key=public_key_b64,
            signature=signature_b64,
            key_fingerprint=fingerprint
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
        expected_fingerprint = CryptoService.generate_fingerprint(signature.public_key)
        return signature.key_fingerprint == expected_fingerprint
