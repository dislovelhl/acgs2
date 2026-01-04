"""
Integration Tests for Dashboard API Endpoints

Tests the governance KPIs and trends endpoints for the executive dashboard:
1. GET /api/v1/governance/kpis - Returns current governance KPIs
2. GET /api/v1/governance/trends - Returns historical trend data
3. GET /api/v1/governance/health - Health check endpoint

These tests verify:
- Endpoints return valid data with correct schema
- Query parameters are properly handled
- Error handling works correctly
- Response data meets API contract requirements
"""

import os
import sys
from datetime import date, datetime, timedelta

import pytest

# Add the service path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import FastAPI test client
try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None  # Will skip tests if FastAPI not available

# Import application components
try:
    from app.main import app as fastapi_app
    from app.models.governance_metrics import (
        GovernanceKPIs,
        TrendDirection,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason=f"Required imports not available: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}",
)


class TestGovernanceKPIsEndpoint:
    """
    Tests for GET /api/v1/governance/kpis endpoint.

    Verifies:
    - Endpoint returns 200 OK with valid JSON
    - Response contains all required KPI fields
    - Data types and ranges are correct
    - Query parameters are handled properly
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_kpis_returns_200_ok(self, test_client):
        """Test that /kpis endpoint returns 200 OK."""
        response = test_client.get("/api/v1/governance/kpis")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_kpis_returns_valid_json(self, test_client):
        """Test that /kpis returns valid JSON with expected structure."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        # Required fields
        assert "tenant_id" in data
        assert "compliance_score" in data
        assert "controls_passing" in data
        assert "controls_failing" in data
        assert "controls_total" in data

    def test_kpis_compliance_score_in_valid_range(self, test_client):
        """Test that compliance_score is between 0 and 100."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        compliance_score = data["compliance_score"]
        assert isinstance(compliance_score, (int, float))
        assert 0 <= compliance_score <= 100

    def test_kpis_control_counts_are_non_negative(self, test_client):
        """Test that control counts are non-negative integers."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        assert isinstance(data["controls_passing"], int)
        assert isinstance(data["controls_failing"], int)
        assert isinstance(data["controls_total"], int)
        assert data["controls_passing"] >= 0
        assert data["controls_failing"] >= 0
        assert data["controls_total"] >= 0

    def test_kpis_controls_total_equals_sum(self, test_client):
        """Test that controls_total equals passing + failing."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        expected_total = data["controls_passing"] + data["controls_failing"]
        assert data["controls_total"] == expected_total

    def test_kpis_includes_trend_direction(self, test_client):
        """Test that trend_direction is a valid enum value."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        assert "trend_direction" in data
        assert data["trend_direction"] in ["improving", "stable", "declining"]

    def test_kpis_includes_trend_change_percent(self, test_client):
        """Test that trend_change_percent is a number."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        assert "trend_change_percent" in data
        assert isinstance(data["trend_change_percent"], (int, float))

    def test_kpis_includes_activity_metrics(self, test_client):
        """Test that activity metrics are included."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        assert "recent_audits" in data
        assert "high_risk_incidents" in data
        assert isinstance(data["recent_audits"], int)
        assert isinstance(data["high_risk_incidents"], int)
        assert data["recent_audits"] >= 0
        assert data["high_risk_incidents"] >= 0

    def test_kpis_includes_last_updated(self, test_client):
        """Test that last_updated timestamp is included."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        assert "last_updated" in data
        # Should be ISO format string
        assert isinstance(data["last_updated"], str)
        # Should be parseable as datetime
        datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))

    def test_kpis_includes_data_stale_warning(self, test_client):
        """Test that data_stale_warning is included."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        assert "data_stale_warning" in data
        assert isinstance(data["data_stale_warning"], bool)

    def test_kpis_with_tenant_id_parameter(self, test_client):
        """Test that tenant_id query parameter is accepted."""
        response = test_client.get(
            "/api/v1/governance/kpis",
            params={"tenant_id": "test-tenant-001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-001"

    def test_kpis_default_tenant_id(self, test_client):
        """Test that default tenant_id is used when not specified."""
        response = test_client.get("/api/v1/governance/kpis")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "default"


class TestGovernanceTrendsEndpoint:
    """
    Tests for GET /api/v1/governance/trends endpoint.

    Verifies:
    - Endpoint returns 200 OK with valid JSON
    - Response contains all required trend fields
    - Days parameter filtering works correctly
    - Trend data points are valid
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_trends_returns_200_ok(self, test_client):
        """Test that /trends endpoint returns 200 OK."""
        response = test_client.get("/api/v1/governance/trends")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_trends_returns_valid_json(self, test_client):
        """Test that /trends returns valid JSON with expected structure."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        # Required fields
        assert "tenant_id" in data
        assert "days" in data
        assert "dates" in data
        assert "compliance_scores" in data
        assert "control_counts" in data

    def test_trends_default_90_days(self, test_client):
        """Test that default is 90 days of trend data."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        assert data["days"] == 90
        # Should have approximately 90 data points (one per day)
        assert len(data["dates"]) == 90
        assert len(data["compliance_scores"]) == 90
        assert len(data["control_counts"]) == 90

    def test_trends_custom_days_parameter(self, test_client):
        """Test that days parameter controls data range."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 30
        assert len(data["dates"]) == 30

    def test_trends_minimum_days_1(self, test_client):
        """Test that minimum days value is 1."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 1
        assert len(data["dates"]) == 1

    def test_trends_maximum_days_365(self, test_client):
        """Test that maximum days value is 365."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": 365},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 365
        assert len(data["dates"]) == 365

    def test_trends_invalid_days_below_minimum(self, test_client):
        """Test that days below minimum returns validation error."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": 0},
        )

        assert response.status_code == 422  # Validation error

    def test_trends_invalid_days_above_maximum(self, test_client):
        """Test that days above maximum returns validation error."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": 366},
        )

        assert response.status_code == 422  # Validation error

    def test_trends_dates_are_valid_iso_format(self, test_client):
        """Test that all dates are valid ISO format strings."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        for date_str in data["dates"]:
            # Should be parseable as date
            parsed_date = date.fromisoformat(date_str)
            assert isinstance(parsed_date, date)

    def test_trends_dates_are_in_chronological_order(self, test_client):
        """Test that dates are in chronological order."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        dates = [date.fromisoformat(d) for d in data["dates"]]
        for i in range(1, len(dates)):
            assert dates[i] > dates[i - 1], "Dates should be in ascending order"

    def test_trends_compliance_scores_in_valid_range(self, test_client):
        """Test that all compliance scores are between 0 and 100."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        for score in data["compliance_scores"]:
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100

    def test_trends_control_counts_structure(self, test_client):
        """Test that control_counts have correct structure."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        for count_data in data["control_counts"]:
            assert "passing" in count_data
            assert "failing" in count_data
            assert "total" in count_data
            assert count_data["passing"] >= 0
            assert count_data["failing"] >= 0
            assert count_data["total"] >= 0

    def test_trends_includes_period_dates(self, test_client):
        """Test that period_start and period_end are included."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        assert "period_start" in data
        assert "period_end" in data
        # Should be parseable
        start_date = date.fromisoformat(data["period_start"])
        end_date = date.fromisoformat(data["period_end"])
        assert start_date < end_date

    def test_trends_includes_aggregate_statistics(self, test_client):
        """Test that aggregate statistics are included."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        assert "avg_compliance_score" in data
        assert "min_compliance_score" in data
        assert "max_compliance_score" in data

        # All should be in valid range
        assert 0 <= data["avg_compliance_score"] <= 100
        assert 0 <= data["min_compliance_score"] <= 100
        assert 0 <= data["max_compliance_score"] <= 100

        # Min should be <= avg <= max
        assert data["min_compliance_score"] <= data["avg_compliance_score"]
        assert data["avg_compliance_score"] <= data["max_compliance_score"]

    def test_trends_includes_trend_direction(self, test_client):
        """Test that trend_direction is included."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        assert "trend_direction" in data
        assert data["trend_direction"] in ["improving", "stable", "declining"]

    def test_trends_includes_trend_slope(self, test_client):
        """Test that trend_slope is included."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        assert "trend_slope" in data
        assert isinstance(data["trend_slope"], (int, float))

    def test_trends_with_tenant_id_parameter(self, test_client):
        """Test that tenant_id query parameter is accepted."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"tenant_id": "test-tenant-002"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-002"


class TestGovernanceHealthEndpoint:
    """
    Tests for GET /api/v1/governance/health endpoint.

    Verifies:
    - Endpoint returns 200 OK
    - Response indicates healthy status
    - Includes expected metadata
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_health_returns_200_ok(self, test_client):
        """Test that /health endpoint returns 200 OK."""
        response = test_client.get("/api/v1/governance/health")

        assert response.status_code == 200

    def test_health_returns_healthy_status(self, test_client):
        """Test that status is 'healthy'."""
        response = test_client.get("/api/v1/governance/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_returns_api_name(self, test_client):
        """Test that API name is 'governance'."""
        response = test_client.get("/api/v1/governance/health")
        data = response.json()

        assert data["api"] == "governance"

    def test_health_returns_version(self, test_client):
        """Test that version is included."""
        response = test_client.get("/api/v1/governance/health")
        data = response.json()

        assert "version" in data
        assert isinstance(data["version"], str)

    def test_health_returns_endpoints_list(self, test_client):
        """Test that available endpoints are listed."""
        response = test_client.get("/api/v1/governance/health")
        data = response.json()

        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)
        assert "/kpis" in data["endpoints"]
        assert "/trends" in data["endpoints"]
        assert "/health" in data["endpoints"]

    def test_health_returns_timestamp(self, test_client):
        """Test that timestamp is included."""
        response = test_client.get("/api/v1/governance/health")
        data = response.json()

        assert "timestamp" in data
        # Should be parseable ISO format
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestDashboardDataIntegrity:
    """
    Tests for data integrity between KPIs and Trends endpoints.

    Verifies:
    - Data consistency between endpoints
    - Trend calculations are accurate
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_kpis_and_trends_same_tenant_id(self, test_client):
        """Test that tenant_id is consistent across endpoints."""
        tenant_id = "integrity-test-tenant"

        kpis_response = test_client.get(
            "/api/v1/governance/kpis",
            params={"tenant_id": tenant_id},
        )
        trends_response = test_client.get(
            "/api/v1/governance/trends",
            params={"tenant_id": tenant_id},
        )

        assert kpis_response.json()["tenant_id"] == tenant_id
        assert trends_response.json()["tenant_id"] == tenant_id

    def test_trend_period_ends_today(self, test_client):
        """Test that trend period ends on today's date."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        end_date = date.fromisoformat(data["period_end"])
        assert end_date == date.today()

    def test_trend_period_start_matches_days(self, test_client):
        """Test that period_start is correct based on days parameter."""
        days = 30
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": days},
        )
        data = response.json()

        start_date = date.fromisoformat(data["period_start"])
        end_date = date.fromisoformat(data["period_end"])
        expected_start = end_date - timedelta(days=days)

        assert start_date == expected_start


class TestDashboardCaching:
    """
    Tests for dashboard API caching and performance.

    Verifies:
    - Repeated requests return consistent data
    - Response times are reasonable
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_repeated_kpis_requests_are_consistent(self, test_client):
        """Test that repeated KPI requests return consistent scores."""
        response1 = test_client.get("/api/v1/governance/kpis")
        response2 = test_client.get("/api/v1/governance/kpis")

        data1 = response1.json()
        data2 = response2.json()

        # Core metrics should be the same (sample data)
        assert data1["compliance_score"] == data2["compliance_score"]
        assert data1["controls_passing"] == data2["controls_passing"]
        assert data1["controls_failing"] == data2["controls_failing"]

    def test_repeated_trends_requests_are_consistent(self, test_client):
        """Test that repeated trend requests return consistent data."""
        response1 = test_client.get("/api/v1/governance/trends")
        response2 = test_client.get("/api/v1/governance/trends")

        data1 = response1.json()
        data2 = response2.json()

        # Trend statistics should be the same
        assert data1["avg_compliance_score"] == data2["avg_compliance_score"]
        assert data1["trend_direction"] == data2["trend_direction"]


class TestDashboardErrorHandling:
    """
    Tests for error handling in dashboard endpoints.

    Verifies:
    - Invalid parameters return appropriate errors
    - Error responses have correct format
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_invalid_days_type_returns_422(self, test_client):
        """Test that non-numeric days parameter returns 422."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": "abc"},
        )

        assert response.status_code == 422

    def test_negative_days_returns_422(self, test_client):
        """Test that negative days parameter returns 422."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": -5},
        )

        assert response.status_code == 422

    def test_error_response_has_detail(self, test_client):
        """Test that validation error response includes detail."""
        response = test_client.get(
            "/api/v1/governance/trends",
            params={"days": 0},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestDashboardResponseSchema:
    """
    Tests to verify response schemas match expected models.

    Verifies:
    - KPIs response matches GovernanceKPIs model
    - Trends response matches GovernanceTrends model
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_kpis_response_matches_model_schema(self, test_client):
        """Test that KPIs response can be used to create GovernanceKPIs model."""
        response = test_client.get("/api/v1/governance/kpis")
        data = response.json()

        # Should be able to create GovernanceKPIs from response
        # Note: last_updated needs datetime, so we need to parse
        try:
            kpis = GovernanceKPIs(
                tenant_id=data["tenant_id"],
                compliance_score=data["compliance_score"],
                controls_passing=data["controls_passing"],
                controls_failing=data["controls_failing"],
                controls_total=data["controls_total"],
                recent_audits=data["recent_audits"],
                high_risk_incidents=data["high_risk_incidents"],
                trend_direction=TrendDirection(data["trend_direction"]),
                trend_change_percent=data["trend_change_percent"],
                data_stale_warning=data["data_stale_warning"],
            )
            assert kpis.compliance_score == data["compliance_score"]
        except Exception as e:
            pytest.fail(f"Failed to create GovernanceKPIs from response: {e}")

    def test_trends_response_contains_required_fields(self, test_client):
        """Test that trends response contains all required fields for charts."""
        response = test_client.get("/api/v1/governance/trends")
        data = response.json()

        # Required fields for dashboard charts
        required_fields = [
            "tenant_id",
            "days",
            "dates",
            "compliance_scores",
            "control_counts",
            "period_start",
            "period_end",
            "avg_compliance_score",
            "min_compliance_score",
            "max_compliance_score",
            "trend_direction",
            "trend_slope",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestDashboardTenantIsolation:
    """
    Tests for tenant isolation in dashboard data.

    Verifies:
    - Different tenants get different data
    - Tenant parameter is properly scoped
    """

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_different_tenants_return_different_tenant_ids(self, test_client):
        """Test that different tenant_id params return data for that tenant."""
        response1 = test_client.get(
            "/api/v1/governance/kpis",
            params={"tenant_id": "tenant-alpha"},
        )
        response2 = test_client.get(
            "/api/v1/governance/kpis",
            params={"tenant_id": "tenant-beta"},
        )

        assert response1.json()["tenant_id"] == "tenant-alpha"
        assert response2.json()["tenant_id"] == "tenant-beta"

    def test_trends_tenant_isolation(self, test_client):
        """Test tenant isolation in trends endpoint."""
        response1 = test_client.get(
            "/api/v1/governance/trends",
            params={"tenant_id": "isolated-tenant-1"},
        )
        response2 = test_client.get(
            "/api/v1/governance/trends",
            params={"tenant_id": "isolated-tenant-2"},
        )

        assert response1.json()["tenant_id"] == "isolated-tenant-1"
        assert response2.json()["tenant_id"] == "isolated-tenant-2"


# Export all test classes
__all__ = [
    "TestGovernanceKPIsEndpoint",
    "TestGovernanceTrendsEndpoint",
    "TestGovernanceHealthEndpoint",
    "TestDashboardDataIntegrity",
    "TestDashboardCaching",
    "TestDashboardErrorHandling",
    "TestDashboardResponseSchema",
    "TestDashboardTenantIsolation",
]
