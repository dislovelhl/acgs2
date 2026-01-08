#!/usr/bin/env python3
"""
ARCH-001: Import Optimization Tool
Constitutional Hash: cdd01ef066bc6cf2

Optimizes complex import patterns and reduces import relationship complexity.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ImportOptimizer(ast.NodeTransformer):
    """Optimizes import statements in Python code."""

    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.file_path = file_path
        self.lines = source_code.split("\n")
        self.changes_made = []
        self.complex_imports_found = 0

    def visit_Try(self, node: ast.Try) -> ast.Try:
        """Detect and optimize try/except import blocks."""
        # Check if this is an import try/except block
        if (
            len(node.body) >= 1
            and any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body)
            and len(node.handlers) == 1
        ):
            handler = node.handlers[0]
            if (
                isinstance(handler.type, ast.Tuple)
                and len(handler.type.elts) == 2
                and all(isinstance(elt, ast.Name) for elt in handler.type.elts)
                and {elt.id for elt in handler.type.elts} == {"ImportError", "ValueError"}
            ):
                # This is a complex import pattern - log it
                self.complex_imports_found += 1

                # For now, we'll just log these - actual optimization would require
                # understanding the fallback strategy and ensuring it's safe
                logger.info(f"Found complex import pattern in {self.file_path}")

        return self.generic_visit(node)

    def analyze_complexity(self) -> Dict[str, any]:
        """Analyze the complexity of imports in this file."""
        tree = ast.parse(self.source_code)

        # Count different types of imports
        import_counts = {
            "regular_imports": 0,
            "from_imports": 0,
            "try_except_imports": 0,
            "relative_imports": 0,
            "conditional_imports": 0,
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                import_counts["regular_imports"] += 1
                # Check for relative imports
                for alias in node.names:
                    if alias.name.startswith("."):
                        import_counts["relative_imports"] += 1

            elif isinstance(node, ast.ImportFrom):
                import_counts["from_imports"] += 1
                if node.module and node.module.startswith("."):
                    import_counts["relative_imports"] += 1

        # Count try/except blocks around imports
        try_blocks = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                if any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body):
                    try_blocks.append(node)
                    import_counts["try_except_imports"] += 1

        # Count conditional imports (imports inside if statements)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in ast.walk(node)):
                    import_counts["conditional_imports"] += 1

        # Calculate complexity score
        complexity_score = (
            import_counts["try_except_imports"] * 3  # High complexity
            + import_counts["conditional_imports"] * 2  # Medium complexity
            + import_counts["relative_imports"] * 1  # Low complexity
            + max(
                0, import_counts["regular_imports"] + import_counts["from_imports"] - 10
            )  # Penalty for too many imports
        )

        return {
            "import_counts": import_counts,
            "complexity_score": complexity_score,
            "try_blocks": len(try_blocks),
            "needs_optimization": complexity_score > 5,  # Threshold for optimization
        }


def analyze_file_complexity(file_path: str) -> Optional[Dict[str, any]]:
    """Analyze import complexity of a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        optimizer = ImportOptimizer(source_code, file_path)
        tree = ast.parse(source_code)
        optimizer.visit(tree)

        analysis = optimizer.analyze_complexity()
        analysis["complex_imports_found"] = optimizer.complex_imports_found
        analysis["file_path"] = file_path

        return analysis

    except (SyntaxError, UnicodeDecodeError) as e:
        logger.warning(f"Could not analyze {file_path}: {e}")
        return None


def find_files_needing_optimization(root_path: str) -> List[Dict[str, any]]:
    """Find files that need import optimization."""
    root = Path(root_path)
    files_to_analyze = []

    # Find Python files, excluding common problematic directories
    for py_file in root.rglob("*.py"):
        if not any(
            part in str(py_file) for part in [".venv", "__pycache__", ".git", "node_modules"]
        ):
            files_to_analyze.append(str(py_file))

    logger.info(
        f"Analyzing {len(files_to_analyze)} Python files for import optimization opportunities"
    )

    results = []
    for file_path in files_to_analyze:
        analysis = analyze_file_complexity(file_path)
        if analysis and analysis.get("needs_optimization", False):
            results.append(analysis)

    # Sort by complexity score
    results.sort(key=lambda x: x["complexity_score"], reverse=True)

    return results


def generate_optimization_report(files_analysis: List[Dict[str, any]]) -> str:
    """Generate a comprehensive optimization report."""
    report = []
    report.append("# ARCH-001: Import Optimization Report")
    report.append("")
    report.append(f"**Constitutional Hash:** {CONSTITUTIONAL_HASH}")
    report.append("")
    report.append("## Executive Summary")
    report.append("")
    report.append(
        f"Analysis of {len(files_analysis)} files identified as needing import optimization."
    )
    report.append("")

    if files_analysis:
        total_complexity = sum(f["complexity_score"] for f in files_analysis)
        total_try_blocks = sum(f["try_blocks"] for f in files_analysis)

        report.append("### Key Findings")
        report.append(f"- **Files needing optimization:** {len(files_analysis)}")
        report.append(f"- **Total complexity score:** {total_complexity}")
        report.append(f"- **Try/except import blocks:** {total_try_blocks}")
        report.append("")

        report.append("### Top Files by Complexity")
        report.append("")
        for i, file_info in enumerate(files_analysis[:10]):  # Top 10
            file_path = file_info["file_path"].replace(str(Path.cwd()), ".")
            complexity = file_info["complexity_score"]
            try_blocks = file_info["try_blocks"]
            imports_count = (
                file_info["import_counts"]["regular_imports"]
                + file_info["import_counts"]["from_imports"]
            )

            report.append(f"#### {i + 1}. {file_path}")
            report.append(f"- **Complexity Score:** {complexity}")
            report.append(f"- **Try/Except Blocks:** {try_blocks}")
            report.append(f"- **Total Imports:** {imports_count}")
            report.append("")

        report.append("## Optimization Strategies")
        report.append("")
        report.append("### 1. Centralize Optional Imports")
        report.append("Move try/except import blocks to dedicated import management modules.")
        report.append("")
        report.append("### 2. Use Lazy Imports")
        report.append("Import heavy dependencies only when needed to reduce startup time.")
        report.append("")
        report.append("### 3. Simplify Fallback Patterns")
        report.append("Replace complex try/except chains with cleaner conditional imports.")
        report.append("")
        report.append("### 4. Consolidate Import Statements")
        report.append("Group related imports and remove unnecessary ones.")
        report.append("")

        report.append("## Implementation Plan")
        report.append("")
        report.append("1. **Phase 1:** Analyze and document current import patterns")
        report.append("2. **Phase 2:** Create centralized import management")
        report.append("3. **Phase 3:** Implement lazy loading where appropriate")
        report.append("4. **Phase 4:** Test and validate all changes")
        report.append("")

    else:
        report.append("### Key Findings")
        report.append("✅ **No files require import optimization at this time.**")
        report.append("All import patterns are within acceptable complexity limits.")
        report.append("")

    report.append("---")
    report.append(f"**Report Generated:** {CONSTITUTIONAL_HASH}")

    return "\n".join(report)


def main():
    """Main ARCH-001 optimization execution."""
    print("🔧 ARCH-001: Import Optimization Analysis")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    root_path = "src/core"

    # Find files needing optimization
    files_needing_optimization = find_files_needing_optimization(root_path)

    print("📊 ANALYSIS RESULTS")
    print(f"Files analyzed: {len(list(Path(root_path).rglob('*.py')))}")
    print(f"Files needing optimization: {len(files_needing_optimization)}")
    print()

    if files_needing_optimization:
        print("🔧 TOP FILES NEEDING OPTIMIZATION:")
        for i, file_info in enumerate(files_needing_optimization[:5]):  # Show top 5
            file_path = file_info["file_path"].replace(str(Path.cwd() / root_path), f"{root_path}/")
            complexity = file_info["complexity_score"]
            try_blocks = file_info["try_blocks"]

            print(f"  {i + 1}. {file_path}")
            print(f"     Complexity: {complexity}, Try/Except blocks: {try_blocks}")
        print()

        # Generate detailed report
        report = generate_optimization_report(files_needing_optimization)
        report_file = "ARCH-001_IMPORT_OPTIMIZATION_REPORT.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📄 Detailed report saved to: {report_file}")

    else:
        print("✅ NO OPTIMIZATION NEEDED")
        print("All import patterns are within acceptable complexity limits.")

    print()
    print("🔧 ARCH-001 OPTIMIZATION ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
