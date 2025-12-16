#!/usr/bin/env python3
"""Ultimate syntax fixer - handles all known patterns properly."""

import re
from pathlib import Path
import sys

def ultimate_fix(filepath: Path) -> bool:
    """Apply all necessary fixes to make the file compile."""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Step 1: Remove duplicate FastAPI boilerplate blocks
    content = re.sub(
        r'\n# FastAPI Integration - Constitutional Hash: cdd01ef066bc6cf2\n'
        r'from fastapi import FastAPI, from pydantic import BaseModel\n'
        r'import logging, # Constitutional compliance\n'
        r'CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"\n\n'
        r'# FastAPI app instance \(if not already defined\)\n'
        r'if \'app\' not in globals\(\):\n'
        r'    app = FastAPI\(title="ACGS Service", version="2\.0\.0"\)\n\n'
        r'logger = logging\.getLogger\(__name__\)\n',
        '',
        content
    )

    # Step 2: Fix broken imports
    content = re.sub(r'from ([^\s]+), from ([^\s]+)', r'from \1\nfrom \2', content)
    content = re.sub(r'import ([^,\n]+), from ([^\s]+)', r'import \1\nfrom \2', content)
    content = re.sub(r'import ([^,\n]+), import ([^\s]+)', r'import \1\nimport \2', content)
    content = re.sub(r'import logging, logger = ', r'import logging\n\nlogger = ', content)
    content = re.sub(r'import logging, # ', r'import logging\n\n# ', content)

    # Step 3: Fix broken logger.info/warning/error calls with duplicated extra=
    content = re.sub(
        r'(logger\.(info|warning|error)\([^)]+), extra=\{[^}]+\}\),\s+extra=\{',
        r'\1,\n            extra={',
        content
    )

    # Step 4: Fix os.getenv nested calls
    content = re.sub(
        r'password=os\.environ\.get\("DATABASE_URL", os\.environ\.get\("DEFAULT_VALUE", "fallback"\)\)',
        r'password=os.getenv("POSTGRESQL_PASSWORD", "")',
        content
    )

    # Step 5: Fix unterminated docstrings
    content = re.sub(r'"""([^"]+)"(\n|\s+)', r'"""\1"""\2', content)
    content = re.sub(r'"""([^"]+)"$', r'"""\1"""', content, flags=re.MULTILINE)

    # Step 6: Remove orphaned Pydantic class definitions
    content = re.sub(
        r'# Pydantic Models for Constitutional Compliance\n'
        r'class ConstitutionalRequest.*?'
        r'tus="success"\n\n\n',
        '',
        content,
        flags=re.DOTALL
    )

    # Step 7: Fix broken Field definitions with try-except in wrong places
    content = re.sub(
        r'(\w+)=Field\(\s+try:\s+default=\[',
        r'\1: list = Field(default=[',
        content
    )
    content = re.sub(
        r'except requests\.RequestException.*?raise\s+',
        '',
        content,
        flags=re.DOTALL
    )

    # Step 8: Fix function definitions with broken async def
    content = re.sub(
        r'async def (\w+)\(([^)]*)\) -> Any:\s+"""([^"]+)"\n\s+try:',
        r'async def \1(\2) -> Any:\n    """\3"""\n    try:',
        content
    )

    # Step 9: Fix broken from statements
    content = re.sub(
        r'from ([^\s]+) import \(,\s+([^)]+)\)',
        r'from \1 import (\n    \2\n)',
        content
    )

    # Step 10: Fix Field definitions in settings
    content = re.sub(
        r'(\w+)=Field\(\s+default=',
        r'\1: str = Field(default=',
        content
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all files."""
    base = Path(__file__).parent

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

    fixed = 0
    for fname in files:
        fpath = base / fname
        if ultimate_fix(fpath):
            print(f"✓ Fixed {fname}")
            fixed += 1
        else:
            print(f"- No changes {fname}")

    print(f"\nFixed {fixed}/{len(files)} files")

if __name__ == '__main__':
    main()
