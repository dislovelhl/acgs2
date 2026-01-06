#!/usr/bin/env python3
"""
Add Constitutional Hash to Python Files
Constitutional Hash: cdd01ef066bc6cf2

This script adds the constitutional hash to Python files that are missing it.
"""

import re
import sys
from pathlib import Path

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
HASH_LINE = f"Constitutional Hash: {CONSTITUTIONAL_HASH}"

# Directories to skip
SKIP_DIRS = {
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    ".git",
    "tests",
    "examples",
    "data",
    "benchmarks",
}


def should_process_file(filepath: Path) -> bool:
    """Check if file should be processed."""
    parts = filepath.parts
    if any(skip in parts for skip in SKIP_DIRS):
        return False
    if not filepath.suffix == ".py":
        return False
    return True


def file_has_hash(content: str) -> bool:
    """Check if file already has constitutional hash."""
    return HASH_LINE in content or "Constitutional Hash:" in content


def add_hash_to_docstring(content: str) -> str:
    """Add constitutional hash to existing docstring or create one."""
    # Pattern for triple-quoted docstring at start of file
    docstring_pattern = r'^(""")(.*?)(""")'

    match = re.match(docstring_pattern, content, re.DOTALL)
    if match:
        # Has existing docstring - add hash after first line
        docstring_content = match.group(2)
        lines = docstring_content.split("\n")
        if len(lines) >= 1:
            # Insert hash after first line of docstring
            if lines[0].strip():
                lines.insert(1, HASH_LINE)
            else:
                lines[0] = HASH_LINE
            new_docstring = "\n".join(lines)
            return f'"""{new_docstring}"""' + content[match.end() :]
    else:
        # No docstring - add one at the start
        return f'"""\n{HASH_LINE}\n"""\n\n' + content

    return content


def process_file(filepath: Path, dry_run: bool = True) -> bool:
    """Process a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if file_has_hash(content):
            return False

        new_content = add_hash_to_docstring(content)

        if new_content == content:
            return False

        if not dry_run:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)

        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Add constitutional hash to Python files")
    parser.add_argument(
        "--apply", action="store_true", help="Actually modify files (default: dry run)"
    )
    parser.add_argument("--path", default="acgs2-core", help="Path to scan")
    args = parser.parse_args()

    base_path = Path(args.path)
    if not base_path.exists():
        print(f"Path not found: {base_path}")
        sys.exit(1)

    modified = 0
    skipped = 0

    for filepath in base_path.rglob("*.py"):
        if not should_process_file(filepath):
            continue

        if process_file(filepath, dry_run=not args.apply):
            modified += 1
            print(f"{'Would modify' if not args.apply else 'Modified'}: {filepath}")
        else:
            skipped += 1

    print(f"\n{'Would modify' if not args.apply else 'Modified'}: {modified} files")
    print(f"Skipped (already has hash): {skipped} files")

    if not args.apply and modified > 0:
        print("\nRun with --apply to actually modify files")


if __name__ == "__main__":
    main()
