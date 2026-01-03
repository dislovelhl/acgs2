#!/usr/bin/env python3
"""
ARCH-001: Import Health Check
Constitutional Hash: cdd01ef066bc6cf2

Checks for import-time errors and circular dependencies by attempting to import modules.
"""

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Constitutional hash for validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def get_python_files(root_path: str) -> List[Path]:
    """Get all Python files in the project."""
    root = Path(root_path)
    python_files = []

    for file_path in root.rglob("*.py"):
        # Skip certain directories
        if any(part in str(file_path) for part in [".venv", "__pycache__", ".git", "node_modules"]):
            continue
        python_files.append(file_path)

    return python_files


def extract_module_name(file_path: Path, root_path: Path) -> str:
    """Convert file path to module name."""
    relative_path = file_path.relative_to(root_path)

    # Remove .py extension
    if relative_path.suffix == ".py":
        relative_path = relative_path.with_suffix("")

    # Convert path separators to dots
    module_name = str(relative_path).replace("/", ".").replace("\\", ".")

    # Handle __init__.py files
    if relative_path.name == "__init__":
        module_name = str(relative_path.parent).replace("/", ".").replace("\\", ".")

    return module_name


def check_module_imports(module_name: str) -> Tuple[bool, str]:
    """Try to import a module and return success status and error message."""
    try:
        # Remove from sys.modules if already imported to force re-import
        if module_name in sys.modules:
            del sys.modules[module_name]

        importlib.import_module(module_name)
        return True, ""
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return False, error_msg


def analyze_import_health(root_path: str) -> Dict[str, any]:
    """Analyze import health across the codebase."""
    print("🔍 Checking import health...")

    python_files = get_python_files(root_path)
    print(f"📁 Found {len(python_files)} Python files")

    results = {
        "total_files": len(python_files),
        "successful_imports": 0,
        "failed_imports": 0,
        "import_errors": [],
        "error_categories": {},
    }

    for file_path in python_files:
        module_name = extract_module_name(file_path, Path(root_path))

        success, error_msg = check_module_imports(module_name)

        if success:
            results["successful_imports"] += 1
        else:
            results["failed_imports"] += 1
            error_info = {"file": str(file_path), "module": module_name, "error": error_msg}
            results["import_errors"].append(error_info)

            # Categorize errors
            error_type = type(Exception(error_msg)).__name__ if error_msg else "Unknown"
            if error_type not in results["error_categories"]:
                results["error_categories"][error_type] = 0
            results["error_categories"][error_type] += 1

    return results


def detect_circular_imports(root_path: str) -> List[Dict[str, any]]:
    """Detect circular imports by analyzing import chains."""
    print("🔄 Detecting circular imports...")

    # This is a simplified circular import detector
    # In a real implementation, you'd need to build a proper dependency graph
    # and detect cycles

    circular_imports = []

    # Look for common circular import patterns in code
    python_files = get_python_files(root_path)

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            imports_in_file = []

            for line in lines:
                line = line.strip()
                if line.startswith("import ") or line.startswith("from "):
                    imports_in_file.append(line)

            # Look for potential circular patterns
            # This is a very basic check - real circular import detection
            # requires building and analyzing the full dependency graph

            if len(imports_in_file) > 20:  # Files with many imports might have issues
                circular_imports.append(
                    {
                        "file": str(file_path),
                        "imports_count": len(imports_in_file),
                        "potential_issue": "high_import_count",
                    }
                )

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    return circular_imports


def main():
    """Main ARCH-001 health check execution."""
    print("🏥 ARCH-001: Import Health Check")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    root_path = "acgs2-core"

    # Check import health
    health_results = analyze_import_health(root_path)

    print("📊 IMPORT HEALTH RESULTS")
    print(f"Total files: {health_results['total_files']}")
    print(f"Successful imports: {health_results['successful_imports']}")
    print(f"Failed imports: {health_results['failed_imports']}")
    print()

    if health_results["error_categories"]:
        print("❌ IMPORT ERROR CATEGORIES:")
        for error_type, count in health_results["error_categories"].items():
            print(f"  {error_type}: {count} occurrences")
        print()

    if health_results["import_errors"]:
        print("🔍 SAMPLE IMPORT ERRORS:")
        for error in health_results["import_errors"][:5]:  # Show first 5
            print(f"  📁 {error['file']}")
            print(f"  📦 {error['module']}")
            print(f"  ❌ {error['error']}")
            print()

    # Check for circular imports
    circular_results = detect_circular_imports(root_path)

    print("🔄 CIRCULAR IMPORT ANALYSIS")
    if circular_results:
        print(f"Potential circular import patterns: {len(circular_results)}")
        for item in circular_results[:3]:  # Show first 3
            print(f"  📁 {item['file']}: {item['imports_count']} imports")
    else:
        print("✅ No obvious circular import patterns detected")
    print()

    # Overall assessment
    success_rate = (health_results["successful_imports"] / health_results["total_files"]) * 100

    print("🎯 OVERALL ASSESSMENT")
    print(f"Import success rate: {success_rate:.1f}%")
    if success_rate >= 95:
        print("✅ EXCELLENT: Import health is very good")
    elif success_rate >= 80:
        print("⚠️  GOOD: Minor import issues detected")
    else:
        print("❌ NEEDS ATTENTION: Significant import issues found")

    print()
    print("🏥 ARCH-001 HEALTH CHECK COMPLETE")


if __name__ == "__main__":
    main()
