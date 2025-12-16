#!/usr/bin/env python3
"""
Enhanced Syntax Repair Tool
Fixes systematic Python corruption patterns in ACGS Code Analysis Service files.

Constitutional Hash: cdd01ef066bc6cf2
"""

import re
import sys
from pathlib import Path


def fix_file(filepath: Path) -> bool:
    """Fix corruption patterns in a single file."""
    print(f"Processing {filepath.name}...")

    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ❌ Error reading: {e}")
        return False

    original = content

    # Pattern 1: Remove orphaned try: blocks before decorators
    content = re.sub(
        r'\ntry:\n(\s*)(@\w+)',
        r'\n\1\2',
        content
    )

    # Pattern 2: Remove try: in function signatures
    content = re.sub(
        r'(\s+)try:\n\s+(current_user:|user_id:|request_id:)',
        r'\1\2',
        content
    )

    # Pattern 3: Remove try: blocks in dict/args
    content = re.sub(
        r'(\s+)try:\n\s+(\"|\w+_id=|job_id=)',
        r'\1\2',
        content
    )

    # Pattern 4: Remove orphaned except blocks
    content = re.sub(
        r'\nexcept Exception as e:\n\s+logger\.error\(f"Operation failed: \{e\}"\)\n\s+raise\n',
        r'\n',
        content
    )

    # Pattern 5: Fix broken imports (comma-separated from statements)
    content = re.sub(
        r'from ([^,\n]+), from ([^\n]+)',
        r'from \1\nfrom \2',
        content
    )
    content = re.sub(
        r'import ([^,\n]+), import ([^\n]+)',
        r'import \1\nimport \2',
        content
    )
    content = re.sub(
        r'import ([^,\n]+), logger = ',
        r'import \1\nlogger = ',
        content
    )

    # Pattern 6: Fix unquoted docstrings (text after import without """)
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line looks like unquoted docstring (starts with "ACGS ")
        if line.strip().startswith('ACGS ') and not line.strip().startswith('"""'):
            # Add docstring quotes
            indent = len(line) - len(line.lstrip())
            new_lines.append(' ' * indent + '"""')
            # Collect all docstring lines
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('import ', 'from ', 'class ', 'def ', '@', '"""')):
                new_lines.append(lines[i])
                i += 1
            new_lines.append(' ' * indent + '"""')
            continue

        new_lines.append(line)
        i += 1

    content = '\n'.join(new_lines)

    # Pattern 7: Fix unterminated triple-quoted strings
    content = re.sub(r'"""([^"]+)""(?=[^\"])', r'"""\1"""', content)

    # Pattern 8: Fix broken import with unquoted text
    content = re.sub(
        r'from ([^\n]+) import ([^,\n]+), ([A-Z][a-zA-Z ]+[^"\n]+)$',
        lambda m: f'from {m.group(1)} import {m.group(2)}\n"""\n{m.group(3)}\n"""',
        content,
        flags=re.MULTILINE
    )

    # Pattern 9: Remove malformed import trailing text
    def fix_import_line(match):
        import_part = match.group(1).strip()
        trailing = match.group(2).strip()
        if trailing.startswith('ACGS '):
            return f'{import_part}\n"""\n{trailing}\n"""'
        return import_part

    content = re.sub(
        r'^(from [^\n]+ import [^,\n]+), ([A-Z][^\n]+)$',
        fix_import_line,
        content,
        flags=re.MULTILINE
    )

    # Pattern 10: Fix import statements with embedded text
    content = re.sub(
        r'^(import \w+), (""|\w+ =)',
        r'\1\n\2',
        content,
        flags=re.MULTILINE
    )

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print(f"  ✅ Fixed")
        return True
    else:
        print(f"  - No changes needed")
        return False


def main():
    base = Path("/home/dislove/acgs2/services/core/code-analysis")

    files_to_fix = [
        base / "code_analysis_service/app/core/file_watcher.py",
        base / "code_analysis_service/app/core/indexer.py",
        base / "code_analysis_service/app/middleware/performance.py",
        base / "code_analysis_service/app/services/cache_service.py",
        base / "code_analysis_service/app/services/registry_service.py",
        base / "code_analysis_service/app/utils/logging.py",
        base / "code_analysis_service/config/database.py",
        base / "code_analysis_service/config/settings.py",
        base / "code_analysis_service/deployment_readiness_validation.py",
        base / "code_analysis_service/main_simple.py",
        base / "deploy_staging.py",
        base / "phase4_service_integration_examples.py",
        base / "phase5_production_monitoring_setup.py",
    ]

    print("=== Enhanced ACGS Syntax Repair ===\n")
    fixed = 0
    for f in files_to_fix:
        if f.exists():
            if fix_file(f):
                fixed += 1
        else:
            print(f"  ⚠️ Not found: {f.name}")

    print(f"\n=== Fixed {fixed} files ===")


if __name__ == "__main__":
    main()
