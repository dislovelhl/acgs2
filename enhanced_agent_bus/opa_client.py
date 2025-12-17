"""
ACGS-2 OPA (Open Policy Agent) Client
Constitutional Hash: cdd01ef066bc6cf2

Provides integration with OPA for policy-based decision making and authorization.
Supports both HTTP API mode (remote OPA server) and embedded mode.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
import httpx

try:
    from .models import AgentMessage, CONSTITUTIONAL_HASH
    from .validators import ValidationResult
    from .exceptions import (
        OPAConnectionError,
        OPANotInitializedError,
        PolicyEvaluationError,
    )
except ImportError:
    # Fallback for direct execution or testing
    from models import AgentMessage, CONSTITUTIONAL_HASH  # type: ignore
    from validators import ValidationResult  # type: ignore
    from exceptions import (  # type: ignore
        OPAConnectionError,
        OPANotInitializedError,
        PolicyEvaluationError,
    )

# Import centralized Redis config for caching
try:
    from shared.redis_config import get_redis_url
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    def get_redis_url(db: int = 0) -> str:
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
    ):
        """
        Initialize OPA client.

        Args:
            opa_url: URL of OPA server (for HTTP mode)
            mode: Operation mode - "http", "embedded", or "fallback"
            timeout: Request timeout in seconds
            cache_ttl: Cache TTL in seconds
            enable_cache: Enable result caching
            redis_url: Redis URL for caching (uses default if None)
        """
        self.opa_url = opa_url.rstrip("/")
        self.mode = mode
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_client: Optional[Any] = None
        self._embedded_opa: Optional[Any] = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

        # Redis configuration
        self.redis_url = redis_url or get_redis_url(db=2)  # Use DB 2 for OPA cache

        # Validate mode
        if mode == "embedded" and not OPA_SDK_AVAILABLE:
            logger.warning("Embedded mode requested but OPA SDK not available, falling back to HTTP mode")
            self.mode = "http"

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize HTTP client and cache connections."""
        # Initialize HTTP client for API mode
        if self.mode in ("http", "fallback"):
            if not self._http_client:
                self._http_client = httpx.AsyncClient(
                    timeout=self.timeout,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
                )

        # Initialize embedded OPA if available
        if self.mode == "embedded" and OPA_SDK_AVAILABLE:
            try:
                self._embedded_opa = EmbeddedOPA()
                logger.info("Embedded OPA initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedded OPA: {e}")
                self.mode = "http"  # Fallback to HTTP mode
                if not self._http_client:
                    self._http_client = httpx.AsyncClient(
                        timeout=self.timeout,
                        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
                    )

        # Initialize Redis cache if enabled and available
        if self.enable_cache and REDIS_CLIENT_AVAILABLE:
            try:
                self._redis_client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis_client.ping()
                logger.info("Redis cache initialized for OPA client")
            except Exception as e:
                logger.warning(f"Redis cache initialization failed: {e}, using memory cache")
                self._redis_client = None

    async def close(self):
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
        """
        Generate cache key for policy evaluation.

        Args:
            policy_path: Policy path
            input_data: Input data

        Returns:
            Cache key string
        """
        # Create deterministic hash of input
        input_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        return f"opa:{policy_path}:{input_hash}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache."""
        if not self.enable_cache:
            return None

        # Try Redis first
        if self._redis_client:
            try:
                cached = await self._redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # Fall back to memory cache
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            # Check if expired
            if datetime.now(timezone.utc).timestamp() - cached["timestamp"] < self.cache_ttl:
                return cached["result"]
            else:
                del self._memory_cache[cache_key]

        return None

    async def _set_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """Set result in cache."""
        if not self.enable_cache:
            return

        # Try Redis first
        if self._redis_client:
            try:
                await self._redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(result)
                )
                return
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")

        # Fall back to memory cache
        self._memory_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc).timestamp()
        }

    async def evaluate_policy(
        self,
        input_data: Dict[str, Any],
        policy_path: str = "data.acgs.allow"
    ) -> Dict[str, Any]:
        """
        Evaluate a policy with given input data.

        Args:
            input_data: Input data for policy evaluation
            policy_path: Policy path to evaluate (e.g., "data.acgs.allow")

        Returns:
            Policy evaluation result dictionary with keys:
            - result: The policy decision (bool or dict)
            - allowed: True if policy allows the action
            - reason: Optional reason for decision
            - metadata: Additional metadata
        """
        # Check cache
        cache_key = self._generate_cache_key(policy_path, input_data)
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for policy {policy_path}")
            return cached_result

        # Evaluate based on mode
        try:
            if self.mode == "http":
                result = await self._evaluate_http(input_data, policy_path)
            elif self.mode == "embedded":
                result = await self._evaluate_embedded(input_data, policy_path)
            else:
                result = await self._evaluate_fallback(input_data, policy_path)

            # Cache the result
            await self._set_to_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            # Fallback to permissive decision with warning
            return {
                "result": False,
                "allowed": False,
                "reason": f"Policy evaluation failed: {str(e)}",
                "metadata": {"error": str(e), "mode": self.mode}
            }

    async def _evaluate_http(
        self,
        input_data: Dict[str, Any],
        policy_path: str
    ) -> Dict[str, Any]:
        """Evaluate policy via HTTP API."""
        if not self._http_client:
            raise OPANotInitializedError("HTTP policy evaluation")

        try:
            # OPA expects POST to /v1/data/{policy_path}
            # Convert policy_path like "data.acgs.allow" to "/v1/data/acgs/allow"
            path_parts = policy_path.replace("data.", "").replace(".", "/")
            url = f"{self.opa_url}/v1/data/{path_parts}"

            response = await self._http_client.post(
                url,
                json={"input": input_data}
            )
            response.raise_for_status()

            # Handle both sync and async json() methods
            json_result = response.json()
            if hasattr(json_result, '__await__'):
                data = await json_result
            else:
                data = json_result
            opa_result = data.get("result", False)

            # Normalize response
            if isinstance(opa_result, bool):
                return {
                    "result": opa_result,
                    "allowed": opa_result,
                    "reason": "Policy evaluated successfully",
                    "metadata": {"mode": "http", "policy_path": policy_path}
                }
            elif isinstance(opa_result, dict):
                return {
                    "result": opa_result,
                    "allowed": opa_result.get("allow", False),
                    "reason": opa_result.get("reason", "Policy evaluated successfully"),
                    "metadata": {
                        "mode": "http",
                        "policy_path": policy_path,
                        **opa_result.get("metadata", {})
                    }
                }
            else:
                return {
                    "result": False,
                    "allowed": False,
                    "reason": f"Unexpected result type: {type(opa_result)}",
                    "metadata": {"mode": "http", "policy_path": policy_path}
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"OPA HTTP error: {e.response.status_code}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"OPA timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"OPA evaluation error: {e}")
            raise

    async def _evaluate_embedded(
        self,
        input_data: Dict[str, Any],
        policy_path: str
    ) -> Dict[str, Any]:
        """Evaluate policy via embedded OPA SDK."""
        if not self._embedded_opa:
            raise OPANotInitializedError("embedded policy evaluation")

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            opa_result = await loop.run_in_executor(
                None,
                self._embedded_opa.evaluate,
                policy_path,
                input_data
            )

            # Normalize response (similar to HTTP mode)
            if isinstance(opa_result, bool):
                return {
                    "result": opa_result,
                    "allowed": opa_result,
                    "reason": "Policy evaluated successfully",
                    "metadata": {"mode": "embedded", "policy_path": policy_path}
                }
            elif isinstance(opa_result, dict):
                return {
                    "result": opa_result,
                    "allowed": opa_result.get("allow", False),
                    "reason": opa_result.get("reason", "Policy evaluated successfully"),
                    "metadata": {
                        "mode": "embedded",
                        "policy_path": policy_path,
                        **opa_result.get("metadata", {})
                    }
                }
            else:
                return {
                    "result": False,
                    "allowed": False,
                    "reason": f"Unexpected result type: {type(opa_result)}",
                    "metadata": {"mode": "embedded", "policy_path": policy_path}
                }

        except Exception as e:
            logger.error(f"Embedded OPA evaluation error: {e}")
            raise

    async def _evaluate_fallback(
        self,
        input_data: Dict[str, Any],
        policy_path: str
    ) -> Dict[str, Any]:
        """
        Fallback policy evaluation when OPA is unavailable.

        SECURITY: Implements FAIL-CLOSED principle.
        When OPA is unavailable, all requests are DENIED by default
        to prevent constitutional bypass attacks.
        """
        logger.warning(f"Using FAIL-CLOSED fallback evaluation for {policy_path}")

        # Basic constitutional hash validation
        constitutional_hash = input_data.get("constitutional_hash", "")
        if constitutional_hash != CONSTITUTIONAL_HASH:
            return {
                "result": False,
                "allowed": False,
                "reason": f"Invalid constitutional hash: {constitutional_hash}",
                "metadata": {"mode": "fallback", "policy_path": policy_path}
            }

        # FAIL-CLOSED: Deny by default when OPA is unavailable
        # This prevents bypass of constitutional validation
        logger.error(
            f"OPA unavailable - DENYING request for policy {policy_path}. "
            "Constitutional validation requires OPA service."
        )
        return {
            "result": False,
            "allowed": False,
            "reason": "OPA service unavailable - constitutional validation denied (fail-closed)",
            "metadata": {
                "mode": "fallback",
                "policy_path": policy_path,
                "security": "fail-closed",
                "action_required": "Restore OPA service to process requests"
            }
        }

    async def validate_constitutional(
        self,
        message: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate message against constitutional rules.

        Args:
            message: Message dictionary to validate

        Returns:
            ValidationResult with validation outcome
        """
        try:
            # Prepare input for OPA
            input_data = {
                "message": message,
                "constitutional_hash": message.get("constitutional_hash", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Evaluate constitutional policy
            result = await self.evaluate_policy(
                input_data,
                policy_path="data.acgs.constitutional.validate"
            )

            # Convert to ValidationResult
            validation_result = ValidationResult(
                is_valid=result["allowed"],
                constitutional_hash=CONSTITUTIONAL_HASH
            )

            if not result["allowed"]:
                validation_result.add_error(result.get("reason", "Constitutional validation failed"))

            # Add warnings if using fallback
            if result.get("metadata", {}).get("mode") == "fallback":
                validation_result.add_warning("OPA unavailable, using fallback validation")

            # Add metadata
            validation_result.metadata.update(result.get("metadata", {}))

            return validation_result

        except Exception as e:
            logger.error(f"Constitutional validation error: {e}")
            # Fail closed - return invalid result on error
            result = ValidationResult(
                is_valid=False,
                constitutional_hash=CONSTITUTIONAL_HASH
            )
            result.add_error(f"Constitutional validation error: {str(e)}")
            return result

    async def check_agent_authorization(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if agent is authorized to perform action on resource.

        Args:
            agent_id: Agent identifier
            action: Action to perform (e.g., "read", "write", "execute")
            resource: Resource identifier
            context: Additional context for authorization decision

        Returns:
            True if authorized, False otherwise
        """
        try:
            # Use hash from context if provided, otherwise use default
            ctx = context or {}
            provided_hash = ctx.get("constitutional_hash", CONSTITUTIONAL_HASH)

            # Validate constitutional hash first - deny if invalid
            if provided_hash != CONSTITUTIONAL_HASH:
                logger.warning(
                    f"Authorization denied for agent {agent_id}: "
                    f"Invalid constitutional hash '{provided_hash}'"
                )
                return False

            # Prepare input for RBAC policy
            input_data = {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": ctx,
                "constitutional_hash": provided_hash,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Evaluate RBAC policy
            result = await self.evaluate_policy(
                input_data,
                policy_path="data.acgs.rbac.allow"
            )

            allowed = result["allowed"]

            if not allowed:
                logger.warning(
                    f"Authorization denied for agent {agent_id} "
                    f"to {action} resource {resource}: {result.get('reason')}"
                )

            return allowed

        except Exception as e:
            logger.error(f"Authorization check error: {e}")
            # Fail closed - deny access on error
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check OPA service health.

        Returns:
            Health status dictionary
        """
        try:
            if self.mode == "http" and self._http_client:
                response = await self._http_client.get(
                    f"{self.opa_url}/health",
                    timeout=2.0
                )
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "mode": "http",
                    "opa_url": self.opa_url,
                    "cache_enabled": self.enable_cache,
                    "cache_backend": "redis" if self._redis_client else "memory"
                }
            elif self.mode == "embedded":
                return {
                    "status": "healthy",
                    "mode": "embedded",
                    "cache_enabled": self.enable_cache,
                    "cache_backend": "redis" if self._redis_client else "memory"
                }
            else:
                return {
                    "status": "degraded",
                    "mode": "fallback",
                    "warning": "OPA unavailable, using fallback validation"
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "mode": self.mode,
                "error": str(e)
            }

    async def load_policy(
        self,
        policy_id: str,
        policy_content: str
    ) -> bool:
        """
        Load a policy into OPA (HTTP mode only).

        Args:
            policy_id: Policy identifier
            policy_content: Rego policy content

        Returns:
            True if successful, False otherwise
        """
        if self.mode != "http":
            logger.error("Policy loading only supported in HTTP mode")
            return False

        if not self._http_client:
            logger.error("HTTP client not initialized")
            return False

        try:
            response = await self._http_client.put(
                f"{self.opa_url}/v1/policies/{policy_id}",
                data=policy_content,
                headers={"Content-Type": "text/plain"}
            )
            response.raise_for_status()

            logger.info(f"Policy {policy_id} loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load policy {policy_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "mode": self.mode,
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._memory_cache),
            "cache_backend": "redis" if self._redis_client else "memory",
            "opa_url": self.opa_url if self.mode == "http" else None,
        }


# Global client instance
_opa_client: Optional[OPAClient] = None


def get_opa_client() -> OPAClient:
    """Get global OPA client instance."""
    global _opa_client
    if _opa_client is None:
        _opa_client = OPAClient()
    return _opa_client


async def initialize_opa_client(
    opa_url: str = "http://localhost:8181",
    mode: str = "http",
    **kwargs
) -> OPAClient:
    """
    Initialize global OPA client.

    Args:
        opa_url: OPA server URL
        mode: Operation mode
        **kwargs: Additional client arguments

    Returns:
        Initialized OPA client
    """
    global _opa_client
    _opa_client = OPAClient(opa_url=opa_url, mode=mode, **kwargs)
    await _opa_client.initialize()
    return _opa_client


async def close_opa_client():
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
