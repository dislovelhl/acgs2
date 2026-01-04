"""Constitutional Hash: cdd01ef066bc6cf2
Export Route - POST /export/pdf endpoint for executive report generation

Provides PDF export functionality for governance analytics:
- Generate executive summary reports
- Include AI-generated insights, anomalies, and predictions
- Return PDF as downloadable file or streaming response
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Add analytics-engine to path for importing PDFExporter
ANALYTICS_ENGINE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "analytics-engine" / "src"
)
if str(ANALYTICS_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(ANALYTICS_ENGINE_PATH))

try:
    from pdf_exporter import PDFExporter, PDFReportMetadata
except ImportError:
    PDFExporter = None
    PDFReportMetadata = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


class PDFExportRequest(BaseModel):
    """Request model for PDF export"""

    title: Optional[str] = Field(
        default="Governance Analytics Report",
        description="Report title",
    )
    subtitle: Optional[str] = Field(
        default="Executive Summary",
        description="Report subtitle",
    )
    time_range: str = Field(
        default="last_7_days",
        description="Time range for report data",
    )
    include_insights: bool = Field(
        default=True,
        description="Include AI-generated insights section",
    )
    include_anomalies: bool = Field(
        default=True,
        description="Include anomaly detection section",
    )
    include_predictions: bool = Field(
        default=True,
        description="Include violation forecast section",
    )


class PDFExportResponse(BaseModel):
    """Response model for PDF export (when not returning file)"""

    success: bool = Field(description="Whether export was successful")
    filename: Optional[str] = Field(
        default=None,
        description="Generated filename",
    )
    file_size_bytes: int = Field(
        default=0,
        description="Size of generated PDF in bytes",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when report was generated",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if export failed",
    )


class ExportErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of error",
    )


# Module-level PDF exporter instance
_pdf_exporter: Optional[PDFExporter] = None


def get_pdf_exporter() -> Optional[PDFExporter]:
    """
    Get or create the PDFExporter instance.

    Returns:
        PDFExporter instance or None if not available
    """
    global _pdf_exporter

    if _pdf_exporter is not None:
        return _pdf_exporter

    if PDFExporter is None:
        logger.warning("PDFExporter not available. Ensure analytics-engine is in the path.")
        return None

    _pdf_exporter = PDFExporter(
        company_name="ACGS-2 Governance Platform",
        include_charts=True,
    )

    return _pdf_exporter


def get_sample_governance_data() -> Dict[str, Any]:
    """
    Get sample governance data for report generation.

    In production, this would fetch real data from Kafka/Redis.
    Returns sample data for demonstration and testing.

    Returns:
        Dictionary with governance metrics
    """
    return {
        "violation_count": 12,
        "top_violated_policy": "data-access-policy",
        "trend": "increasing",
        "total_events": 1547,
        "unique_users": 89,
        "policy_changes": 3,
        "severity_distribution": {
            "low": 3,
            "medium": 5,
            "high": 3,
            "critical": 1,
        },
        "period": "last_7_days",
    }


def get_sample_insights() -> Dict[str, Any]:
    """
    Get sample AI-generated insights for report.

    Returns:
        Dictionary with insight data
    """
    return {
        "summary": (
            "Governance activity shows a 15% increase in policy violations, "
            "primarily in the data-access-policy category."
        ),
        "business_impact": (
            "The increasing violation trend poses moderate compliance risk. "
            "89 unique users have been affected, potentially impacting data security."
        ),
        "recommended_action": (
            "Review and strengthen data-access-policy enforcement. Consider "
            "implementing additional training for affected users."
        ),
        "confidence": 0.85,
    }


def get_sample_anomalies() -> Dict[str, Any]:
    """
    Get sample anomaly detection results for report.

    Returns:
        Dictionary with anomaly data
    """
    return {
        "anomalies_detected": 3,
        "total_records_analyzed": 1547,
        "anomalies": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity_label": "high",
                "description": "Unusual spike in data-access violations detected",
                "affected_metrics": ["violation_count", "unique_users"],
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity_label": "medium",
                "description": "Policy changes exceeded normal threshold",
                "affected_metrics": ["policy_changes"],
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity_label": "low",
                "description": "Minor deviation in user activity patterns",
                "affected_metrics": ["unique_users"],
            },
        ],
    }


def get_sample_predictions() -> Dict[str, Any]:
    """
    Get sample violation predictions for report.

    Returns:
        Dictionary with prediction data
    """
    return {
        "forecast_days": 30,
        "model_trained": True,
        "summary": {
            "mean_predicted_violations": 14.5,
            "total_predicted_violations": 435,
            "trend_direction": "increasing",
        },
        "forecast": [
            {
                "date": "2024-01-01",
                "predicted_value": 13.2,
                "lower_bound": 10.5,
                "upper_bound": 15.9,
            },
            {
                "date": "2024-01-02",
                "predicted_value": 13.5,
                "lower_bound": 10.8,
                "upper_bound": 16.2,
            },
            {
                "date": "2024-01-03",
                "predicted_value": 13.8,
                "lower_bound": 11.1,
                "upper_bound": 16.5,
            },
            {
                "date": "2024-01-04",
                "predicted_value": 14.1,
                "lower_bound": 11.4,
                "upper_bound": 16.8,
            },
            {
                "date": "2024-01-05",
                "predicted_value": 14.4,
                "lower_bound": 11.7,
                "upper_bound": 17.1,
            },
            {
                "date": "2024-01-06",
                "predicted_value": 14.7,
                "lower_bound": 12.0,
                "upper_bound": 17.4,
            },
            {
                "date": "2024-01-07",
                "predicted_value": 15.0,
                "lower_bound": 12.3,
                "upper_bound": 17.7,
            },
        ],
    }


@router.post(
    "/pdf",
    responses={
        200: {
            "description": "Successfully generated PDF report",
            "content": {"application/pdf": {}},
        },
        500: {"description": "Internal server error"},
        503: {"description": "PDF export service temporarily unavailable"},
    },
    summary="Generate PDF executive report",
    description=(
        "Generates an executive PDF report containing governance analytics, "
        "AI-generated insights, anomaly detection results, and violation forecasts."
    ),
)
async def export_pdf(request: Optional[PDFExportRequest] = None) -> Response:
    """
    Generate and return a PDF executive report.

    The report includes:
    - Executive summary with key governance metrics
    - AI-generated insights (if enabled)
    - Anomaly detection alerts (if enabled)
    - Violation forecasts (if enabled)

    Args:
        request: PDFExportRequest with report configuration

    Returns:
        PDF file as streaming response

    Raises:
        HTTPException: If PDF generation fails
    """
    if request is None:
        request = PDFExportRequest()

    exporter = get_pdf_exporter()

    if exporter is None or not exporter.is_available:
        logger.warning("PDFExporter not available, returning error")
        raise HTTPException(
            status_code=503,
            detail="PDF export service temporarily unavailable. ReportLab may not be installed.",
        )

    # Get governance data (sample data for now, Redis integration in future)
    governance_data = get_sample_governance_data()
    governance_data["period"] = request.time_range

    # Get optional sections based on request
    insights = get_sample_insights() if request.include_insights else None
    anomalies = get_sample_anomalies() if request.include_anomalies else None
    predictions = get_sample_predictions() if request.include_predictions else None

    # Create metadata
    now = datetime.now(timezone.utc)
    metadata = None

    if PDFReportMetadata is not None:
        metadata = PDFReportMetadata(
            title=request.title or "Governance Analytics Report",
            subtitle=request.subtitle or "Executive Summary",
            generated_at=now,
        )

    try:
        # Generate PDF as bytes for streaming response
        pdf_bytes = exporter.generate_to_bytes(
            governance_data=governance_data,
            insights=insights,
            anomalies=anomalies,
            predictions=predictions,
            metadata=metadata,
        )

        if pdf_bytes is None:
            logger.error("PDF generation returned None")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF report. Please try again later.",
            )

        # Generate filename
        filename = f"governance_report_{now.strftime('%Y%m%d_%H%M%S')}.pdf"

        logger.info(f"Generated PDF report: {filename} ({len(pdf_bytes)} bytes)")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF report. Please try again later.",
        ) from None


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get PDF export service status",
    description="Returns the current status and configuration of the PDF export service.",
)
async def get_export_status() -> Dict[str, Any]:
    """
    Get the status of the PDF export service.

    Returns:
        Dictionary with exporter status and configuration
    """
    exporter = get_pdf_exporter()

    if exporter is None:
        return {
            "status": "unavailable",
            "message": "PDFExporter module not loaded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    info = exporter.get_exporter_info()
    info["status"] = "available" if info.get("is_available") else "not_configured"
    info["endpoint"] = "/export/pdf"
    info["timestamp"] = datetime.now(timezone.utc).isoformat()

    return info
