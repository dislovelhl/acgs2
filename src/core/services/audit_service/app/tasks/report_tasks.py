"""
Report Generation Celery Tasks for Audit Service
Constitutional Hash: cdd01ef066bc6cf2

Provides background task execution for:
- Scheduled report generation (PDF/CSV)
- Email delivery of generated reports
- Retry logic with exponential backoff
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)

# Report storage path from environment
REPORT_STORAGE_PATH = os.getenv("REPORT_STORAGE_PATH", "/tmp/reports")


@dataclass
class ReportGenerationResult:
    """Result object for report generation tasks."""

    success: bool
    report_id: str
    tenant_id: str
    framework: str
    format: str
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    generated_at: Optional[str] = None
    error_message: Optional[str] = None
    email_sent: bool = False
    email_recipients: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for Celery serialization."""
        return {
            "success": self.success,
            "report_id": self.report_id,
            "tenant_id": self.tenant_id,
            "framework": self.framework,
            "format": self.format,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "generated_at": self.generated_at,
            "error_message": self.error_message,
            "email_sent": self.email_sent,
            "email_recipients": self.email_recipients,
        }


def _get_report_generator():
    """
    Lazy import of ComplianceReportGenerator to avoid circular imports.

    Returns:
        ComplianceReportGenerator class
    """
    try:
        from app.services.report_generator import ComplianceReportGenerator

        return ComplianceReportGenerator
    except ImportError:
        # Fallback for different module contexts
        from ..services.report_generator import ComplianceReportGenerator

        return ComplianceReportGenerator


def _get_email_service():
    """
    Lazy import of EmailService (may not exist yet).

    Returns:
        EmailService class or None if not available
    """
    try:
        from app.services.email_service import EmailService

        return EmailService
    except ImportError:
        try:
            from ..services.email_service import EmailService

            return EmailService
        except ImportError:
            logger.warning("EmailService not available - email delivery disabled")
            return None


def _ensure_storage_directory():
    """Ensure the report storage directory exists."""
    os.makedirs(REPORT_STORAGE_PATH, exist_ok=True)


def _generate_report_id(tenant_id: str, framework: str) -> str:
    """Generate a unique report ID."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"RPT-{tenant_id[:8].upper()}-{framework.upper()}-{timestamp}"


async def _fetch_logs_for_tenant(
    tenant_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch decision logs for a tenant.

    Integrates with the audit ledger to fetch real decision logs with date filtering.

    Args:
        tenant_id: Target tenant identifier
        start_date: Optional start date for log filtering
        end_date: Optional end date for log filtering

    Returns:
        List of decision log dictionaries
    """
    from ..core.audit_ledger import get_audit_ledger

    try:
        logger.info(
            "Fetching logs for tenant=%s, start_date=%s, end_date=%s",
            tenant_id,
            start_date,
            end_date,
        )

        ledger = await get_audit_ledger()

        # Filter ledger entries by tenant and date range
        filtered_logs = []

        # Access ledger entries directly for full history (or as much as is in memory/persistence)
        # In a production environment with millions of logs, this would be a database query.
        for entry in ledger.entries:
            vr = entry.validation_result
            metadata = vr.metadata

            # Check tenant filter
            if tenant_id and tenant_id != "all" and tenant_id != "default":
                log_tenant = metadata.get("tenant_id")
                if log_tenant != tenant_id:
                    continue

            # Check date range filter
            if entry.timestamp:
                log_datetime = datetime.fromtimestamp(entry.timestamp, tz=timezone.utc)
                if start_date and log_datetime < start_date:
                    continue
                if end_date and log_datetime > end_date:
                    continue

            # Format log entry for report
            log_entry = {
                "timestamp": entry.timestamp,
                "date": datetime.fromtimestamp(entry.timestamp, tz=timezone.utc).isoformat()
                if entry.timestamp
                else None,
                "tenant_id": metadata.get("tenant_id", "default"),
                "decision_type": metadata.get("decision_type", "unknown"),
                "agent_id": metadata.get("agent_id", "unknown"),
                "action": metadata.get("action", "unknown"),
                "impact_score": metadata.get("impact_score", 0.0),
                "constitutional_compliant": vr.is_valid,
                "errors": vr.errors,
                "warnings": vr.warnings,
                "hash": entry.hash,
                "batch_id": entry.batch_id,
                "anchored": entry.batch_id
                is not None,  # If it has a batch_id, it's at least queued for anchoring
            }

            filtered_logs.append(log_entry)

        # Sort by timestamp descending (most recent first)
        filtered_logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        logger.info("Fetched %d decision logs for tenant %s", len(filtered_logs), tenant_id)

        return filtered_logs

    except Exception as e:
        logger.error("Failed to fetch logs from audit ledger: %s", e, exc_info=True)
        # Return empty list on error to maintain API compatibility
        return []


def _save_report_to_storage(
    report_bytes: bytes,
    report_id: str,
    format: str,
) -> str:
    """
    Save generated report to storage.

    Args:
        report_bytes: Report content as bytes
        report_id: Unique report identifier
        format: Report format (pdf/csv)

    Returns:
        Full path to saved file
    """
    _ensure_storage_directory()

    extension = format.lower()
    filename = f"{report_id}.{extension}"
    file_path = os.path.join(REPORT_STORAGE_PATH, filename)

    with open(file_path, "wb") as f:
        f.write(report_bytes)

    logger.info("Report saved to %s (%d bytes)", file_path, len(report_bytes))
    return file_path


@shared_task(
    bind=True,
    name="audit_service.generate_scheduled_report",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    queue="reports",
)
async def generate_scheduled_report(
    self,
    tenant_id: str,
    framework: str,
    format: str = "pdf",
    recipient_emails: Optional[List[str]] = None,
    company_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Celery task for generating scheduled compliance reports.

    This task:
    1. Fetches decision logs for the tenant
    2. Generates a report in the specified format (PDF/CSV)
    3. Saves the report to storage
    4. Optionally sends the report via email to specified recipients

    Args:
        tenant_id: Target tenant identifier
        framework: Compliance framework (ISO42001, SOC2, ISO27001, GDPR)
        format: Output format (pdf or csv)
        recipient_emails: Optional list of email addresses for delivery
        company_name: Optional company name for branding (PDF only)
        logo_url: Optional URL/path to company logo (PDF only)
        brand_color: Optional brand color hex code (PDF only)

    Returns:
        Dictionary containing report generation results

    Raises:
        MaxRetriesExceededError: If all retry attempts fail
    """
    report_id = _generate_report_id(tenant_id, framework)
    generated_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Starting scheduled report generation: report_id=%s, tenant=%s, "
        "framework=%s, format=%s, task_id=%s",
        report_id,
        tenant_id,
        framework,
        format,
        self.request.id,
    )

    try:
        # Get the report generator
        ReportGenerator = _get_report_generator()

        # Fetch logs for the tenant
        logs = await _fetch_logs_for_tenant(tenant_id)

        # Generate the report based on format
        format_lower = format.lower()
        if format_lower == "pdf":
            report_bytes = ReportGenerator.generate_pdf_report(
                logs=logs,
                tenant_id=tenant_id,
                framework=framework,
                company_name=company_name,
                logo_url=logo_url,
                brand_color=brand_color,
            )
        elif format_lower == "csv":
            report_bytes = ReportGenerator.generate_csv_bytes(
                logs=logs,
                tenant_id=tenant_id,
            )
        else:
            raise ValueError(f"Unsupported format: {format}. Must be 'pdf' or 'csv'")

        # Save report to storage
        file_path = _save_report_to_storage(report_bytes, report_id, format_lower)
        file_size = len(report_bytes)

        logger.info(
            "Report generated successfully: report_id=%s, file_path=%s, size=%d bytes",
            report_id,
            file_path,
            file_size,
        )

        # Send email if recipients specified
        email_sent = False
        if recipient_emails:
            email_sent = _send_report_email(
                report_bytes=report_bytes,
                report_id=report_id,
                format=format_lower,
                framework=framework,
                tenant_id=tenant_id,
                recipient_emails=recipient_emails,
            )

        result = ReportGenerationResult(
            success=True,
            report_id=report_id,
            tenant_id=tenant_id,
            framework=framework,
            format=format_lower,
            file_path=file_path,
            file_size_bytes=file_size,
            generated_at=generated_at,
            email_sent=email_sent,
            email_recipients=recipient_emails if email_sent else None,
        )

        return result.to_dict()

    except MaxRetriesExceededError:
        logger.error(
            "Max retries exceeded for report generation: report_id=%s, tenant=%s, framework=%s",
            report_id,
            tenant_id,
            framework,
        )
        result = ReportGenerationResult(
            success=False,
            report_id=report_id,
            tenant_id=tenant_id,
            framework=framework,
            format=format,
            generated_at=generated_at,
            error_message="Max retries exceeded",
        )
        return result.to_dict()

    except Exception as e:
        logger.error(
            "Report generation failed: report_id=%s, tenant=%s, framework=%s, "
            "error=%s, retry=%d/%d",
            report_id,
            tenant_id,
            framework,
            str(e),
            self.request.retries,
            self.max_retries,
        )

        # Retry with exponential backoff
        # The task decorator handles retries automatically with autoretry_for
        raise


def _send_report_email(
    report_bytes: bytes,
    report_id: str,
    format: str,
    framework: str,
    tenant_id: str,
    recipient_emails: List[str],
) -> bool:
    """
    Send report via email to specified recipients.

    Args:
        report_bytes: Report content as bytes
        report_id: Unique report identifier
        format: Report format (pdf/csv)
        framework: Compliance framework name
        tenant_id: Tenant identifier
        recipient_emails: List of recipient email addresses

    Returns:
        True if email was sent successfully, False otherwise
    """
    EmailService = _get_email_service()
    if EmailService is None:
        logger.warning(
            "Email service not available, skipping email delivery for report_id=%s",
            report_id,
        )
        return False

    try:
        report_name = f"{framework} Compliance Report"

        for recipient in recipient_emails:
            logger.info(
                "Sending report email: report_id=%s, recipient=%s",
                report_id,
                recipient,
            )
            EmailService.send_report_email(
                recipient=recipient,
                pdf_bytes=report_bytes,
                report_name=report_name,
                format=format,
            )

        logger.info(
            "Report emails sent successfully: report_id=%s, recipients=%s",
            report_id,
            recipient_emails,
        )
        return True

    except Exception as e:
        logger.error(
            "Failed to send report email: report_id=%s, error=%s",
            report_id,
            str(e),
        )
        # Don't fail the task if email fails - report was still generated
        return False


@shared_task(
    bind=True,
    name="audit_service.generate_report_async",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
    queue="reports",
)
async def generate_report_async(
    self,
    tenant_id: str,
    framework: str,
    format: str = "pdf",
    logs: Optional[List[Dict[str, Any]]] = None,
    company_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Celery task for on-demand async report generation.

    Unlike generate_scheduled_report, this task:
    - Accepts pre-fetched logs directly (useful for API-triggered generation)
    - Does not send emails automatically
    - Has shorter retry delays for faster feedback

    Args:
        tenant_id: Target tenant identifier
        framework: Compliance framework (ISO42001, SOC2, ISO27001, GDPR)
        format: Output format (pdf or csv)
        logs: Optional pre-fetched decision logs
        company_name: Optional company name for branding (PDF only)
        logo_url: Optional URL/path to company logo (PDF only)
        brand_color: Optional brand color hex code (PDF only)

    Returns:
        Dictionary containing report generation results
    """
    report_id = _generate_report_id(tenant_id, framework)
    generated_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Starting async report generation: report_id=%s, tenant=%s, "
        "framework=%s, format=%s, task_id=%s",
        report_id,
        tenant_id,
        framework,
        format,
        self.request.id,
    )

    try:
        # Get the report generator
        ReportGenerator = _get_report_generator()

        # Use provided logs or fetch from storage
        if logs is None:
            logs = await _fetch_logs_for_tenant(tenant_id)

        # Generate the report based on format
        format_lower = format.lower()
        if format_lower == "pdf":
            report_bytes = ReportGenerator.generate_pdf_report(
                logs=logs,
                tenant_id=tenant_id,
                framework=framework,
                company_name=company_name,
                logo_url=logo_url,
                brand_color=brand_color,
            )
        elif format_lower == "csv":
            report_bytes = ReportGenerator.generate_csv_bytes(
                logs=logs,
                tenant_id=tenant_id,
            )
        else:
            raise ValueError(f"Unsupported format: {format}. Must be 'pdf' or 'csv'")

        # Save report to storage
        file_path = _save_report_to_storage(report_bytes, report_id, format_lower)
        file_size = len(report_bytes)

        logger.info(
            "Async report generated successfully: report_id=%s, file_path=%s, size=%d bytes",
            report_id,
            file_path,
            file_size,
        )

        result = ReportGenerationResult(
            success=True,
            report_id=report_id,
            tenant_id=tenant_id,
            framework=framework,
            format=format_lower,
            file_path=file_path,
            file_size_bytes=file_size,
            generated_at=generated_at,
        )

        return result.to_dict()

    except Exception as e:
        logger.error(
            "Async report generation failed: report_id=%s, tenant=%s, "
            "framework=%s, error=%s, retry=%d/%d",
            report_id,
            tenant_id,
            framework,
            str(e),
            self.request.retries,
            self.max_retries,
        )
        raise
