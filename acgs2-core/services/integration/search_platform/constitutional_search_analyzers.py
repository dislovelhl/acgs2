"""
Constitutional Code Search - Analyzers
Constitutional Hash: cdd01ef066bc6cf2

Security analyzer implementations for constitutional code search.
"""

import ast
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from .constitutional_search_models import (
    CONSTITUTIONAL_HASH,
    ConstitutionalViolationType,
    ConstitutionalViolation,
    ConstitutionalSearchResult,
)

if TYPE_CHECKING:
    from .constitutional_search import ConstitutionalCodeSearchService

logger = logging.getLogger(__name__)


class ASTSecurityAnalyzer(ast.NodeVisitor):
    """
    AST-based security analyzer for detecting advanced vulnerabilities.

    Detects:
    - Taint propagation (user input to sensitive operations)
    - Control flow vulnerabilities (SQL injection, XSS)
    - Dependency injection risks

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, source_code: str, filename: str):
        self.source_code = source_code
        self.filename = filename
        self.violations: List[ConstitutionalViolation] = []

        # Taint tracking
        self.tainted_vars: Set[str] = set()
        self.user_inputs = {
            'input', 'raw_input', 'sys.argv',
            'request.args', 'request.form', 'request.data'
        }

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

    Constitutional Hash: cdd01ef066bc6cf2
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

    Constitutional Hash: cdd01ef066bc6cf2
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

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self):
        self.feedback_db: Dict[str, Dict[str, int]] = {}  # violation_hash -> {"confirmed": count, "false_positive": count}
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

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, service: 'ConstitutionalCodeSearchService'):
        self.service = service
        self.scan_results: List[ConstitutionalSearchResult] = []
        self.active_scans: Dict[str, asyncio.Task] = {}

    async def start_scan(
        self,
        scan_id: str,
        paths: List[str],
        file_types: Optional[List[str]] = None
    ):
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

    Constitutional Hash: cdd01ef066bc6cf2
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
                "scan_time": datetime.now(timezone.utc).isoformat(),
                "success": True
            }

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Trivy scan failed for {image_name}: {e}")
            self.scan_results[image_name] = {
                "error": str(e),
                "scan_time": datetime.now(timezone.utc).isoformat(),
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


__all__ = [
    "ASTSecurityAnalyzer",
    "SemgrepAnalyzer",
    "CodeQLAnalyzer",
    "FalsePositiveSuppressor",
    "RealTimeScanDashboard",
    "TrivyContainerScanner",
]
