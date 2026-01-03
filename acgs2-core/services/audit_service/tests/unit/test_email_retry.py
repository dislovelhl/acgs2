"""
Unit tests for EmailService retry logic with exponential backoff.

Tests cover:
- RetryConfig configuration and delay calculation
- Exponential backoff behavior
- Retryable vs non-retryable error handling
- Retry exhaustion and EmailRetryExhaustedError
- Success after retries
- Multiple recipient retry handling
"""

import os
import smtplib
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the service path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.email_service import (  # noqa: E402
    EmailDeliveryError,
    EmailRetryExhaustedError,
    EmailService,
    EmailSettings,
    RetryConfig,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self):
        """Test default retry configuration values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.jitter is True
        assert config.jitter_factor == 0.1

    def test_custom_values(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=1.0,
            max_delay=30.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.jitter is False

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=2.0, jitter=False)

        # 2^0 * 2 = 2
        assert config.calculate_delay(0) == 2.0
        # 2^1 * 2 = 4
        assert config.calculate_delay(1) == 4.0
        # 2^2 * 2 = 8
        assert config.calculate_delay(2) == 8.0
        # 2^3 * 2 = 16
        assert config.calculate_delay(3) == 16.0

    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=2.0, max_delay=10.0, jitter=False)

        # Attempt 4: 2^4 * 2 = 32, but capped at 10
        assert config.calculate_delay(4) == 10.0
        # Attempt 5: 2^5 * 2 = 64, but capped at 10
        assert config.calculate_delay(5) == 10.0

    def test_calculate_delay_with_jitter(self):
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(base_delay=2.0, jitter=True, jitter_factor=0.1)

        delays = [config.calculate_delay(0) for _ in range(10)]

        # Base delay should be 2.0, with jitter up to 0.2
        for delay in delays:
            assert 2.0 <= delay <= 2.2

        # Delays should not all be identical (with high probability)
        assert len(set(delays)) > 1

    def test_is_retryable_connection_error(self):
        """Test that connection errors are retryable."""
        config = RetryConfig()

        assert config.is_retryable(smtplib.SMTPConnectError(421, "Service unavailable"))
        assert config.is_retryable(smtplib.SMTPServerDisconnected("Connection lost"))
        assert config.is_retryable(TimeoutError("Connection timed out"))
        assert config.is_retryable(ConnectionError("Connection refused"))

    def test_is_retryable_authentication_error(self):
        """Test that authentication errors are NOT retryable by default."""
        config = RetryConfig()

        # SMTPAuthenticationError is not in the default retryable list
        assert not config.is_retryable(smtplib.SMTPAuthenticationError(535, b"Auth failed"))

    def test_is_retryable_recipient_refused(self):
        """Test that recipient refused errors are NOT retryable by default."""
        config = RetryConfig()

        # SMTPRecipientsRefused is not in the default retryable list
        assert not config.is_retryable(
            smtplib.SMTPRecipientsRefused({"user@example.com": (550, b"Unknown")})
        )

    def test_is_retryable_custom_exceptions(self):
        """Test custom retryable exception configuration."""
        config = RetryConfig(retryable_exceptions=(ValueError, TypeError))

        assert config.is_retryable(ValueError("test"))
        assert config.is_retryable(TypeError("test"))
        assert not config.is_retryable(smtplib.SMTPConnectError(421, "test"))


class TestEmailRetryExhaustedError:
    """Tests for EmailRetryExhaustedError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = EmailRetryExhaustedError("All retries failed")

        assert str(error) == "All retries failed"
        assert error.recipient is None
        assert error.attempts == 0
        assert error.last_error is None

    def test_error_with_details(self):
        """Test error with full details."""
        last_err = smtplib.SMTPConnectError(421, "Service unavailable")
        error = EmailRetryExhaustedError(
            message="Failed after 4 attempts",
            recipient="user@example.com",
            attempts=4,
            last_error=last_err,
        )

        assert error.recipient == "user@example.com"
        assert error.attempts == 4
        assert error.last_error is last_err


class TestEmailServiceRetry:
    """Tests for EmailService retry methods."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

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

    def test_send_with_retry_success_first_attempt(self, service):
        """Test successful email on first attempt."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = service.send_email_with_retry(
                recipient="user@example.com",
                attachment_data=b"test data",
                report_name="Test Report",
                format="pdf",
            )

            assert result.success is True
            assert result.recipient == "user@example.com"
            mock_server.send_message.assert_called_once()

    def test_send_with_retry_success_after_retries(self, service):
        """Test successful email after transient failures."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Fail twice with retryable error, then succeed
            connect_error = smtplib.SMTPConnectError(421, "Service unavailable")
            mock_smtp.side_effect = [
                connect_error,
                connect_error,
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            # Use short delays for faster testing
            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                result = service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test data",
                    report_name="Test Report",
                    format="pdf",
                    retry_config=config,
                )

            assert result.success is True
            assert mock_smtp.call_count == 3

    def test_send_with_retry_exhausted(self, service):
        """Test retry exhaustion raises EmailRetryExhaustedError."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            # Always fail with retryable error
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Service unavailable")

            config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                with pytest.raises(EmailRetryExhaustedError) as exc_info:
                    service.send_email_with_retry(
                        recipient="user@example.com",
                        attachment_data=b"test data",
                        report_name="Test Report",
                        format="pdf",
                        retry_config=config,
                    )

            error = exc_info.value
            assert error.recipient == "user@example.com"
            assert error.attempts == 3  # Initial + 2 retries
            assert mock_smtp.call_count == 3

    def test_send_with_retry_non_retryable_error(self, service):
        """Test non-retryable errors are raised immediately."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
            mock_smtp.return_value.__enter__.return_value = mock_server

            with pytest.raises(EmailDeliveryError) as exc_info:
                service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test data",
                    report_name="Test Report",
                    format="pdf",
                )

            assert "authentication" in str(exc_info.value).lower()
            # Should only try once for non-retryable errors
            mock_smtp.assert_called_once()

    def test_send_with_retry_exponential_backoff_delays(self, service):
        """Test that retry delays follow exponential backoff."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Service unavailable")

            config = RetryConfig(max_retries=3, base_delay=1.0, jitter=False)

            with patch("app.services.email_service.time.sleep") as mock_sleep:
                with pytest.raises(EmailRetryExhaustedError):
                    service.send_email_with_retry(
                        recipient="user@example.com",
                        attachment_data=b"test data",
                        report_name="Test Report",
                        format="pdf",
                        retry_config=config,
                    )

                # Check delay calls: 1.0, 2.0, 4.0 (exponential)
                assert mock_sleep.call_count == 3
                delays = [call[0][0] for call in mock_sleep.call_args_list]
                assert delays == [1.0, 2.0, 4.0]

    def test_send_with_retry_timeout_is_retryable(self, service):
        """Test that timeout errors trigger retries."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            timeout_error = TimeoutError("Connection timed out")
            mock_server = MagicMock()

            # Fail with timeout first, then succeed
            mock_smtp.side_effect = [
                timeout_error,
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                result = service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test data",
                    report_name="Test Report",
                    format="pdf",
                    retry_config=config,
                )

            assert result.success is True
            assert mock_smtp.call_count == 2

    def test_send_with_retry_server_disconnect_is_retryable(self, service):
        """Test that server disconnect errors trigger retries."""
        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            disconnect_error = smtplib.SMTPServerDisconnected("Lost connection")
            mock_server = MagicMock()

            mock_smtp.side_effect = [
                disconnect_error,
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                result = service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test data",
                    report_name="Test Report",
                    format="pdf",
                    retry_config=config,
                )

            assert result.success is True


class TestEmailServiceRetryStaticMethods:
    """Tests for static retry methods."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    def test_send_report_email_with_retry_success(self):
        """Test static send_report_email_with_retry method."""
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

                result = EmailService.send_report_email_with_retry(
                    recipient="user@example.com",
                    pdf_bytes=b"%PDF-1.4 test",
                    report_name="SOC 2 Report",
                    format="pdf",
                )

                assert result.success is True
                assert result.recipient == "user@example.com"

    def test_send_report_email_with_retry_custom_config(self):
        """Test static method with custom retry config."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_EMAIL": "sender@test.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
                mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Unavailable")

                config = RetryConfig(max_retries=1, base_delay=0.01, jitter=False)

                with patch("app.services.email_service.time.sleep"):
                    with pytest.raises(EmailRetryExhaustedError) as exc_info:
                        EmailService.send_report_email_with_retry(
                            recipient="user@example.com",
                            pdf_bytes=b"test",
                            report_name="Report",
                            format="pdf",
                            retry_config=config,
                        )

                assert exc_info.value.attempts == 2

    def test_send_report_to_multiple_with_retry_success(self):
        """Test sending to multiple recipients with retry."""
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

                results = EmailService.send_report_to_multiple_with_retry(
                    recipients=["user1@example.com", "user2@example.com"],
                    pdf_bytes=b"test",
                    report_name="Report",
                    format="pdf",
                )

                assert len(results) == 2
                assert all(r.success for r in results)

    def test_send_report_to_multiple_with_retry_partial_failure(self):
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
                mock_smtp.return_value.__enter__.return_value = mock_server

                # First succeeds, second always fails with non-retryable error
                mock_server.send_message.side_effect = [
                    None,  # First succeeds
                    smtplib.SMTPRecipientsRefused({"user2@example.com": (550, b"Unknown")}),
                ]

                results = EmailService.send_report_to_multiple_with_retry(
                    recipients=["user1@example.com", "user2@example.com"],
                    pdf_bytes=b"test",
                    report_name="Report",
                    format="pdf",
                )

                assert len(results) == 2
                assert results[0].success is True
                assert results[1].success is False


class TestEmailRetryLogging:
    """Tests for retry logging behavior."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = EmailSettings()
        settings.host = "smtp.test.com"
        settings.username = "testuser"
        settings.password = "testpass"
        settings.from_email = "sender@test.com"
        return settings

    def test_logs_retry_attempts(self, settings, caplog):
        """Test that retry attempts are logged."""
        import logging

        caplog.set_level(logging.INFO)

        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Unavailable")

            config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                with pytest.raises(EmailRetryExhaustedError):
                    service.send_email_with_retry(
                        recipient="user@example.com",
                        attachment_data=b"test",
                        report_name="Report",
                        retry_config=config,
                    )

        # Check that attempts were logged
        assert "attempt 1/3" in caplog.text
        assert "attempt 2/3" in caplog.text
        assert "attempt 3/3" in caplog.text

    def test_logs_success_after_retry(self, settings, caplog):
        """Test that success after retry is logged."""
        import logging

        caplog.set_level(logging.INFO)

        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.side_effect = [
                smtplib.SMTPConnectError(421, "Unavailable"),
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Report",
                    retry_config=config,
                )

        assert "delivered successfully after 1 retries" in caplog.text

    def test_logs_exhaustion_error(self, settings, caplog):
        """Test that exhaustion is logged as error."""
        import logging

        caplog.set_level(logging.ERROR)

        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Unavailable")

            config = RetryConfig(max_retries=1, base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                with pytest.raises(EmailRetryExhaustedError):
                    service.send_email_with_retry(
                        recipient="user@example.com",
                        attachment_data=b"test",
                        report_name="Report",
                        retry_config=config,
                    )

        assert "failed after 2 attempts" in caplog.text


class TestEmailRetryEdgeCases:
    """Tests for edge cases in retry logic."""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset cached settings before each test."""
        EmailService.reset_default_settings()
        yield
        EmailService.reset_default_settings()

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = EmailSettings()
        settings.host = "smtp.test.com"
        settings.username = "testuser"
        settings.password = "testpass"
        settings.from_email = "sender@test.com"
        return settings

    def test_zero_retries(self, settings):
        """Test with zero retries (only one attempt)."""
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Unavailable")

            config = RetryConfig(max_retries=0, base_delay=0.01)

            with pytest.raises(EmailRetryExhaustedError) as exc_info:
                service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Report",
                    retry_config=config,
                )

            assert exc_info.value.attempts == 1
            mock_smtp.assert_called_once()

    def test_os_error_is_retryable(self, settings):
        """Test that OSError (network issues) triggers retry."""
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.side_effect = [
                OSError("Network unreachable"),
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                result = service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Report",
                    retry_config=config,
                )

            assert result.success is True
            assert mock_smtp.call_count == 2

    def test_delay_cap_enforced(self, settings):
        """Test that max_delay cap is enforced."""
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Unavailable")

            # With base_delay=10 and max_delay=15, delays should be capped
            config = RetryConfig(
                max_retries=4,
                base_delay=10.0,
                max_delay=15.0,
                jitter=False,
            )

            with patch("app.services.email_service.time.sleep") as mock_sleep:
                with pytest.raises(EmailRetryExhaustedError):
                    service.send_email_with_retry(
                        recipient="user@example.com",
                        attachment_data=b"test",
                        report_name="Report",
                        retry_config=config,
                    )

                # Delays: 10, 15 (capped from 20), 15 (capped from 40), 15 (capped)
                delays = [call[0][0] for call in mock_sleep.call_args_list]
                assert delays == [10.0, 15.0, 15.0, 15.0]

    def test_smtp_response_exception_is_retryable(self, settings):
        """Test that SMTPResponseException triggers retry."""
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()

            # SMTPResponseException with 4xx code (temporary failure)
            response_error = smtplib.SMTPResponseException(451, b"Try again later")
            mock_smtp.side_effect = [
                response_error,
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                result = service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Report",
                    retry_config=config,
                )

            assert result.success is True

    def test_intermittent_failures(self, settings):
        """Test handling of intermittent failures."""
        service = EmailService(settings=settings)

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()

            # Fail, succeed, fail pattern (but we'll succeed before second fail)
            mock_smtp.side_effect = [
                smtplib.SMTPConnectError(421, "Unavailable"),
                MagicMock(__enter__=MagicMock(return_value=mock_server)),
            ]

            config = RetryConfig(base_delay=0.01, jitter=False)

            with patch("app.services.email_service.time.sleep"):
                result = service.send_email_with_retry(
                    recipient="user@example.com",
                    attachment_data=b"test",
                    report_name="Report",
                    retry_config=config,
                )

            assert result.success is True
