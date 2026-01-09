#!/usr/bin/env python3
"""
ACGS-2 Large File Refactoring Plan
"""

from pathlib import Path


class RefactoringPlanner:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def analyze_large_files(self):
        """Analyze files that are too large and suggest refactoring."""
        large_files = []

        for py_file in self.project_root.rglob("src/**/*.py"):
            if ".venv" in str(py_file) or "node_modules" in str(py_file):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                if len(lines) > 400:  # Files over 400 lines
                    large_files.append(
                        {
                            "file": str(py_file),
                            "lines": len(lines),
                            "classes": sum(
                                1 for line in lines if line.strip().startswith("class ")
                            ),
                            "functions": sum(
                                1 for line in lines if line.strip().startswith("def ")
                            ),
                            "imports": sum(
                                1 for line in lines if line.strip().startswith(("import ", "from "))
                            ),
                        }
                    )

            except Exception:
                continue

        return sorted(large_files, key=lambda x: x["lines"], reverse=True)

    def suggest_refactoring(self, file_info):
        """Suggest refactoring approaches for large files."""
        suggestions = []
        file_path = file_info["file"]

        if file_info["classes"] > 5:
            suggestions.append("Split into multiple modules (one per class)")

        if file_info["functions"] > 20:
            suggestions.append("Extract utility functions into separate module")

        if file_info["imports"] > 30:
            suggestions.append("Consider module reorganization to reduce import complexity")

        if "test" in file_path.lower():
            suggestions.append("Break up large test file into multiple test modules")
        elif "api" in file_path.lower():
            suggestions.append("Split API endpoints into logical groups")
        elif "service" in file_path.lower():
            suggestions.append("Extract business logic into separate service classes")

        return suggestions


def main():
    planner = RefactoringPlanner(Path("."))
    large_files = planner.analyze_large_files()

    with open("refactoring_recommendations.md", "w") as f:
        f.write("# ACGS-2 Large File Refactoring Plan\n\n")
        f.write(f"Generated for {len(large_files)} oversized files\n\n")

        for i, file_info in enumerate(large_files[:10], 1):  # Top 10
            file_path = file_info["file"]
            relative_path = Path(file_path).relative_to(Path("."))

            suggestions = planner.suggest_refactoring(file_info)
            if suggestions:
                for _ in suggestions:
                    pass

            # Write to file
            f.write(f"## {i}. {relative_path}\n\n")
            f.write(f"- **Lines:** {file_info['lines']}\n")
            f.write(f"- **Classes:** {file_info['classes']}\n")
            f.write(f"- **Functions:** {file_info['functions']}\n")
            f.write(f"- **Imports:** {file_info['imports']}\n\n")

            if suggestions:
                f.write("### Suggestions\n\n")
                for suggestion in suggestions:
                    f.write(f"- {suggestion}\n")
                f.write("\n")


if __name__ == "__main__":
    main()
