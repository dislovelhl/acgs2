#!/usr/bin/env python3
"""
ACGS-2 Debug Code Cleanup Script - Comprehensive Execution
Priority: HIGH-001
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple


class DebugCleanup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.replacements: Dict[str, List[Tuple[int, str, str]]] = {}

    def find_debug_statements(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find all debug print statements in core services."""
        debug_files = {}

        # Find all Python files in core services (excluding CLI/tools/examples/venv)
        for py_file in self.project_root.rglob("src/**/*.py"):
            if any(
                skip in str(py_file)
                for skip in [
                    "cli/",
                    "tools/",
                    "scripts/",
                    "examples/",
                    "verify_",
                    ".venv/",
                    "/venv/",
                    "/node_modules/",
                ]
            ):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                debug_lines = []
                for i, line in enumerate(lines, 1):
                    # Find print statements that are not in comments or strings
                    stripped = line.strip()
                    if (
                        stripped.startswith("print(")
                        and not stripped.startswith("#")
                        and '"""' not in line
                        and "'''" not in line
                    ):
                        debug_lines.append((i, stripped))

                if debug_lines:
                    debug_files[str(py_file)] = debug_lines

            except Exception as e:
                print(f"Error reading {py_file}: {e}")

        return debug_files

    def analyze_replacements(self, debug_files: Dict[str, List[Tuple[int, str]]]) -> None:
        """Analyze what replacements should be made."""
        for file_path, debug_lines in debug_files.items():
            replacements = []

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    content = "".join(lines)

                # Check if file has logging setup
                has_logger = "logger = logging.getLogger" in content or "get_logger" in content

                for line_num, debug_line in debug_lines:
                    if has_logger:
                        # Replace with logger.debug
                        if "Error" in debug_line or "Failed" in debug_line:
                            replacement = debug_line.replace("print(", "logger.error(")
                        elif "success" in debug_line.lower() or "✓" in debug_line:
                            replacement = debug_line.replace("print(", "logger.info(")
                        else:
                            replacement = debug_line.replace("print(", "logger.debug(")
                    else:
                        # Comment out the print statement if no logger
                        replacement = f"# {debug_line}"

                    replacements.append((line_num, debug_line, replacement))

            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                continue

            if replacements:
                self.replacements[file_path] = replacements

    def apply_replacements(self) -> int:
        """Apply all replacements to files."""
        total_applied = 0
        for file_path, file_replacements in self.replacements.items():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Apply from bottom up to maintain line numbers if needed,
                # but here we match exact strings so order doesn't matter much
                # as long as we don't have multiple identical print() on same line
                for line_num, original, replacement in reversed(file_replacements):
                    idx = line_num - 1
                    if lines[idx].strip() == original:
                        # Preserve indentation
                        indent = lines[idx][: lines[idx].find("p")]
                        lines[idx] = indent + replacement + "\n"
                        total_applied += 1

                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

            except Exception as e:
                print(f"Error writing {file_path}: {e}")

        return total_applied

    def generate_report(self) -> str:
        """Generate cleanup report."""
        total_files = len(self.replacements)
        total_statements = sum(len(replacements) for replacements in self.replacements.values())

        report = f"""🔧 ACGS-2 Debug Code Cleanup Report
═══════════════════════════════════════════════

📊 SUMMARY
Files cleaned: {total_files}
Debug statements replaced: {total_statements}

📁 FILES PROCESSED:
"""

        for file_path, replacements in self.replacements.items():
            relative_path = Path(file_path).relative_to(self.project_root)
            report += f"✅ {relative_path} ({len(replacements)} replacements)\n"

        return report

    def run(self, dry_run: bool = True) -> str:
        """Execute the cleanup workflow."""
        print(f"🔍 Finding debug statements (dry_run={dry_run})...")
        debug_files = self.find_debug_statements()

        print(f"📊 Found {len(debug_files)} files with debug statements")
        self.analyze_replacements(debug_files)

        if not dry_run:
            print("🚀 Applying replacements...")
            applied = self.apply_replacements()
            print(f"✅ Replaced {applied} statements")

        return self.generate_report()


if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv
    cleanup = DebugCleanup()
    report = cleanup.run(dry_run=dry_run)
    print(report)
