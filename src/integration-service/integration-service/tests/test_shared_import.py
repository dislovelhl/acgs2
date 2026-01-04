"""
Test to verify that integration-service can import from acgs2-core/shared/security/auth.py
"""

import pytest


def test_import_shared_auth_module():
    """Verify that we can import the shared authentication module."""
    try:
        from src.core.shared.security.auth import (
            UserClaims,
            create_access_token,
            create_test_token,
            get_current_user,
            verify_token,
        )

        # Verify imports are callable/classes
        assert callable(create_access_token)
        assert callable(create_test_token)
        assert callable(verify_token)
        assert callable(get_current_user)
        assert UserClaims is not None
    except ImportError as e:
        pytest.fail(f"Failed to import from src.core.shared.security.auth: {e}")


def test_import_shared_config():
    """Verify that we can import the shared config module."""
    try:
        from src.core.shared.config import settings

        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import from src.core.shared.config: {e}")


def test_import_shared_logging():
    """Verify that we can import the shared logging module."""
    try:
        from src.core.shared.logging import get_logger

        assert callable(get_logger)
    except ImportError as e:
        pytest.fail(f"Failed to import from src.core.shared.logging: {e}")


def test_jwt_configuration_accessible():
    """Verify that JWT configuration from src.core.shared.config is accessible."""
    import os
    from src.core.shared.config import settings

    # Set a test JWT_SECRET if not already set
    if not os.getenv("JWT_SECRET"):
        os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"

    # Re-import to pick up the environment variable
    from src.core.shared.config import get_settings

    test_settings = get_settings()

    # Verify JWT configuration is accessible
    assert test_settings.security is not None
    assert test_settings.security.jwt_secret is not None
    assert test_settings.security.jwt_secret.get_secret_value() != ""


def test_create_test_token():
    """Verify that we can create a test token using the shared auth module."""
    import os
    from src.core.shared.security.auth import create_test_token

    # Ensure JWT_SECRET is set for token creation
    if not os.getenv("JWT_SECRET"):
        os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-testing-only"

    # This test will actually create a token to ensure the module is fully functional
    token = create_test_token(
        user_id="test-user", tenant_id="test-tenant", roles=["admin"], permissions=["read", "write"]
    )

    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0
    # JWT tokens have three parts separated by dots
    assert token.count(".") == 2
