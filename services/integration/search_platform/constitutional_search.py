"""
Constitutional Code Search Service

High-level service for searching code with constitutional compliance awareness.
Integrates with ACGS2's constitutional validation framework.

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .client import SearchPlatformClient, SearchPlatformConfig
from .models import (
    SearchDomain,
    SearchMatch,
    SearchOptions,
    SearchResponse,
    SearchScope,
)

logger = logging.getLogger(__name__)


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
    timestamp: datetime = field(default_factory=datetime.utcnow)

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
    constitutional_hash: str = "cdd01ef066bc6cf2"

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


class ConstitutionalCodeSearchService:
    """
    Service for searching code with constitutional compliance awareness.

    This service wraps the Search Platform client and adds:
    - Constitutional hash verification
    - Security pattern detection
    - Compliance violation scanning
    - Safe search patterns
    """

    # Default patterns for constitutional compliance checking
    DEFAULT_VIOLATION_PATTERNS: List[ConstitutionalPattern] = [
        ConstitutionalPattern(
            name="hardcoded_secrets",
            pattern=r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']',
            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
            severity="critical",
            description="Potential hardcoded secret or credential",
            remediation="Use environment variables or a secrets manager",
            file_types=["py", "js", "ts", "go", "rs"],
        ),
        ConstitutionalPattern(
            name="sql_injection_risk",
            pattern=r'execute\s*\(\s*["\'].*%s.*["\']\s*%',
            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
            severity="critical",
            description="Potential SQL injection vulnerability",
            remediation="Use parameterized queries",
            file_types=["py"],
        ),
        ConstitutionalPattern(
            name="eval_usage",
            pattern=r'\beval\s*\(',
            violation_type=ConstitutionalViolationType.UNSAFE_PATTERN,
            severity="high",
            description="Use of eval() can lead to code injection",
            remediation="Use safer alternatives like ast.literal_eval",
            file_types=["py", "js"],
        ),
        ConstitutionalPattern(
            name="missing_constitutional_hash",
            pattern=r'^(?!.*Constitutional Hash:).*$',
            violation_type=ConstitutionalViolationType.MISSING_HASH,
            severity="medium",
            description="File missing constitutional hash marker",
            remediation="Add 'Constitutional Hash: cdd01ef066bc6cf2' to file header",
            file_types=["py"],
        ),
        ConstitutionalPattern(
            name="unsafe_deserialization",
            pattern=r'pickle\.loads?\s*\(|yaml\.load\s*\([^,]+\)(?!.*Loader)',
            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
            severity="critical",
            description="Unsafe deserialization detected",
            remediation="Use safe loaders (yaml.safe_load, json.loads)",
            file_types=["py"],
        ),
        ConstitutionalPattern(
            name="subprocess_shell",
            pattern=r'subprocess\.\w+\([^)]*shell\s*=\s*True',
            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
            severity="high",
            description="Subprocess with shell=True can be dangerous",
            remediation="Use shell=False and pass command as list",
            file_types=["py"],
        ),
    ]

    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

    def __init__(
        self,
        client: Optional[SearchPlatformClient] = None,
        config: Optional[SearchPlatformConfig] = None,
        custom_patterns: Optional[List[ConstitutionalPattern]] = None,
    ):
        self.client = client or SearchPlatformClient(config)
        self.violation_patterns = self.DEFAULT_VIOLATION_PATTERNS.copy()
        if custom_patterns:
            self.violation_patterns.extend(custom_patterns)

    async def close(self) -> None:
        """Close the underlying client."""
        await self.client.close()

    async def __aenter__(self) -> "ConstitutionalCodeSearchService":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def search(
        self,
        pattern: str,
        paths: List[str],
        file_types: Optional[List[str]] = None,
        check_compliance: bool = True,
        max_results: int = 1000,
    ) -> ConstitutionalSearchResult:
        """
        Search code with optional constitutional compliance checking.

        Args:
            pattern: Search pattern (regex)
            paths: Paths to search
            file_types: Optional file type filter
            check_compliance: Whether to check for constitutional compliance
            max_results: Maximum results to return

        Returns:
            ConstitutionalSearchResult with matches and any violations
        """
        start_time = datetime.utcnow()

        # Execute the search
        response = await self.client.search_code(
            pattern=pattern,
            paths=paths,
            file_types=file_types,
            max_results=max_results,
        )

        violations: List[ConstitutionalViolation] = []
        compliant_matches: List[SearchMatch] = []

        if check_compliance:
            # Check each match for compliance
            for match in response.results:
                match_violations = await self._check_match_compliance(match)
                if match_violations:
                    violations.extend(match_violations)
                else:
                    compliant_matches.append(match)
        else:
            compliant_matches = response.results

        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ConstitutionalSearchResult(
            query=pattern,
            total_files_searched=response.stats.files_searched,
            total_matches=response.stats.total_matches,
            violations=violations,
            compliant_matches=compliant_matches,
            duration_ms=duration,
        )

    async def scan_for_violations(
        self,
        paths: List[str],
        file_types: Optional[List[str]] = None,
        severity_filter: Optional[List[str]] = None,
    ) -> ConstitutionalSearchResult:
        """
        Scan codebase for constitutional violations.

        Args:
            paths: Paths to scan
            file_types: Optional file type filter
            severity_filter: Only return violations of these severities

        Returns:
            ConstitutionalSearchResult with all found violations
        """
        start_time = datetime.utcnow()
        all_violations: List[ConstitutionalViolation] = []
        files_searched: Set[str] = set()

        # Run each violation pattern search
        for vp in self.violation_patterns:
            # Skip if file type filter doesn't match
            if file_types and vp.file_types:
                if not any(ft in vp.file_types for ft in file_types):
                    continue

            # Skip if severity doesn't match filter
            if severity_filter and vp.severity not in severity_filter:
                continue

            try:
                response = await self.client.search_code(
                    pattern=vp.pattern,
                    paths=paths,
                    file_types=vp.file_types or file_types,
                    max_results=500,
                )

                for match in response.results:
                    files_searched.add(match.file)
                    violation = ConstitutionalViolation(
                        violation_type=vp.violation_type,
                        file=match.file,
                        line_number=match.line_number,
                        description=vp.description,
                        severity=vp.severity,
                        match_content=match.line_content,
                        remediation=vp.remediation,
                    )
                    all_violations.append(violation)

            except Exception as e:
                logger.warning(f"Error scanning with pattern '{vp.name}': {e}")

        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ConstitutionalSearchResult(
            query="constitutional_violation_scan",
            total_files_searched=len(files_searched),
            total_matches=len(all_violations),
            violations=all_violations,
            compliant_matches=[],
            duration_ms=duration,
        )

    async def verify_constitutional_hash(
        self,
        paths: List[str],
    ) -> ConstitutionalSearchResult:
        """
        Verify that all Python files have the correct constitutional hash.

        Args:
            paths: Paths to verify

        Returns:
            ConstitutionalSearchResult with hash violations
        """
        start_time = datetime.utcnow()
        violations: List[ConstitutionalViolation] = []
        compliant_files: List[SearchMatch] = []

        # Search for files WITH the correct hash
        correct_hash_response = await self.client.search_code(
            pattern=f"Constitutional Hash: {self.CONSTITUTIONAL_HASH}",
            paths=paths,
            file_types=["py"],
            max_results=10000,
        )

        compliant_file_set = {m.file for m in correct_hash_response.results}

        # Search for Python files without the hash (search for common patterns)
        # We'll look for Python files by searching for common constructs
        py_files_response = await self.client.search_code(
            pattern=r"^(import|from|def|class|async)",
            paths=paths,
            file_types=["py"],
            max_results=10000,
        )

        all_py_files = {m.file for m in py_files_response.results}

        # Files without the hash
        non_compliant_files = all_py_files - compliant_file_set

        for file_path in non_compliant_files:
            violations.append(
                ConstitutionalViolation(
                    violation_type=ConstitutionalViolationType.MISSING_HASH,
                    file=file_path,
                    line_number=1,
                    description="File missing constitutional hash marker",
                    severity="medium",
                    match_content="",
                    remediation=f"Add 'Constitutional Hash: {self.CONSTITUTIONAL_HASH}' to file header",
                )
            )

        for match in correct_hash_response.results:
            compliant_files.append(match)

        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ConstitutionalSearchResult(
            query="constitutional_hash_verification",
            total_files_searched=len(all_py_files),
            total_matches=len(compliant_file_set),
            violations=violations,
            compliant_matches=compliant_files,
            duration_ms=duration,
        )

    async def find_security_issues(
        self,
        paths: List[str],
    ) -> ConstitutionalSearchResult:
        """
        Find security-related issues in the codebase.

        Args:
            paths: Paths to scan

        Returns:
            ConstitutionalSearchResult with security violations
        """
        return await self.scan_for_violations(
            paths=paths,
            severity_filter=["critical", "high"],
        )

    async def _check_match_compliance(
        self,
        match: SearchMatch,
    ) -> List[ConstitutionalViolation]:
        """Check a single match for compliance violations."""
        violations = []

        for vp in self.violation_patterns:
            # Check file type filter
            if vp.file_types:
                file_ext = match.file.rsplit(".", 1)[-1] if "." in match.file else ""
                if file_ext not in vp.file_types:
                    continue

            # Check if pattern matches the line content
            if re.search(vp.pattern, match.line_content, re.IGNORECASE):
                violations.append(
                    ConstitutionalViolation(
                        violation_type=vp.violation_type,
                        file=match.file,
                        line_number=match.line_number,
                        description=vp.description,
                        severity=vp.severity,
                        match_content=match.line_content,
                        remediation=vp.remediation,
                    )
                )

        return violations

    def add_custom_pattern(self, pattern: ConstitutionalPattern) -> None:
        """Add a custom violation pattern."""
        self.violation_patterns.append(pattern)

    def remove_pattern(self, name: str) -> bool:
        """Remove a violation pattern by name."""
        initial_count = len(self.violation_patterns)
        self.violation_patterns = [
            p for p in self.violation_patterns if p.name != name
        ]
        return len(self.violation_patterns) < initial_count
