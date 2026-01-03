#!/usr/bin/env python3
"""
ARCH-001: Import Refactoring Tool
Constitutional Hash: cdd01ef066bc6cf2

Refactors complex import patterns to use centralized import management.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ImportRefactorer(ast.NodeTransformer):
    """Refactors complex import patterns."""

    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.file_path = file_path
        self.lines = source_code.split("\n")
        self.changes_made = []
        self.complex_patterns_found = 0

    def visit_Try(self, node: ast.Try) -> ast.Try:
        """Detect and potentially refactor try/except import blocks."""
        # Check if this is an import try/except block with fallback imports
        if (
            len(node.body) >= 1
            and len(node.handlers) == 1
            and any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body)
            and any(
                isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.handlers[0].body
            )
        ):
            self.complex_patterns_found += 1

            # For now, we'll log these - the actual refactoring would need
            # careful analysis of each specific case
            logger.info(f"Found complex import pattern in {self.file_path}")

        return self.generic_visit(node)

    def analyze_import_patterns(self) -> Dict[str, any]:
        """Analyze import patterns in this file."""
        tree = ast.parse(self.source_code)

        patterns = {
            "uses_centralized_imports": False,
            "has_try_except_imports": False,
            "relative_import_fallbacks": 0,
            "complexity_score": 0,
        }

        # Check for centralized imports usage
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == ".imports":
                    patterns["uses_centralized_imports"] = True

        # Count try/except blocks with imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                if (
                    any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body)
                    and len(node.handlers) > 0
                ):
                    patterns["has_try_except_imports"] = True

                    # Check for relative import fallbacks
                    for handler in node.handlers:
                        for stmt in handler.body:
                            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                                if (
                                    isinstance(stmt, ast.ImportFrom)
                                    and stmt.module
                                    and not stmt.module.startswith(".")
                                ):
                                    patterns["relative_import_fallbacks"] += 1

        # Calculate complexity
        patterns["complexity_score"] = (10 if patterns["has_try_except_imports"] else 0) + (
            patterns["relative_import_fallbacks"] * 5
        )

        return patterns


def identify_refactoring_candidates(root_path: str) -> List[Dict[str, any]]:
    """Identify files that would benefit from import refactoring."""
    root = Path(root_path)
    candidates = []

    # Focus on enhanced_agent_bus since that's where most issues are
    target_dirs = ["enhanced_agent_bus"]

    for target_dir in target_dirs:
        target_path = root / target_dir
        if not target_path.exists():
            continue

        for py_file in target_path.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue  # Skip test files for now

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source_code = f.read()

                refactorer = ImportRefactorer(source_code, str(py_file))
                tree = ast.parse(source_code)
                refactorer.visit(tree)

                patterns = refactorer.analyze_import_patterns()

                if patterns["complexity_score"] > 0:
                    candidates.append(
                        {
                            "file_path": str(py_file),
                            "patterns": patterns,
                            "complex_patterns_found": refactorer.complex_patterns_found,
                        }
                    )

            except Exception as e:
                logger.warning(f"Could not analyze {py_file}: {e}")

    # Sort by complexity score
    candidates.sort(key=lambda x: x["patterns"]["complexity_score"], reverse=True)

    return candidates


def generate_refactoring_plan(candidates: List[Dict[str, any]]) -> str:
    """Generate a refactoring plan."""
    plan = []
    plan.append("# ARCH-001: Import Refactoring Plan")
    plan.append("")
    plan.append(f"**Constitutional Hash:** {CONSTITUTIONAL_HASH}")
    plan.append("")

    if candidates:
        plan.append("## Files Identified for Refactoring")
        plan.append("")
        plan.append(f"Total files needing refactoring: {len(candidates)}")
        plan.append("")

        for i, candidate in enumerate(candidates[:15]):  # Show top 15
            file_path = candidate["file_path"]
            patterns = candidate["patterns"]

            plan.append(f"### {i + 1}. {Path(file_path).name}")
            plan.append(f"- **File:** {file_path}")
            plan.append(f"- **Complexity Score:** {patterns['complexity_score']}")
            plan.append(f"- **Uses Centralized Imports:** {patterns['uses_centralized_imports']}")
            plan.append(f"- **Has Try/Except Imports:** {patterns['has_try_except_imports']}")
            plan.append(f"- **Relative Import Fallbacks:** {patterns['relative_import_fallbacks']}")
            plan.append("")

        plan.append("## Refactoring Strategy")
        plan.append("")
        plan.append("### Phase 1: Consolidate Import Usage")
        plan.append("Ensure all files use centralized imports module (.imports) for optionals.")
        plan.append("")
        plan.append("### Phase 2: Simplify Import Patterns")
        plan.append("Replace complex try/except import blocks with simpler patterns:")
        plan.append("")
        plan.append("```python")
        plan.append("# Instead of:")
        plan.append("try:")
        plan.append("    from .models import AgentMessage")
        plan.append("except ImportError:")
        plan.append("    from models import AgentMessage  # type: ignore")
        plan.append("")
        plan.append("# Use:")
        plan.append("from .models import AgentMessage")
        plan.append("```")
        plan.append("")
        plan.append("### Phase 3: Remove Fallback Complexity")
        plan.append("Eliminate relative import fallbacks by ensuring proper package structure.")
        plan.append("")
        plan.append("### Phase 4: Implement Lazy Loading")
        plan.append("For heavy optional dependencies, implement lazy loading patterns.")
        plan.append("")

    else:
        plan.append("## Assessment")
        plan.append("✅ No files require import refactoring at this time.")
        plan.append("")

    plan.append("---")
    plan.append(f"**Generated:** {CONSTITUTIONAL_HASH}")

    return "\n".join(plan)


def main():
    """Main ARCH-001 refactoring execution."""
    print("🔧 ARCH-001: Import Refactoring Analysis")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    root_path = "acgs2-core"

    # Identify refactoring candidates
    candidates = identify_refactoring_candidates(root_path)

    print("📊 ANALYSIS RESULTS")
    agent_bus_files = list(Path(root_path).glob("enhanced_agent_bus/*.py"))
    print(f"Files analyzed in enhanced_agent_bus: {len(agent_bus_files)}")
    print(f"Files needing refactoring: {len(candidates)}")
    print()

    if candidates:
        print("🔧 TOP FILES NEEDING REFACTORING:")
        for i, candidate in enumerate(candidates[:5]):  # Show top 5
            file_path = candidate["file_path"]
            patterns = candidate["patterns"]

            print(f"  {i + 1}. {Path(file_path).name}")
            complexity = patterns["complexity_score"]
            has_try = patterns["has_try_except_imports"]
            print(f"     Complexity: {complexity}, Try/Except: {has_try}")
        print()

        # Generate refactoring plan
        plan = generate_refactoring_plan(candidates)
        plan_file = "ARCH-001_IMPORT_REFACTORING_PLAN.md"

        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(plan)

        print(f"📄 Refactoring plan saved to: {plan_file}")

        # Summary of potential impact
        total_complexity = sum(c["patterns"]["complexity_score"] for c in candidates)
        files_using_centralized = sum(
            1 for c in candidates if c["patterns"]["uses_centralized_imports"]
        )
        files_with_fallbacks = sum(
            1 for c in candidates if c["patterns"]["relative_import_fallbacks"] > 0
        )

        print("📈 REFACTORING IMPACT:")
        print(f"Total complexity that can be reduced: {total_complexity}")
        print(f"Files already using centralized imports: {files_using_centralized}")
        print(f"Files with problematic fallbacks: {files_with_fallbacks}")

    else:
        print("✅ NO REFACTORING NEEDED")
        print("Import patterns are already optimized.")

    print()
    print("🔧 ARCH-001 REFACTORING ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
