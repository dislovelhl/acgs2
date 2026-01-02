#!/usr/bin/env python3
"""
ACGS-2 Import Cleanup Tool

Automatically detects and removes unused imports from Python files.
Constitutional Hash: cdd01ef066bc6cf2

Usage:
    python3 tools/import_cleanup.py --check [files...]  # Check for unused imports
    python3 tools/import_cleanup.py --fix [files...]    # Remove unused imports
    python3 tools/import_cleanup.py --dry-run [files...] # Show what would be removed

Author: ACGS-2 Development Team
"""

import argparse
import ast
import os
import sys
from typing import Dict, List, Tuple


class ImportAnalyzer:
    """Advanced import analysis for Python files."""

    def __init__(self):
        self.standard_library = {
            "abc",
            "argparse",
            "ast",
            "asyncio",
            "base64",
            "collections",
            "contextlib",
            "copy",
            "csv",
            "datetime",
            "decimal",
            "enum",
            "functools",
            "glob",
            "hashlib",
            "heapq",
            "hmac",
            "html",
            "http",
            "inspect",
            "io",
            "itertools",
            "json",
            "logging",
            "math",
            "multiprocessing",
            "operator",
            "os",
            "pathlib",
            "pickle",
            "platform",
            "queue",
            "random",
            "re",
            "secrets",
            "shutil",
            "socket",
            "ssl",
            "stat",
            "string",
            "subprocess",
            "sys",
            "tempfile",
            "threading",
            "time",
            "traceback",
            "typing",
            "unicodedata",
            "urllib",
            "uuid",
            "warnings",
            "weakref",
            "xml",
            "zipfile",
            "zlib",
        }

    def find_unused_imports(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Find unused imports in a Python file.

        Returns:
            List of tuples (import_name, line_number) for unused imports
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)

            # Find all import statements
            imports = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name.split(".")[0]
                        imports[name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split(".")[0]
                        # Skip standard library and typing imports
                        if module_name not in self.standard_library and module_name not in {
                            "__future__",
                            "typing",
                        }:
                            for alias in node.names:
                                name = alias.asname if alias.asname else alias.name
                                imports[name] = node.lineno

            # Find all usages
            usages = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    usages.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        usages.add(node.value.id)

            # Check for unused imports
            unused = []
            for name, line in imports.items():
                if name not in usages and name != "*":
                    unused.append((name, line))

            return unused

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            return []

    def remove_unused_imports(self, file_path: str, dry_run: bool = False) -> Dict[str, any]:
        """
        Remove unused imports from a file.

        Returns:
            Dict with 'changed', 'removed_imports', and 'backup_content' keys
        """
        unused = self.find_unused_imports(file_path)
        if not unused:
            return {"changed": False, "removed_imports": [], "backup_content": None}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            lines = original_content.split("\n")
            lines_to_remove = {line_no - 1 for _, line_no in unused}  # Convert to 0-based indexing

            # Remove the lines
            new_lines = []
            removed_lines = []
            for i, line in enumerate(lines):
                if i in lines_to_remove:
                    removed_lines.append(line)
                else:
                    new_lines.append(line)

            new_content = "\n".join(new_lines)

            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

            return {
                "changed": True,
                "removed_imports": [name for name, _ in unused],
                "removed_lines": removed_lines,
                "backup_content": original_content,
            }

        except Exception as e:
            print(f"Error modifying {file_path}: {e}", file=sys.stderr)
            return {"changed": False, "removed_imports": [], "backup_content": None}


def main():
    parser = argparse.ArgumentParser(description="ACGS-2 Import Cleanup Tool")
    parser.add_argument("files", nargs="*", help="Python files to analyze")
    parser.add_argument("--check", action="store_true", help="Check for unused imports only")
    parser.add_argument("--fix", action="store_true", help="Remove unused imports")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be removed without making changes"
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Recursively find Python files"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["venv", "__pycache__", ".git"],
        help="Directories to exclude",
    )

    args = parser.parse_args()

    if not args.files and not args.recursive:
        # Default to current directory
        args.recursive = True
        args.files = ["."]

    analyzer = ImportAnalyzer()

    # Find files to process
    files_to_check = []
    if args.recursive:
        for root_path in args.files:
            if os.path.isfile(root_path) and root_path.endswith(".py"):
                files_to_check.append(root_path)
            elif os.path.isdir(root_path):
                for root, dirs, files in os.walk(root_path):
                    # Exclude specified directories
                    dirs[:] = [d for d in dirs if d not in args.exclude]
                    for file in files:
                        if file.endswith(".py"):
                            files_to_check.append(os.path.join(root, file))
    else:
        files_to_check = [f for f in args.files if f.endswith(".py") and os.path.isfile(f)]

    total_issues = 0
    files_changed = 0

    for file_path in files_to_check:
        unused = analyzer.find_unused_imports(file_path)

        if unused:
            print(f"📁 {file_path}:")
            for name, line in unused:
                print(f"  ❌ Line {line}: unused import '{name}'")
            total_issues += len(unused)

            if args.fix or args.dry_run:
                result = analyzer.remove_unused_imports(file_path, dry_run=args.dry_run)
                if result["changed"]:
                    files_changed += 1
                    print("  ✅ Removed imports:")
                    for imp in result["removed_imports"]:
                        print(f"    - {imp}")

                    if args.dry_run:
                        print("  💡 (dry run - no changes made)")
                print()

    # Summary
    print("\n📊 Summary:")
    print(f"  Files checked: {len(files_to_check)}")
    print(
        f"  Files with issues: {len([f for f in files_to_check if analyzer.find_unused_imports(f)])}"
    )
    print(f"  Total unused imports: {total_issues}")

    if args.fix and files_changed > 0:
        print(f"  Files modified: {files_changed}")
        print("  ✅ Import cleanup completed!")
    elif args.dry_run and files_changed > 0:
        print(f"  Files that would be modified: {files_changed}")
        print("  💡 Run with --fix to apply changes")

    if total_issues > 0 and not (args.fix or args.dry_run):
        print("\n💡 To fix automatically: python3 tools/import_cleanup.py --fix [files...]")
        print("💡 To see what would change: python3 tools/import_cleanup.py --dry-run [files...]")

    # Exit with error code if issues found and not fixing
    if total_issues > 0 and not args.fix and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
