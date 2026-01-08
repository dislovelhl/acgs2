#!/usr/bin/env python3
"""
ACGS-2 String Concatenation Optimization
"""

from pathlib import Path


class StringOptimizer:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def find_string_concat_patterns(self):
        """Find inefficient string concatenation patterns."""
        patterns = []

        for py_file in self.project_root.rglob("src/**/*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Look for string += patterns in loops
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if "+=" in line and ("str" in line.lower() or "String" in line):
                        # Check if it's in a loop context (look back a few lines)
                        loop_context = False
                        for j in range(max(0, i - 5), i):
                            if any(
                                keyword in lines[j]
                                for keyword in ["for ", "while ", "if ", "elif "]
                            ):
                                loop_context = True
                                break

                        if loop_context:
                            patterns.append(
                                {
                                    "file": str(py_file),
                                    "line": i,
                                    "content": line.strip(),
                                    "context": "\n".join(
                                        lines[max(0, i - 2) : min(len(lines), i + 3)]
                                    ),
                                }
                            )

            except Exception:
                continue

        return patterns

    def optimize_patterns(self, patterns):
        """Apply string optimization suggestions."""
        optimizations = []

        for pattern in patterns:
            file_path = pattern["file"]
            line_num = pattern["line"]
            content = pattern["content"]

            # Suggest using join() instead of +=
            if " += " in content:
                content.replace(" += ", " = ").replace(
                    "str_var", "parts.append(str_var)"
                )
                optimizations.append(
                    {
                        "file": file_path,
                        "line": line_num,
                        "original": content,
                        "suggestion": f"Use list.append() then ''.join(parts) instead:\n{content.replace(' += ', ' = ')}\nparts = []\nparts.append(...)\nresult = ''.join(parts)",
                    }
                )

        return optimizations


def main():
    optimizer = StringOptimizer(Path("."))
    patterns = optimizer.find_string_concat_patterns()

    print(f"Found {len(patterns)} string concatenation patterns in loops")

    if patterns:
        optimizations = optimizer.optimize_patterns(patterns)
        print(f"Generated {len(optimizations)} optimization suggestions")

        # Save to file
        with open("string_optimizations.txt", "w") as f:
            f.write("ACGS-2 String Concatenation Optimizations\n")
            f.write("=" * 50 + "\n\n")

            for opt in optimizations[:10]:  # Show first 10
                f.write(f"File: {opt['file']}:{opt['line']}\n")
                f.write(f"Original: {opt['original']}\n")
                f.write(f"Suggestion: {opt['suggestion']}\n\n")

        print("✅ Optimizations saved to string_optimizations.txt")


if __name__ == "__main__":
    main()
