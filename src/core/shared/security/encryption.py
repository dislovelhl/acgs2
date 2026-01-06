"""
ACGS-2 Audit Data Encryption
Constitutional Hash: cdd01ef066bc6cf2

Provides envelope encryption for sensitive audit payloads.
"""

import base64
import json
import logging
import os
from typing import Any, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# Master key for envelope encryption (should be from KMS/Vault in production)
MASTER_KEY = os.environ.get("ACGS2_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode())


class EncryptionManager:
    """Manager for audit data encryption."""

    @staticmethod
    def encrypt_payload(payload: Dict[str, Any]) -> str:
        """
        Encrypt a payload using envelope encryption (AES-GCM).
        Returns a base64 encoded string containing IV + Tag + Ciphertext.
        """
        try:
            # Generate a random data key
            data_key = os.urandom(32)
            aesgcm = AESGCM(data_key)
            nonce = os.urandom(12)

            payload_bytes = json.dumps(payload).encode("utf-8")
            ciphertext = aesgcm.encrypt(nonce, payload_bytes, None)

            # Encrypt the data key with the master key (simplified envelope)
            master_aesgcm = AESGCM(base64.b64decode(MASTER_KEY))
            encrypted_key = master_aesgcm.encrypt(nonce, data_key, None)

            # Combine everything: nonce (12) + encrypted_key (32 + tag) + ciphertext
            combined = nonce + encrypted_key + ciphertext
            return base64.b64encode(combined).decode("utf-8")
        except Exception as e:
            logger.error(f"Payload encryption failed: {e}")
            raise RuntimeError("Encryption failure")

    @staticmethod
    def decrypt_payload(encrypted_str: str) -> Dict[str, Any]:
        """Decrypt an encrypted payload."""
        try:
            combined = base64.b64decode(encrypted_str)
            nonce = combined[:12]
            # encrypted_key is 32 bytes + 16 bytes tag = 48 bytes
            encrypted_key = combined[12:60]
            ciphertext = combined[60:]

            # Decrypt data key
            master_aesgcm = AESGCM(base64.b64decode(MASTER_KEY))
            data_key = master_aesgcm.decrypt(nonce, encrypted_key, None)

            # Decrypt payload
            aesgcm = AESGCM(data_key)
            payload_bytes = aesgcm.decrypt(nonce, ciphertext, None)

            return json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Payload decryption failed: {e}")
            raise ValueError("Decryption failure")


__all__ = ["EncryptionManager"]
