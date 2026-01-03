import logging

#!/usr/bin/env python3
"""
ACGS-2 Syntax Repair Tool
Constitutional Hash: cdd01ef066bc6cf2

Fixes corrupted try/except patterns that were incorrectly inserted around:
- Dataclass field declarations
- Method definitions
- Function signatures
- Class-level variable assignments

This tool identifies and removes the following invalid patterns:
    field: Type = value
And restores them to:
    field: Type = value
"""

import re
import sys
from pathlib import Path
from typing import Tuple

# Constitutional hash validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def fix_corrupted_try_except(content: str) -> Tuple[str, int]:
    """
    Fix corrupted try/except patterns in Python code.

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    fixes = 0

    # Pattern 0a: Named arguments with type annotations (e.g., pattern_type: str = "value")
    # Should be: pattern_type="value"
    pattern0a = re.compile(
        r'(\w+):\s*(?:str|int|float|bool|dict|list|Any|Optional)\s*=\s*(["\'][^"\']*["\']|[\d.]+|True|False|None|\{[^}]*\}|\[[^\]]*\])',
        re.MULTILINE,
    )

    # Only apply in function call contexts (after opening paren or comma)
    def fix_named_args(match):
        # Check if this looks like a function argument context
        return f"{match.group(1)}={match.group(2)}"

    # Pattern 0b: Corrupted function signatures with extra type annotation
    # e.g., entry: dict[str, Any] should be entry: dict[str, Any]
    pattern0b = re.compile(
        r"(\w+:\s*(?:dict|list|Optional|Union|Any)\[[^\]]+\]):\s*(?:Any|str|int|float|bool|None)",
        re.MULTILINE,
    )

    while pattern0b.search(content):
        content = pattern0b.sub(r"\1", content)
        fixes += 1

    # Pattern 1: try/except around single-line field declarations or assignments
    # Matches:
    #     try:
    #         field: Type = value
    #     except Exception as e:
    #         logger.error(f"Operation failed: {e}")
    #         raise
    pattern1 = re.compile(
        r"(\s*)try:\s*\n"
        r"\1    ([^\n]+)\s*\n"
        r"\1except Exception as e:\s*\n"
        r'\1    logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1    raise\s*\n",
        re.MULTILINE,
    )

    while pattern1.search(content):
        content = pattern1.sub(r"\1\2\n", content)
        fixes += 1

    # Pattern 2: try/except breaking method definition signatures
    # Matches:
    #     @decorator
    #     try:
    #         def method_name(self, ...):
    #     except Exception as e:
    #         logger.error(...)
    #         raise
    pattern2 = re.compile(
        r"(\s*)(@\w+[^\n]*\n)?"
        r"\1try:\s*\n"
        r"\1    (def \w+\([^)]*\)[^:]*:)\s*\n"
        r"\1except Exception as e:\s*\n"
        r'\1    logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1    raise\s*\n",
        re.MULTILINE,
    )

    while pattern2.search(content):
        match = pattern2.search(content)
        decorator = match.group(2) if match.group(2) else ""
        content = pattern2.sub(r"\1" + decorator + r"\3\n", content, count=1)
        fixes += 1

    # Pattern 3: try/except around function parameters (multi-line)
    # Matches broken function signatures
    pattern3 = re.compile(
        r"(\s*)(def \w+\()\s*\n"
        r"\1    try:\s*\n"
        r"\1        (self[^)]*)\s*\n"
        r"\1    except Exception as e:\s*\n"
        r'\1        logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1        raise\s*\n"
        r"\1    \)",
        re.MULTILINE,
    )

    while pattern3.search(content):
        content = pattern3.sub(r"\1\2\3)", content)
        fixes += 1

    # Pattern 4: try/except in dataclass field definition with field factory
    pattern4 = re.compile(
        r"(\s*)try:\s*\n"
        r"\1    (\w+:\s*\w+\[.*\]\s*=\s*(?:Field|field)\([^)]*\))\s*\n"
        r"\1except Exception as e:\s*\n"
        r'\1    logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1    raise\s*\n",
        re.MULTILINE,
    )

    while pattern4.search(content):
        content = pattern4.sub(r"\1\2\n", content)
        fixes += 1

    # Pattern 5: try/except around simple type-hinted variables
    pattern5 = re.compile(
        r"(\s*)try:\s*\n"
        r"\1    (\w+:\s*\w+(?:\[.*?\])?\s*=\s*[^\n]+)\s*\n"
        r"\1except Exception as e:\s*\n"
        r'\1    logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1    raise\s*\n",
        re.MULTILINE,
    )

    while pattern5.search(content):
        content = pattern5.sub(r"\1\2\n", content)
        fixes += 1

    # Pattern 6: try/except around if statements at class/method level
    pattern6 = re.compile(
        r"(\s*)try:\s*\n"
        r"\1    (if [^\n]+:)\s*\n"
        r"\1except Exception as e:\s*\n"
        r'\1    logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1    raise\s*\n",
        re.MULTILINE,
    )

    while pattern6.search(content):
        content = pattern6.sub(r"\1\2\n", content)
        fixes += 1

    # Pattern 7: try/except around simple statements like list/dict items
    pattern7 = re.compile(
        r"(\s*)try:\s*\n"
        r'\1    (["\']?\w+["\']?\s*[:=]\s*[^\n]+,?)\s*\n'
        r"\1except Exception as e:\s*\n"
        r'\1    logger\.error\(f"Operation failed: \{e\}"\)\s*\n'
        r"\1    raise\s*\n",
        re.MULTILINE,
    )

    while pattern7.search(content):
        content = pattern7.sub(r"\1\2\n", content)
        fixes += 1

    return content, fixes


def process_file(filepath: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Process a single file and fix corrupted syntax.

    Returns:
        Tuple of (was_modified, number_of_fixes)
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logging.error(f"  Error reading {filepath}: {e}")
        return False, 0

    fixed_content, fixes = fix_corrupted_try_except(content)

    if fixes > 0:
        if not dry_run:
            filepath.write_text(fixed_content, encoding="utf-8")
        return True, fixes

    return False, 0


def main():
    """Main entry point for syntax repair tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix corrupted try/except syntax in ACGS-2 codebase"
    )
    parser.add_argument(
        "paths", nargs="*", default=["."], help="Paths to process (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be fixed without making changes"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    logging.info("ACGS-2 Syntax Repair Tool")
    logging.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
    logging.info(
        f"{'DRY RUN - No changes will be made' if args.dry_run else 'Processing files...'}"
    )
    logging.info("")

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
            logging.info(f"Skipping invalid path: {path}")
            continue

        for filepath in files:
            # Skip certain directories
            skip_dirs = ["__pycache__", ".git", "node_modules", ".venv", "venv", "env"]
            if any(skip_dir in str(filepath) for skip_dir in skip_dirs):
                continue

            total_files += 1
            was_modified, fixes = process_file(filepath, args.dry_run)

            if was_modified:
                modified_files += 1
                total_fixes += fixes
                if args.verbose or args.dry_run:
                    action = "Would fix" if args.dry_run else "Fixed"
                    logging.info(f"  {action} {fixes} patterns in {filepath}")

    logging.info("")
    logging.info("Summary:")
    logging.info(f"  Files scanned: {total_files}")
    logging.info(f"  Files {'to be ' if args.dry_run else ''}modified: {modified_files}")
    logging.info(f"  Total fixes {'needed' if args.dry_run else 'applied'}: {total_fixes}")

    return 0 if total_fixes == 0 or args.dry_run else 0


if __name__ == "__main__":
    sys.exit(main())
