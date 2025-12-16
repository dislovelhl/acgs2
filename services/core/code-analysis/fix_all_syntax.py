#!/usr/bin/env python3
"""Fix syntax errors in all code-analysis service files."""

import re
from pathlib import Path

def fix_file(filepath: Path):
    """Fix syntax errors in a single file."""
    print(f"Fixing {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Fix 1: Multiple imports on same line with commas
    content = re.sub(r'import (\w+), import (\w+)', r'import \1\nimport \2', content)
    content = re.sub(r'import (\w+), logger = ', r'import \1\n\nlogger = ', content)
    content = re.sub(r'from (\S+), from (\S+)', r'from \1\nfrom \2', content)

    # Fix 2: Unterminated docstrings (single quote at end instead of triple quote)
    content = re.sub(r'"""([^"]*)"\n', r'"""\1"""\n', content)
    content = re.sub(r'"""([^"]*)"$', r'"""\1"""', content, flags=re.MULTILINE)

    # Fix 3: Broken logger.info/warning/error calls with extra commas and "extra" duplication
    content = re.sub(
        r'logger\.(info|warning|error)\("([^"]*)", extra=\{[^}]*\}\),\s+extra=\{',
        r'logger.\1(\n            "\2",\n            extra={',
        content
    )

    # Fix 4: from statement with opening paren but missing closing
    content = re.sub(r'from ([^\s]+) import \(,\s+([^)]+)\)', r'from \1 import (\n    \2\n)', content)

    # Fix 5: Pydantic class definitions in wrong place
    content = re.sub(
        r'# Pydantic Models for Constitutional Compliance\nclass ConstitutionalRequest.*?tus="success"\n\n\n',
        '',
        content,
        flags=re.DOTALL
    )

    # Fix 6: async def function return type split across lines incorrectly
    content = re.sub(r'def (\w+)\(([^)]*)\) -> Optional\[Dict\[str, Any\]\]:\s+"""([^"]+)"\n',
                     r'def \1(\2) -> Optional[Dict[str, Any]]:\n    """\3"""\n', content)

    # Fix 7: try-except blocks in wrong places
    content = re.sub(r'(\s+)try:\s+default=\[', r'\1default=[', content)
    content = re.sub(r'except requests\.RequestException as e:.*?raise\s+', '', content, flags=re.DOTALL)

    # Fix 8: Field definitions with line breaks
    content = re.sub(r'(\w+)=Field\(\s+try:', r'\1: str = Field(', content)
    content = re.sub(r'= defaul\s+', r'= Field(default=', content)
    content = re.sub(r'tries=(\d+),', r'max_retries=\1,', content)

    # Fix 9: Function definitions split across lines
    content = re.sub(r'async def (\w+)\(([^)]*)\) -> Any:\s+"""([^"]+)"\n',
                     r'async def \1(\2) -> Any:\n    """\3"""\n', content)

    # Fix 10: Broken string formatting
    content = re.sub(r'str = "    (\w+)="(\w+)",', r'    \1: str = "\2",', content)

    # Fix 11: Remove duplicate logger declarations
    lines = content.split('\n')
    seen_logger = False
    new_lines = []
    for line in lines:
        if 'logger = logging.getLogger(__name__)' in line or 'logger = get_logger(' in line:
            if not seen_logger:
                new_lines.append(line)
                seen_logger = True
        else:
            new_lines.append(line)
    content = '\n'.join(new_lines)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Fixed {filepath}")
        return True
    else:
        print(f"  - No changes needed for {filepath}")
        return False

def main():
    """Fix all Python files in the code-analysis service."""
    base_dir = Path(__file__).parent / 'code_analysis_service'

    # List of files to fix
    files_to_fix = [
        'app/api/v1/router.py',
        'app/core/file_watcher.py',
        'app/core/indexer.py',
        'app/middleware/performance.py',
        'app/services/cache_service.py',
        'app/services/registry_service.py',
        'app/utils/logging.py',
        'config/database.py',
        'config/settings.py',
        'deployment_readiness_validation.py',
        'main_simple.py',
    ]

    # Also fix deployment scripts
    deployment_files = [
        '../deploy_staging.py',
        '../phase4_service_integration_examples.py',
        '../phase5_production_monitoring_setup.py',
    ]

    all_files = [base_dir / f for f in files_to_fix] + [Path(__file__).parent / f for f in deployment_files]

    fixed_count = 0
    for filepath in all_files:
        if filepath.exists():
            if fix_file(filepath):
                fixed_count += 1
        else:
            print(f"  ! File not found: {filepath}")

    print(f"\n✓ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
