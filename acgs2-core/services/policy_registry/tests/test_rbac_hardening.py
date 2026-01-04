"""
Unit tests for hardened RBAC middleware.
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock
import sys

# Mock JWT library availability for one of the tests if needed,
# but here we test the hardened RBACMiddleware implementation.

def test_rbac_middleware_dev_secret_in_production(monkeypatch):
    """Verify that 'dev-secret' is forbidden in production."""
    from pydantic import SecretStr

    mock_settings = MagicMock()
    mock_settings.env = "production"
    # Ensure raw_secret in RBACConfig.__init__ sees the SecretStr
    mock_settings.security.jwt_secret = SecretStr("dev-secret")
    mock_settings.security.jwt_algorithm = "HS256"

    # Mock settings in BOTH the module and shared.config if needed
    import services.policy_registry.app.middleware.rbac as rbac_module
    monkeypatch.setattr(rbac_module, "settings", mock_settings)

    from services.policy_registry.app.middleware.rbac import RBACMiddleware
    app = MagicMock()
    with pytest.raises(ValueError, match="Insecure JWT_SECRET 'dev-secret' is forbidden in production"):
        RBACMiddleware(app)

def test_rbac_token_validation_no_jwt_library(monkeypatch):
    """Verify that token validation fails if JWT library is missing."""
    import services.policy_registry.app.middleware.rbac as rbac_module
    from pydantic import SecretStr

    # Mock settings for successful initialization
    mock_settings = MagicMock()
    mock_settings.env = "development"
    mock_settings.security.jwt_secret = SecretStr("valid-secret-at-least-thirty-two-chars-long")
    monkeypatch.setattr(rbac_module, "settings", mock_settings)

    # Temporarily set JWT_AVAILABLE to False
    monkeypatch.setattr(rbac_module, "JWT_AVAILABLE", False)

    from services.policy_registry.app.middleware.rbac import RBACMiddleware
    app = MagicMock()
    middleware = RBACMiddleware(app)

    # validate_token is a method of token_validator and it is synchronous
    with pytest.raises(HTTPException) as exc:
        middleware.token_validator.validate_token("dummy-token")

    assert exc.value.status_code == 500
    assert "Authentication service misconfigured" in exc.value.detail
