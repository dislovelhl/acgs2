"""
Comprehensive tests for malformed JWT token handling.

This test suite verifies that all policy validation endpoints properly reject
malformed or invalid JWT tokens with appropriate error messages and status codes.
"""

import base64
import json

from fastapi.testclient import TestClient


class TestMalformedTokenRejection:
    """Test that all endpoints properly reject malformed JWT tokens."""

    def test_validate_endpoint_rejects_malformed_token(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify /api/policy/validate rejects malformed JWT tokens with 401."""
        response = test_client.post(
            "/api/policy/validate",
            headers=malformed_auth_headers,
            json={
                "resources": [
                    {
                        "path": "test.py",
                        "type": "code",
                        "content": "print('hello')",
                    }
                ]
            },
        )
        assert response.status_code == 401
        assert "detail" in response.json()
        # Verify error message indicates authentication failure
        assert "Could not validate credentials" in response.json()["detail"]

    def test_list_policies_endpoint_rejects_malformed_token(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify /api/policy/policies rejects malformed JWT tokens with 401."""
        response = test_client.get("/api/policy/policies", headers=malformed_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_policy_endpoint_rejects_malformed_token(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify /api/policy/policies/{id} rejects malformed JWT tokens with 401."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=malformed_auth_headers
        )
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Could not validate credentials" in response.json()["detail"]

    def test_health_endpoint_rejects_malformed_token(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify /api/policy/health rejects malformed JWT tokens with 401."""
        response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Could not validate credentials" in response.json()["detail"]


class TestMalformedTokenVariations:
    """Test various malformed token scenarios."""

    def test_empty_token(self, test_client: TestClient):
        """Verify empty token string is rejected."""
        headers = {"Authorization": "Bearer "}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_without_bearer_prefix(self, test_client: TestClient):
        """Verify token without 'Bearer' prefix is rejected."""
        headers = {"Authorization": "malformed.jwt.token"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401

    def test_token_with_invalid_parts_count(self, test_client: TestClient):
        """Verify token without exactly 3 parts (header.payload.signature) is rejected."""
        # Token with only 2 parts
        headers = {"Authorization": "Bearer invalid.token"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

        # Token with 4 parts
        headers = {"Authorization": "Bearer invalid.token.with.extra"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401

    def test_token_with_invalid_base64_encoding(self, test_client: TestClient):
        """Verify token with invalid base64 encoding is rejected."""
        # Create token with invalid base64 characters
        headers = {"Authorization": "Bearer !!!invalid!!!.???payload???.***signature***"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_invalid_json_payload(self, test_client: TestClient):
        """Verify token with non-JSON payload is rejected."""
        # Create token with valid base64 but invalid JSON
        invalid_payload = base64.urlsafe_b64encode(b"not-valid-json").decode("utf-8")
        headers = {"Authorization": f"Bearer header.{invalid_payload}.signature"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_missing_signature(self, test_client: TestClient):
        """Verify token without signature component is rejected."""
        # Create a valid-looking header and payload but omit signature
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode("utf-8")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user", "tenant_id": "tenant"}).encode()
        ).decode("utf-8")
        headers = {"Authorization": f"Bearer {header}.{payload}."}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_invalid_signature(self, test_client: TestClient):
        """Verify token with tampered signature is rejected."""
        # Create a properly formatted token but with wrong signature
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).decode("utf-8")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user", "tenant_id": "tenant", "exp": 9999999999}).encode()
        ).decode("utf-8")
        invalid_signature = base64.urlsafe_b64encode(b"wrong_signature").decode("utf-8")
        headers = {"Authorization": f"Bearer {header}.{payload}.{invalid_signature}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_wrong_algorithm(self, test_client: TestClient):
        """Verify token claiming unsupported algorithm is rejected."""
        # Create token with algorithm set to "none"
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).decode("utf-8")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user", "tenant_id": "tenant"}).encode()
        ).decode("utf-8")
        headers = {"Authorization": f"Bearer {header}.{payload}."}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_random_string_as_token(self, test_client: TestClient):
        """Verify random string is rejected as invalid token."""
        headers = {"Authorization": "Bearer random_gibberish_not_a_jwt_token_12345"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_malformed_token_does_not_leak_system_info(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify malformed token error doesn't leak system information."""
        response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
        assert response.status_code == 401

        data = response.json()
        # Should only return generic error, not system information
        assert "opa_available" not in data
        assert "builtin_policies" not in data
        assert "status" not in data or data.get("status") != "healthy"
        assert "audit_context" not in data


class TestMalformedTokenWithValidData:
    """Test that malformed tokens are rejected even with valid request data."""

    def test_malformed_token_with_valid_validation_request(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify valid validation data doesn't bypass malformed token check."""
        response = test_client.post(
            "/api/policy/validate",
            headers=malformed_auth_headers,
            json={
                "resources": [
                    {
                        "path": "main.py",
                        "type": "code",
                        "content": "import os\nprint('valid code')",
                        "metadata": {"language": "python"},
                    }
                ],
                "options": {"severity_threshold": "medium", "fail_fast": False},
            },
        )
        assert response.status_code == 401
        # Should not process the validation at all
        assert "passed" not in response.json()
        assert "violations" not in response.json()

    def test_malformed_token_with_valid_policy_id(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify valid policy ID doesn't bypass malformed token check."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=malformed_auth_headers
        )
        assert response.status_code == 401
        # Should not return policy data
        assert "policy" not in response.json()

    def test_malformed_token_with_valid_query_params(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify valid query parameters don't bypass malformed token check."""
        response = test_client.get(
            "/api/policy/policies?resource_type=kubernetes&enabled_only=true",
            headers=malformed_auth_headers,
        )
        assert response.status_code == 401
        # Should not return policy list
        assert "policies" not in response.json()


class TestMalformedTokenCrossEndpoint:
    """Test malformed token behavior consistency across all endpoints."""

    def test_malformed_token_rejected_by_all_endpoints(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify all policy endpoints consistently reject malformed tokens."""
        endpoints = [
            ("POST", "/api/policy/validate", {"resources": [{"path": "test.py"}]}),
            ("GET", "/api/policy/policies", None),
            ("GET", "/api/policy/policies/acgs2-security-001", None),
            ("GET", "/api/policy/health", None),
        ]

        for method, url, json_data in endpoints:
            if method == "POST":
                response = test_client.post(url, headers=malformed_auth_headers, json=json_data)
            else:
                response = test_client.get(url, headers=malformed_auth_headers)

            # All should return 401
            assert (
                response.status_code == 401
            ), f"{method} {url} should reject malformed token with 401"

            # All should have error detail
            assert "detail" in response.json()

            # All should return same generic error message
            assert "Could not validate credentials" in response.json()["detail"]

    def test_malformed_token_vs_valid_token_different_behavior(
        self, test_client: TestClient, malformed_auth_headers: dict, auth_headers: dict
    ):
        """Verify malformed vs valid tokens produce different results."""
        # Malformed token should fail
        malformed_response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
        assert malformed_response.status_code == 401

        # Valid token should succeed
        valid_response = test_client.get("/api/policy/health", headers=auth_headers)
        assert valid_response.status_code == 200

        # Valid response should include system information
        assert "status" in valid_response.json()
        assert valid_response.json()["status"] == "healthy"

    def test_multiple_malformed_token_types_same_error(self, test_client: TestClient):
        """Verify different types of malformed tokens return same generic error."""
        malformed_tokens = [
            "invalid",
            "invalid.token",
            "invalid.token.signature",
            "",
            "Bearer.only.one",
            "random_string_123",
        ]

        responses = []
        for token in malformed_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = test_client.get("/api/policy/health", headers=headers)
            responses.append(response)

        # All should return 401
        for response in responses:
            assert response.status_code == 401

        # All should have the same error detail (generic message)
        error_messages = [r.json()["detail"] for r in responses]
        # All messages should contain the generic error text
        for msg in error_messages:
            assert "Could not validate credentials" in msg


class TestMalformedTokenSecurityConsiderations:
    """Test security-related aspects of malformed token handling."""

    def test_malformed_token_no_audit_context_in_error(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify malformed token errors don't include audit context."""
        response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
        assert response.status_code == 401

        # Error response should not include audit context
        assert "audit_context" not in response.json()

        # Should only include error detail
        assert "detail" in response.json()

    def test_malformed_token_prevents_policy_enumeration(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify malformed tokens can't be used to enumerate policies."""
        # Try to get list of policies with malformed token
        response = test_client.get("/api/policy/policies", headers=malformed_auth_headers)
        assert response.status_code == 401

        # Should not return any policy information
        assert "policies" not in response.json()
        assert "total" not in response.json()

    def test_malformed_token_prevents_policy_validation(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify malformed tokens can't be used to validate policies."""
        response = test_client.post(
            "/api/policy/validate",
            headers=malformed_auth_headers,
            json={
                "resources": [
                    {
                        "path": "test.py",
                        "type": "code",
                        "content": "import os; os.system('ls')",  # Potentially sensitive code
                    }
                ]
            },
        )
        assert response.status_code == 401

        # Should not return validation results
        assert "passed" not in response.json()
        assert "violations" not in response.json()
        assert "summary" not in response.json()

    def test_malformed_token_prevents_system_reconnaissance(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify malformed tokens can't be used for system reconnaissance."""
        response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
        assert response.status_code == 401

        data = response.json()
        # Should not reveal system health information
        assert "opa_available" not in data
        assert "builtin_policies" not in data
        assert "opa_url" not in data
        assert "demo_mode" not in data

    def test_multiple_malformed_token_requests_consistent(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify multiple requests with malformed token are consistently rejected."""
        for _ in range(5):
            response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
            assert response.status_code == 401
            assert "Could not validate credentials" in response.json()["detail"]

    def test_malformed_token_error_message_consistency(
        self, test_client: TestClient, malformed_auth_headers: dict, expired_auth_headers: dict
    ):
        """Verify malformed and expired tokens return same generic error."""
        # Get response for malformed token
        malformed_response = test_client.get("/api/policy/health", headers=malformed_auth_headers)

        # Get response for expired token
        expired_response = test_client.get("/api/policy/health", headers=expired_auth_headers)

        # Both should return 401
        assert malformed_response.status_code == 401
        assert expired_response.status_code == 401

        # Both should return the same generic error message
        # (to avoid leaking information about token validity vs expiration)
        assert malformed_response.json()["detail"] == expired_response.json()["detail"]


class TestMalformedTokenEdgeCases:
    """Test edge cases and boundary conditions for malformed tokens."""

    def test_token_with_sql_injection_attempt(self, test_client: TestClient):
        """Verify SQL injection attempts in token are safely rejected."""
        sql_injection = "'; DROP TABLE users; --"
        headers = {"Authorization": f"Bearer {sql_injection}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_script_injection_attempt(self, test_client: TestClient):
        """Verify script injection attempts in token are safely rejected."""
        xss_attempt = "<script>alert('xss')</script>"
        headers = {"Authorization": f"Bearer {xss_attempt}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_path_traversal_attempt(self, test_client: TestClient):
        """Verify path traversal attempts in token are safely rejected."""
        path_traversal = "../../etc/passwd"
        headers = {"Authorization": f"Bearer {path_traversal}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_extremely_long_token(self, test_client: TestClient):
        """Verify extremely long token strings are rejected."""
        # Create a very long token string
        long_token = "a" * 10000
        headers = {"Authorization": f"Bearer {long_token}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_unicode_characters(self, test_client: TestClient):
        """Verify tokens with unicode characters are rejected."""
        unicode_token = "токен.с.юникодом"
        headers = {"Authorization": f"Bearer {unicode_token}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_null_bytes(self, test_client: TestClient):
        """Verify tokens with null bytes are rejected."""
        # Note: null bytes might be filtered by HTTP layer, but we test anyway
        null_token = "token\x00with\x00nulls"
        headers = {"Authorization": f"Bearer {null_token}"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401


class TestMalformedTokenAuthHeaderVariations:
    """Test various malformed Authorization header formats."""

    def test_missing_authorization_header(self, test_client: TestClient):
        """Verify request without Authorization header is rejected."""
        response = test_client.get("/api/policy/health")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_empty_authorization_header(self, test_client: TestClient):
        """Verify empty Authorization header is rejected."""
        headers = {"Authorization": ""}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401

    def test_authorization_header_without_scheme(self, test_client: TestClient):
        """Verify Authorization header without Bearer scheme is rejected."""
        headers = {"Authorization": "just-a-token"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401

    def test_authorization_header_with_wrong_scheme(self, test_client: TestClient):
        """Verify Authorization header with wrong scheme (not Bearer) is rejected."""
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401

    def test_authorization_header_with_multiple_tokens(self, test_client: TestClient):
        """Verify Authorization header with multiple tokens is rejected."""
        headers = {"Authorization": "Bearer token1 token2"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401

    def test_case_sensitive_bearer_scheme(self, test_client: TestClient):
        """Verify 'bearer' (lowercase) vs 'Bearer' handling."""
        # Test with lowercase 'bearer'
        headers = {"Authorization": "bearer malformed.token.here"}
        response = test_client.get("/api/policy/health", headers=headers)
        # Should still be rejected due to malformed token (Bearer is case-insensitive in HTTP)
        assert response.status_code == 401
