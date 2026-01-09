#!/usr/bin/env python3
"""
Quarterly Code Quality Review System for ACGS-2.

This script generates comprehensive quarterly reports on code quality metrics,
identifies trends, and provides actionable recommendations for maintaining
code quality standards.

Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List


class QuarterlyCodeReview:
    """Manages quarterly code quality review processes."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.quarter = self._get_current_quarter()
        self.year = datetime.now().year
        self.reports_dir = self.project_root / "reports" / "quarterly_reviews"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_quarter(self) -> int:
        """Get the current quarter (1-4)."""
        month = datetime.now().month
        return (month - 1) // 3 + 1

    def _run_complexity_analysis(self) -> Dict[str, Any]:
        """Run complexity analysis using the complexity monitor."""
        complexity_script = self.project_root / "ci" / "complexity_monitor.py"
        output_file = self.reports_dir / f"complexity_q{self.quarter}_{self.year}.json"

        cmd = [
            sys.executable,
            str(complexity_script),
            "--path",
            str(self.project_root),
            "--output",
            str(output_file),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            with open(output_file, "r") as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Complexity analysis failed: {str(e)}"}

    def _analyze_test_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage trends."""
        coverage_files = list(self.project_root.glob("**/coverage.xml"))
        coverage_data = {}

        for coverage_file in coverage_files:
            try:
                # Parse coverage XML (simplified)
                with open(coverage_file, "r") as f:
                    content = f.read()
                    # Extract coverage percentage (simplified parsing)
                    if "line-rate=" in content:
                        rate_str = content.split('line-rate="')[1].split('"')[0]
                        coverage_data[str(coverage_file)] = float(rate_str) * 100
            except Exception:
                continue

        return {
            "coverage_files": len(coverage_data),
            "average_coverage": (
                sum(coverage_data.values()) / len(coverage_data) if coverage_data else 0
            ),
            "coverage_by_file": coverage_data,
        }

    def _analyze_code_churn(self) -> Dict[str, Any]:
        """Analyze code churn metrics using git history."""
        try:
            # Get commits in the last quarter
            quarter_start = datetime.now() - timedelta(days=90)
            since_date = quarter_start.strftime("%Y-%m-%d")

            # Run git log to get commit statistics
            cmd = ["git", "log", f"--since={since_date}", "--pretty=format:", "--numstat"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            lines_added = 0
            lines_deleted = 0
            files_changed = set()

            for line in result.stdout.split("\n"):
                if line.strip() and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        try:
                            added = int(parts[0]) if parts[0].isdigit() else 0
                            deleted = int(parts[1]) if parts[1].isdigit() else 0
                            filename = parts[2]

                            lines_added += added
                            lines_deleted += deleted
                            files_changed.add(filename)
                        except ValueError:
                            continue

            return {
                "quarter_start": since_date,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
                "net_change": lines_added - lines_deleted,
                "files_changed": len(files_changed),
            }

        except Exception as e:
            return {"error": f"Code churn analysis failed: {str(e)}"}

    def _analyze_technical_debt(self) -> Dict[str, Any]:
        """Analyze technical debt indicators."""
        debt_indicators = {
            "large_files": [],
            "complex_functions": [],
            "missing_tests": [],
            "outdated_dependencies": [],
        }

        # Find large files (>1000 lines)
        for py_file in self.project_root.rglob("*.py"):
            if py_file.stat().st_size > 100000:  # ~1000 lines
                debt_indicators["large_files"].append(str(py_file))

        # Find files without corresponding tests
        for py_file in self.project_root.rglob("src/**/*.py"):
            if not py_file.name.startswith("test_"):
                test_file = py_file.parent / f"test_{py_file.name}"
                if not test_file.exists():
                    debt_indicators["missing_tests"].append(str(py_file))

        return debt_indicators

    def _generate_recommendations(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Complexity-based recommendations
        if "complexity" in analysis_data:
            complexity_data = analysis_data["complexity"]
            if complexity_data.get("violations", []):
                violation_count = len(complexity_data["violations"])
                recommendations.append(
                    f"🔧 Address {violation_count} complexity violations identified"
                )
                recommendations.append(
                    "   - Split large test files (>800 lines) into smaller modules"
                )
                recommendations.append(
                    "   - Refactor functions with high cyclomatic complexity (>15)"
                )
                recommendations.append("   - Break down large classes (>300 lines)")

        # Coverage-based recommendations
        if "coverage" in analysis_data:
            coverage_data = analysis_data["coverage"]
            avg_coverage = coverage_data.get("average_coverage", 0)
            if avg_coverage < 80:
                recommendations.append(
                    f"📊 Improve test coverage: currently {avg_coverage:.1f}% (target: >80%)"
                )
                recommendations.append("   - Add unit tests for uncovered modules")
                recommendations.append("   - Implement integration tests for critical paths")

        # Churn-based recommendations
        if "churn" in analysis_data:
            churn_data = analysis_data["churn"]
            net_change = churn_data.get("net_change", 0)
            if net_change > 5000:  # High churn
                recommendations.append(
                    f"⚡ High code churn detected: {net_change} net lines changed"
                )
                recommendations.append("   - Review recent changes for refactoring opportunities")
                recommendations.append("   - Consider architectural improvements")

        # Technical debt recommendations
        if "technical_debt" in analysis_data:
            debt_data = analysis_data["technical_debt"]
            large_files = debt_data.get("large_files", [])
            if large_files:
                recommendations.append(f"🏗️ Refactor {len(large_files)} large files (>1000 lines)")
                recommendations.append("   - Apply established splitting patterns for test files")
                recommendations.append("   - Extract utility functions from large modules")

        return recommendations

    def generate_quarterly_report(self) -> str:
        """Generate the complete quarterly code quality report."""

        print(f"📊 Generating Q{self.quarter} {self.year} Code Quality Review...")

        # Run all analyses
        analysis_data = {
            "complexity": self._run_complexity_analysis(),
            "coverage": self._analyze_test_coverage(),
            "churn": self._analyze_code_churn(),
            "technical_debt": self._analyze_technical_debt(),
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(analysis_data)

        # Create the report
        report_path = self.reports_dir / f"code_quality_review_q{self.quarter}_{self.year}.md"

        report_content = f"""# ACGS-2 Quarterly Code Quality Review
## Q{self.quarter} {self.year}

**Report Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Constitutional Hash:** cdd01ef066bc6cf2

---

## 📈 Executive Summary

This quarterly review assesses code quality metrics, identifies trends, and provides
actionable recommendations for maintaining high code quality standards.

---

## 🔍 Complexity Analysis

"""

        if "error" not in analysis_data["complexity"]:
            complexity = analysis_data["complexity"]
            report_content += f"""- **Total Files Analyzed:** {complexity.get("summary", {}).get("total_files", 0)}
- **Files with Violations:** {complexity.get("summary", {}).get("violation_files", 0)}
- **Clean Files:** {complexity.get("summary", {}).get("clean_files", 0)}

"""
        else:
            report_content += (
                f"❌ Complexity analysis failed: {analysis_data['complexity']['error']}\n\n"
            )

        report_content += """## 📊 Test Coverage

"""

        coverage = analysis_data["coverage"]
        report_content += f"""- **Coverage Files:** {coverage.get("coverage_files", 0)}
- **Average Coverage:** {coverage.get("average_coverage", 0):.1f}%

"""

        report_content += """## ⚡ Code Churn

"""

        churn = analysis_data["churn"]
        if "error" not in churn:
            report_content += f"""- **Lines Added:** {churn.get("lines_added", 0):,}
- **Lines Deleted:** {churn.get("lines_deleted", 0):,}
- **Net Change:** {churn.get("net_change", 0):,}
- **Files Changed:** {churn.get("files_changed", 0)}

"""
        else:
            report_content += f"❌ Code churn analysis failed: {churn['error']}\n\n"

        report_content += """## 🏗️ Technical Debt Indicators

"""

        debt = analysis_data["technical_debt"]
        report_content += f"""- **Large Files (>1000 lines):** {len(debt.get("large_files", []))}
- **Missing Tests:** {len(debt.get("missing_tests", []))}
- **Complex Functions:** {len(debt.get("complex_functions", []))}

"""

        report_content += """## 🎯 Recommendations

"""

        for rec in recommendations:
            report_content += f"- {rec}\n"

        report_content += """

---

## 📋 Action Items

### Immediate Actions (Next Sprint)
- [ ] Review and address high-priority complexity violations
- [ ] Improve test coverage for critical modules
- [ ] Refactor identified large files

### Short-term Goals (Next Quarter)
- [ ] Establish code quality gates in CI/CD
- [ ] Implement automated refactoring tools
- [ ] Train team on complexity management

### Long-term Vision (Next Year)
- [ ] Achieve >90% test coverage across all modules
- [ ] Maintain complexity metrics within acceptable thresholds
- [ ] Implement AI-assisted code review processes

---

*This report was generated automatically by the ACGS-2 Code Quality Review System.*
"""

        # Write the report
        with open(report_path, "w") as f:
            f.write(report_content)

        # Save detailed analysis data
        data_path = self.reports_dir / f"analysis_data_q{self.quarter}_{self.year}.json"
        with open(data_path, "w") as f:
            json.dump(analysis_data, f, indent=2, default=str)

        print(f"✅ Quarterly review report generated: {report_path}")
        return str(report_path)


def main():
    """Main entry point for quarterly code review."""
    import argparse

    parser = argparse.ArgumentParser(description="Quarterly Code Quality Review")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument(
        "--generate-report", action="store_true", help="Generate the quarterly report"
    )

    args = parser.parse_args()

    if args.generate_report:
        reviewer = QuarterlyCodeReview(args.project_root)
        report_path = reviewer.generate_quarterly_report()
        print(f"Report saved to: {report_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
