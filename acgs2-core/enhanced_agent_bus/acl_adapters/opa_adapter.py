"""
ACGS-2 OPA (Open Policy Agent) Adapter
Constitutional Hash: cdd01ef066bc6cf2

ACL adapter for OPA integration with fail-closed security model.
Wraps existing opa_client with additional protections.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import ACLAdapter, AdapterConfig, AdapterResult

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


@dataclass
class OPAAdapterConfig(AdapterConfig):
    """OPA-specific adapter configuration."""

    # OPA server settings
    opa_url: str = "http://localhost:8181"
    opa_bundle_path: str = "/v1/data"

    # Fail-closed mode: deny on any failure
    fail_closed: bool = True

    # Policy path within OPA
    default_policy_path: str = "acgs2/constitutional"

    # Cache settings
    cache_enabled: bool = True
    cache_ttl_s: int = 60  # 1 minute - policies can change

    # Override base settings for fast policy checks
    timeout_ms: int = 1000  # 1 second max
    max_retries: int = 2
    circuit_failure_threshold: int = 3  # Faster circuit opening


@dataclass
class OPARequest:
    """Request to OPA policy evaluation."""

    # Input data for policy
    input: dict[str, Any]

    # Optional: specific policy path (overrides default)
    policy_path: Optional[str] = None

    # Request options
    explain: bool = False
    pretty: bool = False
    metrics: bool = True

    # Tracing
    trace_id: Optional[str] = None

    def __post_init__(self):
        if not self.trace_id:
            import json

            self.trace_id = hashlib.sha256(
                json.dumps(self.input, sort_keys=True).encode()
            ).hexdigest()[:16]


@dataclass
class OPAResponse:
    """Response from OPA policy evaluation."""

    # Policy decision
    allow: bool

    # Full result from OPA
    result: Optional[dict[str, Any]] = None

    # Decision ID for audit
    decision_id: Optional[str] = None

    # Explanation (if requested)
    explanation: Optional[list[str]] = None

    # Metrics
    metrics: Optional[dict[str, Any]] = None

    # Constitutional hash
    constitutional_hash: str = CONSTITUTIONAL_HASH

    # Tracing
    trace_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "allow": self.allow,
            "result": self.result,
            "decision_id": self.decision_id,
            "explanation": self.explanation,
            "metrics": self.metrics,
            "constitutional_hash": self.constitutional_hash,
            "trace_id": self.trace_id,
        }


class OPAAdapter(ACLAdapter[OPARequest, OPAResponse]):
    """
    ACL adapter for Open Policy Agent (OPA).

    Provides:
    - Fail-closed security model (deny on error)
    - Fast timeout for policy checks
    - Caching of recent policy decisions
    - Circuit breaker for OPA server failures
    - Integration with existing opa_client
    """

    def __init__(self, name: str = "opa", config: OPAAdapterConfig = None):
        super().__init__(name, config or OPAAdapterConfig())
        self.opa_config = config or OPAAdapterConfig()
        self._http_client = None

    async def _get_http_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import aiohttp

                self._http_client = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(
                        total=self.config.timeout_ms / 1000.0,
                        connect=self.config.connect_timeout_ms / 1000.0,
                    )
                )
            except ImportError:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] aiohttp not available for OPA adapter"
                )
        return self._http_client

    async def _execute(self, request: OPARequest) -> OPAResponse:
        """Execute OPA policy evaluation."""
        policy_path = request.policy_path or self.opa_config.default_policy_path
        url = f"{self.opa_config.opa_url}{self.opa_config.opa_bundle_path}/{policy_path}"

        # Build query params
        params = []
        if request.explain:
            params.append("explain=full")
        if request.pretty:
            params.append("pretty=true")
        if request.metrics:
            params.append("metrics=true")

        if params:
            url = f"{url}?{'&'.join(params)}"

        client = await self._get_http_client()
        if client is None:
            # Fallback to simulated OPA (for testing without aiohttp)
            return self._simulate_opa_response(request)

        try:
            async with client.post(
                url,
                json={"input": request.input},
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] OPA returned status {resp.status}"
                    )
                    # Fail-closed: deny on error
                    if self.opa_config.fail_closed:
                        return OPAResponse(
                            allow=False,
                            result={"error": f"OPA status {resp.status}"},
                            trace_id=request.trace_id,
                        )
                    raise Exception(f"OPA returned status {resp.status}")

                data = await resp.json()
                return self._parse_opa_response(data, request)

        except asyncio.TimeoutError:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] OPA request timed out")
            # Fail-closed: deny on timeout
            if self.opa_config.fail_closed:
                return OPAResponse(
                    allow=False,
                    result={"error": "timeout"},
                    trace_id=request.trace_id,
                )
            raise

        except Exception as e:
            logger.error(f"[{CONSTITUTIONAL_HASH}] OPA request failed: {e}")
            # Fail-closed: deny on any error
            if self.opa_config.fail_closed:
                return OPAResponse(
                    allow=False,
                    result={"error": str(e)},
                    trace_id=request.trace_id,
                )
            raise

    def _parse_opa_response(
        self, data: dict, request: OPARequest
    ) -> OPAResponse:
        """Parse OPA response into OPAResponse."""
        result = data.get("result", {})

        # Extract allow decision - support multiple formats
        allow = False
        if isinstance(result, bool):
            allow = result
        elif isinstance(result, dict):
            allow = result.get("allow", result.get("allowed", False))

        # Extract explanation
        explanation = None
        if request.explain and "explanation" in data:
            explanation = data["explanation"]

        # Extract metrics
        metrics = data.get("metrics")

        # Generate decision ID
        decision_id = hashlib.sha256(
            f"{request.trace_id}:{allow}".encode()
        ).hexdigest()[:16]

        return OPAResponse(
            allow=allow,
            result=result,
            decision_id=decision_id,
            explanation=explanation,
            metrics=metrics,
            trace_id=request.trace_id,
        )

    def _simulate_opa_response(self, request: OPARequest) -> OPAResponse:
        """Simulate OPA response when HTTP client unavailable."""
        # In fail-closed mode, deny everything when OPA is unavailable
        if self.opa_config.fail_closed:
            return OPAResponse(
                allow=False,
                result={"simulated": True, "reason": "opa_unavailable"},
                trace_id=request.trace_id,
            )

        # In fail-open mode, allow (not recommended)
        return OPAResponse(
            allow=True,
            result={"simulated": True, "reason": "opa_unavailable_failopen"},
            trace_id=request.trace_id,
        )

    def _validate_response(self, response: OPAResponse) -> bool:
        """Validate OPA response."""
        # Response is valid if it has a boolean allow decision
        return isinstance(response.allow, bool)

    def _get_cache_key(self, request: OPARequest) -> str:
        """Generate cache key for OPA request."""
        import json

        policy_path = request.policy_path or self.opa_config.default_policy_path
        key_data = f"{policy_path}|{json.dumps(request.input, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_fallback_response(self, request: OPARequest) -> Optional[OPAResponse]:
        """Fallback response when circuit open."""
        # Fail-closed: deny on circuit open
        if self.opa_config.fail_closed:
            return OPAResponse(
                allow=False,
                result={"fallback": True, "reason": "circuit_open"},
                trace_id=request.trace_id,
            )
        return None

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.close()
            self._http_client = None


# Convenience functions for common OPA operations
async def check_constitutional_compliance(
    action: str,
    resource: str,
    context: dict[str, Any] = None,
    adapter: Optional[OPAAdapter] = None,
) -> AdapterResult[OPAResponse]:
    """
    Check if action on resource is constitutionally compliant.

    Args:
        action: Action being performed (e.g., "read", "write", "execute")
        resource: Resource being accessed
        context: Additional context for policy evaluation
        adapter: Optional adapter instance

    Returns:
        AdapterResult with OPAResponse
    """
    if adapter is None:
        adapter = OPAAdapter()

    input_data = {
        "action": action,
        "resource": resource,
        "constitutional_hash": CONSTITUTIONAL_HASH,
        **(context or {}),
    }

    request = OPARequest(
        input=input_data,
        policy_path="acgs2/constitutional/compliance",
        metrics=True,
    )
    return await adapter.call(request)


async def check_agent_permission(
    agent_id: str,
    permission: str,
    target: Optional[str] = None,
    adapter: Optional[OPAAdapter] = None,
) -> AdapterResult[OPAResponse]:
    """
    Check if agent has permission for an action.

    Args:
        agent_id: ID of the agent
        permission: Permission being requested
        target: Optional target resource/agent
        adapter: Optional adapter instance

    Returns:
        AdapterResult with OPAResponse
    """
    if adapter is None:
        adapter = OPAAdapter()

    input_data = {
        "agent_id": agent_id,
        "permission": permission,
        "target": target,
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }

    request = OPARequest(
        input=input_data,
        policy_path="acgs2/agent/permissions",
        metrics=True,
    )
    return await adapter.call(request)


async def evaluate_maci_role(
    agent_role: str,
    action: str,
    target_role: Optional[str] = None,
    adapter: Optional[OPAAdapter] = None,
) -> AdapterResult[OPAResponse]:
    """
    Evaluate MACI role separation constraints.

    Ensures executive/legislative/judicial separation.

    Args:
        agent_role: Role of the agent (executive, legislative, judicial)
        action: Action being performed (propose, validate, extract_rules)
        target_role: Role of target agent (for cross-validation)
        adapter: Optional adapter instance

    Returns:
        AdapterResult with OPAResponse
    """
    if adapter is None:
        adapter = OPAAdapter()

    input_data = {
        "agent_role": agent_role,
        "action": action,
        "target_role": target_role,
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }

    request = OPARequest(
        input=input_data,
        policy_path="acgs2/maci/role_separation",
        explain=True,  # Always explain role decisions
        metrics=True,
    )
    return await adapter.call(request)
