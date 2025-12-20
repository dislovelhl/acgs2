#!/usr/bin/env python3
"""
Comprehensive fix for syntax errors in code-analysis service files.
Constitutional Hash: cdd01ef066bc6cf2
"""

import re
from pathlib import Path


def fix_constitutional_hash_outside_string(content: str) -> str:
    """Fix 'Constitutional Hash: ...' appearing outside of comments/strings."""
    # Replace bare Constitutional Hash lines with comments
    content = re.sub(
        r'^Constitutional Hash: (cdd01ef066bc6cf2)\s*$',
        r'# Constitutional Hash: \1',
        content,
        flags=re.MULTILINE
    )
    # Also handle indented versions
    content = re.sub(
        r'^(\s+)Constitutional Hash: (cdd01ef066bc6cf2)\s*$',
        r'\1# Constitutional Hash: \2',
        content,
        flags=re.MULTILINE
    )
    return content


def fix_split_imports(content: str) -> str:
    """Fix imports that were split into multiline strings."""
    # Pattern: from X import Y\n"""\nZ, W\n"""
    # Should be: from X import Y, Z, W

    # Fix split typing imports
    content = re.sub(
        r'from typing import Any\n"""\nDict, Optional\n"""',
        'from typing import Any, Dict, Optional',
        content
    )
    content = re.sub(
        r'from typing import Dict\n"""\nList, Optional, Union, Any, Tuple\n"""',
        'from typing import Dict, List, Optional, Union, Any, Tuple',
        content
    )

    # Fix split pydantic imports
    content = re.sub(
        r'from pydantic import BaseModel\n"""\nField\n"""',
        'from pydantic import BaseModel, Field',
        content
    )

    # Fix split fastapi imports
    content = re.sub(
        r'from fastapi import FastAPI\n"""\nHTTPException, BackgroundTasks\n"""',
        'from fastapi import FastAPI, HTTPException, BackgroundTasks',
        content
    )
    content = re.sub(
        r'from fastapi import Request\n"""\nResponse\n"""',
        'from fastapi import Request, Response',
        content
    )

    # Fix split prometheus imports
    content = re.sub(
        r'from prometheus_client import Counter\n"""\nGauge, Histogram\n"""',
        'from prometheus_client import Counter, Gauge, Histogram',
        content
    )

    return content


def fix_try_except_around_functions(content: str) -> str:
    """Fix try/except blocks incorrectly wrapping function definitions."""
    # Pattern: try:\n    async def foo():\nexcept...\n    """docstring"""
    # Should be: async def foo():\n    """docstring"""

    # Remove try: before async def
    content = re.sub(
        r'(\s*)try:\s*\n\s*(async def \w+\([^)]*\)[^:]*:)\s*\n\s*except[^:]+:\s*\n\s*logger\.error[^\n]+\n\s*raise\s*\n',
        r'\1\2\n',
        content
    )

    # Remove try: before def
    content = re.sub(
        r'(\s*)try:\s*\n\s*(def \w+\([^)]*\)[^:]*:)\s*\n\s*except[^:]+:\s*\n\s*logger\.error[^\n]+\n\s*raise\s*\n',
        r'\1\2\n',
        content
    )

    return content


def fix_broken_logger_calls(content: str) -> str:
    """Fix broken logger.warning calls split across lines."""
    # Fix pattern: logger.warning("msg", extra={...})\n    f" more",\n    extra={...},\n)
    content = re.sub(
        r'logger\.warning\("([^"]+)"[^)]*\)\s*\n\s*f" ([^"]+)",\s*\n\s*extra=\{[^}]+\},\s*\n\s*\)',
        r'logger.warning(f"\1 \2", extra={"constitutional_hash": CONSTITUTIONAL_HASH})',
        content
    )
    return content


def fix_inline_import_class(content: str) -> str:
    """Fix imports merged with class definitions on same line."""
    content = re.sub(
        r'import requests, class (\w+):',
        r'import requests\n\n\nclass \1:',
        content
    )
    content = re.sub(
        r'import uvicorn, # (.+)',
        r'import uvicorn  # \1',
        content
    )
    return content


def fix_inline_import_comment(content: str) -> str:
    """Fix imports with trailing comments incorrectly formatted."""
    content = re.sub(
        r'from app\.utils\.constitutional import CONSTITUTIONAL_HASH, # (.+)\n',
        r'from app.utils.constitutional import CONSTITUTIONAL_HASH  # \1\n',
        content
    )
    return content


def fix_service_port_outside_string(content: str) -> str:
    """Fix 'Service Port: ...' appearing outside of comments/strings."""
    content = re.sub(
        r'^Service Port: (\d+)\s*$',
        r'# Service Port: \1',
        content,
        flags=re.MULTILINE
    )
    return content


def fix_bare_text_outside_strings(content: str) -> str:
    """Fix descriptive text appearing outside of docstrings."""
    # Fix patterns like:
    # """
    # Title
    # """
    # Description text here <- this is invalid
    content = re.sub(
        r'^"""\s*$\n^([^"\n]+)\s*$\n^"""\s*$\n^([A-Z][^"\n=]+)\s*$',
        r'"""\n\1\n\2\n"""',
        content,
        flags=re.MULTILINE
    )
    return content


def remove_duplicate_code_blocks(content: str) -> str:
    """Remove duplicate code blocks appended to files."""
    # Remove duplicate FastAPI app definitions at end of file
    content = re.sub(
        r'\n# Constitutional Hash: cdd01ef066bc6cf2\nCONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"\n\napp = FastAPI\([^)]+\)\n\nlogger = logging\.getLogger\(__name__\)\n\n@app\.get\("/health"\)[^}]+\}\s*$',
        '',
        content,
        flags=re.DOTALL
    )
    return content


def remove_misplaced_pydantic_models(content: str) -> str:
    """Remove Pydantic models inserted in wrong places."""
    content = re.sub(
        r'# Pydantic Models for Constitutional Compliance\nclass ConstitutionalRequest\(BaseModel\):\n\s+constitutional_hash: str = "cdd01ef066bc6cf2"\n\s+\nclass ConstitutionalResponse\(BaseModel\):\n\s+constitutional_hash: str = "cdd01ef066bc6cf2"\n\s+status: str = "success"\n\n',
        '',
        content
    )
    return content


def fix_missing_docstring_quotes(content: str) -> str:
    """Fix docstrings missing closing quotes."""
    # Fix class docstrings
    content = re.sub(
        r'(class \w+[^:]*:)\s*\n\s*\n\s*([A-Z][^"]+\.)\s*\n\s*\n\s*(def __init__)',
        r'\1\n    """\2"""\n\n    \3',
        content
    )
    # Fix method docstrings
    content = re.sub(
        r'(def \w+\([^)]*\)[^:]*:)\s*\n\s*\n\s*([A-Z][^"]+\.)\s*\n\s*\n\s*(Args:|Returns:|[a-z])',
        r'\1\n        """\2"""\n        \3',
        content
    )
    return content


def fix_split_docstrings(content: str) -> str:
    """Fix docstrings where Args/Returns sections are outside the quotes."""
    # Pattern: """Short description."""\n        Args:\n...
    # Should be: """Short description.\n\n        Args:\n...        """

    # Fix pattern with Args and Returns
    content = re.sub(
        r'"""([^"]+)\."""\n(\s+)(Args:\n(?:\s+\w+:[^\n]+\n)+)\n(\s+)(Returns:\n(?:\s+[^\n]+\n)+)\s*\n(\s+)(\w)',
        r'"""\1.\n\n\2\3\n\4\5        """\n\6\7',
        content
    )

    # Fix pattern with just Returns
    content = re.sub(
        r'"""([^"]+)\."""\n(\s+)(Returns:\n(?:\s+[^\n]+\n)+)\s*\n(\s+)(\w)',
        r'"""\1.\n\n\2\3        """\n\4\5',
        content
    )

    # Fix pattern with just Args
    content = re.sub(
        r'"""([^"]+)\."""\n(\s+)(Args:\n(?:\s+\w+:[^\n]+\n)+)\s*\n(\s+)(\w)',
        r'"""\1.\n\n\2\3        """\n\4\5',
        content
    )

    return content


def fix_extra_try_except_blocks(content: str) -> str:
    """Remove extraneous try/except blocks around simple statements."""
    # Pattern: try:\n            required_fields = [...]\n        except...\n            raise\n        for field
    content = re.sub(
        r'(\s+)try:\s*\n\s+(\w+ = \[[^\]]+\])\s*\n\s+except Exception as e:\s*\n\s+logger\.error[^\n]+\n\s+raise\s*\n(\s+for)',
        r'\1\2\n\3',
        content
    )
    # Pattern around hashlib
    content = re.sub(
        r'(\s+)try:\s*\n\s+(key_hash = hashlib[^\n]+)\s*\n\s+except Exception as e:\s*\n\s+logger\.error[^\n]+\n\s+raise\s*\n(\s+return)',
        r'\1\2\n\3',
        content
    )
    return content


def fix_file(filepath: Path) -> bool:
    """Apply all fixes to a single file."""
    print(f"Processing {filepath}...")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ! Error reading file: {e}")
        return False

    original = content

    # Apply fixes in order
    content = fix_constitutional_hash_outside_string(content)
    content = fix_service_port_outside_string(content)
    content = fix_split_imports(content)
    content = fix_try_except_around_functions(content)
    content = fix_broken_logger_calls(content)
    content = fix_inline_import_class(content)
    content = fix_inline_import_comment(content)
    content = fix_bare_text_outside_strings(content)
    content = remove_duplicate_code_blocks(content)
    content = remove_misplaced_pydantic_models(content)
    content = fix_missing_docstring_quotes(content)
    content = fix_split_docstrings(content)
    content = fix_extra_try_except_blocks(content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Fixed {filepath.name}")
        return True
    else:
        print(f"  - No changes for {filepath.name}")
        return False


def validate_syntax(filepath: Path) -> bool:
    """Check if file has valid Python syntax."""
    import subprocess
    result = subprocess.run(
        ['python3', '-m', 'py_compile', str(filepath)],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def main():
    """Fix all syntax errors in code-analysis service."""
    base_dir = Path(__file__).parent

    # Find all Python files
    python_files = list(base_dir.rglob('*.py'))

    print(f"Found {len(python_files)} Python files\n")

    fixed = 0
    still_broken = []

    for filepath in python_files:
        if filepath.name == 'fix_all_syntax_errors.py':
            continue

        # Check if file has syntax errors
        if not validate_syntax(filepath):
            print(f"\n[BROKEN] {filepath.relative_to(base_dir)}")
            if fix_file(filepath):
                fixed += 1
                if validate_syntax(filepath):
                    print(f"  ✓ Syntax now valid")
                else:
                    print(f"  ! Still has syntax errors")
                    still_broken.append(filepath)
            else:
                still_broken.append(filepath)

    print(f"\n{'='*50}")
    print(f"Fixed: {fixed} files")

    if still_broken:
        print(f"\nStill broken ({len(still_broken)} files):")
        for f in still_broken:
            print(f"  - {f.relative_to(base_dir)}")
    else:
        print("\n✓ All files have valid syntax!")


if __name__ == '__main__':
    main()
