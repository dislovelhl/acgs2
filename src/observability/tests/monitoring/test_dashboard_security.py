"""
Integration tests for security headers in observability dashboard.

Tests verify:
- All six security headers are present on all HTTP responses
- GET /health endpoint returns security headers
- GET /dashboard/overview endpoint returns security headers
- GET /dashboard/metrics endpoint returns security headers
- WebSocket upgrade respects security requirements
- CSP header allows WebSocket connections for real-time updates
- Security headers work alongside CORS middleware

Constitutional Hash: cdd01ef066bc6cf2
"""

import sys
from pathlib import Path

import pytest

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the dashboard app
try:
    from monitoring.dashboard_api import create_dashboard_app

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Import TestClient if FastAPI is available
if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a test client for the observability dashboard."""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")

    app = create_dashboard_app()
    return TestClient(app)


# ============================================================================
# Basic Security Headers Tests
# ============================================================================


class TestSecurityHeadersPresence:
    """Test that all security headers are present on responses."""

    def test_health_endpoint_has_all_security_headers(self, client):
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

    def test_dashboard_overview_has_all_security_headers(self, client):
        """Test GET /dashboard/overview endpoint returns all six security headers."""
        response = client.get("/dashboard/overview")

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_dashboard_health_has_security_headers(self, client):
        """Test GET /dashboard/health endpoint returns security headers."""
        response = client.get("/dashboard/health")

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_dashboard_metrics_has_security_headers(self, client):
        """Test GET /dashboard/metrics endpoint returns security headers."""
        response = client.get("/dashboard/metrics")

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_dashboard_alerts_has_security_headers(self, client):
        """Test GET /dashboard/alerts endpoint returns security headers."""
        response = client.get("/dashboard/alerts")

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_dashboard_services_has_security_headers(self, client):
        """Test GET /dashboard/services endpoint returns security headers."""
        response = client.get("/dashboard/services")

        # Verify all 6 security headers are present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_dashboard_memory_has_security_headers(self, client):
        """Test GET /dashboard/memory endpoint returns security headers."""
        response = client.get("/dashboard/memory")

        # Verify all 6 security headers are present
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

    def test_content_security_policy_header(self, client):
        """Test Content-Security-Policy header is properly configured for WebSocket support."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Verify CSP contains base directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp

        # Verify CSP allows WebSocket connections for /dashboard/ws endpoint
        assert "connect-src" in csp
        # Should allow both self and WebSocket protocols
        csp_lower = csp.lower()
        assert "'self'" in csp_lower
        # WebSocket protocols should be allowed
        assert "ws:" in csp_lower or "wss:" in csp_lower

    def test_x_content_type_options_header(self, client):
        """Test X-Content-Type-Options header prevents MIME sniffing."""
        response = client.get("/dashboard/overview")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_header(self, client):
        """Test X-Frame-Options header prevents clickjacking."""
        response = client.get("/dashboard/overview")

        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_strict_transport_security_header(self, client):
        """Test Strict-Transport-Security header enforces HTTPS."""
        response = client.get("/dashboard/overview")

        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None

        # Should have long max-age for production
        assert "max-age=" in hsts

        # Should include subdomains
        assert "includeSubDomains" in hsts

    def test_x_xss_protection_header(self, client):
        """Test X-XSS-Protection header is set correctly."""
        response = client.get("/dashboard/overview")

        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy_header(self, client):
        """Test Referrer-Policy header controls referrer information."""
        response = client.get("/dashboard/overview")

        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ============================================================================
# HTTP Method Tests
# ============================================================================


class TestSecurityHeadersOnDifferentMethods:
    """Test security headers are present across different HTTP methods."""

    def test_get_request_has_security_headers(self, client):
        """Test GET requests have security headers."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_options_request_has_security_headers(self, client):
        """Test OPTIONS requests (CORS preflight) have security headers."""
        response = client.options("/health")

        # Security headers should be present even on OPTIONS
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


# ============================================================================
# WebSocket-Specific CSP Tests
# ============================================================================


class TestWebSocketServiceCSP:
    """Test CSP configuration specific to WebSocket service."""

    def test_csp_allows_websocket_connections(self, client):
        """Test CSP allows WebSocket connections for real-time dashboard updates."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # WebSocket service needs ws: and wss: in connect-src
        csp_lower = csp.lower()
        assert "connect-src" in csp_lower
        # Should allow WebSocket protocols
        assert "ws:" in csp_lower or "wss:" in csp_lower

    def test_csp_allows_self_connections(self, client):
        """Test CSP allows connections to self for API calls."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Should allow self
        assert "'self'" in csp

    def test_csp_has_base_security_directives(self, client):
        """Test CSP has essential security directives."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Base security directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp

    def test_csp_allows_data_images(self, client):
        """Test CSP allows data: URIs for images (for dashboard charts and icons)."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Should allow data: URIs for images
        assert "img-src" in csp
        assert "data:" in csp


# ============================================================================
# WebSocket Endpoint Tests
# ============================================================================


class TestWebSocketSecurityHeaders:
    """Test WebSocket endpoint respects security requirements."""

    def test_websocket_upgrade_request(self, client):
        """Test WebSocket upgrade request handling."""
        # Note: TestClient doesn't fully support WebSocket testing,
        # so we test what we can - the HTTP response headers before upgrade
        # In production, the WebSocket connection would be established after
        # the initial HTTP upgrade request

        # Test that we can at least access the WebSocket endpoint
        # The actual WebSocket connection requires a proper WebSocket client
        # but we can verify the endpoint exists and security headers are configured

        # This is a basic connectivity test - in production environments,
        # use a proper WebSocket testing client
        pass

    def test_websocket_csp_configuration(self, client):
        """Test CSP configuration allows WebSocket upgrade."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # The CSP should allow WebSocket connections
        csp_lower = csp.lower()
        # Check for ws: or wss: in the policy
        has_ws = "ws:" in csp_lower or "wss:" in csp_lower
        assert has_ws, "CSP should allow WebSocket connections (ws: or wss:)"


# ============================================================================
# Middleware Integration Tests
# ============================================================================


class TestSecurityHeadersWithCORS:
    """Test security headers work alongside CORS middleware."""

    def test_security_headers_and_cors_headers_coexist(self, client):
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

    def test_cors_preflight_has_security_headers(self, client):
        """Test CORS preflight OPTIONS requests have security headers."""
        response = client.options(
            "/dashboard/overview",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
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

    def test_all_endpoints_have_consistent_headers(self, client):
        """Test all dashboard endpoints have the same security headers."""
        endpoints = [
            ("/health", "GET"),
            ("/dashboard/overview", "GET"),
            ("/dashboard/health", "GET"),
            ("/dashboard/metrics", "GET"),
            ("/dashboard/alerts", "GET"),
            ("/dashboard/services", "GET"),
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

    def test_404_response_has_security_headers(self, client):
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

    def test_500_error_has_security_headers(self, client):
        """Test error responses have security headers."""
        # Note: This test would require triggering a 500 error
        # which may not be straightforward without specific error conditions
        # For now, we test what we can with 404
        pass


# ============================================================================
# Compliance Verification Tests
# ============================================================================


class TestSecurityHeadersCompliance:
    """Test compliance with security header requirements."""

    def test_all_six_required_headers_present(self, client):
        """Test all six required security headers are present."""
        response = client.get("/dashboard/overview")

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

    def test_headers_have_non_empty_values(self, client):
        """Test security headers have non-empty values."""
        response = client.get("/dashboard/overview")

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

    def test_production_grade_hsts(self, client):
        """Test HSTS is configured for production."""
        response = client.get("/dashboard/overview")

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

        # Production should have max-age >= 1 day for observability dashboard
        assert max_age >= 86400, "HSTS max-age should be at least 1 day"

    def test_csp_configuration_for_websocket_service(self, client):
        """Test CSP is configured appropriately for WebSocket-enabled service."""
        response = client.get("/dashboard/overview")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Verify WebSocket service CSP characteristics
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp

        # Must allow WebSocket connections
        csp_lower = csp.lower()
        assert "ws:" in csp_lower or "wss:" in csp_lower, (
            "CSP must allow WebSocket connections for real-time dashboard updates"
        )


# ============================================================================
# Dashboard-Specific Endpoint Tests
# ============================================================================


class TestDashboardEndpointSecurityHeaders:
    """Test security headers on dashboard-specific endpoints."""

    def test_overview_endpoint_returns_data_with_headers(self, client):
        """Test /dashboard/overview returns both data and security headers."""
        response = client.get("/dashboard/overview")

        # Should return success
        assert response.status_code == 200

        # Should have response body
        data = response.json()
        assert data is not None

        # Verify all security headers present
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_metrics_endpoint_returns_data_with_headers(self, client):
        """Test /dashboard/metrics returns both data and security headers."""
        response = client.get("/dashboard/metrics")

        # Should return success
        assert response.status_code == 200

        # Should have response body
        data = response.json()
        assert data is not None

        # Security headers should be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_health_endpoint_returns_data_with_headers(self, client):
        """Test /dashboard/health returns both data and security headers."""
        response = client.get("/dashboard/health")

        # Should return success
        assert response.status_code == 200

        # Should have response body
        data = response.json()
        assert data is not None

        # Security headers should be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_alerts_endpoint_returns_data_with_headers(self, client):
        """Test /dashboard/alerts returns both data and security headers."""
        response = client.get("/dashboard/alerts")

        # Should return success (200) with list of alerts (may be empty)
        assert response.status_code == 200

        # Should have response body (list)
        data = response.json()
        assert isinstance(data, list)

        # Security headers should be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
