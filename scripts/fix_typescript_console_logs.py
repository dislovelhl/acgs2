#!/usr/bin/env python3
"""
Automated TypeScript Console.log Replacement Script

Systematically replaces console.log statements with proper structured logging
across the ACGS-2 TypeScript codebase.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def find_console_logs(root_dir: str) -> Dict[str, List[Tuple[int, str]]]:
    """
    Find all console.log statements in TypeScript files.

    Args:
        root_dir: Root directory to search

    Returns:
        Dictionary mapping file paths to list of (line_number, line_content) tuples
    """
    console_logs = {}

    for ts_file in Path(root_dir).rglob("*.ts"):
        if (
            "node_modules" in str(ts_file)
            or "dist" in str(ts_file)
            or ".git" in str(ts_file)
        ):
            continue

        try:
            with open(ts_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            file_logs = []
            for i, line in enumerate(lines, 1):
                if "console.log(" in line and not line.strip().startswith("//"):
                    file_logs.append((i, line.rstrip()))

            if file_logs:
                console_logs[str(ts_file)] = file_logs

        except Exception as e:
            print(f"Error reading {ts_file}: {e}")

    return console_logs


def replace_console_logs(file_path: str, statements: List[Tuple[int, str]]) -> int:
    """
    Replace console.log statements in a file with structured logging.

    Args:
        file_path: Path to the TypeScript file
        statements: List of (line_number, line_content) tuples

    Returns:
        Number of replacements made
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    replacements = 0
    lines = content.split('\n')

    # Check if logger import is already present
    has_logger_import = any(
        'from' in line and 'logger' in line and 'utils/logger' in line
        for line in lines
    )

    if not has_logger_import and statements:
        # Add logger import at the top
        import_line = "import { getLogger } from '../utils/logger';"
        if "src/" in file_path:
            # Adjust relative path based on file location
            rel_path = os.path.relpath(
                "/home/dislove/document/acgs2/sdk/typescript/src/utils/logger.ts",
                os.path.dirname(file_path)
            )
            import_line = f"import {{ getLogger }} from '{rel_path.replace('.ts', '')}';"

        # Find a good place to insert the import
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import') or line.strip().startswith('//'):
                insert_index = i + 1
            elif line.strip() and not line.strip().startswith('//'):
                break

        lines.insert(insert_index, import_line)
        lines.insert(insert_index + 1, "")

    for line_num, line_content in statements:
        # Skip if already processed
        if 'getLogger(' in line_content or 'logger.' in line_content:
            continue

        # Extract the console.log content
        match = re.search(r'console\.log\((.+)\);?', line_content.strip())
        if not match:
            continue

        log_content = match.group(1).strip()

        # Create logger instance if not present
        logger_var = "logger"
        if f"const {logger_var} =" not in '\n'.join(lines):
            # Add logger initialization near the top
            logger_init = f"const {logger_var} = getLogger('{Path(file_path).stem}');"

            # Find where to insert it (after imports)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import') or line.strip().startswith('const') and 'getLogger' in line:
                    insert_idx = i + 1
                elif line.strip() and not line.strip().startswith('//') and not line.strip().startswith('import'):
                    break

            if insert_idx > 0:
                lines.insert(insert_idx, logger_init)
                lines.insert(insert_idx + 1, "")

        # Replace console.log with structured logging
        if '"success"' in log_content and 'json.dumps' in log_content:
            # Replace print(json.dumps({"success": False, "error": "..."}))
            new_line = f"{logger_var}.error({log_content});"
        elif 'json.dumps' in log_content:
            # Replace print(json.dumps(result))
            new_line = f"{logger_var}.logResult({log_content.replace('JSON.stringify', '')});"
        else:
            # General replacement
            new_line = f"{logger_var}.info({log_content});"

        # Replace the line
        adjusted_line_num = line_num - 1  # Convert to 0-based indexing
        if adjusted_line_num < len(lines):
            lines[adjusted_line_num] = line_content.replace(
                f"console.log({log_content})",
                new_line.replace("console.log(", "").replace(");", "")
            )
            replacements += 1

    # Write back the modified content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))

    return replacements


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_typescript_console_logs.py <root_directory>")
        sys.exit(1)

    root_dir = sys.argv[1]

    print(f"Scanning for console.log statements in {root_dir}...")
    console_logs = find_console_logs(root_dir)

    total_files = len(console_logs)
    total_logs = sum(len(logs) for logs in console_logs.values())

    print(f"Found {total_logs} console.log statements in {total_files} files")

    if not console_logs:
        print("No console.log statements found.")
        return

    total_replacements = 0
    processed_files = 0

    for file_path, statements in console_logs.items():
        print(f"Processing {file_path} ({len(statements)} statements)...")
        replacements = replace_console_logs(file_path, statements)
        total_replacements += replacements
        processed_files += 1
        print(f"  Replaced {replacements} statements")

    success_rate = (total_replacements / total_logs * 100) if total_logs > 0 else 0
    print("\nSummary:")
    print(f"  Files processed: {processed_files}/{total_files}")
    print(f"  Console.log statements replaced: {total_replacements}/{total_logs}")
    print(f"  Success rate: {success_rate:.1f}%")
    if success_rate < 100:
        print("  Some statements may need manual review.")


if __name__ == "__main__":
    main()
