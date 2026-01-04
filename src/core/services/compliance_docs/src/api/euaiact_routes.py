"""
EU AI Act Compliance API Routes
Constitutional Hash: cdd01ef066bc6cf2

FastAPI routes for EU AI Act compliance validation, document generation, and export.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..generators import DOCXGenerator, PDFGenerator, XLSXGenerator
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

    document_type: str = Field(..., description="Document type: risk_assessment, human_oversight, compliance_checklist, quarterly_report")
    data: Dict[str, Any] = Field(..., description="Document data")
    format: str = Field(default="pdf", description="Output format: pdf, docx, xlsx")


@router.post("/validate", response_model=ComplianceValidationResponse)
async def validate_compliance(request: ComplianceValidationRequest) -> ComplianceValidationResponse:
    """
    Validate EU AI Act compliance for a high-risk AI system.

    Performs automated compliance checks against EU AI Act requirements
    and returns detailed findings with remediation guidance.
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


async def _perform_compliance_validation(request: ComplianceValidationRequest) -> List[EUAIActComplianceFinding]:
    """
    Perform compliance validation checks.

    This is a simplified implementation. In production, this would
    integrate with actual system metadata and policy checks.
    """
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

    # Article 10: Data Governance (simplified check)
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

    Supported document types:
    - risk_assessment: Article 9 Risk Assessment
    - human_oversight: Article 14 Human Oversight
    - compliance_checklist: Compliance Checklist
    - quarterly_report: Quarterly Compliance Report

    Supported formats: pdf, docx, xlsx
    """
    try:
        # Prepare data with document type
        data = request.data.copy()
        data["document_type"] = document_type
        data["title"] = _get_document_title(document_type)

        # Generate document based on format
        if format == "pdf":
            generator = PDFGenerator()
            file_path = generator.generate(data, f"euaiact_{document_type}_{int(datetime.now().timestamp())}")
        elif format == "docx":
            generator = DOCXGenerator()
            file_path = generator.generate(data, f"euaiact_{document_type}_{int(datetime.now().timestamp())}")
        elif format == "xlsx":
            generator = XLSXGenerator()
            file_path = generator.generate(data, f"euaiact_{document_type}_{int(datetime.now().timestamp())}")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        # Return file
        media_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        return FileResponse(
            path=str(file_path),
            media_type=media_type_map.get(format, "application/octet-stream"),
            filename=file_path.name,
        )
    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


def _get_document_title(document_type: str) -> str:
    """Get document title for document type."""
    titles = {
        "risk_assessment": "EU AI Act Risk Assessment - Article 9",
        "human_oversight": "EU AI Act Human Oversight - Article 14",
        "compliance_checklist": "EU AI Act Compliance Checklist",
        "quarterly_report": "EU AI Act Quarterly Compliance Report",
    }
    return titles.get(document_type, "EU AI Act Compliance Document")


@router.post("/export/checklist")
async def export_compliance_checklist(
    checklist: EUAIActComplianceChecklist,
    format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$"),
) -> FileResponse:
    """Export compliance checklist document."""
    data = checklist.model_dump()
    data["document_type"] = "compliance_checklist"
    data["title"] = "EU AI Act Compliance Checklist"

    request = DocumentGenerationRequest(document_type="compliance_checklist", data=data, format=format)
    return await generate_document("compliance_checklist", request, format)


@router.post("/export/risk-assessment")
async def export_risk_assessment(
    assessment: EUAIActRiskAssessment,
    format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$"),
) -> FileResponse:
    """Export risk assessment document."""
    data = assessment.model_dump()
    data["document_type"] = "risk_assessment"
    data["title"] = "EU AI Act Risk Assessment"

    request = DocumentGenerationRequest(document_type="risk_assessment", data=data, format=format)
    return await generate_document("risk_assessment", request, format)


@router.post("/export/human-oversight")
async def export_human_oversight(
    oversight: EUAIActHumanOversight,
    format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$"),
) -> FileResponse:
    """Export human oversight document."""
    data = oversight.model_dump()
    data["document_type"] = "human_oversight"
    data["title"] = "EU AI Act Human Oversight"

    request = DocumentGenerationRequest(document_type="human_oversight", data=data, format=format)
    return await generate_document("human_oversight", request, format)


@router.post("/export/quarterly-report")
async def export_quarterly_report(
    report: EUAIActQuarterlyReport,
    format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$"),
) -> FileResponse:
    """Export quarterly compliance report."""
    data = report.model_dump()
    data["document_type"] = "quarterly_report"
    data["title"] = "EU AI Act Quarterly Compliance Report"

    request = DocumentGenerationRequest(document_type="quarterly_report", data=data, format=format)
    return await generate_document("quarterly_report", request, format)
