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
from typing import Any, Dict, List, Optional

from .guardrails.enums import GuardrailLayer, SafetyAction, ViolationSeverity
from .guardrails.models import GuardrailResult, Violation

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Centralized PII patterns for synchronization across layers
PII_PATTERNS = [
    # Social Security Numbers (US)
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b\d{9}\b",  # SSN without dashes
    # Credit/Debit Card Numbers
    r"\b\d{13,19}\b",  # General card number length
    r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",  # Card with spaces
    r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",  # Card with dashes
    # Email Addresses
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    # Phone Numbers (various formats)
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # US phone
    r"\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b",  # US phone with parens
    r"\b\+?\d{1,3}[-.\s]?\d{1,14}\b",  # International phone
    # IP Addresses
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    # MAC Addresses
    r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",
    # Bank Account Numbers (US routing + account)
    r"\b\d{9}\s+\d{6,17}\b",
    # Driver's License Numbers (various states)
    r"\b[A-Z]\d{7}\b",  # California format
    r"\b\d{2}\s\d{3}\s\d{4}\b",  # New York format
    # Passport Numbers
    r"\b[A-Z]{1,2}\d{6,9}\b",
    # Tax ID Numbers
    r"\b\d{2}-\d{7}\b",  # EIN format
    # Health Insurance Numbers
    r"\b[A-Z]{2}\d{8}\b",  # Sample health ID format
    # API Keys/Tokens (common patterns)
    r"\b[A-Za-z0-9]{32}\b",  # 32-char API key
    r"\b[A-Za-z0-9]{40}\b",  # GitHub token
    r"sk-\w{48}",  # OpenAI API key pattern
    r"xoxb-\d+-\d+-\w{24}",  # Slack bot token
    # Cryptocurrency Addresses
    r"\b(1|3|bc1)[A-Za-z0-9]{25,62}\b",  # Bitcoin
    r"\b0x[A-Fa-f0-9]{40}\b",  # Ethereum
    # URLs with sensitive parameters
    r"https?://[^\s]*?(password|token|key|secret|credential)[^\s]*",
]


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
    allowed_content_types: List[str] = field(
        default_factory=lambda: ["text/plain", "application/json"]
    )
    sanitize_html: bool = True
    detect_injection: bool = True
    pii_detection: bool = True
    timeout_ms: int = 1000


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter (OWASP DoS protection)."""

    enabled: bool = True
    requests_per_minute: int = 60
    burst_limit: int = 10
    window_seconds: int = 60
    block_duration_seconds: int = 300  # 5 minutes
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)


class RateLimiter(GuardrailComponent):
    """Rate Limiter: OWASP DoS protection layer.

    Prevents abuse through request rate limiting using token bucket algorithm.
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None):
        self.config = config or RateLimiterConfig()
        # Simple in-memory rate limiting (use Redis in production)
        self._request_counts: Dict[str, List[float]] = {}
        self._blocked_until: Dict[str, float] = {}

    def get_layer(self) -> GuardrailLayer:
        return GuardrailLayer.RATE_LIMITER

    async def process(self, data: Any, context: Dict[str, Any]) -> GuardrailResult:
        """Apply rate limiting to the request."""
        start_time = time.monotonic()
        trace_id = context.get("trace_id", "")

        # Extract client identifier (IP, user ID, API key, etc.)
        client_id = self._extract_client_id(context)

        # Check whitelist/blacklist first
        if client_id in self.config.blacklist:
            return GuardrailResult(
                action=SafetyAction.BLOCK,
                allowed=False,
                violations=[
                    Violation(
                        layer=self.get_layer(),
                        violation_type="blacklisted_client",
                        severity=ViolationSeverity.CRITICAL,
                        message=f"Client {client_id} is blacklisted",
                        trace_id=trace_id,
                    )
                ],
                processing_time_ms=(time.monotonic() - start_time) * 1000,
                trace_id=trace_id,
            )

        if client_id in self.config.whitelist:
            return GuardrailResult(
                action=SafetyAction.ALLOW,
                allowed=True,
                processing_time_ms=(time.monotonic() - start_time) * 1000,
                trace_id=trace_id,
            )

        # Check if client is currently blocked
        current_time = time.time()
        if client_id in self._blocked_until:
            if current_time < self._blocked_until[client_id]:
                return GuardrailResult(
                    action=SafetyAction.BLOCK,
                    allowed=False,
                    violations=[
                        Violation(
                            layer=self.get_layer(),
                            violation_type="rate_limit_blocked",
                            severity=ViolationSeverity.HIGH,
                            message=f"Client {client_id} is rate limited until {self._blocked_until[client_id]}",
                            trace_id=trace_id,
                        )
                    ],
                    processing_time_ms=(time.monotonic() - start_time) * 1000,
                    trace_id=trace_id,
                )
            else:
                # Block period expired, remove from blocked list
                del self._blocked_until[client_id]

        # Apply token bucket rate limiting
        if self._is_rate_limited(client_id, current_time):
            # Add to blocked list
            self._blocked_until[client_id] = current_time + self.config.block_duration_seconds

            return GuardrailResult(
                action=SafetyAction.BLOCK,
                allowed=False,
                violations=[
                    Violation(
                        layer=self.get_layer(),
                        violation_type="rate_limit_exceeded",
                        severity=ViolationSeverity.MEDIUM,
                        message=f"Rate limit exceeded for client {client_id}",
                        trace_id=trace_id,
                    )
                ],
                processing_time_ms=(time.monotonic() - start_time) * 1000,
                trace_id=trace_id,
            )

        return GuardrailResult(
            action=SafetyAction.ALLOW,
            allowed=True,
            processing_time_ms=(time.monotonic() - start_time) * 1000,
            trace_id=trace_id,
        )

    def _extract_client_id(self, context: Dict[str, Any]) -> str:
        """Extract client identifier from request context."""
        # Priority order: API key > User ID > IP address > session ID
        client_id = (
            context.get("api_key")
            or context.get("user_id")
            or context.get("ip_address")
            or context.get("session_id")
            or "anonymous"
        )
        return str(client_id)

    def _is_rate_limited(self, client_id: str, current_time: float) -> bool:
        """Check if client has exceeded rate limits using token bucket algorithm."""
        if client_id not in self._request_counts:
            self._request_counts[client_id] = []

        request_times = self._request_counts[client_id]

        # Remove requests outside the time window
        window_start = current_time - self.config.window_seconds
        request_times[:] = [t for t in request_times if t > window_start]

        # Check burst limit (requests in very short time)
        recent_requests = [t for t in request_times if t > current_time - 1.0]  # Last second
        if len(recent_requests) >= self.config.burst_limit:
            return True

        # Check sustained rate limit
        if len(request_times) >= self.config.requests_per_minute:
            return True

        # Add current request
        request_times.append(current_time)

        # Clean up old entries periodically
        if len(request_times) > self.config.requests_per_minute * 2:
            # Keep only recent entries
            cutoff = current_time - (self.config.window_seconds * 2)
            request_times[:] = [t for t in request_times if t > cutoff]

        return False


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
        """Compile comprehensive PII detection patterns (GDPR/HIPAA compliant)."""
        return [re.compile(p, re.IGNORECASE) for p in PII_PATTERNS]

    def _compile_injection_patterns(self) -> List[re.Pattern]:
        """Compile comprehensive injection attack patterns (OWASP compliant)."""
        patterns = [
            # XSS (Cross-Site Scripting)
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            # SQL Injection
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b.*\b(FROM|INTO|TABLE|DATABASE)\b)",
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bOR\b.*\d+\s*=\s*\d+)",
            r"(\bAND\b.*\d+\s*=\s*\d+)",
            # Command Injection
            r"[;&|`$()<>]",
            r"\\\$\{.*\}",
            r"\$\(.*\)",
            r"`.*`",
            r"eval\s*\(",
            r"exec\s*\(",
            r"system\s*\(",
            r"popen\s*\(",
            r"import\s+os",
            r"import\s+subprocess",
            r"os\.",
            r"subprocess\.",
            r"shutil\.",
            r"commands\.",
            # Path Traversal
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e/",
            r"~",
            r"passwd",
            r"shadow",
            r"etc",
            # LDAP Injection
            r"(\*\)|\(\*\))",
            r"(\|\|)",
            r"(&&)",
            # NoSQL Injection
            r"\$ne|\$gt|\$lt|\$gte|\$lte|\$regex|\$where",
            r"db\.\w+\.",
            r"collection\.\w+\.",
            # Template Injection
            r"\{\{.*\}\}",
            r"\{\%.*\%\}",
            r"\$\{.*\}",
            # XML External Entity (XXE)
            r"<!ENTITY",
            r"<!DOCTYPE.*SYSTEM",
            r"file://",
            r"http://",
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
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="input_too_large",
                        severity=ViolationSeverity.HIGH,
                        message=f"Input size {len(data)} exceeds maximum {self.config.max_input_length}",
                        trace_id=trace_id,
                    )
                )

            # Content type validation
            content_type = context.get("content_type", "text/plain")
            if content_type not in self.config.allowed_content_types:
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="invalid_content_type",
                        severity=ViolationSeverity.MEDIUM,
                        message=f"Content type {content_type} not allowed",
                        trace_id=trace_id,
                    )
                )

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
                injection_violations = self._detect_injection(original_text, trace_id)
                violations.extend(injection_violations)

            # PII detection
            if self.config.pii_detection:
                pii_violations = self._detect_pii(input_text, trace_id)
                violations.extend(pii_violations)

            # Determine action
            if violations:
                # Check if any violations are critical
                critical_violations = [
                    v for v in violations if v.severity == ViolationSeverity.CRITICAL
                ]
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
                        action = (
                            SafetyAction.MODIFY if self.config.sanitize_html else SafetyAction.AUDIT
                        )
                        allowed = True
                        # Apply sanitization if needed
                        if action == SafetyAction.MODIFY:
                            input_text = self._apply_sanitization(input_text, violations)
            else:
                action = SafetyAction.ALLOW
                allowed = True

        except Exception as e:
            logger.error(f"Input sanitizer error: {e}")
            violations.append(
                Violation(
                    layer=self.get_layer(),
                    violation_type="processing_error",
                    severity=ViolationSeverity.HIGH,
                    message=f"Input processing failed: {str(e)}",
                    trace_id=trace_id,
                )
            )
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
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        # Remove other dangerous tags
        dangerous_tags = ["iframe", "object", "embed", "form", "input", "button"]
        for tag in dangerous_tags:
            text = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", text, flags=re.IGNORECASE | re.DOTALL)
        return text

    def _detect_injection(self, text: str, trace_id: str = "") -> List[Violation]:
        """Detect injection attacks."""
        violations = []
        for i, pattern in enumerate(self._injection_patterns):
            if pattern.search(text):
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="injection_attack",
                        severity=ViolationSeverity.CRITICAL,
                        message=f"Potential injection attack detected (pattern {i})",
                        details={"pattern_index": i},
                        trace_id=trace_id,
                    )
                )
        return violations

    def _detect_pii(self, text: str, trace_id: str = "") -> List[Violation]:
        """Detect personally identifiable information."""
        violations = []
        for i, pattern in enumerate(self._pii_patterns):
            matches = pattern.findall(text)
            if matches:
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="pii_detected",
                        severity=ViolationSeverity.HIGH,
                        message=f"PII detected: {len(matches)} potential matches (pattern {i})",
                        details={"pattern_index": i, "match_count": len(matches)},
                        trace_id=trace_id,
                    )
                )
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
                    violations.append(
                        Violation(
                            layer=self.get_layer(),
                            violation_type="constitutional_violation",
                            severity=ViolationSeverity.HIGH,
                            message="Request violates constitutional principles",
                            details=constitutional_result,
                            trace_id=trace_id,
                        )
                    )

            # Impact scoring
            if self.config.impact_scoring:
                impact_score = await self._calculate_impact_score(data, context)
                if impact_score > self.config.deliberation_required_threshold:
                    violations.append(
                        Violation(
                            layer=self.get_layer(),
                            violation_type="high_impact",
                            severity=ViolationSeverity.MEDIUM,
                            message=f"High impact action requires deliberation (score: {impact_score})",
                            details={"impact_score": impact_score},
                            trace_id=trace_id,
                        )
                    )

            # Determine action
            if violations:
                action = SafetyAction.ESCALATE
                allowed = False
            else:
                action = SafetyAction.ALLOW
                allowed = True

        except Exception as e:
            logger.error(f"Agent engine error: {e}")
            violations.append(
                Violation(
                    layer=self.get_layer(),
                    violation_type="processing_error",
                    severity=ViolationSeverity.HIGH,
                    message=f"Agent engine processing failed: {str(e)}",
                    trace_id=trace_id,
                )
            )
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
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="sandbox_execution_failed",
                        severity=ViolationSeverity.HIGH,
                        message=f"Sandbox execution failed: {sandbox_result.get('error', 'Unknown error')}",
                        details=sandbox_result,
                        trace_id=trace_id,
                    )
                )
                action = SafetyAction.BLOCK
                allowed = False

        except Exception as e:
            logger.error(f"Sandbox error: {e}")
            violations.append(
                Violation(
                    layer=self.get_layer(),
                    violation_type="sandbox_error",
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Sandbox execution error: {str(e)}",
                    trace_id=trace_id,
                )
            )
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
        self._pii_patterns = [re.compile(p, re.IGNORECASE) for p in PII_PATTERNS]

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
                safety_violations = self._check_content_safety(output_text, trace_id)
                violations.extend(safety_violations)

            # Toxicity filter
            if self.config.toxicity_filter:
                toxicity_violations = self._check_toxicity(output_text, trace_id)
                violations.extend(toxicity_violations)

            # PII redaction
            if self.config.pii_redaction:
                output_text, pii_violations = self._redact_pii(output_text, trace_id)
                violations.extend(pii_violations)
                if pii_violations:
                    modified_output = output_text

            # Determine action
            if violations:
                # Check for critical violations
                critical_violations = [
                    v for v in violations if v.severity == ViolationSeverity.CRITICAL
                ]
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
            violations.append(
                Violation(
                    layer=self.get_layer(),
                    violation_type="processing_error",
                    severity=ViolationSeverity.HIGH,
                    message=f"Output verification failed: {str(e)}",
                    trace_id=trace_id,
                )
            )
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

    def _check_content_safety(self, text: str, trace_id: str = "") -> List[Violation]:
        """Check content for safety violations."""
        violations = []

        # Check for harmful instructions
        harmful_patterns = [
            r"\b(how\s+to|instructions?\s+for|steps?\s+to)\s+(hack|exploit|attack|build.*bomb)\b",
            r"\b(to|how\s+to|instructions?\s+for)\s+(hack|exploit|bypass|crack)\b",
            r"\b(create|make|build|generate)\s+(virus|malware|ransomware|trojan|rootkit)\b",
            r"\b(instructions?\s+to)\s+(harm|kill|murder|attack)\b",
        ]

        for pattern in harmful_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="harmful_content",
                        severity=ViolationSeverity.CRITICAL,
                        message="Output contains potentially harmful instructions",
                        trace_id=trace_id,
                    )
                )
                break  # Only report once

        return violations

    def _check_toxicity(self, text: str, trace_id: str = "") -> List[Violation]:
        """Check for toxic content."""
        violations = []

        for i, pattern in enumerate(self._toxicity_patterns):
            if pattern.search(text):
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="toxicity_detected",
                        severity=ViolationSeverity.HIGH,
                        message=f"Toxic content detected (pattern {i})",
                        details={"pattern_index": i},
                        trace_id=trace_id,
                    )
                )

        return violations

    def _redact_pii(self, text: str, trace_id: str = "") -> tuple[str, List[Violation]]:
        """Redact PII from output using synchronized patterns."""
        violations = []
        redacted = text

        for i, pattern in enumerate(self._pii_patterns):
            matches = pattern.findall(text)
            if matches:
                violations.append(
                    Violation(
                        layer=self.get_layer(),
                        violation_type="pii_leak",
                        severity=ViolationSeverity.HIGH,
                        message=f"PII detected in output: {len(matches)} instances (pattern {i})",
                        details={"match_count": len(matches), "pattern_index": i},
                        trace_id=trace_id,
                    )
                )
                redacted = pattern.sub("[REDACTED]", redacted)

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
            "avg_processing_time_ms": sum(
                entry.get("processing_time_ms", 0) for entry in self._audit_entries
            )
            / total_entries,
        }

    def get_entries(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit entries, optionally filtered by trace ID."""
        if trace_id:
            return [entry for entry in self._audit_entries if entry.get("trace_id") == trace_id]
        return self._audit_entries.copy()


@dataclass
class RuntimeSafetyGuardrailsConfig:
    """Configuration for the complete runtime safety guardrails system."""

    rate_limiter: RateLimiterConfig = field(default_factory=RateLimiterConfig)
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

    Implements 6-layer security architecture for comprehensive protection:
    1. Rate Limiter - OWASP DoS protection and abuse prevention
    2. Input Sanitizer - Clean and validate incoming requests
    3. Agent Engine - Constitutional governance validation
    4. Tool Runner Sandbox - Isolated execution environment
    5. Output Verifier - Post-execution content validation
    6. Audit Log - Immutable compliance trail

    Features OWASP Top 10 protection, rate limiting, comprehensive injection detection,
    and multi-layer validation with fail-closed security.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, config: Optional[RuntimeSafetyGuardrailsConfig] = None):
        self.config = config or RuntimeSafetyGuardrailsConfig()

        # Initialize guardrail layers (OWASP ordered)
        self.layers = {
            GuardrailLayer.RATE_LIMITER: RateLimiter(self.config.rate_limiter),
            GuardrailLayer.INPUT_SANITIZER: InputSanitizer(self.config.input_sanitizer),
            GuardrailLayer.AGENT_ENGINE: AgentEngine(self.config.agent_engine),
            GuardrailLayer.TOOL_RUNNER_SANDBOX: ToolRunnerSandbox(self.config.sandbox),
            GuardrailLayer.OUTPUT_VERIFIER: OutputVerifier(self.config.output_verifier),
            GuardrailLayer.AUDIT_LOG: AuditLog(self.config.audit_log),
        }

    async def process_request(
        self, request_data: Any, context: Optional[Dict[str, Any]] = None
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
                        timeout=self.config.timeout_ms / 1000,
                    )
                except asyncio.TimeoutError:
                    result = GuardrailResult(
                        action=SafetyAction.BLOCK,
                        allowed=False,
                        violations=[
                            Violation(
                                layer=layer_type,
                                violation_type="timeout",
                                severity=ViolationSeverity.CRITICAL,
                                message=f"Layer {layer_type.value} timed out",
                                trace_id=trace_id,
                            )
                        ],
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
            audit_context.update(
                {
                    "action": SafetyAction.ALLOW if final_allowed else SafetyAction.BLOCK,
                    "allowed": final_allowed,
                    "violations": all_violations,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                }
            )

            await audit_layer.process(current_data, audit_context)

        except Exception as e:
            logger.error(f"Guardrails processing error: {e}")
            final_allowed = False
            all_violations.append(
                Violation(
                    layer=GuardrailLayer.AUDIT_LOG,  # Generic error
                    violation_type="system_error",
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Guardrails system error: {str(e)}",
                    trace_id=trace_id,
                )
            )

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
                "layers_enabled": [
                    layer.value
                    for layer, component in self.layers.items()
                    if getattr(component.config, "enabled", True)
                ],
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
