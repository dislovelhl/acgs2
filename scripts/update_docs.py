#!/usr/bin/env python3
"""
Script to update documentation path references after directory reorganization.
"""

import os
import re


def update_file_paths(filepath):
    """Update path references in a documentation file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Define path replacement patterns
    replacements = [
        # Directory moves
        (r"\./src/core/", r"./src/core/"),
        (r"\./acgs2-infra/", r"./src/infra/"),
        (r"\./acgs2-observability/", r"./src/observability/"),
        (r"\./acgs2-research/", r"./src/research/"),
        (r"\./acgs2-neural-mcp/", r"./src/neural-mcp/"),
        (r"\./acgs2-frontend/", r"./src/frontend/"),
        # Sub-project moves
        (r"\./integration-service/", r"./src/integration-service/"),
        (r"\./adaptive-learning-engine/", r"./src/adaptive-learning/"),
        (r"\./analytics-dashboard/", r"./src/frontend/analytics-dashboard/"),
        (r"\./claude-flow/", r"./src/claude-flow/"),
        (r"\./compliance-docs-service/", r"./archive/compliance-docs-service/"),
        # File moves
        (r"\./architecture/", r"./docs/architecture/"),
        (r"\./clausedocs/", r"./docs/research/"),
        (r"\./scripts/", r"./scripts/"),  # scripts stayed at root
        # Reports moves
        (r"\./BUILD_VERIFICATION\.md", r"./reports/BUILD_VERIFICATION.md"),
        (r"\./E2E_TEST_RESULTS\.md", r"./reports/E2E_TEST_RESULTS.md"),
        (
            r"\./FINAL_ROADMAP_COMPLIANCE_REPORT\.json",
            r"./reports/FINAL_ROADMAP_COMPLIANCE_REPORT.json",
        ),
        (r"\./FULL_TEST_SUITE_REPORT\.json", r"./reports/FULL_TEST_SUITE_REPORT.json"),
        (r"\./REMEDIATION_AUDIT_REPORT\.json", r"./reports/REMEDIATION_AUDIT_REPORT.json"),
        (r"\./TEST_COVERAGE_SPRINT_REPORT\.json", r"./reports/TEST_COVERAGE_SPRINT_REPORT.json"),
        (r"\./performance_benchmark_report\.json", r"./reports/performance_benchmark_report.json"),
        # Documentation moves
        (r"\./CONTRIBUTING\.md", r"./CONTRIBUTING.md"),  # stayed at root
        (r"\./DIRECTORY_STRUCTURE\.md", r"./docs/DIRECTORY_STRUCTURE.md"),
        (r"\./OPERATIONS_GUIDE\.md", r"./docs/OPERATIONS_GUIDE.md"),
        (r"\./ROADMAP_2025\.md", r"./docs/ROADMAP_2025.md"),
        (r"\./ROADMAP_IMPLEMENTATION_SUMMARY\.md", r"./docs/ROADMAP_IMPLEMENTATION_SUMMARY.md"),
        (r"\./SDK_PUBLISHING_GUIDE\.md", r"./docs/SDK_PUBLISHING_GUIDE.md"),
        (r"\./coordination\.md", r"./docs/coordination.md"),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    # Write back only if content changed
    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def find_markdown_files():
    """Find all markdown files that need path updates."""
    markdown_files = []

    # Find all .md files, excluding certain directories
    exclude_dirs = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "htmlcov",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
    }

    for root, dirs, files in os.walk("."):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                markdown_files.append(filepath)

    return markdown_files


def main():
    """Main function to update all documentation path references."""
    print("Finding markdown files...")
    markdown_files = find_markdown_files()
    print(f"Found {len(markdown_files)} markdown files to check")

    updated_count = 0
    for filepath in markdown_files:
        if update_file_paths(filepath):
            print(f"Updated: {filepath}")
            updated_count += 1

    print(f"\nSummary: Updated {updated_count} out of {len(markdown_files)} markdown files")


if __name__ == "__main__":
    main()
