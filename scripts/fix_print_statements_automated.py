#!/usr/bin/env python3
"""
Automated Print Statement Removal Script

Systematically replaces print() statements with proper logging across the ACGS-2 codebase.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def find_print_statements(root_dir: str) -> Dict[str, List[Tuple[int, str]]]:
    """
    Find all print statements in Python files.

    Args:
        root_dir: Root directory to search

    Returns:
        Dictionary mapping file paths to list of (line_number, line_content) tuples
    """
    print_statements = {}

    for py_file in Path(root_dir).rglob("*.py"):
        if (
            "venv" in str(py_file)
            or "__pycache__" in str(py_file)
            or "node_modules" in str(py_file)
        ):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            file_statements = []
            for i, line in enumerate(lines, 1):
                if "print(" in line and not line.strip().startswith("#"):
                    file_statements.append((i, line.rstrip()))

            if file_statements:
                print_statements[str(py_file)] = file_statements

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return print_statements


def categorize_print_statement(line: str) -> str:
    """
    Categorize a print statement to determine the appropriate logging replacement.

    Args:
        line: The line containing the print statement

    Returns:
        Category: 'json_error', 'json_success', 'warning_stderr', 'debug', 'other'
    """
    line = line.strip()

    # JSON error results
    if 'json.dumps({"success": False' in line:
        return "json_error"

    # JSON success results
    if "json.dumps(result)" in line or "json.dumps({" in line:
        return "json_success"

    # Warning messages to stderr
    if "file=sys.stderr" in line or "Warning:" in line:
        return "warning_stderr"

    # Simple debug prints
    if "print(" in line and len(line) < 100:
        return "debug"

    return "other"


def generate_logging_replacement(line: str, category: str, logger_name: str = "logger") -> str:
    """
    Generate the appropriate logging replacement for a print statement.

    Args:
        line: Original line with print statement
        category: Category determined by categorize_print_statement
        logger_name: Name of the logger variable

    Returns:
        Replacement line
    """
    if category == "json_error":
        # Extract error message from json.dumps({"success": False, "error": "..."})
        error_match = re.search(r'json\.dumps\(\{"success": False, "error": ([^}]+)\}\)', line)
        if error_match:
            error_expr = error_match.group(1)
            return f"    log_error_result({logger_name}, {error_expr})"

    elif category == "json_success":
        # Replace print(json.dumps(result)) with log_success_result(logger, result)
        if "json.dumps(result)" in line:
            return f"    log_success_result({logger_name}, result)"
        else:
            # More complex JSON structures - keep for manual review
            return line

    elif category == "warning_stderr":
        # Extract message from print("Warning: ...", file=sys.stderr)
        msg_match = re.search(r"print\(([^,]+(?:, file=sys\.stderr)?)\)", line)
        if msg_match:
            msg_expr = msg_match.group(1).replace(", file=sys.stderr", "")
            return f"    log_warning({logger_name}, {msg_expr})"

    elif category == "debug":
        # Simple debug prints - convert to logger.info or logger.debug
        msg_match = re.search(r"print\((.+)\)", line)
        if msg_match:
            msg_expr = msg_match.group(1)
            return f"    {logger_name}.info({msg_expr})"

    # For complex cases, return original line for manual review
    return line


def add_logging_imports(file_path: str) -> bool:
    """
    Add necessary logging imports to a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        True if imports were added, False if already present
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if logging imports already exist
        if "from ..utils.logging_config import" in content:
            return False

        # Find the import section
        lines = content.split("\n")
        import_end = 0

        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_end = i + 1
            elif line.strip() and not line.startswith("#") and import_end > 0:
                break

        # Add logging imports after existing imports
        logging_imports = [
            "",
            "from ..utils.logging_config import ("
            "setup_logging, log_error_result, log_success_result, log_warning)",
            "",
            "# Setup logging",
            "logger = setup_logging(__name__, json_format=True)",
            "",
        ]

        lines[import_end:import_end] = logging_imports

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    except Exception as e:
        print(f"Error adding imports to {file_path}: {e}")
        return False


def process_file(file_path: str, print_statements: List[Tuple[int, str]]) -> int:
    """
    Process a single file to replace print statements.

    Args:
        file_path: Path to the file
        print_statements: List of (line_number, line_content) tuples

    Returns:
        Number of replacements made
    """
    replacements = 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Add logging imports if needed
        add_logging_imports(file_path)

        # Process each print statement (in reverse order to maintain line numbers)
        for line_num, line_content in reversed(print_statements):
            category = categorize_print_statement(line_content)
            replacement = generate_logging_replacement(line_content, category)

            if replacement != line_content:  # Only replace if we generated a replacement
                lines[line_num - 1] = replacement + "\n"
                replacements += 1
                print(f"  Replaced line {line_num}: {line_content.strip()[:50]}...")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0

    # Write back the file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"Processed {file_path}: {replacements} replacements")
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return 0

    return replacements


def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python fix_print_statements_automated.py <root_directory>")
        sys.exit(1)

    root_dir = sys.argv[1]

    if not os.path.exists(root_dir):
        print(f"Directory {root_dir} does not exist")
        sys.exit(1)

    print(f"Scanning for print statements in {root_dir}...")

    # Find all print statements
    print_files = find_print_statements(root_dir)

    total_files = len(print_files)
    total_statements = sum(len(statements) for statements in print_files.values())

    print(f"Found {total_statements} print statements in {total_files} files")

    if total_files == 0:
        print("No print statements found!")
        return

    # Process files
    total_replacements = 0
    processed_files = 0

    for file_path, statements in print_files.items():
        print(f"\nProcessing {file_path} ({len(statements)} statements)...")
        replacements = process_file(file_path, statements)
        total_replacements += replacements
        if replacements > 0:
            processed_files += 1

    print("\nSummary:")
    print(f"  Files processed: {processed_files}/{total_files}")
    print(f"  Print statements replaced: {total_replacements}/{total_statements}")
    if total_statements > 0:
        success_rate = (total_replacements / total_statements) * 100
        print(f"  Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
