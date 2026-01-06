"""
ACGS-2 Policy Enforcement
Constitutional Hash: cdd01ef066bc6cf2

Provides policy enforcement mechanisms for constitutional AI governance,
including enforcement actions, violation tracking, and remediation.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EnforcementAction(Enum):
    """Possible enforcement actions."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ESCALATE = "escalate"
    RATE_LIMIT = "rate_limit"
    AUDIT_ONLY = "audit_only"
    QUARANTINE = "quarantine"


class ViolationSeverity(Enum):
    """Violation severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EnforcementMode(Enum):
    """Enforcement mode configuration."""

    ENFORCE = "enforce"  # Full enforcement
    AUDIT = "audit"  # Log only, don't block
    DRY_RUN = "dry_run"  # Simulate without side effects
    DISABLED = "disabled"  # No enforcement


@dataclass
class PolicyContext:
    """Context for policy evaluation."""

    agent_id: str
    action: str
    resource_type: str
    resource_id: str
    tenant_id: str = "default"
    constitutional_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str = ""
    parent_request_id: str = ""
    environment: str = "development"

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "agent_id": self.agent_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "tenant_id": self.tenant_id,
            "constitutional_hash": self.constitutional_hash,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "parent_request_id": self.parent_request_id,
            "environment": self.environment,
        }


@dataclass
class PolicyViolation:
    """Represents a policy violation."""

    id: str
    policy_id: str
    policy_name: str
    rule_id: str
    severity: ViolationSeverity
    message: str
    context: PolicyContext
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    remediation_hint: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "remediation_hint": self.remediation_hint,
            "metadata": self.metadata,
        }


@dataclass
class EnforcementResult:
    """Result of policy enforcement."""

    allowed: bool
    action: EnforcementAction
    violations: List[PolicyViolation] = field(default_factory=list)
    policies_evaluated: int = 0
    evaluation_time_ms: float = 0.0
    confidence_score: float = 1.0
    reasoning: str = ""
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    require_human_review: bool = False
    escalation_level: int = 0

    @property
    def has_violations(self) -> bool:
        """Check if there are any violations."""
        return len(self.violations) > 0

    @property
    def max_severity(self) -> Optional[ViolationSeverity]:
        """Get the maximum severity of violations."""
        if not self.violations:
            return None
        severities = [
            ViolationSeverity.CRITICAL,
            ViolationSeverity.HIGH,
            ViolationSeverity.MEDIUM,
            ViolationSeverity.LOW,
            ViolationSeverity.INFO,
        ]
        for severity in severities:
            if any(v.severity == severity for v in self.violations):
                return severity
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "violations": [v.to_dict() for v in self.violations],
            "policies_evaluated": self.policies_evaluated,
            "evaluation_time_ms": self.evaluation_time_ms,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "require_human_review": self.require_human_review,
            "escalation_level": self.escalation_level,
        }


@dataclass
class PolicyRule:
    """Individual policy rule."""

    id: str
    policy_id: str
    name: str
    condition: str
    action: EnforcementAction
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    message_template: str = ""
    remediation_hint: str = ""
    enabled: bool = True
    priority: int = 0

    def evaluate(self, context: PolicyContext, evaluator: Callable) -> Tuple[bool, str]:
        """Evaluate the rule against context."""
        if not self.enabled:
            return True, ""

        try:
            result = evaluator(self.condition, context.to_dict())
            if not result:
                message = self.message_template.format(**context.to_dict())
                return False, message
            return True, ""
        except Exception as e:
            logger.error(f"Rule evaluation error for {self.id}: {e}")
            return True, ""  # Fail open on evaluation errors


class PolicyEnforcer:
    """Enforces governance policies."""

    def __init__(
        self,
        constitutional_hash: str,
        mode: EnforcementMode = EnforcementMode.ENFORCE,
    ):
        self.constitutional_hash = constitutional_hash
        self.mode = mode

        # Policy rules registry
        self._rules: Dict[str, PolicyRule] = {}
        self._rule_lock = threading.Lock()

        # Custom evaluators
        self._condition_evaluator: Optional[Callable] = None
        self._pre_enforcement_hooks: List[Callable] = []
        self._post_enforcement_hooks: List[Callable] = []

        # Metrics
        self._total_evaluations = 0
        self._total_violations = 0
        self._total_allowed = 0
        self._total_denied = 0
        self._evaluation_times: List[float] = []

        # Rate limiting
        self._rate_limit_buckets: Dict[str, List[float]] = {}
        self._rate_limit_lock = threading.Lock()
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_requests = 100

    def set_mode(self, mode: EnforcementMode) -> None:
        """Set the enforcement mode."""
        logger.info(f"Enforcement mode changed: {self.mode.value} -> {mode.value}")
        self.mode = mode

    def set_condition_evaluator(self, evaluator: Callable) -> None:
        """Set a custom condition evaluator."""
        self._condition_evaluator = evaluator

    def add_pre_hook(self, hook: Callable) -> None:
        """Add a pre-enforcement hook."""
        self._pre_enforcement_hooks.append(hook)

    def add_post_hook(self, hook: Callable) -> None:
        """Add a post-enforcement hook."""
        self._post_enforcement_hooks.append(hook)

    def register_rule(self, rule: PolicyRule) -> None:
        """Register a policy rule."""
        with self._rule_lock:
            self._rules[rule.id] = rule

    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a policy rule."""
        with self._rule_lock:
            if rule_id in self._rules:
                del self._rules[rule_id]

                return True
        return False

    def get_rules(self) -> List[PolicyRule]:
        """Get all registered rules sorted by priority."""
        with self._rule_lock:
            rules = list(self._rules.values())
            rules.sort(key=lambda r: r.priority, reverse=True)
            return rules

    async def enforce(self, context: PolicyContext) -> EnforcementResult:
        """Enforce policies against the given context."""
        start_time = time.time()

        # Check enforcement mode
        if self.mode == EnforcementMode.DISABLED:
            return EnforcementResult(
                allowed=True,
                action=EnforcementAction.ALLOW,
                reasoning="Enforcement disabled",
            )

        # Run pre-enforcement hooks
        for hook in self._pre_enforcement_hooks:
            try:
                hook(context)
            except Exception as e:
                logger.error(f"Pre-enforcement hook error: {e}")

        # Check rate limiting first
        rate_limit_result = self._check_rate_limit(context.agent_id)
        if not rate_limit_result:
            return EnforcementResult(
                allowed=False,
                action=EnforcementAction.RATE_LIMIT,
                reasoning="Rate limit exceeded",
                violations=[
                    PolicyViolation(
                        id=f"violation-{int(time.time() * 1000000)}",
                        policy_id="rate-limit",
                        policy_name="Rate Limiting",
                        rule_id="rate-limit-exceeded",
                        severity=ViolationSeverity.MEDIUM,
                        message="Agent has exceeded the rate limit",
                        context=context,
                    )
                ],
            )

        # Evaluate all rules
        violations = []
        policies_evaluated = 0

        with self._rule_lock:
            rules = sorted(self._rules.values(), key=lambda r: r.priority, reverse=True)

        for rule in rules:
            if not rule.enabled:
                continue

            policies_evaluated += 1
            passed, message = self._evaluate_rule(rule, context)

            if not passed:
                violation = PolicyViolation(
                    id=f"violation-{int(time.time() * 1000000)}",
                    policy_id=rule.policy_id,
                    policy_name=rule.name,
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=message or f"Violated rule: {rule.name}",
                    context=context,
                    remediation_hint=rule.remediation_hint,
                )
                violations.append(violation)

        # Determine enforcement action
        action, allowed, require_review, escalation = self._determine_action(violations)

        # Calculate evaluation time
        evaluation_time = (time.time() - start_time) * 1000  # ms
        self._evaluation_times.append(evaluation_time)

        # Keep only recent times
        if len(self._evaluation_times) > 1000:
            self._evaluation_times = self._evaluation_times[-1000:]

        # Build result
        result = EnforcementResult(
            allowed=allowed if self.mode == EnforcementMode.ENFORCE else True,
            action=action if self.mode == EnforcementMode.ENFORCE else EnforcementAction.AUDIT_ONLY,
            violations=violations,
            policies_evaluated=policies_evaluated,
            evaluation_time_ms=evaluation_time,
            reasoning=self._generate_reasoning(allowed, violations),
            require_human_review=require_review,
            escalation_level=escalation,
        )

        # Update metrics
        self._update_metrics(result)

        # Run post-enforcement hooks
        for hook in self._post_enforcement_hooks:
            try:
                hook(context, result)
            except Exception as e:
                logger.error(f"Post-enforcement hook error: {e}")

        return result

    def _evaluate_rule(
        self,
        rule: PolicyRule,
        context: PolicyContext,
    ) -> Tuple[bool, str]:
        """Evaluate a single rule."""
        if self._condition_evaluator:
            return rule.evaluate(context, self._condition_evaluator)

        # Default evaluation - check for simple conditions
        try:
            # Simple expression evaluation
            return self._default_evaluate(rule.condition, context)
        except Exception as e:
            logger.error(f"Rule evaluation error: {e}")
            return True, ""  # Fail open

    def _default_evaluate(
        self,
        condition: str,
        context: PolicyContext,
    ) -> Tuple[bool, str]:
        """Default rule evaluation logic."""
        # Parse simple conditions like "action != 'delete'" or "resource_type == 'public'"
        try:
            # Build evaluation context
            eval_context = context.to_dict()

            # Simple operator parsing
            if "!=" in condition:
                parts = condition.split("!=")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip("'\"")
                    actual = eval_context.get(key, "")
                    if actual == value:
                        return False, f"{key} must not be {value}"

            elif "==" in condition:
                parts = condition.split("==")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip("'\"")
                    actual = eval_context.get(key, "")
                    if actual != value:
                        return False, f"{key} must be {value}"

            elif "in " in condition:
                # Handle "action in ['read', 'list']"
                parts = condition.split(" in ")
                if len(parts) == 2:
                    key = parts[0].strip()
                    actual = eval_context.get(key, "")
                    # Simple list parsing
                    allowed = (
                        parts[1].strip().strip("[]").replace("'", "").replace('"', "").split(",")
                    )
                    allowed = [v.strip() for v in allowed]
                    if actual not in allowed:
                        return False, f"{key} must be one of {allowed}"

            return True, ""

        except Exception as e:
            logger.warning(f"Default evaluation error for condition '{condition}': {e}")
            return True, ""  # Fail open

    def _determine_action(
        self,
        violations: List[PolicyViolation],
    ) -> Tuple[EnforcementAction, bool, bool, int]:
        """Determine enforcement action based on violations."""
        if not violations:
            return EnforcementAction.ALLOW, True, False, 0

        # Find highest severity
        max_severity = None
        for v in violations:
            if max_severity is None:
                max_severity = v.severity
            elif self._severity_level(v.severity) > self._severity_level(max_severity):
                max_severity = v.severity

        # Determine action based on severity
        if max_severity == ViolationSeverity.CRITICAL:
            return EnforcementAction.DENY, False, True, 3
        elif max_severity == ViolationSeverity.HIGH:
            return EnforcementAction.REQUIRE_APPROVAL, False, True, 2
        elif max_severity == ViolationSeverity.MEDIUM:
            return EnforcementAction.ESCALATE, False, True, 1
        elif max_severity == ViolationSeverity.LOW:
            return EnforcementAction.AUDIT_ONLY, True, False, 0
        else:
            return EnforcementAction.ALLOW, True, False, 0

    def _severity_level(self, severity: ViolationSeverity) -> int:
        """Get numeric level for severity comparison."""
        levels = {
            ViolationSeverity.INFO: 0,
            ViolationSeverity.LOW: 1,
            ViolationSeverity.MEDIUM: 2,
            ViolationSeverity.HIGH: 3,
            ViolationSeverity.CRITICAL: 4,
        }
        return levels.get(severity, 0)

    def _generate_reasoning(
        self,
        allowed: bool,
        violations: List[PolicyViolation],
    ) -> str:
        """Generate human-readable reasoning."""
        if allowed and not violations:
            return "Action allowed - no policy violations detected"

        if allowed:
            return f"Action allowed with {len(violations)} low-severity violations (audit only)"

        reasons = [f"Policy violation: {v.message}" for v in violations[:3]]
        if len(violations) > 3:
            reasons.append(f"...and {len(violations) - 3} more violations")

        return f"Action denied - {'; '.join(reasons)}"

    def _check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent is within rate limits."""
        current_time = time.time()

        with self._rate_limit_lock:
            if agent_id not in self._rate_limit_buckets:
                self._rate_limit_buckets[agent_id] = []

            # Remove old entries
            bucket = self._rate_limit_buckets[agent_id]
            bucket[:] = [t for t in bucket if current_time - t < self.rate_limit_window]

            # Check if within limit
            if len(bucket) >= self.rate_limit_max_requests:
                return False

            # Add current request
            bucket.append(current_time)
            return True

    def _update_metrics(self, result: EnforcementResult) -> None:
        """Update enforcement metrics."""
        self._total_evaluations += 1
        self._total_violations += len(result.violations)

        if result.allowed:
            self._total_allowed += 1
        else:
            self._total_denied += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get enforcement metrics."""
        avg_time = 0.0
        if self._evaluation_times:
            avg_time = sum(self._evaluation_times) / len(self._evaluation_times)

        return {
            "total_evaluations": self._total_evaluations,
            "total_violations": self._total_violations,
            "total_allowed": self._total_allowed,
            "total_denied": self._total_denied,
            "average_evaluation_time_ms": avg_time,
            "enforcement_mode": self.mode.value,
            "registered_rules": len(self._rules),
        }

    def reset_metrics(self) -> None:
        """Reset enforcement metrics."""
        self._total_evaluations = 0
        self._total_violations = 0
        self._total_allowed = 0
        self._total_denied = 0
        self._evaluation_times.clear()


# Global instance
_policy_enforcer: Optional[PolicyEnforcer] = None
_enforcer_lock = threading.Lock()


def get_policy_enforcer() -> Optional[PolicyEnforcer]:
    """Get the global policy enforcer instance."""
    return _policy_enforcer


def initialize_policy_enforcer(
    constitutional_hash: str,
    mode: EnforcementMode = EnforcementMode.ENFORCE,
) -> PolicyEnforcer:
    """Initialize the global policy enforcer."""
    global _policy_enforcer

    with _enforcer_lock:
        if _policy_enforcer is None:
            _policy_enforcer = PolicyEnforcer(constitutional_hash, mode)
        elif _policy_enforcer.constitutional_hash != constitutional_hash:
            _policy_enforcer = PolicyEnforcer(constitutional_hash, mode)

    return _policy_enforcer


async def enforce_policy(context: PolicyContext) -> EnforcementResult:
    """Enforce policies using the global enforcer."""
    enforcer = get_policy_enforcer()
    if enforcer is None:
        raise RuntimeError("Policy enforcer not initialized")

    return await enforcer.enforce(context)


def shutdown_policy_enforcer() -> None:
    """Shutdown the global policy enforcer."""
    global _policy_enforcer

    with _enforcer_lock:
        if _policy_enforcer:
            _policy_enforcer = None
