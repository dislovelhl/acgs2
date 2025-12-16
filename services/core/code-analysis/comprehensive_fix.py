#!/usr/bin/env python3
"""Comprehensive syntax error fixes for all code-analysis files."""

import re
from pathlib import Path

def comprehensive_fix(filepath: Path):
    """Apply comprehensive fixes to a file."""
    print(f"Fixing {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Fix 1: Broken docstrings (missing opening triple quotes)
    content = re.sub(r'\n(\s+)\n(\s+)([A-Z][^\n]+)\n(\s+)', r'\n\1"""\n\2\3\n\4"""\n\4', content)

    # Fix 2: from X, from Y imports
    content = re.sub(r'from ([^\s]+), from ([^\s]+)', r'from \1\nfrom \2', content)

    # Fix 3: import X, from Y
    content = re.sub(r'import ([^,\n]+), from ([^\n]+)', r'import \1\nfrom \2', content)

    # Fix 4: Broken multi-line docstrings
    content = re.sub(r'"""([^"]+)""([^"])', r'"""\1"""\2', content)

    # Fix 5: Duplicate logger assignments and FastAPI boilerplate
    # Remove the duplicate FastAPI integration blocks
    content = re.sub(
        r'# FastAPI Integration - Constitutional Hash:.*?logger = logging\.getLogger\(__name__\)\n\n',
        '',
        content,
        flags=re.DOTALL
    )

    # Fix 6: Broken except blocks
    content = re.sub(r'(\))except ', r')\n        except ', content)

    # Fix 7: Function signatures broken with except
    content = re.sub(r'def (\w+)\(([^)]*)\) -> ([^:]+):except', r'def \1(\2) -> \3:\n    """Function docstring."""\nexcept', content)

    # Fix 8: Fix missing closing quotes on docstrings
    content = re.sub(r'"""([^"]*)""\n', r'"""\1"""\n', content)
    content = re.sub(r'"""([^"]*)""$', r'"""\1"""', content, flags=re.MULTILINE)

    # Fix 9: Remove orphaned Pydantic classes
    content = re.sub(
        r'# Constitutional Hash: cdd01ef066bc6cf2\nCONSTITUTIONAL_HASH.*?@handle_errors.*?\n\n',
        '',
        content,
        flags=re.DOTALL
    )

    # Fix 10: Fix broken except in middle of code
    content = re.sub(r'(\s+)except [^\n]+\n\s+logger\.error[^\n]+\n\s+raise\n(\s+)(\w+)', r'\1\3', content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Applied fixes to {filepath}")
        return True
    else:
        print(f"  - No changes needed for {filepath}")
        return False

def main():
    """Fix all files."""
    base_dir = Path(__file__).parent

    files = [
        'code_analysis_service/app/api/v1/router.py',
        'code_analysis_service/app/core/file_watcher.py',
        'code_analysis_service/app/core/indexer.py',
        'code_analysis_service/app/middleware/performance.py',
        'code_analysis_service/app/services/cache_service.py',
        'code_analysis_service/app/services/registry_service.py',
        'code_analysis_service/app/utils/logging.py',
        'code_analysis_service/config/database.py',
        'code_analysis_service/config/settings.py',
        'code_analysis_service/deployment_readiness_validation.py',
        'code_analysis_service/main_simple.py',
        'deploy_staging.py',
        'phase4_service_integration_examples.py',
        'phase5_production_monitoring_setup.py',
    ]

    fixed_count = 0
    for filename in files:
        filepath = base_dir / filename
        if filepath.exists():
            if comprehensive_fix(filepath):
                fixed_count += 1

    print(f"\n✓ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
