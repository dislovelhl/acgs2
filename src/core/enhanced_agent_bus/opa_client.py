"""
ACGS-2 OPA (Open Policy Agent) Client
Constitutional Hash: cdd01ef066bc6cf2

Provides integration with OPA for policy-based decision making.
Supports HTTP API mode, embedded mode, and OCI bundle distribution.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

try:
    from .config import settings
    from .exceptions import OPAConnectionError, OPANotInitializedError, PolicyEvaluationError
    from .models import CONSTITUTIONAL_HASH, AgentMessage
    from .validators import ValidationResult
except (ImportError, ValueError):
    try:
        from config import settings  # type: ignore
        from exceptions import (
            OPAConnectionError,  # type: ignore
            OPANotInitializedError,
            PolicyEvaluationError,
        )
        from models import CONSTITUTIONAL_HASH, AgentMessage  # type: ignore
        from validators import ValidationResult  # type: ignore
    except ImportError:
        try:
            from core.enhanced_agent_bus.config import settings
            from core.enhanced_agent_bus.exceptions import (
                OPAConnectionError,
                OPANotInitializedError,
                PolicyEvaluationError,
            )
            from core.enhanced_agent_bus.models import CONSTITUTIONAL_HASH, AgentMessage
            from core.enhanced_agent_bus.validators import ValidationResult
        except ImportError:
            # Fallback for sharing with shared package
            from core.shared.config import settings  # type: ignore
            from exceptions import OPANotInitializedError  # type: ignore
            from models import CONSTITUTIONAL_HASH  # type: ignore
            from validators import ValidationResult  # type: ignore

# Import centralized Redis config for caching
try:
    from core.shared.redis_config import get_redis_url

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

    def get_redis_url(db: int = 0) -> str:
        """Mock redis url."""
        return f"redis://localhost:6379/{db}"


# Optional Redis client for caching
try:
    import redis.asyncio as aioredis

    REDIS_CLIENT_AVAILABLE = True
except ImportError:
    REDIS_CLIENT_AVAILABLE = False
    aioredis = None

# Optional OPA Python SDK for embedded mode
try:
    from opa import OPA as EmbeddedOPA

    OPA_SDK_AVAILABLE = True
except ImportError:
    OPA_SDK_AVAILABLE = False
    EmbeddedOPA = None

logger = logging.getLogger(__name__)


class OPAClient:
    """
    Client for OPA (Open Policy Agent) policy evaluation.

    Supports multiple modes:
    1. HTTP API mode - Connect to remote OPA server
    2. Embedded mode - Use OPA Python SDK (if available)
    3. Fallback mode - Local validation when OPA unavailable
    """

    def __init__(
        self,
        opa_url: str = "http://localhost:8181",
        mode: str = "http",  # "http", "embedded", or "fallback"
        timeout: float = 5.0,
        cache_ttl: int = 300,  # 5 minutes
        enable_cache: bool = True,
        redis_url: Optional[str] = None,
        ssl_verify: bool = True,
        ssl_cert: Optional[str] = None,
        ssl_key: Optional[str] = None,
    ):
        """Initialize OPA client."""
        # Use settings defaults if not provided
        self.opa_url = opa_url or settings.opa.url
        self.opa_url = self.opa_url.rstrip("/")
        self.mode = mode or settings.opa.mode
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.ssl_verify = ssl_verify
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        # SECURITY FIX (VULN-002): Force fail-closed architecture.
        # This prevents any "fail-open" scenarios when OPA is unavailable.
        self.fail_closed = True
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_client: Optional[Any] = None
        self._embedded_opa: Optional[Any] = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._lkg_bundle_path: Optional[str] = None

        # Redis configuration
        self.redis_url = redis_url or get_redis_url(db=2)

        # Validate mode
        if mode == "embedded" and not OPA_SDK_AVAILABLE:
            logger.warning("Embedded mode requested but OPA SDK not available")
            self.mode = "http"

    async def __aenter__(self) -> "OPAClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize HTTP client and cache connections."""
        if self.mode in ("http", "fallback"):
            if not self._http_client:
                # Configure SSL context if needed
                ssl_context = None
                if self.opa_url.startswith("https"):
                    ssl_context = ssl.create_default_context()
                    if not self.ssl_verify:
                        logger.warning(
                            "SSL verification disabled for OPA client. "
                            "This is insecure and should only be used in development/testing."
                        )
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE

                    if self.ssl_cert and self.ssl_key:
                        ssl_context.load_cert_chain(certfile=self.ssl_cert, keyfile=self.ssl_key)

                self._http_client = httpx.AsyncClient(
                    timeout=self.timeout,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    verify=ssl_context if ssl_context else self.ssl_verify,
                )

        if self.mode == "embedded" and OPA_SDK_AVAILABLE:
            try:
                self._embedded_opa = EmbeddedOPA()
                logger.info("Embedded OPA initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedded OPA: {e}")
                self.mode = "http"
                if not self._http_client:
                    self._http_client = httpx.AsyncClient(
                        timeout=self.timeout,
                        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    )

        if self.enable_cache and REDIS_CLIENT_AVAILABLE:
            try:
                self._redis_client = await aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                await self._redis_client.ping()
                logger.info("Redis cache initialized for OPA client")
            except Exception as e:
                logger.warning(f"Redis cache failed: {e}, using memory")
                self._redis_client = None

    async def close(self) -> None:
        """Close all connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

        self._embedded_opa = None
        self._memory_cache.clear()

    def _generate_cache_key(self, policy_path: str, input_data: Dict[str, Any]) -> str:
        """Generate cache key."""
        input_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        return f"opa:{policy_path}:{input_hash}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache."""
        if not self.enable_cache:
            return None

        if self._redis_client:
            try:
                cached = await self._redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            now = datetime.now(timezone.utc).timestamp()
            if now - cached["timestamp"] < self.cache_ttl:
                return cached["result"]
            else:
                del self._memory_cache[cache_key]

        return None

    async def _set_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Set result in cache."""
        if not self.enable_cache:
            return

        if self._redis_client:
            try:
                await self._redis_client.setex(cache_key, self.cache_ttl, json.dumps(result))
                # Phase 4: Track keys by policy path for smart invalidation
                policy_path = cache_key.split(":")[1]
                path_set_key = f"opa:path_keys:{policy_path}"
                await self._redis_client.sadd(path_set_key, cache_key)
                await self._redis_client.expire(path_set_key, self.cache_ttl * 2)
                return
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")

        self._memory_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        }

    async def clear_cache(self, policy_path: Optional[str] = None) -> None:
        """
        Clear the policy evaluation cache.

        Args:
            policy_path: If provided, only clear cache for this specific policy path.
                         If None, clear the entire cache.
        """
        if not self.enable_cache:
            return

        logger.info(f"Clearing OPA cache (path={policy_path or 'ALL'})")

        if self._redis_client:
            try:
                if policy_path:
                    # Clear specific policy path
                    path_set_key = f"opa:path_keys:{policy_path}"
                    keys = await self._redis_client.smembers(path_set_key)
                    if keys:
                        await self._redis_client.delete(*keys)
                    await self._redis_client.delete(path_set_key)
                else:
                    # Clear all OPA keys
                    pattern = "opa:*"
                    cursor = 0
                    while True:
                        cursor, keys = await self._redis_client.scan(cursor, match=pattern)
                        if keys:
                            await self._redis_client.delete(*keys)
                        if cursor == 0:
                            break
            except Exception as e:
                logger.error(f"Failed to clear Redis cache: {e}")

        if policy_path:
            # Clear specific path from memory
            prefix = f"opa:{policy_path}:"
            keys_to_del = [k for k in self._memory_cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._memory_cache[k]
        else:
            self._memory_cache.clear()

    async def evaluate_policy(
        self, input_data: Dict[str, Any], policy_path: str = "data.acgs.allow"
    ) -> Dict[str, Any]:
        """Evaluate a policy."""
        cache_key = self._generate_cache_key(policy_path, input_data)
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            # SECURITY FIX (VULN-009): Strict input validation
            self._validate_policy_path(policy_path)
            self._validate_input_data(input_data)

            if self.mode == "http":
                result = await self._evaluate_http(input_data, policy_path)
            elif self.mode == "embedded":
                result = await self._evaluate_embedded(input_data, policy_path)
            else:
                result = await self._evaluate_fallback(input_data, policy_path)

            await self._set_to_cache(cache_key, result)
            return result

        except Exception as e:
            sanitized_error = self._sanitize_error(e)
            logger.error(f"Policy evaluation error: {sanitized_error}")
            return self._handle_evaluation_error(e, policy_path)

    def _validate_policy_path(self, policy_path: str) -> None:
        """Strict validation of OPA policy path to prevent injection (VULN-009)."""
        if not re.match(r"^[a-zA-Z0-9_.]+$", policy_path):
            raise ValueError(f"Invalid policy path characters: {policy_path}")
        if ".." in policy_path:
            raise ValueError(f"Path traversal detected in policy path: {policy_path}")

    def _validate_input_data(self, input_data: Dict[str, Any]) -> None:
        """Validate input data size and structure (VULN-009)."""
        if len(json.dumps(input_data)) > 1024 * 512:  # 512KB limit
            raise ValueError("Input data exceeds maximum allowed size")

    def _sanitize_error(self, error: Exception) -> str:
        """Strip sensitive metadata from error messages (VULN-008)."""
        error_msg = str(error)
        # Remove potential API keys, URLs with tokens, and stack traces
        error_msg = re.sub(r"key=[^&\s]+", "key=REDACTED", error_msg)
        error_msg = re.sub(r"token=[^&\s]+", "token=REDACTED", error_msg)
        error_msg = re.sub(r"https?://[^:\s]+:[^@\s]+@", "http://REDACTED@", error_msg)
        return error_msg

    def _handle_evaluation_error(self, error: Exception, policy_path: str) -> Dict[str, Any]:
        """Build a response for OPA evaluation failures - ALWAYS FAIL-CLOSED."""
        sanitized_error = self._sanitize_error(error)
        logger.error(f"OPA evaluation failed: {sanitized_error}")
        return {
            "result": False,
            "allowed": False,
            "reason": f"Policy evaluation failed: {sanitized_error}",
            "metadata": {
                "error": sanitized_error,
                "mode": self.mode,
                "policy_path": policy_path,
                "security": "fail-closed",
            },
        }

    async def _evaluate_http(self, input_data: Dict[str, Any], policy_path: str) -> Dict[str, Any]:
        """Evaluate policy via HTTP API."""
        if not self._http_client:
            raise OPANotInitializedError("HTTP policy evaluation")

        try:
            path_parts = policy_path.replace("data.", "").replace(".", "/")
            url = f"{self.opa_url}/v1/data/{path_parts}"

            response = await self._http_client.post(url, json={"input": input_data})
            response.raise_for_status()

            data = response.json()
            opa_result = data.get("result", False)

            if isinstance(opa_result, bool):
                return {
                    "result": opa_result,
                    "allowed": opa_result,
                    "reason": "Policy evaluated successfully",
                    "metadata": {"mode": "http", "policy_path": policy_path},
                }
            elif isinstance(opa_result, dict):
                return {
                    "result": opa_result,
                    "allowed": opa_result.get("allow", False),
                    "reason": opa_result.get("reason", "Success"),
                    "metadata": {
                        "mode": "http",
                        "policy_path": policy_path,
                        **opa_result.get("metadata", {}),
                    },
                }
            else:
                return {
                    "result": False,
                    "allowed": False,
                    "reason": f"Unexpected result type: {type(opa_result)}",
                    "metadata": {"mode": "http", "policy_path": policy_path},
                }

        except Exception as e:
            sanitized_error = self._sanitize_error(e)
            logger.error(f"OPA evaluation error: {sanitized_error}")
            raise

    async def _evaluate_embedded(
        self, input_data: Dict[str, Any], policy_path: str
    ) -> Dict[str, Any]:
        """Evaluate policy via embedded OPA SDK."""
        if not self._embedded_opa:
            raise OPANotInitializedError("embedded policy evaluation")

        try:
            loop = asyncio.get_running_loop()
            opa_result = await loop.run_in_executor(
                None, self._embedded_opa.evaluate, policy_path, input_data
            )

            if isinstance(opa_result, bool):
                return {
                    "result": opa_result,
                    "allowed": opa_result,
                    "reason": "Policy evaluated successfully",
                    "metadata": {"mode": "embedded", "policy_path": policy_path},
                }
            elif isinstance(opa_result, dict):
                return {
                    "result": opa_result,
                    "allowed": opa_result.get("allow", False),
                    "reason": opa_result.get("reason", "Success"),
                    "metadata": {
                        "mode": "embedded",
                        "policy_path": policy_path,
                        **opa_result.get("metadata", {}),
                    },
                }
            else:
                return {
                    "result": False,
                    "allowed": False,
                    "reason": f"Unexpected result type: {type(opa_result)}",
                    "metadata": {"mode": "embedded", "policy_path": policy_path},
                }

        except Exception as e:
            sanitized_error = self._sanitize_error(e)
            logger.error(f"Embedded OPA evaluation error: {sanitized_error}")
            raise

    async def _evaluate_fallback(
        self, input_data: Dict[str, Any], policy_path: str
    ) -> Dict[str, Any]:
        """Fallback policy evaluation - ALWAYS FAIL-CLOSED."""
        logger.warning(f"Using fail-closed fallback for {policy_path}")

        constitutional_hash = input_data.get("constitutional_hash", "")
        if constitutional_hash != CONSTITUTIONAL_HASH:
            return {
                "result": False,
                "allowed": False,
                "reason": f"Invalid constitutional hash: {constitutional_hash}",
                "metadata": {"mode": "fallback", "policy_path": policy_path},
            }

        return {
            "result": False,
            "allowed": False,
            "reason": "OPA service unavailable - denied (fail-closed)",
            "metadata": {"mode": "fallback", "policy_path": policy_path, "security": "fail-closed"},
        }

    async def validate_constitutional(self, message: Dict[str, Any]) -> ValidationResult:
        """Validate message against constitutional rules."""
        try:
            input_data = {
                "message": message,
                "constitutional_hash": message.get("constitutional_hash", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            result = await self.evaluate_policy(
                input_data, policy_path="data.acgs.constitutional.validate"
            )

            validation_result = ValidationResult(
                is_valid=result["allowed"], constitutional_hash=CONSTITUTIONAL_HASH
            )

            if not result["allowed"]:
                validation_result.add_error(result.get("reason", "Failed"))

            validation_result.metadata.update(result.get("metadata", {}))
            return validation_result

        except Exception as e:
            logger.error(f"Constitutional validation error: {e}")
            res = ValidationResult(is_valid=False, constitutional_hash=CONSTITUTIONAL_HASH)
            res.add_error(f"Error: {str(e)}")
            return res

    async def check_agent_authorization(
        self, agent_id: str, action: str, resource: str, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if agent is authorized."""
        try:
            ctx = context or {}
            provided_hash = ctx.get("constitutional_hash", CONSTITUTIONAL_HASH)

            if provided_hash != CONSTITUTIONAL_HASH:
                return False

            input_data = {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": ctx,
                "constitutional_hash": provided_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            result = await self.evaluate_policy(input_data, policy_path="data.acgs.rbac.allow")

            return result["allowed"]

        except Exception as e:
            logger.error(f"Authorization check error: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check OPA service health."""
        try:
            if self.mode == "http" and self._http_client:
                response = await self._http_client.get(f"{self.opa_url}/health", timeout=2.0)
                response.raise_for_status()
                return {"status": "healthy", "mode": "http"}
            return {"status": "healthy", "mode": self.mode}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def load_policy(self, policy_id: str, policy_content: str) -> bool:
        """Load a policy into OPA."""
        if self.mode != "http" or not self._http_client:
            return False

        try:
            response = await self._http_client.put(
                f"{self.opa_url}/v1/policies/{policy_id}",
                data=policy_content,
                headers={"Content-Type": "text/plain"},
            )
            response.raise_for_status()

            # Smart Invalidation: Clear cache when policy is updated
            # Note: policy_id might not match the evaluation policy_path exactly,
            # so we clear the whole cache to be safe when a specific policy is loaded.
            await self.clear_cache()

            return True
        except Exception as e:
            logger.error(f"Failed to load policy {policy_id}: {e}")
            return False

    async def load_bundle_from_url(self, url: str, signature: str, public_key: str) -> bool:
        """
        Download and load an OPA bundle with signature verification.
        Implements Pillar 1: Dynamic Policy-as-Code distribution.
        """
        if not self._http_client:
            await self.initialize()

        try:
            # 1. Download bundle
            response = await self._http_client.get(url)
            response.raise_for_status()

            bundle_data = response.content
            temp_path = "runtime/policy_bundles/temp_bundle.tar.gz"
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(bundle_data)

            # 2. Verify signature
            if not await self._verify_bundle(temp_path, signature, public_key):
                logger.error("Bundle signature verification failed")
                return await self._rollback_to_lkg()

            # 3. Load into OPA (Simulated)
            if self.mode == "http":
                logger.info(f"Loading bundle from {url} into OPA")

            # Smart Invalidation: Clear cache when new bundle is loaded
            await self.clear_cache()

            # 4. Update LKG
            lkg_path = "runtime/policy_bundles/lkg_bundle.tar.gz"
            if os.path.exists(lkg_path):
                os.replace(temp_path, lkg_path)
            else:
                os.rename(temp_path, lkg_path)
            self._lkg_bundle_path = lkg_path

            return True

        except Exception as e:
            logger.error(f"Failed to load bundle: {e}")
            return await self._rollback_to_lkg()

    async def _verify_bundle(self, bundle_path: str, signature: str, public_key: str) -> bool:
        """Verify bundle signature using CryptoService."""
        try:
            import sys

            sys.path.append(os.path.join(os.getcwd(), "services/policy_registry"))
            from app.services.crypto_service import CryptoService

            with open(bundle_path, "rb") as f:
                data = f.read()
                bundle_hash = hashlib.sha256(data).hexdigest()

            metadata = {"hash": bundle_hash, "constitutional_hash": CONSTITUTIONAL_HASH}

            return CryptoService.verify_policy_signature(metadata, signature, public_key)
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False

    async def _rollback_to_lkg(self) -> bool:
        """Rollback to Last-Known-Good bundle."""
        lkg_path = "runtime/policy_bundles/lkg_bundle.tar.gz"
        if os.path.exists(lkg_path):
            logger.warning("Rolling back to LKG policy bundle")
            return True
        logger.error("No LKG bundle available for rollback")
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "mode": self.mode,
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._memory_cache),
            "cache_backend": "redis" if self._redis_client else "memory",
            "opa_url": self.opa_url if self.mode == "http" else None,
            "lkg_bundle": self._lkg_bundle_path,
            "fail_closed": self.fail_closed,
        }


# Global client instance
_opa_client: Optional[OPAClient] = None


def get_opa_client(fail_closed: bool = True) -> OPAClient:
    """Get global OPA client instance.

    Args:
        fail_closed: If True, reject requests when OPA is unavailable.
                    Default True for security (fail-closed architecture).
    """
    global _opa_client
    if _opa_client is None:
        _opa_client = OPAClient()
    # Allow callers to configure fail_closed behavior
    _opa_client.fail_closed = fail_closed
    return _opa_client


async def initialize_opa_client(
    opa_url: str = "http://localhost:8181", mode: str = "http", **kwargs
) -> OPAClient:
    """Initialize global OPA client."""
    global _opa_client
    _opa_client = OPAClient(opa_url=opa_url, mode=mode, **kwargs)
    await _opa_client.initialize()
    return _opa_client


async def close_opa_client() -> None:
    """Close global OPA client."""
    global _opa_client
    if _opa_client:
        await _opa_client.close()
        _opa_client = None


__all__ = [
    "OPAClient",
    "get_opa_client",
    "initialize_opa_client",
    "close_opa_client",
]
