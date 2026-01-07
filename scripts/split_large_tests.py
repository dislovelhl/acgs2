#!/usr/bin/env python3
"""
Generic script to split large test files into smaller, focused test modules.
"""

import re
from pathlib import Path


def split_large_test_file(source_file: Path, target_dir: Path):
    """Split a large test file into smaller modules by test class."""

    if not source_file.exists():
        print(f"Source file {source_file} does not exist")
        return

    target_dir.mkdir(exist_ok=True)

    with open(source_file, "r") as f:
        content = f.read()

    # Find the end of the header (imports and fixtures) before the first class
    header_end_pattern = r"(.*?)(\n\nclass Test)"
    header_match = re.match(header_end_pattern, content, re.DOTALL)

    if not header_match:
        print(f"Could not find header end pattern in {source_file}")
        return

    header_content = header_match.group(1)

    # Find all test classes
    class_pattern = r"(class\s+Test\w+.*?)(?=\n\nclass Test|\n# =+|\Z)"
    classes = re.findall(class_pattern, content, re.DOTALL)

    if not classes:
        print(f"No test classes found in {source_file}")
        return

    print(f"Found {len(classes)} test classes in {source_file}")

    # Create a mapping for class names to file names
    class_mapping = {}
    for class_content in classes:
        class_match = re.match(r"class\s+(Test\w+)", class_content)
        if class_match:
            class_name = class_match.group(1)
            filename = f"{class_name.lower()}.py"
            class_mapping[class_name] = filename

    # Extract each class
    for class_name, filename in class_mapping.items():
        # Find the class content
        class_pattern = rf"(class\s+{class_name}.*?)(?=\n\nclass Test|\n# =+|\Z)"
        class_match = re.search(class_pattern, content, re.DOTALL)

        if class_match:
            class_content = class_match.group(1)

            # Create the file content - header_content already includes imports and docstrings
            file_content = f"""{header_content.strip()}

{class_content.strip()}
"""

            target_file = target_dir / filename
            with open(target_file, "w") as f:
                f.write(file_content)

            print(f"Created {target_file}")

    print(f"Test file splitting completed for {source_file}!")


def main():
    """Split the identified large test files."""

    large_files = [
        (
            Path(
                "src/adaptive-learning/adaptive-learning-engine/tests/unit/monitoring/test_drift_detector.py"
            ),
            Path(
                "src/adaptive-learning/adaptive-learning-engine/tests/unit/monitoring/drift_detector"
            ),
        ),
        (
            Path("src/core/enhanced_agent_bus/tests/test_constitutional_saga_comprehensive.py"),
            Path("src/core/enhanced_agent_bus/tests/constitutional_saga"),
        ),
        (
            Path("src/core/enhanced_agent_bus/tests/test_hitl_manager.py"),
            Path("src/core/enhanced_agent_bus/tests/hitl_manager"),
        ),
    ]

    for source_file, target_dir in large_files:
        print(f"\nProcessing {source_file}...")
        split_large_test_file(source_file, target_dir)


if __name__ == "__main__":
    main()
