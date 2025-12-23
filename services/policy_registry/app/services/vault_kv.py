"""
ACGS-2 Vault Crypto Service - KV Secrets Engine Operations
Constitutional Hash: cdd01ef066bc6cf2

Key-Value secrets engine operations for secure secret storage
and retrieval using HashiCorp Vault.
"""

import logging
from typing import Any, Dict, Optional

from .vault_models import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class VaultKVOperations:
    """
    Vault KV secrets engine operations wrapper.

    Provides high-level methods for secret storage operations
    using the Vault KV secrets engine (v1 and v2).
    """

    def __init__(
        self,
        http_client: Any,
        kv_mount: str = "secret",
        kv_version: int = 2,
    ):
        """
        Initialize KV operations.

        Args:
            http_client: VaultHttpClient instance for API calls
            kv_mount: Mount path for KV engine
            kv_version: KV engine version (1 or 2)
        """
        self._http_client = http_client
        self._kv_mount = kv_mount
        self._kv_version = kv_version

    async def put(
        self,
        path: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Store a secret in KV engine.

        Args:
            path: Secret path
            data: Secret data to store
            metadata: Optional metadata
        """
        if self._kv_version == 2:
            api_path = f"/v1/{self._kv_mount}/data/{path}"
            payload: Dict[str, Any] = {"data": data}
            if metadata:
                payload["options"] = {"cas": 0}  # Check-and-set
        else:
            api_path = f"/v1/{self._kv_mount}/{path}"
            payload = data

        await self._http_client.request("POST", api_path, data=payload)
        logger.debug(f"Stored secret at: {path}")

    async def get(
        self,
        path: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get a secret from KV engine.

        Args:
            path: Secret path
            version: Specific version (None for latest, KV v2 only)

        Returns:
            Secret data dictionary
        """
        if self._kv_version == 2:
            api_path = f"/v1/{self._kv_mount}/data/{path}"
            if version:
                api_path += f"?version={version}"
        else:
            api_path = f"/v1/{self._kv_mount}/{path}"

        response = await self._http_client.request("GET", api_path)

        if self._kv_version == 2:
            return response.get("data", {}).get("data", {})
        return response.get("data", {})

    async def delete(self, path: str) -> None:
        """
        Delete a secret from KV engine.

        Args:
            path: Secret path
        """
        if self._kv_version == 2:
            api_path = f"/v1/{self._kv_mount}/data/{path}"
        else:
            api_path = f"/v1/{self._kv_mount}/{path}"

        await self._http_client.request("DELETE", api_path)
        logger.debug(f"Deleted secret at: {path}")

    async def list_secrets(self, path: str = "") -> Dict[str, Any]:
        """
        List secrets at a path in KV engine.

        Args:
            path: Path to list (empty for root)

        Returns:
            Dictionary with keys list
        """
        if self._kv_version == 2:
            api_path = f"/v1/{self._kv_mount}/metadata/{path}"
        else:
            api_path = f"/v1/{self._kv_mount}/{path}"

        # Use LIST method via query parameter
        api_path += "?list=true"
        response = await self._http_client.request("GET", api_path)
        return response.get("data", {})

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get secret metadata (KV v2 only).

        Args:
            path: Secret path

        Returns:
            Metadata dictionary
        """
        if self._kv_version != 2:
            raise RuntimeError("Metadata operations require KV v2")

        api_path = f"/v1/{self._kv_mount}/metadata/{path}"
        response = await self._http_client.request("GET", api_path)
        return response.get("data", {})

    async def delete_versions(
        self,
        path: str,
        versions: list[int],
    ) -> None:
        """
        Delete specific versions of a secret (KV v2 only).

        Args:
            path: Secret path
            versions: List of version numbers to delete
        """
        if self._kv_version != 2:
            raise RuntimeError("Version operations require KV v2")

        api_path = f"/v1/{self._kv_mount}/delete/{path}"
        await self._http_client.request("POST", api_path, data={"versions": versions})
        logger.debug(f"Deleted versions {versions} at: {path}")

    async def undelete_versions(
        self,
        path: str,
        versions: list[int],
    ) -> None:
        """
        Undelete specific versions of a secret (KV v2 only).

        Args:
            path: Secret path
            versions: List of version numbers to undelete
        """
        if self._kv_version != 2:
            raise RuntimeError("Version operations require KV v2")

        api_path = f"/v1/{self._kv_mount}/undelete/{path}"
        await self._http_client.request("POST", api_path, data={"versions": versions})
        logger.debug(f"Undeleted versions {versions} at: {path}")

    async def destroy_versions(
        self,
        path: str,
        versions: list[int],
    ) -> None:
        """
        Permanently destroy specific versions of a secret (KV v2 only).

        Args:
            path: Secret path
            versions: List of version numbers to destroy
        """
        if self._kv_version != 2:
            raise RuntimeError("Version operations require KV v2")

        api_path = f"/v1/{self._kv_mount}/destroy/{path}"
        await self._http_client.request("POST", api_path, data={"versions": versions})
        logger.warning(f"Permanently destroyed versions {versions} at: {path}")


__all__ = ["VaultKVOperations"]
