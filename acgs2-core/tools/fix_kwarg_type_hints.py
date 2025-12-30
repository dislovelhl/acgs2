#!/usr/bin/env python3
"""
ACGS-2 Keyword Argument Type Hint Repair Tool
Constitutional Hash: cdd01ef066bc6cf2

Fixes incorrectly placed type annotations in function call keyword arguments.
For example:
    BehaviorPattern(
        pattern_type="value",  # WRONG
    )
Should be:
    BehaviorPattern(
        pattern_type="value",  # CORRECT
    )
"""

import re
import sys
from pathlib import Path
from typing import Tuple

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def fix_kwarg_type_hints(content: str) -> Tuple[str, int]:
    """
    Fix keyword argument type hints in function calls.

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    fixes = 0

    # Pattern: keyword argument with type hint inside function call
    # Matches: name: Type = value, (with comma at end, inside function call context)
    # We need to be careful not to match dataclass field definitions

    # Pattern for keyword args with simple types
    pattern1 = re.compile(
        r'(\s+)(\w+):\s*(?:str|int|float|bool)\s*=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|[\d.]+|True|False|None)(,?\s*(?:#[^\n]*)?\n)',
        re.MULTILINE,
    )

    # Only replace if we're inside a function call (preceded by ( or , on a previous line)
    def replace_kwarg(match):
        indent = match.group(1)
        name = match.group(2)
        value = match.group(3)
        trailing = match.group(4)
        return f"{indent}{name}={value}{trailing}"

    # Find all matches and check context
    new_content = content
    for match in list(pattern1.finditer(content)):
        # Check if this looks like a function call context
        # Look backward for opening paren or previous argument
        start = match.start()
        context = content[max(0, start - 200) : start]

        # If we see a class definition or dataclass, skip
        if re.search(r"@dataclass|class\s+\w+.*:\s*$", context, re.MULTILINE):
            # Check if this is at class level (field definition)
            lines_before = context.split("\n")
            if lines_before and not any("(" in line for line in lines_before[-3:]):
                continue

        # If we see an opening paren in recent lines, it's likely a function call
        if "(" in context.split("\n")[-1] or any(
            "(" in line and ")" not in line for line in context.split("\n")[-5:]
        ):
            new_content = (
                new_content[: match.start()] + replace_kwarg(match) + new_content[match.end() :]
            )
            fixes += 1

    # Simpler approach: target specific patterns in function calls
    # Pattern: inside parentheses with multiple arguments
    lines = new_content.split("\n")
    new_lines = []
    in_call = 0

    for i, line in enumerate(lines):
        # Track parentheses depth
        in_call += line.count("(") - line.count(")")

        # If we're inside a call (paren depth > 0), fix type-hinted kwargs
        if in_call > 0:
            # Match kwarg with type hint
            kwarg_pattern = re.compile(
                r"^(\s*)(\w+):\s*(?:str|int|float|bool|dict|list|Any|Optional)(?:\[[^\]]*\])?\s*=\s*(.+)$"
            )
            match = kwarg_pattern.match(line)
            if match:
                indent = match.group(1)
                name = match.group(2)
                value = match.group(3)
                # Only fix if it looks like a function argument (not a field default)
                if not line.strip().startswith("@") and "(" not in line[: line.find("=")]:
                    new_line = f"{indent}{name}={value}"
                    new_lines.append(new_line)
                    fixes += 1
                    continue

        new_lines.append(line)

    return "\n".join(new_lines), fixes


def fix_double_type_annotations(content: str) -> Tuple[str, int]:
    """
    Fix double type annotations in function parameters.
    e.g., entry: dict[str, Any] -> entry: dict[str, Any]
    """
    fixes = 0

    # Pattern: param: Type[...]: Type
    pattern = re.compile(
        r"(\w+:\s*(?:dict|list|Optional|Union|Any|Callable)\[[^\]]+\]):\s*(?:Any|str|int|float|bool|None|Self)"
    )

    while pattern.search(content):
        content = pattern.sub(r"\1", content)
        fixes += 1

    return content, fixes


def fix_self_type_hint(content: str) -> Tuple[str, int]:
    """
    Fix self: Self type hints (not valid in older Python).
    """
    fixes = 0

    # Pattern: (self, or (self)
    pattern = re.compile(r"\(self:\s*Self([,)])")

    while pattern.search(content):
        content = pattern.sub(r"(self\1", content)
        fixes += 1

    return content, fixes


def process_file(filepath: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """Process a single file."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return False, 0

    total_fixes = 0

    # Apply fixes
    content, fixes = fix_double_type_annotations(content)
    total_fixes += fixes

    content, fixes = fix_self_type_hint(content)
    total_fixes += fixes

    content, fixes = fix_kwarg_type_hints(content)
    total_fixes += fixes

    if total_fixes > 0:
        if not dry_run:
            filepath.write_text(content, encoding="utf-8")
        return True, total_fixes

    return False, 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix keyword argument type hints in ACGS-2 codebase"
    )
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    print("ACGS-2 Keyword Argument Type Hint Repair Tool")
    print(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
    print()

    total_files = 0
    modified_files = 0
    total_fixes = 0

    for path_str in args.paths:
        path = Path(path_str)

        if path.is_file() and path.suffix == ".py":
            files = [path]
        elif path.is_dir():
            files = list(path.rglob("*.py"))
        else:
            continue

        for filepath in files:
            skip_dirs = ["__pycache__", ".git", "node_modules", ".venv"]
            if any(skip_dir in str(filepath) for skip_dir in skip_dirs):
                continue

            total_files += 1
            was_modified, fixes = process_file(filepath, args.dry_run)

            if was_modified:
                modified_files += 1
                total_fixes += fixes
                if args.verbose:
                    action = "Would fix" if args.dry_run else "Fixed"
                    print(f"  {action} {fixes} patterns in {filepath}")

    print("Summary:")
    print(f"  Files scanned: {total_files}")
    print(f"  Files modified: {modified_files}")
    print(f"  Total fixes: {total_fixes}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
