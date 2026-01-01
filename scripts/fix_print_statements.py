#!/usr/bin/env python3
"""
ACGS-2 Print Statement Replacement Script

Replaces all print() statements with proper logging in the enhanced_agent_bus module.
Part of QUAL-001: Remove Print Statements task execution.
"""

import os
import re
import logging
from pathlib import Path

# Configure logging for this script
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class PrintStatementFixer:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.files_modified = 0
        self.print_statements_replaced = 0

    def find_files_with_print(self) -> list[Path]:
        """Find all Python files containing print() statements."""
        files_with_print = []
        for py_file in self.base_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if re.search(r"\bprint\s*\(", content):
                        files_with_print.append(py_file)
            except Exception as e:
                logger.warning(f"Could not read {py_file}: {e}")
        return files_with_print

    def analyze_print_statement(self, line: str) -> str:
        """Analyze a print statement and determine appropriate logging level."""
        line_lower = line.lower()

        # Error/warning conditions
        if any(
            keyword in line_lower
            for keyword in ["error", "fail", "critical", "exception", "traceback"]
        ):
            return "error"
        elif any(keyword in line_lower for keyword in ["warn", "warning", "alert"]):
            return "warning"
        elif any(keyword in line_lower for keyword in ["debug", "trace"]):
            return "debug"
        else:
            # Default to info for general output
            return "info"

    def replace_print_statement(self, line: str) -> str:
        """Replace a print statement with appropriate logging call."""
        # Extract the content inside print()
        print_match = re.search(r"print\s*\((.*?)\)", line, re.DOTALL)
        if not print_match:
            return line

        content = print_match.group(1).strip()

        # Determine logging level
        log_level = self.analyze_print_statement(line)

        # Create logger call
        if log_level == "error":
            replacement = f"logger.error({content})"
        elif log_level == "warning":
            replacement = f"logger.warning({content})"
        elif log_level == "debug":
            replacement = f"logger.debug({content})"
        else:
            replacement = f"logger.info({content})"

        # Replace the print statement
        new_line = line.replace(f"print({print_match.group(1)})", replacement)
        return new_line

    def add_logging_import(self, content: str) -> str:
        """Add logging import if not already present."""
        lines = content.split("\n")
        import_added = False

        # Check if logging is already imported
        for line in lines:
            line = line.strip()
            if line.startswith("import logging") or "import logging" in line:
                return content  # Already imported
            if line.startswith("import ") or line.startswith("from "):
                # Add logging import after other imports
                if not import_added:
                    lines.insert(lines.index(line), "import logging")
                    import_added = True
                    break

        # If no imports found, add at the beginning after docstring
        if not import_added:
            docstring_end = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    # Find end of docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            docstring_end = j + 1
                            break
                    break

            lines.insert(docstring_end, "import logging")
            lines.insert(docstring_end + 1, "")

        return "\n".join(lines)

    def add_logger_instance(self, content: str, filename: str) -> str:
        """Add logger instance if not already present."""
        lines = content.split("\n")

        # Check if logger is already defined
        for line in lines:
            if "logger = logging.getLogger(" in line:
                return content

        # Find where to add logger (after imports, before code)
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                insert_index = i + 1
            elif line.strip() and not line.strip().startswith("#"):
                # Found first non-import, non-comment line
                break

        # Create logger name from filename
        logger_name = filename.replace(".py", "").replace("/", ".")
        if logger_name.startswith("enhanced_agent_bus."):
            logger_name = logger_name
        else:
            logger_name = f"enhanced_agent_bus.{logger_name}"

        logger_line = f"logger = logging.getLogger(__name__)"

        # Insert logger after imports
        lines.insert(insert_index, "")
        lines.insert(insert_index + 1, logger_line)
        lines.insert(insert_index + 2, "")

        return "\n".join(lines)

    def process_file(self, file_path: Path) -> bool:
        """Process a single file to replace print statements."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            content = original_content
            print_count = len(re.findall(r"\bprint\s*\(", content))

            if print_count == 0:
                return False

            logger.info(f"Processing {file_path} - {print_count} print statements")

            # Add logging import if needed
            content = self.add_logging_import(content)

            # Add logger instance if needed
            content = self.add_logger_instance(content, str(file_path.relative_to(self.base_dir)))

            # Replace print statements
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "print(" in line:
                    lines[i] = self.replace_print_statement(line)
                    self.print_statements_replaced += 1

            new_content = "\n".join(lines)

            # Write back if changed
            if new_content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.files_modified += 1
                logger.info(f"✅ Modified {file_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return False

        return False

    def execute(self):
        """Execute the print statement replacement across all files."""
        logger.info("🔍 Finding files with print statements...")

        files_with_print = self.find_files_with_print()
        logger.info(f"📋 Found {len(files_with_print)} files with print statements")

        for file_path in files_with_print:
            self.process_file(file_path)

        logger.info("📊 EXECUTION SUMMARY")
        logger.info("=" * 30)
        logger.info(f"Files processed: {len(files_with_print)}")
        logger.info(f"Files modified: {self.files_modified}")
        logger.info(f"Print statements replaced: {self.print_statements_replaced}")

        if self.files_modified > 0:
            logger.info("✅ Task QUAL-001 partially completed")
            logger.info("🔄 Next steps: Update imports and test logging functionality")
        else:
            logger.warning("⚠️ No files were modified - check for issues")


def main():
    base_dir = "acgs2-core/enhanced_agent_bus"

    if not os.path.exists(base_dir):
        logger.error(f"Directory {base_dir} not found")
        return

    fixer = PrintStatementFixer(base_dir)
    fixer.execute()


if __name__ == "__main__":
    main()
