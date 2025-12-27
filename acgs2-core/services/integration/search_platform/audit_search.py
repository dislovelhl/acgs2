"""
Audit Trail Search Service

Service for searching audit logs and compliance records using the
Universal Search Platform for high-performance log analysis.

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .client import SearchPlatformClient, SearchPlatformConfig
from .models import (
    SearchDomain,
    SearchMatch,
    SearchOptions,
    SearchResponse,
    SearchScope,
    TimeRange,
)

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    GOVERNANCE_DECISION = "governance_decision"
    CONSTITUTIONAL_CHECK = "constitutional_check"
    POLICY_VIOLATION = "policy_violation"
    ACCESS_ATTEMPT = "access_attempt"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    SYSTEM_ERROR = "system_error"
    USER_ACTION = "user_action"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AuditEvent:
    """Parsed audit event from search results."""
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    source: str
    message: str
    file: str
    line_number: int
    raw_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_match(cls, match: SearchMatch) -> Optional["AuditEvent"]:
        """Parse an audit event from a search match."""
        try:
            content = match.line_content

            # Try to extract timestamp
            timestamp = cls._extract_timestamp(content)

            # Try to extract event type
            event_type = cls._extract_event_type(content)

            # Try to extract severity
            severity = cls._extract_severity(content)

            # Extract source (usually in brackets or after a prefix)
            source = cls._extract_source(content)

            # Extract the message
            message = cls._extract_message(content)

            return cls(
                timestamp=timestamp,
                event_type=event_type,
                severity=severity,
                source=source,
                message=message,
                file=match.file,
                line_number=match.line_number,
                raw_content=content,
            )
        except Exception as e:
            logger.debug(f"Failed to parse audit event: {e}")
            return None

    @staticmethod
    def _extract_timestamp(content: str) -> datetime:
        """Extract timestamp from log line."""
        import re

        # Common timestamp patterns
        patterns = [
            r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})',  # ISO format
            r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})',     # US format
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', # Bracketed ISO
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                ts_str = match.group(1)
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S",
                    "%m/%d/%Y %H:%M:%S",
                ]:
                    try:
                        return datetime.strptime(ts_str, fmt)
                    except ValueError:
                        continue

        return datetime.now(timezone.utc)

    @staticmethod
    def _extract_event_type(content: str) -> AuditEventType:
        """Extract event type from content."""
        content_lower = content.lower()

        if "governance" in content_lower or "decision" in content_lower:
            return AuditEventType.GOVERNANCE_DECISION
        elif "constitutional" in content_lower or "compliance" in content_lower:
            return AuditEventType.CONSTITUTIONAL_CHECK
        elif "violation" in content_lower or "breach" in content_lower:
            return AuditEventType.POLICY_VIOLATION
        elif "access" in content_lower or "auth" in content_lower:
            return AuditEventType.ACCESS_ATTEMPT
        elif "config" in content_lower or "setting" in content_lower:
            return AuditEventType.CONFIGURATION_CHANGE
        elif "security" in content_lower or "attack" in content_lower:
            return AuditEventType.SECURITY_EVENT
        elif "error" in content_lower or "exception" in content_lower:
            return AuditEventType.SYSTEM_ERROR
        else:
            return AuditEventType.USER_ACTION

    @staticmethod
    def _extract_severity(content: str) -> AuditSeverity:
        """Extract severity from content."""
        content_lower = content.lower()

        if any(s in content_lower for s in ["critical", "fatal", "emergency"]):
            return AuditSeverity.CRITICAL
        elif any(s in content_lower for s in ["error", "high", "alert"]):
            return AuditSeverity.HIGH
        elif any(s in content_lower for s in ["warn", "medium"]):
            return AuditSeverity.MEDIUM
        elif any(s in content_lower for s in ["info", "notice"]):
            return AuditSeverity.INFO
        else:
            return AuditSeverity.LOW

    @staticmethod
    def _extract_source(content: str) -> str:
        """Extract source/component from content."""
        import re

        # Look for [source] pattern
        match = re.search(r'\[([^\]]+)\]', content)
        if match:
            return match.group(1)

        # Look for source: pattern
        match = re.search(r'(\w+):', content)
        if match:
            return match.group(1)

        return "unknown"

    @staticmethod
    def _extract_message(content: str) -> str:
        """Extract main message from content."""
        import re

        # Remove timestamp and bracketed prefixes
        message = re.sub(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\s*', '', content)
        message = re.sub(r'^\[[^\]]+\]\s*', '', message)
        message = re.sub(r'^(INFO|DEBUG|WARN|ERROR|CRITICAL)\s*', '', message)

        return message.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "message": self.message,
            "file": self.file,
            "line_number": self.line_number,
            "metadata": self.metadata,
        }


@dataclass
class AuditSearchResult:
    """Result of an audit trail search."""
    query: str
    events: List[AuditEvent]
    total_matches: int
    files_searched: int
    duration_ms: int
    time_range: Optional[Tuple[datetime, datetime]] = None

    @property
    def critical_events(self) -> List[AuditEvent]:
        return [e for e in self.events if e.severity == AuditSeverity.CRITICAL]

    @property
    def high_severity_events(self) -> List[AuditEvent]:
        return [
            e for e in self.events
            if e.severity in [AuditSeverity.CRITICAL, AuditSeverity.HIGH]
        ]

    def filter_by_type(self, event_type: AuditEventType) -> List[AuditEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def filter_by_severity(self, severity: AuditSeverity) -> List[AuditEvent]:
        return [e for e in self.events if e.severity == severity]

    def filter_by_source(self, source: str) -> List[AuditEvent]:
        return [e for e in self.events if e.source == source]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_events": len(self.events),
            "total_matches": self.total_matches,
            "files_searched": self.files_searched,
            "duration_ms": self.duration_ms,
            "events": [e.to_dict() for e in self.events],
            "time_range": {
                "start": self.time_range[0].isoformat() if self.time_range else None,
                "end": self.time_range[1].isoformat() if self.time_range else None,
            },
            "critical_count": len(self.critical_events),
            "high_severity_count": len(self.high_severity_events),
        }


class AuditTrailSearchService:
    """
    Service for searching and analyzing audit trails.

    This service provides:
    - Audit log searching with time-based filtering
    - Event type classification
    - Severity analysis
    - Governance decision tracking
    - Constitutional compliance event monitoring
    """

    # Default audit log paths
    DEFAULT_LOG_PATHS = [
        "/var/log",
        "/var/log/acgs2",
        "logs",
        "audit",
    ]

    # Default log file patterns
    LOG_FILE_TYPES = ["log", "audit", "json"]

    def __init__(
        self,
        client: Optional[SearchPlatformClient] = None,
        config: Optional[SearchPlatformConfig] = None,
        log_paths: Optional[List[str]] = None,
    ):
        self.client = client or SearchPlatformClient(config)
        self.log_paths = log_paths or self.DEFAULT_LOG_PATHS

    async def close(self) -> None:
        """Close the underlying client."""
        await self.client.close()

    async def __aenter__(self) -> "AuditTrailSearchService":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def search(
        self,
        pattern: str,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        max_results: int = 1000,
    ) -> AuditSearchResult:
        """
        Search audit logs.

        Args:
            pattern: Search pattern (regex)
            paths: Log paths to search (defaults to configured paths)
            time_range: Optional (start, end) datetime tuple
            max_results: Maximum results

        Returns:
            AuditSearchResult with parsed events
        """
        start_time = datetime.now(timezone.utc)

        search_paths = paths or self.log_paths

        scope = SearchScope(
            paths=search_paths,
            file_types=self.LOG_FILE_TYPES,
        )

        if time_range:
            scope.time_range = TimeRange(start=time_range[0], end=time_range[1])

        options = SearchOptions(
            max_results=max_results,
            context_lines=1,  # Include surrounding context
        )

        response = await self.client.search(
            pattern=pattern,
            domain=SearchDomain.LOGS,
            scope=scope,
            options=options,
        )

        # Parse events from matches
        events = []
        for match in response.results:
            event = AuditEvent.from_match(match)
            if event:
                events.append(event)

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp, reverse=True)

        duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return AuditSearchResult(
            query=pattern,
            events=events,
            total_matches=response.stats.total_matches,
            files_searched=response.stats.files_searched,
            duration_ms=duration,
            time_range=time_range,
        )

    async def search_governance_decisions(
        self,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        decision_type: Optional[str] = None,
    ) -> AuditSearchResult:
        """
        Search for governance decision records.

        Args:
            paths: Log paths to search
            time_range: Time range filter
            decision_type: Optional specific decision type filter

        Returns:
            AuditSearchResult with governance events
        """
        pattern = r"governance|decision|policy\s+(approved|rejected|modified)"
        if decision_type:
            pattern = f"{decision_type}.*({pattern})"

        result = await self.search(
            pattern=pattern,
            paths=paths,
            time_range=time_range,
        )

        # Filter to only governance events
        result.events = [
            e for e in result.events
            if e.event_type == AuditEventType.GOVERNANCE_DECISION
        ]

        return result

    async def search_constitutional_checks(
        self,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        include_failures: bool = True,
    ) -> AuditSearchResult:
        """
        Search for constitutional compliance check records.

        Args:
            paths: Log paths to search
            time_range: Time range filter
            include_failures: Include failed checks

        Returns:
            AuditSearchResult with constitutional check events
        """
        if include_failures:
            pattern = r"constitutional|compliance|hash\s+(check|verify|valid|invalid|fail)"
        else:
            pattern = r"constitutional|compliance|hash\s+(check|verify|valid)"

        result = await self.search(
            pattern=pattern,
            paths=paths,
            time_range=time_range,
        )

        # Filter to constitutional events
        result.events = [
            e for e in result.events
            if e.event_type == AuditEventType.CONSTITUTIONAL_CHECK
        ]

        return result

    async def search_policy_violations(
        self,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        severity: Optional[AuditSeverity] = None,
    ) -> AuditSearchResult:
        """
        Search for policy violation records.

        Args:
            paths: Log paths to search
            time_range: Time range filter
            severity: Filter by severity

        Returns:
            AuditSearchResult with violation events
        """
        pattern = r"violation|breach|unauthorized|denied|forbidden"

        result = await self.search(
            pattern=pattern,
            paths=paths,
            time_range=time_range,
        )

        # Filter to violation events
        events = [
            e for e in result.events
            if e.event_type == AuditEventType.POLICY_VIOLATION
        ]

        if severity:
            events = [e for e in events if e.severity == severity]

        result.events = events
        return result

    async def search_security_events(
        self,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        only_critical: bool = False,
    ) -> AuditSearchResult:
        """
        Search for security-related events.

        Args:
            paths: Log paths to search
            time_range: Time range filter
            only_critical: Only return critical events

        Returns:
            AuditSearchResult with security events
        """
        pattern = r"security|attack|intrusion|malicious|threat|vulnerability"

        result = await self.search(
            pattern=pattern,
            paths=paths,
            time_range=time_range,
        )

        # Filter to security events
        events = [
            e for e in result.events
            if e.event_type == AuditEventType.SECURITY_EVENT
        ]

        if only_critical:
            events = [e for e in events if e.severity == AuditSeverity.CRITICAL]

        result.events = events
        return result

    async def search_errors(
        self,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        component: Optional[str] = None,
    ) -> AuditSearchResult:
        """
        Search for system errors.

        Args:
            paths: Log paths to search
            time_range: Time range filter
            component: Filter by component/source

        Returns:
            AuditSearchResult with error events
        """
        pattern = r"error|exception|traceback|failed|failure"
        if component:
            pattern = f"\\[{component}\\].*({pattern})|{pattern}.*{component}"

        result = await self.search(
            pattern=pattern,
            paths=paths,
            time_range=time_range,
        )

        # Filter to error events
        events = [
            e for e in result.events
            if e.event_type == AuditEventType.SYSTEM_ERROR
        ]

        if component:
            events = [e for e in events if component.lower() in e.source.lower()]

        result.events = events
        return result

    async def get_recent_critical_events(
        self,
        hours: int = 24,
        paths: Optional[List[str]] = None,
    ) -> AuditSearchResult:
        """
        Get critical events from the last N hours.

        Args:
            hours: Number of hours to look back
            paths: Log paths to search

        Returns:
            AuditSearchResult with critical events
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        pattern = r"critical|fatal|emergency|alert"

        result = await self.search(
            pattern=pattern,
            paths=paths,
            time_range=(start_time, end_time),
        )

        result.events = [
            e for e in result.events
            if e.severity == AuditSeverity.CRITICAL
        ]

        return result

    async def generate_audit_summary(
        self,
        paths: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a summary of audit events.

        Args:
            paths: Log paths to search
            time_range: Time range for summary

        Returns:
            Dictionary with audit summary statistics
        """
        # Search for all audit events
        result = await self.search(
            pattern=r".",  # Match all log lines
            paths=paths,
            time_range=time_range,
            max_results=10000,
        )

        # Count by event type
        type_counts: Dict[str, int] = {}
        for event in result.events:
            type_name = event.event_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Count by severity
        severity_counts: Dict[str, int] = {}
        for event in result.events:
            sev_name = event.severity.value
            severity_counts[sev_name] = severity_counts.get(sev_name, 0) + 1

        # Count by source
        source_counts: Dict[str, int] = {}
        for event in result.events:
            source_counts[event.source] = source_counts.get(event.source, 0) + 1

        return {
            "total_events": len(result.events),
            "files_searched": result.files_searched,
            "duration_ms": result.duration_ms,
            "by_event_type": type_counts,
            "by_severity": severity_counts,
            "by_source": dict(sorted(
                source_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]),  # Top 20 sources
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0),
            "time_range": {
                "start": time_range[0].isoformat() if time_range else None,
                "end": time_range[1].isoformat() if time_range else None,
            },
        }
