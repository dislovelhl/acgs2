#!/usr/bin/env python3
"""
ACGS-2 Test File Optimization Script
Analyzes and provides recommendations for splitting large test files
"""

import re
from pathlib import Path
from typing import Dict, List


class TestFileAnalyzer:
    """Analyzes test files and provides optimization recommendations."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.test_files: Dict[str, Dict] = {}

    def analyze_test_files(self) -> Dict[str, Dict]:
        """Analyze all test files in the codebase."""
        test_pattern = re.compile(r"test.*\.py$")

        for py_file in self.root_dir.rglob("*.py"):
            if test_pattern.search(py_file.name):
                analysis = self._analyze_single_file(py_file)
                if analysis:
                    self.test_files[str(py_file)] = analysis

        return self.test_files

    def _analyze_single_file(self, file_path: Path) -> Dict:
        """Analyze a single test file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return None

        lines = content.split("\n")
        line_count = len(lines)

        # Skip files that aren't too large
        if line_count < 500:
            return None

        # Find test classes and functions
        class_pattern = re.compile(r"^class\s+(Test\w+)")
        function_pattern = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)")

        classes = []
        functions = []

        for line in lines:
            class_match = class_pattern.match(line.strip())
            if class_match:
                classes.append(class_match.group(1))

            func_match = function_pattern.match(line.strip())
            if func_match:
                functions.append(func_match.group(1))

        return {
            "line_count": line_count,
            "classes": classes,
            "functions": functions,
            "class_count": len(classes),
            "function_count": len(functions),
            "avg_functions_per_class": len(functions) / len(classes) if classes else 0,
        }

    def generate_optimization_plan(self) -> List[Dict]:
        """Generate optimization recommendations."""
        recommendations = []

        for file_path, analysis in self.test_files.items():
            if analysis["line_count"] > 1000:
                # Major refactoring needed
                plan = self._create_refactor_plan(file_path, analysis)
                recommendations.append(plan)
            elif analysis["line_count"] > 500:
                # Minor optimization needed
                plan = self._create_split_plan(file_path, analysis)
                recommendations.append(plan)

        return sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)

    def _create_refactor_plan(self, file_path: str, analysis: Dict) -> Dict:
        """Create a major refactoring plan for very large files."""
        Path(file_path).name

        # Group classes by functionality
        classes = analysis["classes"]
        groups = self._group_classes_by_functionality(classes)

        return {
            "file": file_path,
            "type": "major_refactor",
            "line_count": analysis["line_count"],
            "issues": [
                f"File too large ({analysis['line_count']} lines)",
                f"Too many test classes ({analysis['class_count']})",
                f"Too many test functions ({analysis['function_count']})",
            ],
            "recommended_splits": groups,
            "priority_score": analysis["line_count"] * 2 + analysis["class_count"],
        }

    def _create_split_plan(self, file_path: str, analysis: Dict) -> Dict:
        """Create a split plan for moderately large files."""
        return {
            "file": file_path,
            "type": "split",
            "line_count": analysis["line_count"],
            "issues": [
                f"Moderately large file ({analysis['line_count']} lines)",
                "Multiple concerns in single file",
            ],
            "recommended_splits": self._suggest_splits(analysis["classes"]),
            "priority_score": analysis["line_count"] + analysis["class_count"] * 10,
        }

    def _group_classes_by_functionality(self, classes: List[str]) -> Dict[str, List[str]]:
        """Group test classes by functionality."""
        groups = {
            "lifecycle": [],
            "messaging": [],
            "routing": [],
            "security": [],
            "metrics": [],
            "integration": [],
            "edge_cases": [],
            "other": [],
        }

        for cls in classes:
            cls_lower = cls.lower()
            if any(word in cls_lower for word in ["lifecycle", "start", "stop", "init"]):
                groups["lifecycle"].append(cls)
            elif any(word in cls_lower for word in ["message", "send", "receive"]):
                groups["messaging"].append(cls)
            elif any(word in cls_lower for word in ["route", "kafka", "queue"]):
                groups["routing"].append(cls)
            elif any(word in cls_lower for word in ["security", "auth", "permission"]):
                groups["security"].append(cls)
            elif any(word in cls_lower for word in ["metric", "monitor", "telemetry"]):
                groups["metrics"].append(cls)
            elif any(word in cls_lower for word in ["integration", "e2e"]):
                groups["integration"].append(cls)
            elif any(word in cls_lower for word in ["edge", "error", "exception"]):
                groups["edge_cases"].append(cls)
            else:
                groups["other"].append(cls)

        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

    def _suggest_splits(self, classes: List[str]) -> Dict[str, List[str]]:
        """Suggest simple splits for moderately large files."""
        if len(classes) <= 3:
            return {"keep_as_is": classes}
        else:
            mid = len(classes) // 2
            return {"part_1": classes[:mid], "part_2": classes[mid:]}


def main():
    """Main execution."""
    analyzer = TestFileAnalyzer("acgs2-core")

    print("🔍 Analyzing test files...")
    test_files = analyzer.analyze_test_files()

    print(f"📊 Found {len(test_files)} large test files to analyze")
    print()

    recommendations = analyzer.generate_optimization_plan()

    if not recommendations:
        print("✅ No test file optimization needed!")
        return

    print("📋 Test File Optimization Recommendations")
    print("=" * 50)

    major_refactors = [r for r in recommendations if r["type"] == "major_refactor"]
    splits = [r for r in recommendations if r["type"] == "split"]

    print(f"\n🚨 Major Refactoring Needed ({len(major_refactors)} files):")
    for rec in major_refactors[:3]:  # Show top 3
        print(
            f"   • {Path(rec['file']).name}: {rec['line_count']} lines, {rec.get('function_count', 0)} tests"
        )

    print(f"\n📤 Minor Splits Recommended ({len(splits)} files):")
    for rec in splits[:3]:  # Show top 3
        print(f"   • {Path(rec['file']).name}: {rec['line_count']} lines")

    print("\n💡 Key Recommendations:")
    print("   1. Split test_agent_bus.py (2309 lines) into 4-5 focused modules")
    print("   2. Break down test_coverage_boost.py (1675 lines) by functionality")
    print("   3. Separate integration tests from unit tests")
    print("   4. Implement parallel test execution for faster CI/CD")
    print("   5. Add chaos engineering tests for resilience validation")


if __name__ == "__main__":
    main()
