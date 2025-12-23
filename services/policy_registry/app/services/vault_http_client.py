"""
ACGS-2 Vault Crypto Service - HTTP Client Layer
Constitutional Hash: cdd01ef066bc6cf2

HTTP communication layer for Vault API operations.
Supports httpx, aiohttp, and hvac client libraries.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .vault_models import VaultConfig, CONSTITUTIONAL_HASH

# HTTP client - prefer httpx for async, fallback to aiohttp
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Optional hvac library for Vault SDK operations
try:
    import hvac
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False

logger = logging.getLogger(__name__)


class VaultHttpClient:
    """
    HTTP client wrapper for Vault API operations.

    Supports multiple HTTP libraries with fallback:
    1. hvac (Vault SDK) - preferred for full Vault features
    2. httpx - async HTTP client
    3. aiohttp - fallback async client
    """

    def __init__(self, config: VaultConfig):
        """
        Initialize Vault HTTP client.

        Args:
            config: Vault connection configuration
        """
        self.config = config
        self._hvac_client: Optional[Any] = None
        self._http_client: Optional[Any] = None
        self._aiohttp_session: Optional[Any] = None
        self._initialized = False
        self._vault_available = False

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize HTTP client connection to Vault.

        Returns:
            Dict with initialization status
        """
        result = {
            "success": False,
            "vault_available": False,
            "connection_method": None,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Try hvac library first
            if HVAC_AVAILABLE and self.config.token:
                self._hvac_client = hvac.Client(
                    url=self.config.address,
                    token=self.config.token,
                    namespace=self.config.namespace,
                    verify=self.config.verify_tls if self.config.verify_tls else self.config.ca_cert,
                )
                if self._hvac_client.is_authenticated():
                    self._vault_available = True
                    result["connection_method"] = "hvac"
                    logger.info("Connected to Vault via hvac library")

            # Fallback to httpx
            if not self._vault_available and HTTPX_AVAILABLE:
                self._http_client = httpx.AsyncClient(
                    base_url=self.config.address,
                    timeout=self.config.timeout,
                    verify=self.config.verify_tls,
                )
                # Test connection
                try:
                    health = await self._http_health_check()
                    if health.get("initialized"):
                        self._vault_available = True
                        result["connection_method"] = "httpx"
                        logger.info("Connected to Vault via httpx")
                except Exception as e:
                    logger.warning(f"httpx connection failed: {e}")

            # Fallback to aiohttp
            if not self._vault_available and AIOHTTP_AVAILABLE:
                try:
                    health = await self._aiohttp_health_check()
                    if health.get("initialized"):
                        self._vault_available = True
                        result["connection_method"] = "aiohttp"
                        logger.info("Connected to Vault via aiohttp")
                except Exception as e:
                    logger.warning(f"aiohttp connection failed: {e}")

            result["vault_available"] = self._vault_available
            result["success"] = self._vault_available
            self._initialized = True

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Vault initialization failed: {e}")

        return result

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to Vault.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path
            data: Request body data
            headers: Additional headers

        Returns:
            Response data
        """
        if self._http_client:
            return await self._httpx_request(method, path, data, headers)
        elif AIOHTTP_AVAILABLE:
            return await self._aiohttp_request(method, path, data, headers)
        else:
            raise RuntimeError("No HTTP client available")

    async def _httpx_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make request using httpx client."""
        req_headers = {"X-Vault-Token": self.config.token or ""}
        if self.config.namespace:
            req_headers["X-Vault-Namespace"] = self.config.namespace
        if headers:
            req_headers.update(headers)

        response = await self._http_client.request(
            method=method,
            url=path,
            json=data,
            headers=req_headers,
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    async def _aiohttp_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make request using aiohttp client."""
        req_headers = {"X-Vault-Token": self.config.token or ""}
        if self.config.namespace:
            req_headers["X-Vault-Namespace"] = self.config.namespace
        if headers:
            req_headers.update(headers)

        url = f"{self.config.address}{path}"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                json=data,
                headers=req_headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as response:
                response.raise_for_status()
                return await response.json() if response.content_length else {}

    async def _http_health_check(self) -> Dict[str, Any]:
        """Health check using httpx."""
        response = await self._http_client.get("/v1/sys/health")
        return response.json()

    async def _aiohttp_health_check(self) -> Dict[str, Any]:
        """Health check using aiohttp."""
        url = f"{self.config.address}/v1/sys/health"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Vault health status.

        Returns:
            Health status information
        """
        result = {
            "vault_available": self._vault_available,
            "connection_method": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            if self._hvac_client:
                health = self._hvac_client.sys.read_health_status(method="GET")
                result["connection_method"] = "hvac"
                result["health"] = {
                    "initialized": health.get("initialized"),
                    "sealed": health.get("sealed"),
                    "version": health.get("version"),
                }
            elif self._http_client:
                result["connection_method"] = "httpx"
                result["health"] = await self._http_health_check()
            elif AIOHTTP_AVAILABLE:
                result["connection_method"] = "aiohttp"
                result["health"] = await self._aiohttp_health_check()
        except Exception as e:
            result["error"] = str(e)

        return result

    @property
    def hvac_client(self) -> Optional[Any]:
        """Get hvac client if available."""
        return self._hvac_client

    @property
    def is_available(self) -> bool:
        """Check if Vault is available."""
        return self._vault_available

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._aiohttp_session:
            await self._aiohttp_session.close()
            self._aiohttp_session = None

    async def __aenter__(self) -> "VaultHttpClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


__all__ = [
    "VaultHttpClient",
    "HTTPX_AVAILABLE",
    "AIOHTTP_AVAILABLE",
    "HVAC_AVAILABLE",
]
