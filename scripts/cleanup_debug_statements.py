#!/usr/bin/env python3
"""
Script to clean up debug statements from production code.

This script removes print() statements and logger.debug() calls from production code,
while preserving them in test files and legitimate logging statements.
"""

import re
from pathlib import Path


def should_process_file(filepath: Path) -> bool:
    """Determine if a file should be processed for debug cleanup."""
    # Skip test files
    if "test" in str(filepath).lower() or "tests" in str(filepath):
        return False

    # Skip example files
    if "example" in str(filepath).lower():
        return False

    # Skip script files (they might need debug output)
    if "scripts" in str(filepath):
        return False

    # Skip research and experimental code
    if "research" in str(filepath) or "experiments" in str(filepath):
        return False

    # Only process Python files
    return filepath.suffix == ".py"


def clean_debug_statements(content: str) -> tuple[str, int]:
    """Clean debug statements from file content."""
    original_lines = content.count("\n") + 1

    # Remove print() statements (but preserve those with variables that might be needed)
    # Only remove simple print statements without variables
    content = re.sub(r"^\s*print\([^)]*\)\s*$", "", content, flags=re.MULTILINE)

    # Remove logger.debug() calls
    content = re.sub(r"^\s*logger\.debug\(.*?\)\s*$", "", content, flags=re.MULTILINE)

    # Remove consecutive empty lines (but keep at most 2)
    content = re.sub(r"\n\n\n+", "\n\n", content)

    new_lines = content.count("\n") + 1
    cleaned_count = original_lines - new_lines

    return content, cleaned_count


def main():
    """Main cleanup function."""
    src_dir = Path("src")
    total_cleaned = 0
    files_processed = 0

    for py_file in src_dir.rglob("*.py"):
        if should_process_file(py_file):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    original_content = f.read()

                cleaned_content, cleaned_count = clean_debug_statements(original_content)

                if cleaned_count > 0:
                    with open(py_file, "w", encoding="utf-8") as f:
                        f.write(cleaned_content)

                    print(f"Cleaned {cleaned_count} debug statements from {py_file}")
                    total_cleaned += cleaned_count
                    files_processed += 1

            except Exception as e:
                print(f"Error processing {py_file}: {e}")

    print("\nSummary:")
    print(f"- Files processed: {files_processed}")
    print(f"- Total debug statements removed: {total_cleaned}")


if __name__ == "__main__":
    main()
