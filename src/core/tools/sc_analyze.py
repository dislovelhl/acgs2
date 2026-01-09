#!/usr/bin/env python3
"""
Constitutional Hash: cdd01ef066bc6cf2

SuperClaude Analyze Command (/sc:analyze)
Code analysis and quality assessment system.

Usage:
/sc:analyze [target] [--focus quality|security|performance|architecture] [--depth quick|deep] [--format text|json|report]

This command provides comprehensive code analysis with:
- Multi-domain analysis (quality, security, performance, architecture)
- Severity-based prioritization of findings
- Actionable recommendations with implementation guidance
- Comprehensive reporting with metrics and improvement roadmap
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CodeAnalyzer:
    """Comprehensive code analyzer with multi-domain assessment capabilities."""

    SEVERITY_LEVELS = ["critical", "high", "medium", "low", "info"]

    def __init__(self, root_path: str, focus: str = "quality", depth: str = "quick"):
        self.root_path = Path(root_path)
        self.focus = focus
        self.depth = depth
        self.project_name = self._detect_project_name()
        self.findings: List[Dict] = []
        self.recommendations: List[Dict] = []
        self.metrics: Dict = {}

    def _detect_project_name(self) -> str:
        """Detect project name from various sources."""
        # Try pyproject.toml
        pyproject_path = self.root_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    return str(
                        data.get("tool", {})
                        .get("poetry", {})
                        .get("name", data.get("project", {}).get("name", "Unknown Project"))
                    )
            except (ImportError, FileNotFoundError, KeyError):
                pass

        # Try package.json
        package_path = self.root_path / "package.json"
        if package_path.exists():
            try:
                with open(package_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return str(data.get("name", "Unknown Project"))
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

        return self.root_path.name

    def discover_files(self, target: Optional[str] = None) -> Dict[str, List[Path]]:
        """Phase 1: Discover and categorize source files."""

        search_path = self.root_path / target if target else self.root_path

        file_categories: Dict[str, List[Path]] = {
            "python": [],
            "typescript": [],
            "javascript": [],
            "go": [],
            "java": [],
            "config": [],
            "tests": [],
            "docs": [],
        }

        # Common ignore patterns
        ignore_patterns = {
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
            "htmlcov",
            "coverage",
            ".coverage",
            ".tox",
            ".eggs",
            "*.egg-info",
        }

        extensions_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "go",
            ".java": "java",
            ".json": "config",
            ".yaml": "config",
            ".yml": "config",
            ".toml": "config",
            ".md": "docs",
        }

        for path in search_path.rglob("*"):
            if path.is_file():
                # Skip ignored paths
                if any(ignore in str(path) for ignore in ignore_patterns):
                    continue

                # Categorize by extension
                ext = path.suffix.lower()
                if ext in extensions_map:
                    category = extensions_map[ext]
                    file_categories[category].append(path)

                # Detect test files
                if "test" in path.name.lower() or "spec" in path.name.lower():
                    file_categories["tests"].append(path)

        total_files = sum(len(files) for files in file_categories.values())
        print(  # noqa: T201
            f"  Found {total_files} files across {len([k for k, v in file_categories.items() if v])} categories"
        )

        return file_categories

    def analyze_quality(self, files: Dict[str, List[Path]]) -> Tuple[List[Dict], List[Dict], Dict]:
        """Analyze code quality across multiple dimensions."""

        findings = []
        recommendations = []
        metrics = {
            "total_files": sum(len(files) for files in files.values()),
            "total_lines": 0,
            "complexity_issues": 0,
            "style_issues": 0,
            "documentation_coverage": 0.0,
        }

        # Analyze Python files
        for py_file in files.get("python", []):
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    lines = content.split("\n")
                    metrics["total_lines"] += len(lines)

                    # Check for common quality issues
                    if len(lines) > 1000:
                        findings.append(
                            {
                                "file": str(py_file.relative_to(self.root_path)),
                                "line": 1,
                                "severity": "medium",
                                "category": "quality",
                                "issue": "Large file detected",
                                "description": f"File has {len(lines)} lines. Consider splitting into smaller modules.",
                                "recommendation": "Break down into smaller, focused modules (aim for <500 lines)",
                            }
                        )

                    # Check for long functions
                    for i, line in enumerate(lines, 1):
                        if re.match(r"^\s*def\s+\w+", line):
                            # Simple function length check
                            func_start = i
                            indent_level = len(line) - len(line.lstrip())
                            func_lines = 0
                            for j in range(i + 1, min(i + 200, len(lines))):
                                if (
                                    lines[j].strip()
                                    and len(lines[j]) - len(lines[j].lstrip()) <= indent_level
                                ):
                                    break
                                func_lines += 1

                            if func_lines > 100:
                                findings.append(
                                    {
                                        "file": str(py_file.relative_to(self.root_path)),
                                        "line": func_start,
                                        "severity": "medium",
                                        "category": "quality",
                                        "issue": "Long function detected",
                                        "description": f"Function starting at line {func_start} has {func_lines} lines.",
                                        "recommendation": "Refactor into smaller functions (aim for <50 lines)",
                                    }
                                )

                    # Check documentation coverage
                    has_docstring = '"""' in content or "'''" in content
                    pass

                    if not has_docstring and len(lines) > 20:
                        findings.append(
                            {
                                "file": str(py_file.relative_to(self.root_path)),
                                "line": 1,
                                "severity": "low",
                                "category": "quality",
                                "issue": "Missing module docstring",
                                "description": "File lacks module-level documentation",
                                "recommendation": "Add module docstring describing purpose and usage",
                            }
                        )

            except Exception as e:
                if self.depth == "deep":
                    findings.append(
                        {
                            "file": str(py_file.relative_to(self.root_path)),
                            "line": 0,
                            "severity": "info",
                            "category": "quality",
                            "issue": "Analysis error",
                            "description": f"Could not analyze file: {str(e)}",
                            "recommendation": "Manual review recommended",
                        }
                    )

        # Generate recommendations based on findings
        if findings:
            critical_count = len([f for f in findings if f["severity"] == "critical"])
            high_count = len([f for f in findings if f["severity"] == "high"])

            if critical_count > 0:
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "quality",
                        "title": "Address critical quality issues",
                        "description": f"{critical_count} critical issues found requiring immediate attention",
                        "action": "Review and fix critical findings first",
                        "benefits": "Improves code maintainability and reduces technical debt",
                    }
                )

            if high_count > 5:
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": "quality",
                        "title": "Establish code quality standards",
                        "description": "Multiple high-severity issues suggest need for coding standards",
                        "action": "Implement linting rules and code review guidelines",
                        "benefits": "Prevents future quality issues and improves consistency",
                    }
                )

        return findings, recommendations, metrics

    def analyze_security(self, files: Dict[str, List[Path]]) -> Tuple[List[Dict], List[Dict], Dict]:
        """Analyze security vulnerabilities and compliance."""

        findings = []
        recommendations = []
        metrics = {"vulnerabilities": 0, "secrets_detected": 0, "insecure_patterns": 0}

        # Security patterns to check
        security_patterns = {
            "hardcoded_secrets": [
                (r'password\s*=\s*["\']\w+["\']', "Hardcoded password detected"),
                (r'api_key\s*=\s*["\']\w+["\']', "Hardcoded API key detected"),
                (r'secret\s*=\s*["\']\w+["\']', "Hardcoded secret detected"),
                (r'token\s*=\s*["\']\w+["\']', "Hardcoded token detected"),
            ],
            "sql_injection": [
                (r'execute\s*\(\s*["\'].*%s.*["\']', "Potential SQL injection vulnerability"),
                (
                    r'query\s*\(\s*f["\'].*\{.*\}.*["\']',
                    "Potential SQL injection in f-string query",
                ),
            ],
            "command_injection": [
                (r"os\.system\s*\(", "Use of os.system() - potential command injection"),
                (
                    r"subprocess\.call\s*\([^,]+shell\s*=\s*True",
                    "Shell=True in subprocess - potential injection",
                ),
            ],
            "insecure_random": [
                (r"random\.\w+\(", "Use of insecure random module"),
            ],
        }

        for category, patterns in security_patterns.items():
            for py_file in files.get("python", []):
                try:
                    with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")

                        for pattern, description in patterns:
                            for i, line in enumerate(lines, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    severity = "high" if "injection" in category else "medium"
                                    findings.append(
                                        {
                                            "file": str(py_file.relative_to(self.root_path)),
                                            "line": i,
                                            "severity": severity,
                                            "category": "security",
                                            "issue": description,
                                            "description": f"Potential security vulnerability: {description}",
                                            "recommendation": self._get_security_recommendation(
                                                category
                                            ),
                                        }
                                    )
                                    metrics["vulnerabilities"] += 1
                                    break
                except Exception:
                    continue

        # Generate security recommendations
        if metrics["vulnerabilities"] > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "security",
                    "title": "Address security vulnerabilities",
                    "description": f"{metrics['vulnerabilities']} security issues found",
                    "action": "Review and remediate security findings immediately",
                    "benefits": "Reduces security risk and improves compliance",
                }
            )

        return findings, recommendations, metrics

    def analyze_performance(
        self, files: Dict[str, List[Path]]
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """Analyze performance bottlenecks and optimization opportunities."""

        findings = []
        recommendations = []
        metrics = {"bottlenecks": 0, "optimization_opportunities": 0}

        # Performance anti-patterns
        performance_patterns = {
            "nested_loops": [
                (
                    r"for\s+\w+\s+in\s+.*:\s*\n\s*for\s+\w+\s+in\s+.*:",
                    "Nested loops detected - O(n²) complexity",
                ),
            ],
            "inefficient_queries": [
                (r"\.all\(\)\s*\[:", "Loading all records then slicing - inefficient"),
            ],
            "synchronous_io": [
                (
                    r"open\s*\([^)]+\)\s*\.read\(\)",
                    "Synchronous file I/O in potentially async context",
                ),
            ],
        }

        for py_file in files.get("python", []):
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    content.split("\n")

                    for category, patterns in performance_patterns.items():
                        for pattern, description in patterns:
                            if re.search(pattern, content, re.MULTILINE):
                                findings.append(
                                    {
                                        "file": str(py_file.relative_to(self.root_path)),
                                        "line": 1,
                                        "severity": "medium",
                                        "category": "performance",
                                        "issue": description,
                                        "description": f"Performance issue: {description}",
                                        "recommendation": self._get_performance_recommendation(
                                            category
                                        ),
                                    }
                                )
                                metrics["bottlenecks"] += 1
                                break
            except Exception:
                continue

        if metrics["bottlenecks"] > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "performance",
                    "title": "Optimize performance bottlenecks",
                    "description": f"{metrics['bottlenecks']} performance issues identified",
                    "action": "Profile and optimize identified bottlenecks",
                    "benefits": "Improves application responsiveness and resource efficiency",
                }
            )

        return findings, recommendations, metrics

    def analyze_architecture(
        self, files: Dict[str, List[Path]]
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """Analyze architecture and technical debt."""

        findings = []
        recommendations = []
        metrics = {"circular_dependencies": 0, "coupling_issues": 0, "technical_debt": 0}

        # Architecture patterns
        for py_file in files.get("python", []):
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                    # Check for circular imports
                    imports = re.findall(r"^import\s+(\w+)|^from\s+(\w+)", content, re.MULTILINE)
                    if len(set(imports)) > 20:
                        findings.append(
                            {
                                "file": str(py_file.relative_to(self.root_path)),
                                "line": 1,
                                "severity": "low",
                                "category": "architecture",
                                "issue": "High import count",
                                "description": f"File has {len(set(imports))} imports - potential coupling issue",
                                "recommendation": "Consider dependency injection or refactoring to reduce coupling",
                            }
                        )
                        metrics["coupling_issues"] += 1
            except Exception:
                continue

        recommendations.append(
            {
                "priority": "low",
                "category": "architecture",
                "title": "Review architecture patterns",
                "description": "Consider architectural improvements for maintainability",
                "action": "Conduct architecture review and document patterns",
                "benefits": "Improves long-term maintainability and scalability",
            }
        )

        return findings, recommendations, metrics

    def _get_security_recommendation(self, category: str) -> str:
        """Get security-specific recommendation."""
        recommendations = {
            "hardcoded_secrets": "Use environment variables or secret management system",
            "sql_injection": "Use parameterized queries or ORM methods",
            "command_injection": "Use subprocess with explicit arguments, avoid shell=True",
            "insecure_random": "Use secrets module for cryptographic randomness",
        }
        return recommendations.get(category, "Review security best practices")

    def _get_performance_recommendation(self, category: str) -> str:
        """Get performance-specific recommendation."""
        recommendations = {
            "nested_loops": "Consider using itertools or vectorized operations",
            "inefficient_queries": "Use database-level filtering with limit/offset",
            "synchronous_io": "Consider async/await for I/O operations",
        }
        return recommendations.get(category, "Profile and optimize based on actual usage")

    def prioritize_findings(self, findings: List[Dict]) -> List[Dict]:
        """Phase 3: Prioritize findings by severity and impact."""

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        return sorted(findings, key=lambda x: severity_order.get(x["severity"], 99))

    def generate_report(
        self,
        findings: List[Dict],
        recommendations: List[Dict],
        metrics: Dict,
        format_type: str = "text",
    ) -> str:
        """Phase 4: Generate comprehensive analysis report."""

        if format_type == "json":
            return json.dumps(
                {
                    "project": self.project_name,
                    "analysis_date": datetime.now().isoformat(),
                    "focus": self.focus,
                    "depth": self.depth,
                    "summary": {
                        "total_findings": len(findings),
                        "findings_by_severity": {
                            sev: len([f for f in findings if f["severity"] == sev])
                            for sev in self.SEVERITY_LEVELS
                        },
                        "total_recommendations": len(recommendations),
                    },
                    "findings": findings,
                    "recommendations": recommendations,
                    "metrics": metrics,
                },
                indent=2,
            )

        # Text/Report format
        report_lines = [
            f"# Code Analysis Report: {self.project_name}",
            f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Focus**: {self.focus}",
            f"**Depth**: {self.depth}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Findings**: {len(findings)}",
            f"- **Critical**: {len([f for f in findings if f['severity'] == 'critical'])}",
            f"- **High**: {len([f for f in findings if f['severity'] == 'high'])}",
            f"- **Medium**: {len([f for f in findings if f['severity'] == 'medium'])}",
            f"- **Low**: {len([f for f in findings if f['severity'] == 'low'])}",
            f"- **Recommendations**: {len(recommendations)}",
            "",
            "## Findings",
            "",
        ]

        # Group findings by severity
        by_severity = defaultdict(list)
        for finding in findings:
            by_severity[finding["severity"]].append(finding)

        for severity in self.SEVERITY_LEVELS:
            if severity in by_severity:
                report_lines.extend([f"### {severity.upper()} Severity", ""])
                for finding in by_severity[severity]:
                    report_lines.extend(
                        [
                            f"**{finding['issue']}**",
                            f"- File: `{finding['file']}`",
                            f"- Line: {finding['line']}",
                            f"- Description: {finding['description']}",
                            f"- Recommendation: {finding['recommendation']}",
                            "",
                        ]
                    )

        report_lines.extend(["## Recommendations", ""])

        for rec in recommendations:
            report_lines.extend(
                [
                    f"### {rec['title']} ({rec['priority']} priority)",
                    f"- **Category**: {rec['category']}",
                    f"- **Description**: {rec['description']}",
                    f"- **Action**: {rec['action']}",
                    f"- **Benefits**: {rec['benefits']}",
                    "",
                ]
            )

        report_lines.extend(["## Metrics", "", "```json", json.dumps(metrics, indent=2), "```"])

        return "\n".join(report_lines)

    def run(self, target: Optional[str] = None, output_path: Optional[str] = None):
        """Execute complete analysis workflow."""

        # Phase 1: Discover
        files = self.discover_files(target)

        # Phase 2: Analyze based on focus
        if self.focus == "quality":
            findings, recommendations, metrics = self.analyze_quality(files)
        elif self.focus == "security":
            findings, recommendations, metrics = self.analyze_security(files)
        elif self.focus == "performance":
            findings, recommendations, metrics = self.analyze_performance(files)
        elif self.focus == "architecture":
            findings, recommendations, metrics = self.analyze_architecture(files)
        else:
            # Multi-domain analysis
            all_findings = []
            all_recommendations = []
            all_metrics = {}

            q_findings, q_recs, q_metrics = self.analyze_quality(files)
            s_findings, s_recs, s_metrics = self.analyze_security(files)
            p_findings, p_recs, p_metrics = self.analyze_performance(files)
            a_findings, a_recs, a_metrics = self.analyze_architecture(files)

            all_findings.extend(q_findings + s_findings + p_findings + a_findings)
            all_recommendations.extend(q_recs + s_recs + p_recs + a_recs)
            all_metrics = {**q_metrics, **s_metrics, **p_metrics, **a_metrics}

            findings, recommendations, metrics = all_findings, all_recommendations, all_metrics

        # Phase 3: Prioritize
        findings = self.prioritize_findings(findings)

        # Phase 4: Generate report
        format_type = "json" if output_path and output_path.endswith(".json") else "text"
        report = self.generate_report(findings, recommendations, metrics, format_type)

        # Phase 5: Save
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)


def main():
    parser = argparse.ArgumentParser(
        description="SuperClaude Analyze - Code Analysis and Quality Assessment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --focus quality
  %(prog)s src/auth --focus security --depth deep
  %(prog)s --focus performance --format json --output analysis.json
  %(prog)s src/components --focus quality --depth quick
        """,
    )

    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target directory or file to analyze (default: current directory)",
    )

    parser.add_argument(
        "--focus",
        choices=["quality", "security", "performance", "architecture"],
        default="quality",
        help="Analysis focus area (default: quality)",
    )

    parser.add_argument(
        "--depth",
        choices=["quick", "deep"],
        default="quick",
        help="Analysis depth (default: quick)",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "report"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = CodeAnalyzer(args.target, focus=args.focus, depth=args.depth)

    # Run analysis
    analyzer.run(target=args.target, output_path=args.output)


if __name__ == "__main__":
    main()
