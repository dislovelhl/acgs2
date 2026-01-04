"""
Unit tests for EmailService in Audit Service.

Tests email delivery functionality including:
- EmailSettings configuration
- EmailResult data class
- EmailService send methods
- Error handling for SMTP failures
- Attachment creation for PDF and CSV

All tests use mocked SMTP connections.
"""

import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

import pytest

# Add the service path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.email_service import (  # noqa: E402
    EmailConfigurationError,
    EmailDeliveryError,
    EmailResult,
    EmailService,
    EmailSettings,
)


class TestEmailSettings:
    """Tests for EmailSettings dataclass."""

    def test_default_values(self):
        """Test default settings values."""
        # Clear any existing env vars
        with patch.dict(os.environ, {}, clear=True):
            settings = EmailSettings()

            assert settings.host == "smtp.gmail.com"
            assert settings.port == 587
            assert settings.username is None
            assert settings.password is None
            assert settings.from_email == "noreply@acgs2.local"
            assert settings.use_tls is True
            assert settings.timeout == 30.0

    def test_settings_from_environment(self):
        """Test settings are read from environment variables."""
        env_vars = {
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "465",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_FROM_EMAIL": "reports@example.com",
            "SMTP_USE_TLS": "false",
            "SMTP_TIMEOUT": "60.0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EmailSettings()

            assert settings.host == "mail.example.com"
            assert settings.port == 465
            assert settings.username == "testuser"
            assert settings.password == "testpass"
            assert settings.from_email == "reports@example.com"
            assert settings.use_tls is False
            assert settings.timeout == 60.0

    def test_is_configured_false_without_credentials(self):
        """Test is_configured returns False without credentials."""
        with patch.dict(os.environ, {}, clear=True):
            settings = EmailSettings()
            assert settings.is_configured() is False

    def test_is_configured_true_with_credentials(self):
        """Test is_configured returns True with all credentials."""
        env_vars = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = EmailSettings()
            assert settings.is_configured() is True


class TestEmailResult:
    """Tests for EmailResult dataclass."""

    def test_success_result(self):
        """Test creating a success result."""
        result = EmailResult(
            success=True,
            recipient="user@example.com",
            message_id="<123@example.com>",
            sent_at="2026-01-02T10:00:00+00:00",
        )

        assert result.success is True
        assert result.recipient == "user@example.com"
        assert result.message_id == "<123@example.com>"
        assert result.error_message is None
        assert result.sent_at == "2026-01-02T10:00:00+00:00"

    def test_failure_result(self):
        """Test creating a failure result."""
        result = EmailResult(
            success=False,
            recipient="user@example.com",
            error_message="Connection refused",
        )

        assert result.success is False
        assert result.recipient == "user@example.com"
        assert result.error_message == "Connection refused"
        assert result.message_id is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = EmailResult(
            success=True,
            recipient="user@example.com",
            message_id="<123>",
            sent_at="2026-01-02T10:00:00+00:00",
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["recipient"] == "user@example.com"
        assert result_dict["message_id"] == "<123>"
        assert result_dict["error_message"] is None
        assert result_dict["sent_at"] == "2026-01-02T10:00:00+00:00"


class TestEmailDeliveryError:
    """Tests for EmailDeliveryError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = EmailDeliveryError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.recipient is None
        assert error.original_error is None

    def test_error_with_recipient(self):
        """Test error with recipient information."""
        error = EmailDeliveryError(
            "Delivery failed",
            recipient="user@example.com",
        )
        assert error.recipient == "user@example.com"

    def test_error_with_original_exception(self):
        """Test error wrapping original exception."""
        original = smtplib.SMTPConnectError(421, "Service not available")
        error = EmailDeliveryError(
            "Connection failed",
            original_error=original,
        )
        assert error.original_error is original


class TestEmailConfigurationError:
    """Tests for EmailConfigurationError exception."""

    def test_configuration_error(self):
        """Test configuration error creation."""
        error = EmailConfigurationError("SMTP_HOST not configured")
        assert str(error) == "SMTP_HOST not configured"


class TestEmailService:
    """Tests for EmailService class."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    def test_init_with_default_settings(self):
        """Test initialization with default settings."""
        with patch.dict(os.environ, {"SMTP_HOST": "mail.test.com"}, clear=True):
            service = EmailService()
            assert service.settings.host == "mail.test.com"

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        custom_settings = EmailSettings()
        custom_settings.host = "custom.smtp.com"
        custom_settings.port = 2525

        service = EmailService(settings=custom_settings)
        assert service.settings.host == "custom.smtp.com"
        assert service.settings.port == 2525

    def test_validate_settings_missing_host(self):
        """Test validation fails without host."""
        settings = EmailSettings()
        settings.host = ""
        service = EmailService(settings=settings)

        with pytest.raises(EmailConfigurationError) as exc_info:
            service._validate_settings()

        assert "SMTP_HOST" in str(exc_info.value)

    def test_validate_settings_missing_from_email(self):
        """Test validation fails without from_email."""
        settings = EmailSettings()
        settings.host = "smtp.test.com"
        settings.from_email = ""
        service = EmailService(settings=settings)

        with pytest.raises(EmailConfigurationError) as exc_info:
            service._validate_settings()

        assert "SMTP_FROM_EMAIL" in str(exc_info.value)


class TestEmailServiceCreateMessage:
    """Tests for message creation in EmailService."""

    @pytest.fixture
    def service(self):
        """Create a test service instance."""
        settings = EmailSettings()
        settings.host = "smtp.test.com"
        settings.from_email = "sender@test.com"
        return EmailService(settings=settings)

    def test_create_pdf_message(self, service):
        """Test creating message with PDF attachment."""
        pdf_data = b"%PDF-1.4 test content"
        msg = service._create_message(
            recipient="user@example.com",
            attachment_data=pdf_data,
            report_name="SOC 2 Report",
            format="pdf",
        )

        assert isinstance(msg, MIMEMultipart)
        assert msg["From"] == "sender@test.com"
        assert msg["To"] == "user@example.com"
        assert "SOC 2 Report" in msg["Subject"]

        # Check for attachment
        payloads = msg.get_payload()
        assert len(payloads) == 2  # body + attachment

        # Check attachment is PDF
        attachment = payloads[1]
        assert attachment.get_content_subtype() == "pdf"
        assert "SOC_2_Report" in attachment.get_filename()
        assert ".pdf" in attachment.get_filename()

    def test_create_csv_message(self, service):
        """Test creating message with CSV attachment."""
        csv_data = b"id,name,value\n1,test,100"
        msg = service._create_message(
            recipient="user@example.com",
            attachment_data=csv_data,
            report_name="Compliance Data",
            format="csv",
        )

        payloads = msg.get_payload()
        attachment = payloads[1]

        assert attachment.get_content_subtype() == "csv"
        assert ".csv" in attachment.get_filename()

    def test_message_subject_includes_date(self, service):
        """Test message subject includes current date."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        msg = service._create_message(
            recipient="user@example.com",
            attachment_data=b"test",
            report_name="Test Report",
            format="pdf",
        )

        assert today in msg["Subject"]

    def test_message_with_custom_body(self, service):
        """Test creating message with custom body text."""
        custom_body = "Custom message body"
        msg = service._create_message(
            recipient="user@example.com",
            attachment_data=b"test",
            report_name="Test Report",
            format="pdf",
            body_text=custom_body,
        )

        body_payload = msg.get_payload()[0]
        assert custom_body in body_payload.get_payload()

    def test_sanitize_filename_special_chars(self, service):
        """Test that special characters are sanitized in filename."""
        msg = service._create_message(
            recipient="user@example.com",
            attachment_data=b"test",
            report_name="Report/With:Special*Chars?",
            format="pdf",
        )

        attachment = msg.get_payload()[1]
        filename = attachment.get_filename()

        # No special characters should be in filename
        assert "/" not in filename
        assert ":" not in filename
        assert "*" not in filename
        assert "?" not in filename


class TestEmailServiceSendEmail:
    """Tests for send_email method with mocked SMTP."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = EmailSettings()
        settings.host = "smtp.test.com"
        settings.port = 587
        settings.username = "testuser"
        settings.password = "testpass"
        settings.from_email = "sender@test.com"
        return settings

    @pytest.fixture
    def service(self, settings):
        """Create service with test settings."""
        return EmailService(settings=settings)

    def test_successful_send(self, service):
        """Test successful email send."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = service.send_email(
                recipient="user@example.com",
                attachment_data=b"test data",
                report_name="Test Report",
                format="pdf",
            )

            assert result.success is True
            assert result.recipient == "user@example.com"
            assert result.sent_at is not None
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("testuser", "testpass")
            mock_server.send_message.assert_called_once()

    def test_send_without_tls(self, settings):
        """Test sending without TLS."""
        settings.use_tls = False
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = service.send_email(
                recipient="user@example.com",
                attachment_data=b"test",
                report_name="Test",
                format="pdf",
            )

            assert result.success is True
            mock_server.starttls.assert_not_called()

    def test_send_without_auth(self, settings):
        """Test sending without authentication."""
        settings.username = None
        settings.password = None
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = service.send_email(
                recipient="user@example.com",
                attachment_data=b"test",
                report_name="Test",
                format="pdf",
            )

            assert result.success is True
            mock_server.login.assert_not_called()

    def test_authentication_error(self, service):
        """Test handling of authentication error."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
                535, b"Authentication failed"
            )
            mock_smtp.return_value.__enter__.return_value = mock_server

            with pytest.raises(EmailDeliveryError) as exc_info:
                service.send_email(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Test",
                    format="pdf",
                )

            assert "authentication" in str(exc_info.value).lower()
            assert exc_info.value.recipient == "user@example.com"

    def test_connection_error(self, service):
        """Test handling of connection error."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Service not available")

            with pytest.raises(EmailDeliveryError) as exc_info:
                service.send_email(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Test",
                    format="pdf",
                )

            assert "connect" in str(exc_info.value).lower()

    def test_recipient_refused_error(self, service):
        """Test handling of recipient refused error."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused(
                {"user@example.com": (550, b"User unknown")}
            )
            mock_smtp.return_value.__enter__.return_value = mock_server

            with pytest.raises(EmailDeliveryError) as exc_info:
                service.send_email(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Test",
                    format="pdf",
                )

            assert "refused" in str(exc_info.value).lower()

    def test_timeout_error(self, service):
        """Test handling of timeout error."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = TimeoutError("Connection timed out")

            with pytest.raises(EmailDeliveryError) as exc_info:
                service.send_email(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Test",
                    format="pdf",
                )

            assert "timeout" in str(exc_info.value).lower()

    def test_generic_smtp_error(self, service):
        """Test handling of generic SMTP error."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPException("Unknown error")
            mock_smtp.return_value.__enter__.return_value = mock_server

            with pytest.raises(EmailDeliveryError) as exc_info:
                service.send_email(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Test",
                    format="pdf",
                )

            assert "SMTP error" in str(exc_info.value)


class TestEmailServiceStaticMethods:
    """Tests for static class methods."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    def test_send_report_email_success(self):
        """Test static send_report_email method."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_EMAIL": "sender@test.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = EmailService.send_report_email(
                    recipient="user@example.com",
                    pdf_bytes=b"%PDF-1.4 test",
                    report_name="SOC 2 Compliance Report",
                    format="pdf",
                )

                assert result.success is True
                assert result.recipient == "user@example.com"

    def test_send_report_email_csv_format(self):
        """Test send_report_email with CSV format."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_EMAIL": "sender@test.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = EmailService.send_report_email(
                    recipient="user@example.com",
                    pdf_bytes=b"id,name\n1,test",
                    report_name="Data Export",
                    format="csv",
                )

                assert result.success is True

    def test_send_report_to_multiple_success(self):
        """Test sending report to multiple recipients."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_EMAIL": "sender@test.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                results = EmailService.send_report_to_multiple(
                    recipients=["user1@example.com", "user2@example.com"],
                    pdf_bytes=b"test",
                    report_name="Test Report",
                    format="pdf",
                )

                assert len(results) == 2
                assert all(r.success for r in results)
                assert results[0].recipient == "user1@example.com"
                assert results[1].recipient == "user2@example.com"

    def test_send_report_to_multiple_partial_failure(self):
        """Test partial failure when sending to multiple recipients."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_EMAIL": "sender@test.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                # First call succeeds, second fails
                mock_server.send_message.side_effect = [
                    None,  # Success for first
                    smtplib.SMTPRecipientsRefused({"user2@example.com": (550, b"Unknown")}),
                ]
                mock_smtp.return_value.__enter__.return_value = mock_server

                results = EmailService.send_report_to_multiple(
                    recipients=["user1@example.com", "user2@example.com"],
                    pdf_bytes=b"test",
                    report_name="Test Report",
                    format="pdf",
                )

                assert len(results) == 2
                assert results[0].success is True
                assert results[1].success is False
                assert results[1].error_message is not None


class TestEmailServiceDefaultBody:
    """Tests for default email body generation."""

    @pytest.fixture
    def service(self):
        """Create a test service instance."""
        settings = EmailSettings()
        settings.host = "smtp.test.com"
        settings.from_email = "sender@test.com"
        return EmailService(settings=settings)

    def test_pdf_body_text(self, service):
        """Test default body text for PDF format."""
        body = service._get_default_body_text("SOC 2 Report", "pdf")

        assert "SOC 2 Report" in body
        assert "PDF document" in body
        assert "ACGS-2 Audit Service" in body
        assert "cdd01ef066bc6cf2" in body  # Constitutional hash

    def test_csv_body_text(self, service):
        """Test default body text for CSV format."""
        body = service._get_default_body_text("Data Export", "csv")

        assert "Data Export" in body
        assert "CSV data" in body

    def test_body_includes_timestamp(self, service):
        """Test body includes generation timestamp."""
        body = service._get_default_body_text("Test", "pdf")
        assert "UTC" in body


class TestEmailServiceIntegration:
    """Integration-style tests for email service workflow."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    def test_full_pdf_report_email_workflow(self):
        """Test complete workflow for sending a PDF report."""
        # Simulate a real PDF header
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog>>\nendobj\n"

        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "reports@company.com",
            "SMTP_PASSWORD": "secure-app-password",
            "SMTP_FROM_EMAIL": "compliance@company.com",
            "SMTP_USE_TLS": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = EmailService.send_report_email(
                    recipient="ciso@company.com",
                    pdf_bytes=pdf_content,
                    report_name="Monthly SOC 2 Type II Report",
                    format="pdf",
                )

                # Verify result
                assert result.success is True
                assert result.recipient == "ciso@company.com"
                assert result.sent_at is not None

                # Verify SMTP calls
                mock_smtp.assert_called_once_with(
                    "smtp.test.com",
                    587,
                    timeout=30.0,
                )
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once_with(
                    "reports@company.com",
                    "secure-app-password",
                )
                mock_server.send_message.assert_called_once()

                # Verify message structure
                sent_message = mock_server.send_message.call_args[0][0]
                assert isinstance(sent_message, MIMEMultipart)
                assert sent_message["From"] == "compliance@company.com"
                assert sent_message["To"] == "ciso@company.com"
                assert "Monthly SOC 2 Type II Report" in sent_message["Subject"]

    def test_full_csv_report_email_workflow(self):
        """Test complete workflow for sending a CSV report."""
        csv_content = (
            b"timestamp,agent_id,decision,risk_score\n"
            b"2026-01-02T10:00:00,agent-001,ALLOW,0.15\n"
            b"2026-01-02T10:05:00,agent-002,DENY,0.85\n"
        )

        env_vars = {
            "SMTP_HOST": "smtp.company.com",
            "SMTP_USERNAME": "reports",
            "SMTP_PASSWORD": "password",
            "SMTP_FROM_EMAIL": "audit@company.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = EmailService.send_report_email(
                    recipient="analyst@company.com",
                    pdf_bytes=csv_content,
                    report_name="Weekly Decision Log Export",
                    format="csv",
                )

                assert result.success is True

                # Verify CSV attachment
                sent_message = mock_server.send_message.call_args[0][0]
                attachment = sent_message.get_payload()[1]
                assert attachment.get_content_subtype() == "csv"
                assert ".csv" in attachment.get_filename()
