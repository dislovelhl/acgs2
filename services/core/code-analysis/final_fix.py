#!/usr/bin/env python3
"""Final targeted fixes for remaining syntax errors."""

from pathlib import Path
import re

def fix_file_targeted(filepath: Path):
    """Apply targeted fixes based on specific error patterns."""
    print(f"Fixing {filepath.name}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Pattern 1: Standalone description lines that should be in docstrings
        if i > 0 and re.match(r'^\s+[A-Z][a-zA-Z\s]+[^\.\n]\n$', line):
            prev_line = lines[i-1]
            # Check if previous line starts a function/class but has no docstring
            if re.search(r'(def |class |async def )[^:]+:\s*$', prev_line):
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + '"""\n')
                fixed_lines.append(line)
                # Look ahead for more description lines
                j = i + 1
                while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith(('"""', 'def ', 'class ', 'if ', 'return', 'try:', 'for ', 'while ')):
                    fixed_lines.append(lines[j])
                    j += 1
                fixed_lines.append(' ' * indent + '"""\n')
                i = j - 1
                i += 1
                continue

        # Pattern 2: Fix broken import with trailing docstring
        if re.match(r'^from .+ import .+, "', line):
            parts = line.split(', "')
            fixed_lines.append(parts[0] + '\n')
            if len(parts) > 1:
                fixed_lines.append('"""\n')
                fixed_lines.append(parts[1])
            i += 1
            continue

        # Pattern 3: Docstring without opening """
        if re.match(r'^\s*ACGS .+ - ', line) and '"""' not in lines[i-1]:
            indent = len(line) - len(line.lstrip())
            fixed_lines.append(' ' * indent + '"""\n')
            fixed_lines.append(line)
            i += 1
            continue

        # Pattern 4: Unmatched closing parenthesis (usually after logger statement)
        if line.strip() == ')' and i > 0:
            # Check if this is a stray closing paren
            prev_context = ''.join(fixed_lines[-5:]) if len(fixed_lines) >= 5 else ''.join(fixed_lines)
            open_count = prev_context.count('(')
            close_count = prev_context.count(')')
            if close_count >= open_count:
                # Skip this stray closing paren
                i += 1
                continue

        # Pattern 5: Unterminated docstring at end of function
        if line.strip().startswith('"""') and line.strip().endswith('"""') and len(line.strip()) > 6:
            # This is fine, keep it
            fixed_lines.append(line)
        elif line.strip() == '"""' or (line.strip().startswith('"""') and line.count('"""') == 1):
            # Check if docstring is properly closed
            fixed_lines.append(line)
            # Look ahead to ensure it's closed
            j = i + 1
            found_close = False
            while j < len(lines) and j < i + 10:
                if '"""' in lines[j]:
                    found_close = True
                    break
                j += 1
            if not found_close and line.strip().startswith('"""') and not line.strip().endswith('"""'):
                # Need to close it
                k = i + 1
                while k < len(lines) and lines[k].strip() and not lines[k].strip().startswith(('def ', 'class ', 'if __name__')):
                    fixed_lines.append(lines[k])
                    k += 1
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + '"""\n')
                i = k - 1
                i += 1
                continue
        else:
            fixed_lines.append(line)

        i += 1

    # Write fixed content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"  ✓ Fixed {filepath.name}")

def main():
    """Fix all remaining files."""
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
        'code_analysis_service/deployment_readiness_validation.py',
        'code_analysis_service/main_simple.py',
        'deploy_staging.py',
        'phase4_service_integration_examples.py',
        'phase5_production_monitoring_setup.py',
    ]

    for filename in files:
        filepath = base_dir / filename
        if filepath.exists():
            fix_file_targeted(filepath)

    print("\n✓ Completed targeted fixes")

if __name__ == '__main__':
    main()
