"""
Report Generation API Endpoints

Provides endpoints for on-demand compliance report generation,
task status checking, and report downloads.

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter()

# Report storage path from environment
REPORT_STORAGE_PATH = os.getenv("REPORT_STORAGE_PATH", "/tmp/reports")


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks for report generation."""

    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    ISO42001 = "iso42001"


class ReportFormat(str, Enum):
    """Supported report output formats."""

    PDF = "pdf"
    CSV = "csv"


class BrandingConfig(BaseModel):
    """Branding configuration for PDF reports."""

    company_name: Optional[str] = Field(
        default=None,
        description="Company name to display in report header",
        max_length=200,
    )
    logo_url: Optional[str] = Field(
        default=None,
        description="URL or path to company logo image",
        max_length=500,
    )
    brand_color: Optional[str] = Field(
        default=None,
        description="Brand color as hex code (e.g., #003366)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class ReportGenerateRequest(BaseModel):
    """Request model for report generation."""

    framework: ComplianceFramework = Field(
        ...,
        description="Compliance framework for the report",
    )
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Output format (pdf or csv)",
    )
    tenant_id: Optional[str] = Field(
        default="default",
        description="Tenant identifier for multi-tenant deployments",
        max_length=50,
    )
    branding: Optional[BrandingConfig] = Field(
        default=None,
        description="Branding configuration for PDF reports",
    )
    send_email: bool = Field(
        default=False,
        description="Whether to send report via email after generation",
    )
    recipient_emails: Optional[List[str]] = Field(
        default=None,
        description="Email addresses to send the report to",
    )

    @field_validator("recipient_emails")
    @classmethod
    def validate_emails(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate email list."""
        if v is None:
            return None
        if len(v) > 10:
            raise ValueError("Maximum 10 recipients allowed")
        # Basic email format validation
        for email in v:
            if "@" not in email or "." not in email.split("@")[-1]:
                raise ValueError(f"Invalid email format: {email}")
        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "framework": "soc2",
                "format": "pdf",
                "tenant_id": "default",
                "branding": {
                    "company_name": "ACME Corporation",
                    "logo_url": "/assets/logo.png",
                    "brand_color": "#003366",
                },
                "send_email": False,
                "recipient_emails": None,
            }
        }


class ReportGenerateResponse(BaseModel):
    """Response model for report generation request."""

    status: str = Field(
        ...,
        description="Request status (accepted)",
    )
    task_id: str = Field(
        ...,
        description="Celery task ID for tracking progress",
    )
    message: str = Field(
        ...,
        description="Status message",
    )
    framework: str = Field(
        ...,
        description="Requested compliance framework",
    )
    format: str = Field(
        ...,
        description="Requested output format",
    )
    submitted_at: str = Field(
        ...,
        description="Request submission timestamp",
    )


class ReportStatusResponse(BaseModel):
    """Response model for report status check."""

    task_id: str = Field(
        ...,
        description="Celery task ID",
    )
    status: str = Field(
        ...,
        description="Task status (pending, started, success, failure, retry)",
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task result (if completed)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)",
    )
    report_url: Optional[str] = Field(
        default=None,
        description="URL to download report (if successful)",
    )
    checked_at: str = Field(
        ...,
        description="Status check timestamp",
    )


def _get_celery_app():
    """
    Lazy import of Celery app to avoid circular imports.

    Returns:
        Celery app instance or None if not available
    """
    try:
        from app.celery_app import celery_app

        return celery_app
    except ImportError:
        try:
            from ..celery_app import celery_app

            return celery_app
        except ImportError:
            logger.warning("Celery app not available - async tasks disabled")
            return None


def _get_generate_report_task():
    """
    Lazy import of generate_report_async task.

    Returns:
        Celery task function or None if not available
    """
    try:
        from app.tasks.report_tasks import generate_report_async

        return generate_report_async
    except ImportError:
        try:
            from ..tasks.report_tasks import generate_report_async

            return generate_report_async
        except ImportError:
            logger.warning("Report tasks not available")
            return None


@router.post(
    "/generate",
    response_model=ReportGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate compliance report",
    description="Trigger on-demand generation of a compliance report. "
    "Returns a task ID for tracking progress.",
)
async def generate_report(request: ReportGenerateRequest) -> ReportGenerateResponse:
    """
    Generate a compliance report asynchronously.

    Accepts framework (soc2, iso27001, gdpr, iso42001), format (pdf, csv),
    and optional branding configuration. Returns a task ID for tracking
    the async report generation via Celery.

    Returns 202 Accepted with task_id for status polling.
    """
    submitted_at = datetime.now(timezone.utc).isoformat()

    # Get the Celery task
    generate_task = _get_generate_report_task()

    if generate_task is None:
        logger.error("Celery task not available for report generation")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report generation service temporarily unavailable. Please try again later.",
        )

    try:
        # Extract branding config
        branding = request.branding or BrandingConfig()

        # Build task arguments
        task_kwargs = {
            "tenant_id": request.tenant_id or "default",
            "framework": request.framework.value.upper(),
            "format": request.format.value,
            "company_name": branding.company_name,
            "logo_url": branding.logo_url,
            "brand_color": branding.brand_color,
        }

        # Submit async task to Celery
        task_result = generate_task.delay(**task_kwargs)

        logger.info(
            "Report generation task submitted: task_id=%s, framework=%s, format=%s, tenant=%s",
            task_result.id,
            request.framework.value,
            request.format.value,
            request.tenant_id,
        )

        return ReportGenerateResponse(
            status="accepted",
            task_id=task_result.id,
            message=f"Report generation started for {request.framework.value.upper()} "
            f"framework in {request.format.value.upper()} format",
            framework=request.framework.value,
            format=request.format.value,
            submitted_at=submitted_at,
        )

    except Exception as e:
        logger.error(
            "Failed to submit report generation task: %s",
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate report generation. Please try again later.",
        ) from None


@router.get(
    "/{task_id}",
    response_model=ReportStatusResponse,
    summary="Check report generation status",
    description="Check the status of a report generation task by task ID.",
)
async def get_report_status(task_id: str) -> ReportStatusResponse:
    """
    Check the status of an async report generation task.

    Returns current status, result (if completed), and download URL.
    """
    checked_at = datetime.now(timezone.utc).isoformat()

    celery_app = _get_celery_app()

    if celery_app is None:
        logger.error("Celery app not available for status check")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report status service temporarily unavailable.",
        )

    try:
        # Get task result from Celery
        task_result = celery_app.AsyncResult(task_id)

        # Map Celery status to response
        status_value = task_result.status.lower()
        result_data = None
        error_msg = None
        report_url = None

        if status_value == "success":
            result_data = task_result.result
            if result_data and result_data.get("success"):
                # Build download URL if report was generated
                report_id = result_data.get("report_id")
                report_format = result_data.get("format", "pdf")
                if report_id:
                    report_url = f"/api/v1/reports/download/{report_id}.{report_format}"

        elif status_value == "failure":
            error_msg = str(task_result.result) if task_result.result else "Unknown error"

        return ReportStatusResponse(
            task_id=task_id,
            status=status_value,
            result=result_data,
            error=error_msg,
            report_url=report_url,
            checked_at=checked_at,
        )

    except Exception as e:
        logger.error("Failed to check task status: task_id=%s, error=%s", task_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status.",
        ) from None


@router.get(
    "/download/{filename}",
    summary="Download generated report",
    description="Download a generated report file by filename.",
)
async def download_report(filename: str) -> FileResponse:
    """
    Download a generated report file.

    Returns the report file as a downloadable attachment.
    """
    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    # Determine file path and media type
    file_path = os.path.join(REPORT_STORAGE_PATH, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Determine media type based on extension
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".csv"):
        media_type = "text/csv"
    else:
        media_type = "application/octet-stream"

    logger.info("Serving report download: %s", filename)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Reports API health check",
)
async def reports_health() -> Dict[str, Any]:
    """
    Health check for reports API.

    Returns service status and Celery worker availability.
    """
    celery_available = _get_celery_app() is not None
    tasks_available = _get_generate_report_task() is not None

    return {
        "status": "healthy" if (celery_available and tasks_available) else "degraded",
        "api": "reports",
        "version": "1.0.0",
        "celery_available": celery_available,
        "tasks_available": tasks_available,
        "storage_path": REPORT_STORAGE_PATH,
        "endpoints": ["/generate", "/{task_id}", "/download/{filename}", "/health"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
