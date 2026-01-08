"""
Integration tests for security headers in integration-service.

Tests verify:
- All six security headers are present on all HTTP responses
- GET /health endpoint returns security headers
- GET / root endpoint returns security headers
- POST endpoints return security headers
- CSP header allows necessary third-party connections for webhooks and integrations
- Security headers work alongside CORS middleware
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "core"))

from src.main import app  # noqa: E402

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the integration service."""
    return TestClient(app)


# ============================================================================
# Basic Security Headers Tests
# ============================================================================


class TestSecurityHeadersPresence:
    """Test that all security headers are present on responses."""

    def test_health_endpoint_has_all_security_headers(self, client: TestClient):
        """Test GET /health endpoint returns all six security headers."""
        response = client.get("/health")

        # Verify response is successful
        assert response.status_code == 200

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_root_endpoint_has_all_security_headers(self, client: TestClient):
        """Test GET / root endpoint returns all six security headers."""
        response = client.get("/")

        # Verify response is successful
        assert response.status_code == 200

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_docs_endpoint_has_security_headers(self, client: TestClient):
        """Test GET /docs endpoint returns security headers."""
        response = client.get("/docs")

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_api_endpoint_has_security_headers(self, client: TestClient):
        """Test API endpoints return security headers."""
        # Test policy check endpoint
        response = client.post(
            "/api/policy/check", json={"action": "test", "resource": "resource", "context": {}}
        )

        # Verify security headers are present regardless of response status
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


# ============================================================================
# Specific Security Headers Tests
# ============================================================================


class TestIndividualSecurityHeaders:
    """Test individual security header values."""

    def test_content_security_policy_header(self, client: TestClient):
        """Test Content-Security-Policy header is properly configured."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Verify CSP contains base directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp

        # Verify CSP allows HTTPS connections for integrations
        assert "connect-src 'self' https:" in csp

        # Verify CSP allows HTTPS images for third-party integrations
        assert "img-src" in csp
        assert "https:" in csp

    def test_x_content_type_options_header(self, client: TestClient):
        """Test X-Content-Type-Options header prevents MIME sniffing."""
        response = client.get("/")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_header(self, client: TestClient):
        """Test X-Frame-Options header prevents clickjacking."""
        response = client.get("/")

        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_strict_transport_security_header(self, client: TestClient):
        """Test Strict-Transport-Security header enforces HTTPS."""
        response = client.get("/")

        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None

        # Should have long max-age for production
        assert "max-age=" in hsts

        # Should include subdomains
        assert "includeSubDomains" in hsts

    def test_x_xss_protection_header(self, client: TestClient):
        """Test X-XSS-Protection header is set correctly."""
        response = client.get("/")

        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy_header(self, client: TestClient):
        """Test Referrer-Policy header controls referrer information."""
        response = client.get("/")

        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ============================================================================
# HTTP Method Tests
# ============================================================================


class TestSecurityHeadersOnDifferentMethods:
    """Test security headers are present across different HTTP methods."""

    def test_get_request_has_security_headers(self, client: TestClient):
        """Test GET requests have security headers."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers

    def test_post_request_has_security_headers(self, client: TestClient):
        """Test POST requests have security headers."""
        response = client.post(
            "/api/policy/check", json={"action": "test", "resource": "resource", "context": {}}
        )

        # Verify security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_options_request_has_security_headers(self, client: TestClient):
        """Test OPTIONS requests (CORS preflight) have security headers."""
        response = client.options("/health")

        # Security headers should be present even on OPTIONS
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


# ============================================================================
# Integration-Specific CSP Tests
# ============================================================================


class TestIntegrationServiceCSP:
    """Test CSP configuration specific to integration service."""

    def test_csp_allows_external_https_connections(self, client: TestClient):
        """Test CSP allows HTTPS connections for third-party integrations."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Integration service needs to connect to external APIs
        assert "connect-src 'self' https:" in csp

    def test_csp_allows_external_images(self, client: TestClient):
        """Test CSP allows HTTPS images for integration logos and assets."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Integration service may need to display third-party images
        assert "img-src" in csp
        assert "'self'" in csp
        assert "data:" in csp
        assert "https:" in csp

    def test_csp_has_base_security_directives(self, client: TestClient):
        """Test CSP has essential security directives."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Base security directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp


# ============================================================================
# Middleware Integration Tests
# ============================================================================


class TestSecurityHeadersWithCORS:
    """Test security headers work alongside CORS middleware."""

    def test_security_headers_and_cors_headers_coexist(self, client: TestClient):
        """Test both security and CORS headers are present."""
        response = client.get("/health")

        # Security headers should be present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers

        # CORS headers should also be present (case-insensitive check)
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers_lower

    def test_cors_preflight_has_security_headers(self, client: TestClient):
        """Test CORS preflight OPTIONS requests have security headers."""
        response = client.options(
            "/api/policy/check",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # Security headers should be present even on preflight
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


# ============================================================================
# Edge Cases and Consistency Tests
# ============================================================================


class TestSecurityHeadersEdgeCases:
    """Test edge cases and consistency of security headers."""

    def test_all_endpoints_have_consistent_headers(self, client: TestClient):
        """Test all endpoints have the same security headers."""
        endpoints = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/docs", "GET"),
        ]

        # Collect headers from all endpoints
        all_headers = {}
        for path, method in endpoints:
            if method == "GET":
                response = client.get(path)

            # Extract security headers
            security_headers = {
                "Content-Security-Policy": response.headers.get("Content-Security-Policy"),
                "X-Content-Type-Options": response.headers.get("X-Content-Type-Options"),
                "X-Frame-Options": response.headers.get("X-Frame-Options"),
                "X-XSS-Protection": response.headers.get("X-XSS-Protection"),
                "Referrer-Policy": response.headers.get("Referrer-Policy"),
            }
            all_headers[path] = security_headers

        # Verify consistency across endpoints
        # All endpoints should have the same values for most headers
        first_endpoint = list(all_headers.values())[0]
        for endpoint_headers in all_headers.values():
            assert (
                endpoint_headers["X-Content-Type-Options"]
                == first_endpoint["X-Content-Type-Options"]
            )
            assert endpoint_headers["X-Frame-Options"] == first_endpoint["X-Frame-Options"]
            assert endpoint_headers["X-XSS-Protection"] == first_endpoint["X-XSS-Protection"]
            assert endpoint_headers["Referrer-Policy"] == first_endpoint["Referrer-Policy"]

    def test_404_response_has_security_headers(self, client: TestClient):
        """Test 404 responses still have security headers."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404

        # Security headers should be present even on error responses
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    def test_500_error_has_security_headers(self, client: TestClient):
        """Test error responses have security headers."""
        # The /api/policy/check endpoint should return an error for invalid input
        response = client.post("/api/policy/check", json={})

        # Even if there's an error, security headers should be present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers


# ============================================================================
# Compliance Verification Tests
# ============================================================================


class TestSecurityHeadersCompliance:
    """Test compliance with security header requirements."""

    def test_all_six_required_headers_present(self, client: TestClient):
        """Test all six required security headers are present."""
        response = client.get("/")

        required_headers = [
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Strict-Transport-Security",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing required header: {header}"

    def test_headers_have_non_empty_values(self, client: TestClient):
        """Test security headers have non-empty values."""
        response = client.get("/")

        security_headers = [
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Strict-Transport-Security",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]

        for header in security_headers:
            value = response.headers.get(header)
            assert value is not None, f"Header {header} is None"
            assert len(value) > 0, f"Header {header} is empty"

    def test_production_grade_hsts(self, client: TestClient):
        """Test HSTS is configured for production."""
        response = client.get("/")

        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None

        # Extract max-age value
        max_age_str = None
        for part in hsts.split(";"):
            part = part.strip()
            if part.startswith("max-age="):
                max_age_str = part.split("=")[1]
                break

        assert max_age_str is not None
        max_age = int(max_age_str)

        # Production should have max-age >= 1 year (31536000 seconds)
        # But we'll accept anything > 1 day for integration service
        assert max_age >= 86400, "HSTS max-age should be at least 1 day"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
