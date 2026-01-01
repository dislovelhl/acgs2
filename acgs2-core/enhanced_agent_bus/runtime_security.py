"""
ACGS-2 Enhanced Agent Bus - Runtime Security Scanner
Constitutional Hash: cdd01ef066bc6cf2

Unified runtime security scanning and validation that aggregates all security features:
- Prompt injection detection
- Tenant validation
- Permission scoping
- Constitutional hash validation
- Rate limiting checks
- Security event logging
- Anomaly detection
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

try:
    from .security.tenant_validator import TenantValidator
    from .security_helpers import detect_prompt_injection
    from .validators import validate_constitutional_hash
except ImportError:
    # Fallback for standalone usage
    detect_prompt_injection = None  # type: ignore
    TenantValidator = None  # type: ignore
    from validators import validate_constitutional_hash  # type: ignore

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events for monitoring and alerting."""

    PROMPT_INJECTION_ATTEMPT = "prompt_injection_attempt"
    TENANT_VIOLATION = "tenant_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CONSTITUTIONAL_HASH_MISMATCH = "constitutional_hash_mismatch"
    PERMISSION_DENIED = "permission_denied"
    INVALID_INPUT = "invalid_input"
    ANOMALY_DETECTED = "anomaly_detected"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


class SecuritySeverity(Enum):
    """Severity levels for security events."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Represents a security event for logging and alerting."""

    event_type: SecurityEventType
    severity: SecuritySeverity
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "runtime_security_scanner"
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class SecurityScanResult:
    """Result of a comprehensive security scan."""

    is_secure: bool = True
    events: List[SecurityEvent] = field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None
    scan_duration_ms: float = 0.0
    checks_performed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def add_event(self, event: SecurityEvent) -> None:
        """Add a security event to the result."""
        self.events.append(event)
        if event.severity in (SecuritySeverity.HIGH, SecuritySeverity.CRITICAL):
            self.is_secure = False

    def add_blocking_event(self, event: SecurityEvent, reason: str) -> None:
        """Add a blocking security event."""
        self.add_event(event)
        self.blocked = True
        self.block_reason = reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_secure": self.is_secure,
            "events": [e.to_dict() for e in self.events],
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "scan_duration_ms": self.scan_duration_ms,
            "checks_performed": self.checks_performed,
            "warnings": self.warnings,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class RuntimeSecurityConfig:
    """Configuration for runtime security scanning."""

    # Enable/disable specific checks
    enable_prompt_injection_detection: bool = True
    enable_tenant_validation: bool = True
    enable_rate_limit_check: bool = True
    enable_constitutional_validation: bool = True
    enable_anomaly_detection: bool = True
    enable_input_sanitization: bool = True

    # Thresholds
    rate_limit_qps: int = 100
    rate_limit_burst: int = 200
    max_input_length: int = 100000
    max_nested_depth: int = 50

    # Anomaly detection settings
    anomaly_window_seconds: int = 60
    anomaly_threshold_events: int = 10

    # Security event retention
    event_retention_seconds: int = 3600
    max_events_retained: int = 10000

    # Fail-closed behavior (deny on error)
    fail_closed: bool = True


class RuntimeSecurityScanner:
    """
    Unified runtime security scanner for ACGS-2.

    Provides comprehensive runtime security scanning and validation by
    aggregating all security features into a single, easy-to-use interface.

    Features:
    - Prompt injection detection
    - Tenant ID validation
    - Rate limiting checks
    - Constitutional hash validation
    - Input sanitization
    - Anomaly detection
    - Security event logging

    Constitutional Hash: cdd01ef066bc6cf2
    """

    # Additional suspicious patterns beyond prompt injection
    SUSPICIOUS_PATTERNS = [
        r"<script[^>]*>",  # XSS attempts
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"(?:union|select|insert|update|delete|drop)\s+",  # SQL injection
        r"\.\./",  # Path traversal
        r"\\x[0-9a-fA-F]{2}",  # Hex escapes
        r"\\u[0-9a-fA-F]{4}",  # Unicode escapes used maliciously
        r"base64_decode",  # Base64 decode attempts
        r"eval\s*\(",  # Eval calls
        r"exec\s*\(",  # Exec calls
        r"__import__",  # Python import injection
        r"subprocess\.",  # Subprocess access
        r"os\.system",  # OS command execution
    ]

    def __init__(self, config: Optional[RuntimeSecurityConfig] = None):
        """
        Initialize the runtime security scanner.

        Args:
            config: Security configuration (uses defaults if not provided)
        """
        self.config = config or RuntimeSecurityConfig()
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
        self._event_buffer: List[SecurityEvent] = []
        self._rate_counters: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

        # Metrics
        self._total_scans = 0
        self._blocked_requests = 0
        self._events_detected = 0

        logger.info(
            f"RuntimeSecurityScanner initialized with constitutional hash: {CONSTITUTIONAL_HASH}"
        )

    async def scan(
        self,
        content: Any,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        constitutional_hash: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SecurityScanResult:
        """
        Perform comprehensive security scan on content.

        Args:
            content: Content to scan (string, dict, or any)
            tenant_id: Tenant identifier for validation
            agent_id: Agent identifier for tracking
            constitutional_hash: Constitutional hash to validate
            context: Additional context for scanning

        Returns:
            SecurityScanResult with scan results and any events
        """
        start_time = time.monotonic()
        result = SecurityScanResult()
        context = context or {}

        try:
            # Track scan
            self._total_scans += 1

            # 1. Constitutional hash validation
            if self.config.enable_constitutional_validation and constitutional_hash:
                result.checks_performed.append("constitutional_hash_validation")
                await self._check_constitutional_hash(
                    result, constitutional_hash, tenant_id, agent_id
                )

            # 2. Tenant validation
            if self.config.enable_tenant_validation and tenant_id is not None:
                result.checks_performed.append("tenant_validation")
                await self._check_tenant(result, tenant_id, agent_id)

            # 3. Rate limiting
            if self.config.enable_rate_limit_check:
                result.checks_performed.append("rate_limit_check")
                await self._check_rate_limit(result, tenant_id, agent_id)

            # 4. Input sanitization and validation
            if self.config.enable_input_sanitization:
                result.checks_performed.append("input_sanitization")
                await self._check_input(result, content, tenant_id, agent_id)

            # 5. Prompt injection detection
            if self.config.enable_prompt_injection_detection:
                result.checks_performed.append("prompt_injection_detection")
                await self._check_prompt_injection(result, content, tenant_id, agent_id)

            # 6. Suspicious pattern detection
            result.checks_performed.append("suspicious_pattern_detection")
            await self._check_suspicious_patterns(result, content, tenant_id, agent_id)

            # 7. Anomaly detection
            if self.config.enable_anomaly_detection:
                result.checks_performed.append("anomaly_detection")
                await self._check_anomalies(result, tenant_id, agent_id)

        except Exception as e:
            logger.error(f"Security scan error: {e}")
            if self.config.fail_closed:
                result.blocked = True
                result.block_reason = f"Security scan error: {str(e)}"
                result.is_secure = False

        # Calculate scan duration
        result.scan_duration_ms = (time.monotonic() - start_time) * 1000

        # Update metrics
        if result.blocked:
            self._blocked_requests += 1
        self._events_detected += len(result.events)

        # Store events
        await self._store_events(result.events)

        return result

    async def _check_constitutional_hash(
        self,
        result: SecurityScanResult,
        hash_value: str,
        tenant_id: Optional[str],
        agent_id: Optional[str],
    ) -> None:
        """Validate constitutional hash."""
        validation = validate_constitutional_hash(hash_value)
        if not validation.is_valid:
            event = SecurityEvent(
                event_type=SecurityEventType.CONSTITUTIONAL_HASH_MISMATCH,
                severity=SecuritySeverity.CRITICAL,
                message="Constitutional hash mismatch detected",
                tenant_id=tenant_id,
                agent_id=agent_id,
                metadata={"provided_hash_prefix": hash_value[:8] if hash_value else ""},
            )
            result.add_blocking_event(event, "Constitutional hash validation failed")

    async def _check_tenant(
        self,
        result: SecurityScanResult,
        tenant_id: str,
        agent_id: Optional[str],
    ) -> None:
        """Validate tenant ID."""
        if TenantValidator is None:
            result.warnings.append("TenantValidator not available")
            return

        normalized, is_valid = TenantValidator.sanitize_and_validate(tenant_id)
        if not is_valid:
            event = SecurityEvent(
                event_type=SecurityEventType.TENANT_VIOLATION,
                severity=SecuritySeverity.HIGH,
                message="Invalid tenant ID format",
                tenant_id=tenant_id,
                agent_id=agent_id,
                metadata={"normalized": normalized},
            )
            result.add_blocking_event(event, "Tenant validation failed")

    async def _check_rate_limit(
        self,
        result: SecurityScanResult,
        tenant_id: Optional[str],
        agent_id: Optional[str],
    ) -> None:
        """Check rate limiting."""
        key = f"{tenant_id or 'global'}:{agent_id or 'unknown'}"
        now = time.monotonic()

        async with self._lock:
            if key not in self._rate_counters:
                self._rate_counters[key] = []

            # Clean old entries
            window_start = now - 1.0  # 1 second window
            self._rate_counters[key] = [t for t in self._rate_counters[key] if t > window_start]

            # Check rate
            current_rate = len(self._rate_counters[key])
            if current_rate >= self.config.rate_limit_qps:
                event = SecurityEvent(
                    event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                    severity=SecuritySeverity.MEDIUM,
                    message=f"Rate limit exceeded: {current_rate} QPS",
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    metadata={
                        "current_rate": current_rate,
                        "limit": self.config.rate_limit_qps,
                    },
                )
                result.add_event(event)
                result.warnings.append(f"Rate limit exceeded: {current_rate} QPS")

            # Record this request
            self._rate_counters[key].append(now)

    async def _check_input(
        self,
        result: SecurityScanResult,
        content: Any,
        tenant_id: Optional[str],
        agent_id: Optional[str],
    ) -> None:
        """Validate and sanitize input."""
        content_str = str(content) if content is not None else ""

        # Check length
        if len(content_str) > self.config.max_input_length:
            event = SecurityEvent(
                event_type=SecurityEventType.INVALID_INPUT,
                severity=SecuritySeverity.MEDIUM,
                message="Input exceeds maximum length",
                tenant_id=tenant_id,
                agent_id=agent_id,
                metadata={
                    "length": len(content_str),
                    "max_length": self.config.max_input_length,
                },
            )
            result.add_event(event)
            result.warnings.append("Input exceeds maximum length")

        # Check nested depth for dicts
        if isinstance(content, dict):
            depth = self._get_nested_depth(content)
            if depth > self.config.max_nested_depth:
                event = SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    severity=SecuritySeverity.MEDIUM,
                    message="Input exceeds maximum nesting depth",
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    metadata={
                        "depth": depth,
                        "max_depth": self.config.max_nested_depth,
                    },
                )
                result.add_event(event)
                result.warnings.append("Input exceeds maximum nesting depth")

    async def _check_prompt_injection(
        self,
        result: SecurityScanResult,
        content: Any,
        tenant_id: Optional[str],
        agent_id: Optional[str],
    ) -> None:
        """Check for prompt injection attempts."""
        if detect_prompt_injection is None:
            result.warnings.append("Prompt injection detection not available")
            return

        content_str = str(content) if content is not None else ""
        if detect_prompt_injection(content_str):
            event = SecurityEvent(
                event_type=SecurityEventType.PROMPT_INJECTION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                message="Potential prompt injection attempt detected",
                tenant_id=tenant_id,
                agent_id=agent_id,
                metadata={"content_length": len(content_str)},
            )
            result.add_blocking_event(event, "Prompt injection detected")

    async def _check_suspicious_patterns(
        self,
        result: SecurityScanResult,
        content: Any,
        tenant_id: Optional[str],
        agent_id: Optional[str],
    ) -> None:
        """Check for suspicious patterns."""
        content_str = str(content) if content is not None else ""

        for pattern in self._compiled_patterns:
            if pattern.search(content_str):
                event = SecurityEvent(
                    event_type=SecurityEventType.SUSPICIOUS_PATTERN,
                    severity=SecuritySeverity.MEDIUM,
                    message=f"Suspicious pattern detected: {pattern.pattern[:30]}...",
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    metadata={"pattern": pattern.pattern},
                )
                result.add_event(event)

    async def _check_anomalies(
        self,
        result: SecurityScanResult,
        tenant_id: Optional[str],
        agent_id: Optional[str],
    ) -> None:
        """Check for security anomalies based on event history."""
        now = datetime.now(timezone.utc)
        window_start = now.timestamp() - self.config.anomaly_window_seconds

        # Count recent events for this tenant/agent
        recent_events = [
            e
            for e in self._event_buffer
            if e.timestamp.timestamp() > window_start
            and e.tenant_id == tenant_id
            and (agent_id is None or e.agent_id == agent_id)
        ]

        if len(recent_events) >= self.config.anomaly_threshold_events:
            event = SecurityEvent(
                event_type=SecurityEventType.ANOMALY_DETECTED,
                severity=SecuritySeverity.HIGH,
                message=f"Anomaly detected: {len(recent_events)} events in {self.config.anomaly_window_seconds}s",
                tenant_id=tenant_id,
                agent_id=agent_id,
                metadata={
                    "event_count": len(recent_events),
                    "window_seconds": self.config.anomaly_window_seconds,
                    "threshold": self.config.anomaly_threshold_events,
                },
            )
            result.add_event(event)

    def _get_nested_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate nested depth of an object."""
        if current_depth > self.config.max_nested_depth:
            return current_depth

        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_nested_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, (list, tuple)):
            if not obj:
                return current_depth
            return max(self._get_nested_depth(v, current_depth + 1) for v in obj)
        return current_depth

    async def _store_events(self, events: List[SecurityEvent]) -> None:
        """Store security events for anomaly detection and auditing."""
        async with self._lock:
            self._event_buffer.extend(events)

            # Trim old events
            if len(self._event_buffer) > self.config.max_events_retained:
                self._event_buffer = self._event_buffer[-self.config.max_events_retained :]

            # Remove expired events
            cutoff = datetime.now(timezone.utc).timestamp() - self.config.event_retention_seconds
            self._event_buffer = [e for e in self._event_buffer if e.timestamp.timestamp() > cutoff]

    def get_metrics(self) -> Dict[str, Any]:
        """Get security scanner metrics."""
        return {
            "total_scans": self._total_scans,
            "blocked_requests": self._blocked_requests,
            "events_detected": self._events_detected,
            "block_rate": (
                self._blocked_requests / self._total_scans if self._total_scans > 0 else 0.0
            ),
            "events_buffered": len(self._event_buffer),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def get_recent_events(
        self,
        limit: int = 100,
        severity_filter: Optional[SecuritySeverity] = None,
        event_type_filter: Optional[SecurityEventType] = None,
    ) -> List[SecurityEvent]:
        """Get recent security events with optional filtering."""
        events = self._event_buffer[-limit:]

        if severity_filter:
            events = [e for e in events if e.severity == severity_filter]

        if event_type_filter:
            events = [e for e in events if e.event_type == event_type_filter]

        return events


# Global scanner instance
_scanner: Optional[RuntimeSecurityScanner] = None


def get_runtime_security_scanner(
    config: Optional[RuntimeSecurityConfig] = None,
) -> RuntimeSecurityScanner:
    """Get or create the global runtime security scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = RuntimeSecurityScanner(config)
    return _scanner


async def scan_content(
    content: Any,
    tenant_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    constitutional_hash: Optional[str] = None,
) -> SecurityScanResult:
    """
    Convenience function to perform a security scan.

    Args:
        content: Content to scan
        tenant_id: Tenant identifier
        agent_id: Agent identifier
        constitutional_hash: Constitutional hash to validate

    Returns:
        SecurityScanResult with scan results
    """
    scanner = get_runtime_security_scanner()
    return await scanner.scan(
        content=content,
        tenant_id=tenant_id,
        agent_id=agent_id,
        constitutional_hash=constitutional_hash,
    )


__all__ = [
    "CONSTITUTIONAL_HASH",
    "RuntimeSecurityConfig",
    "RuntimeSecurityScanner",
    "SecurityEvent",
    "SecurityEventType",
    "SecurityScanResult",
    "SecuritySeverity",
    "get_runtime_security_scanner",
    "scan_content",
]
