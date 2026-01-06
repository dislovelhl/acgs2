"""
Configuration validation utilities.

Provides validators for integration configurations, including
connectivity checks, credential validation, and schema enforcement.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import ValidationError as PydanticValidationError

from ..exceptions.validation import ConfigValidationError
from .models import (
    BaseIntegrationConfig,
    GitHubActionsConfig,
    GitLabCIConfig,
    JiraConfig,
    SentinelConfig,
    ServiceNowConfig,
    SplunkConfig,
    WebhookConfig,
)

logger = logging.getLogger(__name__)

# Public API exports - make exceptions and validators available for import from this module
__all__ = [
    "ConfigValidationError",
    "ValidationResult",
    "ConfigValidator",
]


class ValidationResult:
    """Result of a configuration validation check."""

    def __init__(
        self,
        valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        return self.valid

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ConfigValidator:
    """
    Validator for integration configurations.

    Provides comprehensive validation including:
    - Schema validation via Pydantic
    - Business rule validation
    - Cross-field validation
    - Environment-specific checks
    """

    # URL patterns for validation
    URL_PATTERN = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    # Email pattern for validation
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __init__(self) -> None:
        """Initialize the validator."""
        self._custom_validators: Dict[str, callable] = {}

    def register_validator(self, provider: str, validator: callable) -> None:
        """
        Register a custom validator for a specific provider.

        Args:
            provider: Integration provider name (e.g., 'splunk')
            validator: Callable that takes config and returns ValidationResult
        """
        self._custom_validators[provider] = validator

    def validate(
        self,
        config: Union[Dict[str, Any], BaseIntegrationConfig],
        config_type: Optional[Type[BaseIntegrationConfig]] = None,
    ) -> ValidationResult:
        """
        Validate an integration configuration.

        Args:
            config: Configuration dict or Pydantic model
            config_type: Optional type hint for dict configs

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Convert dict to Pydantic model if needed
        if isinstance(config, dict):
            try:
                if config_type:
                    config = config_type(**config)
                else:
                    config = self._infer_and_parse_config(config)
            except PydanticValidationError as e:
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    errors.append(f"{field}: {error['msg']}")
                return ValidationResult(valid=False, errors=errors)

        # Run provider-specific validation
        provider = getattr(config, "provider", None)
        if provider:
            provider_result = self._validate_provider(config)
            errors.extend(provider_result.errors)
            warnings.extend(provider_result.warnings)

        # Run custom validators if registered
        if provider and provider in self._custom_validators:
            try:
                custom_result = self._custom_validators[provider](config)
                if isinstance(custom_result, ValidationResult):
                    errors.extend(custom_result.errors)
                    warnings.extend(custom_result.warnings)
            except Exception as e:
                logger.warning(f"Custom validator failed for {provider}: {e}")
                warnings.append(f"Custom validation skipped: {str(e)}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _infer_and_parse_config(self, config: Dict[str, Any]) -> BaseIntegrationConfig:
        """
        Infer the config type from the dict and parse it.

        Args:
            config: Configuration dictionary

        Returns:
            Parsed Pydantic model

        Raises:
            ValueError: If config type cannot be inferred
        """
        provider = config.get("provider")
        if not provider:
            raise ValueError("Cannot infer config type: 'provider' field is required")

        provider_map: Dict[str, Type[BaseIntegrationConfig]] = {
            "splunk": SplunkConfig,
            "sentinel": SentinelConfig,
            "jira": JiraConfig,
            "servicenow": ServiceNowConfig,
            "github": GitHubActionsConfig,
            "gitlab": GitLabCIConfig,
            "webhook": WebhookConfig,
        }

        config_class = provider_map.get(provider)
        if not config_class:
            raise ValueError(f"Unknown provider: {provider}")

        return config_class(**config)

    def _validate_provider(self, config: BaseIntegrationConfig) -> ValidationResult:
        """
        Run provider-specific validation rules.

        Args:
            config: Parsed configuration model

        Returns:
            ValidationResult with provider-specific errors/warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        if isinstance(config, SplunkConfig):
            result = self._validate_splunk(config)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif isinstance(config, SentinelConfig):
            result = self._validate_sentinel(config)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif isinstance(config, JiraConfig):
            result = self._validate_jira(config)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif isinstance(config, ServiceNowConfig):
            result = self._validate_servicenow(config)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif isinstance(config, (GitHubActionsConfig, GitLabCIConfig)):
            result = self._validate_cicd(config)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        elif isinstance(config, WebhookConfig):
            result = self._validate_webhook(config)
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_splunk(self, config: SplunkConfig) -> ValidationResult:
        """Validate Splunk-specific configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Check host format
        if "/" in config.host:
            errors.append(
                "host should not contain paths, only hostname (e.g., 'splunk.example.com')"
            )

        # Warn about SSL settings
        if not config.use_ssl:
            warnings.append("SSL is disabled - credentials will be sent in plain text")
        elif not config.verify_ssl:
            warnings.append("SSL verification is disabled - vulnerable to MITM attacks")

        # Check for common HEC port
        if config.port not in [8088, 443]:
            warnings.append(f"Non-standard HEC port {config.port} - verify this is correct")

        # Index name validation
        if config.index == "main":
            warnings.append("Using default 'main' index - consider using a dedicated index")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_sentinel(self, config: SentinelConfig) -> ValidationResult:
        """Validate Azure Sentinel-specific configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate tenant ID format (GUID)
        guid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not guid_pattern.match(config.tenant_id):
            errors.append("tenant_id must be a valid GUID")
        if not guid_pattern.match(config.client_id):
            errors.append("client_id must be a valid GUID")

        # Validate DCR immutable ID format
        if not config.dcr_immutable_id.startswith("dcr-"):
            warnings.append(
                "dcr_immutable_id typically starts with 'dcr-' - verify this is correct"
            )

        # Stream name validation
        if not config.stream_name.startswith("Custom-"):
            warnings.append("stream_name should typically start with 'Custom-' for custom tables")
        if not config.stream_name.endswith("_CL"):
            warnings.append("stream_name should typically end with '_CL' for custom logs")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_jira(self, config: JiraConfig) -> ValidationResult:
        """Validate Jira-specific configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate base URL
        if not self.URL_PATTERN.match(config.base_url):
            errors.append("base_url is not a valid URL")

        # Check for Atlassian Cloud
        if "atlassian.net" in config.base_url and not config.is_cloud:
            warnings.append("URL appears to be Jira Cloud but is_cloud is False")

        # Validate email for API token auth
        if config.auth_type == "api_token" and config.user_email:
            if not self.EMAIL_PATTERN.match(config.user_email):
                errors.append("user_email is not a valid email address")

        # Project key format
        if not re.match(r"^[A-Z][A-Z0-9]*$", config.project_key):
            warnings.append("project_key should be uppercase letters/numbers (e.g., 'GOV')")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_servicenow(self, config: ServiceNowConfig) -> ValidationResult:
        """Validate ServiceNow-specific configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate instance URL
        if not self.URL_PATTERN.match(config.instance):
            errors.append("instance is not a valid URL")

        # Check for service-now.com domain
        if "service-now.com" not in config.instance:
            warnings.append(
                "instance URL does not contain 'service-now.com' - verify this is correct"
            )

        # Impact and urgency should be 1-3
        valid_levels = {"1", "2", "3"}
        if config.impact not in valid_levels:
            errors.append("impact must be '1', '2', or '3'")
        if config.urgency not in valid_levels:
            errors.append("urgency must be '1', '2', or '3'")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_cicd(
        self, config: Union[GitHubActionsConfig, GitLabCIConfig]
    ) -> ValidationResult:
        """Validate CI/CD integration configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate severity threshold
        valid_severities = {"critical", "high", "medium", "low", "info"}
        if config.severity_threshold.lower() not in valid_severities:
            errors.append(f"severity_threshold must be one of: {', '.join(valid_severities)}")

        if isinstance(config, GitHubActionsConfig):
            # Validate GitHub API URL
            if not self.URL_PATTERN.match(config.api_url):
                errors.append("api_url is not a valid URL")

            # Warn about token permissions
            if config.app_id and not config.app_private_key:
                errors.append("app_private_key is required when using GitHub App authentication")

        elif isinstance(config, GitLabCIConfig):
            # Validate GitLab API URL
            if not self.URL_PATTERN.match(config.api_url):
                errors.append("api_url is not a valid URL")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_webhook(self, config: WebhookConfig) -> ValidationResult:
        """Validate webhook configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate URL
        if not self.URL_PATTERN.match(config.url):
            errors.append("url is not a valid URL")

        # Warn about HTTP endpoints
        if config.url.startswith("http://"):
            warnings.append("Using HTTP instead of HTTPS - credentials may be exposed")

        # HMAC validation
        if config.auth_type.value == "hmac" and not config.hmac_secret:
            errors.append("hmac_secret is required when using HMAC authentication")

        # Auth value validation
        if config.auth_type.value in ("api_key", "bearer") and not config.auth_value:
            errors.append(
                f"auth_value is required when using {config.auth_type.value} authentication"
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


def validate_integration_config(
    config: Union[Dict[str, Any], BaseIntegrationConfig],
    config_type: Optional[Type[BaseIntegrationConfig]] = None,
    raise_on_error: bool = False,
) -> ValidationResult:
    """
    Convenience function to validate an integration configuration.

    Args:
        config: Configuration dict or Pydantic model
        config_type: Optional type hint for dict configs
        raise_on_error: If True, raise ConfigValidationError on validation failure

    Returns:
        ValidationResult with validation status

    Raises:
        ConfigValidationError: If raise_on_error is True and validation fails
    """
    validator = ConfigValidator()
    result = validator.validate(config, config_type)

    if raise_on_error and not result.valid:
        raise ConfigValidationError(
            message="Configuration validation failed",
            details={"errors": result.errors, "warnings": result.warnings},
        )

    return result
