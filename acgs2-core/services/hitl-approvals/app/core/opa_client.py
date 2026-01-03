"""
HITL Approvals OPA Client

Provides integration with Open Policy Agent for role-based routing policy evaluation.
Supports querying OPA to determine approval chain routing based on decision type,
impact level, and user roles.

Pattern from: acgs2-core/enhanced_agent_bus/opa_client.py
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OPAClientError(Exception):
    """Base exception for OPA client errors."""

    pass


class OPAConnectionError(OPAClientError):
    """Raised when unable to connect to OPA."""

    pass


class OPANotInitializedError(OPAClientError):
    """Raised when OPA client is not initialized."""

    pass


class PolicyEvaluationError(OPAClientError):
    """Raised when policy evaluation fails."""

    pass


class OPAClient:
    """
    Client for OPA (Open Policy Agent) policy evaluation.

    Provides role-based routing policy evaluation for the HITL approvals service.
    Implements fail-closed architecture for security.

    Features:
    - HTTP API mode for remote OPA server
    - Memory caching for performance
    - Fail-closed behavior when OPA unavailable
    - Input validation to prevent injection attacks
    """

    # Default policy paths for HITL routing
    ROUTING_POLICY = "data.hitl.routing"
    AUTHORIZATION_POLICY = "data.hitl.authorization"
    ESCALATION_POLICY = "data.hitl.escalation"

    def __init__(
        self,
        opa_url: Optional[str] = None,
        timeout: float = 5.0,
        cache_ttl: int = 300,  # 5 minutes
        enable_cache: bool = True,
        fail_closed: bool = True,
    ):
        """
        Initialize OPA client.

        Args:
            opa_url: OPA server URL (defaults to settings.opa_url)
            timeout: Request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
            enable_cache: Enable memory caching
            fail_closed: Deny requests when OPA unavailable (security default)
        """
        self.opa_url = (opa_url or settings.opa_url).rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.fail_closed = fail_closed

        self._http_client: Optional[httpx.AsyncClient] = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

        logger.info(f"OPAClient configured with URL: {self._sanitize_url(self.opa_url)}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        if self._initialized:
            return

        self._http_client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        self._initialized = True
        logger.info("OPAClient initialized")

    async def close(self) -> None:
        """Close HTTP client and clear cache."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        self._memory_cache.clear()
        self._initialized = False
        logger.info("OPAClient closed")

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL for logging (mask sensitive parts)."""
        if not url:
            return "<not configured>"
        # Only show host:port for logging
        match = re.match(r"(https?://[^/]+)", url)
        if match:
            return match.group(1)
        return "<url>"

    def _generate_cache_key(self, policy_path: str, input_data: Dict[str, Any]) -> str:
        """Generate cache key from policy path and input data."""
        input_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        return f"opa:{policy_path}:{input_hash}"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from memory cache."""
        if not self.enable_cache:
            return None

        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            now = datetime.now(timezone.utc).timestamp()
            if now - cached["timestamp"] < self.cache_ttl:
                return cached["result"]
            else:
                del self._memory_cache[cache_key]

        return None

    def _set_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Set result in memory cache."""
        if not self.enable_cache:
            return

        self._memory_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        }

    def _validate_policy_path(self, policy_path: str) -> None:
        """
        Validate OPA policy path to prevent injection attacks.

        Args:
            policy_path: The policy path to validate

        Raises:
            ValueError: If policy path contains invalid characters
        """
        if not re.match(r"^[a-zA-Z0-9_.]+$", policy_path):
            raise ValueError(f"Invalid policy path characters: {policy_path}")
        if ".." in policy_path:
            raise ValueError(f"Path traversal detected in policy path: {policy_path}")

    def _validate_input_data(self, input_data: Dict[str, Any]) -> None:
        """
        Validate input data size and structure.

        Args:
            input_data: The input data to validate

        Raises:
            ValueError: If input data exceeds size limits
        """
        serialized = json.dumps(input_data)
        if len(serialized) > 512 * 1024:  # 512KB limit
            raise ValueError("Input data exceeds maximum allowed size (512KB)")

    def _sanitize_error(self, error: Exception) -> str:
        """Strip sensitive metadata from error messages."""
        error_msg = str(error)
        # Remove potential API keys, URLs with tokens
        error_msg = re.sub(r"key=[^&\s]+", "key=REDACTED", error_msg)
        error_msg = re.sub(r"token=[^&\s]+", "token=REDACTED", error_msg)
        error_msg = re.sub(r"https?://[^:\s]+:[^@\s]+@", "http://REDACTED@", error_msg)
        return error_msg

    async def evaluate_policy(
        self, input_data: Dict[str, Any], policy_path: str = "data.hitl.routing.allow"
    ) -> Dict[str, Any]:
        """
        Evaluate a policy against input data.

        Args:
            input_data: Input data for policy evaluation
            policy_path: OPA policy path (default: data.hitl.routing.allow)

        Returns:
            Dictionary containing:
            - result: The raw policy result
            - allowed: Boolean indicating if action is allowed
            - reason: Human-readable reason
            - metadata: Additional context

        Raises:
            PolicyEvaluationError: If evaluation fails and fail_closed is True
        """
        # Check cache first
        cache_key = self._generate_cache_key(policy_path, input_data)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for policy: {policy_path}")
            return cached_result

        try:
            # Validate inputs
            self._validate_policy_path(policy_path)
            self._validate_input_data(input_data)

            # Ensure client is initialized
            if not self._http_client:
                await self.initialize()

            # Convert policy path to URL path
            # "data.hitl.routing" -> "hitl/routing"
            path_parts = policy_path.replace("data.", "").replace(".", "/")
            url = f"{self.opa_url}/v1/data/{path_parts}"

            response = await self._http_client.post(url, json={"input": input_data})
            response.raise_for_status()

            data = response.json()
            opa_result = data.get("result")

            result = self._process_opa_result(opa_result, policy_path)
            self._set_to_cache(cache_key, result)

            logger.debug(
                f"Policy evaluation completed: {policy_path} -> allowed={result['allowed']}"
            )
            return result

        except httpx.ConnectError as e:
            sanitized_error = self._sanitize_error(e)
            logger.error(f"OPA connection error: {sanitized_error}")
            return self._handle_unavailable(policy_path, sanitized_error)

        except httpx.HTTPStatusError as e:
            sanitized_error = self._sanitize_error(e)
            logger.error(f"OPA HTTP error: {sanitized_error}")
            return self._handle_unavailable(policy_path, sanitized_error)

        except Exception as e:
            sanitized_error = self._sanitize_error(e)
            logger.error(f"Policy evaluation error: {sanitized_error}")
            return self._handle_unavailable(policy_path, sanitized_error)

    def _process_opa_result(self, opa_result: Any, policy_path: str) -> Dict[str, Any]:
        """Process OPA result into standard format."""
        if opa_result is None:
            return {
                "result": None,
                "allowed": False,
                "reason": "Policy not found or returned undefined",
                "metadata": {"policy_path": policy_path},
            }

        if isinstance(opa_result, bool):
            return {
                "result": opa_result,
                "allowed": opa_result,
                "reason": "Policy evaluated successfully",
                "metadata": {"policy_path": policy_path},
            }

        if isinstance(opa_result, dict):
            return {
                "result": opa_result,
                "allowed": opa_result.get("allow", False),
                "reason": opa_result.get("reason", "Policy evaluated successfully"),
                "metadata": {
                    "policy_path": policy_path,
                    **opa_result.get("metadata", {}),
                },
            }

        # Unexpected result type
        return {
            "result": opa_result,
            "allowed": False,
            "reason": f"Unexpected result type: {type(opa_result).__name__}",
            "metadata": {"policy_path": policy_path},
        }

    def _handle_unavailable(self, policy_path: str, error: str) -> Dict[str, Any]:
        """
        Handle OPA unavailability with fail-closed behavior.

        When OPA is unavailable, deny all requests for security.
        """
        if self.fail_closed:
            logger.warning(f"OPA unavailable - denying request (fail-closed): {error}")
            return {
                "result": False,
                "allowed": False,
                "reason": f"OPA unavailable - denied (fail-closed): {error}",
                "metadata": {
                    "policy_path": policy_path,
                    "security": "fail-closed",
                    "error": error,
                },
            }
        else:
            # This should not happen in production - fail_closed should always be True
            logger.error("OPA unavailable and fail_closed=False - this is a security risk!")
            return {
                "result": False,
                "allowed": False,
                "reason": "OPA unavailable - denied",
                "metadata": {
                    "policy_path": policy_path,
                    "error": error,
                },
            }

    # =========================================================================
    # HITL-Specific Policy Evaluation Methods
    # =========================================================================

    async def evaluate_routing(
        self,
        decision_type: str,
        user_role: str,
        impact_level: str = "medium",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate routing policy to determine approval chain.

        Args:
            decision_type: Type of decision (e.g., "high_risk", "standard")
            user_role: Role of the user (e.g., "engineer", "manager")
            impact_level: Impact level (low, medium, high, critical)
            context: Additional context for policy evaluation

        Returns:
            Dictionary containing routing decision:
            - allowed: Whether the request can proceed
            - chain_id: Recommended approval chain ID
            - reason: Explanation of routing decision
        """
        input_data = {
            "decision_type": decision_type,
            "user_role": user_role,
            "impact_level": impact_level,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(context or {}),
        }

        result = await self.evaluate_policy(input_data, self.ROUTING_POLICY)

        # Extract chain_id from result if available
        if result.get("result") and isinstance(result["result"], dict):
            chain_id = result["result"].get("chain_id")
            if chain_id:
                result["chain_id"] = chain_id

        return result

    async def evaluate_authorization(
        self,
        user_id: str,
        user_role: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if user is authorized to perform action on resource.

        Args:
            user_id: User identifier
            user_role: User's role
            action: Action to perform (e.g., "approve", "reject", "escalate")
            resource: Resource identifier (e.g., request_id)
            context: Additional authorization context

        Returns:
            True if authorized, False otherwise
        """
        input_data = {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "resource": resource,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(context or {}),
        }

        result = await self.evaluate_policy(input_data, self.AUTHORIZATION_POLICY)
        return result.get("allowed", False)

    async def evaluate_escalation(
        self,
        request_id: str,
        current_level: int,
        escalation_count: int,
        priority: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate escalation policy for a request.

        Args:
            request_id: Approval request identifier
            current_level: Current approval level
            escalation_count: Number of times escalated
            priority: Request priority (low, medium, high, critical)
            context: Additional context

        Returns:
            Dictionary containing:
            - allowed: Whether escalation is allowed
            - next_level: Next approval level (if allowed)
            - reason: Explanation
        """
        input_data = {
            "request_id": request_id,
            "current_level": current_level,
            "escalation_count": escalation_count,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(context or {}),
        }

        result = await self.evaluate_policy(input_data, self.ESCALATION_POLICY)

        # Extract next_level from result if available
        if result.get("result") and isinstance(result["result"], dict):
            next_level = result["result"].get("next_level")
            if next_level is not None:
                result["next_level"] = next_level

        return result

    async def get_required_approvers(
        self,
        decision_type: str,
        impact_level: str,
        current_level: int,
    ) -> List[str]:
        """
        Get list of required approver roles for a given decision type and level.

        Args:
            decision_type: Type of decision
            impact_level: Impact level
            current_level: Current approval level

        Returns:
            List of required approver roles
        """
        input_data = {
            "decision_type": decision_type,
            "impact_level": impact_level,
            "current_level": current_level,
        }

        result = await self.evaluate_policy(input_data, "data.hitl.routing.required_approvers")

        if result.get("result") and isinstance(result["result"], list):
            return result["result"]

        # Default approver roles based on level
        default_roles = {
            1: ["engineer", "analyst"],
            2: ["manager", "lead"],
            3: ["director", "vp"],
            4: ["executive", "ciso"],
        }
        return default_roles.get(current_level, ["admin"])

    # =========================================================================
    # Health Check and Status
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check OPA service health.

        Returns:
            Dictionary containing health status
        """
        try:
            if not self._http_client:
                await self.initialize()

            response = await self._http_client.get(f"{self.opa_url}/health", timeout=2.0)
            response.raise_for_status()

            return {
                "status": "healthy",
                "opa_url": self._sanitize_url(self.opa_url),
                "cache_enabled": self.enable_cache,
                "cache_size": len(self._memory_cache),
                "fail_closed": self.fail_closed,
            }

        except Exception as e:
            sanitized_error = self._sanitize_error(e)
            return {
                "status": "unhealthy",
                "error": sanitized_error,
                "opa_url": self._sanitize_url(self.opa_url),
                "fail_closed": self.fail_closed,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "opa_url": self._sanitize_url(self.opa_url),
            "initialized": self._initialized,
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._memory_cache),
            "fail_closed": self.fail_closed,
        }


# Global client instance (singleton pattern)
_opa_client: Optional[OPAClient] = None


def get_opa_client() -> OPAClient:
    """
    Get the global OPAClient instance.

    Returns:
        The singleton OPAClient instance
    """
    global _opa_client
    if _opa_client is None:
        _opa_client = OPAClient()
    return _opa_client


async def initialize_opa_client(
    opa_url: Optional[str] = None,
    timeout: float = 5.0,
    **kwargs: Any,
) -> OPAClient:
    """
    Initialize the global OPA client.

    Args:
        opa_url: OPA server URL
        timeout: Request timeout
        **kwargs: Additional OPAClient arguments

    Returns:
        Initialized OPAClient instance
    """
    global _opa_client
    _opa_client = OPAClient(opa_url=opa_url, timeout=timeout, **kwargs)
    await _opa_client.initialize()
    return _opa_client


async def close_opa_client() -> None:
    """Close the global OPA client."""
    global _opa_client
    if _opa_client:
        await _opa_client.close()
        _opa_client = None


def reset_opa_client() -> None:
    """
    Reset the global OPAClient instance.

    Used primarily for test isolation.
    """
    global _opa_client
    _opa_client = None


__all__ = [
    "OPAClient",
    "OPAClientError",
    "OPAConnectionError",
    "OPANotInitializedError",
    "PolicyEvaluationError",
    "get_opa_client",
    "initialize_opa_client",
    "close_opa_client",
    "reset_opa_client",
]
