"""
End-to-End Integration Tests for Audit Reporting System

Tests the full workflow from API request through Celery task processing
to email delivery and report storage:
1. Trigger on-demand report via POST /api/v1/reports/generate
2. Verify Celery task created and processed
3. Verify PDF generated with correct branding
4. Mock email sent successfully
5. Verify report stored in REPORT_STORAGE_PATH

These tests require:
- Redis server running (mocked for unit-style tests, real for full integration)
- Celery worker (mocked for unit-style tests)
- SMTP server (mocked)
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

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
    from app.services.email_service import EmailResult, EmailService
    from app.tasks.report_tasks import generate_report_async, generate_scheduled_report

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason=f"Required imports not available: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}",
)


class TestE2EReportGeneration:
    """
    End-to-end tests for report generation workflow.

    Tests the complete pipeline:
    API Request -> Celery Task -> Report Generation -> Storage -> Email
    """

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for report storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_env_vars(self, temp_storage_dir):
        """Set up mock environment variables for testing."""
        env_vars = {
            "REPORT_STORAGE_PATH": temp_storage_dir,
            "SMTP_HOST": "smtp.test.local",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_FROM_EMAIL": "reports@test.local",
            "SMTP_USE_TLS": "false",
            "CELERY_BROKER_URL": "memory://",
            "CELERY_RESULT_BACKEND": "cache+memory://",
            "APP_ENV": "test",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            # Reset email service cached settings
            EmailService.reset_default_settings()
            yield env_vars
            EmailService.reset_default_settings()

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    @pytest.fixture
    def sample_logs(self) -> List[Dict[str, Any]]:
        """Sample decision logs for report generation."""
        return [
            {
                "timestamp": "2026-01-02T10:00:00+00:00",
                "tenant_id": "test-tenant-001",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": 0.15,
                "compliance_tags": ["soc2-cc1.1", "iso27001-a.5"],
                "policy_version": "v1.2.3",
                "trace_id": "trace-abc-123",
            },
            {
                "timestamp": "2026-01-02T10:05:00+00:00",
                "tenant_id": "test-tenant-001",
                "agent_id": "agent-002",
                "decision": "DENY",
                "risk_score": 0.85,
                "compliance_tags": ["soc2-cc6.1", "gdpr-art32"],
                "policy_version": "v1.2.3",
                "trace_id": "trace-def-456",
            },
            {
                "timestamp": "2026-01-02T10:10:00+00:00",
                "tenant_id": "test-tenant-001",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": 0.25,
                "compliance_tags": ["iso27001-a.9"],
                "policy_version": "v1.2.4",
                "trace_id": "trace-ghi-789",
            },
        ]

    def test_api_report_generate_returns_202_accepted(
        self,
        test_client,
        mock_env_vars,
    ):
        """Test that POST /api/v1/reports/generate returns 202 Accepted."""
        # Mock the Celery task to return a task ID
        with patch("app.api.reports._get_generate_report_task") as mock_get_task:
            mock_task = MagicMock()
            mock_result = MagicMock()
            mock_result.id = "test-task-id-001"
            mock_task.delay.return_value = mock_result
            mock_get_task.return_value = mock_task

            response = test_client.post(
                "/api/v1/reports/generate",
                json={
                    "framework": "soc2",
                    "format": "pdf",
                    "tenant_id": "test-tenant-001",
                    "branding": {
                        "company_name": "Test Corporation",
                        "logo_url": "https://example.com/logo.png",
                        "brand_color": "#003366",
                    },
                },
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert data["task_id"] == "test-task-id-001"
            assert data["framework"] == "soc2"
            assert data["format"] == "pdf"
            assert "submitted_at" in data

    def test_api_report_generate_validates_framework(
        self,
        test_client,
        mock_env_vars,
    ):
        """Test that invalid framework is rejected."""
        response = test_client.post(
            "/api/v1/reports/generate",
            json={
                "framework": "invalid_framework",
                "format": "pdf",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_api_report_generate_validates_format(
        self,
        test_client,
        mock_env_vars,
    ):
        """Test that invalid format is rejected."""
        response = test_client.post(
            "/api/v1/reports/generate",
            json={
                "framework": "soc2",
                "format": "xlsx",  # Invalid format
            },
        )

        assert response.status_code == 422  # Validation error

    def test_api_report_generate_validates_branding_color(
        self,
        test_client,
        mock_env_vars,
    ):
        """Test that invalid brand color format is rejected."""
        with patch("app.api.reports._get_generate_report_task") as mock_get_task:
            mock_task = MagicMock()
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_task.delay.return_value = mock_result
            mock_get_task.return_value = mock_task

            response = test_client.post(
                "/api/v1/reports/generate",
                json={
                    "framework": "soc2",
                    "format": "pdf",
                    "branding": {
                        "brand_color": "not-a-hex-color",
                    },
                },
            )

            assert response.status_code == 422  # Validation error

    def test_api_report_status_check(
        self,
        test_client,
        mock_env_vars,
    ):
        """Test that GET /api/v1/reports/{task_id} returns task status."""
        with patch("app.api.reports._get_celery_app") as mock_get_app:
            mock_app = MagicMock()
            mock_async_result = MagicMock()
            mock_async_result.status = "SUCCESS"
            mock_async_result.result = {
                "success": True,
                "report_id": "RPT-TEST-SOC2-123456",
                "format": "pdf",
            }
            mock_app.AsyncResult.return_value = mock_async_result
            mock_get_app.return_value = mock_app

            response = test_client.get("/api/v1/reports/test-task-id-001")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-id-001"
            assert data["status"] == "success"
            assert data["result"]["success"] is True
            assert data["report_url"] is not None

    def test_api_report_status_pending(
        self,
        test_client,
        mock_env_vars,
    ):
        """Test status check for pending task."""
        with patch("app.api.reports._get_celery_app") as mock_get_app:
            mock_app = MagicMock()
            mock_async_result = MagicMock()
            mock_async_result.status = "PENDING"
            mock_async_result.result = None
            mock_app.AsyncResult.return_value = mock_async_result
            mock_get_app.return_value = mock_app

            response = test_client.get("/api/v1/reports/pending-task-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"
            assert data["result"] is None
            assert data["report_url"] is None


class TestCeleryTaskExecution:
    """
    Tests for Celery task execution and report generation.

    Verifies that tasks correctly:
    - Generate reports with proper branding
    - Save reports to storage
    - Send emails when configured
    """

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for report storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_report_generator(self):
        """Mock the report generator to return test content."""
        mock_generator = MagicMock()
        # Return a valid PDF-like header for verification
        mock_generator.generate_pdf_report.return_value = (
            b"%PDF-1.4\n1 0 obj\n<</Type/Catalog>>\nendobj\n%%EOF"
        )
        mock_generator.generate_csv_bytes.return_value = (
            b"timestamp,agent_id,decision,risk_score\n"
            b"2026-01-02T10:00:00,agent-001,ALLOW,0.1500\n"
            b"2026-01-02T10:05:00,agent-002,DENY,0.8500\n"
        )
        return mock_generator

    def test_scheduled_report_generates_pdf(
        self,
        temp_storage_dir,
        mock_report_generator,
    ):
        """Test that scheduled report task generates a PDF file."""
        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_report_generator,
            ):
                with patch(
                    "app.tasks.report_tasks._fetch_logs_for_tenant",
                    return_value=[],
                ):
                    # Set up task mock
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "e2e-test-task-001"
                    task.request.retries = 0
                    task.max_retries = 3

                    result = task.run(
                        tenant_id="test-tenant-001",
                        framework="SOC2",
                        format="pdf",
                        company_name="E2E Test Corp",
                        logo_url="https://example.com/logo.png",
                        brand_color="#003366",
                    )

                    # Verify result
                    assert result["success"] is True
                    assert result["framework"] == "SOC2"
                    assert result["format"] == "pdf"
                    assert result["file_path"] is not None
                    assert result["file_size_bytes"] > 0

                    # Verify file was created
                    assert os.path.exists(result["file_path"])
                    with open(result["file_path"], "rb") as f:
                        content = f.read()
                    assert content.startswith(b"%PDF")

    def test_scheduled_report_generates_csv(
        self,
        temp_storage_dir,
        mock_report_generator,
    ):
        """Test that scheduled report task generates a CSV file."""
        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_report_generator,
            ):
                with patch(
                    "app.tasks.report_tasks._fetch_logs_for_tenant",
                    return_value=[],
                ):
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "e2e-test-task-002"
                    task.request.retries = 0
                    task.max_retries = 3

                    result = task.run(
                        tenant_id="test-tenant-001",
                        framework="GDPR",
                        format="csv",
                    )

                    # Verify result
                    assert result["success"] is True
                    assert result["format"] == "csv"
                    assert result["file_path"].endswith(".csv")

                    # Verify CSV content
                    with open(result["file_path"], "rb") as f:
                        content = f.read()
                    assert b"timestamp" in content
                    assert b"agent_id" in content

    def test_scheduled_report_with_email_delivery(
        self,
        temp_storage_dir,
        mock_report_generator,
    ):
        """Test that scheduled report sends email when recipients specified."""
        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_report_generator,
            ):
                with patch(
                    "app.tasks.report_tasks._fetch_logs_for_tenant",
                    return_value=[],
                ):
                    with patch("app.tasks.report_tasks._get_email_service") as mock_get_email:
                        mock_email_service = MagicMock()
                        mock_email_service.send_report_email.return_value = EmailResult(
                            success=True,
                            recipient="admin@test.local",
                            message_id="<test-msg-id>",
                            sent_at=datetime.now(timezone.utc).isoformat(),
                        )
                        mock_get_email.return_value = mock_email_service

                        task = generate_scheduled_report
                        task.request = MagicMock()
                        task.request.id = "e2e-test-task-003"
                        task.request.retries = 0
                        task.max_retries = 3

                        result = task.run(
                            tenant_id="test-tenant-001",
                            framework="ISO27001",
                            format="pdf",
                            recipient_emails=[
                                "admin@test.local",
                                "compliance@test.local",
                            ],
                        )

                        # Verify result
                        assert result["success"] is True
                        assert result["email_sent"] is True
                        assert result["email_recipients"] == [
                            "admin@test.local",
                            "compliance@test.local",
                        ]

                        # Verify email was sent to each recipient
                        assert mock_email_service.send_report_email.call_count == 2

    def test_async_report_with_provided_logs(
        self,
        temp_storage_dir,
        mock_report_generator,
    ):
        """Test async report generation with pre-fetched logs."""
        sample_logs = [
            {"timestamp": "2026-01-02T10:00:00", "agent_id": "agent-001", "decision": "ALLOW"},
            {"timestamp": "2026-01-02T10:05:00", "agent_id": "agent-002", "decision": "DENY"},
        ]

        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_report_generator,
            ):
                task = generate_report_async
                task.request = MagicMock()
                task.request.id = "e2e-async-task-001"
                task.request.retries = 0
                task.max_retries = 3

                result = task.run(
                    tenant_id="test-tenant-001",
                    framework="SOC2",
                    format="csv",
                    logs=sample_logs,
                )

                # Verify result
                assert result["success"] is True
                assert result["format"] == "csv"

                # Verify generator was called with logs
                mock_report_generator.generate_csv_bytes.assert_called_once()
                call_kwargs = mock_report_generator.generate_csv_bytes.call_args[1]
                assert call_kwargs["logs"] == sample_logs

    def test_branding_parameters_passed_correctly(
        self,
        temp_storage_dir,
        mock_report_generator,
    ):
        """Test that branding parameters are passed to the generator."""
        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_report_generator,
            ):
                with patch(
                    "app.tasks.report_tasks._fetch_logs_for_tenant",
                    return_value=[],
                ):
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "e2e-branding-test"
                    task.request.retries = 0
                    task.max_retries = 3

                    result = task.run(
                        tenant_id="test-tenant-001",
                        framework="SOC2",
                        format="pdf",
                        company_name="Branded Corp Inc",
                        logo_url="https://branded.com/logo.png",
                        brand_color="#FF5733",
                    )

                    assert result["success"] is True

                    # Verify branding was passed to generator
                    call_kwargs = mock_report_generator.generate_pdf_report.call_args[1]
                    assert call_kwargs["company_name"] == "Branded Corp Inc"
                    assert call_kwargs["logo_url"] == "https://branded.com/logo.png"
                    assert call_kwargs["brand_color"] == "#FF5733"


class TestEmailDeliveryIntegration:
    """
    Tests for email delivery in the reporting workflow.

    Verifies that emails are properly formatted and sent.
    """

    @pytest.fixture(autouse=True)
    def reset_email_settings(self):
        """Reset email service settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    def test_email_sent_with_pdf_attachment(self):
        """Test that PDF reports are attached to emails correctly."""
        env_vars = {
            "SMTP_HOST": "smtp.test.local",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_FROM_EMAIL": "reports@test.local",
            "SMTP_USE_TLS": "false",
        }

        pdf_content = b"%PDF-1.4\n%Test PDF Content\n%%EOF"

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = EmailService.send_report_email(
                    recipient="admin@example.com",
                    pdf_bytes=pdf_content,
                    report_name="SOC 2 Compliance Report",
                    format="pdf",
                )

                assert result.success is True
                assert result.recipient == "admin@example.com"

                # Verify message was sent
                mock_server.send_message.assert_called_once()
                sent_message = mock_server.send_message.call_args[0][0]

                # Verify attachment
                payloads = sent_message.get_payload()
                assert len(payloads) == 2  # body + attachment

                attachment = payloads[1]
                assert attachment.get_content_subtype() == "pdf"
                assert "SOC_2_Compliance_Report" in attachment.get_filename()

    def test_email_sent_with_csv_attachment(self):
        """Test that CSV reports are attached to emails correctly."""
        env_vars = {
            "SMTP_HOST": "smtp.test.local",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_FROM_EMAIL": "reports@test.local",
        }

        csv_content = b"timestamp,agent_id,decision\n2026-01-02,agent-001,ALLOW\n"

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = EmailService.send_report_email(
                    recipient="analyst@example.com",
                    pdf_bytes=csv_content,
                    report_name="Weekly Data Export",
                    format="csv",
                )

                assert result.success is True

                # Verify CSV attachment
                sent_message = mock_server.send_message.call_args[0][0]
                attachment = sent_message.get_payload()[1]
                assert attachment.get_content_subtype() == "csv"
                assert ".csv" in attachment.get_filename()

    def test_email_to_multiple_recipients(self):
        """Test sending report to multiple recipients."""
        env_vars = {
            "SMTP_HOST": "smtp.test.local",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_FROM_EMAIL": "reports@test.local",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                results = EmailService.send_report_to_multiple(
                    recipients=[
                        "admin@example.com",
                        "compliance@example.com",
                        "ciso@example.com",
                    ],
                    pdf_bytes=b"%PDF test",
                    report_name="Monthly Report",
                    format="pdf",
                )

                assert len(results) == 3
                assert all(r.success for r in results)
                assert mock_server.send_message.call_count == 3


class TestFullE2EWorkflow:
    """
    Full end-to-end workflow tests simulating real-world scenarios.

    These tests verify the complete pipeline from API request to email delivery.
    """

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for report storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    @pytest.fixture
    def mock_full_environment(self, temp_storage_dir):
        """Set up complete mock environment for full E2E tests."""
        env_vars = {
            "REPORT_STORAGE_PATH": temp_storage_dir,
            "SMTP_HOST": "smtp.test.local",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_FROM_EMAIL": "reports@test.local",
            "SMTP_USE_TLS": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            EmailService.reset_default_settings()
            yield {"env_vars": env_vars, "storage_dir": temp_storage_dir}
            EmailService.reset_default_settings()

    def test_full_soc2_report_workflow(
        self,
        test_client,
        mock_full_environment,
    ):
        """
        Test complete SOC 2 report generation workflow.

        Steps:
        1. Submit report generation request via API
        2. Simulate Celery task execution
        3. Verify PDF is generated with branding
        4. Verify email is sent
        5. Verify report is stored correctly
        """
        storage_dir = mock_full_environment["storage_dir"]

        # Step 1: Mock task submission
        with patch("app.api.reports._get_generate_report_task") as mock_get_task:
            mock_task = MagicMock()
            mock_result = MagicMock()
            mock_result.id = "full-e2e-soc2-001"
            mock_task.delay.return_value = mock_result
            mock_get_task.return_value = mock_task

            response = test_client.post(
                "/api/v1/reports/generate",
                json={
                    "framework": "soc2",
                    "format": "pdf",
                    "tenant_id": "e2e-test-tenant",
                    "branding": {
                        "company_name": "E2E Test Company",
                        "brand_color": "#0066CC",
                    },
                },
            )

            assert response.status_code == 202
            task_id = response.json()["task_id"]
            assert task_id == "full-e2e-soc2-001"

        # Step 2-5: Simulate task execution
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"%PDF-1.4 E2E Test Report"

        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_generator,
            ):
                with patch("app.tasks.report_tasks._fetch_logs_for_tenant", return_value=[]):
                    with patch("app.tasks.report_tasks._get_email_service") as mock_email:
                        mock_email_service = MagicMock()
                        mock_email.return_value = mock_email_service

                        task = generate_scheduled_report
                        task.request = MagicMock()
                        task.request.id = task_id
                        task.request.retries = 0
                        task.max_retries = 3

                        result = task.run(
                            tenant_id="e2e-test-tenant",
                            framework="SOC2",
                            format="pdf",
                            recipient_emails=["ciso@e2e-test.com"],
                            company_name="E2E Test Company",
                            brand_color="#0066CC",
                        )

        # Verify complete workflow
        assert result["success"] is True
        assert result["framework"] == "SOC2"
        assert result["format"] == "pdf"
        assert result["email_sent"] is True

        # Verify file exists and contains expected content
        assert os.path.exists(result["file_path"])
        with open(result["file_path"], "rb") as f:
            content = f.read()
        assert content == b"%PDF-1.4 E2E Test Report"

        # Verify branding was passed
        call_kwargs = mock_generator.generate_pdf_report.call_args[1]
        assert call_kwargs["company_name"] == "E2E Test Company"
        assert call_kwargs["brand_color"] == "#0066CC"

    def test_full_gdpr_csv_export_workflow(
        self,
        test_client,
        mock_full_environment,
    ):
        """Test complete GDPR CSV export workflow."""
        storage_dir = mock_full_environment["storage_dir"]

        mock_generator = MagicMock()
        mock_generator.generate_csv_bytes.return_value = (
            b"timestamp,agent_id,decision,compliance_tags\n"
            b"2026-01-02T10:00:00,agent-001,ALLOW,gdpr-art32\n"
        )

        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_generator,
            ):
                with patch("app.tasks.report_tasks._fetch_logs_for_tenant", return_value=[]):
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "gdpr-csv-001"
                    task.request.retries = 0
                    task.max_retries = 3

                    result = task.run(
                        tenant_id="gdpr-tenant",
                        framework="GDPR",
                        format="csv",
                    )

        assert result["success"] is True
        assert result["format"] == "csv"
        assert result["file_path"].endswith(".csv")

        # Verify CSV content
        with open(result["file_path"], "rb") as f:
            content = f.read()
        assert b"gdpr-art32" in content

    def test_api_health_check(self, test_client):
        """Test reports API health check endpoint."""
        response = test_client.get("/api/v1/reports/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "api" in data
        assert data["api"] == "reports"


class TestReportDownload:
    """Tests for report download functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for report storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_download_existing_pdf_report(self, test_client, temp_storage_dir):
        """Test downloading an existing PDF report."""
        # Create a test report file
        report_filename = "RPT-TEST-SOC2-123456.pdf"
        report_path = os.path.join(temp_storage_dir, report_filename)
        with open(report_path, "wb") as f:
            f.write(b"%PDF-1.4 Test PDF Content")

        with patch("app.api.reports.REPORT_STORAGE_PATH", temp_storage_dir):
            response = test_client.get(f"/api/v1/reports/download/{report_filename}")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert b"%PDF-1.4" in response.content

    def test_download_existing_csv_report(self, test_client, temp_storage_dir):
        """Test downloading an existing CSV report."""
        report_filename = "RPT-TEST-GDPR-789012.csv"
        report_path = os.path.join(temp_storage_dir, report_filename)
        with open(report_path, "wb") as f:
            f.write(b"timestamp,agent_id,decision\n")

        with patch("app.api.reports.REPORT_STORAGE_PATH", temp_storage_dir):
            response = test_client.get(f"/api/v1/reports/download/{report_filename}")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_download_nonexistent_report(self, test_client, temp_storage_dir):
        """Test downloading a non-existent report returns 404."""
        with patch("app.api.reports.REPORT_STORAGE_PATH", temp_storage_dir):
            response = test_client.get("/api/v1/reports/download/nonexistent.pdf")

            assert response.status_code == 404

    def test_download_path_traversal_blocked(self, test_client, temp_storage_dir):
        """Test that path traversal attempts are blocked."""
        with patch("app.api.reports.REPORT_STORAGE_PATH", temp_storage_dir):
            response = test_client.get("/api/v1/reports/download/../../../etc/passwd")

            assert response.status_code == 400


class TestErrorHandling:
    """Tests for error handling in the reporting workflow."""

    @pytest.fixture
    def test_client(self):
        """Create a FastAPI test client."""
        if TestClient is None:
            pytest.skip("FastAPI TestClient not available")
        return TestClient(fastapi_app)

    def test_celery_unavailable_returns_503(self, test_client):
        """Test that unavailable Celery returns 503."""
        with patch("app.api.reports._get_generate_report_task", return_value=None):
            response = test_client.post(
                "/api/v1/reports/generate",
                json={
                    "framework": "soc2",
                    "format": "pdf",
                },
            )

            assert response.status_code == 503
            assert "unavailable" in response.json()["detail"].lower()

    def test_task_submission_failure_returns_500(self, test_client):
        """Test that task submission failure returns 500."""
        with patch("app.api.reports._get_generate_report_task") as mock_get_task:
            mock_task = MagicMock()
            mock_task.delay.side_effect = Exception("Redis connection failed")
            mock_get_task.return_value = mock_task

            response = test_client.post(
                "/api/v1/reports/generate",
                json={
                    "framework": "soc2",
                    "format": "pdf",
                },
            )

            assert response.status_code == 500

    def test_status_check_celery_unavailable(self, test_client):
        """Test status check when Celery is unavailable."""
        with patch("app.api.reports._get_celery_app", return_value=None):
            response = test_client.get("/api/v1/reports/some-task-id")

            assert response.status_code == 503


class TestReportStorageVerification:
    """Tests to verify reports are correctly stored."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for report storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_report_stored_with_correct_extension(self, temp_storage_dir):
        """Test that reports are stored with correct file extension."""
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"%PDF test"
        mock_generator.generate_csv_bytes.return_value = b"timestamp,value\n"

        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_generator,
            ):
                with patch("app.tasks.report_tasks._fetch_logs_for_tenant", return_value=[]):
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "storage-test-001"
                    task.request.retries = 0
                    task.max_retries = 3

                    # Test PDF
                    pdf_result = task.run(
                        tenant_id="storage-tenant",
                        framework="SOC2",
                        format="pdf",
                    )
                    assert pdf_result["file_path"].endswith(".pdf")

                    # Test CSV
                    csv_result = task.run(
                        tenant_id="storage-tenant",
                        framework="GDPR",
                        format="csv",
                    )
                    assert csv_result["file_path"].endswith(".csv")

    def test_report_id_format_correct(self, temp_storage_dir):
        """Test that report IDs follow the expected format."""
        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"%PDF test"

        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", temp_storage_dir):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_generator,
            ):
                with patch("app.tasks.report_tasks._fetch_logs_for_tenant", return_value=[]):
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "id-format-test"
                    task.request.retries = 0
                    task.max_retries = 3

                    result = task.run(
                        tenant_id="tenant-abc123",
                        framework="ISO27001",
                        format="pdf",
                    )

                    report_id = result["report_id"]
                    # Should follow format: RPT-{TENANT_PREFIX}-{FRAMEWORK}-{TIMESTAMP}
                    assert report_id.startswith("RPT-")
                    assert "TENANT-A" in report_id
                    assert "ISO27001" in report_id

    def test_storage_directory_created_if_missing(self, temp_storage_dir):
        """Test that storage directory is created if it doesn't exist."""
        nested_path = os.path.join(temp_storage_dir, "nested", "reports")

        mock_generator = MagicMock()
        mock_generator.generate_pdf_report.return_value = b"%PDF test"

        with patch("app.tasks.report_tasks.REPORT_STORAGE_PATH", nested_path):
            with patch(
                "app.tasks.report_tasks._get_report_generator",
                return_value=mock_generator,
            ):
                with patch("app.tasks.report_tasks._fetch_logs_for_tenant", return_value=[]):
                    task = generate_scheduled_report
                    task.request = MagicMock()
                    task.request.id = "mkdir-test"
                    task.request.retries = 0
                    task.max_retries = 3

                    result = task.run(
                        tenant_id="mkdir-tenant",
                        framework="SOC2",
                        format="pdf",
                    )

                    assert result["success"] is True
                    assert os.path.exists(nested_path)
                    assert os.path.exists(result["file_path"])
