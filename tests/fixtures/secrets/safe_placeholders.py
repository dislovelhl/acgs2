"""
ACGS-2 Safe Placeholder Test Fixtures
Constitutional Hash: cdd01ef066bc6cf2

This file contains SAFE placeholders that should PASS secrets detection.
These are development placeholders following the allow-list patterns.

⚠️ TESTING ONLY - All values here are fake placeholders for validation
"""

# =============================================================================
# ✅ SAFE: Development Prefix Placeholders (dev-*, test-*, etc.)
# =============================================================================

# These should all PASS because they use safe prefixes
CLAUDE_CODE_OAUTH_TOKEN = "dev-claude-code-token-placeholder"
OPENAI_API_KEY = "test-openai-key-12345"
OPENROUTER_API_KEY = "dev-openrouter-api-key"
HF_TOKEN = "test-huggingface-token"
ANTHROPIC_API_KEY = "dev-anthropic-key-placeholder"
AWS_ACCESS_KEY_ID = "dev-aws-access-key"
AWS_SECRET_ACCESS_KEY = "dev-aws-secret-key"
JWT_SECRET = "dev-jwt-secret-min-32-chars-required"
VAULT_TOKEN = "dev-vault-token-placeholder"
REDIS_PASSWORD = "dev_password"
DB_USER_PASSWORD = "test_password"


# =============================================================================
# ✅ SAFE: Instructional Placeholders (<...>, your-*, etc.)
# =============================================================================

# These should all PASS because they use instructional markers
CLAUDE_CODE_OAUTH_TOKEN_INSTRUCTION = "<your-claude-code-token>"
OPENAI_API_KEY_INSTRUCTION = "your-openai-api-key-here"
OPENROUTER_API_KEY_INSTRUCTION = "<insert-openrouter-key>"
HF_TOKEN_INSTRUCTION = "your-hf-token"
ANTHROPIC_API_KEY_INSTRUCTION = "<your-anthropic-key>"
AWS_ACCESS_KEY_ID_INSTRUCTION = "your-aws-access-key-id"
JWT_SECRET_INSTRUCTION = "your-jwt-secret-here"
VAULT_TOKEN_INSTRUCTION = "<your-vault-token>"


# =============================================================================
# ✅ SAFE: Redacted Examples (XXX, ***, sk-ant-XXX...XXX)
# =============================================================================

# These should all PASS because they are clearly redacted
CLAUDE_CODE_OAUTH_TOKEN_REDACTED = "sk-ant-oat01-XXX...XXX"
OPENAI_API_KEY_REDACTED = "sk-XXX...XXX"
OPENROUTER_API_KEY_REDACTED = "sk-or-v1-XXX...XXX"
HF_TOKEN_REDACTED = "hf_XXX...XXX"
ANTHROPIC_API_KEY_REDACTED = "sk-ant-XXX...XXX"
AWS_ACCESS_KEY_ID_REDACTED = "AKIA****************"
JWT_SECRET_REDACTED = "************************************************************"
VAULT_TOKEN_REDACTED = "hvs.XXX...XXX"


# =============================================================================
# ✅ SAFE: Example/Sample Prefixes
# =============================================================================

# These should all PASS because they use example/sample prefixes
EXAMPLE_API_KEY = "example-api-key-abc123"
SAMPLE_TOKEN = "sample-token-xyz789"
PLACEHOLDER_SECRET = "placeholder-secret-value"


# =============================================================================
# ✅ SAFE: Generic Development Values
# =============================================================================

# These should all PASS as generic safe values
GENERIC_PASSWORD = "changeme"
GENERIC_SECRET = "secret"
EMPTY_VALUE = ""
NONE_VALUE = None
TODO_VALUE = "TODO: add your key here"
FIXME_VALUE = "FIXME: replace with real token"


# =============================================================================
# ✅ SAFE: Known Safe Development Values from .env.dev
# =============================================================================

# These should all PASS because they're in the known_safe_values list
KNOWN_JWT_SECRET = "dev-jwt-secret-min-32-chars-required"
KNOWN_REDIS_PASSWORD = "dev_password"
KNOWN_POSTGRES_PASSWORD = "mlflow_password"


# =============================================================================
# Configuration Dictionary (Safe)
# =============================================================================

SAFE_CONFIG = {
    "ai_providers": {
        "claude_code": "dev-claude-code-token",
        "openai": "test-openai-key",
        "openrouter": "example-openrouter-key",
        "huggingface": "sample-hf-token",
        "anthropic": "your-anthropic-key",
    },
    "infrastructure": {
        "aws_access_key_id": "dev-aws-access-key",
        "aws_secret_access_key": "dev-aws-secret-key",
        "jwt_secret": "dev-jwt-secret-min-32-chars-required",
        "vault_token": "test-vault-token",
        "redis_password": "dev_password",
    },
    "placeholders": {
        "generic": "changeme",
        "instructional": "<your-key-here>",
        "redacted": "XXX...XXX",
        "empty": "",
    },
}


# =============================================================================
# Class-based Configuration (Safe)
# =============================================================================


class SafeSecretsConfig:
    """Safe configuration with development placeholders."""

    # AI Provider Keys
    CLAUDE_CODE_OAUTH_TOKEN = "dev-claude-code-oauth-token"
    OPENAI_API_KEY = "test-openai-api-key"
    OPENROUTER_API_KEY = "dev-openrouter-api-key"
    HF_TOKEN = "test-hf-token-placeholder"
    ANTHROPIC_API_KEY = "dev-anthropic-api-key"

    # Infrastructure Secrets
    AWS_ACCESS_KEY_ID = "dev-aws-access-key-id"
    AWS_SECRET_ACCESS_KEY = "dev-aws-secret-access-key"
    JWT_SECRET = "dev-jwt-secret-min-32-chars-required"
    VAULT_TOKEN = "dev-vault-token"
    REDIS_PASSWORD = "dev_password"
    DB_USER_PASSWORD = "test_password"

    # Instructional placeholders
    EXAMPLE_API_KEY = "your-api-key-here"
    EXAMPLE_TOKEN = "<insert-token-here>"


# =============================================================================
# Environment-style Assignments (Safe)
# =============================================================================

# These should all PASS with various safe patterns
os_environ_safe = {
    "CLAUDE_CODE_OAUTH_TOKEN": "dev-claude-code-token-placeholder",
    "OPENAI_API_KEY": "test-openai-api-key-12345",
    "OPENROUTER_API_KEY": "example-openrouter-key",
    "HF_TOKEN": "sample-hf-token",
    "ANTHROPIC_API_KEY": "your-anthropic-key-here",
    "AWS_ACCESS_KEY_ID": "dev-aws-access-key-id",
    "AWS_SECRET_ACCESS_KEY": "dev-aws-secret-access-key",
    "JWT_SECRET": "dev-jwt-secret-min-32-chars-required",
    "VAULT_TOKEN": "test-vault-token-placeholder",
    "REDIS_PASSWORD": "dev_password",
    "DB_USER_PASSWORD": "test_password",
    "KAFKA_SASL_PASSWORD": "changeme",
}


# =============================================================================
# Function Return Values (Safe)
# =============================================================================


def get_safe_api_key():
    """Return a safe development API key placeholder."""
    return "dev-api-key-placeholder"


def get_safe_token():
    """Return a safe test token placeholder."""
    return "test-token-12345"


def get_safe_secret():
    """Return an instructional placeholder."""
    return "<your-secret-here>"


# =============================================================================
# Multi-line Safe Examples
# =============================================================================

SAFE_MULTILINE_CONFIG = """
# Development Configuration (Safe Placeholders)
CLAUDE_CODE_OAUTH_TOKEN=dev-claude-code-token
OPENAI_API_KEY=test-openai-key
OPENROUTER_API_KEY=example-openrouter-key
HF_TOKEN=sample-hf-token
ANTHROPIC_API_KEY=your-anthropic-key
AWS_ACCESS_KEY_ID=dev-aws-access-key
JWT_SECRET=dev-jwt-secret-min-32-chars-required
VAULT_TOKEN=test-vault-token
"""

SAFE_JSON_CONFIG = """
{
    "claude_code_token": "dev-claude-code-oauth-token",
    "openai_key": "test-openai-api-key",
    "openrouter_key": "example-openrouter-key",
    "hf_token": "sample-hf-token",
    "anthropic_key": "your-anthropic-key-here",
    "aws_access_key_id": "dev-aws-access-key-id",
    "jwt_secret": "dev-jwt-secret-min-32-chars-required",
    "vault_token": "test-vault-token"
}
"""

# =============================================================================
# Edge Cases (Safe)
# =============================================================================

# Empty/None values should be safe
EMPTY_STRING = ""
NULL_VALUE = None

# Comments with placeholders should be safe
# Example: sk-ant-oat01-YOUR_TOKEN_HERE
# Example: AKIAIOSFODNN7EXAMPLE

# Redacted documentation examples
DOCS_EXAMPLE_1 = "sk-ant-XXX...XXX"  # Redacted format
DOCS_EXAMPLE_2 = "AKIA****************"  # Redacted AWS key

# Template strings
TEMPLATE_1 = "sk-ant-{token}"
TEMPLATE_2 = "${OPENAI_API_KEY}"
TEMPLATE_3 = "{{ANTHROPIC_API_KEY}}"
