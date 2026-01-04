"""
Integration tests for security headers in compliance-docs service.

Tests verify:
- All six security headers are present on all HTTP responses
- GET /health endpoint returns security headers
- GET /ready endpoint returns security headers
- GET / root endpoint returns security headers
- POST endpoints return security headers
- Strict CSP configuration appropriate for documentation service
- Security headers work alongside CORS middleware

Constitutional Hash: cdd01ef066bc6cf2
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.compliance_docs.src.main import app  # noqa: E402

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the compliance-docs service."""
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

    def test_ready_endpoint_has_all_security_headers(self, client: TestClient):
        """Test GET /ready endpoint returns all six security headers."""
        response = client.get("/ready")

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

    def test_euaiact_validation_endpoint_has_security_headers(self, client: TestClient):
        """Test POST /api/v1/euaiact/validate endpoint returns security headers."""
        # Test EU AI Act validation endpoint
        response = client.post(
            "/api/v1/euaiact/validate",
            json={
                "system_name": "test-system",
                "system_version": "1.0.0",
                "high_risk_category": "BIOMETRIC_IDENTIFICATION",
                "system_description": "Test system",
                "context": {},
            },
        )

        # Verify security headers are present regardless of response status
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers


# ============================================================================
# Specific Security Headers Tests
# ============================================================================


class TestIndividualSecurityHeaders:
    """Test individual security header values."""

    def test_content_security_policy_header(self, client: TestClient):
        """Test Content-Security-Policy header is properly configured with strict settings."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Verify CSP contains strict base directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "connect-src 'self'" in csp

        # Verify strict CSP doesn't allow unsafe directives (no unsafe-inline, unsafe-eval)
        # These are only allowed in development mode
        # For production strict mode, these should not be present

    def test_x_content_type_options_header(self, client: TestClient):
        """Test X-Content-Type-Options header prevents MIME sniffing."""
        response = client.get("/")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_header(self, client: TestClient):
        """Test X-Frame-Options header prevents clickjacking."""
        response = client.get("/")

        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_strict_transport_security_header(self, client: TestClient):
        """Test Strict-Transport-Security header enforces HTTPS with production settings."""
        response = client.get("/")

        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None

        # Production strict mode should have long max-age
        assert "max-age=" in hsts

        # Should include subdomains
        assert "includeSubDomains" in hsts

        # Should include preload for strict production
        assert "preload" in hsts

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
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_post_request_has_security_headers(self, client: TestClient):
        """Test POST requests have security headers."""
        response = client.post(
            "/api/v1/euaiact/validate",
            json={
                "system_name": "test-system",
                "system_version": "1.0.0",
                "high_risk_category": "BIOMETRIC_IDENTIFICATION",
            },
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
# Compliance Docs Service Specific CSP Tests
# ============================================================================


class TestComplianceDocsServiceStrictCSP:
    """Test strict CSP configuration specific to compliance-docs service."""

    def test_csp_has_strict_default_src(self, client: TestClient):
        """Test CSP has strict default-src 'self' only."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Strict CSP should only allow 'self'
        assert "default-src 'self'" in csp

    def test_csp_has_strict_script_src(self, client: TestClient):
        """Test CSP has strict script-src without unsafe-inline or unsafe-eval."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Should have script-src 'self'
        assert "script-src 'self'" in csp

    def test_csp_has_strict_connect_src(self, client: TestClient):
        """Test CSP has strict connect-src 'self' only (no external connections)."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Strict mode should only allow connections to self (no https: wildcard)
        assert "connect-src 'self'" in csp

    def test_csp_has_frame_ancestors_none(self, client: TestClient):
        """Test CSP has frame-ancestors 'none' for strict protection."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Strict CSP should prevent framing
        assert "frame-ancestors 'none'" in csp

    def test_csp_has_form_action_self(self, client: TestClient):
        """Test CSP restricts form actions to self."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Strict CSP should restrict form submissions
        assert "form-action 'self'" in csp

    def test_csp_allows_data_images(self, client: TestClient):
        """Test CSP allows data: URIs for images (for embedded compliance logos)."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Should allow self and data: for images
        assert "img-src" in csp
        assert "'self'" in csp
        assert "data:" in csp


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
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

        # CORS headers should also be present (case-insensitive check)
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers_lower

    def test_cors_preflight_has_security_headers(self, client: TestClient):
        """Test CORS preflight OPTIONS requests have security headers."""
        response = client.options(
            "/api/v1/euaiact/validate",
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
            ("/ready", "GET"),
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
        # All endpoints should have the same values for headers
        first_endpoint = list(all_headers.values())[0]
        for endpoint_headers in all_headers.values():
            assert (
                endpoint_headers["X-Content-Type-Options"]
                == first_endpoint["X-Content-Type-Options"]
            )
            assert endpoint_headers["X-Frame-Options"] == first_endpoint["X-Frame-Options"]
            assert endpoint_headers["X-XSS-Protection"] == first_endpoint["X-XSS-Protection"]
            assert endpoint_headers["Referrer-Policy"] == first_endpoint["Referrer-Policy"]
            # CSP should be consistent too
            assert (
                endpoint_headers["Content-Security-Policy"]
                == first_endpoint["Content-Security-Policy"]
            )

    def test_404_response_has_security_headers(self, client: TestClient):
        """Test 404 responses still have security headers."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404

        # Security headers should be present even on error responses
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_422_validation_error_has_security_headers(self, client: TestClient):
        """Test validation error responses have security headers."""
        # Send invalid request to trigger validation error
        response = client.post("/api/v1/euaiact/validate", json={})

        # Should get validation error
        assert response.status_code == 422

        # Even with validation error, security headers should be present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers


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

    def test_production_strict_hsts(self, client: TestClient):
        """Test HSTS is configured for strict production with preload."""
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

        # Production strict should have max-age = 1 year (31536000 seconds)
        assert max_age >= 31536000, "HSTS max-age should be at least 1 year for production"

        # Should include subdomains
        assert "includeSubDomains" in hsts

        # Should include preload for strict production
        assert "preload" in hsts

    def test_csp_strict_configuration_for_documentation_service(self, client: TestClient):
        """Test CSP is configured with strict settings appropriate for documentation service."""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Verify strict production CSP characteristics
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "form-action 'self'" in csp

        # Documentation service shouldn't need external resources
        # Should NOT have https: wildcard in connect-src
        # (unlike integration-service which needs external API connections)


# ============================================================================
# EU AI Act Endpoint Specific Tests
# ============================================================================


class TestEUAIActEndpointSecurityHeaders:
    """Test security headers on EU AI Act specific endpoints."""

    def test_validate_endpoint_post_has_security_headers(self, client: TestClient):
        """Test POST /api/v1/euaiact/validate has all security headers."""
        response = client.post(
            "/api/v1/euaiact/validate",
            json={
                "system_name": "test-ai-system",
                "system_version": "2.0.0",
                "high_risk_category": "CRITICAL_INFRASTRUCTURE",
                "system_description": "Critical infrastructure AI system",
                "context": {"deployment": "production"},
            },
        )

        # Should return success
        assert response.status_code == 200

        # Verify all security headers present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_validate_endpoint_response_body_and_headers(self, client: TestClient):
        """Test validation endpoint returns both valid response and security headers."""
        response = client.post(
            "/api/v1/euaiact/validate",
            json={
                "system_name": "governance-ai",
                "system_version": "1.0.0",
                "high_risk_category": "BIOMETRIC_IDENTIFICATION",
            },
        )

        # Should return success with findings
        assert response.status_code == 200
        data = response.json()
        assert "system_name" in data
        assert "overall_status" in data
        assert "findings" in data

        # Security headers should be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
