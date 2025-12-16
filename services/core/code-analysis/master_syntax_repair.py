#!/usr/bin/env python3
"""
Master Syntax Repair Tool
Constitutional Hash: cdd01ef066bc6cf2

Combines structural repair logic (indentation/blocks) with regex pattern matching
to fix the remaining corrupted files in the Code Analysis Service.
"""

import re
import sys
from pathlib import Path
from typing import Tuple, List

# --- Configuration ---
TARGET_FILES = [
    "code_analysis_service/app/api/v1/router.py",
    "code_analysis_service/app/core/file_watcher.py",
    "code_analysis_service/app/core/indexer.py",
    "code_analysis_service/app/middleware/performance.py",
    "code_analysis_service/app/services/cache_service.py",
    "code_analysis_service/app/services/registry_service.py",
    "code_analysis_service/app/utils/logging.py",
    "code_analysis_service/config/database.py",
    "code_analysis_service/config/settings.py",
    "code_analysis_service/deployment_readiness_validation.py",
    "code_analysis_service/main_simple.py",
    "deploy_staging.py",
    "phase4_service_integration_examples.py",
    "phase5_production_monitoring_setup.py",
]

# --- Structural Repair Functions (Context Sensitive) ---

def fix_broken_with_blocks(content: str) -> Tuple[str, int]:
    """
    Fixes corruption where `try/except` was inserted into `with` blocks,
    breaking the indentation structure.
    """
    lines = content.split('\n')
    new_lines = []
    fixes = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect: with statement followed immediately by except (corruption)
        if re.match(r'^(\s*)with\s+.+:\s*$', line):
            indent = len(line) - len(line.lstrip())

            if i + 1 < len(lines):
                next_line = lines[i+1]
                next_indent = len(next_line) - len(next_line.lstrip())

                # If next line is 'except' at same indent, it's corrupted
                if next_indent == indent and next_line.strip().startswith('except'):
                    # Keep the 'with' line
                    new_lines.append(line)
                    fixes += 1

                    # Scan ahead to skip the broken try/except/raise block
                    k = i + 1
                    found_raise = False
                    while k < len(lines):
                        if lines[k].strip() == 'raise':
                            found_raise = True
                            k += 1
                            break
                        k += 1

                    if found_raise:
                        # Add code after raise if it exists and looks valid
                        i = k
                        continue

        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines), fixes

def remove_orphaned_blocks(content: str) -> Tuple[str, int]:
    """Removes orphaned logger/raise blocks that appear without context."""
    fixes = 0
    # Pattern: except ... raise, followed immediately by another except or unrelated code
    # This cleans up the debris left by previous regex replacements
    pattern = re.compile(
        r'(\s*)except [^:]+:\s*\n'
        r'\1    logger\.error\([^)]+\)\s*\n'
        r'\1    raise\s*\n',
        re.MULTILINE
    )

    # Only replace if it doesn't look like a valid error handler (heuristic)
    # We look for specific "Data operation failed" or "Unexpected error" from the bad automation
    bad_pattern = re.compile(
        r'(\s*)except \(ValueError, KeyError, TypeError\) as e:\s*\n'
        r'\1    logger\.error\(f"Data operation failed: \{e\}"\)\s*\n'
        r'\1    raise\s*\n'
        r'\1except Exception as e:\s*\n'
        r'\1    logger\.error\(f"Unexpected error: \{e\}"\)\s*\n'
        r'\1    raise\s*\n',
        re.MULTILINE
    )

    while bad_pattern.search(content):
        content = bad_pattern.sub('', content)
        fixes += 1

    return content, fixes

def fix_broken_definitions(content: str) -> Tuple[str, int]:
    """Fixes function/method definitions broken by try/except injection."""
    fixes = 0

    # Pattern: def func( try: args except...
    pattern = re.compile(
        r'def\s+(\w+)\(\s*\n\s*try:\s*\n\s*([^)]+)\n\s*except[^)]+\)',
        re.DOTALL
    )

    # This is complex to regex, so we handle the specific "args after raise" case
    # Often appears as: raise \n self, arg2):

    lines = content.split('\n')
    new_lines = []
    skip = False

    for idx, line in enumerate(lines):
        if skip:
            skip = False
            continue

        # Check for the specific corruption signature at end of function sig
        if line.strip() == 'raise':
            if idx + 1 < len(lines):
                next_line = lines[idx+1]
                if next_line.strip().startswith(('self,', 'cls,', 'request:', 'background_tasks:')):
                    # This is likely parts of a function signature
                    fixes += 1
                    # We simply drop the raise line, the next line will be appended
                    continue

        new_lines.append(line)

    return '\n'.join(new_lines), fixes

# --- Regex Repair Functions (Pattern Matching) ---

def fix_docstrings(content: str) -> Tuple[str, int]:
    """Fixes unterminated or malformed docstrings."""
    fixes = 0

    # Fix 1: Missing opening quotes on obvious class/func docstrings
    # Look for capitalized text indented after a def/class
    lines = content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        if i > 0 and re.match(r'^\s+[A-Z]', line) and not line.strip().startswith(('"""', "'''", "#")):
            prev = lines[i-1]
            if re.match(r'^\s*(class|def|async def)\s+', prev) and prev.strip().endswith(':'):
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + '"""')
                new_lines.append(line)
                new_lines.append(' ' * indent + '"""')
                fixes += 1
                continue
        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Fix 2: " text " without triple quotes
    content = re.sub(r'"""([^"]+)"(\n)', r'"""\1"""\2', content)

    return content, fixes

def fix_imports(content: str) -> Tuple[str, int]:
    """Fixes broken import statements."""
    fixes = 0

    # Fix: from X, from Y
    new_content = re.sub(r'from ([^\s,]+), from ([^\s,]+)', r'from \1\nfrom \2', content)
    if new_content != content:
        fixes += 1
        content = new_content

    # Fix: import X, from Y
    new_content = re.sub(r'import ([^,\n]+), from ([^\n]+)', r'import \1\nfrom \2', content)
    if new_content != content:
        fixes += 1
        content = new_content

    return content, fixes

# --- Main Logic ---

def repair_file(filepath: Path) -> bool:
    print(f"Processing {filepath}...")
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False

    original_content = content
    total_fixes = 0

    # 1. Structural Fixes (Indentation & Blocks)
    content, n = fix_broken_with_blocks(content)
    total_fixes += n

    content, n = remove_orphaned_blocks(content)
    total_fixes += n

    content, n = fix_broken_definitions(content)
    total_fixes += n

    # 2. Syntax Fixes
    content, n = fix_docstrings(content)
    total_fixes += n

    content, n = fix_imports(content)
    total_fixes += n

    # 3. Cleanup: Remove duplicate FastAPI blocks
    if "# FastAPI Integration" in content:
        # Simple heuristic to remove the duplicate block if it appears twice
        parts = content.split("# FastAPI Integration - Constitutional Hash: cdd01ef066bc6cf2")
        if len(parts) > 2:
            content = parts[0] + "# FastAPI Integration - Constitutional Hash: cdd01ef066bc6cf2" + parts[1]
            total_fixes += 1

    if content != original_content:
        filepath.write_text(content, encoding='utf-8')
        print(f"  ✅ Applied {total_fixes} fixes")
        return True
    else:
        print(f"  - No issues detected")
        return False

def main():
    base_dir = Path(__file__).parent
    fixed_count = 0

    print("=== ACGS-2 Master Syntax Repair ===")
    print(f"Target Directory: {base_dir.resolve()}")

    for rel_path in TARGET_FILES:
        # Handle cases where path might be absolute or relative to different roots
        fpath = base_dir / rel_path

        # If not found, try stripping the first directory component
        # (e.g. code_analysis_service/app -> app) if running inside the service dir
        if not fpath.exists():
            parts = Path(rel_path).parts
            if len(parts) > 1:
                alt_path = base_dir / Path(*parts[1:])
                if alt_path.exists():
                    fpath = alt_path

        if fpath.exists():
            if repair_file(fpath):
                fixed_count += 1
        else:
            print(f"  ⚠️ File not found: {rel_path}")

    print(f"\nSummary: Repaired {fixed_count} files.")

if __name__ == '__main__':
    main()
