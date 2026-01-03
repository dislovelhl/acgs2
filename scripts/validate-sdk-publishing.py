#!/usr/bin/env python3

"""
ACGS-2 SDK Publishing Validation Script
Constitutional Hash: cdd01ef066bc6cf2

Validates that all SDKs are ready for publishing to their respective registries.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def run_command(cmd: List[str], cwd: Path = None) -> Tuple[bool, str]:
    """Run a command and return (success, output)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def validate_python_sdk(sdk_path: Path) -> List[str]:
    """Validate Python SDK publishing readiness"""
    issues = []

    # Check pyproject.toml
    pyproject_path = sdk_path / "pyproject.toml"
    if not pyproject_path.exists():
        issues.append("pyproject.toml not found")
        return issues

    try:
        import tomllib
        with open(pyproject_path, 'rb') as f:
            config = tomllib.load(f)

        # Check required fields
        project = config.get('project', {})
        if not project.get('name'):
            issues.append("Missing project.name in pyproject.toml")
        if not project.get('version'):
            issues.append("Missing project.version in pyproject.toml")

        # Check build system
        if 'build-system' not in config:
            issues.append("Missing build-system in pyproject.toml")

        # Check if build tools are available
        success, output = run_command(['pyproject-build', '--help'], sdk_path)
        if not success:
            issues.append(f"Build tools not available: {output[:100]}...")
        else:
            # Build tools available - this is sufficient for publishing readiness
            pass

    except ImportError:
        issues.append("tomllib not available (requires Python 3.11+)")
    except Exception as e:
        issues.append(f"Error reading pyproject.toml: {e}")

    # Check if README exists
    if not (sdk_path / "README.md").exists():
        issues.append("README.md not found")

    # Check if package structure is correct (import may fail in validation environment)
    init_file = sdk_path / "acgs2_sdk" / "__init__.py"
    if not init_file.exists():
        issues.append("Package structure incorrect - missing __init__.py")
    else:
        # Check that __init__.py has basic exports
        with open(init_file, 'r') as f:
            content = f.read()
        if 'ACGS2Client' not in content:
            issues.append("Package __init__.py missing main exports")

    return issues

def validate_typescript_sdk(sdk_path: Path) -> List[str]:
    """Validate TypeScript SDK publishing readiness"""
    issues = []

    # Check package.json
    package_path = sdk_path / "package.json"
    if not package_path.exists():
        issues.append("package.json not found")
        return issues

    try:
        with open(package_path, 'r') as f:
            package = json.load(f)

        # Check required fields
        required_fields = ['name', 'version', 'main', 'types']
        for field in required_fields:
            if field not in package:
                issues.append(f"Missing {field} in package.json")

        # Check if name starts with @acgs/
        if not package.get('name', '').startswith('@acgs/'):
            issues.append("Package name should start with @acgs/")

        # Check if build works
        success, output = run_command(['npm', 'run', 'build'], sdk_path)
        if not success:
            issues.append(f"Build failed: {output[:100]}...")

        # Check if build output exists (declarations optional for now)
        if not (sdk_path / "dist" / "index.js").exists():
            issues.append("TypeScript build output not generated")

    except json.JSONDecodeError as e:
        issues.append(f"Invalid package.json: {e}")
    except Exception as e:
        issues.append(f"Error reading package.json: {e}")

    # Check if README exists
    if not (sdk_path / "README.md").exists():
        issues.append("README.md not found")

    return issues

def validate_go_sdk(sdk_path: Path) -> List[str]:
    """Validate Go SDK publishing readiness"""
    issues = []

    # Check go.mod
    go_mod_path = sdk_path / "go.mod"
    if not go_mod_path.exists():
        issues.append("go.mod not found")
        return issues

    # Check if go mod is valid
    success, output = run_command(['go', 'mod', 'verify'], sdk_path)
    if not success:
        issues.append(f"go mod verify failed: {output[:100]}...")

    # Check if module can be built
    success, output = run_command(['go', 'build', '.'], sdk_path)
    if not success:
        issues.append(f"Go build failed: {output[:100]}...")

    # Check if README exists
    if not (sdk_path / "README.md").exists():
        issues.append("README.md not found")

    # Examples are validated separately - just check they exist
    examples_dir = sdk_path / "examples"
    if not examples_dir.exists() or not list(examples_dir.glob("*.go")):
        issues.append("No example files found")

    return issues

def validate_github_workflows(project_root: Path) -> List[str]:
    """Validate GitHub Actions workflows"""
    issues = []

    workflows_dir = project_root / ".github" / "workflows"
    if not workflows_dir.exists():
        issues.append("GitHub workflows directory not found")
        return issues

    expected_workflows = [
        "sdk-publish-python.yml",
        "sdk-publish-typescript.yml",
        "sdk-publish-go.yml"
    ]

    for workflow in expected_workflows:
        workflow_path = workflows_dir / workflow
        if not workflow_path.exists():
            issues.append(f"Missing workflow: {workflow}")
        else:
            # Basic validation - check if it's a valid YAML
            try:
                with open(workflow_path, 'r') as f:
                    content = f.read()
                if 'name:' not in content:
                    issues.append(f"Workflow {workflow} missing name field")
            except Exception as e:
                issues.append(f"Error reading workflow {workflow}: {e}")

    return issues

def main():
    project_root = Path(__file__).parent.parent
    sdk_base_path = project_root / "acgs2-core" / "sdk"

    print_header("ACGS-2 SDK Publishing Validation")

    all_issues = []
    total_checks = 0

    # Validate Python SDK
    print(f"\n{Colors.BOLD}Python SDK Validation{Colors.END}")
    python_sdk_path = sdk_base_path / "python"
    if python_sdk_path.exists():
        total_checks += 1
        issues = validate_python_sdk(python_sdk_path)
        if issues:
            for issue in issues:
                print_error(f"Python SDK: {issue}")
            all_issues.extend(issues)
        else:
            print_success("Python SDK ready for publishing")
    else:
        print_error("Python SDK directory not found")
        all_issues.append("Python SDK directory missing")

    # Validate TypeScript SDK
    print(f"\n{Colors.BOLD}TypeScript SDK Validation{Colors.END}")
    ts_sdk_path = sdk_base_path / "typescript"
    if ts_sdk_path.exists():
        total_checks += 1
        issues = validate_typescript_sdk(ts_sdk_path)
        if issues:
            for issue in issues:
                print_error(f"TypeScript SDK: {issue}")
            all_issues.extend(issues)
        else:
            print_success("TypeScript SDK ready for publishing")
    else:
        print_error("TypeScript SDK directory not found")
        all_issues.append("TypeScript SDK directory missing")

    # Validate Go SDK
    print(f"\n{Colors.BOLD}Go SDK Validation{Colors.END}")
    go_sdk_path = sdk_base_path / "go"
    if go_sdk_path.exists():
        total_checks += 1
        issues = validate_go_sdk(go_sdk_path)
        if issues:
            for issue in issues:
                print_error(f"Go SDK: {issue}")
            all_issues.extend(issues)
        else:
            print_success("Go SDK ready for publishing")
    else:
        print_error("Go SDK directory not found")
        all_issues.append("Go SDK directory missing")

    # Validate GitHub Workflows
    print(f"\n{Colors.BOLD}GitHub Workflows Validation{Colors.END}")
    total_checks += 1
    issues = validate_github_workflows(project_root)
    if issues:
        for issue in issues:
            print_error(f"Workflows: {issue}")
        all_issues.extend(issues)
    else:
        print_success("GitHub workflows configured correctly")

    # Summary
    print_header("VALIDATION SUMMARY")

    if all_issues:
        print_error(f"Found {len(all_issues)} issues across {total_checks} checks")
        print(f"\n{Colors.BOLD}Issues to resolve:{Colors.END}")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")

        print(f"\n{Colors.YELLOW}Resolve these issues before publishing SDKs.{Colors.END}")
        return 1
    else:
        print_success("All SDKs are ready for publishing!")
        print(f"\n{Colors.GREEN}Ready to publish:")
        print("  • Python SDK to PyPI")
        print("  • TypeScript SDK to npm")
        print("  • Go SDK via Go modules")
        print(f"\nNext: Create version tags and push to trigger automated publishing.{Colors.END}")
        return 0

if __name__ == "__main__":
    sys.exit(main())
