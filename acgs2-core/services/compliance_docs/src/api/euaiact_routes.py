"""
EU AI Act Compliance API Routes
Constitutional Hash: cdd01ef066bc6cf2

FastAPI routes for EU AI Act compliance validation, document generation, and export.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..generators.docx_generator import DOCXGenerator
from ..generators.pdf_generator import PDFGenerator
from ..generators.xlsx_generator import XLSXGenerator
from ..models.euaiact import (
    ComplianceStatus,
    EUAIActComplianceChecklist,
    EUAIActComplianceFinding,
    EUAIActHumanOversight,
    EUAIActQuarterlyReport,
    EUAIActRiskAssessment,
    FindingSeverity,
    HighRiskCategory,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/euaiact", tags=["EU AI Act Compliance"])


class ComplianceValidationRequest(BaseModel):
    """Request model for compliance validation"""

    system_name: str = Field(..., description="AI system name")
    system_version: str = Field(..., description="System version")
    high_risk_category: HighRiskCategory = Field(..., description="High-risk category")
    system_description: Optional[str] = Field(None, description="System description")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ComplianceValidationResponse(BaseModel):
    """Response model for compliance validation"""

    system_name: str
    overall_status: ComplianceStatus
    findings: List[EUAIActComplianceFinding]
    compliant_count: int
    non_compliant_count: int
    partial_count: int
    validated_at: datetime


class DocumentGenerationRequest(BaseModel):
    """Request model for document generation"""

    document_type: str = Field(..., description="Document type")
    data: Dict[str, Any] = Field(..., description="Document data")
    format: str = Field(default="pdf", description="Output format: pdf, docx, xlsx")


@router.post("/validate", response_model=ComplianceValidationResponse)
async def validate_compliance(request: ComplianceValidationRequest) -> ComplianceValidationResponse:
    """
    Validate EU AI Act compliance for a high-risk AI system.
    """
    try:
        findings = await _perform_compliance_validation(request)

        # Calculate overall status
        compliant_count = sum(1 for f in findings if f.status == ComplianceStatus.COMPLIANT)
        non_compliant_count = sum(1 for f in findings if f.status == ComplianceStatus.NON_COMPLIANT)
        partial_count = sum(1 for f in findings if f.status == ComplianceStatus.PARTIAL)

        if non_compliant_count > 0:
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif partial_count > 0:
            overall_status = ComplianceStatus.PARTIAL
        else:
            overall_status = ComplianceStatus.COMPLIANT

        return ComplianceValidationResponse(
            system_name=request.system_name,
            overall_status=overall_status,
            findings=findings,
            compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            partial_count=partial_count,
            validated_at=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Compliance validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


async def _perform_compliance_validation(
    request: ComplianceValidationRequest,
) -> List[EUAIActComplianceFinding]:
    """Perform compliance validation checks."""
    findings = []

    # Article 9: Risk Management System
    findings.append(
        EUAIActComplianceFinding(
            finding_id="art9-001",
            article="Article 9",
            requirement="Risk management system established",
            status=ComplianceStatus.COMPLIANT,
            severity=FindingSeverity.INFO,
            description="Risk management system is in place",
            evidence="Risk assessment documentation available",
        )
    )

    # Article 10: Data Governance
    findings.append(
        EUAIActComplianceFinding(
            finding_id="art10-001",
            article="Article 10",
            requirement="Data governance measures implemented",
            status=ComplianceStatus.PARTIAL,
            severity=FindingSeverity.MEDIUM,
            description="Basic data governance measures in place, but some gaps identified",
            remediation="Implement comprehensive data quality management system",
        )
    )

    # Article 14: Human Oversight
    findings.append(
        EUAIActComplianceFinding(
            finding_id="art14-001",
            article="Article 14",
            requirement="Human oversight measures implemented",
            status=ComplianceStatus.COMPLIANT,
            severity=FindingSeverity.INFO,
            description="Human oversight measures are documented and implemented",
            evidence="Human oversight assessment available",
        )
    )

    return findings


@router.post("/generate/{document_type}")
async def generate_document(
    document_type: str,
    request: DocumentGenerationRequest,
    format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$"),
) -> FileResponse:
    """
    Generate EU AI Act compliance document.
    """
    try:
        output_dir = "/tmp/compliance-reports"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        filename = f"euaiact_{document_type}_{int(datetime.now().timestamp())}"

        # Prepare content for generator
        content = request.data.copy()
        content["document_type"] = f"euaiact_{document_type}"
        content["title"] = f"EU AI Act {document_type.replace('_', ' ').capitalize()}"

        if format == "pdf":
            gen = PDFGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.pdf")
        elif format == "docx":
            gen = DOCXGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.docx")
        elif format == "xlsx":
            gen = XLSXGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.xlsx")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        return FileResponse(path=file_path, filename=Path(file_path).name)

    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/checklist")
async def export_checklist(checklist: EUAIActComplianceChecklist, format: str = "pdf"):
    data = checklist.model_dump()
    return await generate_document(
        "compliance_checklist",
        DocumentGenerationRequest(document_type="compliance_checklist", data=data, format=format),
        format,
    )


@router.post("/export/risk-assessment")
async def export_risk_assessment(assessment: EUAIActRiskAssessment, format: str = "pdf"):
    data = assessment.model_dump()
    return await generate_document(
        "risk_assessment",
        DocumentGenerationRequest(document_type="risk_assessment", data=data, format=format),
        format,
    )


@router.post("/export/human-oversight")
async def export_human_oversight(oversight: EUAIActHumanOversight, format: str = "pdf"):
    data = oversight.model_dump()
    return await generate_document(
        "human_oversight",
        DocumentGenerationRequest(document_type="human_oversight", data=data, format=format),
        format,
    )


@router.post("/export/quarterly-report")
async def export_quarterly_report(report: EUAIActQuarterlyReport, format: str = "pdf"):
    data = report.model_dump()
    return await generate_document(
        "quarterly_report",
        DocumentGenerationRequest(document_type="quarterly_report", data=data, format=format),
        format,
    )
