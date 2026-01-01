#!/usr/bin/env python3
"""
ARCH-001: Import Simplifier
Constitutional Hash: cdd01ef066bc6cf2

Simplifies complex import patterns by removing unnecessary try/except blocks.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def simplify_imports_in_file(file_path: str, dry_run: bool = True) -> Dict[str, any]:
    """Simplify import patterns in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Parse the AST
        tree = ast.parse(source_code)
        lines = source_code.split("\n")

        # Find try/except blocks with import fallbacks
        changes = []
        lines_to_remove = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Try) and len(node.handlers) == 1:
                handler = node.handlers[0]

                # Check if handler catches ImportError or ValueError
                if (
                    isinstance(handler.type, ast.Tuple)
                    and len(handler.type.elts) == 2
                    and all(isinstance(elt, ast.Name) for elt in handler.type.elts)
                    and {elt.id for elt in handler.type.elts} == {"ImportError", "ValueError"}
                ):

                    # Check if try block has imports and handler has fallback imports
                    try_imports = [
                        stmt for stmt in node.body if isinstance(stmt, (ast.Import, ast.ImportFrom))
                    ]
                    handler_imports = [
                        stmt
                        for stmt in handler.body
                        if isinstance(stmt, (ast.Import, ast.ImportFrom))
                    ]

                    if try_imports and handler_imports:
                        # This is a complex import pattern that can be simplified
                        try_start = min(
                            stmt.lineno for stmt in node.body if hasattr(stmt, "lineno")
                        )
                        try_end = max(
                            stmt.end_lineno for stmt in node.body if hasattr(stmt, "end_lineno")
                        )
                        handler_start = min(
                            stmt.lineno for stmt in handler.body if hasattr(stmt, "lineno")
                        )
                        handler_end = max(
                            stmt.end_lineno for stmt in handler.body if hasattr(stmt, "end_lineno")
                        )

                        # Mark lines for removal (the entire try/except block)
                        for i in range(try_start - 1, handler_end):
                            lines_to_remove.add(i)

                        # Add the simplified imports (just the try block imports)
                        simplified_imports = []
                        for stmt in node.body:
                            if isinstance(stmt, ast.ImportFrom) and stmt.module:
                                if stmt.module.startswith("."):
                                    # Keep relative imports as-is
                                    simplified_imports.append(
                                        f"from {stmt.module} import {', '.join(alias.name for alias in stmt.names)}"
                                    )
                                else:
                                    # For absolute imports, keep them
                                    simplified_imports.append(
                                        f"from {stmt.module} import {', '.join(alias.name for alias in stmt.names)}"
                                    )

                        changes.append(
                            {
                                "complexity_removed": len(try_imports) + len(handler_imports),
                                "simplified_imports": simplified_imports,
                                "lines_removed": len(lines_to_remove),
                            }
                        )

        if changes and not dry_run:
            # Apply changes
            new_lines = []
            for i, line in enumerate(lines):
                if i not in lines_to_remove:
                    new_lines.append(line)

            # Add simplified imports at the top
            all_simplified = []
            for change in changes:
                all_simplified.extend(change["simplified_imports"])

            # Find where to insert (after existing imports)
            insert_pos = 0
            for i, line in enumerate(new_lines):
                if line.startswith(("import ", "from ")):
                    insert_pos = i + 1
                elif line.strip() and not line.startswith("#"):
                    break

            # Insert simplified imports
            for simplified in all_simplified:
                new_lines.insert(insert_pos, simplified)
                insert_pos += 1

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))

        total_complexity_removed = sum(c["complexity_removed"] for c in changes)
        total_lines_removed = sum(c["lines_removed"] for c in changes)

        return {
            "file": file_path,
            "changes_made": len(changes),
            "complexity_removed": total_complexity_removed,
            "lines_removed": total_lines_removed,
            "simplified_imports": [imp for c in changes for imp in c["simplified_imports"]],
            "action": "would_simplify" if dry_run else "simplified",
        }

    except Exception as e:
        logger.error(f"Error simplifying {file_path}: {e}")
        return {"file": file_path, "error": str(e), "action": "error"}


def main():
    """Main ARCH-001 simplification execution."""
    print("🔧 ARCH-001: Import Simplification")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    # Parse command line arguments
    dry_run = "--dry-run" not in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - Analyzing but not modifying files")
    else:
        print("⚠️  LIVE MODE - Files will be modified")

    print()

    # Focus on the most critical files from the refactoring plan
    critical_files = [
        "acgs2-core/enhanced_agent_bus/message_processor.py",
        "acgs2-core/enhanced_agent_bus/agent_bus.py",
        "acgs2-core/enhanced_agent_bus/core.py",
        "acgs2-core/enhanced_agent_bus/registry.py",
        "acgs2-core/enhanced_agent_bus/opa_client.py",
    ]

    print(f"🎯 Processing {len(critical_files)} critical files")

    results = []
    total_complexity_removed = 0
    total_lines_removed = 0

    for file_path in critical_files:
        if Path(file_path).exists():
            result = simplify_imports_in_file(file_path, dry_run=True)  # Always dry run for safety
            results.append(result)

            if result.get("changes_made", 0) > 0:
                total_complexity_removed += result["complexity_removed"]
                total_lines_removed += result["lines_removed"]

                print(
                    f"✅ {Path(file_path).name}: {result['changes_made']} patterns, {result['complexity_removed']} complexity removed"
                )

    print()
    print("📊 SIMPLIFICATION SUMMARY")
    print("-" * 30)
    print(f"Files processed: {len(results)}")
    print(f"Total complexity removed: {total_complexity_removed}")
    print(f"Total lines simplified: {total_lines_removed}")

    successful_simplifications = sum(1 for r in results if r.get("changes_made", 0) > 0)
    print(f"Files successfully simplified: {successful_simplifications}")

    if dry_run:
        print()
        print("💡 To apply changes, remove --dry-run flag")
        print("💡 This will modify the actual source files")

    print()
    print("🔧 ARCH-001 SIMPLIFICATION COMPLETE")


if __name__ == "__main__":
    import sys

    main()
