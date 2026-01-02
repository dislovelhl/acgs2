#!/usr/bin/env python3
"""
QUAL-001: Print Statement Removal Tool
Constitutional Hash: cdd01ef066bc6cf2

Systematically replaces print() statements with appropriate logging across ACGS-2 codebase.
Prioritizes critical files and maintains functionality while improving code quality.
"""

import ast
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging for this tool
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
tool_logger = logging.getLogger(__name__)

# Constitutional hash for validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Categories of files with different replacement strategies
FILE_CATEGORIES = {
    "core_services": {  # Highest priority - must use logging
        "enhanced_agent_bus/",
        "services/",
        "shared/",
    },
    "testing": {  # Should use logging for test output
        "testing/",
        "tests/",
        "/tests/",
    },
    "tools_scripts": {  # Should use logging
        "tools/",
        "scripts/",
        "quantum_research/",
    },
    "examples_demos": {  # May keep print() for demonstration purposes
        "examples/",
        "demo",
        "example",
    },
    "documentation": {  # Skip - documentation files
        "README",
        "CHANGELOG",
        "DEPLOYMENT",
        "GUIDE",
        ".md",
    },
}


class PrintStatementAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to find and categorize print statements."""

    def __init__(self, source_code: str, filename: str):
        self.source_code = source_code
        self.filename = filename
        self.print_statements: List[Tuple[int, str]] = []  # (line_number, statement_text)
        self.has_logging_import = False
        self.has_logger_definition = False
        self.logger_name = None

    def visit_Import(self, node: ast.Import) -> None:
        """Check for logging import."""
        for alias in node.names:
            if alias.name == "logging":
                self.has_logging_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for logging import from."""
        if node.module == "logging":
            self.has_logging_import = True
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for logger definition."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if hasattr(node.value, "func") and isinstance(node.value.func, ast.Attribute):
                    if (
                        isinstance(node.value.func.value, ast.Call)
                        and hasattr(node.value.func.value.func, "id")
                        and node.value.func.value.func.id == "getLogger"
                    ):
                        self.has_logger_definition = True
                        self.logger_name = target.id
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Find print() calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            line_number = getattr(node, "lineno", 0)
            # Extract the print statement text
            lines = self.source_code.split("\n")
            if line_number <= len(lines):
                statement_text = lines[line_number - 1].strip()
                self.print_statements.append((line_number, statement_text))
        self.generic_visit(node)


class PrintToLoggingConverter:
    """Converts print statements to appropriate logging calls."""

    def __init__(self, source_code: str, filename: str):
        self.source_code = source_code
        self.filename = filename
        self.lines = source_code.split("\n")
        self.analyzer = PrintStatementAnalyzer(source_code, filename)
        self.analyzer.visit(ast.parse(source_code))

    def categorize_file(self) -> str:
        """Categorize file type for replacement strategy."""
        path = Path(self.filename)

        # Check for documentation files
        if any(str(path).endswith(ext) for ext in [".md", ".txt", ".rst"]):
            return "documentation"

        # Check for examples/demos
        if any(keyword in str(path).lower() for keyword in ["example", "demo"]):
            return "examples_demos"

        # Check for testing files
        if any(part in ["testing", "tests"] for part in path.parts):
            return "testing"

        # Check for tools/scripts
        if any(part in ["tools", "scripts"] for part in path.parts):
            return "tools_scripts"

        # Check for core services
        if any(part in ["enhanced_agent_bus", "services", "shared"] for part in path.parts):
            return "core_services"

        return "other"

    def determine_log_level(self, print_statement: str) -> str:
        """Determine appropriate logging level for print statement."""
        lower_stmt = print_statement.lower()

        # Error conditions
        if any(
            word in lower_stmt for word in ["error", "exception", "failed", "failure", "critical"]
        ):
            return "ERROR"

        # Warning conditions
        if any(word in lower_stmt for word in ["warning", "warn", "deprecated", "timeout"]):
            return "WARNING"

        # Debug conditions (detailed technical info)
        if any(word in lower_stmt for word in ["debug", "trace", "verbose", "detail"]):
            return "DEBUG"

        # Info for general output (default)
        return "INFO"

    def generate_replacement(self, line_number: int, statement_text: str) -> Tuple[str, List[str]]:
        """Generate logging replacement for print statement."""
        log_level = self.determine_log_level(statement_text)

        # Extract the arguments from print statement
        # Handle multiline print statements by finding the complete print call
        lines_to_check = []
        start_line = line_number - 1
        open_parens = 0
        in_string = False
        string_char = None

        for i in range(start_line, len(self.lines)):
            line = self.lines[i]
            j = 0
            while j < len(line):
                char = line[j]

                # Handle string literals
                if not in_string and char in ('"', "'"):
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    # Check for escaped quote
                    escape_count = 0
                    k = j - 1
                    while k >= 0 and line[k] == "\\":
                        escape_count += 1
                        k -= 1
                    if escape_count % 2 == 0:  # Not escaped
                        in_string = False
                        string_char = None
                elif not in_string:
                    if char == "(":
                        open_parens += 1
                    elif char == ")":
                        open_parens -= 1
                        if open_parens == 0:
                            # Found the complete print statement
                            lines_to_check.append(line[: j + 1])
                            break

                j += 1

            lines_to_check.append(line)
            if open_parens == 0:
                break

        # Join the lines and extract arguments
        full_statement = "\n".join(lines_to_check)

        # Use AST to parse the print call properly
        try:
            tree = ast.parse(full_statement, mode="eval")
            if (
                isinstance(tree.body, ast.Call)
                and isinstance(tree.body.func, ast.Name)
                and tree.body.func.id == "print"
            ):
                # Convert AST arguments back to string representation
                args_parts = []
                for arg in tree.body.args:
                    if isinstance(arg, ast.Str):
                        args_parts.append(repr(arg.s))
                    elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        args_parts.append(repr(arg.value))
                    else:
                        # For complex expressions, use ast.unparse if available (Python 3.9+)
                        # Otherwise, keep the original argument representation
                        arg_lines = self.lines[start_line : start_line + len(lines_to_check)]
                        arg_text = "\n".join(arg_lines)
                        # Extract just the argument part
                        print_match = re.search(r"print\s*\(\s*(.+?)\s*\)", arg_text, re.DOTALL)
                        if print_match:
                            args_parts.append(print_match.group(1).strip())
                        else:
                            args_parts.append(str(arg))

                args = ", ".join(args_parts)

                # Generate logger call
                if self.analyzer.logger_name:
                    logger_call = f"{self.analyzer.logger_name}.{log_level.lower()}({args})"
                else:
                    # Fallback to basic logging
                    logger_call = f"logging.{log_level.lower()}({args})"

                return logger_call, []
        except:
            pass

        # Fallback: simple regex approach
        match = re.search(r"print\s*\(\s*(.+?)\s*\)", statement_text, re.DOTALL)
        if match:
            args = match.group(1).strip()

            # Generate logger call
            if self.analyzer.logger_name:
                logger_call = f"{self.analyzer.logger_name}.{log_level.lower()}({args})"
            else:
                # Fallback to basic logging
                logger_call = f"logging.{log_level.lower()}({args})"

            return logger_call, []

        return statement_text, []  # No change if can't parse

    def convert_file(self) -> Tuple[str, List[str]]:
        """Convert all print statements in file to logging."""
        modified_lines = self.lines.copy()
        replacements_made = []
        changes = []

        # Sort print statements by line number (reverse order to maintain line numbers)
        for line_number, statement_text in reversed(self.analyzer.print_statements):
            replacement, additional_lines = self.generate_replacement(line_number, statement_text)

            # Replace the line
            modified_lines[line_number - 1] = modified_lines[line_number - 1].replace(
                statement_text, replacement
            )
            changes.append(f"Line {line_number}: {statement_text} -> {replacement}")

        # Add logging import if needed and not present
        if not self.analyzer.has_logging_import and changes:
            # Insert import after any existing imports
            insert_pos = 0
            for i, line in enumerate(modified_lines):
                if line.startswith(("import ", "from ")):
                    insert_pos = i + 1
                elif line.strip() and not line.startswith(("import ", "from ", "#", '"""', "'''")):
                    break

            modified_lines.insert(insert_pos, "import logging")
            changes.insert(0, "Added: import logging")

        # Add logger definition if needed and not present
        if not self.analyzer.has_logger_definition and changes and self.analyzer.has_logging_import:
            # Insert after imports
            insert_pos = 0
            for i, line in enumerate(modified_lines):
                if line.startswith(("import ", "from ")) or line.strip() == "":
                    insert_pos = i + 1
                elif line.strip() and not line.startswith("#"):
                    break

            logger_definition = "logger = logging.getLogger(__name__)"
            modified_lines.insert(insert_pos, "")
            modified_lines.insert(insert_pos + 1, logger_definition)
            changes.insert(0, f"Added: {logger_definition}")

        return "\n".join(modified_lines), changes


def process_file(file_path: str, dry_run: bool = True) -> Dict[str, any]:
    """Process a single file for print statement replacement."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        converter = PrintToLoggingConverter(source_code, file_path)
        category = converter.categorize_file()

        # Skip documentation files
        if category == "documentation":
            return {
                "file": file_path,
                "category": category,
                "action": "skipped",
                "reason": "documentation file",
                "print_count": len(converter.analyzer.print_statements),
            }

        # Skip example files (may keep print for demo purposes)
        if category == "examples_demos":
            return {
                "file": file_path,
                "category": category,
                "action": "skipped",
                "reason": "example/demo file - keeping print for demonstration",
                "print_count": len(converter.analyzer.print_statements),
            }

        # Process files that need conversion
        new_code, changes = converter.convert_file()

        if not changes:
            return {
                "file": file_path,
                "category": category,
                "action": "no_changes",
                "reason": "no print statements to convert",
                "print_count": 0,
            }

        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_code)

        return {
            "file": file_path,
            "category": category,
            "action": "converted" if not dry_run else "would_convert",
            "changes": changes,
            "print_count": len(converter.analyzer.print_statements),
        }

    except Exception as e:
        tool_logger.error(f"Error processing {file_path}: {e}")
        return {
            "file": file_path,
            "category": "error",
            "action": "error",
            "error": str(e),
            "print_count": 0,
        }


def main():
    """Main QUAL-001 execution."""
    print("🔧 QUAL-001: Print Statement Removal")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    # Parse command line arguments
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    else:
        print("⚠️  LIVE MODE - Files will be modified")

    print()

    # Find all Python files with print statements
    project_root = Path(__file__).parent / "acgs2-core"
    python_files = []

    for root, dirs, files in os.walk(project_root):
        # Skip virtual environment
        if ".venv" in dirs:
            dirs.remove(".venv")

        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                python_files.append(str(file_path))

    print(f"📁 Found {len(python_files)} Python files to analyze")

    # Process files
    results = []
    total_print_statements = 0
    converted_files = 0

    for file_path in python_files:
        result = process_file(file_path, dry_run)
        results.append(result)
        total_print_statements += result.get("print_count", 0)

        if result["action"] in ["converted", "would_convert"]:
            converted_files += 1
            if verbose:
                print(f"✅ {result['file']}: {result['print_count']} statements")
        elif result["action"] == "skipped" and verbose:
            print(f"⏭️  {result['file']}: skipped ({result.get('reason', 'unknown')})")

    # Summary
    print()
    print("📊 QUAL-001 EXECUTION SUMMARY")
    print("-" * 30)

    categories = {}
    for result in results:
        cat = result.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"files": 0, "print_statements": 0, "converted": 0}
        categories[cat]["files"] += 1
        categories[cat]["print_statements"] += result.get("print_count", 0)
        if result["action"] in ["converted", "would_convert"]:
            categories[cat]["converted"] += 1

    for category, stats in categories.items():
        action_word = "would convert" if dry_run else "converted"
        print(
            f"{category}: {stats['files']} files, {stats['print_statements']} print statements, {stats['converted']} {action_word}"
        )

    print()
    print(f"Total files analyzed: {len(results)}")
    print(f"Total print statements: {total_print_statements}")
    print(f"Files {('that would be' if dry_run else '')} converted: {converted_files}")

    if dry_run:
        print()
        print("💡 To apply changes, run without --dry-run flag")
        print("💡 Use --verbose for detailed file-by-file output")

    print()
    print("🎯 QUAL-001 COMPLETE")
    print("✅ Print statement analysis and conversion ready")


if __name__ == "__main__":
    main()
