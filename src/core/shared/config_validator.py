import logging

logger = logging.getLogger(__name__)
"""
ACGS-2 Configuration Validator
Constitutional Hash: cdd01ef066bc6cf2

Provides comprehensive configuration validation for:
- Environment detection
- Required variable validation
- Configuration schema enforcement
- Cross-environment drift detection
"""

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from src.core.shared.types import JSONDict
except ImportError:
    JSONDict = Dict[str, Any]

# Constitutional compliance constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class Environment(Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    CI = "ci"
    TEST = "test"


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"  # Must be fixed
    WARNING = "warning"  # Should be addressed
    INFO = "info"  # Informational


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""

    severity: ValidationSeverity
    category: str
    message: str
    fix_suggestion: Optional[str] = None
    key: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    environment: Environment
    issues: List[ValidationIssue] = field(default_factory=list)
    config_summary: JSONDict = field(default_factory=dict)

    def add_issue(
        self,
        severity: ValidationSeverity,
        category: str,
        message: str,
        fix_suggestion: Optional[str] = None,
        key: Optional[str] = None,
    ):
        """Add a validation issue."""
        self.issues.append(
            ValidationIssue(
                severity=severity,
                category=category,
                message=message,
                fix_suggestion=fix_suggestion,
                key=key,
            )
        )
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all errors."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warnings."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def print_report(self, verbose: bool = False):
        """Print a human-readable validation report."""
        logging.info("\n" + "=" * 60)
        logging.info("ACGS-2 Configuration Validation Report")
        logging.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
        logging.info("=" * 60)
        logging.info(f"\nEnvironment: {self.environment.value}")
        logging.info(f"Status: {'✓ VALID' if self.is_valid else '✗ INVALID'}")

        if self.errors:
            logging.error(f"\n❌ Errors ({len(self.errors)}):")
            for issue in self.errors:
                logging.info(f"   • [{issue.category}] {issue.message}")
                if issue.fix_suggestion:
                    logging.info(f"     💡 Fix: {issue.fix_suggestion}")

        if self.warnings:
            logging.warning(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for issue in self.warnings:
                logging.info(f"   • [{issue.category}] {issue.message}")
                if verbose and issue.fix_suggestion:
                    logging.info(f"     💡 Fix: {issue.fix_suggestion}")

        if verbose:
            info_issues = [i for i in self.issues if i.severity == ValidationSeverity.INFO]
            if info_issues:
                logging.info(f"\nℹ️  Info ({len(info_issues)}):")
                for issue in info_issues:
                    logging.info(f"   • [{issue.category}] {issue.message}")

        logging.info("\n" + "=" * 60)


class ConfigValidator:
    """
    Validates ACGS-2 configuration across environments.

    Usage:
        validator = ConfigValidator()
        result = validator.validate()
        if not result.is_valid:
            result.print_report()
            sys.exit(1)
    """

    # Required variables by environment
    REQUIRED_VARS: Dict[Environment, Set[str]] = {
        Environment.DEVELOPMENT: {
            "REDIS_URL",
        },
        Environment.STAGING: {
            "REDIS_URL",
            "OPA_URL",
            "KAFKA_BOOTSTRAP_SERVERS",
        },
        Environment.PRODUCTION: {
            "REDIS_URL",
            "REDIS_PASSWORD",
            "OPA_URL",
            "KAFKA_BOOTSTRAP_SERVERS",
            "KAFKA_PASSWORD",
            "JWT_SECRET",
            "API_KEY_INTERNAL",
        },
        Environment.CI: {
            "REDIS_URL",
        },
        Environment.TEST: set(),  # No required vars for test
    }

    # Security-sensitive variables that should never have default values in production
    SENSITIVE_VARS = {
        "JWT_SECRET",
        "API_KEY_INTERNAL",
        "BLOCKCHAIN_PRIVATE_KEY",
        "GITHUB_WEBHOOK_SECRET",
        "REDIS_PASSWORD",
        "KAFKA_PASSWORD",
    }

    # Forbidden placeholder values
    FORBIDDEN_PLACEHOLDERS = {
        "PLACEHOLDER",
        "CHANGE_ME",
        "DANGEROUS_DEFAULT",
        "TODO",
        "FIXME",
        "xxx",
        "password",
        "secret",
    }

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize validator."""
        self.project_root = project_root or Path.cwd()
        while self.project_root != self.project_root.parent:
            if (self.project_root / "src/core").exists():
                break
            self.project_root = self.project_root.parent

    def detect_environment(self) -> Environment:
        """Detect the current environment."""
        # Check explicit environment variable
        env_value = os.getenv("ACGS_ENV", os.getenv("APP_ENV", "")).lower()

        # Map to Environment enum
        env_map = {
            "production": Environment.PRODUCTION,
            "prod": Environment.PRODUCTION,
            "staging": Environment.STAGING,
            "stage": Environment.STAGING,
            "development": Environment.DEVELOPMENT,
            "dev": Environment.DEVELOPMENT,
            "ci": Environment.CI,
            "test": Environment.TEST,
            "testing": Environment.TEST,
        }

        if env_value in env_map:
            return env_map[env_value]

        # Check CI indicators
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("GITLAB_CI"):
            return Environment.CI

        # Check for environment-specific files
        if (self.project_root / ".env.production").exists():
            return Environment.PRODUCTION
        if (self.project_root / ".env.staging").exists():
            return Environment.STAGING

        # Default to development
        return Environment.DEVELOPMENT

    def validate(self, env: Optional[Environment] = None) -> ValidationResult:
        """Run full configuration validation."""
        detected_env = env or self.detect_environment()
        result = ValidationResult(is_valid=True, environment=detected_env)

        # Run all validations
        self._validate_required_vars(result)
        self._validate_sensitive_vars(result)
        self._validate_constitutional_hash(result)
        self._validate_env_files(result)
        self._validate_docker_config(result)
        self._validate_service_urls(result)

        return result

    def _validate_required_vars(self, result: ValidationResult):
        """Check that all required variables are set."""
        required = self.REQUIRED_VARS.get(result.environment, set())

        for var in required:
            value = os.getenv(var)
            if not value:
                result.add_issue(
                    severity=ValidationSeverity.ERROR,
                    category="required",
                    message=f"Required variable '{var}' is not set",
                    fix_suggestion=f"Set {var} in your .env file or environment",
                    key=var,
                )
            else:
                result.config_summary[var] = "***" if var in self.SENSITIVE_VARS else value

    def _validate_sensitive_vars(self, result: ValidationResult):
        """Check sensitive variables for weak values."""
        for var in self.SENSITIVE_VARS:
            value = os.getenv(var, "")
            if not value:
                continue  # Already handled by required check

            # Check for forbidden placeholders
            value_lower = value.lower()
            for placeholder in self.FORBIDDEN_PLACEHOLDERS:
                if placeholder in value_lower:
                    severity = (
                        ValidationSeverity.ERROR
                        if result.environment == Environment.PRODUCTION
                        else ValidationSeverity.WARNING
                    )
                    result.add_issue(
                        severity=severity,
                        category="security",
                        message=f"Variable '{var}' contains a forbidden placeholder value",
                        fix_suggestion="Replace with a secure, randomly generated value",
                        key=var,
                    )
                    break

            # Check minimum length for secrets
            if var in {"JWT_SECRET", "API_KEY_INTERNAL"} and len(value) < 32:
                result.add_issue(
                    severity=ValidationSeverity.WARNING,
                    category="security",
                    message=f"Variable '{var}' should be at least 32 characters",
                    fix_suggestion="Generate a longer secret for better security",
                    key=var,
                )

    def _validate_constitutional_hash(self, result: ValidationResult):
        """Verify constitutional hash is correctly configured."""
        config_hash = os.getenv("CONSTITUTIONAL_HASH", CONSTITUTIONAL_HASH)

        if config_hash != CONSTITUTIONAL_HASH:
            result.add_issue(
                severity=ValidationSeverity.ERROR,
                category="constitutional",
                message=(
                    f"Constitutional hash mismatch: expected "
                    f"'{CONSTITUTIONAL_HASH}', got '{config_hash}'"
                ),
                fix_suggestion="Ensure CONSTITUTIONAL_HASH is set correctly",
            )
        else:
            result.add_issue(
                severity=ValidationSeverity.INFO,
                category="constitutional",
                message=f"Constitutional hash verified: {CONSTITUTIONAL_HASH}",
            )

    def _validate_env_files(self, result: ValidationResult):
        """Check environment file configuration."""
        env_file = self.project_root / ".env"
        env_dev = self.project_root / ".env.dev"

        if not env_file.exists() and not env_dev.exists():
            result.add_issue(
                severity=ValidationSeverity.WARNING,
                category="config",
                message="No .env file found",
                fix_suggestion=(
                    "Create .env from .env.dev template or configure environment variables directly"
                ),
            )
        elif env_file.exists():
            result.add_issue(
                severity=ValidationSeverity.INFO,
                category="config",
                message=f".env file found at {env_file}",
            )

    def _validate_docker_config(self, result: ValidationResult):
        """Validate Docker Compose configuration."""
        compose_file = self.project_root / "docker-compose.dev.yml"

        if not compose_file.exists():
            result.add_issue(
                severity=ValidationSeverity.WARNING,
                category="docker",
                message="docker-compose.dev.yml not found",
                fix_suggestion="Ensure Docker Compose file exists for development",
            )
        else:
            result.add_issue(
                severity=ValidationSeverity.INFO,
                category="docker",
                message="Docker Compose configuration found",
            )

    def _validate_service_urls(self, result: ValidationResult):
        """Validate service URL configurations."""
        url_vars = {
            "REDIS_URL": "redis://localhost:6379",
            "OPA_URL": "http://localhost:8181",
            "AUDIT_SERVICE_URL": "http://localhost:8001",
        }

        for var, default in url_vars.items():
            value = os.getenv(var, default)
            result.config_summary[var] = value

            # Check for localhost in production
            if result.environment == Environment.PRODUCTION:
                if "localhost" in value or "127.0.0.1" in value:
                    result.add_issue(
                        severity=ValidationSeverity.ERROR,
                        category="urls",
                        message=f"Variable '{var}' uses localhost in production",
                        fix_suggestion=f"Configure {var} to use production service address",
                        key=var,
                    )


def validate_config(verbose: bool = False) -> bool:
    """
    Convenience function to validate configuration.

    Returns:
        True if configuration is valid, False otherwise
    """
    validator = ConfigValidator()
    result = validator.validate()
    result.print_report(verbose=verbose)
    return result.is_valid


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ACGS-2 Configuration Validator")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production", "ci", "test"],
        help="Override environment detection",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    validator = ConfigValidator()

    env = None
    if args.env:
        env = Environment(args.env)

    result = validator.validate(env)

    if args.json:
        import json

        output = {
            "valid": result.is_valid,
            "environment": result.environment.value,
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "fix": i.fix_suggestion,
                    "key": i.key,
                }
                for i in result.issues
            ],
            "config": result.config_summary,
        }
        logging.info(json.dumps(output, indent=2))
    else:
        result.print_report(verbose=args.verbose)

    sys.exit(0 if result.is_valid else 1)
