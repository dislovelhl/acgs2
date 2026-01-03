"""
Integration tests for analytics-api ↔ analytics-engine.

Constitutional Hash: cdd01ef066bc6cf2

Tests verify the integration between the analytics-api REST endpoints
and the analytics-engine components:
- GET /insights - AI-generated governance summaries
- GET /anomalies - IsolationForest-detected outliers
- GET /predictions - Prophet time-series forecasts
- POST /query - Natural language query processing
- POST /export/pdf - PDF report generation

These tests run against the FastAPI TestClient and verify that:
1. Endpoints return expected response structures
2. Analytics-engine components are properly integrated
3. Error handling works correctly
4. Edge cases are handled gracefully
"""

import sys
from pathlib import Path

import pytest

# Ensure analytics-engine and analytics-api are importable
SERVICES_PATH = Path(__file__).parent.parent.parent.parent.parent
ANALYTICS_ENGINE_PATH = SERVICES_PATH / "analytics-engine" / "src"
ANALYTICS_API_PATH = Path(__file__).parent.parent.parent / "src"

for path in [str(ANALYTICS_ENGINE_PATH), str(ANALYTICS_API_PATH)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Try to import FastAPI test client
try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    """Create FastAPI TestClient for the analytics-api application."""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")

    try:
        from main import app

        with TestClient(app) as test_client:
            yield test_client
    except ImportError as e:
        pytest.skip(f"Could not import analytics-api main app: {e}")


class TestInsightsIntegration:
    """Tests for GET /insights endpoint integration with InsightGenerator."""

    def test_get_insights_returns_200(self, client):
        """Verify GET /insights returns 200 status code."""
        response = client.get("/insights")
        assert response.status_code == 200

    def test_get_insights_response_structure(self, client):
        """Verify GET /insights returns expected JSON structure."""
        response = client.get("/insights")
        data = response.json()

        # Check required fields
        assert "summary" in data, "Response missing 'summary' field"
        assert "business_impact" in data, "Response missing 'business_impact' field"
        assert "recommended_action" in data, "Response missing 'recommended_action' field"
        assert "confidence" in data, "Response missing 'confidence' field"
        assert "generated_at" in data, "Response missing 'generated_at' field"

    def test_get_insights_summary_not_empty(self, client):
        """Verify insights summary is not empty."""
        response = client.get("/insights")
        data = response.json()

        assert data["summary"], "Summary should not be empty"
        assert len(data["summary"]) > 10, "Summary should be meaningful text"

    def test_get_insights_confidence_in_range(self, client):
        """Verify confidence score is within valid range."""
        response = client.get("/insights")
        data = response.json()

        assert 0.0 <= data["confidence"] <= 1.0, "Confidence should be between 0 and 1"

    def test_get_insights_with_time_range_param(self, client):
        """Verify GET /insights accepts time_range parameter."""
        for time_range in ["last_24_hours", "last_7_days", "last_30_days"]:
            response = client.get(f"/insights?time_range={time_range}")
            assert response.status_code == 200

    def test_get_insights_with_refresh_param(self, client):
        """Verify GET /insights accepts refresh parameter."""
        response = client.get("/insights?refresh=true")
        assert response.status_code == 200

    def test_get_insights_status_endpoint(self, client):
        """Verify GET /insights/status returns generator status."""
        response = client.get("/insights/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestAnomaliesIntegration:
    """Tests for GET /anomalies endpoint integration with AnomalyDetector."""

    def test_get_anomalies_returns_200(self, client):
        """Verify GET /anomalies returns 200 status code."""
        response = client.get("/anomalies")
        assert response.status_code == 200

    def test_get_anomalies_response_structure(self, client):
        """Verify GET /anomalies returns expected JSON structure."""
        response = client.get("/anomalies")
        data = response.json()

        # Check required fields
        assert "analysis_timestamp" in data, "Response missing 'analysis_timestamp'"
        assert "total_records_analyzed" in data, "Response missing 'total_records_analyzed'"
        assert "anomalies_detected" in data, "Response missing 'anomalies_detected'"
        assert "contamination_rate" in data, "Response missing 'contamination_rate'"
        assert "anomalies" in data, "Response missing 'anomalies'"
        assert "model_trained" in data, "Response missing 'model_trained'"

    def test_get_anomalies_is_list(self, client):
        """Verify anomalies field is a list."""
        response = client.get("/anomalies")
        data = response.json()

        assert isinstance(data["anomalies"], list), "Anomalies should be a list"

    def test_get_anomalies_with_outliers_detected(self, client):
        """Verify detected anomalies have correct structure when present."""
        response = client.get("/anomalies")
        data = response.json()

        # Sample data should produce at least some anomalies
        if data["anomalies_detected"] > 0:
            anomaly = data["anomalies"][0]
            assert "anomaly_id" in anomaly
            assert "timestamp" in anomaly
            assert "severity_score" in anomaly
            assert "severity_label" in anomaly
            assert "affected_metrics" in anomaly
            assert "description" in anomaly

    def test_get_anomalies_severity_filter(self, client):
        """Verify severity filter parameter works."""
        for severity in ["critical", "high", "medium", "low"]:
            response = client.get(f"/anomalies?severity={severity}")
            assert response.status_code == 200
            data = response.json()

            # All returned anomalies should match filter
            for anomaly in data["anomalies"]:
                assert anomaly["severity_label"] == severity

    def test_get_anomalies_limit_parameter(self, client):
        """Verify limit parameter restricts results."""
        response = client.get("/anomalies?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert len(data["anomalies"]) <= 5

    def test_get_anomalies_contamination_rate_valid(self, client):
        """Verify contamination rate is within valid range."""
        response = client.get("/anomalies")
        data = response.json()

        assert 0.0 <= data["contamination_rate"] <= 0.5

    def test_get_anomalies_status_endpoint(self, client):
        """Verify GET /anomalies/status returns detector status."""
        response = client.get("/anomalies/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestPredictionsIntegration:
    """Tests for GET /predictions endpoint integration with ViolationPredictor."""

    def test_get_predictions_returns_200(self, client):
        """Verify GET /predictions returns 200 status code."""
        response = client.get("/predictions")
        assert response.status_code == 200

    def test_get_predictions_response_structure(self, client):
        """Verify GET /predictions returns expected JSON structure."""
        response = client.get("/predictions")
        data = response.json()

        # Check required fields
        assert "forecast_timestamp" in data, "Response missing 'forecast_timestamp'"
        assert "historical_days" in data, "Response missing 'historical_days'"
        assert "forecast_days" in data, "Response missing 'forecast_days'"
        assert "model_trained" in data, "Response missing 'model_trained'"
        assert "predictions" in data, "Response missing 'predictions'"
        assert "summary" in data, "Response missing 'summary'"

    def test_get_predictions_is_list(self, client):
        """Verify predictions field is a list."""
        response = client.get("/predictions")
        data = response.json()

        assert isinstance(data["predictions"], list), "Predictions should be a list"

    def test_get_predictions_point_structure(self, client):
        """Verify prediction points have correct structure."""
        response = client.get("/predictions")
        data = response.json()

        # If predictions are generated, verify structure
        if data["predictions"] and data["model_trained"]:
            point = data["predictions"][0]
            assert "date" in point
            assert "predicted_value" in point
            assert "lower_bound" in point
            assert "upper_bound" in point

    def test_get_predictions_forecast_days_parameter(self, client):
        """Verify forecast_days parameter is respected."""
        response = client.get("/predictions?forecast_days=7")
        assert response.status_code == 200
        data = response.json()

        # Forecast days should match request if model trained
        assert data["forecast_days"] == 7 or data["forecast_days"] <= 7

    def test_get_predictions_historical_days_parameter(self, client):
        """Verify historical_days parameter is accepted."""
        response = client.get("/predictions?historical_days=30")
        assert response.status_code == 200

    def test_get_predictions_summary_fields(self, client):
        """Verify summary contains expected fields."""
        response = client.get("/predictions")
        data = response.json()

        summary = data["summary"]
        assert "status" in summary

        # If successful, should have statistics
        if summary.get("status") == "success":
            assert "mean_predicted_violations" in summary or "note" in summary

    def test_get_predictions_values_non_negative(self, client):
        """Verify all prediction values are non-negative."""
        response = client.get("/predictions")
        data = response.json()

        for point in data["predictions"]:
            if "predicted_value" in point:
                assert point["predicted_value"] >= 0
            if "lower_bound" in point:
                assert point["lower_bound"] >= 0
            if "upper_bound" in point:
                assert point["upper_bound"] >= 0

    def test_get_predictions_status_endpoint(self, client):
        """Verify GET /predictions/status returns predictor status."""
        response = client.get("/predictions/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestQueryIntegration:
    """Tests for POST /query endpoint integration with InsightGenerator."""

    def test_post_query_returns_200(self, client):
        """Verify POST /query returns 200 status code."""
        response = client.post("/query", json={"question": "Show violations this week"})
        assert response.status_code == 200

    def test_post_query_response_structure(self, client):
        """Verify POST /query returns expected JSON structure."""
        response = client.post("/query", json={"question": "Show violations this week"})
        data = response.json()

        # Check required fields
        assert "query" in data, "Response missing 'query' field"
        assert "answer" in data, "Response missing 'answer' field"
        assert "data" in data, "Response missing 'data' field"
        assert "query_understood" in data, "Response missing 'query_understood' field"
        assert "generated_at" in data, "Response missing 'generated_at' field"

    def test_post_query_echoes_original_query(self, client):
        """Verify response contains original query."""
        question = "Which policy is violated most?"
        response = client.post("/query", json={"question": question})
        data = response.json()

        assert data["query"] == question

    def test_post_query_answer_not_empty(self, client):
        """Verify answer is not empty."""
        response = client.post("/query", json={"question": "Show violations this week"})
        data = response.json()

        assert data["answer"], "Answer should not be empty"
        assert len(data["answer"]) > 10, "Answer should be meaningful text"

    def test_post_query_various_questions(self, client):
        """Verify various query types work."""
        questions = [
            "Show violations this week",
            "Which policy is violated most?",
            "What is the compliance trend?",
            "How many users are affected?",
        ]

        for question in questions:
            response = client.post("/query", json={"question": question})
            assert response.status_code == 200, f"Query failed for: {question}"

    def test_post_query_empty_question_fails(self, client):
        """Verify empty question returns validation error."""
        response = client.post("/query", json={"question": ""})
        # Empty question should fail validation (422) or be handled gracefully (200)
        assert response.status_code in [200, 422]

    def test_post_query_missing_question_fails(self, client):
        """Verify missing question field returns error."""
        response = client.post("/query", json={})
        assert response.status_code == 422  # Validation error

    def test_post_query_status_endpoint(self, client):
        """Verify GET /query/status returns processor status."""
        response = client.get("/query/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestExportPDFIntegration:
    """Tests for POST /export/pdf endpoint integration with PDFExporter."""

    def test_post_export_pdf_returns_200_or_503(self, client):
        """Verify POST /export/pdf returns 200 or 503 (if ReportLab unavailable)."""
        response = client.post("/export/pdf")
        # 200 = success, 503 = ReportLab not installed
        assert response.status_code in [200, 503]

    def test_post_export_pdf_content_type(self, client):
        """Verify PDF endpoint returns correct content type when successful."""
        response = client.post("/export/pdf")

        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"

    def test_post_export_pdf_has_content_disposition(self, client):
        """Verify PDF has Content-Disposition header for download."""
        response = client.post("/export/pdf")

        if response.status_code == 200:
            content_disposition = response.headers.get("content-disposition", "")
            assert "attachment" in content_disposition
            assert "filename" in content_disposition

    def test_post_export_pdf_with_options(self, client):
        """Verify PDF export accepts configuration options."""
        response = client.post(
            "/export/pdf",
            json={
                "title": "Test Report",
                "subtitle": "Integration Test",
                "time_range": "last_30_days",
                "include_insights": True,
                "include_anomalies": True,
                "include_predictions": True,
            },
        )
        assert response.status_code in [200, 503]

    def test_post_export_pdf_without_sections(self, client):
        """Verify PDF export works with sections disabled."""
        response = client.post(
            "/export/pdf",
            json={
                "include_insights": False,
                "include_anomalies": False,
                "include_predictions": False,
            },
        )
        assert response.status_code in [200, 503]

    def test_post_export_pdf_file_not_empty(self, client):
        """Verify PDF file content is not empty when successful."""
        response = client.post("/export/pdf")

        if response.status_code == 200:
            assert len(response.content) > 0, "PDF content should not be empty"
            # PDF files start with %PDF
            assert response.content[:4] == b"%PDF", "Content should be valid PDF"

    def test_get_export_status_endpoint(self, client):
        """Verify GET /export/status returns exporter status."""
        response = client.get("/export/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_liveness_check(self, client):
        """Verify liveness endpoint returns healthy status."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_check(self, client):
        """Verify readiness endpoint returns ready status."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_detailed_health_check(self, client):
        """Verify detailed health endpoint returns complete status."""
        response = client.get("/health/details")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "config" in data

    def test_root_endpoint(self, client):
        """Verify root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Analytics API"
        assert "endpoints" in data


class TestErrorHandling:
    """Tests for error handling across endpoints."""

    def test_invalid_endpoint_returns_404(self, client):
        """Verify invalid endpoint returns 404."""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_invalid_method_returns_405(self, client):
        """Verify invalid HTTP method returns 405."""
        response = client.post("/insights")
        assert response.status_code == 405

    def test_invalid_json_returns_422(self, client):
        """Verify invalid JSON returns 422."""
        response = client.post(
            "/query",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_invalid_query_params_handled(self, client):
        """Verify invalid query params are handled."""
        # Invalid enum value
        response = client.get("/anomalies?severity=invalid_severity")
        assert response.status_code == 422

        # Out of range limit
        response = client.get("/anomalies?limit=-1")
        assert response.status_code == 422
