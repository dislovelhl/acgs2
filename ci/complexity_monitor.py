#!/usr/bin/env python3
"""
Code Complexity Monitoring Script for ACGS-2 CI/CD Pipeline.

This script monitors code complexity metrics to ensure maintainability and prevent
code quality degradation over time.

Monitors:
- Cyclomatic Complexity (McCabe)
- Lines of Code (LOC)
- Function/Class size limits
- Test file sizes
- Import complexity
- Coupling metrics

Constitutional Hash: cdd01ef066bc6cf2
"""

import ast
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ComplexityMetrics:
    """Container for complexity metrics."""

    file_path: str
    lines_of_code: int
    cyclomatic_complexity: int
    function_count: int
    class_count: int
    max_function_length: int
    max_class_length: int
    import_count: int
    test_class_count: int
    violations: List[str]


@dataclass
class ComplexityThresholds:
    """Thresholds for complexity monitoring."""

    max_lines_per_file: int = 1000
    max_cyclomatic_complexity: int = 15
    max_lines_per_function: int = 50
    max_lines_per_class: int = 300
    max_lines_per_test_file: int = 800
    max_imports_per_file: int = 30
    max_functions_per_class: int = 20


class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code complexity."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.complexity = 0
        self.function_count = 0
        self.class_count = 0
        self.functions: List[Tuple[str, int, int]] = []  # (name, start_line, end_line)
        self.classes: List[Tuple[str, int, int]] = []  # (name, start_line, end_line)
        self.import_count = 0
        self.test_class_count = 0

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.function_count += 1
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line + 1)
        self.functions.append((node.name, start_line, end_line))

        # Calculate cyclomatic complexity
        func_complexity = self._calculate_function_complexity(node)
        self.complexity = max(self.complexity, func_complexity)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.class_count += 1
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line + 1)
        self.classes.append((node.name, start_line, end_line))

        # Check if it's a test class
        if node.name.startswith("Test"):
            self.test_class_count += 1

        self.generic_visit(node)

    def visit_Import(self, node):
        """Visit import statements."""
        self.import_count += 1

    def visit_ImportFrom(self, node):
        """Visit from import statements."""
        self.import_count += 1

    def _calculate_function_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp) and len(child.values) > 1:
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers) + 1
            elif isinstance(child, ast.comprehension):
                complexity += 1

        return complexity


def analyze_file(file_path: Path, thresholds: ComplexityThresholds) -> ComplexityMetrics:
    """Analyze a single Python file for complexity metrics."""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines_of_code = len(content.splitlines())

        # Parse AST
        tree = ast.parse(content, filename=str(file_path))
        analyzer = ComplexityAnalyzer(str(file_path))
        analyzer.visit(tree)

        # Calculate metrics
        max_function_length = 0
        max_class_length = 0

        for _, start, end in analyzer.functions:
            length = end - start + 1
            max_function_length = max(max_function_length, length)

        for _, start, end in analyzer.classes:
            length = end - start + 1
            max_class_length = max(max_class_length, length)

        # Check for violations
        violations = []

        if lines_of_code > thresholds.max_lines_per_file:
            violations.append(
                f"File too large: {lines_of_code} lines (max: {thresholds.max_lines_per_file})"
            )

        if analyzer.complexity > thresholds.max_cyclomatic_complexity:
            violations.append(
                f"High cyclomatic complexity: {analyzer.complexity} (max: {thresholds.max_cyclomatic_complexity})"
            )

        if max_function_length > thresholds.max_lines_per_function:
            violations.append(
                f"Function too long: {max_function_length} lines (max: {thresholds.max_lines_per_function})"
            )

        if max_class_length > thresholds.max_lines_per_class:
            violations.append(
                f"Class too long: {max_class_length} lines (max: {thresholds.max_lines_per_class})"
            )

        if "test" in str(file_path).lower() and lines_of_code > thresholds.max_lines_per_test_file:
            violations.append(
                f"Test file too large: {lines_of_code} lines (max: {thresholds.max_lines_per_test_file})"
            )

        if analyzer.import_count > thresholds.max_imports_per_file:
            violations.append(
                f"Too many imports: {analyzer.import_count} (max: {thresholds.max_imports_per_file})"
            )

        if (
            analyzer.class_count > 0
            and analyzer.function_count > thresholds.max_functions_per_class * analyzer.class_count
        ):
            violations.append(
                f"Too many functions per class: {analyzer.function_count} functions in {analyzer.class_count} classes"
            )

        return ComplexityMetrics(
            file_path=str(file_path),
            lines_of_code=lines_of_code,
            cyclomatic_complexity=analyzer.complexity,
            function_count=analyzer.function_count,
            class_count=analyzer.class_count,
            max_function_length=max_function_length,
            max_class_length=max_class_length,
            import_count=analyzer.import_count,
            test_class_count=analyzer.test_class_count,
            violations=violations,
        )

    except Exception as e:
        return ComplexityMetrics(
            file_path=str(file_path),
            lines_of_code=0,
            cyclomatic_complexity=0,
            function_count=0,
            class_count=0,
            max_function_length=0,
            max_class_length=0,
            import_count=0,
            test_class_count=0,
            violations=[f"Analysis failed: {str(e)}"],
        )


def analyze_project(
    root_path: str, thresholds: ComplexityThresholds
) -> Dict[str, List[ComplexityMetrics]]:
    """Analyze all Python files in the project."""

    results = {"passed": [], "violations": []}

    for file_path in Path(root_path).rglob("*.py"):
        # Skip certain directories
        if any(skip in str(file_path) for skip in ["__pycache__", ".venv", "node_modules", ".git"]):
            continue

        metrics = analyze_file(file_path, thresholds)

        if metrics.violations:
            results["violations"].append(metrics)
        else:
            results["passed"].append(metrics)

    return results


def generate_report(
    results: Dict[str, List[ComplexityMetrics]], output_path: Optional[str] = None
) -> str:
    """Generate a complexity analysis report."""

    total_files = len(results["passed"]) + len(results["violations"])
    violation_count = len(results["violations"])

    report = []
    report.append("=" * 80)
    report.append("CODE COMPLEXITY ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"Total files analyzed: {total_files}")
    report.append(f"Files with violations: {violation_count}")
    report.append(f"Clean files: {len(results['passed'])}")
    report.append("")

    if results["violations"]:
        report.append("🚨 FILES WITH COMPLEXITY VIOLATIONS:")
        report.append("-" * 50)

        for metrics in sorted(results["violations"], key=lambda x: len(x.violations), reverse=True):
            report.append(f"📁 {metrics.file_path}")
            report.append(
                f"   Lines: {metrics.lines_of_code}, Complexity: {metrics.cyclomatic_complexity}"
            )
            for violation in metrics.violations:
                report.append(f"   ❌ {violation}")
            report.append("")

    # Summary statistics
    if results["passed"] or results["violations"]:
        all_metrics = results["passed"] + results["violations"]
        avg_loc = sum(m.lines_of_code for m in all_metrics) / len(all_metrics)
        max_loc = max(m.lines_of_code for m in all_metrics)
        avg_complexity = sum(m.cyclomatic_complexity for m in all_metrics) / len(all_metrics)

        report.append("📊 SUMMARY STATISTICS:")
        report.append("-" * 30)
        report.append(f"Average lines per file: {avg_loc:.1f}")
        report.append(f"Maximum lines in file: {max_loc}")
        report.append(f"Average cyclomatic complexity: {avg_complexity:.1f}")
        report.append("")

    # Save detailed results to JSON if output path provided
    if output_path:
        detailed_results = {
            "summary": {
                "total_files": total_files,
                "violation_files": violation_count,
                "clean_files": len(results["passed"]),
            },
            "violations": [asdict(m) for m in results["violations"]],
            "passed": [asdict(m) for m in results["passed"]],
        }

        with open(output_path, "w") as f:
            json.dump(detailed_results, f, indent=2)

    return "\n".join(report)


def main():
    """Main entry point for complexity monitoring."""

    import argparse

    parser = argparse.ArgumentParser(description="Code Complexity Monitoring")
    parser.add_argument("--path", default=".", help="Root path to analyze")
    parser.add_argument("--thresholds", help="JSON file with custom thresholds")
    parser.add_argument("--output", help="Output JSON file for detailed results")
    parser.add_argument(
        "--fail-on-violations", action="store_true", help="Exit with error code on violations"
    )

    args = parser.parse_args()

    # Load custom thresholds if provided
    thresholds = ComplexityThresholds()
    if args.thresholds and os.path.exists(args.thresholds):
        with open(args.thresholds, "r") as f:
            threshold_data = json.load(f)
            for key, value in threshold_data.items():
                if hasattr(thresholds, key):
                    setattr(thresholds, key, value)

    # Analyze project
    print("🔍 Analyzing code complexity...")
    results = analyze_project(args.path, thresholds)

    # Generate and print report
    report = generate_report(results, args.output)
    print(report)

    # Exit with appropriate code
    violation_count = len(results["violations"])
    if args.fail_on_violations and violation_count > 0:
        print(f"❌ Complexity check FAILED: {violation_count} files with violations")
        sys.exit(1)
    else:
        print("✅ Complexity check PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
