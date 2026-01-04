"""
Constitutional Code Search - Data Models
Constitutional Hash: cdd01ef066bc6cf2

Data models, enums, and data classes for constitutional code search.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import SearchMatch

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ConstitutionalViolationType(str, Enum):
    """Types of constitutional violations that can be detected."""

    MISSING_HASH = "missing_hash"
    INVALID_HASH = "invalid_hash"
    UNSAFE_PATTERN = "unsafe_pattern"
    SECURITY_VIOLATION = "security_violation"
    COMPLIANCE_GAP = "compliance_gap"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class ConstitutionalViolation:
    """A detected constitutional violation."""

    violation_type: ConstitutionalViolationType
    file: str
    line_number: int
    description: str
    severity: str  # "critical", "high", "medium", "low"
    match_content: str
    remediation: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_type": self.violation_type.value,
            "file": self.file,
            "line_number": self.line_number,
            "description": self.description,
            "severity": self.severity,
            "match_content": self.match_content,
            "remediation": self.remediation,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConstitutionalSearchResult:
    """Result of a constitutional code search."""

    query: str
    total_files_searched: int
    total_matches: int
    violations: List[ConstitutionalViolation]
    compliant_matches: List[SearchMatch]
    duration_ms: int
    constitutional_hash: str = CONSTITUTIONAL_HASH

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    @property
    def critical_violations(self) -> List[ConstitutionalViolation]:
        return [v for v in self.violations if v.severity == "critical"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_files_searched": self.total_files_searched,
            "total_matches": self.total_matches,
            "violations_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "compliant_matches_count": len(self.compliant_matches),
            "duration_ms": self.duration_ms,
            "constitutional_hash": self.constitutional_hash,
            "has_violations": self.has_violations,
        }


@dataclass
class ConstitutionalPattern:
    """Pattern for detecting constitutional violations."""

    name: str
    pattern: str
    violation_type: ConstitutionalViolationType
    severity: str
    description: str
    remediation: str
    file_types: List[str] = field(default_factory=list)


__all__ = [
    "CONSTITUTIONAL_HASH",
    "ConstitutionalViolationType",
    "ConstitutionalViolation",
    "ConstitutionalSearchResult",
    "ConstitutionalPattern",
]
