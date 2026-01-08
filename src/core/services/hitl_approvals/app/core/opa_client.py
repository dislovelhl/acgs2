"""Constitutional Hash: cdd01ef066bc6cf2
HITL Approvals OPA Client

Provides integration with Open Policy Agent for role-based routing policy evaluation.
Supports querying OPA to determine approval chain routing based on decision type,
impact level, and user roles.
"""

import datetime
import logging
from datetime import timezone
from typing import Any, Dict, List, Optional

import httpx
from src.core.shared.audit_client import AuditClient
from src.core.shared.policy.models import PolicySpecification, VerificationStatus
from src.core.shared.policy.unified_generator import UnifiedVerifiedPolicyGenerator

# Use local config/settings if available, otherwise fallback
try:
    from ..config.settings import settings
except ImportError:
    # Minimal mock for settings if not found
    class Settings:
        opa_url = "http://localhost:8181"

    settings = Settings()

logger = logging.getLogger(__name__)

# Basic types if shared types not easily accessible
JSONDict = Dict[str, Any]
JSONValue = Any


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
    """

    ROUTING_POLICY = "data.hitl.routing"
    AUTHORIZATION_POLICY = "data.hitl.authorization"
    ESCALATION_POLICY = "data.hitl.escalation"

    def __init__(
        self,
        opa_url: Optional[str] = None,
        timeout: float = 5.0,
        cache_ttl: int = 300,
        enable_cache: bool = True,
        fail_closed: bool = True,
    ):
        self.opa_url = (opa_url or settings.opa_url).rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.fail_closed = fail_closed

        self._http_client: Optional[httpx.AsyncClient] = None
        self._audit_client: Optional[AuditClient] = None
        self._policy_generator = UnifiedVerifiedPolicyGenerator()
        self._memory_cache: Dict[str, JSONDict] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        if self._initialized:
            return

        self._http_client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        self._audit_client = AuditClient(service_url=settings.audit_service_url)
        self._initialized = True
        logger.info("OPAClient initialized")

    async def close(self) -> None:
        """Close HTTP client and clear cache."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        self._memory_cache.clear()
        self._initialized = False

    async def evaluate_policy(
        self, input_data: JSONDict, policy_path: str = "data.hitl.routing.allow"
    ) -> JSONDict:
        """
        Evaluate a policy against input data.
        """
        try:
            if not self._http_client:
                await self.initialize()

            # Convert policy path to URL path
            path_parts = policy_path.replace("data.", "").replace(".", "/")
            url = f"{self.opa_url}/v1/data/{path_parts}"

            response = await self._http_client.post(url, json={"input": input_data})
            response.raise_for_status()

            data = response.json()
            opa_result = data.get("result")

            # Report evaluation to audit ledger
            if self._audit_client:
                await self._audit_client.report_decision(
                    {
                        "type": "opa_evaluation",
                        "policy": policy_path,
                        "input": input_data,
                        "result": opa_result,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "constitutional_hash": "cdd01ef066bc6cf2",
                    }
                )

            if opa_result is None:
                return {
                    "result": None,
                    "allowed": False,
                    "reason": "Policy not found or returned undefined",
                }

            if isinstance(opa_result, bool):
                return {
                    "result": opa_result,
                    "allowed": opa_result,
                    "reason": "Policy evaluated successfully",
                }

            if isinstance(opa_result, dict):
                return {
                    "result": opa_result,
                    "allowed": opa_result.get("allow", opa_result.get("allowed", False)),
                    "reason": opa_result.get("reason", "Policy evaluated successfully"),
                }

            return {
                "result": opa_result,
                "allowed": False,
                "reason": f"Unexpected result type: {type(opa_result).__name__}",
            }

        except Exception as e:
            logger.error(f"OPA policy evaluation failed: {e}")
            if self.fail_closed:
                return {
                    "result": False,
                    "allowed": False,
                    "reason": f"OPA unavailable or error occurred (fail-closed): {e}",
                }
            return {
                "result": False,
                "allowed": False,
                "reason": f"OPA elevation error: {e}",
            }

    async def evaluate_policy_verified(
        self,
        input_data: JSONDict,
        policy_path: str,
        natural_language_intent: str,
    ) -> JSONDict:
        """
        Evaluate a policy and provide a formal proof of correctness.
        """
        # Step 1: Standard OPA Evaluation
        opa_result = await self.evaluate_policy(input_data, policy_path)

        # Step 2: Formal Verification
        spec = PolicySpecification(
            spec_id=f"opa_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            natural_language=natural_language_intent,
            context=input_data,
        )

        try:
            policy = await self._policy_generator.generate_verified_policy(spec)

            opa_result["verification_status"] = policy.verification_status.value
            opa_result["smt_formulation"] = policy.smt_formulation
            opa_result["proven"] = policy.verification_status in (
                VerificationStatus.VERIFIED,
                VerificationStatus.PROVEN,
            )

            # Verification override if OPA allowed but proof fails (Safe-fail)
            if opa_result["allowed"] and not opa_result["proven"]:
                opa_result["allowed"] = False
                opa_result[
                    "reason"
                ] = f"Action allowed by OPA but failed formal verification: {policy.verification_status.value}"

            return opa_result
        except Exception as e:
            logger.error(f"Formal verification failed: {e}")
            if self.fail_closed:
                opa_result["allowed"] = False
                opa_result["reason"] = f"Formal verification error (fail-closed): {e}"
            return opa_result

    async def evaluate_routing(
        self,
        decision_type: str,
        user_role: str,
        impact_level: str = "medium",
        context: Optional[JSONDict] = None,
    ) -> JSONDict:
        """
        Evaluate routing policy to determine approval chain.
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

    async def _compute_dfc(self, result: JSONDict) -> float:
        """
        Compute Democratic Fidelity Coefficient (DFC) as a diagnostic heuristic.
        Measures the alignment of the decision with constitutional principles.
        """
        # Baseline score
        score = 0.7 if result.get("allowed") else 0.3

        # Boost if formally proven
        if result.get("proven"):
            score += 0.2

        # Adjustment based on impact level
        impact = result.get("impact_level", "medium")
        if impact == "high":
            score -= 0.1  # Higher rigor needed for high impact
        elif impact == "low":
            score += 0.05

        return min(max(score, 0.0), 1.0)

    async def evaluate_with_dfc(
        self,
        decision_type: str,
        user_role: str,
        impact_level: str = "medium",
        context: Optional[JSONDict] = None,
    ) -> JSONDict:
        """
        Evaluate policy with DFC diagnostic metrics.
        """
        input_data = {
            "decision_type": decision_type,
            "user_role": user_role,
            "impact_level": impact_level,
            **(context or {}),
        }

        # Use verified evaluation
        intent = f"Evaluate routing for {decision_type} (impact: {impact_level})"
        result = await self.evaluate_policy_verified(input_data, self.ROUTING_POLICY, intent)

        # Append DFC score
        result["dfc_score"] = await self._compute_dfc(result)
        result["impact_level"] = impact_level

        return result

    async def evaluate_authorization(
        self,
        user_id: str,
        user_role: str,
        action: str,
        resource: str,
        context: Optional[JSONDict] = None,
    ) -> bool:
        """
        Check if user is authorized to perform action on resource.
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

    async def get_required_approvers(
        self,
        decision_type: str,
        impact_level: str,
        current_level: int,
    ) -> List[str]:
        """
        Get list of required approver roles for a given decision type and level.
        """
        input_data = {
            "decision_type": decision_type,
            "impact_level": impact_level,
            "current_level": current_level,
        }

        result = await self.evaluate_policy(input_data, "data.hitl.routing.required_approvers")

        if result.get("result") and isinstance(result["result"], list):
            return result["result"]

        # Default fallback roles if OPA is unavailable
        default_roles = {
            1: ["engineer", "analyst"],
            2: ["manager", "lead"],
            3: ["director", "vp"],
        }
        return default_roles.get(current_level, ["admin"])


# Global client instance
_opa_client: Optional[OPAClient] = None


def get_opa_client() -> OPAClient:
    global _opa_client
    if _opa_client is None:
        _opa_client = OPAClient()
    return _opa_client
