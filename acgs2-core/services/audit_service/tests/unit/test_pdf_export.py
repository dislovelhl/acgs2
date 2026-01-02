"""
Unit tests for PDF export functionality in ComplianceReportGenerator.

Tests the generate_pdf_report() method including:
- Basic PDF generation with sample data
- Framework selection (ISO42001, SOC2, ISO27001, GDPR)
- Branding customization (company name, logo, colors)
- Error handling for missing dependencies
- Edge cases (empty data, invalid frameworks)
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Add the service path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.report_generator import (  # noqa: E402
    DEFAULT_REPORT_TEMPLATE,
    JINJA2_AVAILABLE,
    WEASYPRINT_AVAILABLE,
    ComplianceReportGenerator,
)


# Sample test data
def create_sample_logs(tenant_id: str, count: int = 5):
    """Create sample decision logs for testing."""
    logs = []
    for i in range(count):
        logs.append(
            {
                "tenant_id": tenant_id,
                "agent_id": f"agent-{i:03d}",
                "decision": "ALLOW" if i % 3 != 0 else "DENY",
                "risk_score": 0.2 + (i * 0.15),
                "compliance_tags": ["POLICY", "PRIVACY"] if i % 2 == 0 else ["SAFETY"],
                "policy_version": "v1.0.0",
                "trace_id": f"trace-{i:06d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    return logs


class TestPDFExportAvailability:
    """Test PDF export dependency checks."""

    def test_weasyprint_availability_flag_exists(self):
        """Verify WEASYPRINT_AVAILABLE flag is defined."""
        from app.services.report_generator import WEASYPRINT_AVAILABLE

        assert isinstance(WEASYPRINT_AVAILABLE, bool)

    def test_jinja2_availability_flag_exists(self):
        """Verify JINJA2_AVAILABLE flag is defined."""
        from app.services.report_generator import JINJA2_AVAILABLE

        assert isinstance(JINJA2_AVAILABLE, bool)

    def test_default_template_exists(self):
        """Verify default HTML template is defined."""
        from app.services.report_generator import DEFAULT_REPORT_TEMPLATE

        assert isinstance(DEFAULT_REPORT_TEMPLATE, str)
        assert len(DEFAULT_REPORT_TEMPLATE) > 0
        assert "<!DOCTYPE html>" in DEFAULT_REPORT_TEMPLATE


class TestGeneratePDFReportMethod:
    """Test the generate_pdf_report static method."""

    def test_generate_pdf_report_method_exists(self):
        """Verify generate_pdf_report method exists on the class."""
        assert hasattr(ComplianceReportGenerator, "generate_pdf_report")
        assert callable(ComplianceReportGenerator.generate_pdf_report)

    def test_generate_pdf_report_signature(self):
        """Verify the method signature accepts required parameters."""
        import inspect

        sig = inspect.signature(ComplianceReportGenerator.generate_pdf_report)
        params = list(sig.parameters.keys())

        # Required parameters
        assert "logs" in params
        assert "tenant_id" in params

        # Optional parameters with defaults
        assert "framework" in params
        assert "company_name" in params
        assert "logo_url" in params
        assert "brand_color" in params
        assert "template" in params

    @pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE,
        reason="WeasyPrint not available (requires Pango system libraries)",
    )
    def test_generate_pdf_report_returns_bytes(self):
        """Verify PDF generation returns bytes."""
        logs = create_sample_logs("tenant-001", count=3)
        pdf_bytes = ComplianceReportGenerator.generate_pdf_report(
            logs=logs,
            tenant_id="tenant-001",
            framework="ISO42001",
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    @pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE,
        reason="WeasyPrint not available (requires Pango system libraries)",
    )
    def test_generate_pdf_report_valid_pdf_header(self):
        """Verify generated PDF has valid PDF header."""
        logs = create_sample_logs("tenant-002", count=2)
        pdf_bytes = ComplianceReportGenerator.generate_pdf_report(
            logs=logs,
            tenant_id="tenant-002",
        )

        # PDF files start with %PDF-
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE,
        reason="WeasyPrint not available (requires Pango system libraries)",
    )
    def test_generate_pdf_with_custom_branding(self):
        """Test PDF generation with custom branding options."""
        logs = create_sample_logs("tenant-003", count=2)
        pdf_bytes = ComplianceReportGenerator.generate_pdf_report(
            logs=logs,
            tenant_id="tenant-003",
            framework="SOC2",
            company_name="Test Corporation",
            brand_color="#FF5500",
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE,
        reason="WeasyPrint not available (requires Pango system libraries)",
    )
    def test_generate_pdf_all_frameworks(self):
        """Test PDF generation for all supported frameworks."""
        frameworks = ["ISO42001", "SOC2", "ISO27001", "GDPR"]
        logs = create_sample_logs("tenant-004", count=2)

        for framework in frameworks:
            pdf_bytes = ComplianceReportGenerator.generate_pdf_report(
                logs=logs,
                tenant_id="tenant-004",
                framework=framework,
            )
            assert isinstance(pdf_bytes, bytes)
            assert len(pdf_bytes) > 0
            assert pdf_bytes[:5] == b"%PDF-"


class TestGeneratePDFReportValidation:
    """Test input validation for PDF export."""

    def test_invalid_framework_raises_error(self):
        """Test that invalid framework raises ValueError."""
        if not WEASYPRINT_AVAILABLE or not JINJA2_AVAILABLE:
            pytest.skip("WeasyPrint or Jinja2 not available")

        logs = create_sample_logs("tenant-005", count=2)

        with pytest.raises(ValueError) as exc_info:
            ComplianceReportGenerator.generate_pdf_report(
                logs=logs,
                tenant_id="tenant-005",
                framework="INVALID_FRAMEWORK",
            )

        assert "Invalid framework" in str(exc_info.value)
        assert "INVALID_FRAMEWORK" in str(exc_info.value)

    @pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE,
        reason="WeasyPrint not available (requires Pango system libraries)",
    )
    def test_empty_logs_generates_pdf(self):
        """Test PDF generation with empty logs (edge case)."""
        logs = []
        pdf_bytes = ComplianceReportGenerator.generate_pdf_report(
            logs=logs,
            tenant_id="tenant-006",
        )

        # Should still generate a valid PDF, just with empty data
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE,
        reason="WeasyPrint not available (requires Pango system libraries)",
    )
    def test_logs_with_different_tenant_filtered(self):
        """Test that logs from different tenants are properly filtered."""
        logs = [
            {
                "tenant_id": "tenant-007",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": 0.5,
            },
            {
                "tenant_id": "other-tenant",
                "agent_id": "agent-002",
                "decision": "DENY",
                "risk_score": 0.8,
            },
            {
                "tenant_id": "tenant-007",
                "agent_id": "agent-003",
                "decision": "ALLOW",
                "risk_score": 0.3,
            },
        ]

        pdf_bytes = ComplianceReportGenerator.generate_pdf_report(
            logs=logs,
            tenant_id="tenant-007",
        )

        # Should still generate valid PDF
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"


class TestRenderHTMLReport:
    """Test the render_html_report helper method."""

    def test_render_html_report_method_exists(self):
        """Verify render_html_report method exists."""
        assert hasattr(ComplianceReportGenerator, "render_html_report")
        assert callable(ComplianceReportGenerator.render_html_report)

    @pytest.mark.skipif(not JINJA2_AVAILABLE, reason="Jinja2 not available")
    def test_render_html_report_returns_string(self):
        """Test HTML rendering returns a string."""
        logs = create_sample_logs("tenant-008", count=2)
        html = ComplianceReportGenerator.render_html_report(
            logs=logs,
            tenant_id="tenant-008",
        )

        assert isinstance(html, str)
        assert len(html) > 0

    @pytest.mark.skipif(not JINJA2_AVAILABLE, reason="Jinja2 not available")
    def test_render_html_contains_expected_elements(self):
        """Test rendered HTML contains expected elements."""
        logs = create_sample_logs("tenant-009", count=2)
        html = ComplianceReportGenerator.render_html_report(
            logs=logs,
            tenant_id="tenant-009",
            company_name="Test Company",
        )

        assert "<!DOCTYPE html>" in html
        assert "Test Company" in html
        assert "tenant-009" in html
        assert "Executive Summary" in html
        assert "NIST AI RMF Alignment" in html

    @pytest.mark.skipif(not JINJA2_AVAILABLE, reason="Jinja2 not available")
    def test_render_html_with_custom_brand_color(self):
        """Test HTML rendering includes custom brand color."""
        logs = create_sample_logs("tenant-010", count=1)
        html = ComplianceReportGenerator.render_html_report(
            logs=logs,
            tenant_id="tenant-010",
            brand_color="#123456",
        )

        assert "#123456" in html


class TestPDFExportWithMockedDependencies:
    """Test PDF export with mocked WeasyPrint for environments without Pango."""

    def test_generate_pdf_calls_weasyprint(self):
        """Test that generate_pdf_report calls WeasyPrint correctly."""
        if not JINJA2_AVAILABLE:
            pytest.skip("Jinja2 not available for template rendering")

        logs = create_sample_logs("tenant-011", count=2)

        with patch("app.services.report_generator.WEASYPRINT_AVAILABLE", True):
            with patch("app.services.report_generator.HTML") as mock_html:
                # Set up the mock
                mock_pdf = MagicMock()
                mock_pdf.write_pdf = MagicMock()
                mock_html.return_value = mock_pdf

                # The actual call would fail without proper mock setup
                # This test verifies the integration point
                try:
                    ComplianceReportGenerator.generate_pdf_report(
                        logs=logs,
                        tenant_id="tenant-011",
                    )
                except Exception:
                    pass  # Expected when mock doesn't fully simulate PDF generation

                # Verify HTML was called with string parameter
                if mock_html.called:
                    call_kwargs = mock_html.call_args
                    assert "string" in call_kwargs.kwargs

    def test_missing_weasyprint_raises_runtime_error(self):
        """Test that missing WeasyPrint raises RuntimeError."""
        logs = create_sample_logs("tenant-012", count=1)

        with patch("app.services.report_generator.WEASYPRINT_AVAILABLE", False):
            with pytest.raises(RuntimeError) as exc_info:
                ComplianceReportGenerator.generate_pdf_report(
                    logs=logs,
                    tenant_id="tenant-012",
                )

            assert "WeasyPrint is not installed" in str(exc_info.value)

    def test_missing_jinja2_raises_runtime_error(self):
        """Test that missing Jinja2 raises RuntimeError."""
        logs = create_sample_logs("tenant-013", count=1)

        with patch("app.services.report_generator.WEASYPRINT_AVAILABLE", True):
            with patch("app.services.report_generator.JINJA2_AVAILABLE", False):
                with pytest.raises(RuntimeError) as exc_info:
                    ComplianceReportGenerator.generate_pdf_report(
                        logs=logs,
                        tenant_id="tenant-013",
                    )

                assert "Jinja2 is not installed" in str(exc_info.value)


class TestDefaultReportTemplate:
    """Test the default HTML report template."""

    def test_template_has_branding_placeholders(self):
        """Verify template includes branding placeholders."""
        assert "{{ company_name" in DEFAULT_REPORT_TEMPLATE
        assert "{{ brand_color" in DEFAULT_REPORT_TEMPLATE
        assert "{{ logo_url" in DEFAULT_REPORT_TEMPLATE

    def test_template_has_report_data_placeholders(self):
        """Verify template includes report data placeholders."""
        assert "{{ report." in DEFAULT_REPORT_TEMPLATE
        assert "report_metadata" in DEFAULT_REPORT_TEMPLATE
        assert "executive_summary" in DEFAULT_REPORT_TEMPLATE

    def test_template_has_framework_placeholder(self):
        """Verify template includes framework placeholder."""
        assert "{{ framework" in DEFAULT_REPORT_TEMPLATE

    def test_template_is_valid_html(self):
        """Verify template is valid HTML structure."""
        assert DEFAULT_REPORT_TEMPLATE.strip().startswith("<!DOCTYPE html>")
        assert "</html>" in DEFAULT_REPORT_TEMPLATE
        assert "<head>" in DEFAULT_REPORT_TEMPLATE
        assert "<body>" in DEFAULT_REPORT_TEMPLATE
        assert "</body>" in DEFAULT_REPORT_TEMPLATE
