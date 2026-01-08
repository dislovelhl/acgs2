"""
Constitutional Compliance Review Agent.

Code review agent ensuring constitutional compliance in code changes.
Operates in read-only mode by default to prevent unauthorized modifications.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentResult, AgentStatus, BaseGovernanceAgent

logger = logging.getLogger(__name__)


class ComplianceSeverity(Enum):
    """Severity level for compliance issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ComplianceIssue:
    """A compliance issue found during review."""

    file_path: str
    line_number: Optional[int]
    severity: ComplianceSeverity
    rule: str
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ComplianceReport:
    """Full compliance review report."""

    total_files_scanned: int
    issues: List[ComplianceIssue]
    passed: bool
    summary: str
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ComplianceSeverity.CRITICAL)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ComplianceSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ComplianceSeverity.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files_scanned": self.total_files_scanned,
            "issue_count": len(self.issues),
            "critical_count": self.critical_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "passed": self.passed,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


# Constitutional compliance rules
COMPLIANCE_RULES = {
    "HITL-001": {
        "name": "Human-in-the-Loop Required",
        "pattern": r"bypass.*approval|skip.*review|auto.*approve",
        "severity": ComplianceSeverity.CRITICAL,
        "message": "Potential bypass of human oversight detected",
    },
    "CONST-001": {
        "name": "Constitutional Hash Validation",
        "pattern": r"CONSTITUTIONAL_HASH",
        "severity": ComplianceSeverity.ERROR,
        "message": "Constitutional hash must be validated for governance changes",
        "required": True,
    },
    "DFC-001": {
        "name": "DFC Threshold Check",
        "pattern": r"dfc.*threshold|DFC.*THRESHOLD",
        "severity": ComplianceSeverity.WARNING,
        "message": "DFC threshold should be checked for governance decisions",
    },
    "DELIBERATION-001": {
        "name": "Cross-Group Consensus",
        "pattern": r"cross.*group|consensus.*threshold",
        "severity": ComplianceSeverity.WARNING,
        "message": "Cross-group consensus should be validated",
    },
    "AUDIT-001": {
        "name": "Audit Trail",
        "pattern": r"audit.*log|logger\.(info|warning|error)",
        "severity": ComplianceSeverity.INFO,
        "message": "Audit logging recommended for governance actions",
    },
}


class ComplianceReviewAgent(BaseGovernanceAgent):
    """
    Agent for constitutional compliance review.

    Capabilities:
    - Scan codebase for constitutional principle violations
    - Review PRs against governance framework
    - Flag non-compliant patterns (missing HITL, bypassed approvals)
    - Generate compliance reports

    Note: Operates in read-only mode by default.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the compliance review agent."""
        default_config = AgentConfig(
            allowed_tools=["Read", "Glob", "Grep"],  # No Edit/Write
            permission_mode="bypassPermissions",  # Read-only operations
        )

        if config:
            # Ensure no write tools unless explicitly configured
            if "Edit" in (config.allowed_tools or []) or "Write" in (config.allowed_tools or []):
                logger.warning("ComplianceReviewAgent: Edit/Write tools enabled. Use with caution.")
            default_config.allowed_tools = config.allowed_tools or default_config.allowed_tools

        super().__init__("compliance-review-agent", default_config)

        self.rules = COMPLIANCE_RULES.copy()
        self._blocked_operations: List[Dict[str, Any]] = []

    @property
    def description(self) -> str:
        return (
            "Constitutional compliance reviewer for ACGS-2. "
            "Scans code for governance violations and generates compliance reports."
        )

    @property
    def system_prompt(self) -> str:
        return """You are a constitutional compliance review agent for the ACGS-2 system.

Your role is to review code changes and ensure they comply with constitutional governance principles.

Key compliance rules:
1. HITL-001: Human-in-the-Loop must not be bypassed
2. CONST-001: Constitutional hash must be validated for amendments
3. DFC-001: DFC threshold checks should be present for governance decisions
4. DELIBERATION-001: Cross-group consensus must be validated
5. AUDIT-001: Audit logging should be present for governance actions

When reviewing code:
- Flag any patterns that bypass human oversight
- Check for proper constitutional hash validation
- Verify DFC threshold checks are in place
- Ensure deliberation processes include consensus validation
- Recommend adding audit logging where missing

Output format:
- List of compliance issues by severity (CRITICAL, ERROR, WARNING, INFO)
- File paths and line numbers where issues were found
- Specific suggestions for remediation
- Overall compliance status (PASS/FAIL)

IMPORTANT: You are operating in READ-ONLY mode. Do not attempt to modify any files.
"""

    async def run(self, prompt: str) -> AgentResult:
        """
        Execute compliance review.

        Args:
            prompt: Review request (e.g., "Review src/core for compliance")

        Returns:
            AgentResult with compliance report
        """
        self.status = AgentStatus.RUNNING
        logger.info(f"Starting compliance review: {prompt[:100]}...")

        try:
            # Execute pre-tool hooks (including write blocking)
            hook_result = await self._execute_hooks("PreToolUse", {"prompt": prompt})

            if hook_result.get("decision") == "block":
                logger.warning(f"Operation blocked: {hook_result.get('reason')}")
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.CANCELLED,
                    result=f"Operation blocked: {hook_result.get('reason')}",
                )

            # Simulate compliance review
            report = await self._simulate_compliance_review(prompt)

            # Execute post-tool hooks
            await self._execute_hooks(
                "PostToolUse",
                {
                    "prompt": prompt,
                    "report": report.to_dict(),
                },
            )

            # Execute stop hook to generate final report
            await self._execute_hooks("Stop", {"report": report.to_dict()})

            self.status = AgentStatus.COMPLETED

            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                result=self._format_compliance_report(report),
                metrics={
                    "files_scanned": report.total_files_scanned,
                    "issues_found": len(report.issues),
                    "critical_count": report.critical_count,
                    "passed": report.passed,
                },
            )

        except Exception as e:
            logger.error(f"Compliance review failed: {e}")
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def review_file(self, file_path: str, content: str) -> List[ComplianceIssue]:
        """
        Review a single file for compliance issues.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of compliance issues found
        """
        import re

        issues = []

        for rule_id, rule in self.rules.items():
            pattern = rule["pattern"]
            is_required = rule.get("required", False)

            # Search for pattern in content
            matches = list(re.finditer(pattern, content, re.IGNORECASE))

            if is_required and not matches:
                # Required pattern not found
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        line_number=None,
                        severity=rule["severity"],
                        rule=rule_id,
                        message=f"{rule['name']}: Required pattern not found",
                        suggestion=f"Ensure {rule['name']} is implemented",
                    )
                )
            elif not is_required and matches:
                # Problematic pattern found
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    issues.append(
                        ComplianceIssue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=rule["severity"],
                            rule=rule_id,
                            message=f"{rule['name']}: {rule['message']}",
                            suggestion=f"Review line {line_num} for compliance",
                        )
                    )

        return issues

    def add_write_blocking_hook(self) -> None:
        """Add a hook that blocks all write operations."""

        async def block_writes(input_data: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = input_data.get("tool_name", "")

            if tool_name in ["Edit", "Write", "Bash"]:
                self._blocked_operations.append(
                    {
                        "tool": tool_name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "input": input_data,
                    }
                )
                return {
                    "decision": "block",
                    "reason": f"Write operation '{tool_name}' blocked in compliance mode",
                }

            return {}

        self.register_hook("PreToolUse", block_writes)
        logger.info("Write blocking hook enabled")

    async def _simulate_compliance_review(self, prompt: str) -> ComplianceReport:
        """Simulate compliance review for testing."""
        await asyncio.sleep(0.1)

        # Simulated review results
        issues = [
            ComplianceIssue(
                file_path="src/core/services/example.py",
                line_number=42,
                severity=ComplianceSeverity.WARNING,
                rule="DFC-001",
                message="DFC threshold check recommended",
                suggestion="Add DFC validation before governance decision",
            ),
        ]

        return ComplianceReport(
            total_files_scanned=15,
            issues=issues,
            passed=True,  # Warnings don't fail the review
            summary="Compliance review completed with minor warnings",
            recommendations=[
                "Add DFC threshold checks to governance decision points",
                "Consider adding audit logging to approval workflows",
            ],
        )

    def _format_compliance_report(self, report: ComplianceReport) -> str:
        """Format compliance report for display."""
        status_icon = "✓" if report.passed else "✗"

        lines = [
            "# Compliance Review Report",
            "",
            "## Summary",
            f"- Status: {status_icon} {'PASSED' if report.passed else 'FAILED'}",
            f"- Files Scanned: {report.total_files_scanned}",
            f"- Total Issues: {len(report.issues)}",
            f"  - Critical: {report.critical_count}",
            f"  - Errors: {report.error_count}",
            f"  - Warnings: {report.warning_count}",
            "",
        ]

        if report.issues:
            lines.extend(["## Issues", ""])

            for issue in sorted(report.issues, key=lambda x: x.severity.value):
                severity_icon = {
                    ComplianceSeverity.CRITICAL: "🔴",
                    ComplianceSeverity.ERROR: "🟠",
                    ComplianceSeverity.WARNING: "🟡",
                    ComplianceSeverity.INFO: "🔵",
                }[issue.severity]

                line_info = f":{issue.line_number}" if issue.line_number else ""
                lines.append(f"- {severity_icon} **[{issue.rule}]** {issue.file_path}{line_info}")
                lines.append(f"  - {issue.message}")
                if issue.suggestion:
                    lines.append(f"  - Suggestion: {issue.suggestion}")
                lines.append("")

        if report.recommendations:
            lines.extend(
                [
                    "## Recommendations",
                    *[f"- {r}" for r in report.recommendations],
                ]
            )

        return "\n".join(lines)


async def main():
    """Test the compliance review agent."""
    agent = ComplianceReviewAgent()
    agent.add_write_blocking_hook()

    await agent.run("Review src/core for constitutional compliance")


if __name__ == "__main__":
    asyncio.run(main())
