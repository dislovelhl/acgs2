"""
Constitutional Runtime Safety Guardrails
==========================================

Constitutional Hash: cdd01ef066bc6cf2

Implements comprehensive guardrails layer that enforces
constitutional principles at runtime with minimal latency:
- Input sanitization
- Policy enforcement (pre-execution)
- Sandbox execution
- Output verification
- Audit logging

References:
- Superagent Framework Guardrails
- OWASP GenAI Security Project
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Awaitable
from enum import Enum
import uuid
import logging
import re

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class GuardrailLevel(Enum):
    """Levels of guardrail enforcement."""
    STRICT = "strict"      # Block all violations
    MODERATE = "moderate"  # Block high-risk, warn moderate
    PERMISSIVE = "permissive"  # Warn only, allow most


class EscalationAction(Enum):
    """Actions for escalation handling."""
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"
    ENHANCED_LOGGING = "enhanced_logging"
    NOTIFY = "notify"


@dataclass
class SanitizationResult:
    """Result from input sanitization."""
    sanitized: Any
    modifications_made: List[str]
    risks_detected: List[str]
    blocked: bool = False


@dataclass
class PolicyResult:
    """Result from policy evaluation."""
    allowed: bool
    policy_id: str
    reasons: List[str]
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None


@dataclass
class SandboxResult:
    """Result from sandboxed execution."""
    output: Any
    execution_time_ms: float
    resource_usage: Dict[str, float]
    errors: List[str]
    truncated: bool = False


@dataclass
class VerificationResult:
    """Result from output verification."""
    verified: bool
    modifications_made: List[str]
    warnings: List[str]


@dataclass
class GuardrailResult:
    """Complete result from guardrail pipeline."""
    result_id: str
    action: Any
    result: Any
    sanitization: SanitizationResult
    policy_result: PolicyResult
    sandbox_result: Optional[SandboxResult]
    verification: VerificationResult
    audit_id: str
    processing_time_ms: float
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "constitutional_hash": self.constitutional_hash,
            "processing_time_ms": self.processing_time_ms,
            "audit_id": self.audit_id,
            "blocked": self.sanitization.blocked or not self.policy_result.allowed,
        }


class InputSanitizer:
    """
    Sanitizes input to prevent injection attacks.

    Removes or escapes potentially dangerous patterns.
    """

    # Patterns to remove or escape
    DANGEROUS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"data:",
        r"on\w+\s*=",
        r"\{\{.*?\}\}",
        r"\$\{.*?\}",
    ]

    INJECTION_PATTERNS = [
        r";\s*DROP\s+TABLE",
        r";\s*DELETE\s+FROM",
        r"--\s*$",
        r"\/\*.*?\*\/",
    ]

    def __init__(self, level: GuardrailLevel = GuardrailLevel.MODERATE):
        self.level = level

    async def sanitize(self, input_data: Any) -> SanitizationResult:
        """
        Sanitize input data.

        Args:
            input_data: Raw input to sanitize

        Returns:
            SanitizationResult with sanitized data
        """
        modifications = []
        risks = []
        blocked = False

        if isinstance(input_data, str):
            sanitized, mods, found_risks = await self._sanitize_string(input_data)
            modifications.extend(mods)
            risks.extend(found_risks)

        elif isinstance(input_data, dict):
            sanitized = {}
            for key, value in input_data.items():
                # Sanitize keys
                clean_key, key_mods, key_risks = await self._sanitize_string(str(key))
                modifications.extend(key_mods)
                risks.extend(key_risks)

                # Recursively sanitize values
                sub_result = await self.sanitize(value)
                sanitized[clean_key] = sub_result.sanitized
                modifications.extend(sub_result.modifications_made)
                risks.extend(sub_result.risks_detected)

        elif isinstance(input_data, list):
            sanitized = []
            for item in input_data:
                sub_result = await self.sanitize(item)
                sanitized.append(sub_result.sanitized)
                modifications.extend(sub_result.modifications_made)
                risks.extend(sub_result.risks_detected)
        else:
            sanitized = input_data

        # Block if too many risks in strict mode
        if self.level == GuardrailLevel.STRICT and len(risks) > 3:
            blocked = True

        return SanitizationResult(
            sanitized=sanitized,
            modifications_made=modifications,
            risks_detected=risks,
            blocked=blocked,
        )

    async def _sanitize_string(
        self,
        text: str
    ) -> tuple[str, List[str], List[str]]:
        """Sanitize a string value."""
        modifications = []
        risks = []
        sanitized = text

        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, sanitized, re.IGNORECASE)
            if matches:
                risks.append(f"Dangerous pattern: {pattern}")
                sanitized = re.sub(pattern, "[REMOVED]", sanitized, flags=re.IGNORECASE)
                modifications.append(f"Removed pattern: {pattern}")

        # Check injection patterns
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                risks.append(f"Injection pattern: {pattern}")
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
                modifications.append(f"Removed injection: {pattern}")

        # Escape remaining special characters in strict mode
        if self.level == GuardrailLevel.STRICT:
            sanitized = sanitized.replace("<", "&lt;").replace(">", "&gt;")

        return sanitized, modifications, risks


class PolicyEngine:
    """
    Evaluates actions against constitutional policies.

    Pre-execution check to ensure compliance.
    """

    def __init__(self):
        self._policies: Dict[str, Callable[[Any, Dict], bool]] = {}
        self._load_default_policies()

    def _load_default_policies(self):
        """Load default constitutional policies."""
        self._policies["constitutional_hash"] = lambda action, ctx: \
            ctx.get("constitutional_hash") == CONSTITUTIONAL_HASH or \
            "constitutional_hash" not in ctx

        self._policies["no_admin_bypass"] = lambda action, ctx: \
            "admin_override" not in str(action).lower()

        self._policies["rate_limit"] = lambda action, ctx: \
            ctx.get("request_count", 0) < 1000

    async def evaluate(
        self,
        action: Any,
        context: Dict[str, Any],
        constitutional_hash: str = CONSTITUTIONAL_HASH
    ) -> PolicyResult:
        """
        Evaluate action against all policies.

        Args:
            action: The action to evaluate
            context: Execution context
            constitutional_hash: Expected hash

        Returns:
            PolicyResult with evaluation outcome
        """
        reasons = []
        requires_escalation = False
        escalation_reason = None

        context["constitutional_hash"] = constitutional_hash

        for policy_id, check_fn in self._policies.items():
            try:
                if not check_fn(action, context):
                    reasons.append(f"Policy '{policy_id}' violation")

                    # High-risk violations require escalation
                    if policy_id in ["constitutional_hash", "no_admin_bypass"]:
                        requires_escalation = True
                        escalation_reason = f"Critical policy violation: {policy_id}"

            except Exception as e:
                reasons.append(f"Policy '{policy_id}' error: {str(e)}")

        return PolicyResult(
            allowed=len(reasons) == 0,
            policy_id="combined",
            reasons=reasons,
            requires_escalation=requires_escalation,
            escalation_reason=escalation_reason,
        )


class Sandbox:
    """
    Sandboxed execution environment.

    Executes actions in isolated environment with resource limits.
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        memory_limit_mb: int = 512
    ):
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb

    async def execute(self, action: Any) -> SandboxResult:
        """
        Execute action in sandbox.

        Args:
            action: The action to execute

        Returns:
            SandboxResult with execution outcome
        """
        import time
        start_time = time.perf_counter()
        errors = []
        output = None
        truncated = False

        try:
            # Simulate sandboxed execution
            # In production, would use actual isolation (e.g., Firecracker)

            if callable(action):
                output = await asyncio.wait_for(
                    action(),
                    timeout=self.timeout_seconds
                )
            else:
                output = action

            # Truncate large outputs
            if isinstance(output, str) and len(output) > 10000:
                output = output[:10000] + "...[truncated]"
                truncated = True

        except asyncio.TimeoutError:
            errors.append(f"Execution timeout after {self.timeout_seconds}s")
        except Exception as e:
            errors.append(f"Execution error: {str(e)}")

        execution_time = (time.perf_counter() - start_time) * 1000

        return SandboxResult(
            output=output,
            execution_time_ms=execution_time,
            resource_usage={
                "cpu_percent": 5.0,  # Simulated
                "memory_mb": 50.0,
            },
            errors=errors,
            truncated=truncated,
        )


class OutputVerifier:
    """
    Verifies output for constitutional compliance.

    Post-execution check to ensure output is safe.
    """

    SENSITIVE_PATTERNS = [
        r"password\s*[:=]\s*\S+",
        r"api[_-]?key\s*[:=]\s*\S+",
        r"secret\s*[:=]\s*\S+",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    ]

    async def verify(self, output: Any) -> VerificationResult:
        """
        Verify output for compliance.

        Args:
            output: The output to verify

        Returns:
            VerificationResult with verification outcome
        """
        modifications = []
        warnings = []

        if isinstance(output, str):
            # Check for sensitive data leakage
            for pattern in self.SENSITIVE_PATTERNS:
                if re.search(pattern, output, re.IGNORECASE):
                    warnings.append(f"Potential sensitive data: {pattern}")
                    # Redact sensitive data
                    output = re.sub(pattern, "[REDACTED]", output, flags=re.IGNORECASE)
                    modifications.append(f"Redacted: {pattern}")

        return VerificationResult(
            verified=len(warnings) == 0,
            modifications_made=modifications,
            warnings=warnings,
        )


class EscalationHandler:
    """
    Handles escalation of policy violations.

    Routes violations to appropriate handlers.
    """

    def __init__(self):
        self._handlers: Dict[EscalationAction, Callable] = {}
        self._escalation_log: List[Dict[str, Any]] = []

    async def escalate(
        self,
        action: Any,
        reason: str,
        escalation_action: EscalationAction = EscalationAction.HUMAN_REVIEW
    ) -> Dict[str, Any]:
        """
        Escalate a violation.

        Args:
            action: The violating action
            reason: Reason for escalation
            escalation_action: Type of escalation

        Returns:
            Escalation result
        """
        escalation_id = f"esc-{uuid.uuid4().hex[:8]}"

        escalation_record = {
            "escalation_id": escalation_id,
            "action": str(action)[:100],
            "reason": reason,
            "escalation_action": escalation_action.value,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
        }

        self._escalation_log.append(escalation_record)

        logger.warning(f"Escalation {escalation_id}: {reason}")

        return escalation_record


class AuditLog:
    """
    Audit logging for all guardrail operations.

    Maintains immutable record of all actions.
    """

    def __init__(self):
        self._logs: List[Dict[str, Any]] = []

    async def record(
        self,
        action: Any,
        result: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an action and its result.

        Args:
            action: The action taken
            result: The result
            metadata: Optional metadata

        Returns:
            Audit ID
        """
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"

        record = {
            "audit_id": audit_id,
            "action_hash": hash(str(action)),
            "result_hash": hash(str(result)),
            "timestamp": datetime.utcnow().isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "metadata": metadata or {},
        }

        self._logs.append(record)
        return audit_id

    async def get_logs(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent audit logs."""
        return self._logs[-limit:]


class ConstitutionalGuardrails:
    """
    Constitutional Runtime Guardrails.

    Full pipeline:
    1. Input sanitization
    2. Policy enforcement (pre-execution)
    3. Sandbox execution
    4. Output verification
    5. Audit logging

    Enforces constitutional principles at runtime
    with minimal latency impact.
    """

    def __init__(
        self,
        level: GuardrailLevel = GuardrailLevel.MODERATE
    ):
        """
        Initialize guardrails.

        Args:
            level: Enforcement level
        """
        self.level = level

        self.input_sanitizer = InputSanitizer(level)
        self.policy_engine = PolicyEngine()
        self.sandbox = Sandbox()
        self.output_verifier = OutputVerifier()
        self.escalation_handler = EscalationHandler()
        self.audit_log = AuditLog()

        self._stats = {
            "total_requests": 0,
            "blocked": 0,
            "escalated": 0,
            "completed": 0,
        }

        logger.info(f"Initialized ConstitutionalGuardrails level={level.value}")

    async def enforce(
        self,
        action: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        """
        Full guardrail pipeline execution.

        Args:
            action: The action to guard
            context: Execution context

        Returns:
            GuardrailResult with complete pipeline results
        """
        import time
        start_time = time.perf_counter()

        result_id = f"guard-{uuid.uuid4().hex[:8]}"
        self._stats["total_requests"] += 1
        context = context or {}

        # Step 1: Input sanitization
        sanitization = await self.input_sanitizer.sanitize(action)

        if sanitization.blocked:
            self._stats["blocked"] += 1
            audit_id = await self.audit_log.record(action, "blocked_by_sanitizer")
            processing_time = (time.perf_counter() - start_time) * 1000

            return GuardrailResult(
                result_id=result_id,
                action=action,
                result=None,
                sanitization=sanitization,
                policy_result=PolicyResult(False, "sanitizer", ["Blocked by sanitizer"], False),
                sandbox_result=None,
                verification=VerificationResult(False, [], ["Blocked before execution"]),
                audit_id=audit_id,
                processing_time_ms=processing_time,
            )

        sanitized_action = sanitization.sanitized

        # Step 2: Policy enforcement (pre-execution)
        policy_result = await self.policy_engine.evaluate(
            sanitized_action,
            context
        )

        if policy_result.requires_escalation:
            self._stats["escalated"] += 1
            await self.escalation_handler.escalate(
                sanitized_action,
                policy_result.escalation_reason or "Policy violation"
            )

        if not policy_result.allowed:
            self._stats["blocked"] += 1
            audit_id = await self.audit_log.record(action, "blocked_by_policy")
            processing_time = (time.perf_counter() - start_time) * 1000

            return GuardrailResult(
                result_id=result_id,
                action=action,
                result=None,
                sanitization=sanitization,
                policy_result=policy_result,
                sandbox_result=None,
                verification=VerificationResult(False, [], policy_result.reasons),
                audit_id=audit_id,
                processing_time_ms=processing_time,
            )

        # Step 3: Sandbox execution
        sandbox_result = await self.sandbox.execute(sanitized_action)

        # Step 4: Output verification
        verification = await self.output_verifier.verify(sandbox_result.output)

        # Step 5: Audit logging
        audit_id = await self.audit_log.record(
            action,
            sandbox_result.output,
            {"verification": verification.verified}
        )

        self._stats["completed"] += 1
        processing_time = (time.perf_counter() - start_time) * 1000

        return GuardrailResult(
            result_id=result_id,
            action=action,
            result=sandbox_result.output,
            sanitization=sanitization,
            policy_result=policy_result,
            sandbox_result=sandbox_result,
            verification=verification,
            audit_id=audit_id,
            processing_time_ms=processing_time,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get guardrails statistics."""
        total = self._stats["total_requests"]
        block_rate = self._stats["blocked"] / max(total, 1)

        return {
            **self._stats,
            "block_rate": block_rate,
            "level": self.level.value,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


def create_guardrails(
    level: GuardrailLevel = GuardrailLevel.MODERATE
) -> ConstitutionalGuardrails:
    """Factory function to create guardrails."""
    return ConstitutionalGuardrails(level=level)
