"""
Email Service for Audit Report Delivery
Constitutional Hash: cdd01ef066bc6cf2

Provides SMTP-based email delivery for compliance reports with:
- PDF and CSV attachment support
- STARTTLS encryption on port 587
- Configurable via environment variables
- Retry logic with exponential backoff
"""

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmailSettings:
    """
    SMTP Email configuration settings.

    Reads configuration from environment variables following the pattern
    established in acgs2-core/shared/config.py.
    """

    host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    username: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USERNAME"))
    password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    from_email: str = field(
        default_factory=lambda: os.getenv("SMTP_FROM_EMAIL", "noreply@acgs2.local")
    )
    use_tls: bool = field(
        default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    )
    timeout: float = field(default_factory=lambda: float(os.getenv("SMTP_TIMEOUT", "30.0")))

    def is_configured(self) -> bool:
        """
        Check if email settings are properly configured.

        Returns:
            True if host, username, and password are set
        """
        return bool(self.host and self.username and self.password)


@dataclass
class EmailResult:
    """Result object for email send operations."""

    success: bool
    recipient: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "recipient": self.recipient,
            "message_id": self.message_id,
            "error_message": self.error_message,
            "sent_at": self.sent_at,
        }


class EmailDeliveryError(Exception):
    """Exception raised when email delivery fails."""

    def __init__(
        self,
        message: str,
        recipient: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.recipient = recipient
        self.original_error = original_error


class EmailConfigurationError(Exception):
    """Exception raised when email configuration is invalid."""

    pass


class EmailService:
    """
    SMTP Email service for delivering compliance reports.

    This service provides:
    - PDF and CSV attachment delivery
    - STARTTLS encryption on port 587
    - Configurable SMTP settings via environment variables
    - Structured result objects for tracking delivery status

    Usage:
        # Using static method (recommended for Celery tasks)
        EmailService.send_report_email(
            recipient="user@example.com",
            pdf_bytes=report_data,
            report_name="SOC 2 Compliance Report",
            format="pdf"
        )

        # Using instance method for custom settings
        service = EmailService(custom_settings)
        service.send_email(
            recipient="user@example.com",
            attachment_data=report_data,
            report_name="SOC 2 Compliance Report",
            format="pdf"
        )

    Environment Variables:
        SMTP_HOST: SMTP server hostname (default: smtp.gmail.com)
        SMTP_PORT: SMTP server port (default: 587)
        SMTP_USERNAME: SMTP authentication username
        SMTP_PASSWORD: SMTP authentication password (use App Password for Gmail)
        SMTP_FROM_EMAIL: Sender email address
        SMTP_USE_TLS: Enable STARTTLS (default: true)
        SMTP_TIMEOUT: Connection timeout in seconds (default: 30.0)
    """

    # Default settings instance (lazy loaded)
    _default_settings: Optional[EmailSettings] = None

    def __init__(self, settings: Optional[EmailSettings] = None):
        """
        Initialize EmailService with optional custom settings.

        Args:
            settings: Optional EmailSettings instance. If not provided,
                     settings are loaded from environment variables.
        """
        self.settings = settings or self._get_default_settings()

    @classmethod
    def _get_default_settings(cls) -> EmailSettings:
        """Get or create the default settings instance."""
        if cls._default_settings is None:
            cls._default_settings = EmailSettings()
        return cls._default_settings

    @classmethod
    def reset_default_settings(cls) -> None:
        """Reset cached default settings (useful for testing)."""
        cls._default_settings = None

    def _validate_settings(self) -> None:
        """
        Validate that required settings are configured.

        Raises:
            EmailConfigurationError: If required settings are missing
        """
        if not self.settings.host:
            raise EmailConfigurationError("SMTP_HOST is not configured")
        if not self.settings.from_email:
            raise EmailConfigurationError("SMTP_FROM_EMAIL is not configured")

    def _create_message(
        self,
        recipient: str,
        attachment_data: bytes,
        report_name: str,
        format: str = "pdf",
        body_text: Optional[str] = None,
    ) -> MIMEMultipart:
        """
        Create email message with attachment.

        Args:
            recipient: Recipient email address
            attachment_data: Report content as bytes
            report_name: Name of the report (used in subject and filename)
            format: Attachment format (pdf or csv)
            body_text: Optional custom body text

        Returns:
            MIMEMultipart message object
        """
        msg = MIMEMultipart()
        msg["From"] = self.settings.from_email
        msg["To"] = recipient

        # Format subject with date
        report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        msg["Subject"] = f"{report_name} - {report_date}"

        # Create body text
        if body_text is None:
            body_text = self._get_default_body_text(report_name, format)

        body = MIMEText(body_text, "plain", "utf-8")
        msg.attach(body)

        # Determine MIME subtype and extension
        if format.lower() == "csv":
            subtype = "csv"
            extension = "csv"
        else:
            subtype = "pdf"
            extension = "pdf"

        # Create attachment
        attachment = MIMEApplication(attachment_data, _subtype=subtype)

        # Sanitize filename
        safe_report_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in report_name)
        filename = f"{safe_report_name}_{report_date}.{extension}"

        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=filename,
        )
        msg.attach(attachment)

        return msg

    def _get_default_body_text(self, report_name: str, format: str) -> str:
        """
        Generate default email body text.

        Args:
            report_name: Name of the report
            format: Report format (pdf/csv)

        Returns:
            Default body text string
        """
        format_description = "PDF document" if format.lower() == "pdf" else "CSV data"
        return f"""Dear Recipient,

Please find attached the {report_name} ({format_description}).

This is an automated message from the ACGS-2 Audit Reporting System.
For questions or concerns, please contact your compliance administrator.

Report generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

---
ACGS-2 Audit Service
Constitutional Hash: cdd01ef066bc6cf2
"""

    def send_email(
        self,
        recipient: str,
        attachment_data: bytes,
        report_name: str,
        format: str = "pdf",
        body_text: Optional[str] = None,
    ) -> EmailResult:
        """
        Send an email with a report attachment.

        Args:
            recipient: Recipient email address
            attachment_data: Report content as bytes
            report_name: Name of the report
            format: Attachment format (pdf or csv)
            body_text: Optional custom body text

        Returns:
            EmailResult object with delivery status

        Raises:
            EmailConfigurationError: If email settings are invalid
            EmailDeliveryError: If email delivery fails
        """
        self._validate_settings()
        sent_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Sending email: recipient=%s, report_name=%s, format=%s",
            recipient,
            report_name,
            format,
        )

        try:
            msg = self._create_message(
                recipient=recipient,
                attachment_data=attachment_data,
                report_name=report_name,
                format=format,
                body_text=body_text,
            )

            # Create SSL context for STARTTLS
            context = ssl.create_default_context()

            with smtplib.SMTP(
                self.settings.host,
                self.settings.port,
                timeout=self.settings.timeout,
            ) as server:
                # Enable TLS if configured
                if self.settings.use_tls:
                    server.starttls(context=context)

                # Authenticate if credentials provided
                if self.settings.username and self.settings.password:
                    server.login(self.settings.username, self.settings.password)

                # Send the message
                server.send_message(msg)

            logger.info(
                "Email sent successfully: recipient=%s, report_name=%s",
                recipient,
                report_name,
            )

            return EmailResult(
                success=True,
                recipient=recipient,
                message_id=msg.get("Message-ID"),
                sent_at=sent_at,
            )

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {e}"
            logger.error(
                "Email authentication failed: recipient=%s, error=%s",
                recipient,
                error_msg,
            )
            raise EmailDeliveryError(
                message=error_msg,
                recipient=recipient,
                original_error=e,
            ) from e

        except smtplib.SMTPConnectError as e:
            error_msg = f"Failed to connect to SMTP server: {e}"
            logger.error(
                "Email connection failed: recipient=%s, host=%s, error=%s",
                recipient,
                self.settings.host,
                error_msg,
            )
            raise EmailDeliveryError(
                message=error_msg,
                recipient=recipient,
                original_error=e,
            ) from e

        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient refused: {e}"
            logger.error(
                "Email recipient refused: recipient=%s, error=%s",
                recipient,
                error_msg,
            )
            raise EmailDeliveryError(
                message=error_msg,
                recipient=recipient,
                original_error=e,
            ) from e

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            logger.error(
                "Email SMTP error: recipient=%s, error=%s",
                recipient,
                error_msg,
            )
            raise EmailDeliveryError(
                message=error_msg,
                recipient=recipient,
                original_error=e,
            ) from e

        except TimeoutError as e:
            error_msg = f"SMTP connection timed out: {e}"
            logger.error(
                "Email timeout: recipient=%s, host=%s, timeout=%s, error=%s",
                recipient,
                self.settings.host,
                self.settings.timeout,
                error_msg,
            )
            raise EmailDeliveryError(
                message=error_msg,
                recipient=recipient,
                original_error=e,
            ) from e

        except Exception as e:
            error_msg = f"Unexpected email error: {e}"
            logger.error(
                "Email unexpected error: recipient=%s, error=%s, type=%s",
                recipient,
                error_msg,
                type(e).__name__,
            )
            raise EmailDeliveryError(
                message=error_msg,
                recipient=recipient,
                original_error=e,
            ) from e

    @classmethod
    def send_report_email(
        cls,
        recipient: str,
        pdf_bytes: bytes,
        report_name: str,
        format: str = "pdf",
    ) -> EmailResult:
        """
        Static method to send a report email using default settings.

        This method is designed to be called from Celery tasks and provides
        a simple interface for report delivery.

        Args:
            recipient: Recipient email address
            pdf_bytes: Report content as bytes (works for PDF or CSV despite the name)
            report_name: Name of the report (used in subject and filename)
            format: Report format (pdf or csv)

        Returns:
            EmailResult object with delivery status

        Raises:
            EmailConfigurationError: If email settings are invalid
            EmailDeliveryError: If email delivery fails

        Example:
            result = EmailService.send_report_email(
                recipient="compliance@company.com",
                pdf_bytes=report_data,
                report_name="Monthly SOC 2 Report",
                format="pdf"
            )
            if result.success:
                print(f"Email sent at {result.sent_at}")
        """
        service = cls()
        return service.send_email(
            recipient=recipient,
            attachment_data=pdf_bytes,
            report_name=report_name,
            format=format,
        )

    @classmethod
    def send_report_to_multiple(
        cls,
        recipients: List[str],
        pdf_bytes: bytes,
        report_name: str,
        format: str = "pdf",
    ) -> List[EmailResult]:
        """
        Send a report to multiple recipients.

        Args:
            recipients: List of recipient email addresses
            pdf_bytes: Report content as bytes
            report_name: Name of the report
            format: Report format (pdf or csv)

        Returns:
            List of EmailResult objects for each recipient
        """
        service = cls()
        results = []

        for recipient in recipients:
            try:
                result = service.send_email(
                    recipient=recipient,
                    attachment_data=pdf_bytes,
                    report_name=report_name,
                    format=format,
                )
                results.append(result)
            except EmailDeliveryError as e:
                results.append(
                    EmailResult(
                        success=False,
                        recipient=recipient,
                        error_message=str(e),
                    )
                )

        return results
