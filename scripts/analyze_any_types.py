#!/usr/bin/env python3
"""
Comprehensive analysis script for 'Any' type usage in Python codebase.
Categorizes occurrences by usage pattern and generates detailed reports.
"""

import csv
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AnyOccurrence:
    """Represents a single occurrence of 'Any' type."""

    file_path: str
    line_number: int
    line_content: str
    category: str
    context: str
    function_name: Optional[str]
    class_name: Optional[str]
    priority: str
    ease_of_replacement: str
    impact: str
    notes: str


class AnyTypeAnalyzer:
    """Analyzes 'Any' type usage across the codebase."""

    CATEGORIES = {
        "function_param": "Function Parameter",
        "function_return": "Function Return Type",
        "pydantic_validator": "Pydantic Validator",
        "wrapper_function": "Wrapper/Decorator Function",
        "model_field": "Data Model Field",
        "context_manager": "Context Manager",
        "cache_value": "Cache Value",
        "serialization": "Serialization/Deserialization",
        "logging": "Logging Parameter",
        "test_utility": "Test Utility",
        "protocol_interface": "Protocol/Interface",
        "external_library": "External Library Integration",
        "configuration": "Configuration Value",
        "other": "Other/Uncategorized",
    }

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.occurrences: List[AnyOccurrence] = []
        self.stats = defaultdict(int)

    def find_all_occurrences(self) -> List[AnyOccurrence]:
        """Find all 'Any' type occurrences using grep."""
        try:
            # Use grep to find all occurrences
            result = subprocess.run(
                ["grep", "-rn", "--include=*.py", ": Any", "."],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )

            lines = result.stdout.strip().split("\n")

            for line in lines:
                if not line:
                    continue

                # Parse grep output: filename:line_number:content
                parts = line.split(":", 2)
                if len(parts) < 3:
                    continue

                file_path = parts[0].lstrip("./")
                try:
                    line_number = int(parts[1])
                except ValueError:
                    continue

                line_content = parts[2].strip()

                occurrence = self._analyze_occurrence(file_path, line_number, line_content)
                if occurrence:
                    self.occurrences.append(occurrence)

        except Exception as e:
            print(f"Error finding occurrences: {e}")

        return self.occurrences

    def _analyze_occurrence(
        self, file_path: str, line_number: int, line_content: str
    ) -> Optional[AnyOccurrence]:
        """Analyze a single occurrence and categorize it."""

        # Determine category based on context
        category = self._categorize_occurrence(file_path, line_content)

        # Extract function and class context
        function_name, class_name = self._extract_context(file_path, line_number)

        # Determine priority, ease of replacement, and impact
        priority = self._calculate_priority(file_path, category, line_content)
        ease = self._calculate_ease_of_replacement(category, line_content)
        impact = self._calculate_impact(file_path, category)

        # Generate notes
        notes = self._generate_notes(category, line_content, file_path)

        # Create context description
        context = self._create_context_description(line_content, function_name, class_name)

        return AnyOccurrence(
            file_path=file_path,
            line_number=line_number,
            line_content=line_content,
            category=category,
            context=context,
            function_name=function_name,
            class_name=class_name,
            priority=priority,
            ease_of_replacement=ease,
            impact=impact,
            notes=notes,
        )

    def _categorize_occurrence(self, file_path: str, line_content: str) -> str:
        """Categorize the Any occurrence based on context."""

        # Pydantic validators
        if (
            "def validate_" in line_content
            or "@validator" in line_content
            or "@field_validator" in line_content
        ):
            return "pydantic_validator"

        # Model post init (Pydantic specific)
        if "model_post_init" in line_content:
            return "pydantic_validator"

        # Wrapper functions and decorators
        if "*args: Any" in line_content or "**kwargs: Any" in line_content:
            return "wrapper_function"

        # Context managers
        if (
            "__context: Any" in line_content
            or "__exit__" in line_content
            or "__aexit__" in line_content
        ):
            return "context_manager"

        # Cache related
        if "cache" in file_path.lower() or "cache" in line_content.lower():
            if "value: Any" in line_content or "get(" in line_content or "set(" in line_content:
                return "cache_value"

        # Serialization
        if any(
            term in line_content.lower()
            for term in ["serialize", "deserialize", "dump", "json", "orjson"]
        ):
            return "serialization"

        # Logging
        if "log" in file_path.lower() or any(
            term in line_content for term in ["logger", "logging", "exc_info"]
        ):
            return "logging"

        # Test files
        if "/test" in file_path or file_path.startswith("test_"):
            return "test_utility"

        # Configuration
        if "config" in file_path.lower() or "settings" in file_path.lower():
            return "configuration"

        # External library integration
        if any(lib in file_path for lib in ["nemo", "temporal", "kafka", "mlflow", "vault"]):
            return "external_library"

        # Model fields (Pydantic)
        if ": Any" in line_content and "=" in line_content and "Field(" in line_content:
            return "model_field"

        # Function return type
        if "-> Any" in line_content:
            return "function_return"

        # Function parameter (default if : Any appears)
        if ": Any" in line_content and "def " in line_content:
            return "function_param"

        return "other"

    def _extract_context(self, file_path: str, line_number: int) -> tuple:
        """Extract function and class context from the file."""
        function_name = None
        class_name = None

        try:
            full_path = self.root_dir / file_path
            if not full_path.exists():
                return None, None

            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Look backwards from the line to find function/class definitions
            for i in range(line_number - 1, max(0, line_number - 50), -1):
                if i >= len(lines):
                    continue

                line = lines[i].strip()

                # Find function
                if function_name is None and line.startswith("def "):
                    match = re.match(r"def\s+(\w+)\s*\(", line)
                    if match:
                        function_name = match.group(1)

                # Find class
                if class_name is None and line.startswith("class "):
                    match = re.match(r"class\s+(\w+)", line)
                    if match:
                        class_name = match.group(1)

                if function_name and class_name:
                    break

        except Exception:
            pass

        return function_name, class_name

    def _calculate_priority(self, file_path: str, category: str, line_content: str) -> str:
        """Calculate priority: High, Medium, Low."""

        # High priority: Core business logic, public APIs, model fields
        if category in ["model_field", "function_return"]:
            return "High"

        # High priority: Core services
        if any(
            p in file_path
            for p in [
                "integration-service/src/integrations/",
                "src/core/breakthrough/",
                "src/core/enhanced_agent_bus/",
                "src/core/sdk/",
            ]
        ):
            if category not in ["wrapper_function", "logging", "test_utility"]:
                return "High"

        # Low priority: Tests, logging, wrappers
        if category in ["test_utility", "logging", "wrapper_function", "context_manager"]:
            return "Low"

        # Medium priority: Everything else
        return "Medium"

    def _calculate_ease_of_replacement(self, category: str, line_content: str) -> str:
        """Calculate ease of replacement: Easy, Medium, Hard."""

        # Easy: Clear patterns with obvious replacements
        if category in ["pydantic_validator", "serialization", "logging"]:
            return "Easy"

        # Hard: Wrappers, complex generic functions
        if category in ["wrapper_function", "context_manager"]:
            return "Hard"

        # Hard: External library integrations
        if category == "external_library":
            return "Hard"

        # Medium: Most other cases
        return "Medium"

    def _calculate_impact(self, file_path: str, category: str) -> str:
        """Calculate impact of fixing: High, Medium, Low."""

        # High impact: Public APIs, SDKs, core services
        if category in ["model_field", "function_return", "protocol_interface"]:
            return "High"

        if "sdk" in file_path or "api" in file_path:
            return "High"

        # Low impact: Tests, internal utilities, logging
        if category in ["test_utility", "logging", "wrapper_function"]:
            return "Low"

        return "Medium"

    def _generate_notes(self, category: str, line_content: str, file_path: str) -> str:
        """Generate helpful notes for fixing this occurrence."""

        notes = []

        if category == "pydantic_validator":
            notes.append(
                "Pydantic validators can use specific types based on field being validated"
            )

        if category == "model_field":
            notes.append("Consider Union of specific types or TypedDict")

        if category == "cache_value":
            notes.append("Use Generic[T] or Union of cacheable types")

        if category == "wrapper_function":
            notes.append("Consider using TypeVar with ParamSpec for proper typing")

        if category == "serialization":
            notes.append("JSON serialization can use JSONSerializable type alias")

        if category == "external_library":
            notes.append("May require stub files or Protocol definitions")

        if "context" in line_content.lower():
            notes.append("Context data can often use TypedDict")

        return "; ".join(notes) if notes else "Review context to determine appropriate type"

    def _create_context_description(
        self, line_content: str, function_name: Optional[str], class_name: Optional[str]
    ) -> str:
        """Create a human-readable context description."""

        parts = []

        if class_name:
            parts.append(f"Class: {class_name}")

        if function_name:
            parts.append(f"Function: {function_name}")

        # Extract parameter name if possible
        param_match = re.search(r"(\w+):\s*Any", line_content)
        if param_match:
            parts.append(f"Parameter: {param_match.group(1)}")

        return " | ".join(parts) if parts else "N/A"

    def generate_statistics(self) -> Dict:
        """Generate statistics about Any usage."""

        stats = {
            "total_occurrences": len(self.occurrences),
            "by_category": defaultdict(int),
            "by_priority": defaultdict(int),
            "by_directory": defaultdict(int),
            "by_ease": defaultdict(int),
            "by_impact": defaultdict(int),
            "unique_files": len(set(o.file_path for o in self.occurrences)),
            "top_files": [],
        }

        file_counts = defaultdict(int)

        for occ in self.occurrences:
            stats["by_category"][occ.category] += 1
            stats["by_priority"][occ.priority] += 1
            stats["by_ease"][occ.ease_of_replacement] += 1
            stats["by_impact"][occ.impact] += 1

            # Get top-level directory
            dir_parts = occ.file_path.split("/")
            top_dir = dir_parts[0] if dir_parts else "root"
            stats["by_directory"][top_dir] += 1

            file_counts[occ.file_path] += 1

        # Get top 20 files by occurrence count
        stats["top_files"] = sorted(
            [{"file": f, "count": c} for f, c in file_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:20]

        return stats

    def export_to_csv(self, output_path: str):
        """Export occurrences to CSV file."""

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "file_path",
                    "line_number",
                    "category",
                    "priority",
                    "ease_of_replacement",
                    "impact",
                    "context",
                    "function_name",
                    "class_name",
                    "line_content",
                    "notes",
                ],
            )

            writer.writeheader()

            for occ in sorted(
                self.occurrences, key=lambda x: (x.priority, x.file_path, x.line_number)
            ):
                writer.writerow(
                    {
                        "file_path": occ.file_path,
                        "line_number": occ.line_number,
                        "category": self.CATEGORIES.get(occ.category, occ.category),
                        "priority": occ.priority,
                        "ease_of_replacement": occ.ease_of_replacement,
                        "impact": occ.impact,
                        "context": occ.context,
                        "function_name": occ.function_name or "",
                        "class_name": occ.class_name or "",
                        "line_content": occ.line_content,
                        "notes": occ.notes,
                    }
                )

    def export_to_json(self, output_path: str):
        """Export occurrences and statistics to JSON file."""

        data = {
            "metadata": {
                "total_occurrences": len(self.occurrences),
                "unique_files": len(set(o.file_path for o in self.occurrences)),
                "analysis_date": subprocess.run(
                    ["date", "-Iseconds"], capture_output=True, text=True
                ).stdout.strip(),
            },
            "statistics": self.generate_statistics(),
            "occurrences": [
                {
                    "file_path": occ.file_path,
                    "line_number": occ.line_number,
                    "category": occ.category,
                    "category_name": self.CATEGORIES.get(occ.category, occ.category),
                    "priority": occ.priority,
                    "ease_of_replacement": occ.ease_of_replacement,
                    "impact": occ.impact,
                    "context": occ.context,
                    "function_name": occ.function_name,
                    "class_name": occ.class_name,
                    "line_content": occ.line_content,
                    "notes": occ.notes,
                }
                for occ in sorted(
                    self.occurrences, key=lambda x: (x.priority, x.file_path, x.line_number)
                )
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def print_summary(self):
        """Print a summary of findings to console."""

        stats = self.generate_statistics()

        print("\n" + "=" * 80)
        print("ANY TYPE USAGE ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"\nTotal 'Any' occurrences found: {stats['total_occurrences']}")
        print(f"Across {stats['unique_files']} unique files")

        print("\n--- By Category ---")
        for category, count in sorted(
            stats["by_category"].items(), key=lambda x: x[1], reverse=True
        ):
            category_name = self.CATEGORIES.get(category, category)
            print(f"  {category_name:40s}: {count:4d}")

        print("\n--- By Priority ---")
        for priority in ["High", "Medium", "Low"]:
            count = stats["by_priority"][priority]
            print(f"  {priority:10s}: {count:4d}")

        print("\n--- By Directory ---")
        for directory, count in sorted(
            stats["by_directory"].items(), key=lambda x: x[1], reverse=True
        )[:15]:
            print(f"  {directory:50s}: {count:4d}")

        print("\n--- Top 10 Files ---")
        for item in stats["top_files"][:10]:
            print(f"  {item['file']:70s}: {item['count']:4d}")

        print("\n--- By Ease of Replacement ---")
        for ease in ["Easy", "Medium", "Hard"]:
            count = stats["by_ease"][ease]
            print(f"  {ease:10s}: {count:4d}")

        print("\n--- By Impact ---")
        for impact in ["High", "Medium", "Low"]:
            count = stats["by_impact"][impact]
            print(f"  {impact:10s}: {count:4d}")

        print("\n" + "=" * 80)


def main():
    """Main entry point."""

    analyzer = AnyTypeAnalyzer()

    print("Analyzing 'Any' type usage in codebase...")
    occurrences = analyzer.find_all_occurrences()

    if not occurrences:
        print("No 'Any' type occurrences found!")
        return

    # Print summary to console
    analyzer.print_summary()

    # Create output directory
    output_dir = Path(".auto-claude/specs/056-reduce-excessive-any-type-usage-in-python-codebase")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export reports
    csv_path = output_dir / "any_type_analysis.csv"
    json_path = output_dir / "any_type_analysis.json"

    print(f"\nExporting CSV report to: {csv_path}")
    analyzer.export_to_csv(str(csv_path))

    print(f"Exporting JSON report to: {json_path}")
    analyzer.export_to_json(str(json_path))

    print("\nAnalysis complete!")
    print(f"  - CSV report: {csv_path}")
    print(f"  - JSON report: {json_path}")


if __name__ == "__main__":
    main()
