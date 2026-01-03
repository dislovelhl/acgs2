#!/usr/bin/env python3
"""
ACGS-2 Auto Quality Fixer
Automatically fixes common code quality issues
"""

import re
from pathlib import Path


class QualityAutoFixer:
    """Automatically fixes common code quality issues."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixed_count = 0

    def run_auto_fixes(self):
        """Run all automatic fixes."""
        print("🔧 ACGS-2 Auto Quality Fixer")
        print("=" * 40)

        # Fix bare except clauses
        self.fix_bare_except_clauses()

        # Fix print statements in production code
        self.fix_print_statements()

        # Fix common import issues
        self.fix_import_issues()

        print(f"\n✅ Fixed {self.fixed_count} issues automatically")
        print("\nRemaining issues require manual review:")
        print("- Syntax errors (need manual fixes)")
        print("- Undefined names (may need imports or variable definitions)")
        print("- Complex logic issues (require code review)")

    def fix_bare_except_clauses(self):
        """Fix bare except clauses by adding specific exception types."""
        print("\n🔍 Fixing bare except clauses...")

        # Common bare except patterns and their fixes
        patterns = [
            # HTTP-related exceptions
            (
                r"except:\s*$",
                "except (httpx.RequestError, httpx.TimeoutException, Exception) as e:",
                "api_gateway",
            ),
            # JSON parsing
            (r"except:\s*$", "except (json.JSONDecodeError, TypeError, ValueError) as e:", "json"),
            # General exceptions
            (r"except:\s*$", "except Exception as e:", "general"),
        ]

        for pattern, replacement, context in patterns:
            self._fix_pattern_in_files(pattern, replacement, context, "*.py")

    def fix_print_statements(self):
        """Replace print statements with logging in production code."""
        print("\n📝 Converting print statements to logging...")

        # Skip test files and example files

        print("⚠️  Skipping print statement conversion (requires manual review)")
        print("   Manual conversion needed for context-aware logging")

    def fix_import_issues(self):
        """Fix common import issues."""
        print("\n📦 Checking import issues...")

        # This would require more complex analysis
        # For now, just report what we found
        print("ℹ️  Import issues require manual review")

    def _fix_pattern_in_files(
        self, pattern: str, replacement: str, context: str, file_pattern: str
    ):
        """Fix a pattern in matching files."""
        for file_path in self.root_dir.rglob(file_pattern):
            if self._should_process_file(file_path, context):
                self._fix_pattern_in_file(file_path, pattern, replacement, context)

    def _should_process_file(self, file_path: Path, context: str) -> bool:
        """Determine if a file should be processed for a given context."""
        # Skip certain directories
        if any(skip in str(file_path) for skip in ["venv", ".venv", "__pycache__", "node_modules"]):
            return False

        # Context-specific filtering
        if context == "api_gateway" and "api_gateway" in str(file_path).lower():
            return True
        elif context == "json" and (
            "json" in file_path.read_text() or "parse" in file_path.read_text()
        ):
            return True
        elif context == "general":
            return "api_gateway" not in str(file_path) and "json" not in file_path.read_text()

        return True

    def _fix_pattern_in_file(self, file_path: Path, pattern: str, replacement: str, context: str):
        """Fix a pattern in a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find all matches
            matches = list(re.finditer(pattern, content, re.MULTILINE))

            if not matches:
                return

            # Apply fixes
            modified_content = content
            for match in reversed(matches):  # Process in reverse to maintain positions
                start, end = match.span()

                # Check if this is actually a bare except (not already fixed)
                line_start = content.rfind("\n", 0, start) + 1
                line = content[line_start:end].strip()

                if line == "except:":
                    # Check if we need logging import
                    if "logger." in replacement and "logging" not in modified_content:
                        # Add logging import if needed
                        import_match = re.search(
                            r"^(import|from).*", modified_content, re.MULTILINE
                        )
                        if import_match:
                            insert_pos = import_match.end()
                            modified_content = (
                                modified_content[:insert_pos]
                                + "\n"
                                + "import logging\n"
                                + "logger = logging.getLogger(__name__)\n"
                                + modified_content[insert_pos:]
                            )

                    # Replace the bare except
                    modified_content = (
                        modified_content[:start] + replacement + modified_content[end:]
                    )

                    self.fixed_count += 1
                    print(f"  ✅ Fixed bare except in {file_path.name}")

            # Write back if modified
            if modified_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)

        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")


def main():
    """Main execution."""
    fixer = QualityAutoFixer("acgs2-core")
    fixer.run_auto_fixes()


if __name__ == "__main__":
    main()
