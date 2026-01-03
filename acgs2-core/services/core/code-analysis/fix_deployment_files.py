#!/usr/bin/env python3
"""Fix syntax errors in deployment files."""

import logging
import re
from pathlib import Path


def fix_deployment_file(filepath: Path):
    """Fix syntax errors in deployment files."""
    logging.info(f"Fixing {filepath}...")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Fix 1: Multiple imports on same line
    content = re.sub(
        r"from datetime import datetime, import json",
        r"from datetime import datetime\nimport json",
        content,
    )
    content = re.sub(r"import pathlib, import sys", r"import pathlib\nimport sys", content)
    content = re.sub(r"import time, from typing", r"import time\nfrom typing", content)
    content = re.sub(r"import requests, class", r"import requests\n\n\nclass", content)
    content = re.sub(r"import json, import os", r"import json\nimport os", content)
    content = re.sub(r"import sys, import time", r"import sys\nimport time", content)

    # Fix 2: Remove duplicate "from typing import Any"
    lines = content.split("\n")
    seen_typing_any = False
    new_lines = []
    for line in lines:
        if "from typing import Any" in line:
            if not seen_typing_any:
                new_lines.append(line)
                seen_typing_any = True
        else:
            new_lines.append(line)
    content = "\n".join(new_lines)

    # Fix 3: Fix broken function definitions
    content = re.sub(
        r'def (\w+)\(([^)]*)\) -> Any:\s+"""([^"]+)"\n\s+try:',
        r'def \1(\2) -> Any:\n    """\3"""\n    try:',
        content,
    )

    # Fix 4: Fix try-except blocks in wrong places
    content = re.sub(r"(\s+)try:\s+(\w+)=\[", r"\1\2=[", content)
    content = re.sub(r'(\s+)try:\s+"expr":', r'\1"expr":', content)

    # Fix 5: Fix unterminated docstrings
    content = re.sub(r'"""([^"]*)"\n(\s+)(try:|[a-z_])', r'"""\1"""\n\2\3', content)

    # Fix 6: Remove stray except blocks
    content = re.sub(
        r"\s+except requests\.RequestException as e:\s+logger\.error.*?raise\s+",
        "",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"\s+except Exception as e:\s+logger\.error.*?raise\s+(?=\s+[a-z_])",
        "",
        content,
        flags=re.DOTALL,
    )

    # Fix 7: Fix async function calls that should be regular calls
    content = re.sub(
        r"result = await execute_command\(\s+\[", r"result = execute_command([", content
    )

    # Fix 8: Remove duplicate Pydantic models
    content = re.sub(
        r'# Pydantic Models for Constitutional Compliance\nclass ConstitutionalRequest.*?tus="success"\n\n\n',
        "",
        content,
        flags=re.DOTALL,
    )

    # Fix 9: Fix broken import lines
    content = re.sub(r"import yaml, try:", r"import yaml\n        try:", content)

    # Fix 10: Fix except blocks in wrong place
    content = re.sub(
        r"(\s+)except Exception as e:\s+logger\.error\(.*?\)\s+raise\s+(\w+)=",
        r"\1\2=",
        content,
        flags=re.DOTALL,
    )

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"  ✓ Fixed {filepath}")
        return True
    else:
        logging.info(f"  - No changes needed for {filepath}")
        return False


def main():
    """Fix all deployment Python files."""
    base_dir = Path(__file__).parent

    # Deployment files to fix
    files_to_fix = [
        "deploy_staging.py",
        "phase4_service_integration_examples.py",
        "phase5_production_monitoring_setup.py",
    ]

    fixed_count = 0
    for filename in files_to_fix:
        filepath = base_dir / filename
        if filepath.exists():
            if fix_deployment_file(filepath):
                fixed_count += 1
        else:
            logging.info(f"  ! File not found: {filepath}")

    logging.info(f"\n✓ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
