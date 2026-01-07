#!/usr/bin/env python3
"""
Script to update import statements after directory reorganization.

This script updates Python import statements to reflect the new directory structure:
- acgs2-core/ -> src/core/
- acgs2-frontend/ -> src/frontend/
- etc.
"""

import os
import re


def update_imports_in_file(filepath):
    """Update import statements in a single Python file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Define import pattern replacements
    replacements = [
        # Core components moved to src/core/
        (r"from src.core.enhanced_agent_bus", "from src.core.enhanced_agent_bus"),
        (r"import src.core.enhanced_agent_bus", "import src.core.enhanced_agent_bus"),
        (r"from services\.", "from src.core.services."),
        (r"import services\.", "import src.core.services."),
        (r"from shared\.", "from src.core.shared."),
        (r"import shared\.", "import src.core.shared."),
        (r"from breakthrough\.", "from src.core.breakthrough."),
        (r"import breakthrough\.", "import src.core.breakthrough."),
        # Sub-projects moved to src/
        (r"from src.integration_service", "from src.integration_service"),
        (r"import src.integration_service", "import src.integration_service"),
        (r"from src.adaptive_learning", "from src.adaptive_learning"),
        (r"import src.adaptive_learning", "import src.adaptive_learning"),
        (r"from src.claude_flow", "from src.claude_flow"),
        (r"import src.claude_flow", "import src.claude_flow"),
        # Frontend moved to src/frontend/
        (r"from src.frontend.analytics_dashboard", "from src.frontend.analytics_dashboard"),
        (r"import src.frontend.analytics_dashboard", "import src.frontend.analytics_dashboard"),
        # Infra components moved to src/infra/
        (r"from src.infra", "from src.infra"),
        (r"import src.infra", "import src.infra"),
        # Observability moved to src/observability/
        (r"from src.observability", "from src.observability"),
        (r"import src.observability", "import src.observability"),
        # Research moved to src/research/
        (r"from src.research", "from src.research"),
        (r"import src.research", "import src.research"),
        # Neural MCP moved to src/neural-mcp/
        (r"from src.neural_mcp", "from src.neural_mcp"),
        (r"import src.neural_mcp", "import src.neural_mcp"),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    # Write back only if content changed
    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def find_python_files():
    """Find all Python files that need import updates."""
    # Skip certain directories that shouldn't be modified
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

    python_files = []

    for root, dirs, files in os.walk("."):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                python_files.append(filepath)

    return python_files


def main():
    """Main function to update all import statements."""
    print("Finding Python files...")
    python_files = find_python_files()
    print(f"Found {len(python_files)} Python files to check")

    updated_count = 0
    for filepath in python_files:
        if update_imports_in_file(filepath):
            print(f"Updated: {filepath}")
            updated_count += 1

    print(f"\nSummary: Updated {updated_count} out of {len(python_files)} Python files")


if __name__ == "__main__":
    main()
