#!/usr/bin/env python3
"""
ACGS-2 Test File Splitting Script
Automatically splits large test files into focused modules
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple


class TestFileSplitter:
    """Splits large test files into focused modules."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)

    def split_test_agent_bus(self):
        """Split the large test_agent_bus.py file into focused modules."""
        source_file = self.root_dir / "enhanced_agent_bus" / "tests" / "test_agent_bus.py"

        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            return

        # Read the entire file
        with open(source_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into sections based on comments
        sections = self._parse_test_sections(content)

        # Create mapping of functionality to test classes
        functional_groups = self._group_by_functionality(sections)

        # Create separate files for each functional group
        for group_name, classes in functional_groups.items():
            if len(classes) > 0:
                self._create_functional_test_file(source_file, group_name, classes)

        print(f"✅ Split {source_file.name} into {len(functional_groups)} focused modules")

    def _parse_test_sections(self, content: str) -> Dict[str, List[str]]:
        """Parse test sections from the file content."""
        sections = {}
        current_section = "general"
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for section markers (comments with =====)
            if line.startswith("#") and "=" * 10 in line:
                # Look for section name in the next few lines
                section_name = "unknown"
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith("#") and any(
                        keyword in next_line.lower()
                        for keyword in [
                            "lifecycle",
                            "registration",
                            "filtering",
                            "sending",
                            "receiving",
                            "isolation",
                            "broadcast",
                            "metrics",
                            "mode",
                            "components",
                            "singleton",
                            "helpers",
                            "initialization",
                            "hash",
                            "cases",
                            "factory",
                            "strict",
                            "queue",
                            "routing",
                        ]
                    ):
                        section_name = next_line.replace("#", "").strip().lower().replace(" ", "_")
                        break

                if section_name != "unknown":
                    current_section = section_name
                    sections[current_section] = []
                i += 1
                continue

            # Check for class definitions
            if line.startswith("class Test"):
                class_match = re.match(r"class\s+(Test\w+)", line)
                if class_match:
                    class_name = class_match.group(1)
                    if current_section not in sections:
                        sections[current_section] = []
                    sections[current_section].append(class_name)

            i += 1

        return sections

    def _group_by_functionality(self, sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Group test classes by functionality."""
        functional_groups = {
            "lifecycle": [],
            "agent_management": [],
            "messaging": [],
            "routing": [],
            "security": [],
            "monitoring": [],
            "edge_cases": [],
        }

        for section, classes in sections.items():
            if "lifecycle" in section:
                functional_groups["lifecycle"].extend(classes)
            elif any(word in section for word in ["registration", "filtering"]):
                functional_groups["agent_management"].extend(classes)
            elif any(word in section for word in ["sending", "receiving", "broadcast"]):
                functional_groups["messaging"].extend(classes)
            elif any(word in section for word in ["routing", "queue", "kafka"]):
                functional_groups["routing"].extend(classes)
            elif any(word in section for word in ["hash", "strict", "isolation"]):
                functional_groups["security"].extend(classes)
            elif "metrics" in section:
                functional_groups["monitoring"].extend(classes)
            else:
                functional_groups["edge_cases"].extend(classes)

        return functional_groups

    def _create_functional_test_file(self, source_file: Path, group_name: str, classes: List[str]):
        """Create a new test file for a functional group."""
        # Read the original file
        with open(source_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")

        # Extract imports and fixtures (everything before first class)
        header_content = []
        class_start_idx = 0

        for i, line in enumerate(lines):
            if line.strip().startswith("class Test"):
                class_start_idx = i
                break
            header_content.append(line)

        # For each class in this group, extract it from the original file
        class_blocks = []
        current_class_lines = []
        in_target_class = False
        current_class_name = None

        for line in lines[class_start_idx:]:
            if line.strip().startswith("class Test"):
                # Save previous class if it was a target
                if in_target_class and current_class_lines:
                    class_blocks.append("\n".join(current_class_lines))

                # Start new class
                class_match = re.match(r"class\s+(Test\w+)", line.strip())
                if class_match:
                    current_class_name = class_match.group(1)
                    in_target_class = current_class_name in classes

                current_class_lines = [line] if in_target_class else []
            elif in_target_class:
                current_class_lines.append(line)

        # Add the last class if it was a target
        if in_target_class and current_class_lines:
            class_blocks.append("\n".join(current_class_lines))

        # Create the new file
        target_file = source_file.parent / f"test_agent_bus_{group_name}.py"

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(f'''"""
ACGS-2 Enhanced Agent Bus Tests - {group_name.title().replace("_", " ")}
Focused tests for {group_name} functionality.
"""
''')

            # Write imports and fixtures
            f.write("\n".join(header_content))
            f.write("\n\n")

            # Write test classes
            for class_block in class_blocks:
                f.write(class_block)
                f.write("\n\n")

        print(f"  📄 Created {target_file.name} with {len(class_blocks)} test classes")


def main():
    """Main execution."""
    splitter = TestFileSplitter("acgs2-core")
    splitter.split_test_agent_bus()


if __name__ == "__main__":
    main()
