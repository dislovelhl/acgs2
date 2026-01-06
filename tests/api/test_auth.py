"""
Tests for authentication system
"""

import pytest

from src.acgs2.api.auth import AuthManager


class TestAuthManager:
    """Test authentication manager functionality."""

    def test_user_creation(self):
        """Test user creation and authentication."""
        auth = AuthManager()

        # Create user
        user = auth.create_user("testuser", "password_for_testuser", "user")
        assert user.username == "testuser"
        assert user.role == "user"
        assert user.user_id.startswith("user_")

        # Authenticate user
        authenticated = auth.authenticate_user("testuser", "password_for_testuser")
        assert authenticated is not None
        assert authenticated.user_id == user.user_id

        # Test invalid credentials
        invalid = auth.authenticate_user("testuser", "wrongpassword")
        assert invalid is None

    def test_api_key_management(self):
        """Test API key creation and verification."""
        auth = AuthManager()

        # Create user
        user = auth.create_user("apikeyuser", "password_for_apikeyuser", "user")

        # Create API key
        api_key = auth.create_api_key(user.user_id, "test_key", "user")
        assert isinstance(api_key, str)
        assert len(api_key) > 0

        # Verify API key
        verified_user = auth.verify_api_key(api_key)
        assert verified_user is not None
        assert verified_user.user_id == user.user_id

        # Test invalid API key
        invalid_user = auth.verify_api_key("invalid_key")
        assert invalid_user is None

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        auth = AuthManager()

        user_id = "test_user"

        # Should allow requests initially
        for i in range(10):
            allowed = auth.check_rate_limit(user_id)
            assert allowed is True

        # Check rate limit info
        info = auth.get_rate_limit_info(user_id)
        assert info["requests_used"] == 10
        assert info["requests_limit"] == 100  # Default limit

    def test_jwt_tokens(self):
        """Test JWT token creation and verification."""
        auth = AuthManager()

        # Create user
        user = auth.create_user("jwttest", "password_for_jwttest", "user")

        # Create token
        token = auth.create_access_token(user)
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token
        verified_user = auth.verify_token(token)
        assert verified_user is not None
        assert verified_user.user_id == user.user_id

        # Test invalid token
        invalid_user = auth.verify_token("invalid.jwt.token")
        assert invalid_user is None


if __name__ == "__main__":
    pytest.main([__file__])
