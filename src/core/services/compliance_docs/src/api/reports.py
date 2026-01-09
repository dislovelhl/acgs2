"""Constitutional Hash: cdd01ef066bc6cf2
Report Generation API for Compliance Documentation Service

Provides REST API endpoint for generating custom compliance reports
with support for file streaming for large reports.

Endpoints:
- POST /api/v1/reports/generate - Generate custom compliance report
"""

import io
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ..generators import generate_docx_to_buffer, generate_pdf_to_buffer, generate_xlsx_to_buffer
from ..models.base import ComplianceFramework, ExportFormat

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/reports", tags=["Report Generation"])

# Media types for file downloads
MEDIA_TYPES = {
    "json": "application/json",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Streaming threshold (10MB) - use FileResponse for smaller files, StreamingResponse for larger
STREAMING_THRESHOLD_BYTES = 10 * 1024 * 1024

# Temp file directory for large files
TEMP_DIR = Path(os.getenv("COMPLIANCE_OUTPUT_PATH", "/tmp/compliance-reports"))


class ReportRequest(BaseModel):
    """Request model for generating compliance reports."""

    framework: str = Field(
        ...,
        description="Compliance framework (soc2, iso27001, gdpr, euaiact)",
        examples=["soc2", "iso27001", "gdpr", "euaiact"],
    )
    format: str = Field(
        default="pdf",
        description="Output format (json, pdf, docx, xlsx)",
        examples=["pdf", "docx", "xlsx", "json"],
    )
    organization_name: str = Field(
        default="ACGS-2 Organization",
        description="Name of the organization for the report",
    )
    report_title: Optional[str] = Field(
        default=None,
        description="Custom title for the report (auto-generated if not provided)",
    )
    reporting_period_start: Optional[datetime] = Field(
        default=None,
        description="Start of the reporting period (ISO 8601 format)",
    )
    reporting_period_end: Optional[datetime] = Field(
        default=None,
        description="End of the reporting period (ISO 8601 format)",
    )
    include_evidence: bool = Field(
        default=True,
        description="Include detailed evidence in the report",
    )
    include_recommendations: bool = Field(
        default=True,
        description="Include compliance recommendations",
    )
    custom_data: Optional[dict] = Field(
        default=None,
        description="Custom data to include in the report (for advanced use cases)",
    )

    @field_validator("framework")
    @classmethod
    def validate_framework(cls, v: str) -> str:
        """Validate and normalize framework value."""
        framework_lower = v.lower()
        valid_frameworks = [f.value for f in ComplianceFramework]
        if framework_lower not in valid_frameworks:
            raise ValueError(
                f"Invalid framework: {v}. Valid options: {', '.join(valid_frameworks)}"
            )
        return framework_lower

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate and normalize format value."""
        format_lower = v.lower()
        valid_formats = [f.value for f in ExportFormat]
        if format_lower not in valid_formats:
            raise ValueError(f"Invalid format: {v}. Valid options: {', '.join(valid_formats)}")
        return format_lower


class ReportResponse(BaseModel):
    """Response model for report generation (JSON format only)."""

    report_id: str = Field(..., description="Unique identifier for the report")
    framework: str = Field(..., description="Compliance framework")
    format: str = Field(..., description="Report format")
    organization_name: str = Field(..., description="Organization name")
    report_title: str = Field(..., description="Report title")
    generated_at: str = Field(..., description="Report generation timestamp")
    reporting_period_start: Optional[str] = Field(None, description="Start of reporting period")
    reporting_period_end: Optional[str] = Field(None, description="End of reporting period")
    status: str = Field(..., description="Report generation status")
    data: dict = Field(..., description="Report data")


def _get_default_report_title(framework: str) -> str:
    """Get default report title based on framework."""
    titles = {
        "soc2": "SOC 2 Type II Compliance Report",
        "iso27001": "ISO 27001:2022 ISMS Compliance Report",
        "gdpr": "GDPR Article 30 Records of Processing Activities",
        "euaiact": "EU AI Act Compliance and Risk Assessment Report",
    }
    return titles.get(framework, "Compliance Report")


def _generate_report_data(
    framework: str,
    organization_name: str,
    report_title: str,
    reporting_period_start: Optional[datetime],
    reporting_period_end: Optional[datetime],
    include_evidence: bool,
    include_recommendations: bool,
    custom_data: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Generate report data for the specified framework.

    In production, this would query the database for actual compliance data.
    For now, returns structured sample data suitable for report generation.
    """
    now = datetime.now(timezone.utc)
    report_id = str(uuid.uuid4())

    # Base report metadata
    base_data = {
        "report_id": report_id,
        "framework": framework,
        "organization_name": organization_name,
        "report_title": report_title,
        "generated_at": now.isoformat(),
        "reporting_period_start": (
            reporting_period_start.isoformat() if reporting_period_start else None
        ),
        "reporting_period_end": (
            reporting_period_end.isoformat() if reporting_period_end else None
        ),
        "document_version": "1.0.0",
        "confidentiality_level": "Confidential",
    }

    # Framework-specific data
    if framework == "soc2":
        report_data = _generate_soc2_report_data(
            base_data, include_evidence, include_recommendations
        )
    elif framework == "iso27001":
        report_data = _generate_iso27001_report_data(
            base_data, include_evidence, include_recommendations
        )
    elif framework == "gdpr":
        report_data = _generate_gdpr_report_data(
            base_data, include_evidence, include_recommendations
        )
    elif framework == "euaiact":
        report_data = _generate_euaiact_report_data(
            base_data, include_evidence, include_recommendations
        )
    else:
        report_data = base_data

    # Merge custom data if provided
    if custom_data:
        report_data["custom_sections"] = custom_data

    return report_data


def _generate_soc2_report_data(
    base_data: dict,
    include_evidence: bool,
    include_recommendations: bool,
) -> dict[str, Any]:
    """Generate SOC 2 Type II report data."""
    now = datetime.now(timezone.utc)

    data = {
        **base_data,
        "report_type": "SOC 2 Type II",
        "audit_period_start": base_data.get("reporting_period_start"),
        "audit_period_end": base_data.get("reporting_period_end"),
        "criteria_in_scope": [
            "security",
            "availability",
            "processing_integrity",
            "confidentiality",
            "privacy",
        ],
        "system_description": {
            "name": f"{base_data['organization_name']} AI Guardrails Platform",
            "description": "Enterprise AI content moderation and safety guardrails system",
            "components": [
                "API Gateway",
                "Guardrail Engine",
                "Policy Manager",
                "Audit Service",
            ],
            "infrastructure": "Cloud-hosted containerized microservices",
        },
        "total_controls": 87,
        "controls_tested": 87,
        "controls_effective": 85,
        "controls_with_exceptions": 2,
        "overall_opinion": "unqualified",
        "criteria_sections": [
            {
                "criteria": "security",
                "criteria_name": "Security (Common Criteria)",
                "in_scope": True,
                "total_controls": 25,
                "effective_controls": 24,
                "overall_effectiveness": "effective",
                "controls": [
                    {
                        "control_id": f"CC1.{i}",
                        "title": f"Control Environment {i}",
                        "control_objective": f"Ensure control objective {i} is achieved",
                        "implementation_status": "implemented",
                        "testing_result": "effective" if i != 5 else "partially_effective",
                    }
                    for i in range(1, 6)
                ],
            },
            {
                "criteria": "availability",
                "criteria_name": "Availability",
                "in_scope": True,
                "total_controls": 15,
                "effective_controls": 15,
                "overall_effectiveness": "effective",
            },
            {
                "criteria": "processing_integrity",
                "criteria_name": "Processing Integrity",
                "in_scope": True,
                "total_controls": 18,
                "effective_controls": 17,
                "overall_effectiveness": "effective",
            },
            {
                "criteria": "confidentiality",
                "criteria_name": "Confidentiality",
                "in_scope": True,
                "total_controls": 14,
                "effective_controls": 14,
                "overall_effectiveness": "effective",
            },
            {
                "criteria": "privacy",
                "criteria_name": "Privacy",
                "in_scope": True,
                "total_controls": 15,
                "effective_controls": 15,
                "overall_effectiveness": "effective",
            },
        ],
        "control_mappings": [
            {
                "mapping_id": f"MAP-SOC2-{i:03d}",
                "soc2_control_id": f"CC{i}.1",
                "guardrail_control_id": f"GR-{i:03d}",
                "guardrail_control_name": f"ACGS Guardrail Control {i}",
                "mapping_rationale": f"Guardrail control {i} implements SOC 2 CC{i}.1 requirements",
                "coverage_percentage": 100 if i % 3 != 0 else 85,
            }
            for i in range(1, 10)
        ],
    }

    if include_evidence:
        data["evidence_records"] = [
            {
                "evidence_id": f"EV-SOC2-{i:03d}",
                "control_id": f"CC{(i % 9) + 1}.{(i % 4) + 1}",
                "criteria": [
                    "security",
                    "availability",
                    "processing_integrity",
                    "confidentiality",
                    "privacy",
                ][i % 5],
                "title": f"Control Evidence {i}",
                "description": "Evidence demonstrating control effectiveness",
                "evidence_type": ["document", "screenshot", "log", "configuration"][i % 4],
                "collected_at": now.isoformat(),
                "status": "completed",
            }
            for i in range(1, 16)
        ]

    if include_recommendations:
        data["recommendations"] = [
            {
                "recommendation_id": "REC-001",
                "priority": "medium",
                "area": "Logging and Monitoring",
                "recommendation": (
                    "Enhance log retention to 13 months for compliance with audit requirements"
                ),
                "timeline": "Q2 2026",
            },
            {
                "recommendation_id": "REC-002",
                "priority": "low",
                "area": "Access Controls",
                "recommendation": "Implement quarterly access reviews for privileged accounts",
                "timeline": "Q3 2026",
            },
        ]

    return data


def _generate_iso27001_report_data(
    base_data: dict,
    include_evidence: bool,
    include_recommendations: bool,
) -> dict[str, Any]:
    """Generate ISO 27001:2022 report data."""
    now = datetime.now(timezone.utc)

    data = {
        **base_data,
        "standard_version": "ISO 27001:2022",
        "isms_scope": "Information Security Management System for AI Guardrails Platform",
        "total_controls": 93,
        "applicable_controls": 78,
        "implemented_controls": 74,
        "implementation_percentage": 94.9,
        "certification_body": "Certification Authority (if applicable)",
        "theme_sections": [
            {
                "theme": "organizational",
                "theme_name": "Organizational Controls (A.5)",
                "total_controls": 37,
                "applicable_controls": 32,
                "implemented_controls": 30,
                "controls": [
                    {
                        "control_id": f"A.5.{i}",
                        "title": f"Organizational Policy {i}",
                        "description": "Security governance and policy control",
                        "applicability": "applicable",
                        "implementation_status": "implemented",
                    }
                    for i in range(1, 6)
                ],
            },
            {
                "theme": "people",
                "theme_name": "People Controls (A.6)",
                "total_controls": 8,
                "applicable_controls": 8,
                "implemented_controls": 8,
            },
            {
                "theme": "physical",
                "theme_name": "Physical Controls (A.7)",
                "total_controls": 14,
                "applicable_controls": 10,
                "implemented_controls": 10,
            },
            {
                "theme": "technological",
                "theme_name": "Technological Controls (A.8)",
                "total_controls": 34,
                "applicable_controls": 28,
                "implemented_controls": 26,
            },
        ],
        "statement_of_applicability": {
            "version": "1.0",
            "approved_by": "CISO",
            "approved_date": now.isoformat(),
            "total_entries": 93,
        },
    }

    if include_evidence:
        data["evidence_records"] = [
            {
                "evidence_id": f"EV-ISO-{i:03d}",
                "control_id": f"A.{5 + (i % 4)}.{(i % 8) + 1}",
                "theme": ["organizational", "people", "physical", "technological"][i % 4],
                "description": "Evidence for ISO 27001 control",
                "evidence_type": "document",
                "source": "ISMS Documentation System",
                "collected_at": now.isoformat(),
                "status": "completed",
            }
            for i in range(1, 11)
        ]

    if include_recommendations:
        data["recommendations"] = [
            {
                "recommendation_id": "REC-ISO-001",
                "priority": "high",
                "control_area": "A.8 Technological Controls",
                "recommendation": "Complete implementation of remaining 2 technological controls",
                "timeline": "Q1 2026",
            },
        ]

    return data


def _generate_gdpr_report_data(
    base_data: dict,
    include_evidence: bool,
    include_recommendations: bool,
) -> dict[str, Any]:
    """Generate GDPR Article 30 report data."""
    now = datetime.now(timezone.utc)

    data = {
        **base_data,
        "regulation": "GDPR (Regulation 2016/679)",
        "article": "Article 30 - Records of Processing Activities",
        "entity_role": "controller",
        "dpo": {
            "name": "Data Protection Officer",
            "email": "dpo@organization.com",
            "phone": "+1-555-0100",
        },
        "controller_record": {
            "controller_name": base_data["organization_name"],
            "controller_address": "123 Privacy Lane, Data City, Country",
            "processing_activities": [
                {
                    "processing_id": f"PA-{i:03d}",
                    "name": f"Processing Activity {i}",
                    "purposes": ["Service provision", "Security monitoring", "Analytics"][
                        0 : (i % 3) + 1
                    ],
                    "lawful_basis": ["legitimate_interest", "contract", "consent"][i % 3],
                    "data_subject_categories": ["Users", "Administrators", "Customers"][
                        0 : (i % 3) + 1
                    ],
                    "personal_data_categories": [
                        "Contact information",
                        "Usage data",
                        "Authentication data",
                    ][0 : (i % 3) + 1],
                    "recipients": [
                        {
                            "name": "Cloud Provider",
                            "country": "US",
                            "safeguards": "Standard Contractual Clauses",
                        }
                    ],
                    "third_country_transfers": i % 2 == 0,
                    "retention_period": "3 years after account closure",
                    "security_measures_summary": (
                        "Encryption, access controls, logging, regular security assessments"
                    ),
                    "status": "active",
                }
                for i in range(1, 6)
            ],
        },
        "data_flows": [
            {
                "flow_id": f"DF-{i:03d}",
                "name": f"Data Flow {i}",
                "data_source": ["User Application", "API Gateway", "Admin Portal"][i % 3],
                "data_destination": ["Processing Service", "Analytics Service", "Backup Service"][
                    i % 3
                ],
                "data_categories": ["User data", "System logs"],
                "crosses_border": i % 2 == 0,
                "transfer_mechanism": "Standard Contractual Clauses" if i % 2 == 0 else None,
                "encrypted_in_transit": True,
            }
            for i in range(1, 5)
        ],
        "security_measures": [
            {
                "measure_id": f"SM-{i:03d}",
                "category": ["technical", "organizational"][i % 2],
                "description": [
                    "Encryption at rest",
                    "Access control policy",
                    "Security awareness training",
                    "Incident response procedures",
                    "Regular security audits",
                ][i % 5],
                "status": "implemented",
                "last_reviewed": now.isoformat(),
            }
            for i in range(1, 8)
        ],
    }

    if include_recommendations:
        data["recommendations"] = [
            {
                "recommendation_id": "REC-GDPR-001",
                "priority": "medium",
                "area": "Data Subject Rights",
                "recommendation": "Implement automated data subject request handling portal",
                "timeline": "Q2 2026",
            },
        ]

    return data


def _generate_euaiact_report_data(
    base_data: dict,
    include_evidence: bool,
    include_recommendations: bool,
) -> dict[str, Any]:
    """Generate EU AI Act report data."""
    now = datetime.now(timezone.utc)

    data = {
        **base_data,
        "regulation": "EU AI Act (Regulation 2024/1689)",
        "organization_role": "provider",
        "high_risk_systems_count": 2,
        "limited_risk_systems_count": 1,
        "minimal_risk_systems_count": 3,
        "prohibited_systems_count": 0,
        "ai_systems": [
            {
                "system_id": f"AIS-{i:03d}",
                "system_name": f"AI System {i}",
                "risk_level": ["high_risk", "limited_risk", "minimal_risk"][i % 3],
                "high_risk_category": (f"Annex III Category {(i % 8) + 1}" if i % 3 == 0 else None),
                "intended_purpose": (
                    f"AI system for content moderation and safety guardrails (System {i})"
                ),
                "provider_role": "provider",
                "compliance_status": "compliant" if i % 4 != 0 else "in_progress",
                "last_assessment_date": now.isoformat(),
            }
            for i in range(1, 7)
        ],
        "risk_assessments": [
            {
                "assessment_id": f"RA-{i:03d}",
                "system_name": f"AI System {i}",
                "risk_level": "high_risk" if i % 2 == 0 else "limited_risk",
                "high_risk_category": f"Annex III Category {(i % 8) + 1}" if i % 2 == 0 else None,
                "assessment_date": now.isoformat(),
                "assessor": "Compliance Team",
                "key_findings": ("System meets EU AI Act requirements for its risk classification"),
                "recommendations": (
                    "Continue monitoring for regulatory updates and maintain documentation"
                ),
            }
            for i in range(1, 4)
        ],
        "conformity_assessments": [
            {
                "system_id": f"AIS-{i:03d}",
                "system_name": f"AI System {i}",
                "assessment_type": "internal_control" if i % 2 == 0 else "third_party",
                "assessment_date": now.isoformat(),
                "assessment_result": "passed",
                "certificate_number": f"EU-AI-CERT-{i:04d}" if i % 2 != 0 else None,
                "notified_body": "EU AI Certification Body" if i % 2 != 0 else None,
            }
            for i in range(1, 4)
        ],
        "technical_documentation": [
            {
                "system_name": f"AI System {i}",
                "annex_iv_requirements": {
                    "general_description": True,
                    "elements_development": True,
                    "monitoring_functioning": True,
                    "risk_management": True,
                    "data_governance": i % 2 == 0,
                    "human_oversight": True,
                },
                "documentation_status": "complete" if i % 3 != 0 else "in_progress",
            }
            for i in range(1, 4)
        ],
    }

    if include_recommendations:
        data["recommendations"] = [
            {
                "recommendation_id": "REC-EUAI-001",
                "priority": "high",
                "area": "Technical Documentation",
                "recommendation": "Complete data governance documentation for AI System 3",
                "timeline": "Q1 2026",
            },
            {
                "recommendation_id": "REC-EUAI-002",
                "priority": "medium",
                "area": "Conformity Assessment",
                "recommendation": "Schedule third-party assessment for high-risk systems",
                "timeline": "Q2 2026",
            },
        ]

    return data


def _generate_file_response(
    buffer: io.BytesIO,
    filename: str,
    media_type: str,
) -> StreamingResponse | FileResponse:
    """
    Generate appropriate response based on file size.

    Uses FileResponse for files under STREAMING_THRESHOLD_BYTES (10MB),
    StreamingResponse for larger files to avoid memory issues.
    """
    buffer_size = buffer.seek(0, 2)  # Seek to end to get size
    buffer.seek(0)  # Reset to beginning

    if buffer_size > STREAMING_THRESHOLD_BYTES:
        # Large file: use StreamingResponse for memory efficiency
        logger.info(f"Using StreamingResponse for large file: {filename} ({buffer_size} bytes)")

        # For very large files, write to temp file and stream from disk
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = TEMP_DIR / f"{uuid.uuid4()}_{filename}"

        try:
            with open(temp_path, "wb") as f:
                f.write(buffer.getvalue())

            return FileResponse(
                path=str(temp_path),
                media_type=media_type,
                filename=filename,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception as e:
            logger.error(f"Error writing temp file: {e}")
            # Fall back to streaming from memory
            pass

    # Small file or fallback: stream from memory
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate")
async def generate_report(request: ReportRequest):
    """
    Generate a custom compliance report for the specified framework.

    Supports multiple output formats (JSON, PDF, DOCX, XLSX) with intelligent
    file streaming for large reports. Files smaller than 10MB are served directly;
    larger files use streaming to avoid memory issues.

    - **framework**: Required. One of: soc2, iso27001, gdpr, euaiact
    - **format**: Output format. Default: pdf. Options: json, pdf, docx, xlsx
    - **organization_name**: Organization name for the report header
    - **report_title**: Custom report title (auto-generated if not provided)
    - **reporting_period_start**: Start of reporting period (ISO 8601)
    - **reporting_period_end**: End of reporting period (ISO 8601)
    - **include_evidence**: Include detailed evidence (default: true)
    - **include_recommendations**: Include recommendations (default: true)
    - **custom_data**: Optional custom data to include

    Returns:
        - JSON: JSONResponse with full report data
        - PDF: FileResponse/StreamingResponse with PDF file
        - DOCX: FileResponse/StreamingResponse with DOCX file
        - XLSX: FileResponse/StreamingResponse with XLSX file
    """
    try:
        # Get default title if not provided
        report_title = request.report_title or _get_default_report_title(request.framework)

        # Generate report data
        report_data = _generate_report_data(
            framework=request.framework,
            organization_name=request.organization_name,
            report_title=report_title,
            reporting_period_start=request.reporting_period_start,
            reporting_period_end=request.reporting_period_end,
            include_evidence=request.include_evidence,
            include_recommendations=request.include_recommendations,
            custom_data=request.custom_data,
        )

        # Generate timestamp for filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_filename = f"{request.framework}_report_{timestamp}"

        # Handle JSON format
        if request.format == "json":
            return JSONResponse(
                content=ReportResponse(
                    report_id=report_data["report_id"],
                    framework=request.framework,
                    format=request.format,
                    organization_name=request.organization_name,
                    report_title=report_title,
                    generated_at=report_data["generated_at"],
                    reporting_period_start=report_data.get("reporting_period_start"),
                    reporting_period_end=report_data.get("reporting_period_end"),
                    status="completed",
                    data=report_data,
                ).model_dump(),
                media_type=MEDIA_TYPES["json"],
            )

        # Handle PDF format
        elif request.format == "pdf":
            framework_enum = ComplianceFramework(request.framework)
            buffer = generate_pdf_to_buffer(
                report_data=report_data,
                framework=framework_enum,
            )

            filename = f"{base_filename}.pdf"
            return _generate_file_response(buffer, filename, MEDIA_TYPES["pdf"])

        # Handle DOCX format
        elif request.format == "docx":
            framework_enum = ComplianceFramework(request.framework)
            buffer = generate_docx_to_buffer(
                report_data=report_data,
                framework=framework_enum,
            )

            filename = f"{base_filename}.docx"
            return _generate_file_response(buffer, filename, MEDIA_TYPES["docx"])

        # Handle XLSX format
        elif request.format == "xlsx":
            framework_enum = ComplianceFramework(request.framework)
            buffer = generate_xlsx_to_buffer(
                report_data=report_data,
                framework=framework_enum,
            )

            filename = f"{base_filename}.xlsx"
            return _generate_file_response(buffer, filename, MEDIA_TYPES["xlsx"])

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {request.format}",
            )

    except ValueError as e:
        logger.error(f"Validation error during report generation: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report. Please try again later.",
        ) from None


@router.get("/formats")
async def list_supported_formats():
    """
    List all supported report formats and their media types.

    Returns a dictionary of format codes to media types.
    """
    return {
        "formats": [
            {
                "format": f.value,
                "media_type": MEDIA_TYPES.get(f.value),
                "description": {
                    "json": "JSON data format for programmatic access",
                    "pdf": "Portable Document Format for printing and sharing",
                    "docx": "Microsoft Word format for editing",
                    "xlsx": "Microsoft Excel format for spreadsheet analysis",
                }.get(f.value),
            }
            for f in ExportFormat
        ]
    }


@router.get("/frameworks")
async def list_supported_frameworks():
    """
    List all supported compliance frameworks.

    Returns a list of framework codes with their display names.
    """
    framework_info = {
        "soc2": {
            "code": "soc2",
            "name": "SOC 2 Type II",
            "description": "Service Organization Control 2 Type II report",
        },
        "iso27001": {
            "code": "iso27001",
            "name": "ISO 27001:2022",
            "description": "Information Security Management System standard",
        },
        "gdpr": {
            "code": "gdpr",
            "name": "GDPR",
            "description": "General Data Protection Regulation Article 30 records",
        },
        "euaiact": {
            "code": "euaiact",
            "name": "EU AI Act",
            "description": "EU AI Act (Regulation 2024/1689) compliance documentation",
        },
    }

    return {"frameworks": [framework_info[f.value] for f in ComplianceFramework]}
