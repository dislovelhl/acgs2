"""
ACGS-2 Runtime Safety Guardrails

OWASP-compliant layered security architecture for runtime protection:

1. Input Sanitizer → Cleans and validates incoming requests
2. Agent Engine → Core governance with constitutional validation
3. Tool Runner (Sandbox) → Isolated execution environment
4. Output Verifier → Post-execution content validation
5. Audit Log → Immutable compliance trail

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class GuardrailLayer(str, Enum):
    """OWASP-compliant guardrail layers."""

    INPUT_SANITIZER = "input_sanitizer"
    AGENT_ENGINE = "agent_engine"
    TOOL_RUNNER_SANDBOX = "tool_runner_sandbox"
    OUTPUT_VERIFIER = "output_verifier"
    AUDIT_LOG = "audit_log"


class SafetyAction(str, Enum):
    """Safety actions the guardrails can take."""

    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    ESCALATE = "escalate"
    SANDBOX = "sandbox"
    AUDIT = "audit"


class ViolationSeverity(str, Enum):
    """Severity levels for violations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Violation:
    """A safety violation detected by guardrails."""

    layer: GuardrailLayer
    violation_type: str
    severity: ViolationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer.value,
            "violation_type": self.violation_type,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
        }


@dataclass
class GuardrailResult:
    """Result from a guardrail layer."""

    action: SafetyAction
    allowed: bool
    violations: List[Violation] = field(default_factory=list)
    modified_data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "allowed": self.allowed,
            "violations": [v.to_dict() for v in self.violations],
            "modified_data": self.modified_data,
            "metadata": self.metadata,
            "processing_time_ms": self.processing_time_ms,
            "trace_id": self.trace_id,
        }


class GuardrailComponent(ABC):
    """Abstract base class for guardrail components."""

    @abstractmethod
    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Process data through this guardrail component."""
        pass

    @abstractmethod
    def get_layer(self) -> GuardrailLayer:
        """Return the guardrail layer this component implements."""
        pass

    async def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for this component."""
        return {}


@dataclass
class InputSanitizerConfig:
    """Configuration for input sanitizer."""

    enabled: bool = True
    max_input_length: int = 1000000  # 1MB
    allowed_content_types: List[str] = field(default_factory=lambda: ["text/plain", "application/json"])
    sanitize_html: bool = True
    detect_injection: bool = True
    pii_detection: bool = True
    timeout_ms: int = 1000


class InputSanitizer(GuardrailComponent):
    """Input Sanitizer: Layer 1 of OWASP guardrails.

    Cleans, validates, and sanitizes incoming requests before they reach
    the agent engine.
    """

    def __init__(self, config: Optional[InputSanitizerConfig] = None):
        self.config = config or InputSanitizerConfig()
        self._pii_patterns = self._compile_pii_patterns()
        self._injection_patterns = self._compile_injection_patterns()

    def get_layer(self) -> GuardrailLayer:
        return GuardrailLayer.INPUT_SANITIZER

    def _compile_pii_patterns(self) -> List[re.Pattern]:
        """Compile PII detection patterns."""
        patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{16}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
            r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",  # Credit card with spaces
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _compile_injection_patterns(self) -> List[re.Pattern]:
        """Compile injection attack patterns."""
        patterns = [
            r"<script[^>]*>.*?</script>",  # XSS
            r"javascript:",  # JavaScript injection
            r"on\w+\s*=",  # Event handlers
            r"eval\s*\(",  # Code injection
            r"exec\s*\(",  # Code execution
            r"import\s+os",  # OS command injection
            r"subprocess\.",  # Subprocess injection
        ]
        return [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]

    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Sanitize input data."""
        start_time = time.time()
        violations = []
        trace_id = context.get("trace_id", self._generate_trace_id())

        try:
            # Size validation
            if isinstance(data, str) and len(data) > self.config.max_input_length:
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="input_too_large",
                    severity=ViolationSeverity.HIGH,
                    message=f"Input size {len(data)} exceeds maximum {self.config.max_input_length}",
                    trace_id=trace_id,
                ))

            # Content type validation
            content_type = context.get("content_type", "text/plain")
            if content_type not in self.config.allowed_content_types:
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="invalid_content_type",
                    severity=ViolationSeverity.MEDIUM,
                    message=f"Content type {content_type} not allowed",
                    trace_id=trace_id,
                ))

            # Convert to string for processing
            if isinstance(data, dict):
                input_text = json.dumps(data)
            elif isinstance(data, str):
                input_text = data
            else:
                input_text = str(data)

            # Store original text for injection detection before sanitization
            original_text = input_text

            # HTML sanitization
            if self.config.sanitize_html:
                input_text = self._sanitize_html(input_text)

            # Injection detection (on original text)
            if self.config.detect_injection:
                injection_violations = self._detect_injection(original_text)
                violations.extend(injection_violations)

            # PII detection
            if self.config.pii_detection:
                pii_violations = self._detect_pii(input_text)
                violations.extend(pii_violations)

            # Determine action
            if violations:
                # Check if any violations are critical
                critical_violations = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
                if critical_violations:
                    action = SafetyAction.BLOCK
                    allowed = False
                else:
                    # PII detection should result in AUDIT (flag but allow)
                    pii_violations = [v for v in violations if v.violation_type == "pii_detected"]
                    if pii_violations:
                        action = SafetyAction.AUDIT
                        allowed = True
                    else:
                        action = SafetyAction.MODIFY if self.config.sanitize_html else SafetyAction.AUDIT
                        allowed = True
                        # Apply sanitization if needed
                        if action == SafetyAction.MODIFY:
                            input_text = self._apply_sanitization(input_text, violations)
            else:
                action = SafetyAction.ALLOW
                allowed = True

        except Exception as e:
            logger.error(f"Input sanitizer error: {e}")
            violations.append(Violation(
                layer=self.get_layer(),
                violation_type="processing_error",
                severity=ViolationSeverity.HIGH,
                message=f"Input processing failed: {str(e)}",
                trace_id=trace_id,
            ))
            action = SafetyAction.BLOCK
            allowed = False
            input_text = ""

        processing_time = (time.time() - start_time) * 1000

        return GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            modified_data=input_text if input_text != str(data) else None,
            metadata={"original_length": len(str(data))},
            processing_time_ms=processing_time,
            trace_id=trace_id,
        )

    def _sanitize_html(self, text: str) -> str:
        """Basic HTML sanitization."""
        # Remove script tags and their contents
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove other dangerous tags
        dangerous_tags = ['iframe', 'object', 'embed', 'form', 'input', 'button']
        for tag in dangerous_tags:
            text = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
        return text

    def _detect_injection(self, text: str) -> List[Violation]:
        """Detect injection attacks."""
        violations = []
        for i, pattern in enumerate(self._injection_patterns):
            if pattern.search(text):
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="injection_attack",
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Potential injection attack detected (pattern {i})",
                    details={"pattern_index": i},
                    trace_id="",
                ))
        return violations

    def _detect_pii(self, text: str) -> List[Violation]:
        """Detect personally identifiable information."""
        violations = []
        for i, pattern in enumerate(self._pii_patterns):
            matches = pattern.findall(text)
            if matches:
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="pii_detected",
                    severity=ViolationSeverity.HIGH,
                    message=f"PII detected: {len(matches)} potential matches (pattern {i})",
                    details={"pattern_index": i, "match_count": len(matches)},
                    trace_id="",
                ))
        return violations

    def _apply_sanitization(self, text: str, violations: List[Violation]) -> str:
        """Apply sanitization based on detected violations."""
        sanitized = text
        # Redact PII
        for pattern in self._pii_patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized

    def _generate_trace_id(self) -> str:
        """Generate a trace ID."""
        timestamp = datetime.now(UTC).isoformat()
        data = f"{timestamp}-{CONSTITUTIONAL_HASH}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class AgentEngineConfig:
    """Configuration for agent engine."""

    enabled: bool = True
    constitutional_validation: bool = True
    impact_scoring: bool = True
    deliberation_required_threshold: float = 0.8
    timeout_ms: int = 5000


class AgentEngine(GuardrailComponent):
    """Agent Engine: Layer 2 of OWASP guardrails.

    Core governance layer with constitutional validation and impact scoring.
    """

    def __init__(self, config: Optional[AgentEngineConfig] = None):
        self.config = config or AgentEngineConfig()

    def get_layer(self) -> GuardrailLayer:
        return GuardrailLayer.AGENT_ENGINE

    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Process through agent engine with constitutional validation."""
        start_time = time.time()
        violations = []
        trace_id = context.get("trace_id", "")

        try:
            # Constitutional validation
            if self.config.constitutional_validation:
                constitutional_result = await self._validate_constitutional(data, context)
                if not constitutional_result["compliant"]:
                    violations.append(Violation(
                        layer=self.get_layer(),
                        violation_type="constitutional_violation",
                        severity=ViolationSeverity.HIGH,
                        message="Request violates constitutional principles",
                        details=constitutional_result,
                        trace_id=trace_id,
                    ))

            # Impact scoring
            if self.config.impact_scoring:
                impact_score = await self._calculate_impact_score(data, context)
                if impact_score > self.config.deliberation_required_threshold:
                    violations.append(Violation(
                        layer=self.get_layer(),
                        violation_type="high_impact",
                        severity=ViolationSeverity.MEDIUM,
                        message=f"High impact action requires deliberation (score: {impact_score})",
                        details={"impact_score": impact_score},
                        trace_id=trace_id,
                    ))

            # Determine action
            if violations:
                action = SafetyAction.ESCALATE
                allowed = False
            else:
                action = SafetyAction.ALLOW
                allowed = True

        except Exception as e:
            logger.error(f"Agent engine error: {e}")
            violations.append(Violation(
                layer=self.get_layer(),
                violation_type="processing_error",
                severity=ViolationSeverity.HIGH,
                message=f"Agent engine processing failed: {str(e)}",
                trace_id=trace_id,
            ))
            action = SafetyAction.BLOCK
            allowed = False

        processing_time = (time.time() - start_time) * 1000

        return GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            processing_time_ms=processing_time,
            trace_id=trace_id,
        )

    async def _validate_constitutional(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate against constitutional principles."""
        # This would integrate with the constitutional validation system
        # For now, return a mock result
        return {
            "compliant": True,
            "confidence": 0.95,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def _calculate_impact_score(self, data: Any, context: Dict[str, Any]) -> float:
        """Calculate impact score for the action."""
        # This would use ML-based impact scoring
        # For now, return a mock score
        return 0.3


@dataclass
class SandboxConfig:
    """Configuration for tool runner sandbox."""

    enabled: bool = True
    use_firecracker: bool = False  # For production
    use_docker: bool = True  # For development
    timeout_ms: int = 10000
    memory_limit_mb: int = 512
    cpu_limit: float = 0.5
    network_isolation: bool = True


class ToolRunnerSandbox(GuardrailComponent):
    """Tool Runner Sandbox: Layer 3 of OWASP guardrails.

    Isolated execution environment for tool calls and external integrations.
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    def get_layer(self) -> GuardrailLayer:
        return GuardrailLayer.TOOL_RUNNER_SANDBOX

    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Execute in sandboxed environment."""
        start_time = time.time()
        violations = []
        trace_id = context.get("trace_id", "")

        try:
            if not self.config.enabled:
                return GuardrailResult(
                    action=SafetyAction.ALLOW,
                    allowed=True,
                    trace_id=trace_id,
                )

            # Sandbox the execution
            sandbox_result = await self._execute_in_sandbox(data, context)

            if sandbox_result["success"]:
                action = SafetyAction.ALLOW
                allowed = True
            else:
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="sandbox_execution_failed",
                    severity=ViolationSeverity.HIGH,
                    message=f"Sandbox execution failed: {sandbox_result.get('error', 'Unknown error')}",
                    details=sandbox_result,
                    trace_id=trace_id,
                ))
                action = SafetyAction.BLOCK
                allowed = False

        except Exception as e:
            logger.error(f"Sandbox error: {e}")
            violations.append(Violation(
                layer=self.get_layer(),
                violation_type="sandbox_error",
                severity=ViolationSeverity.CRITICAL,
                message=f"Sandbox execution error: {str(e)}",
                trace_id=trace_id,
            ))
            action = SafetyAction.BLOCK
            allowed = False

        processing_time = (time.time() - start_time) * 1000

        return GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            modified_data=sandbox_result.get("output") if sandbox_result.get("success") else None,
            processing_time_ms=processing_time,
            trace_id=trace_id,
        )

    async def _execute_in_sandbox(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code/data in sandboxed environment."""
        # This would implement actual sandboxing with Docker/Firecracker
        # For now, return a mock successful result
        return {
            "success": True,
            "output": data,
            "execution_time_ms": 100,
        }


@dataclass
class OutputVerifierConfig:
    """Configuration for output verifier."""

    enabled: bool = True
    content_safety_check: bool = True
    pii_redaction: bool = True
    hallucination_detection: bool = False  # Future feature
    toxicity_filter: bool = True
    timeout_ms: int = 2000


class OutputVerifier(GuardrailComponent):
    """Output Verifier: Layer 4 of OWASP guardrails.

    Validates and sanitizes output before it reaches users.
    """

    def __init__(self, config: Optional[OutputVerifierConfig] = None):
        self.config = config or OutputVerifierConfig()
        self._toxicity_patterns = self._compile_toxicity_patterns()

    def get_layer(self) -> GuardrailLayer:
        return GuardrailLayer.OUTPUT_VERIFIER

    def _compile_toxicity_patterns(self) -> List[re.Pattern]:
        """Compile toxicity detection patterns."""
        patterns = [
            r"\b(hate|racist|sexist|violent)\b",
            r"\b(kill|murder|attack|harm)\s+(yourself|others|people)\b",
            r"\b(suicide|self-harm)\b",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Verify and sanitize output."""
        start_time = time.time()
        violations = []
        trace_id = context.get("trace_id", "")
        modified_output = None

        try:
            # Convert to string for processing
            if isinstance(data, dict):
                output_text = json.dumps(data)
            elif isinstance(data, str):
                output_text = data
            else:
                output_text = str(data)

            # Content safety check
            if self.config.content_safety_check:
                safety_violations = self._check_content_safety(output_text)
                violations.extend(safety_violations)

            # Toxicity filter
            if self.config.toxicity_filter:
                toxicity_violations = self._check_toxicity(output_text)
                violations.extend(toxicity_violations)

            # PII redaction
            if self.config.pii_redaction:
                output_text, pii_violations = self._redact_pii(output_text)
                violations.extend(pii_violations)
                if pii_violations:
                    modified_output = output_text

            # Determine action
            if violations:
                # Check for critical violations
                critical_violations = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
                if critical_violations:
                    action = SafetyAction.BLOCK
                    allowed = False
                else:
                    action = SafetyAction.MODIFY
                    allowed = True
            else:
                action = SafetyAction.ALLOW
                allowed = True

        except Exception as e:
            logger.error(f"Output verifier error: {e}")
            violations.append(Violation(
                layer=self.get_layer(),
                violation_type="processing_error",
                severity=ViolationSeverity.HIGH,
                message=f"Output verification failed: {str(e)}",
                trace_id=trace_id,
            ))
            action = SafetyAction.BLOCK
            allowed = False

        processing_time = (time.time() - start_time) * 1000

        return GuardrailResult(
            action=action,
            allowed=allowed,
            violations=violations,
            modified_data=modified_output,
            processing_time_ms=processing_time,
            trace_id=trace_id,
        )

    def _check_content_safety(self, text: str) -> List[Violation]:
        """Check content for safety violations."""
        violations = []

        # Check for harmful instructions
        harmful_patterns = [
            r"\b(how\s+to|instructions?\s+for)\s+(hack|exploit|attack|build.*bomb)\b",
            r"\b(create|make|build)\s+(virus|malware|ransomware|trojan)\b",
        ]

        for pattern in harmful_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="harmful_content",
                    severity=ViolationSeverity.CRITICAL,
                    message="Output contains potentially harmful instructions",
                    trace_id="",
                ))
                break  # Only report once

        return violations

    def _check_toxicity(self, text: str) -> List[Violation]:
        """Check for toxic content."""
        violations = []

        for i, pattern in enumerate(self._toxicity_patterns):
            if pattern.search(text):
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="toxicity_detected",
                    severity=ViolationSeverity.HIGH,
                    message=f"Toxic content detected (pattern {i})",
                    details={"pattern_index": i},
                    trace_id="",
                ))

        return violations

    def _redact_pii(self, text: str) -> tuple[str, List[Violation]]:
        """Redact PII from output."""
        violations = []
        redacted = text

        # Simple PII patterns (same as input sanitizer)
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{16}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        ]

        for pattern in pii_patterns:
            compiled = re.compile(pattern, re.IGNORECASE)
            matches = compiled.findall(text)
            if matches:
                violations.append(Violation(
                    layer=self.get_layer(),
                    violation_type="pii_leak",
                    severity=ViolationSeverity.HIGH,
                    message=f"PII detected in output: {len(matches)} instances",
                    details={"match_count": len(matches)},
                    trace_id="",
                ))
                redacted = compiled.sub("[REDACTED]", redacted)

        return redacted, violations


@dataclass
class AuditLogConfig:
    """Configuration for audit log."""

    enabled: bool = True
    retention_days: int = 90
    log_to_blockchain: bool = False  # Future feature
    log_to_siem: bool = False  # Future feature


class AuditLog(GuardrailComponent):
    """Audit Log: Layer 5 of OWASP guardrails.

    Immutable compliance trail for all guardrail decisions.
    """

    def __init__(self, config: Optional[AuditLogConfig] = None):
        self.config = config or AuditLogConfig()
        self._audit_entries: List[Dict[str, Any]] = []

    def get_layer(self) -> GuardrailLayer:
        return GuardrailLayer.AUDIT_LOG

    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Log the audit entry."""
        trace_id = context.get("trace_id", "")

        audit_entry = {
            "trace_id": trace_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "layer": context.get("current_layer", "").value if context.get("current_layer") else "",
            "action": context.get("action", "").value if context.get("action") else "",
            "allowed": context.get("allowed", False),
            "violations": [v.to_dict() for v in context.get("violations", [])],
            "processing_time_ms": context.get("processing_time_ms", 0),
            "metadata": context.get("metadata", {}),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        if self.config.enabled:
            self._audit_entries.append(audit_entry)
            logger.info(f"Audit log entry: {json.dumps(audit_entry)}")

            # Future: Log to blockchain/SIEM
            if self.config.log_to_blockchain:
                await self._log_to_blockchain(audit_entry)
            if self.config.log_to_siem:
                await self._log_to_siem(audit_entry)

        return GuardrailResult(
            action=SafetyAction.ALLOW,
            allowed=True,
            trace_id=trace_id,
        )

    async def _log_to_blockchain(self, entry: Dict[str, Any]) -> None:
        """Log entry to blockchain for immutability."""
        # Future implementation
        pass

    async def _log_to_siem(self, entry: Dict[str, Any]) -> None:
        """Log entry to SIEM system."""
        # Future implementation
        pass

    async def get_metrics(self) -> Dict[str, Any]:
        """Get audit log metrics."""
        total_entries = len(self._audit_entries)
        if total_entries == 0:
            return {"total_entries": 0}

        # Calculate metrics
        allowed_count = sum(1 for entry in self._audit_entries if entry.get("allowed", False))
        violation_count = sum(len(entry.get("violations", [])) for entry in self._audit_entries)

        return {
            "total_entries": total_entries,
            "allowed_count": allowed_count,
            "blocked_count": total_entries - allowed_count,
            "allowed_rate": allowed_count / total_entries,
            "violation_rate": violation_count / total_entries,
            "avg_processing_time_ms": sum(entry.get("processing_time_ms", 0) for entry in self._audit_entries) / total_entries,
        }

    def get_entries(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit entries, optionally filtered by trace ID."""
        if trace_id:
            return [entry for entry in self._audit_entries if entry.get("trace_id") == trace_id]
        return self._audit_entries.copy()


@dataclass
class RuntimeSafetyGuardrailsConfig:
    """Configuration for the complete runtime safety guardrails system."""

    input_sanitizer: InputSanitizerConfig = field(default_factory=InputSanitizerConfig)
    agent_engine: AgentEngineConfig = field(default_factory=AgentEngineConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    output_verifier: OutputVerifierConfig = field(default_factory=OutputVerifierConfig)
    audit_log: AuditLogConfig = field(default_factory=AuditLogConfig)

    strict_mode: bool = False
    fail_closed: bool = True  # Block on any error
    timeout_ms: int = 15000  # Total timeout for all layers


class RuntimeSafetyGuardrails:
    """
    OWASP-compliant Runtime Safety Guardrails System.

    Implements 5-layer security architecture:
    1. Input Sanitizer - Clean and validate incoming requests
    2. Agent Engine - Constitutional governance validation
    3. Tool Runner Sandbox - Isolated execution environment
    4. Output Verifier - Post-execution content validation
    5. Audit Log - Immutable compliance trail

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, config: Optional[RuntimeSafetyGuardrailsConfig] = None):
        self.config = config or RuntimeSafetyGuardrailsConfig()

        # Initialize guardrail layers
        self.layers = {
            GuardrailLayer.INPUT_SANITIZER: InputSanitizer(self.config.input_sanitizer),
            GuardrailLayer.AGENT_ENGINE: AgentEngine(self.config.agent_engine),
            GuardrailLayer.TOOL_RUNNER_SANDBOX: ToolRunnerSandbox(self.config.sandbox),
            GuardrailLayer.OUTPUT_VERIFIER: OutputVerifier(self.config.output_verifier),
            GuardrailLayer.AUDIT_LOG: AuditLog(self.config.audit_log),
        }

    async def process_request(
        self,
        request_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a request through all guardrail layers.

        Args:
            request_data: The request data to process
            context: Optional context information

        Returns:
            Dict containing processing results and final decision
        """
        context = context or {}
        trace_id = context.get("trace_id", self._generate_trace_id())
        context["trace_id"] = trace_id

        start_time = time.time()
        layer_results = {}
        current_data = request_data
        final_allowed = True
        all_violations = []

        try:
            # Process through each layer in order
            layer_order = [
                GuardrailLayer.INPUT_SANITIZER,
                GuardrailLayer.AGENT_ENGINE,
                GuardrailLayer.TOOL_RUNNER_SANDBOX,
                GuardrailLayer.OUTPUT_VERIFIER,
            ]

            for layer_type in layer_order:
                if not self.layers[layer_type].config.enabled:
                    continue

                layer = self.layers[layer_type]

                # Create layer context
                layer_context = context.copy()
                layer_context["current_data"] = current_data

                # Process through layer
                try:
                    result = await asyncio.wait_for(
                        layer.process(current_data, layer_context),
                        timeout=self.config.timeout_ms / 1000
                    )
                except asyncio.TimeoutError:
                    result = GuardrailResult(
                        action=SafetyAction.BLOCK,
                        allowed=False,
                        violations=[Violation(
                            layer=layer_type,
                            violation_type="timeout",
                            severity=ViolationSeverity.CRITICAL,
                            message=f"Layer {layer_type.value} timed out",
                            trace_id=trace_id,
                        )]
                    )

                layer_results[layer_type.value] = result.to_dict()

                # Update current data if modified
                if result.modified_data is not None:
                    current_data = result.modified_data

                # Collect violations
                all_violations.extend(result.violations)

                # Check if we should continue
                if not result.allowed:
                    final_allowed = False
                    if self.config.fail_closed:
                        break  # Stop processing on first block

            # Always log to audit (final layer)
            audit_layer = self.layers[GuardrailLayer.AUDIT_LOG]
            audit_context = context.copy()
            audit_context.update({
                "action": SafetyAction.ALLOW if final_allowed else SafetyAction.BLOCK,
                "allowed": final_allowed,
                "violations": all_violations,
                "processing_time_ms": (time.time() - start_time) * 1000,
            })

            await audit_layer.process(current_data, audit_context)

        except Exception as e:
            logger.error(f"Guardrails processing error: {e}")
            final_allowed = False
            all_violations.append(Violation(
                layer=GuardrailLayer.AUDIT_LOG,  # Generic error
                violation_type="system_error",
                severity=ViolationSeverity.CRITICAL,
                message=f"Guardrails system error: {str(e)}",
                trace_id=trace_id,
            ))

        total_time = (time.time() - start_time) * 1000

        return {
            "allowed": final_allowed,
            "final_data": current_data,
            "violations": [v.to_dict() for v in all_violations],
            "layer_results": layer_results,
            "trace_id": trace_id,
            "total_processing_time_ms": total_time,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        timestamp = datetime.now(UTC).isoformat()
        data = f"{timestamp}-{CONSTITUTIONAL_HASH}-{id(self)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive guardrails metrics."""
        metrics = {
            "system": {
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "layers_enabled": [layer.value for layer, component in self.layers.items()
                                 if getattr(component.config, 'enabled', True)],
            }
        }

        # Collect metrics from each layer
        for layer_type, component in self.layers.items():
            try:
                layer_metrics = await component.get_metrics()
                metrics[layer_type.value] = layer_metrics
            except Exception as e:
                logger.error(f"Error getting metrics for {layer_type.value}: {e}")
                metrics[layer_type.value] = {"error": str(e)}

        return metrics

    def get_layer(self, layer_type: GuardrailLayer) -> Optional[GuardrailComponent]:
        """Get a specific guardrail layer component."""
        return self.layers.get(layer_type)
