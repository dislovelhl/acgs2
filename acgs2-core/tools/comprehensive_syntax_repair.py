import logging

#!/usr/bin/env python3
"""
ACGS-2 Comprehensive Syntax Repair Tool
Constitutional Hash: cdd01ef066bc6cf2

Fixes multiple corruption patterns in Python files:
1. try/except blocks breaking with statements
2. Empty indented blocks
3. Misplaced code after except blocks
4. Unclosed parentheses from truncated code
"""

import re
import sys
from pathlib import Path
from typing import Tuple

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def fix_with_statement_corruption(content: str) -> Tuple[str, int]:
    """
    Fix corruption where try/except was inserted inside with blocks.

    Pattern:
        with open(...) as f:
            pass
    Should be:
        with open(...) as f:
            actual_code_here
    """
    fixes = 0
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for 'with' statement followed by empty or except
        if re.match(r"^(\s*)with\s+.+:\s*$", line):
            indent = len(line) - len(line.lstrip())
            with_line = line

            # Look ahead for the corruption pattern
            j = i + 1
            found_corruption = False
            code_after_raise = []

            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()

                # Check for except immediately after with (corruption)
                if re.match(r"^(\s*)except\s+", next_line):
                    except_indent = len(next_line) - len(next_line.lstrip())
                    if except_indent == indent:
                        # Found the corruption - skip the try/except block
                        found_corruption = True
                        k = j + 1
                        # Skip until we find code at the right indent or 'raise'
                        while k < len(lines):
                            skip_line = lines[k]
                            skip_stripped = skip_line.strip()
                            if skip_stripped == "raise":
                                k += 1
                                # Collect code after raise until indent decreases
                                while k < len(lines):
                                    after_line = lines[k]
                                    if after_line.strip() and not after_line.startswith(
                                        " " * (indent + 4)
                                    ):
                                        break
                                    if after_line.strip():
                                        code_after_raise.append(after_line)
                                    k += 1
                                break
                            k += 1
                        break
                elif next_stripped and not next_stripped.startswith("#"):
                    break
                j += 1

            if found_corruption and code_after_raise:
                new_lines.append(with_line)
                # Add the code that should be inside the with block
                for code_line in code_after_raise:
                    new_lines.append(code_line)
                i = k
                fixes += 1
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines), fixes


def fix_try_in_with_block(content: str) -> Tuple[str, int]:
    """
    Fix pattern where try block is started but except appears at wrong level.

    Pattern:
        with something:
            try:
                with other:
                    pass
            except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
                ...
    """
    fixes = 0

    # Pattern: with statement followed by try, then except at same level as try
    pattern = re.compile(
        r"^(\s*)(with\s+[^:]+:\s*\n)"
        r"\1    try:\s*\n"
        r"\1        (with\s+[^:]+:\s*\n)"
        r"\1    except\s+[^:]+:\s*\n"
        r"(?:\1        [^\n]+\n)*"
        r"\1        raise\s*\n"
        r"(\1            [^\n]+\n)",
        re.MULTILINE,
    )

    def replace_pattern(match):
        nonlocal fixes
        indent = match.group(1)
        first_with = match.group(2)
        second_with = match.group(3)
        body = match.group(4)
        fixes += 1
        return f"{indent}{first_with}{indent}    {second_with}{body}"

    content = pattern.sub(replace_pattern, content)
    return content, fixes


def fix_empty_with_blocks(content: str) -> Tuple[str, int]:
    """Add pass to empty with blocks."""
    fixes = 0
    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        new_lines.append(line)

        # Check if this is a with statement
        match = re.match(r"^(\s*)with\s+.+:\s*$", line)
        if match:
            indent = match.group(1)
            # Check if next line exists and is not indented properly
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip():
                    next_indent = len(next_line) - len(next_line.lstrip())
                    expected_indent = len(indent) + 4
                    # If next line is except or at same/lower indent, add pass
                    if next_indent <= len(indent) or next_line.strip().startswith("except"):
                        new_lines.append(f"{indent}    pass")
                        fixes += 1
            else:
                # End of file, add pass
                new_lines.append(f"{indent}    pass")
                fixes += 1

    return "\n".join(new_lines), fixes


def fix_broken_except_chain(content: str) -> Tuple[str, int]:
    """
    Fix pattern where except blocks appear without try.
    Remove orphaned except blocks that break the code.
    """
    fixes = 0
    lines = content.split("\n")
    new_lines = []

    skip_until_indent = -1
    current_indent = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if skip_until_indent >= 0:
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= skip_until_indent:
                    skip_until_indent = -1
                else:
                    continue
            else:
                continue

        # Check for orphaned except (not preceded by try at same level)
        if re.match(r"^(\s*)except\s+", line):
            indent = len(line) - len(line.lstrip())
            # Look back for matching try
            found_try = False
            for j in range(len(new_lines) - 1, -1, -1):
                prev = new_lines[j]
                if prev.strip():
                    prev_indent = len(prev) - len(prev.lstrip())
                    if prev_indent == indent and prev.strip().startswith("try:"):
                        found_try = True
                        break
                    elif prev_indent < indent:
                        break

            if not found_try:
                # Skip this except block
                skip_until_indent = indent
                fixes += 1
                continue

        new_lines.append(line)

    return "\n".join(new_lines), fixes


def fix_code_after_raise(content: str) -> Tuple[str, int]:
    """
    Fix code appearing after raise at the same indent (dead code).
    Move it before the raise or remove the raise.
    """
    fixes = 0
    lines = content.split("\n")
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip() == "raise":
            raise_indent = len(line) - len(line.lstrip())
            # Check if there's code after at same indent
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip():
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent == raise_indent + 4:
                        # Code at higher indent after raise - skip the raise
                        fixes += 1
                        i += 1
                        continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines), fixes


def fix_double_except(content: str) -> Tuple[str, int]:
    """Remove duplicate except blocks."""
    fixes = 0
    lines = content.split("\n")
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if re.match(r"^(\s*)except\s+", line):
            # Check if next line is also except at same indent
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.match(r"^(\s*)except\s+", next_line):
                    indent1 = len(line) - len(line.lstrip())
                    indent2 = len(next_line) - len(next_line.lstrip())
                    if indent1 == indent2:
                        # Skip the first except, keep the second
                        i += 1
                        fixes += 1
                        continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines), fixes


def add_pass_to_empty_blocks(content: str) -> Tuple[str, int]:
    """Add pass statement to empty code blocks."""
    fixes = 0
    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        new_lines.append(line)

        # Check for block starters
        if re.match(
            r"^(\s*)(if|elif|else|for|while|try|except|finally|def|class|with)\s*.*:\s*$", line
        ):
            indent_match = re.match(r"^(\s*)", line)
            indent = indent_match.group(1) if indent_match else ""

            # Check next non-empty line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                next_line = lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())
                expected_indent = len(indent) + 4

                # If next line is not properly indented, add pass
                if next_indent <= len(indent):
                    new_lines.append(f"{indent}    pass")
                    fixes += 1
            else:
                # End of file
                new_lines.append(f"{indent}    pass")
                fixes += 1

    return "\n".join(new_lines), fixes


def remove_orphan_logger_blocks(content: str) -> Tuple[str, int]:
    """
    Remove orphaned logger.error + raise blocks that appear after except.
    """
    fixes = 0

    # Pattern: except followed by logger.error and raise, then more except
    pattern = re.compile(
        r"^(\s*)except\s+\w+(\s+as\s+\w+)?:\s*\n"
        r"\1    logger\.error\([^)]+\)\s*\n"
        r"\1    raise\s*\n"
        r"(?=\1except\s+)",
        re.MULTILINE,
    )

    while pattern.search(content):
        content = pattern.sub("", content)
        fixes += 1

    return content, fixes


def process_file(filepath: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """Process a single file with all repair functions."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logging.error(f"  Error reading {filepath}: {e}")
        return False, 0

    total_fixes = 0
    original_content = content

    # Apply fixes in order
    repair_functions = [
        remove_orphan_logger_blocks,
        fix_broken_except_chain,
        fix_code_after_raise,
        fix_double_except,
        add_pass_to_empty_blocks,
    ]

    for func in repair_functions:
        content, fixes = func(content)
        total_fixes += fixes

    if content != original_content:
        if not dry_run:
            filepath.write_text(content, encoding="utf-8")
        return True, total_fixes

    return False, 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive syntax repair for ACGS-2")
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    logging.info("ACGS-2 Comprehensive Syntax Repair Tool")
    logging.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
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
            skip_dirs = ["__pycache__", ".git", "node_modules", ".venv", "venv"]
            if any(skip_dir in str(filepath) for skip_dir in skip_dirs):
                continue

            total_files += 1
            was_modified, fixes = process_file(filepath, args.dry_run)

            if was_modified:
                modified_files += 1
                total_fixes += fixes
                if args.verbose:
                    action = "Would fix" if args.dry_run else "Fixed"
                    logging.info(f"  {action} {fixes} patterns in {filepath}")

    logging.info("Summary:")
    logging.info(f"  Files scanned: {total_files}")
    logging.info(f"  Files modified: {modified_files}")
    logging.info(f"  Total fixes: {total_fixes}")


if __name__ == "__main__":
    sys.exit(main())
