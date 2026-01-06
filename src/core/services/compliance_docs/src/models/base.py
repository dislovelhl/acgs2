"""Constitutional Hash: cdd01ef066bc6cf2
Base Pydantic models for Compliance Documentation Service

Common base classes and shared field definitions used across all compliance frameworks.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

try:
    from src.core.shared.types import JSONDict
except ImportError:
    from typing import Any, Dict

    JSONDict = Dict[str, Any]


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""

    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    EU_AI_ACT = "euaiact"


class ExportFormat(str, Enum):
    """Supported export formats"""

    JSON = "json"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


class EvidenceStatus(str, Enum):
    """Status of compliance evidence"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_REVIEW = "requires_review"


class ComplianceBaseModel(BaseModel):
    """Base model for all compliance data structures"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
        populate_by_name=True,
    )


class VersionedDocument(ComplianceBaseModel):
    """Base model for versioned compliance documents"""

    version: str = Field(
        default="1.0.0",
        description="Document version following semantic versioning",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Document creation timestamp",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp",
    )
    created_by: Optional[str] = Field(
        default=None,
        description="User or system that created the document",
    )
    updated_by: Optional[str] = Field(
        default=None,
        description="User or system that last updated the document",
    )


class ControlEvidence(ComplianceBaseModel):
    """Generic evidence record for any compliance control"""

    evidence_id: str = Field(
        ...,
        description="Unique identifier for this evidence record",
    )
    control_id: str = Field(
        ...,
        description="ID of the control this evidence supports",
    )
    description: str = Field(
        ...,
        description="Description of the evidence",
    )
    evidence_type: str = Field(
        default="document",
        description="Type of evidence (document, screenshot, log, configuration)",
    )
    source: Optional[str] = Field(
        default=None,
        description="Source system or location of the evidence",
    )
    collected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the evidence was collected",
    )
    status: EvidenceStatus = Field(
        default=EvidenceStatus.NOT_STARTED,
        description="Current status of evidence collection",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the evidence",
    )
    attachments: list[str] = Field(
        default_factory=list,
        description="List of attachment file paths or URLs",
    )


class ComplianceReportMetadata(VersionedDocument):
    """Metadata for compliance reports"""

    report_id: str = Field(
        ...,
        description="Unique identifier for the report",
    )
    framework: ComplianceFramework = Field(
        ...,
        description="Compliance framework this report covers",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    report_title: str = Field(
        ...,
        description="Title of the compliance report",
    )
    reporting_period_start: datetime = Field(
        ...,
        description="Start of the reporting period",
    )
    reporting_period_end: datetime = Field(
        ...,
        description="End of the reporting period",
    )
    auditor: Optional[str] = Field(
        default=None,
        description="Name of the auditor or auditing firm",
    )
    confidentiality_level: str = Field(
        default="confidential",
        description="Document confidentiality classification",
    )


class ExportRequest(ComplianceBaseModel):
    """Request model for exporting compliance evidence"""

    framework: ComplianceFramework = Field(
        ...,
        description="Compliance framework to export",
    )
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Export format",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start date for evidence filtering (ISO 8601)",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End date for evidence filtering (ISO 8601)",
    )
    include_metadata: bool = Field(
        default=True,
        description="Include report metadata in export",
    )


class ReportGenerationRequest(ComplianceBaseModel):
    """Request model for generating compliance reports"""

    framework: ComplianceFramework = Field(
        ...,
        description="Compliance framework for the report",
    )
    format: ExportFormat = Field(
        default=ExportFormat.PDF,
        description="Output format for the report",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    report_title: Optional[str] = Field(
        default=None,
        description="Custom title for the report",
    )
    reporting_period_start: datetime = Field(
        ...,
        description="Start of the reporting period",
    )
    reporting_period_end: datetime = Field(
        ...,
        description="End of the reporting period",
    )
    include_evidence: bool = Field(
        default=True,
        description="Include detailed evidence in the report",
    )
    custom_sections: JSONDict = Field(
        default_factory=dict,
        description="Custom sections to include in the report",
    )


class ReportGenerationResponse(ComplianceBaseModel):
    """Response model for report generation"""

    report_id: str = Field(
        ...,
        description="Unique identifier for the generated report",
    )
    status: str = Field(
        ...,
        description="Generation status (pending, generating, completed, failed)",
    )
    download_url: Optional[str] = Field(
        default=None,
        description="URL to download the generated report",
    )
    file_size_bytes: Optional[int] = Field(
        default=None,
        description="Size of the generated file in bytes",
    )
    generated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the report was generated",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if generation failed",
    )
