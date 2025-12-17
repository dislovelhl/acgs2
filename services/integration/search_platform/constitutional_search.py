"""
Constitutional Code Search Service

High-level service for searching code with constitutional compliance awareness.
Integrates with ACGS2's constitutional validation framework.

Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import ast
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
        self.semgrep_analyzer = SemgrepAnalyzer()
        self.codeql_analyzer = CodeQLAnalyzer()
        self.false_positive_suppressor = FalsePositiveSuppressor()
        self.dashboard = RealTimeScanDashboard(self)
        self.trivy_scanner = TrivyContainerScanner()
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
        # AST-based analysis for Python files
        if not file_types or "py" in file_types:
            ast_violations = await self._scan_ast_violations(paths)
            all_violations.extend(ast_violations)
            files_searched.update(v.file for v in ast_violations)
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

    async def _scan_ast_violations(self, paths: List[str]) -> List[ConstitutionalViolation]:
        """Scan Python files using AST analysis for advanced security issues."""
        violations: List[ConstitutionalViolation] = []
        
        # Find all Python files
        py_files_response = await self.client.search_code(
            pattern=r"^(import|from|def|class|async)",
            paths=paths,
            file_types=["py"],
            max_results=10000,
        )
        
        py_files = list(set(m.file for m in py_files_response.results))
        
        for file_path in py_files:
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # Parse AST
                tree = ast.parse(source_code, filename=file_path)
                
                # Analyze with AST security analyzer
                analyzer = ASTSecurityAnalyzer(source_code, file_path)
                analyzer.visit(tree)
                
                # Also run Semgrep analysis
                semgrep_violations = await self.semgrep_analyzer.scan_file(file_path)
                violations.extend(semgrep_violations)
                
                # Also run CodeQL analysis for JS/TS files
                file_ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
                if file_ext in ["js", "ts"]:
                    codeql_violations = await self.codeql_analyzer.scan_file(file_path)
                    violations.extend(codeql_violations)
                
                # Filter out false positives
                filtered_violations = [v for v in analyzer.violations + violations if not self.false_positive_suppressor.should_suppress(v)]
                violations[:] = filtered_violations
                
            except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
                logger.warning(f"Error analyzing {file_path} with AST: {e}")
            except Exception as e:
                logger.error(f"Unexpected error analyzing {file_path}: {e}")
        
        return violations
        
        return violations
        """Remove a violation pattern by name."""
        initial_count = len(self.violation_patterns)
        self.violation_patterns = [
            p for p in self.violation_patterns if p.name != name
        ]
        return len(self.violation_patterns) < initial_count

class ASTSecurityAnalyzer(ast.NodeVisitor):
    """
    AST-based security analyzer for detecting advanced vulnerabilities.
    
    Detects:
    - Taint propagation (user input to sensitive operations)
    - Control flow vulnerabilities (SQL injection, XSS)
    - Dependency injection risks
    """
    
    def __init__(self, source_code: str, filename: str):
        self.source_code = source_code
        self.filename = filename
        self.violations: List[ConstitutionalViolation] = []
        
        # Taint tracking
        self.tainted_vars: Set[str] = set()
        self.user_inputs = {'input', 'raw_input', 'sys.argv', 'request.args', 'request.form', 'request.data'}
        
        # Sensitive operations
        self.sensitive_functions = {
            'execute': 'SQL injection risk',
            'eval': 'Code injection risk',
            'exec': 'Code execution risk',
            'open': 'File operation risk',
            'subprocess.call': 'Command injection risk',
            'subprocess.run': 'Command injection risk',
            'subprocess.Popen': 'Command injection risk',
            'os.system': 'Command injection risk',
            'os.popen': 'Command injection risk',
        }
        
        # Control flow tracking
        self.in_conditional = False
        self.loop_vars: Set[str] = set()
        
    def visit_Assign(self, node: ast.Assign) -> None:
        """Track variable assignments for taint analysis."""
        if isinstance(node.value, ast.Call):
            func_name = self._get_func_name(node.value.func)
            if func_name in self.user_inputs:
                # Mark assigned variables as tainted
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.tainted_vars.add(target.id)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for security issues."""
        func_name = self._get_func_name(node.func)
        
        # Check for sensitive operations with tainted data
        if func_name in self.sensitive_functions:
            for arg in node.args:
                if self._is_tainted_arg(arg):
                    line_content = self._get_line_content(node.lineno)
                    self.violations.append(ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                        file=self.filename,
                        line_number=node.lineno,
                        description=f"Tainted data used in {func_name}: {self.sensitive_functions[func_name]}",
                        severity="critical",
                        match_content=line_content,
                        remediation=f"Avoid using tainted data in {func_name}. Use parameterized queries or input validation.",
                    ))
        
        # Check for dependency injection risks
        if self._is_dependency_injection_risk(node):
            line_content = self._get_line_content(node.lineno)
            self.violations.append(ConstitutionalViolation(
                violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                file=self.filename,
                line_number=node.lineno,
                description="Potential dependency injection vulnerability",
                severity="high",
                match_content=line_content,
                remediation="Validate and sanitize dependency configurations",
            ))
        
        self.generic_visit(node)
    
    def visit_If(self, node: ast.If) -> None:
        """Track control flow for conditional vulnerabilities."""
        old_conditional = self.in_conditional
        self.in_conditional = True
        self.generic_visit(node)
        self.in_conditional = old_conditional
    
    def visit_For(self, node: ast.For) -> None:
        """Track loop variables."""
        if isinstance(node.target, ast.Name):
            self.loop_vars.add(node.target.id)
        self.generic_visit(node)
        if isinstance(node.target, ast.Name):
            self.loop_vars.discard(node.target.id)
    
    def _get_func_name(self, func_node: ast.expr) -> str:
        """Extract function name from AST node."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return f"{self._get_func_name(func_node.value)}.{func_node.attr}"
        return ""
    
    def _is_tainted_arg(self, arg: ast.expr) -> bool:
        """Check if argument contains tainted data."""
        if isinstance(arg, ast.Name) and arg.id in self.tainted_vars:
            return True
        elif isinstance(arg, ast.Str):
            # Check if string contains tainted variables
            return any(var in arg.s for var in self.tainted_vars)
        elif isinstance(arg, ast.BinOp):
            # Check binary operations
            return self._is_tainted_arg(arg.left) or self._is_tainted_arg(arg.right)
        return False
    
    def _is_dependency_injection_risk(self, node: ast.Call) -> bool:
        """Check for dependency injection vulnerabilities."""
        func_name = self._get_func_name(node.func)
        if 'inject' in func_name.lower() or 'resolve' in func_name.lower():
            # Check if arguments are not validated
            for arg in node.args:
                if isinstance(arg, ast.Str) and ('http' in arg.s or 'file:' in arg.s):
                    return True
        return False
    
    def _get_line_content(self, lineno: int) -> str:
        """Get source code line content."""
        lines = self.source_code.splitlines()
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1].strip()
        return ""




class SemgrepAnalyzer:
    """
    Semgrep-based multi-language static analysis for security vulnerabilities.
    """
    
    def __init__(self):
        self.semgrep_rules = {
            "python": [
                "rules/python-security.yaml",
                "rules/python-best-practices.yaml"
            ],
            "javascript": [
                "rules/javascript-security.yaml",
                "rules/javascript-best-practices.yaml"
            ],
            "typescript": [
                "rules/typescript-security.yaml"
            ]
        }
    
    async def scan_file(self, file_path: str) -> List[ConstitutionalViolation]:
        """Scan a single file with Semgrep."""
        violations: List[ConstitutionalViolation] = []
        
        file_ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        lang_map = {"py": "python", "js": "javascript", "ts": "typescript"}
        lang = lang_map.get(file_ext)
        
        if not lang or lang not in self.semgrep_rules:
            return violations
        
        import subprocess
        import json
        
        for rule_file in self.semgrep_rules[lang]:
            try:
                # Run semgrep
                result = subprocess.run(
                    ["semgrep", "--json", "--config", rule_file, file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout:
                    data = json.loads(result.stdout)
                    for finding in data.get("results", []):
                        violations.append(ConstitutionalViolation(
                            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                            file=file_path,
                            line_number=finding["start"]["line"],
                            description=f"Semgrep: {finding['check_id']} - {finding.get('extra', {}).get('message', '')}",
                            severity=self._map_severity(finding.get("extra", {}).get("severity", "medium")),
                            match_content=finding["lines"],
                            remediation=finding.get("extra", {}).get("fix", "Review and fix the security issue"),
                        ))
                        
            except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
                # Semgrep not available or rule file missing
                continue
        
        return violations
    
    def _map_severity(self, semgrep_severity: str) -> str:
        """Map Semgrep severity to our severity levels."""
        mapping = {
            "ERROR": "critical",
            "WARNING": "high", 
            "INFO": "medium"
        }
        return mapping.get(semgrep_severity.upper(), "medium")


class CodeQLAnalyzer:
    """
    CodeQL-based static analysis for JavaScript/TypeScript security vulnerabilities.
    """
    
    def __init__(self):
        self.codeql_db_path = "/tmp/codeql-db"
    
    async def scan_file(self, file_path: str) -> List[ConstitutionalViolation]:
        """Scan a single JS/TS file with CodeQL."""
        violations: List[ConstitutionalViolation] = []
        
        file_ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        if file_ext not in ["js", "ts"]:
            return violations
        
        import subprocess
        import json
        import os
        
        try:
            # Create CodeQL database if needed
            if not os.path.exists(self.codeql_db_path):
                os.makedirs(self.codeql_db_path)
                
                # Initialize database
                result = subprocess.run(
                    ["codeql", "database", "create", self.codeql_db_path, 
                     "--language=javascript", f"--source-root={os.path.dirname(file_path)}"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    logger.warning(f"Failed to create CodeQL database: {result.stderr}")
                    return violations
            
            # Run security queries
            security_queries = [
                "js/xss.ql",
                "js/sql-injection.ql", 
                "js/command-injection.ql",
                "js/path-injection.ql"
            ]
            
            for query in security_queries:
                try:
                    result = subprocess.run(
                        ["codeql", "query", "run", f"--database={self.codeql_db_path}", 
                         f"--output={query}.bqrs", query],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        # Convert results to JSON
                        json_result = subprocess.run(
                            ["codeql", "bqrs", "decode", f"{query}.bqrs", "--format=json"],
                            capture_output=True,
                            text=True
                        )
                        
                        if json_result.returncode == 0:
                            data = json.loads(json_result.stdout)
                            for finding in data.get("#select", []):
                                if isinstance(finding, dict) and "url" in finding:
                                    # Extract line number from URL
                                    url_parts = finding["url"].split("#")
                                    if len(url_parts) > 1:
                                        line_info = url_parts[1]
                                        if "L" in line_info:
                                            line_num = int(line_info.split("L")[1].split("-")[0])
                                            
                                            violations.append(ConstitutionalViolation(
                                                violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                                                file=file_path,
                                                line_number=line_num,
                                                description=f"CodeQL: {query} - {finding.get('message', '')}",
                                                severity="high",
                                                match_content=finding.get("message", ""),
                                                remediation="Review and fix the security vulnerability identified by CodeQL",
                                            ))
                
                except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
                    continue
                    
        except Exception as e:
            logger.warning(f"CodeQL analysis failed for {file_path}: {e}")
        
        return violations


class FalsePositiveSuppressor:
    """
    Machine learning-based false positive suppression using user feedback.
    """
    
    def __init__(self):
        self.feedback_db = {}  # violation_hash -> {"confirmed": count, "false_positive": count}
        self.ml_model = None  # Placeholder for ML model
    
    def should_suppress(self, violation: ConstitutionalViolation) -> bool:
        """Determine if a violation should be suppressed based on feedback."""
        violation_hash = self._hash_violation(violation)
        
        if violation_hash not in self.feedback_db:
            return False
        
        feedback = self.feedback_db[violation_hash]
        total_feedback = feedback["confirmed"] + feedback["false_positive"]
        
        if total_feedback < 5:  # Need minimum feedback
            return False
        
        false_positive_rate = feedback["false_positive"] / total_feedback
        
        # Suppress if >70% of similar violations were marked as false positives
        return false_positive_rate > 0.7
    
    def add_feedback(self, violation: ConstitutionalViolation, is_false_positive: bool):
        """Add user feedback for a violation."""
        violation_hash = self._hash_violation(violation)
        
        if violation_hash not in self.feedback_db:
            self.feedback_db[violation_hash] = {"confirmed": 0, "false_positive": 0}
        
        if is_false_positive:
            self.feedback_db[violation_hash]["false_positive"] += 1
        else:
            self.feedback_db[violation_hash]["confirmed"] += 1
    
    def _hash_violation(self, violation: ConstitutionalViolation) -> str:
        """Create a hash for violation deduplication."""
        import hashlib
        content = f"{violation.violation_type.value}:{violation.description}:{violation.match_content}"
        return hashlib.md5(content.encode()).hexdigest()


class RealTimeScanDashboard:
    """
    Real-time scanning dashboard for monitoring security violations.
    """
    
    def __init__(self, service: 'ConstitutionalCodeSearchService'):
        self.service = service
        self.scan_results: List[ConstitutionalSearchResult] = []
        self.active_scans: Dict[str, asyncio.Task] = {}
    
    async def start_scan(self, scan_id: str, paths: List[str], file_types: Optional[List[str]] = None):
        """Start a real-time scan."""
        async def scan_task():
            result = await self.service.scan_for_violations(paths, file_types)
            self.scan_results.append(result)
            del self.active_scans[scan_id]
        
        task = asyncio.create_task(scan_task())
        self.active_scans[scan_id] = task
    
    def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get status of a scan."""
        if scan_id in self.active_scans:
            return {"status": "running"}
        
        # Find completed scan
        for result in self.scan_results[-10:]:  # Last 10 scans
            if result.query == f"scan_{scan_id}":
                return {
                    "status": "completed",
                    "violations_count": len(result.violations),
                    "critical_violations": len(result.critical_violations),
                    "duration_ms": result.duration_ms
                }
        
        return {"status": "not_found"}
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard summary data."""
        total_scans = len(self.scan_results)
        total_violations = sum(len(r.violations) for r in self.scan_results)
        critical_violations = sum(len(r.critical_violations) for r in self.scan_results)
        
        recent_scans = self.scan_results[-5:]  # Last 5 scans
        
        return {
            "total_scans": total_scans,
            "total_violations": total_violations,
            "critical_violations": critical_violations,
            "active_scans": len(self.active_scans),
            "recent_scans": [
                {
                    "query": r.query,
                    "violations_count": len(r.violations),
                    "duration_ms": r.duration_ms,
                    "timestamp": r.violations[0].timestamp.isoformat() if r.violations else None
                }
                for r in recent_scans
            ]
        }


class TrivyContainerScanner:
    """
    Trivy-based container image security scanning for supply chain risks.
    """
    
    def __init__(self):
        self.scan_results: Dict[str, Dict[str, Any]] = {}
    
    async def scan_image(self, image_name: str) -> List[ConstitutionalViolation]:
        """Scan a container image with Trivy."""
        violations: List[ConstitutionalViolation] = []
        
        import subprocess
        import json
        
        try:
            # Run Trivy scan
            result = subprocess.run(
                ["trivy", "image", "--format", "json", "--output", "-", image_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                
                for result_item in data.get("Results", []):
                    for vulnerability in result_item.get("Vulnerabilities", []):
                        severity = vulnerability.get("Severity", "UNKNOWN").lower()
                        
                        # Map Trivy severity to our severity levels
                        our_severity = self._map_trivy_severity(severity)
                        
                        violations.append(ConstitutionalViolation(
                            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                            file=image_name,
                            line_number=0,  # Container images don't have line numbers
                            description=f"Container vulnerability: {vulnerability.get('VulnerabilityID')} - {vulnerability.get('Title', '')}",
                            severity=our_severity,
                            match_content=f"Package: {vulnerability.get('PkgName')} {vulnerability.get('InstalledVersion')} - {vulnerability.get('Description', '')}",
                            remediation=f"Update to {vulnerability.get('FixedVersion', 'latest version')}",
                        ))
            
            self.scan_results[image_name] = {
                "violations_count": len(violations),
                "scan_time": datetime.utcnow().isoformat(),
                "success": True
            }
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Trivy scan failed for {image_name}: {e}")
            self.scan_results[image_name] = {
                "error": str(e),
                "scan_time": datetime.utcnow().isoformat(),
                "success": False
            }
        
        return violations
    
    async def scan_dockerfile(self, dockerfile_path: str) -> List[ConstitutionalViolation]:
        """Scan Dockerfile for security issues."""
        violations: List[ConstitutionalViolation] = []
        
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            lines = content.splitlines()
            
            for i, line in enumerate(lines, 1):
                line_lower = line.lower().strip()
                
                # Check for security issues in Dockerfile
                if line_lower.startswith('from') and 'latest' in line_lower:
                    violations.append(ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                        file=dockerfile_path,
                        line_number=i,
                        description="Using 'latest' tag in FROM instruction",
                        severity="medium",
                        match_content=line,
                        remediation="Use specific version tags for reproducible builds",
                    ))
                
                elif line_lower.startswith('run') and ('apt-get update' in line_lower or 'yum update' in line_lower):
                    if '&&' not in line_lower or 'rm -rf /var/lib/apt/lists/*' not in line_lower:
                        violations.append(ConstitutionalViolation(
                            violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                            file=dockerfile_path,
                            line_number=i,
                            description="Package manager cache not cleaned after RUN",
                            severity="low",
                            match_content=line,
                            remediation="Clean package manager cache to reduce image size and potential security issues",
                        ))
                
                elif 'add ' in line_lower and 'http' in line_lower:
                    violations.append(ConstitutionalViolation(
                        violation_type=ConstitutionalViolationType.SECURITY_VIOLATION,
                        file=dockerfile_path,
                        line_number=i,
                        description="Using ADD with HTTP URLs",
                        severity="high",
                        match_content=line,
                        remediation="Use COPY for local files or wget/curl in RUN for HTTP URLs",
                    ))
        
        except FileNotFoundError:
            logger.warning(f"Dockerfile not found: {dockerfile_path}")
        
        return violations
    
    def _map_trivy_severity(self, trivy_severity: str) -> str:
        """Map Trivy severity to our severity levels."""
        mapping = {
            "critical": "critical",
            "high": "high", 
            "medium": "medium",
            "low": "low",
            "unknown": "low"
        }
        return mapping.get(trivy_severity.lower(), "low")
    
    def get_scan_summary(self) -> Dict[str, Any]:
        """Get summary of all container scans."""
        total_scans = len(self.scan_results)
        successful_scans = sum(1 for r in self.scan_results.values() if r.get("success", False))
        total_violations = sum(r.get("violations_count", 0) for r in self.scan_results.values())
        
        return {
            "total_scans": total_scans,
            "successful_scans": successful_scans,
            "total_violations": total_violations,
            "scan_results": self.scan_results
        }


    async def scan_containers(self, paths: List[str]) -> ConstitutionalSearchResult:
        """
        Scan container images and Dockerfiles for security issues.
        
        Args:
            paths: Paths to scan for Dockerfiles and images
            
        Returns:
            ConstitutionalSearchResult with container security violations
        """
        start_time = datetime.utcnow()
        all_violations: List[ConstitutionalViolation] = []
        
        # Find Dockerfiles
        dockerfile_response = await self.client.search_code(
            pattern=r"^FROM\s+",  # Dockerfile FROM instructions
            paths=paths,
            file_types=["dockerfile", "Dockerfile"],
            max_results=100
        )
        
        dockerfiles = list(set(m.file for m in dockerfile_response.results))
        
        # Scan each Dockerfile
        for dockerfile in dockerfiles:
            violations = await self.trivy_scanner.scan_dockerfile(dockerfile)
            all_violations.extend(violations)
        
        # Try to find and scan container images (if any are built)
        # This is a simplified version - in practice, you'd need to know image names
        image_names = ["acgs2:latest", "acgs2:dev"]  # Example image names
        
        for image_name in image_names:
            try:
                violations = await self.trivy_scanner.scan_image(image_name)
                all_violations.extend(violations)
            except Exception as e:
                logger.debug(f"Could not scan image {image_name}: {e}")
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return ConstitutionalSearchResult(
            query="container_security_scan",
            total_files_searched=len(dockerfiles),
            total_matches=len(all_violations),
            violations=all_violations,
            compliant_matches=[],
            duration_ms=duration,
        )

