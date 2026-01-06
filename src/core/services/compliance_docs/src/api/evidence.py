"""Constitutional Hash: cdd01ef066bc6cf2
Evidence Export API for Compliance Documentation Service

Provides REST API endpoints for exporting compliance evidence across all
supported frameworks (SOC 2, ISO 27001, GDPR, EU AI Act) in multiple formats
(JSON, PDF, XLSX).

Endpoints:
- GET /api/v1/evidence/export - Export compliance evidence with filtering
"""

import io
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..generators import (
    generate_pdf_to_buffer,
    generate_xlsx_to_buffer,
)
from ..models.base import ComplianceFramework, ExportFormat

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence Export"])

# Media types for file downloads
MEDIA_TYPES = {
    "json": "application/json",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Streaming threshold (10MB)
STREAMING_THRESHOLD_BYTES = 10 * 1024 * 1024


def _get_sample_evidence_data(
    framework: ComplianceFramework,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Generate sample evidence data for the specified framework.

    In production, this would query the database for actual evidence records
    filtered by date range. For now, returns structured sample data.

    Args:
        framework: The compliance framework to generate data for.
        start_date: Optional start date for filtering.
        end_date: Optional end date for filtering.

    Returns:
        Dictionary containing evidence data for the framework.
    """
    now = datetime.now(timezone.utc)
    export_id = str(uuid.uuid4())

    # Base metadata
    base_data = {
        "export_id": export_id,
        "framework": framework.value if isinstance(framework, ComplianceFramework) else framework,
        "exported_at": now.isoformat(),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "organization_name": os.getenv("TENANT_ID", "ACGS-2 Organization"),
    }

    if framework == ComplianceFramework.SOC2:
        return {
            **base_data,
            "report_type": "SOC 2 Type II",
            "audit_period_start": start_date or now,
            "audit_period_end": end_date or now,
            "criteria_in_scope": [
                "security",
                "availability",
                "processing_integrity",
                "confidentiality",
                "privacy",
            ],
            "total_controls": 87,
            "controls_tested": 87,
            "controls_effective": 85,
            "controls_with_exceptions": 2,
            "evidence_records": [
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
                    "description": f"Evidence demonstrating control effectiveness for CC{(i % 9) + 1}.{(i % 4) + 1}",
                    "evidence_type": ["document", "screenshot", "log", "configuration"][i % 4],
                    "collected_at": now.isoformat(),
                    "design_effectiveness": "effective" if i % 10 != 0 else "partially_effective",
                    "operating_effectiveness": "effective" if i % 15 != 0 else "not_tested",
                    "exceptions_noted": 0 if i % 20 != 0 else 1,
                    "status": "completed",
                }
                for i in range(1, 11)
            ],
            "control_mappings": [
                {
                    "mapping_id": f"MAP-SOC2-{i:03d}",
                    "soc2_control_id": f"CC{i}.1",
                    "guardrail_control_id": f"GR-{i:03d}",
                    "guardrail_control_name": f"ACGS Guardrail Control {i}",
                    "mapping_rationale": f"Guardrail control {i} implements SOC 2 CC{i}.1 requirements",
                    "coverage_percentage": 100 if i % 3 != 0 else 85,
                    "gaps": [] if i % 3 != 0 else ["Minor gap in logging coverage"],
                }
                for i in range(1, 6)
            ],
            "criteria_sections": [
                {
                    "criteria": "security",
                    "in_scope": True,
                    "controls": [
                        {
                            "control_id": f"CC{i}.1",
                            "title": f"Security Control {i}",
                            "control_objective": f"Ensure security requirement {i} is met",
                            "implementation_guidance": "Follow security best practices",
                        }
                        for i in range(1, 4)
                    ],
                    "overall_effectiveness": "effective",
                }
            ],
        }

    elif framework == ComplianceFramework.ISO27001:
        return {
            **base_data,
            "isms_scope": "Information Security Management System for AI Guardrails Platform",
            "total_controls": 93,
            "applicable_controls": 78,
            "implemented_controls": 74,
            "implementation_percentage": 94.9,
            "evidence_records": [
                {
                    "evidence_id": f"EV-ISO-{i:03d}",
                    "control_id": f"A.{5 + (i % 4)}.{(i % 8) + 1}",
                    "theme": ["organizational", "people", "physical", "technological"][i % 4],
                    "description": f"Evidence for ISO 27001 control A.{5 + (i % 4)}.{(i % 8) + 1}",
                    "evidence_type": "document",
                    "source": "ISMS Documentation System",
                    "collected_at": now.isoformat(),
                    "status": "completed",
                    "notes": None,
                }
                for i in range(1, 11)
            ],
            "statement_of_applicability": {
                "version": "1.0",
                "approved_by": "CISO",
                "approved_date": now.isoformat(),
                "entries": [
                    {
                        "control_id": f"A.5.{i}",
                        "control_title": f"Organizational Control {i}",
                        "theme": "organizational",
                        "applicability": "applicable",
                        "justification": "Required for information security governance",
                        "implementation_status": "implemented",
                        "implementation_method": "Policy and procedure",
                        "evidence_reference": f"ISMS-DOC-{i:03d}",
                    }
                    for i in range(1, 6)
                ],
            },
            "theme_sections": [
                {
                    "theme": "organizational",
                    "controls": [
                        {
                            "control_id": f"A.5.{i}",
                            "title": f"Organizational Policy {i}",
                            "description": "Security governance control",
                            "status": "implemented",
                        }
                        for i in range(1, 4)
                    ],
                },
                {
                    "theme": "technological",
                    "controls": [
                        {
                            "control_id": f"A.8.{i}",
                            "title": f"Technical Control {i}",
                            "description": "Technical security control",
                            "status": "implemented",
                        }
                        for i in range(1, 4)
                    ],
                },
            ],
        }

    elif framework == ComplianceFramework.GDPR:
        return {
            **base_data,
            "entity_role": "controller",
            "controller_record": {
                "controller_name": base_data["organization_name"],
                "controller_address": "123 Privacy Lane, Data City",
                "dpo": {
                    "name": "Data Protection Officer",
                    "email": "dpo@organization.com",
                    "phone": "+1-555-0100",
                },
                "processing_activities": [
                    {
                        "processing_id": f"PA-{i:03d}",
                        "name": f"Processing Activity {i}",
                        "purposes": ["Service provision", "Security monitoring"],
                        "lawful_basis": "legitimate_interest" if i % 2 == 0 else "contract",
                        "data_subject_categories": ["Users", "Administrators"],
                        "personal_data_categories": ["Contact information", "Usage data"],
                        "recipients": [
                            {"name": "Cloud Provider", "country": "US", "safeguards": "SCCs"}
                        ],
                        "third_country_transfers": i % 2 == 0,
                        "retention_period": "3 years after account closure",
                        "security_measures_summary": "Encryption, access controls, logging",
                        "status": "active",
                    }
                    for i in range(1, 6)
                ],
            },
            "data_flows": [
                {
                    "flow_id": f"DF-{i:03d}",
                    "name": f"Data Flow {i}",
                    "data_source": "User Application",
                    "data_destination": "Processing Service",
                    "data_categories": ["User data", "System logs"],
                    "crosses_border": i % 2 == 0,
                    "transfer_mechanism": "SCCs" if i % 2 == 0 else None,
                    "encrypted_in_transit": True,
                }
                for i in range(1, 4)
            ],
            "security_measures": [
                {
                    "measure_id": f"SM-{i:03d}",
                    "category": ["technical", "organizational"][i % 2],
                    "description": f"Security measure {i}: {'Encryption at rest' if i % 2 == 0 else 'Access control policy'}",
                    "status": "implemented",
                    "last_reviewed": now.isoformat(),
                }
                for i in range(1, 6)
            ],
        }

    else:  # EU_AI_ACT
        return {
            **base_data,
            "organization_role": "provider",
            "high_risk_systems_count": 2,
            "limited_risk_systems_count": 1,
            "minimal_risk_systems_count": 3,
            "ai_systems": [
                {
                    "system_id": f"AIS-{i:03d}",
                    "system_name": f"AI System {i}",
                    "risk_level": ["high_risk", "limited_risk", "minimal_risk"][i % 3],
                    "high_risk_category": "Annex III Category 1" if i % 3 == 0 else None,
                    "intended_purpose": f"AI system for content moderation and safety guardrails (System {i})",
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
                    "high_risk_category": "Annex III Category 1" if i % 2 == 0 else None,
                    "assessment_date": now.isoformat(),
                    "assessor": "Compliance Team",
                    "key_findings": "System meets EU AI Act requirements",
                    "recommendations": "Continue monitoring for regulatory updates",
                }
                for i in range(1, 4)
            ],
            "conformity_assessments": [
                {
                    "system_id": f"AIS-{i:03d}",
                    "assessment_type": "internal_control" if i % 2 == 0 else "third_party",
                    "assessment_date": now.isoformat(),
                    "assessment_result": "passed",
                    "certificate_number": f"EU-AI-CERT-{i:04d}" if i % 2 != 0 else None,
                    "expiry_date": None,
                    "notified_body": "EU AI Certification Body" if i % 2 != 0 else None,
                    "notes": "Assessment completed successfully",
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


def _validate_date_range(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> None:
    """
    Validate the date range parameters.

    Args:
        start_date: Start date for filtering.
        end_date: End date for filtering.

    Raises:
        HTTPException: If date range is invalid.
    """
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="Invalid date range: start_date must be before end_date",
            )

    # Check for future dates
    now = datetime.now(timezone.utc)
    if end_date and end_date > now:
        raise HTTPException(
            status_code=400,
            detail="Invalid date range: end_date cannot be in the future",
        )


@router.get("/export")
async def export_evidence(
    framework: str = Query(
        ...,
        description="Compliance framework (soc2, iso27001, gdpr, euaiact)",
        examples=["soc2", "iso27001", "gdpr", "euaiact"],
    ),
    format: str = Query(
        default="json",
        description="Export format (json, pdf, xlsx)",
        alias="format",
        examples=["json", "pdf", "xlsx"],
    ),
    start_date: Optional[datetime] = Query(  # noqa: B008
        None,
        description="Start date for evidence filtering (ISO 8601 format)",
    ),
    end_date: Optional[datetime] = Query(  # noqa: B008
        None,
        description="End date for evidence filtering (ISO 8601 format)",
    ),
):
    """
    Export compliance evidence for the specified framework.

    Returns evidence data in the requested format (JSON, PDF, or XLSX).
    Supports date range filtering for evidence records.

    - **framework**: Required. One of: soc2, iso27001, gdpr, euaiact
    - **format**: Output format. Default: json. Options: json, pdf, xlsx
    - **start_date**: Optional start date for filtering (ISO 8601)
    - **end_date**: Optional end date for filtering (ISO 8601)

    Returns:
        - JSON: JSONResponse with evidence data
        - PDF: StreamingResponse with PDF file
        - XLSX: StreamingResponse with Excel file
    """
    # Normalize framework
    framework_lower = framework.lower()

    # Validate framework
    valid_frameworks = [f.value for f in ComplianceFramework]
    if framework_lower not in valid_frameworks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework: {framework}. Valid options: {', '.join(valid_frameworks)}",
        )

    # Normalize format
    format_lower = format.lower()

    # Validate format
    valid_formats = [f.value for f in ExportFormat]
    if format_lower not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {format}. Valid options: {', '.join(valid_formats)}",
        )

    # Validate date range
    _validate_date_range(start_date, end_date)

    try:
        # Get framework enum
        framework_enum = ComplianceFramework(framework_lower)

        # Get evidence data
        evidence_data = _get_sample_evidence_data(
            framework=framework_enum,
            start_date=start_date,
            end_date=end_date,
        )

        # Handle JSON format
        if format_lower == "json":
            return JSONResponse(
                content=evidence_data,
                media_type=MEDIA_TYPES["json"],
            )

        # Handle PDF format
        elif format_lower == "pdf":
            buffer = generate_pdf_to_buffer(
                report_data=evidence_data,
                framework=framework_enum,
            )

            filename = f"{framework_lower}_evidence_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"

            return StreamingResponse(
                io.BytesIO(buffer.getvalue()),
                media_type=MEDIA_TYPES["pdf"],
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )

        # Handle XLSX format
        elif format_lower == "xlsx":
            buffer = generate_xlsx_to_buffer(
                report_data=evidence_data,
                framework=framework_enum,
            )

            filename = f"{framework_lower}_evidence_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"

            return StreamingResponse(
                io.BytesIO(buffer.getvalue()),
                media_type=MEDIA_TYPES["xlsx"],
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )

        # Handle DOCX format (not currently implemented for evidence export)
        elif format_lower == "docx":
            raise HTTPException(
                status_code=400,
                detail="DOCX format is not supported for evidence export. Use PDF or XLSX instead.",
            )

    except ValueError as e:
        logger.error(f"Validation error during evidence export: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error exporting evidence: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export evidence. Please try again later.",
        ) from e
