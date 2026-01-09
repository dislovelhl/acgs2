"""
ACGS-2 Vault Crypto Service - Transit Engine Operations
Constitutional Hash: cdd01ef066bc6cf2

Transit secrets engine operations for signing, verification,
encryption, and decryption using HashiCorp Vault.
"""

# ruff: noqa: E402
import base64
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Protocol

# Add src/core to path for shared modules
core_path = Path(__file__).parent.parent.parent.parent.parent
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from shared.types import JSONDict

logger = logging.getLogger(__name__)


class VaultHttpClient(Protocol):
    """Protocol for Vault HTTP client."""

    async def request(self, method: str, path: str, data: Optional[JSONDict] = None) -> JSONDict:
        """Make HTTP request to Vault API."""
        ...


class VaultTransitOperations:
    """
    Vault Transit engine operations wrapper.

    Provides high-level methods for cryptographic operations
    using the Vault Transit secrets engine.
    """

    def __init__(self, http_client: VaultHttpClient, transit_mount: str = "transit"):
        """
        Initialize Transit operations.

        Args:
            http_client: VaultHttpClient instance for API calls
            transit_mount: Mount path for Transit engine
        """
        self._http_client = http_client
        self._transit_mount = transit_mount

    async def create_key(
        self,
        key_name: str,
        key_type: str,
        exportable: bool = False,
        allow_plaintext_backup: bool = False,
    ) -> None:
        """
        Create a key in Transit engine.

        Args:
            key_name: Name for the key
            key_type: Vault key type (ed25519, ecdsa-p256, etc.)
            exportable: Whether key can be exported
            allow_plaintext_backup: Allow plaintext backup
        """
        path = f"/v1/{self._transit_mount}/keys/{key_name}"
        data = {
            "type": key_type,
            "exportable": exportable,
            "allow_plaintext_backup": allow_plaintext_backup,
        }
        await self._http_client.request("POST", path, data=data)

    async def sign(
        self,
        key_name: str,
        data: bytes,
        hash_algorithm: str = "sha2-256",
        prehashed: bool = False,
    ) -> str:
        """
        Sign data using Transit engine.

        Args:
            key_name: Name of the signing key
            data: Data to sign
            hash_algorithm: Hash algorithm (sha2-256, sha2-384, sha2-512)
            prehashed: Whether data is already hashed

        Returns:
            Base64-encoded signature
        """
        path = f"/v1/{self._transit_mount}/sign/{key_name}"

        payload = {
            "input": base64.b64encode(data).decode(),
            "hash_algorithm": hash_algorithm,
            "prehashed": prehashed,
        }

        response = await self._http_client.request("POST", path, data=payload)

        # Vault returns signature as vault:v1:base64...
        signature = response.get("data", {}).get("signature", "")

        # Extract just the base64 part for compatibility
        if signature.startswith("vault:"):
            parts = signature.split(":")
            if len(parts) >= 3:
                return parts[2]
        return signature

    async def verify(
        self,
        key_name: str,
        data: bytes,
        signature: str,
        hash_algorithm: str = "sha2-256",
        prehashed: bool = False,
    ) -> bool:
        """
        Verify signature using Transit engine.

        Args:
            key_name: Name of the signing key
            data: Original data
            signature: Signature to verify
            hash_algorithm: Hash algorithm used for signing
            prehashed: Whether data is already hashed

        Returns:
            True if signature is valid
        """
        path = f"/v1/{self._transit_mount}/verify/{key_name}"

        # Add vault prefix if not present
        if not signature.startswith("vault:"):
            signature = f"vault:v1:{signature}"

        payload = {
            "input": base64.b64encode(data).decode(),
            "signature": signature,
            "hash_algorithm": hash_algorithm,
            "prehashed": prehashed,
        }

        response = await self._http_client.request("POST", path, data=payload)
        return response.get("data", {}).get("valid", False)

    async def encrypt(
        self,
        key_name: str,
        plaintext: bytes,
        context: Optional[bytes] = None,
    ) -> str:
        """
        Encrypt data using Transit engine.

        Args:
            key_name: Name of the encryption key
            plaintext: Data to encrypt
            context: Optional context for key derivation

        Returns:
            Vault ciphertext string (vault:v1:...)
        """
        path = f"/v1/{self._transit_mount}/encrypt/{key_name}"

        payload = {"plaintext": base64.b64encode(plaintext).decode()}
        if context:
            payload["context"] = base64.b64encode(context).decode()

        response = await self._http_client.request("POST", path, data=payload)
        return response.get("data", {}).get("ciphertext", "")

    async def decrypt(
        self,
        key_name: str,
        ciphertext: str,
        context: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data using Transit engine.

        Args:
            key_name: Name of the encryption key
            ciphertext: Vault ciphertext string
            context: Optional context for key derivation

        Returns:
            Decrypted plaintext bytes
        """
        path = f"/v1/{self._transit_mount}/decrypt/{key_name}"

        payload = {"ciphertext": ciphertext}
        if context:
            payload["context"] = base64.b64encode(context).decode()

        response = await self._http_client.request("POST", path, data=payload)
        plaintext_b64 = response.get("data", {}).get("plaintext", "")
        return base64.b64decode(plaintext_b64)

    async def rotate_key(self, key_name: str) -> None:
        """
        Rotate key in Transit engine.

        Args:
            key_name: Name of the key to rotate
        """
        path = f"/v1/{self._transit_mount}/keys/{key_name}/rotate"
        await self._http_client.request("POST", path)
        logger.info(f"Rotated Transit key: {key_name}")

    async def get_public_key(self, key_name: str) -> str:
        """
        Get public key from Transit engine.

        Args:
            key_name: Name of the key

        Returns:
            Base64-encoded public key
        """
        path = f"/v1/{self._transit_mount}/keys/{key_name}"
        response = await self._http_client.request("GET", path)

        keys = response.get("data", {}).get("keys", {})
        latest_version = response.get("data", {}).get("latest_version", 1)
        key_data = keys.get(str(latest_version), {})

        # Return public key in base64 format
        public_key = key_data.get("public_key", "")
        if public_key and not public_key.startswith("-----"):
            return public_key

        # If PEM format, extract just the key
        if public_key.startswith("-----BEGIN"):
            match = re.search(r"-----BEGIN .+-----\n(.+)\n-----END", public_key, re.DOTALL)
            if match:
                return match.group(1).replace("\n", "")

        return public_key

    async def get_key_info(self, key_name: str) -> JSONDict:
        """
        Get key info from Transit engine.

        Args:
            key_name: Name of the key

        Returns:
            Key information dictionary
        """
        path = f"/v1/{self._transit_mount}/keys/{key_name}"
        response = await self._http_client.request("GET", path)
        return response.get("data", {})


__all__ = ["VaultTransitOperations"]
