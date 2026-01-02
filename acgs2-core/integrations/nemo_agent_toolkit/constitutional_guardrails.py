"""
ACGS-2 Constitutional Guardrails for NeMo-Agent-Toolkit
Constitutional Hash: cdd01ef066bc6cf2

Provides constitutional validation guardrails that integrate with
NeMo-Agent-Toolkit's agent optimization pipeline.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import httpx

if TYPE_CHECKING:
    from collections.abc import Awaitable

CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GuardrailAction(str, Enum):
    """Actions a guardrail can take."""

    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    ESCALATE = "escalate"
    AUDIT = "audit"


class ViolationType(str, Enum):
    """Types of constitutional violations."""

    PRIVACY = "privacy"
    SAFETY = "safety"
    ETHICS = "ethics"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    TRANSPARENCY = "transparency"
    FAIRNESS = "fairness"
    ACCOUNTABILITY = "accountability"


@dataclass
class GuardrailConfig:
    """Configuration for constitutional guardrails."""

    enabled: bool = True
    strict_mode: bool = False
    max_retries: int = 3
    timeout_seconds: float = 5.0
    colang_version: str = "2.x"  # Support for latest Colang 2.x
    audit_all_requests: bool = True
    block_on_violation: bool = True
    escalation_threshold: float = 0.8
    constitutional_hash: str = CONSTITUTIONAL_HASH

    # Policy configuration
    privacy_protection: bool = True
    safety_checks: bool = True
    ethics_validation: bool = True
    compliance_enforcement: bool = True

    # PII patterns to detect
    pii_patterns: list[str] = field(
        default_factory=lambda: [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{16}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
        ]
    )

    # NIM Integration
    use_nim: bool = False
    nim_endpoint: str = "http://localhost:8000/v1"
    nim_model: str = "nvidia/nemotron-3-8b-steerlm"
    nim_guardrails_enabled: bool = True

    # Bot Reasoning Monitoring
    monitor_reasoning: bool = True
    reasoning_validation_threshold: float = 0.9

    def validate(self) -> None:
        """Validate configuration."""
        if self.constitutional_hash != CONSTITUTIONAL_HASH:
            raise ValueError(
                f"Invalid constitutional hash. Expected {CONSTITUTIONAL_HASH}, "
                f"got {self.constitutional_hash}"
            )


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""

    action: GuardrailAction
    allowed: bool
    violations: list[dict[str, Any]] = field(default_factory=list)
    modified_content: str | None = None
    reasoning: str = ""
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    constitutional_hash: str = CONSTITUTIONAL_HASH
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "allowed": self.allowed,
            "violations": self.violations,
            "modified_content": self.modified_content,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "constitutional_hash": self.constitutional_hash,
            "trace_id": self.trace_id,
        }


class ConstitutionalGuardrails:
    """
    Constitutional guardrails for NeMo-Agent-Toolkit integration.

    Provides input/output validation, PII protection, safety checks,
    and constitutional compliance enforcement for AI agents.
    """

    def __init__(
        self,
        config: GuardrailConfig | None = None,
        acgs2_client: Any | None = None,
    ) -> None:
        """
        Initialize constitutional guardrails.

        Args:
            config: Guardrail configuration
            acgs2_client: Optional ACGS-2 SDK client for policy validation
        """
        self.config = config or GuardrailConfig()
        self.config.validate()
        self._client = acgs2_client
        self._violation_handlers: dict[ViolationType, list[Callable]] = {}
        self._input_validators: list[Callable] = []
        self._output_validators: list[Callable] = []
        self._audit_log: list[dict[str, Any]] = []
        self._compiled_patterns: list[Any] = []
        self._colang_flows: dict[str, str] = {}
        self._reasoning_traces: list[dict[str, Any]] = []
        self._http_client: httpx.AsyncClient | None = None

        self._compile_patterns()
        self._init_colang_flows()

    async def __aenter__(self):
        """Async context manager entry."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.config.nim_endpoint, timeout=self.config.timeout_seconds
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _init_colang_flows(self) -> None:
        """Initialize Colang 2.0 flows for constitutional principles."""
        if self.config.colang_version.startswith("2"):
            colang_path = Path(__file__).parent / "colang" / "constitutional_principles.co"
            if colang_path.exists():
                try:
                    with open(colang_path, "r") as f:
                        self._colang_flows["constitutional_principles"] = f.read()
                    logger.info(f"Loaded external Colang flows from {colang_path}")
                except Exception as e:
                    logger.error(f"Failed to load external Colang flows: {e}")
            else:
                # Fallback to defaults if file missing
                self._colang_flows = {
                    "privacy_flow": """
flow monitor privacy check
    when bot said $text
    if len(regex_findall("pii_patterns", $text)) > 0
        abort "Constitutional violation: Privacy leak detected."
                    """,
                    "safety_flow": """
flow monitor safety check
    when bot said $text
    if contains_unsafe_content($text)
        abort "Constitutional violation: Unsafe content detected."
                    """,
                }

    def _compile_patterns(self) -> None:
        """Compile PII detection patterns."""
        import re

        self._compiled_patterns = [re.compile(pattern) for pattern in self.config.pii_patterns]

    def _generate_trace_id(self) -> str:
        """Generate a trace ID for audit purposes."""
        timestamp = datetime.now(UTC).isoformat()
        data = f"{timestamp}-{CONSTITUTIONAL_HASH}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def add_input_validator(
        self,
        validator: Callable[[str], Awaitable[GuardrailResult] | GuardrailResult],
    ) -> None:
        """Add a custom input validator."""
        self._input_validators.append(validator)

    def add_output_validator(
        self,
        validator: Callable[[str], Awaitable[GuardrailResult] | GuardrailResult],
    ) -> None:
        """Add a custom output validator."""
        self._output_validators.append(validator)

    def on_violation(
        self,
        violation_type: ViolationType,
        handler: Callable[[dict[str, Any]], None],
    ) -> None:
        """Register a violation handler."""
        if violation_type not in self._violation_handlers:
            self._violation_handlers[violation_type] = []
        self._violation_handlers[violation_type].append(handler)

    async def check_input(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> GuardrailResult:
        """
        Check input content against constitutional guardrails.

        Args:
            content: Input content to validate
            context: Optional context for validation

        Returns:
            GuardrailResult with validation outcome
        """
        if not self.config.enabled:
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                allowed=True,
                trace_id=self._generate_trace_id(),
            )

        trace_id = self._generate_trace_id()
        violations: list[dict[str, Any]] = []

        # Check for PII
        if self.config.privacy_protection:
            pii_violations = self._detect_pii(content)
            violations.extend(pii_violations)

        # Check for safety issues
        if self.config.safety_checks:
            safety_violations = await self._check_safety(content)
            violations.extend(safety_violations)

        # Delegate to NIM if enabled
        if self.config.use_nim and self.config.nim_guardrails_enabled:
            nim_violations = await self._check_with_nim_guardrails(content)
            violations.extend(nim_violations)

        # Run custom validators
        for validator in self._input_validators:
            result = validator(content)
            if asyncio.iscoroutine(result):
                result = await result
            if not result.allowed:
                violations.extend(result.violations)

        # Validate with ACGS-2 if client available
        if self._client and self.config.compliance_enforcement:
            compliance_result = await self._validate_with_acgs2(content, context)
            if not compliance_result.allowed:
                violations.extend(compliance_result.violations)

        # Determine action
        if violations:
            self._handle_violations(violations)
            if self.config.block_on_violation:
                action = GuardrailAction.BLOCK
                allowed = False
            else:
                action = GuardrailAction.AUDIT
                allowed = True
        else:
            action = GuardrailAction.ALLOW
            allowed = True

        result = GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            reasoning=self._generate_reasoning(violations),
            trace_id=trace_id,
        )

        # Audit logging
        if self.config.audit_all_requests:
            self._audit(trace_id, "input", content, result)

        return result

    async def check_output(
        self,
        content: str,
        context: dict[str, Any] | None = None,
        reasoning: str | None = None,
    ) -> GuardrailResult:
        """
        Check output content against constitutional guardrails.

        Args:
            content: Output content to validate
            context: Optional context for validation
            reasoning: Optional LLM thinking/reasoning trace to validate

        Returns:
            GuardrailResult with validation outcome
        """
        if not self.config.enabled:
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                allowed=True,
                trace_id=self._generate_trace_id(),
            )

        trace_id = self._generate_trace_id()
        violations: list[dict[str, Any]] = []
        modified_content: str | None = None

        # Validate reasoning trace if provided
        if reasoning and self.config.monitor_reasoning:
            reasoning_violations = await self._validate_reasoning(reasoning, trace_id)
            violations.extend(reasoning_violations)

        # Check for PII in output
        if self.config.privacy_protection:
            pii_violations = self._detect_pii(content)
            if pii_violations:
                # Attempt to redact PII from output
                modified_content = self._redact_pii(content)
                violations.extend(pii_violations)

        # Check for harmful content
        if self.config.safety_checks:
            safety_violations = await self._check_output_safety(content)
            violations.extend(safety_violations)

        # Run custom validators
        for validator in self._output_validators:
            result = validator(content)
            if asyncio.iscoroutine(result):
                result = await result
            if not result.allowed:
                violations.extend(result.violations)
                if result.modified_content:
                    modified_content = result.modified_content

        # Determine action
        if violations:
            self._handle_violations(violations)
            if modified_content:
                action = GuardrailAction.MODIFY
                allowed = True
            elif self.config.block_on_violation:
                action = GuardrailAction.BLOCK
                allowed = False
            else:
                action = GuardrailAction.AUDIT
                allowed = True
        else:
            action = GuardrailAction.ALLOW
            allowed = True

        result = GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            modified_content=modified_content,
            reasoning=self._generate_reasoning(violations),
            trace_id=trace_id,
        )

        # Audit logging
        if self.config.audit_all_requests:
            self._audit(trace_id, "output", content, result)

        return result

    def _detect_pii(self, content: str) -> list[dict[str, Any]]:
        """Detect PII in content."""
        violations: list[dict[str, Any]] = []
        for i, pattern in enumerate(self._compiled_patterns):
            matches = pattern.findall(content)
            if matches:
                violations.append(
                    {
                        "type": ViolationType.PRIVACY.value,
                        "pattern_index": i,
                        "match_count": len(matches),
                        "message": f"PII detected: {len(matches)} potential matches",
                    }
                )
        return violations

    def _redact_pii(self, content: str) -> str:
        """Redact PII from content."""
        redacted = content
        for pattern in self._compiled_patterns:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    async def _check_safety(self, content: str) -> list[dict[str, Any]]:
        """Check content for safety issues."""
        violations: list[dict[str, Any]] = []

        # Basic safety patterns
        unsafe_patterns = [
            (r"\b(hack|exploit|attack)\s+(system|server|database)\b", "security_threat"),
            (r"\b(delete|drop|truncate)\s+all\b", "destructive_action"),
            (r"\bpassword\s*[:=]\s*\S+", "credential_exposure"),
        ]

        import re

        for pattern, violation_type in unsafe_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(
                    {
                        "type": ViolationType.SECURITY.value,
                        "subtype": violation_type,
                        "message": f"Safety concern detected: {violation_type}",
                    }
                )

        return violations

    async def _check_output_safety(self, content: str) -> list[dict[str, Any]]:
        """Check output content for safety issues."""
        violations: list[dict[str, Any]] = []

        # Check for potential harmful output patterns
        harmful_patterns = [
            (r"\b(instructions?\s+to|how\s+to)\s+(hack|exploit|attack)\b", "harmful_instructions"),
            (r"\b(malware|virus|trojan|ransomware)\s+(code|script)\b", "malicious_content"),
        ]

        import re

        for pattern, violation_type in harmful_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(
                    {
                        "type": ViolationType.SAFETY.value,
                        "subtype": violation_type,
                        "message": f"Harmful content detected: {violation_type}",
                    }
                )

        return violations

    async def _check_with_nim_guardrails(self, content: str) -> list[dict[str, Any]]:
        """Check content using NemoGuard NIM microservices."""
        if not self._http_client:
            logger.warning("HTTP client not initialized. Call __aenter__ or initialize manually.")
            return []

        violations = []
        try:
            response = await self._http_client.post(
                "/guardrails",
                json={
                    "model": self.config.nim_model,
                    "text": content,
                    "guardrails": ["content_safety", "jailbreak_detection"],
                },
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("allowed", True):
                violations.append(
                    {
                        "type": ViolationType.SAFETY.value,
                        "message": "NIM Guardrail identified a violation",
                        "details": result.get("violations", []),
                    }
                )
        except Exception as e:
            logger.error(f"NIM communication error: {e}")
            if self.config.strict_mode:
                violations.append(
                    {
                        "type": ViolationType.SECURITY.value,
                        "message": f"NIM service unavailable: {e}",
                    }
                )

        return violations

    async def _validate_reasoning(self, reasoning: str, trace_id: str) -> list[dict[str, Any]]:
        """Validate LLM thinking/reasoning traces."""
        violations = []

        # Capture trace for audit
        self._reasoning_traces.append(
            {
                "trace_id": trace_id,
                "reasoning": reasoning,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Check for suspicious patterns in reasoning (e.g., trying to bypass guardrails)
        bypass_patterns = [
            r"ignore\s+previous\s+instructions",
            r"bypass\s+safety",
            r"constitutional\s+override",
        ]

        import re

        for pattern in bypass_patterns:
            if re.search(pattern, reasoning, re.IGNORECASE):
                violations.append(
                    {
                        "type": ViolationType.SECURITY.value,
                        "subtype": "reasoning_bypass_attempt",
                        "message": "Potential guardrail bypass attempt detected in reasoning trace",
                    }
                )

        return violations

    async def _validate_with_acgs2(
        self,
        content: str,
        context: dict[str, Any] | None,
    ) -> GuardrailResult:
        """Validate content with ACGS-2 compliance service."""
        if not self._client:
            return GuardrailResult(
                action=GuardrailAction.ALLOW,
                allowed=True,
            )

        try:
            # Use ACGS-2 compliance validation
            from acgs2_sdk import ComplianceService

            compliance = ComplianceService(self._client)
            result = await compliance.validate_action(
                agent_id=context.get("agent_id", "nemo-agent") if context else "nemo-agent",
                action="process_content",
                context={
                    "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                    "content_length": len(content),
                    **(context or {}),
                },
            )

            if not result.get("compliant", True):
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    allowed=False,
                    violations=[
                        {
                            "type": ViolationType.COMPLIANCE.value,
                            "message": "ACGS-2 compliance validation failed",
                            "details": result,
                        }
                    ],
                )

        except Exception as e:
            logger.warning(f"ACGS-2 validation failed: {e}")
            if self.config.strict_mode:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    allowed=False,
                    violations=[
                        {
                            "type": ViolationType.COMPLIANCE.value,
                            "message": f"ACGS-2 validation error: {e}",
                        }
                    ],
                )

        return GuardrailResult(action=GuardrailAction.ALLOW, allowed=True)

    def _handle_violations(self, violations: list[dict[str, Any]]) -> None:
        """Handle detected violations."""
        for violation in violations:
            violation_type = ViolationType(violation.get("type", "compliance"))
            handlers = self._violation_handlers.get(violation_type, [])
            for handler in handlers:
                try:
                    handler(violation)
                except Exception as e:
                    logger.error(f"Violation handler error: {e}")

    def _generate_reasoning(self, violations: list[dict[str, Any]]) -> str:
        """Generate human-readable reasoning for the result."""
        if not violations:
            return "Content passed all constitutional guardrail checks."

        reasons = []
        for v in violations:
            reasons.append(f"- {v.get('type', 'unknown')}: {v.get('message', 'No details')}")

        return "Constitutional violations detected:\n" + "\n".join(reasons)

    def _audit(
        self,
        trace_id: str,
        direction: str,
        content: str,
        result: GuardrailResult,
    ) -> None:
        """Log audit entry."""
        entry = {
            "trace_id": trace_id,
            "direction": direction,
            "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            "content_length": len(content),
            "action": result.action.value,
            "allowed": result.allowed,
            "violation_count": len(result.violations),
            "timestamp": datetime.now(UTC).isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
        self._audit_log.append(entry)
        logger.info(f"Guardrail audit: {json.dumps(entry)}")

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log."""
        return self._audit_log.copy()

    def clear_audit_log(self) -> None:
        """Clear the audit log."""
        self._audit_log.clear()

    async def get_metrics(self) -> dict[str, Any]:
        """Get guardrail metrics."""
        total = len(self._audit_log)
        if total == 0:
            return {
                "total_checks": 0,
                "allowed_rate": 1.0,
                "violation_rate": 0.0,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }

        allowed = sum(1 for entry in self._audit_log if entry.get("allowed", False))
        violations = sum(entry.get("violation_count", 0) for entry in self._audit_log)

        return {
            "total_checks": total,
            "allowed_count": allowed,
            "blocked_count": total - allowed,
            "allowed_rate": allowed / total,
            "violation_rate": violations / total if total > 0 else 0.0,
            "input_checks": sum(1 for e in self._audit_log if e.get("direction") == "input"),
            "output_checks": sum(1 for e in self._audit_log if e.get("direction") == "output"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
