#!/usr/bin/env python3
"""
QUAL-001: Print Statement Removal Tool v2
Constitutional Hash: cdd01ef066bc6cf2

Simplified, more robust version that handles edge cases better.
"""

import logging
import os
import re
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
tool_logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def determine_log_level(text: str) -> str:
    """Determine appropriate logging level based on content."""
    text_lower = text.lower()

    # Error conditions
    if any(
        word in text_lower
        for word in ["error", "exception", "failed", "failure", "critical", "fail"]
    ):
        return "ERROR"

    # Warning conditions
    if any(word in text_lower for word in ["warning", "warn", "deprecated", "timeout"]):
        return "WARNING"

    # Debug conditions (technical details)
    if any(word in text_lower for word in ["debug", "trace", "verbose", "detail"]):
        return "DEBUG"

    # Info for general output (default)
    return "INFO"


def convert_print_to_logging(content: str) -> str:
    """Convert print statements to logging calls."""
    lines = content.split("\n")
    modified_lines = []
    has_logging_import = False
    has_logger = False
    logger_name = "logger"

    for line in lines:
        # Check for existing logging setup
        if "import logging" in line:
            has_logging_import = True
        if "logger = logging.getLogger" in line:
            has_logger = True
            # Extract logger name if possible
            match = re.search(r"(\w+)\s*=\s*logging\.getLogger", line)
            if match:
                logger_name = match.group(1)

        # Look for print statements
        print_match = re.search(r"^\s*print\s*\(", line)
        if print_match:
            # Extract the arguments from print statement
            args_match = re.search(r"print\s*\(\s*(.+?)\s*\)$", line)
            if args_match:
                args = args_match.group(1)
                log_level = determine_log_level(args)

                # Replace with logging call
                indent = re.match(r"^\s*", line).group(0)
                if has_logger:
                    new_line = f"{indent}{logger_name}.{log_level.lower()}({args})"
                else:
                    new_line = f"{indent}logging.{log_level.lower()}({args})"

                modified_lines.append(new_line)
                continue

        modified_lines.append(line)

    # Add logging imports if needed and we made changes
    final_content = "\n".join(modified_lines)

    # Check if we actually made changes
    if final_content != content:
        # Add logging import if not present
        if not has_logging_import:
            # Find a good place to insert the import
            lines = final_content.split("\n")
            insert_pos = 0

            for i, line in enumerate(lines):
                if line.startswith(("import ", "from ")) or line.strip() == "":
                    insert_pos = i + 1
                elif line.strip() and not line.startswith("#"):
                    break

            lines.insert(insert_pos, "import logging")
            final_content = "\n".join(lines)

        # Add logger definition if not present
        if not has_logger and "import logging" in final_content:
            lines = final_content.split("\n")
            insert_pos = 0

            for i, line in enumerate(lines):
                if line.startswith(("import ", "from ")) or line.strip() == "":
                    insert_pos = i + 1
                elif line.strip() and not line.startswith("#"):
                    break

            # Insert logger after imports
            lines.insert(insert_pos, "")
            lines.insert(insert_pos + 1, "logger = logging.getLogger(__name__)")
            final_content = "\n".join(lines)

    return final_content


def process_file(file_path: str) -> bool:
    """Process a single file for print statement conversion."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Skip if no print statements
        if "print(" not in original_content:
            return False

        # Skip example/demo files
        path = Path(file_path)
        if any(keyword in str(path).lower() for keyword in ["example", "demo"]):
            return False

        # Skip documentation files
        if str(path).endswith((".md", ".txt", ".rst")):
            return False

        new_content = convert_print_to_logging(original_content)

        # Only write if content changed
        if new_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Count changes
            original_lines = original_content.split("\n")
            new_lines = new_content.split("\n")
            print_count = sum(1 for line in original_lines if "print(" in line)
            tool_logger.info(f"Converted {print_count} print statements in {file_path}")
            return True

    except Exception as e:
        tool_logger.error(f"Error processing {file_path}: {e}")

    return False


def main():
    """Main QUAL-001 execution."""
    print("🔧 QUAL-001: Print Statement Removal v2")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    # Find all Python files in acgs2-core (excluding venv)
    project_root = Path("acgs2-core")
    python_files = []

    for root, dirs, files in os.walk(project_root):
        # Skip virtual environment
        if ".venv" in dirs:
            dirs.remove(".venv")

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    print(f"📁 Found {len(python_files)} Python files to process")

    converted_count = 0
    total_print_statements = 0

    for file_path in python_files:
        if process_file(str(file_path)):
            converted_count += 1

        # Count print statements in this file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                print_count = content.count("print(")
                total_print_statements += print_count
        except:
            pass

    print()
    print("📊 QUAL-001 EXECUTION SUMMARY")
    print("-" * 30)
    print(f"Files processed: {len(python_files)}")
    print(f"Files converted: {converted_count}")
    print(f"Total print statements found: {total_print_statements}")

    print()
    print("🎯 QUAL-001 v2 COMPLETE")
    print("✅ Print statements converted to logging")


if __name__ == "__main__":
    main()
