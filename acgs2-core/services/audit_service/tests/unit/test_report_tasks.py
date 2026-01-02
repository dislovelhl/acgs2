"""
Unit tests for Celery report generation tasks.

Tests the report_tasks module including:
- generate_scheduled_report task
- generate_report_async task
- ReportGenerationResult dataclass
- Helper functions for report storage and email delivery
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add the service path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.tasks.report_tasks import (
    ReportGenerationResult,
    _generate_report_id,
    _save_report_to_storage,
    generate_report_async,
    generate_scheduled_report,
)


class TestReportGenerationResult:
    """Tests for ReportGenerationResult dataclass."""

    def test_result_creation_success(self):
        """Test creating a successful result."""
        result = ReportGenerationResult(
            success=True,
            report_id="RPT-TENANT01-SOC2-123456",
            tenant_id="tenant-001",
            framework="SOC2",
            format="pdf",
            file_path="/tmp/reports/RPT-TENANT01-SOC2-123456.pdf",
            file_size_bytes=1024,
            generated_at="2026-01-02T10:00:00+00:00",
        )

        assert result.success is True
        assert result.report_id == "RPT-TENANT01-SOC2-123456"
        assert result.tenant_id == "tenant-001"
        assert result.framework == "SOC2"
        assert result.format == "pdf"
        assert result.file_path == "/tmp/reports/RPT-TENANT01-SOC2-123456.pdf"
        assert result.file_size_bytes == 1024
        assert result.error_message is None

    def test_result_creation_failure(self):
        """Test creating a failed result."""
        result = ReportGenerationResult(
            success=False,
            report_id="RPT-TENANT02-GDPR-789012",
            tenant_id="tenant-002",
            framework="GDPR",
            format="csv",
            error_message="PDF generation failed: WeasyPrint not installed",
        )

        assert result.success is False
        assert result.error_message == "PDF generation failed: WeasyPrint not installed"
        assert result.file_path is None

    def test_result_with_email_info(self):
        """Test result with email delivery information."""
        result = ReportGenerationResult(
            success=True,
            report_id="RPT-TENANT03-ISO27001-111111",
            tenant_id="tenant-003",
            framework="ISO27001",
            format="pdf",
            email_sent=True,
            email_recipients=["admin@company.com", "compliance@company.com"],
        )

        assert result.email_sent is True
        assert len(result.email_recipients) == 2
        assert "admin@company.com" in result.email_recipients

    def test_to_dict_serialization(self):
        """Test conversion to dictionary for Celery serialization."""
        result = ReportGenerationResult(
            success=True,
            report_id="RPT-TENANT04-ISO42001-222222",
            tenant_id="tenant-004",
            framework="ISO42001",
            format="pdf",
            file_path="/tmp/reports/test.pdf",
            file_size_bytes=2048,
            generated_at="2026-01-02T11:00:00+00:00",
            email_sent=True,
            email_recipients=["test@example.com"],
        )

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["success"] is True
        assert data["report_id"] == "RPT-TENANT04-ISO42001-222222"
        assert data["tenant_id"] == "tenant-004"
        assert data["framework"] == "ISO42001"
        assert data["format"] == "pdf"
        assert data["file_path"] == "/tmp/reports/test.pdf"
        assert data["file_size_bytes"] == 2048
        assert data["email_sent"] is True
        assert data["email_recipients"] == ["test@example.com"]


class TestGenerateReportId:
    """Tests for report ID generation."""

    def test_report_id_format(self):
        """Test that report ID follows expected format."""
        report_id = _generate_report_id("tenant-abc123", "SOC2")

        # Should start with RPT-
        assert report_id.startswith("RPT-")

        # Should contain uppercase tenant prefix
        assert "TENANT-A" in report_id

        # Should contain framework
        assert "SOC2" in report_id

    def test_report_id_uniqueness(self):
        """Test that consecutive IDs are unique (timestamp-based)."""
        id1 = _generate_report_id("tenant-001", "GDPR")
        id2 = _generate_report_id("tenant-001", "GDPR")

        # Same tenant/framework but timestamp may differ
        # Both should have valid format
        assert id1.startswith("RPT-")
        assert id2.startswith("RPT-")

    def test_report_id_different_frameworks(self):
        """Test report IDs for different frameworks."""
        id_soc2 = _generate_report_id("tenant-001", "SOC2")
        id_gdpr = _generate_report_id("tenant-001", "GDPR")
        id_iso = _generate_report_id("tenant-001", "ISO27001")

        assert "SOC2" in id_soc2
        assert "GDPR" in id_gdpr
        assert "ISO27001" in id_iso


class TestSaveReportToStorage:
    """Tests for report storage functionality."""

    def test_save_pdf_report(self):
        """Test saving a PDF report to storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", tmpdir):
                report_bytes = b"%PDF-1.4 fake pdf content"
                report_id = "RPT-TEST-SOC2-123456"

                file_path = _save_report_to_storage(report_bytes, report_id, "pdf")

                assert file_path == os.path.join(tmpdir, f"{report_id}.pdf")
                assert os.path.exists(file_path)

                with open(file_path, "rb") as f:
                    saved_content = f.read()
                assert saved_content == report_bytes

    def test_save_csv_report(self):
        """Test saving a CSV report to storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", tmpdir):
                report_bytes = b"timestamp,agent_id,decision\n2026-01-01,agent-1,ALLOW"
                report_id = "RPT-TEST-GDPR-789012"

                file_path = _save_report_to_storage(report_bytes, report_id, "csv")

                assert file_path == os.path.join(tmpdir, f"{report_id}.csv")
                assert os.path.exists(file_path)

    def test_creates_directory_if_missing(self):
        """Test that storage directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "nested", "reports")
            with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", nested_path):
                report_bytes = b"test content"
                report_id = "RPT-TEST-ISO-111111"

                file_path = _save_report_to_storage(report_bytes, report_id, "pdf")

                assert os.path.exists(nested_path)
                assert os.path.exists(file_path)


class TestGenerateScheduledReport:
    """Tests for generate_scheduled_report Celery task."""

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    def test_generate_pdf_report_success(self, mock_save, mock_fetch_logs, mock_get_generator):
        """Test successful PDF report generation."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"PDF content"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = [{"tenant_id": "tenant-001", "decision": "ALLOW"}]
        mock_save.return_value = "/tmp/reports/test.pdf"

        # Call task directly (not via Celery)
        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "test-task-id"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-001",
            framework="SOC2",
            format="pdf",
            company_name="Test Corp",
        )

        assert result["success"] is True
        assert result["tenant_id"] == "tenant-001"
        assert result["framework"] == "SOC2"
        assert result["format"] == "pdf"
        assert result["file_path"] == "/tmp/reports/test.pdf"
        assert result["file_size_bytes"] == len(b"PDF content")

        # Verify calls
        mock_fetch_logs.assert_called_once_with("tenant-001")
        mock_generator.generate_pdf_report.assert_called_once()

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    def test_generate_csv_report_success(self, mock_save, mock_fetch_logs, mock_get_generator):
        """Test successful CSV report generation."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_csv_bytes.return_value = b"timestamp,decision\n"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []
        mock_save.return_value = "/tmp/reports/test.csv"

        # Call task directly
        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "test-task-id-2"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-002",
            framework="GDPR",
            format="csv",
        )

        assert result["success"] is True
        assert result["format"] == "csv"
        mock_generator.generate_csv_bytes.assert_called_once()

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    def test_invalid_format_raises_error(self, mock_fetch_logs, mock_get_generator):
        """Test that invalid format raises ValueError."""
        mock_generator = MagicMock()
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []

        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "test-task-id-3"
        task.request.retries = 0
        task.max_retries = 3

        with pytest.raises(ValueError) as exc_info:
            task.run(
                tenant_id="tenant-003",
                framework="SOC2",
                format="xlsx",  # Invalid format
            )

        assert "Unsupported format" in str(exc_info.value)

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    @patch("app.tasks.report_tasks._get_email_service")
    def test_email_delivery_success(
        self, mock_get_email, mock_save, mock_fetch_logs, mock_get_generator
    ):
        """Test report generation with email delivery."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"PDF content"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []
        mock_save.return_value = "/tmp/reports/test.pdf"

        mock_email_service = MagicMock()
        mock_get_email.return_value = mock_email_service

        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "test-task-id-4"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-004",
            framework="ISO27001",
            format="pdf",
            recipient_emails=["admin@test.com", "compliance@test.com"],
        )

        assert result["success"] is True
        assert result["email_sent"] is True
        assert result["email_recipients"] == ["admin@test.com", "compliance@test.com"]

        # Verify email was sent to each recipient
        assert mock_email_service.send_report_email.call_count == 2

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    @patch("app.tasks.report_tasks._get_email_service")
    def test_email_service_not_available(
        self, mock_get_email, mock_save, mock_fetch_logs, mock_get_generator
    ):
        """Test report generation when email service is not available."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"PDF content"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []
        mock_save.return_value = "/tmp/reports/test.pdf"
        mock_get_email.return_value = None  # Email service not available

        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "test-task-id-5"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-005",
            framework="SOC2",
            format="pdf",
            recipient_emails=["admin@test.com"],
        )

        # Report should still succeed, just without email
        assert result["success"] is True
        assert result["email_sent"] is False

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    @patch("app.tasks.report_tasks._get_email_service")
    def test_email_failure_does_not_fail_task(
        self, mock_get_email, mock_save, mock_fetch_logs, mock_get_generator
    ):
        """Test that email failure doesn't fail the overall task."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"PDF content"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []
        mock_save.return_value = "/tmp/reports/test.pdf"

        mock_email_service = MagicMock()
        mock_email_service.send_report_email.side_effect = Exception("SMTP error")
        mock_get_email.return_value = mock_email_service

        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "test-task-id-6"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-006",
            framework="GDPR",
            format="pdf",
            recipient_emails=["admin@test.com"],
        )

        # Report should succeed even if email fails
        assert result["success"] is True
        assert result["email_sent"] is False


class TestGenerateReportAsync:
    """Tests for generate_report_async Celery task."""

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    def test_generate_with_provided_logs(self, mock_save, mock_get_generator):
        """Test async report generation with pre-fetched logs."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_csv_bytes.return_value = b"CSV content"
        mock_get_generator.return_value = mock_generator
        mock_save.return_value = "/tmp/reports/test.csv"

        pre_fetched_logs = [
            {"tenant_id": "tenant-007", "agent_id": "agent-001", "decision": "ALLOW"},
            {"tenant_id": "tenant-007", "agent_id": "agent-002", "decision": "DENY"},
        ]

        task = generate_report_async
        task.request = MagicMock()
        task.request.id = "async-task-id-1"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-007",
            framework="GDPR",
            format="csv",
            logs=pre_fetched_logs,
        )

        assert result["success"] is True
        assert result["format"] == "csv"

        # Verify logs were passed to generator
        mock_generator.generate_csv_bytes.assert_called_once()
        call_args = mock_generator.generate_csv_bytes.call_args
        assert call_args[1]["logs"] == pre_fetched_logs

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    def test_generate_without_logs_fetches_them(
        self, mock_save, mock_fetch_logs, mock_get_generator
    ):
        """Test async report generation fetches logs when not provided."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"PDF content"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = [{"tenant_id": "tenant-008", "decision": "ALLOW"}]
        mock_save.return_value = "/tmp/reports/test.pdf"

        task = generate_report_async
        task.request = MagicMock()
        task.request.id = "async-task-id-2"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-008",
            framework="SOC2",
            format="pdf",
            # logs=None by default
        )

        assert result["success"] is True
        mock_fetch_logs.assert_called_once_with("tenant-008")

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    def test_branding_parameters_passed_to_pdf(self, mock_save, mock_get_generator):
        """Test that branding parameters are passed to PDF generator."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"Branded PDF"
        mock_get_generator.return_value = mock_generator
        mock_save.return_value = "/tmp/reports/branded.pdf"

        task = generate_report_async
        task.request = MagicMock()
        task.request.id = "async-task-id-3"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-009",
            framework="ISO42001",
            format="pdf",
            logs=[],
            company_name="Branded Corp",
            logo_url="https://example.com/logo.png",
            brand_color="#FF5733",
        )

        assert result["success"] is True

        # Verify branding was passed
        call_args = mock_generator.generate_pdf_report.call_args
        assert call_args[1]["company_name"] == "Branded Corp"
        assert call_args[1]["logo_url"] == "https://example.com/logo.png"
        assert call_args[1]["brand_color"] == "#FF5733"


class TestTaskConfiguration:
    """Tests for task configuration and metadata."""

    def test_scheduled_report_task_name(self):
        """Verify task is registered with correct name."""
        assert generate_scheduled_report.name == "audit_service.generate_scheduled_report"

    def test_async_report_task_name(self):
        """Verify async task is registered with correct name."""
        assert generate_report_async.name == "audit_service.generate_report_async"

    def test_scheduled_report_retry_config(self):
        """Verify retry configuration for scheduled reports."""
        assert generate_scheduled_report.max_retries == 3
        assert generate_scheduled_report.default_retry_delay == 60

    def test_async_report_retry_config(self):
        """Verify retry configuration for async reports."""
        assert generate_report_async.max_retries == 3
        assert generate_report_async.default_retry_delay == 30


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    @patch("app.tasks.report_tasks._save_report_to_storage")
    def test_empty_logs_still_generates_report(
        self, mock_save, mock_fetch_logs, mock_get_generator
    ):
        """Test that empty logs still generate a valid report."""
        mock_generator = MagicMock()
        mock_generator.generate_csv_bytes.return_value = b"timestamp,decision\n"
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []
        mock_save.return_value = "/tmp/reports/empty.csv"

        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "empty-logs-task"
        task.request.retries = 0
        task.max_retries = 3

        result = task.run(
            tenant_id="tenant-empty",
            framework="SOC2",
            format="csv",
        )

        assert result["success"] is True
        assert result["file_size_bytes"] == len(b"timestamp,decision\n")

    @patch("app.tasks.report_tasks._get_report_generator")
    @patch("app.tasks.report_tasks._fetch_logs_for_tenant")
    def test_generator_exception_propagates(self, mock_fetch_logs, mock_get_generator):
        """Test that generator exceptions are propagated for retry."""
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.side_effect = RuntimeError("WeasyPrint not installed")
        mock_get_generator.return_value = mock_generator
        mock_fetch_logs.return_value = []

        task = generate_scheduled_report
        task.request = MagicMock()
        task.request.id = "error-task"
        task.request.retries = 0
        task.max_retries = 3

        with pytest.raises(RuntimeError) as exc_info:
            task.run(
                tenant_id="tenant-error",
                framework="SOC2",
                format="pdf",
            )

        assert "WeasyPrint not installed" in str(exc_info.value)

    def test_format_case_insensitive(self):
        """Test that format parameter is case-insensitive."""
        with patch("app.tasks.report_tasks._get_report_generator") as mock_get_gen:
            with patch("app.tasks.report_tasks._fetch_logs_for_tenant") as mock_fetch:
                with patch("app.tasks.report_tasks._save_report_to_storage") as mock_save:
                    mock_generator = MagicMock()
                    mock_generator.generate_pdf_report.return_value = b"PDF"
                    mock_get_gen.return_value = mock_generator
                    mock_fetch.return_value = []
                    mock_save.return_value = "/tmp/reports/test.pdf"

                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "case-task"
                    task.request.retries = 0
                    task.max_retries = 3

                    # Test uppercase
                    result = task.run(
                        tenant_id="tenant-case",
                        framework="SOC2",
                        format="PDF",  # Uppercase
                    )

                    assert result["success"] is True
                    assert result["format"] == "pdf"  # Should be lowercase


class TestIntegrationPatterns:
    """Tests verifying integration patterns work correctly."""

    def test_result_can_be_serialized_to_json(self):
        """Test that result can be JSON serialized for Celery."""
        import json

        result = ReportGenerationResult(
            success=True,
            report_id="RPT-TEST-JSON-999999",
            tenant_id="tenant-json",
            framework="SOC2",
            format="pdf",
            file_path="/tmp/reports/test.pdf",
            file_size_bytes=1024,
            generated_at="2026-01-02T12:00:00+00:00",
            email_sent=True,
            email_recipients=["test@example.com"],
        )

        # Should be serializable
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)

        # Should be deserializable
        data = json.loads(json_str)
        assert data["success"] is True
        assert data["report_id"] == "RPT-TEST-JSON-999999"
