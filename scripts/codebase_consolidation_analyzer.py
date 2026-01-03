#!/usr/bin/env python3
"""
ACGS-2 Codebase Consolidation Analyzer
Identifies redundant utilities and consolidation opportunities in the 52k+ Python files.
"""

import ast
import hashlib
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class CodeMetrics:
    """Metrics for a code file."""

    file_path: str
    lines_of_code: int
    functions: List[str]
    classes: List[str]
    imports: List[str]
    complexity_score: int
    last_modified: float
    hash: str


@dataclass
class ConsolidationOpportunity:
    """Represents a consolidation opportunity."""

    type: str  # "duplicate_function", "unused_import", "similar_class", etc.
    description: str
    files: List[str]
    savings_estimate: int  # lines of code
    risk_level: str  # "low", "medium", "high"
    recommendation: str


class CodebaseConsolidationAnalyzer:
    """Analyzes codebase for consolidation opportunities."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.metrics: Dict[str, CodeMetrics] = {}
        self.function_signatures: Dict[str, List[str]] = defaultdict(list)
        self.class_definitions: Dict[str, List[str]] = defaultdict(list)
        self.import_patterns: Dict[str, List[str]] = defaultdict(list)

    def analyze_codebase(self) -> Dict[str, List[ConsolidationOpportunity]]:
        """Perform comprehensive codebase analysis."""
        print("🔍 Analyzing codebase for consolidation opportunities...")

        # Collect metrics for all Python files
        self._collect_file_metrics()

        opportunities = {}

        # Analyze different types of consolidation opportunities
        opportunities["duplicate_functions"] = self._find_duplicate_functions()
        opportunities["unused_imports"] = self._find_unused_imports()
        opportunities["similar_classes"] = self._find_similar_classes()
        opportunities["redundant_utilities"] = self._find_redundant_utilities()
        opportunities["import_consolidation"] = self._find_import_consolidation()
        opportunities["archival_candidates"] = self._find_archival_candidates()

        return opportunities

    def _collect_file_metrics(self):
        """Collect metrics for all Python files."""
        python_files = list(self.root_path.rglob("*.py"))

        for file_path in python_files:
            # Skip test files, cache directories, and virtual environments
            if (
                "test" in str(file_path).lower()
                or "__pycache__" in str(file_path)
                or "venv" in str(file_path)
                or "node_modules" in str(file_path)
                or ".git" in str(file_path)
            ):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(file_path))

                # Extract functions
                functions = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append(node.name)

                # Extract classes
                classes = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)

                # Extract imports
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(f"{module}.{alias.name}" if module else alias.name)

                # Calculate complexity (simple heuristic)
                complexity = len(functions) + len(classes) + len(content.split("\n"))

                # File hash for change detection
                file_hash = hashlib.md5(content.encode()).hexdigest()

                metrics = CodeMetrics(
                    file_path=str(file_path),
                    lines_of_code=len(content.split("\n")),
                    functions=functions,
                    classes=classes,
                    imports=imports,
                    complexity_score=complexity,
                    last_modified=os.path.getmtime(file_path),
                    hash=file_hash,
                )

                self.metrics[str(file_path)] = metrics

                # Index functions and classes
                for func in functions:
                    self.function_signatures[func].append(str(file_path))
                for cls in classes:
                    self.class_definitions[cls].append(str(file_path))
                for imp in imports:
                    self.import_patterns[imp].append(str(file_path))

            except (SyntaxError, UnicodeDecodeError):
                # Skip files with syntax errors or encoding issues
                continue
            except Exception as e:
                # Log other errors but continue
                print(f"⚠️  Error analyzing {file_path}: {e}")
                continue

        print(f"📊 Analyzed {len(self.metrics)} Python files")

    def _find_duplicate_functions(self) -> List[ConsolidationOpportunity]:
        """Find functions with identical names that might be duplicates."""
        opportunities = []

        for func_name, files in self.function_signatures.items():
            if len(files) > 3:  # Only consider functions that appear in multiple files
                # Check if they have similar implementations
                similar_files = self._check_function_similarity(func_name, files)
                if len(similar_files) > 1:
                    savings = len(similar_files) * 10  # Rough estimate
                    opportunities.append(
                        ConsolidationOpportunity(
                            type="duplicate_function",
                            description=f"Function '{func_name}' appears in {len(similar_files)} files with similar implementations",
                            files=similar_files,
                            savings_estimate=savings,
                            risk_level="medium",
                            recommendation=f"Consider extracting '{func_name}' to a shared utility module",
                        )
                    )

        return opportunities

    def _check_function_similarity(self, func_name: str, files: List[str]) -> List[str]:
        """Check if functions across files are similar."""
        # Simple heuristic: compare function lengths and imports used
        function_metrics = []

        for file_path in files:
            metrics = self.metrics.get(file_path)
            if metrics and func_name in metrics.functions:
                function_metrics.append((file_path, metrics.lines_of_code, len(metrics.imports)))

        # Group by similarity (rough heuristic)
        similar_groups = []
        for i, (file1, loc1, imp1) in enumerate(function_metrics):
            group = [file1]
            for file2, loc2, imp2 in function_metrics[i + 1 :]:
                # Consider similar if LOC and import count are close
                if abs(loc1 - loc2) < 50 and abs(imp1 - imp2) < 3:
                    group.append(file2)
            if len(group) > 1:
                similar_groups.extend(group)

        return list(set(similar_groups))

    def _find_unused_imports(self) -> List[ConsolidationOpportunity]:
        """Find potentially unused imports."""
        opportunities = []

        for file_path, metrics in self.metrics.items():
            unused_candidates = []

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for imp in metrics.imports:
                # Simple heuristic: check if import name appears in code
                imp_name = imp.split(".")[-1]  # Get the actual import name
                if imp_name not in content:
                    unused_candidates.append(imp)

            if unused_candidates:
                opportunities.append(
                    ConsolidationOpportunity(
                        type="unused_imports",
                        description=f"File contains {len(unused_candidates)} potentially unused imports",
                        files=[file_path],
                        savings_estimate=len(unused_candidates) * 2,
                        risk_level="low",
                        recommendation=f"Review and remove unused imports: {', '.join(unused_candidates[:5])}",
                    )
                )

        return opportunities

    def _find_similar_classes(self) -> List[ConsolidationOpportunity]:
        """Find classes with similar names and structures."""
        opportunities = []

        for class_name, files in self.class_definitions.items():
            if len(files) > 2:
                opportunities.append(
                    ConsolidationOpportunity(
                        type="similar_classes",
                        description=f"Class '{class_name}' defined in {len(files)} files",
                        files=files,
                        savings_estimate=len(files) * 15,  # Rough estimate per class
                        risk_level="high",
                        recommendation=f"Review '{class_name}' implementations for consolidation or inheritance",
                    )
                )

        return opportunities

    def _find_redundant_utilities(self) -> List[ConsolidationOpportunity]:
        """Find redundant utility functions and classes."""
        opportunities = []

        # Look for common utility patterns
        utility_patterns = [
            r"def (get_|set_|create_|delete_|update_)",
            r"def (validate_|parse_|format_|convert_)",
            r"def (log_|debug_|info_|error_|warn_)",
            r"class.*Client",
            r"class.*Manager",
            r"class.*Service",
        ]

        pattern_counts = defaultdict(lambda: defaultdict(list))

        for file_path, metrics in self.metrics.items():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in utility_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    pattern_counts[pattern][len(matches)].append(file_path)

        # Identify files with high concentrations of similar utilities
        for pattern, count_groups in pattern_counts.items():
            for count, files in count_groups.items():
                if count > 5 and len(files) > 1:  # High concentration in multiple files
                    opportunities.append(
                        ConsolidationOpportunity(
                            type="redundant_utilities",
                            description=f"Pattern '{pattern}' appears {count} times in {len(files)} files",
                            files=files[:5],  # Limit to first 5 files
                            savings_estimate=count * 8,
                            risk_level="medium",
                            recommendation=f"Consider extracting common {pattern.replace('r', '').replace('def ', '').replace('class ', '')} utilities to shared modules",
                        )
                    )

        return opportunities

    def _find_import_consolidation(self) -> List[ConsolidationOpportunity]:
        """Find opportunities to consolidate import statements."""
        opportunities = []

        # Find files with many imports
        for file_path, metrics in self.metrics.items():
            if len(metrics.imports) > 20:  # Arbitrary threshold
                opportunities.append(
                    ConsolidationOpportunity(
                        type="import_consolidation",
                        description=f"File has {len(metrics.imports)} imports - consider consolidation",
                        files=[file_path],
                        savings_estimate=len(metrics.imports) // 2,
                        risk_level="low",
                        recommendation="Consider using 'from module import *' or consolidating imports",
                    )
                )

        return opportunities

    def _find_archival_candidates(self) -> List[ConsolidationOpportunity]:
        """Find files that could be archived or removed."""
        opportunities = []

        for file_path, metrics in self.metrics.items():
            reasons = []

            # Small files with few functions
            if metrics.lines_of_code < 50 and len(metrics.functions) <= 1:
                reasons.append("very small file")

            # Old files (not modified recently)
            if metrics.last_modified < (time.time() - 365 * 24 * 3600):  # 1 year
                reasons.append("not modified in over a year")

            # Files with no classes or functions
            if not metrics.functions and not metrics.classes:
                reasons.append("no functions or classes defined")

            if reasons:
                opportunities.append(
                    ConsolidationOpportunity(
                        type="archival_candidates",
                        description=f"Candidate for archival: {', '.join(reasons)}",
                        files=[file_path],
                        savings_estimate=metrics.lines_of_code,
                        risk_level="low",
                        recommendation="Review for archival or consolidation",
                    )
                )

        return opportunities


def generate_consolidation_report(opportunities: Dict[str, List[ConsolidationOpportunity]]) -> str:
    """Generate a comprehensive consolidation report."""
    report = []

    report.append("# ACGS-2 Codebase Consolidation Report")
    report.append("")
    report.append(f"**Generated**: {os.popen('date').read().strip()}")
    report.append("**Analysis Target**: 52k+ Python files")
    report.append("")

    total_savings = 0
    total_opportunities = 0

    for category, opps in opportunities.items():
        if not opps:
            continue

        report.append(f"## {category.replace('_', ' ').title()}")
        report.append("")
        report.append(f"Found {len(opps)} opportunities:")
        report.append("")

        for opp in opps[:10]:  # Limit to top 10 per category
            report.append(f"### {opp.description}")
            report.append(f"- **Risk Level**: {opp.risk_level}")
            report.append(f"- **Estimated Savings**: {opp.savings_estimate} lines")
            report.append(f"- **Files**: {len(opp.files)} affected")
            report.append(f"- **Recommendation**: {opp.recommendation}")
            report.append("")

            total_savings += opp.savings_estimate
            total_opportunities += 1

    # Summary
    report.append("## Summary")
    report.append("")
    report.append(f"- **Total Opportunities**: {total_opportunities}")
    report.append(",")
    report.append("")

    # Priority recommendations
    report.append("## Priority Recommendations")
    report.append("")
    report.append("1. **Low-risk consolidation first**: Unused imports, archival candidates")
    report.append("2. **Medium-risk**: Duplicate functions, redundant utilities")
    report.append("3. **High-risk**: Similar classes (requires careful review)")
    report.append("")
    report.append("### Implementation Strategy")
    report.append("")
    report.append("1. Start with automated cleanup (unused imports)")
    report.append("2. Review archival candidates manually")
    report.append("3. Create shared utility modules for common functions")
    report.append("4. Implement gradual consolidation with testing")
    report.append("")

    return "\n".join(report)


def main():
    """Main analysis entry point."""
    analyzer = CodebaseConsolidationAnalyzer("/home/dislove/document/acgs2/acgs2-core")

    try:
        opportunities = analyzer.analyze_codebase()

        # Generate report
        report = generate_consolidation_report(opportunities)

        # Save report
        with open("/home/dislove/document/acgs2/CORE_CONSOLIDATION_REPORT.md", "w") as f:
            f.write(report)

        print("✅ Consolidation analysis complete!")
        print("📄 Report saved to: CORE_CONSOLIDATION_REPORT.md")

        # Print summary
        total_opportunities = sum(len(opps) for opps in opportunities.values())
        total_savings = sum(opp.savings_estimate for opps in opportunities.values() for opp in opps)

        print("\n📊 SUMMARY:")
        print(f"   • Total opportunities: {total_opportunities}")
        print(f"   • Estimated line savings: {total_savings}")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
