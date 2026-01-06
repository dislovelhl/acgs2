"""
ACGS-2 Analyze Workflow
Constitutional Hash: cdd01ef066bc6cf2

Migrated from SuperClaude sc_analyze.py.
Provides comprehensive code analysis with multi-domain assessment.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.tools.sc_analyze import CodeAnalyzer

from ..base.result import WorkflowResult
from ..base.step import WorkflowStep
from ..base.workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class AnalyzeWorkflow(BaseWorkflow):
    """
    Workflow for code analysis and quality assessment.

    Steps:
    1. Constitutional Validation (Inherited)
    2. Discovery: Identify and categorize source files
    3. Analyze: Perform domain-specific analysis (quality, security, etc.)
    4. Prioritize: Rank findings by severity
    5. Report: Generate analysis report
    """

    def __init__(self, **kwargs):
        super().__init__(workflow_name="analyze_workflow", **kwargs)
        self.analyzer: Optional[CodeAnalyzer] = None

    async def execute(self, input_data: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the analysis workflow.

        Input:
            target: Path to analyze (default: ".")
            focus: Analysis focus (quality, security, performance, architecture, all)
            depth: Analysis depth (quick, deep)
            format: Output format (text, json, report)
        """
        # Always validate first
        await self.validate_constitutional_hash()

        target = input_data.get("target", ".")
        focus = input_data.get("focus", "quality")
        depth = input_data.get("depth", "quick")
        output_format = input_data.get("format", "text")

        # Initialize analyzer
        self.analyzer = CodeAnalyzer(root_path=str(Path.cwd()), focus=focus, depth=depth)

        # Step 1: Discover Files
        discovery_step = WorkflowStep(
            name="discovery",
            description="Discover and categorize source files",
            execute=self._discover_files,
        )
        files = await self.run_step(discovery_step, {"target": target})

        # Step 2: Analyze
        analysis_step = WorkflowStep(
            name="analysis", description=f"Perform {focus} analysis", execute=self._perform_analysis
        )
        analysis_results = await self.run_step(analysis_step, {"files": files, "focus": focus})

        # Step 3: Prioritize
        prioritize_step = WorkflowStep(
            name="prioritize",
            description="Prioritize findings by severity",
            execute=self._prioritize_findings,
        )
        prioritized_findings = await self.run_step(
            prioritize_step, {"findings": analysis_results["findings"]}
        )

        # Step 4: Report
        report_step = WorkflowStep(
            name="report", description="Generate analysis report", execute=self._generate_report
        )
        report = await self.run_step(
            report_step,
            {
                "findings": prioritized_findings,
                "recommendations": analysis_results["recommendations"],
                "metrics": analysis_results["metrics"],
                "format": output_format,
            },
        )

        return await self.complete(report)

    async def _discover_files(self, step_input: Dict[str, Any]) -> Dict[str, List[Path]]:
        """Discovery step implementation."""
        target = step_input["input"].get("target")
        return self.analyzer.discover_files(target)

    async def _perform_analysis(self, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """Analysis step implementation."""
        files = step_input["input"]["files"]
        focus = step_input["input"]["focus"]

        if focus == "quality":
            findings, recommendations, metrics = self.analyzer.analyze_quality(files)
        elif focus == "security":
            findings, recommendations, metrics = self.analyzer.analyze_security(files)
        elif focus == "performance":
            findings, recommendations, metrics = self.analyzer.analyze_performance(files)
        elif focus == "architecture":
            findings, recommendations, metrics = self.analyzer.analyze_architecture(files)
        else:
            # Multi-domain analysis
            all_findings, all_recommendations = [], []
            all_metrics = {}

            for f in ["quality", "security", "performance", "architecture"]:
                func = getattr(self.analyzer, f"analyze_{f}")
                found, recs, met = func(files)
                all_findings.extend(found)
                all_recommendations.extend(recs)
                all_metrics.update(met)

            findings, recommendations, metrics = all_findings, all_recommendations, all_metrics

        return {"findings": findings, "recommendations": recommendations, "metrics": metrics}

    async def _prioritize_findings(self, step_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritization step implementation."""
        findings = step_input["input"]["findings"]
        return self.analyzer.prioritize_findings(findings)

    async def _generate_report(self, step_input: Dict[str, Any]) -> str:
        """Reporting step implementation."""
        data = step_input["input"]
        return self.analyzer.generate_report(
            findings=data["findings"],
            recommendations=data["recommendations"],
            metrics=data["metrics"],
            format_type=data["format"],
        )
