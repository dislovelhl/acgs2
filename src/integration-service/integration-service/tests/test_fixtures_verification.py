"""
Verification tests for JWT authentication fixtures.

This test file verifies that the JWT fixtures in conftest.py work correctly.
"""

from src.api.auth import UserClaims


def test_test_user_claims_fixture(test_user_claims):
    """Verify test_user_claims fixture creates valid claims."""
    assert isinstance(test_user_claims, UserClaims)
    assert test_user_claims.sub == "test-user-123"
    assert test_user_claims.tenant_id == "test-tenant-456"
    assert "user" in test_user_claims.roles
    assert "policy:validate" in test_user_claims.permissions


def test_admin_user_claims_fixture(admin_user_claims):
    """Verify admin_user_claims fixture creates valid claims."""
    assert isinstance(admin_user_claims, UserClaims)
    assert admin_user_claims.sub == "admin-user-789"
    assert "admin" in admin_user_claims.roles
    assert "policy:manage" in admin_user_claims.permissions


def test_limited_user_claims_fixture(limited_user_claims):
    """Verify limited_user_claims fixture creates valid claims."""
    assert isinstance(limited_user_claims, UserClaims)
    assert limited_user_claims.sub == "limited-user-999"
    assert "viewer" in limited_user_claims.roles
    assert limited_user_claims.permissions == ["read"]


def test_test_jwt_token_fixture(test_jwt_token):
    """Verify test_jwt_token fixture creates valid token."""
    assert isinstance(test_jwt_token, str)
    assert len(test_jwt_token) > 0
    # JWT tokens have format: header.payload.signature
    assert test_jwt_token.count(".") == 2


def test_admin_jwt_token_fixture(admin_jwt_token):
    """Verify admin_jwt_token fixture creates valid token."""
    assert isinstance(admin_jwt_token, str)
    assert len(admin_jwt_token) > 0
    assert admin_jwt_token.count(".") == 2


def test_expired_jwt_token_fixture(expired_jwt_token):
    """Verify expired_jwt_token fixture creates valid token."""
    assert isinstance(expired_jwt_token, str)
    assert len(expired_jwt_token) > 0
    assert expired_jwt_token.count(".") == 2


def test_malformed_jwt_token_fixture(malformed_jwt_token):
    """Verify malformed_jwt_token fixture returns expected value."""
    assert malformed_jwt_token == "malformed.jwt.token.that.is.invalid"


def test_create_jwt_token_factory(create_jwt_token):
    """Verify create_jwt_token factory fixture works."""
    token = create_jwt_token(
        user_id="custom-user",
        tenant_id="custom-tenant",
        roles=["custom-role"],
        permissions=["custom-permission"],
    )
    assert isinstance(token, str)
    assert token.count(".") == 2


def test_auth_headers_fixture(auth_headers, test_jwt_token):
    """Verify auth_headers fixture creates correct headers."""
    assert "Authorization" in auth_headers
    assert auth_headers["Authorization"] == f"Bearer {test_jwt_token}"
    assert auth_headers["Authorization"].startswith("Bearer ")


def test_admin_auth_headers_fixture(admin_auth_headers, admin_jwt_token):
    """Verify admin_auth_headers fixture creates correct headers."""
    assert "Authorization" in admin_auth_headers
    assert admin_auth_headers["Authorization"] == f"Bearer {admin_jwt_token}"


def test_expired_auth_headers_fixture(expired_auth_headers, expired_jwt_token):
    """Verify expired_auth_headers fixture creates correct headers."""
    assert "Authorization" in expired_auth_headers
    assert expired_auth_headers["Authorization"] == f"Bearer {expired_jwt_token}"


def test_malformed_auth_headers_fixture(malformed_auth_headers):
    """Verify malformed_auth_headers fixture creates correct headers."""
    assert "Authorization" in malformed_auth_headers
    assert "malformed.jwt.token.that.is.invalid" in malformed_auth_headers["Authorization"]


def test_test_client_fixture(test_client):
    """Verify test_client fixture creates TestClient."""
    assert test_client is not None
    # Test that the client can access the root endpoint
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["service"] == "integration-service"


def test_authenticated_client_fixture(authenticated_client):
    """Verify authenticated_client fixture has auth headers."""
    assert authenticated_client is not None
    assert "Authorization" in authenticated_client.headers
    assert authenticated_client.headers["Authorization"].startswith("Bearer ")
