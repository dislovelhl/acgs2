#!/usr/bin/env python3
"""
ACGS-2 Custom Secrets Detection Pre-commit Hook
Constitutional Hash: cdd01ef066bc6cf2

Pre-commit hook to detect ACGS-2-specific secrets using patterns from secrets_manager.py.
Complements gitleaks with project-specific credential validation.

Configuration:
    - Patterns: src/core/shared/secrets_manager.py (CREDENTIAL_PATTERNS)
    - Allow-list: .secrets-allowlist.yaml (placeholder patterns, safe values)

Usage:
    # Automatically via pre-commit framework
    # Or manually:
    python scripts/check-secrets-pre-commit.py [--verbose]
"""

import argparse
import os
import re
import subprocess  # nosec B404 - Required for git operations
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:
    print("❌ ERROR: PyYAML not installed. Run: pip install pyyaml")  # noqa: T201
    sys.exit(1)

# Add project root to path (scripts/security/ -> scripts/ -> project_root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"
ALLOWLIST_CONFIG_PATH = project_root / ".secrets-allowlist.yaml"

# Fallback patterns when secrets_manager.py import fails (for pre-commit isolated env)
FALLBACK_CREDENTIAL_PATTERNS = {
    "JWT_SECRET": r".{32,}",
    "DATABASE_URL": r"postgres(ql)?://[^:]+:[^@]+@.+",
    "REDIS_URL": r"redis://[^:]*:[^@]+@.+",
    "API_KEY": r"[a-zA-Z0-9_-]{20,}",
    "SECRET_KEY": r".{16,}",
    "PRIVATE_KEY": r"-----BEGIN.*PRIVATE KEY-----",
    "AWS_ACCESS_KEY_ID": r"AKIA[0-9A-Z]{16}",
    "AWS_SECRET_ACCESS_KEY": r"[A-Za-z0-9/+=]{40}",
    "OPENAI_API_KEY": r"sk-[a-zA-Z0-9]{48}",
    "ANTHROPIC_API_KEY": r"sk-ant-[a-zA-Z0-9-]{80,}",
}

FALLBACK_SECRET_CATEGORIES = {
    "authentication": ["JWT_SECRET", "SECRET_KEY", "API_KEY"],
    "database": ["DATABASE_URL", "REDIS_URL"],
    "cloud": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
    "ai_services": ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
    "certificates": ["PRIVATE_KEY"],
}

# Import patterns from secrets_manager.py (single source of truth)
# Falls back to inline patterns for pre-commit isolated environment
try:
    from src.core.shared.secrets_manager import CREDENTIAL_PATTERNS, SECRET_CATEGORIES
except ImportError:
    # Use fallback patterns - this is expected in pre-commit isolated environment
    CREDENTIAL_PATTERNS = FALLBACK_CREDENTIAL_PATTERNS
    SECRET_CATEGORIES = FALLBACK_SECRET_CATEGORIES


def load_allowlist_config(config_path: Path) -> Dict:
    """
    Load allow-list configuration from YAML file.

    Args:
        config_path: Path to .secrets-allowlist.yaml

    Returns:
        Dictionary with configuration, or default config if file not found
    """
    if not config_path.exists():
        print(f"⚠️  WARNING: Allow-list config not found: {config_path}")  # noqa: T201
        print("   Using default hardcoded allow-list")  # noqa: T201
        return get_default_config()

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"❌ ERROR: Failed to load allow-list config: {e}")  # noqa: T201
        print("   Using default hardcoded allow-list")  # noqa: T201
        return get_default_config()


def get_default_config() -> Dict:
    """
    Get default allow-list configuration as fallback.

    Returns:
        Dictionary with default configuration
    """
    return {
        "placeholder_patterns": {
            "prefixes": ["dev-", "test-", "your-", "placeholder-", "example-", "sample-"],
            "markers": ["<", ">", "xxx", "***", "[redacted]", "<hidden>", "example", "template"],
            "redaction_patterns": [r"^[X*\-._]+$"],
        },
        "excluded_paths": {
            "directories": [
                "node_modules/",
                ".venv/",
                "venv/",
                "__pycache__/",
                "dist/",
                "build/",
                ".git/",
                ".pytest_cache/",
                ".mypy_cache/",
            ],
            "test_paths": ["tests/fixtures/", "__fixtures__/"],
            "file_patterns": [".env.example", ".env.template", ".example.", ".template."],
        },
        "known_safe_values": {
            "development": [
                {"value": "dev-jwt-secret-min-32-chars-required"},
                {"value": "dev_password"},
                {"value": "mlflow_password"},
            ],
            "generic": [
                {"value": "password"},
                {"value": "acgs2_pass"},
                {"value": "changeme"},
                {"value": "secret"},
                {"value": "test-secret"},
            ],
            "empty_values": ["", "null", "None", "nil", "undefined"],
        },
        "skip_extensions": [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".ico",
            ".svg",
            ".mp4",
            ".webm",
            ".pyc",
            ".pyo",
            ".so",
            ".dylib",
            ".dll",
            ".exe",
            ".bin",
        ],
    }


# Load configuration from file
ALLOWLIST_CONFIG = load_allowlist_config(ALLOWLIST_CONFIG_PATH)

# Extract configuration into module-level variables for backward compatibility
SKIP_EXTENSIONS = set(ALLOWLIST_CONFIG.get("skip_extensions", []))

EXCLUDE_PATHS = set(
    ALLOWLIST_CONFIG.get("excluded_paths", {}).get("directories", [])
    + ALLOWLIST_CONFIG.get("excluded_paths", {}).get("test_paths", [])
)

EXCLUDE_FILE_PATTERNS = set(ALLOWLIST_CONFIG.get("excluded_paths", {}).get("file_patterns", []))

PLACEHOLDER_PREFIXES = set(ALLOWLIST_CONFIG.get("placeholder_patterns", {}).get("prefixes", []))

PLACEHOLDER_MARKERS = set(ALLOWLIST_CONFIG.get("placeholder_patterns", {}).get("markers", []))

REDACTION_PATTERNS = [
    re.compile(pattern)
    for pattern in ALLOWLIST_CONFIG.get("placeholder_patterns", {}).get("redaction_patterns", [])
]

# Build known safe values set from configuration
KNOWN_SAFE_VALUES = set()
for category in ["development", "generic", "empty_values", "test_fixtures"]:
    values = ALLOWLIST_CONFIG.get("known_safe_values", {}).get(category, [])
    for item in values:
        if isinstance(item, dict):
            KNOWN_SAFE_VALUES.add(item.get("value", ""))
        else:
            KNOWN_SAFE_VALUES.add(item)


def get_secret_category(secret_name: str) -> str:
    """
    Get category for a secret name.

    Args:
        secret_name: Secret name

    Returns:
        Category name or 'unknown'
    """
    for category, secrets in SECRET_CATEGORIES.items():
        if secret_name in secrets:
            return category
    return "unknown"


def is_placeholder(value: str, file_path: str) -> bool:
    """
    Check if a value is a safe placeholder rather than a real secret.

    Args:
        value: The value to check
        file_path: Path to file containing the value

    Returns:
        True if value is a safe placeholder
    """
    if not value or not value.strip():
        return True

    value_lower = value.lower()

    # Category 1: Prefix-based placeholders
    if any(value_lower.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
        return True

    # Category 2: Instructional markers
    if any(marker in value_lower for marker in PLACEHOLDER_MARKERS):
        return True

    # Category 3: Known safe values
    if value in KNOWN_SAFE_VALUES:
        return True

    # Category 4: File-specific exceptions
    # .env.example and .env.dev are already excluded by path, but check anyway
    if any(pattern in file_path for pattern in [".env.example", ".env.dev", ".env.template"]):
        return True

    # Category 5: Redacted examples (XXX, ***, etc.)
    for pattern in REDACTION_PATTERNS:
        if pattern.match(value):
            return True

    return False


def should_scan_file(file_path: str) -> bool:
    """
    Determine if a file should be scanned.

    Args:
        file_path: Path to file

    Returns:
        True if file should be scanned
    """
    # Skip if extension is in skip list
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return False

    # Skip if path contains excluded directory
    for exclude_path in EXCLUDE_PATHS:
        if exclude_path in file_path:
            return False

    # Skip if filename matches exclude pattern
    for pattern in EXCLUDE_FILE_PATTERNS:
        if pattern in os.path.basename(file_path):
            return False

    return True


def get_staged_files() -> List[str]:
    """
    Get list of staged files from git.

    Returns:
        List of file paths
    """
    try:
        result = subprocess.run(  # nosec B603, B607 - Safe git command
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return [f for f in files if should_scan_file(f)]
    except subprocess.CalledProcessError as e:
        print(f"⚠️  WARNING: Failed to get staged files: {e}")  # noqa: T201
        return []


def scan_file_for_secrets(file_path: str, verbose: bool = False) -> List[Tuple[str, str, int, str]]:
    """
    Scan a file for secrets matching CREDENTIAL_PATTERNS.

    Args:
        file_path: Path to file to scan
        verbose: Whether to print verbose output

    Returns:
        List of tuples: (secret_name, secret_value, line_number, line_content)
    """
    findings = []

    if not os.path.exists(file_path):
        return findings

    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        if verbose:
            print(f"⚠️  WARNING: Could not read {file_path}: {e}")  # noqa: T201
        return findings

    # Compile patterns once for efficiency
    compiled_patterns = {name: re.compile(pattern) for name, pattern in CREDENTIAL_PATTERNS.items()}

    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()

        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith("#"):
            continue

        # Check each credential pattern
        for secret_name, pattern in compiled_patterns.items():
            # Look for potential values in the line
            # Common formats: KEY=value, "key": "value", key: value
            value_matches = []

            # Environment variable format: KEY=value
            env_match = re.search(
                rf'{secret_name}\s*=\s*["\']?([^"\'\s]+)["\']?', line, re.IGNORECASE
            )
            if env_match:
                value_matches.append(env_match.group(1))

            # JSON/YAML format: "key": "value" or key: value
            json_match = re.search(
                rf'["\']?{secret_name}["\']?\s*:\s*["\']([^"\']+)["\']', line, re.IGNORECASE
            )
            if json_match:
                value_matches.append(json_match.group(1))

            # Python assignment: KEY = "value"
            py_match = re.search(rf'{secret_name}\s*=\s*["\']([^"\']+)["\']', line, re.IGNORECASE)
            if py_match:
                value_matches.append(py_match.group(1))

            # Check if any extracted value matches the pattern
            for value in value_matches:
                if pattern.match(value) and not is_placeholder(value, file_path):
                    findings.append((secret_name, value, line_num, line.rstrip()))

    return findings


def report_findings(
    findings_by_file: Dict[str, List[Tuple[str, str, int, str]]], verbose: bool = False
) -> None:
    """
    Report found secrets with actionable remediation steps.

    Args:
        findings_by_file: Dictionary mapping file paths to findings
        verbose: Whether to print verbose output
    """
    if not findings_by_file:
        if verbose:
            print("✅ No ACGS-2 secrets detected in staged files")  # noqa: T201
        return

    print("\n" + "=" * 80)  # noqa: T201
    print("🚫 ACGS-2 SECRETS DETECTED")  # noqa: T201
    print("=" * 80)  # noqa: T201
    print()  # noqa: T201

    total_findings = sum(len(findings) for findings in findings_by_file.values())

    for file_path, findings in findings_by_file.items():
        print(f"📄 File: {file_path}")  # noqa: T201
        print()  # noqa: T201

        for secret_name, secret_value, line_num, line_content in findings:
            category = get_secret_category(secret_name)

            # Redact value for display (show first 4 and last 4 chars)
            if len(secret_value) > 12:
                redacted_value = f"{secret_value[:4]}...{secret_value[-4:]}"
            else:
                redacted_value = "***"

            print(f"   🔑 Secret Type: {secret_name}")  # noqa: T201
            print(f"      Category: {category}")  # noqa: T201
            print(f"      Line: {line_num}")  # noqa: T201
            print(f"      Value: {redacted_value}")  # noqa: T201
            print(f"      Content: {line_content[:100]}")  # noqa: T201
            print()  # noqa: T201

    # Remediation guidance
    print("=" * 80)  # noqa: T201
    print("💡 REMEDIATION STEPS")  # noqa: T201
    print("=" * 80)  # noqa: T201
    print()  # noqa: T201
    print("Option 1: Remove the secret and use environment variables")  # noqa: T201
    print("   1. Remove the secret value from the file")  # noqa: T201
    print("   2. Add to .env file (ensure .env is in .gitignore)")  # noqa: T201
    print(
        "   3. Load via: from src.core.shared.secrets_manager import get_secrets_manager"
    )  # noqa: T201
    print("                secret = get_secrets_manager().get('SECRET_NAME')")  # noqa: T201
    print()  # noqa: T201
    print("Option 2: If this is a development placeholder")  # noqa: T201
    print("   1. Use a safe prefix: dev-*, test-*, your-*, example-*")  # noqa: T201
    print("   2. Example: JWT_SECRET=dev-jwt-secret-min-32-chars-required")  # noqa: T201
    print()  # noqa: T201
    print("Option 3: Add exception to .gitleaksignore")  # noqa: T201
    print("   1. Only if you're certain it's safe (development cert, test fixture)")  # noqa: T201
    print("   2. Add with clear comment explaining why it's safe")  # noqa: T201
    print("   3. Include production mitigation notes")  # noqa: T201
    print()  # noqa: T201
    print("=" * 80)  # noqa: T201
    print(
        f"Total findings: {total_findings} secret(s) in {len(findings_by_file)} file(s)"
    )  # noqa: T201
    print("=" * 80)  # noqa: T201
    print()  # noqa: T201
    print("📚 Documentation: docs/SECRETS_DETECTION.md")  # noqa: T201
    print("🔧 Pattern source: src/core/shared/secrets_manager.py")  # noqa: T201
    print("⚙️  Allow-list config: .secrets-allowlist.yaml")  # noqa: T201
    print(f"🏛️  Constitutional Hash: {CONSTITUTIONAL_HASH}")  # noqa: T201
    print()  # noqa: T201


def main():
    """Main entry point for pre-commit hook."""
    parser = argparse.ArgumentParser(description="ACGS-2 custom secrets detection for pre-commit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("files", nargs="*", help="Files to check (default: staged files from git)")
    args = parser.parse_args()

    if args.verbose:
        print("🔐 ACGS-2 Custom Secrets Detection")  # noqa: T201
        print(f"   Constitutional Hash: {CONSTITUTIONAL_HASH}")  # noqa: T201
        print("   Patterns from: secrets_manager.py")  # noqa: T201
        print(f"   Allow-list from: {ALLOWLIST_CONFIG_PATH.name}")  # noqa: T201
        print(
            f"   Config loaded: {'✅' if ALLOWLIST_CONFIG_PATH.exists() else '⚠️ Using defaults'}"
        )  # noqa: T201
        print()  # noqa: T201

    # Get files to scan
    if args.files:
        files_to_scan = [f for f in args.files if should_scan_file(f)]
    else:
        files_to_scan = get_staged_files()

    if not files_to_scan:
        if args.verbose:
            print("ℹ️  No files to scan")  # noqa: T201
        return 0

    if args.verbose:
        print(f"📁 Scanning {len(files_to_scan)} file(s)...")  # noqa: T201
        print()  # noqa: T201

    # Scan files
    findings_by_file = {}
    for file_path in files_to_scan:
        findings = scan_file_for_secrets(file_path, verbose=args.verbose)
        if findings:
            findings_by_file[file_path] = findings

    # Report findings
    report_findings(findings_by_file, verbose=args.verbose)

    # Exit with appropriate code
    if findings_by_file:
        return 1  # Fail - secrets found
    return 0  # Pass - no secrets


if __name__ == "__main__":
    sys.exit(main())
