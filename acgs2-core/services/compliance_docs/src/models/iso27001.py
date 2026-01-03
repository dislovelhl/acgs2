"""
ISO 27001:2022 Pydantic models for Compliance Documentation Service

Models for ISO 27001:2022 Annex A controls, Statement of Applicability (SoA),
and evidence collection.

ISO 27001:2022 has 93 controls organized into 4 themes:
- Organizational controls (A.5): 37 controls
- People controls (A.6): 8 controls
- Physical controls (A.7): 14 controls
- Technological controls (A.8): 34 controls
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import (
    ComplianceBaseModel,
    ControlEvidence,
    VersionedDocument,
)


class ControlTheme(str, Enum):
    """ISO 27001:2022 Annex A control themes"""

    ORGANIZATIONAL = "organizational"
    PEOPLE = "people"
    PHYSICAL = "physical"
    TECHNOLOGICAL = "technological"


class ControlApplicability(str, Enum):
    """Statement of Applicability status for controls"""

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    PARTIALLY_APPLICABLE = "partially_applicable"


class ImplementationStatus(str, Enum):
    """Implementation status of a control"""

    NOT_IMPLEMENTED = "not_implemented"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    NOT_REQUIRED = "not_required"


class ISO27001Control(ComplianceBaseModel):
    """Individual ISO 27001:2022 Annex A control definition"""

    control_id: str = Field(
        ...,
        description="Control identifier (e.g., A.5.1, A.8.12)",
    )
    theme: ControlTheme = Field(
        ...,
        description="Control theme category",
    )
    title: str = Field(
        ...,
        description="Control title",
    )
    description: str = Field(
        ...,
        description="Control description from the standard",
    )
    purpose: Optional[str] = Field(
        default=None,
        description="Purpose of the control",
    )
    attributes: list[str] = Field(
        default_factory=list,
        description="Control attributes (e.g., Preventive, Detective)",
    )
    implementation_guidance: Optional[str] = Field(
        default=None,
        description="Guidance for implementing this control",
    )
    related_controls: list[str] = Field(
        default_factory=list,
        description="Related control identifiers",
    )


class ISO27001ControlMapping(ComplianceBaseModel):
    """Mapping of guardrail controls to ISO 27001 controls"""

    mapping_id: str = Field(
        ...,
        description="Unique identifier for this mapping",
    )
    iso27001_control_id: str = Field(
        ...,
        description="ISO 27001 control identifier",
    )
    guardrail_control_id: str = Field(
        ...,
        description="ACGS guardrail control identifier",
    )
    guardrail_control_name: str = Field(
        ...,
        description="Name of the guardrail control",
    )
    mapping_rationale: str = Field(
        ...,
        description="Explanation of how the guardrail satisfies the control",
    )
    coverage_level: str = Field(
        default="full",
        description="Coverage level (full, partial, minimal)",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Identified gaps in control coverage",
    )


class StatementOfApplicabilityEntry(ComplianceBaseModel):
    """Single entry in the Statement of Applicability (SoA)"""

    control_id: str = Field(
        ...,
        description="ISO 27001 control identifier",
    )
    control_title: str = Field(
        ...,
        description="Control title",
    )
    theme: ControlTheme = Field(
        ...,
        description="Control theme category",
    )
    applicability: ControlApplicability = Field(
        default=ControlApplicability.APPLICABLE,
        description="Whether the control is applicable",
    )
    justification: str = Field(
        default="",
        description="Justification for applicability decision",
    )
    implementation_status: ImplementationStatus = Field(
        default=ImplementationStatus.NOT_IMPLEMENTED,
        description="Current implementation status",
    )
    implementation_description: str = Field(
        default="",
        description="Description of how the control is implemented",
    )
    responsible_party: Optional[str] = Field(
        default=None,
        description="Party responsible for the control",
    )
    implementation_date: Optional[datetime] = Field(
        default=None,
        description="Date the control was implemented",
    )
    review_date: Optional[datetime] = Field(
        default=None,
        description="Next scheduled review date",
    )
    evidence_reference: list[str] = Field(
        default_factory=list,
        description="References to supporting evidence",
    )


class ISO27001ControlEvidence(ControlEvidence):
    """Evidence record specific to ISO 27001 controls"""

    theme: ControlTheme = Field(
        ...,
        description="Control theme category",
    )
    implementation_status: ImplementationStatus = Field(
        default=ImplementationStatus.NOT_IMPLEMENTED,
        description="Implementation status of the control",
    )
    audit_findings: list[str] = Field(
        default_factory=list,
        description="Findings from internal or external audits",
    )
    nonconformities: list[str] = Field(
        default_factory=list,
        description="Any nonconformities identified",
    )
    corrective_actions: list[str] = Field(
        default_factory=list,
        description="Corrective actions taken or planned",
    )
    last_audit_date: Optional[datetime] = Field(
        default=None,
        description="Date of last audit of this control",
    )
    next_review_date: Optional[datetime] = Field(
        default=None,
        description="Date of next scheduled review",
    )


class StatementOfApplicability(VersionedDocument):
    """Complete Statement of Applicability (SoA) document"""

    soa_id: str = Field(
        ...,
        description="Unique identifier for this SoA",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    scope: str = Field(
        default="",
        description="ISMS scope covered by this SoA",
    )
    risk_assessment_reference: Optional[str] = Field(
        default=None,
        description="Reference to the risk assessment",
    )
    approved_by: Optional[str] = Field(
        default=None,
        description="Person who approved the SoA",
    )
    approval_date: Optional[datetime] = Field(
        default=None,
        description="Date of SoA approval",
    )
    entries: list[StatementOfApplicabilityEntry] = Field(
        default_factory=list,
        description="All SoA entries for Annex A controls",
    )
    total_controls: int = Field(
        default=93,
        description="Total number of controls in Annex A",
    )
    applicable_controls: int = Field(
        default=0,
        ge=0,
        description="Number of applicable controls",
    )
    implemented_controls: int = Field(
        default=0,
        ge=0,
        description="Number of implemented controls",
    )


class ControlThemeSection(ComplianceBaseModel):
    """Section for a control theme in the evidence report"""

    theme: ControlTheme = Field(
        ...,
        description="Control theme category",
    )
    theme_description: str = Field(
        default="",
        description="Description of the theme",
    )
    controls: list[ISO27001Control] = Field(
        default_factory=list,
        description="Controls in this theme",
    )
    soa_entries: list[StatementOfApplicabilityEntry] = Field(
        default_factory=list,
        description="SoA entries for controls in this theme",
    )
    evidence: list[ISO27001ControlEvidence] = Field(
        default_factory=list,
        description="Evidence for controls in this theme",
    )
    control_count: int = Field(
        default=0,
        ge=0,
        description="Number of controls in this theme",
    )
    implementation_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of controls implemented",
    )


class ISO27001ReportData(VersionedDocument):
    """Complete data model for an ISO 27001 compliance report"""

    report_id: str = Field(
        ...,
        description="Unique identifier for this report",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    isms_scope: str = Field(
        default="",
        description="Scope of the Information Security Management System",
    )
    certification_body: Optional[str] = Field(
        default=None,
        description="Certification body name",
    )
    certification_date: Optional[datetime] = Field(
        default=None,
        description="Date of certification",
    )
    certification_expiry: Optional[datetime] = Field(
        default=None,
        description="Certification expiry date",
    )
    audit_period_start: datetime = Field(
        ...,
        description="Start of the audit period",
    )
    audit_period_end: datetime = Field(
        ...,
        description="End of the audit period",
    )
    statement_of_applicability: StatementOfApplicability = Field(
        ...,
        description="Statement of Applicability",
    )
    theme_sections: list[ControlThemeSection] = Field(
        default_factory=list,
        description="Evidence organized by control theme",
    )
    control_mappings: list[ISO27001ControlMapping] = Field(
        default_factory=list,
        description="Mappings to guardrail controls",
    )
    nonconformities_summary: list[str] = Field(
        default_factory=list,
        description="Summary of nonconformities found",
    )
    improvement_opportunities: list[str] = Field(
        default_factory=list,
        description="Identified improvement opportunities",
    )


class ISO27001EvidenceMatrix(ComplianceBaseModel):
    """Evidence matrix for ISO 27001 controls"""

    matrix_id: str = Field(
        ...,
        description="Unique identifier for this matrix",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this matrix was generated",
    )
    soa_reference: Optional[str] = Field(
        default=None,
        description="Reference to the Statement of Applicability",
    )
    evidence_records: list[ISO27001ControlEvidence] = Field(
        default_factory=list,
        description="All evidence records in the matrix",
    )
    by_theme: dict = Field(
        default_factory=dict,
        description="Evidence grouped by theme",
    )
    total_controls: int = Field(
        default=93,
        ge=0,
        description="Total number of Annex A controls",
    )
    applicable_controls: int = Field(
        default=0,
        ge=0,
        description="Number of applicable controls",
    )
    controls_with_evidence: int = Field(
        default=0,
        ge=0,
        description="Number of controls with evidence",
    )
    controls_fully_implemented: int = Field(
        default=0,
        ge=0,
        description="Number of fully implemented controls",
    )


class ISO27001ExportRequest(ComplianceBaseModel):
    """Request model for ISO 27001 report export"""

    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    audit_period_start: datetime = Field(
        ...,
        description="Start of the audit period",
    )
    audit_period_end: datetime = Field(
        ...,
        description="End of the audit period",
    )
    themes_in_scope: list[ControlTheme] = Field(
        default_factory=lambda: list(ControlTheme),
        description="Control themes to include",
    )
    include_soa: bool = Field(
        default=True,
        description="Include Statement of Applicability",
    )
    include_evidence_matrix: bool = Field(
        default=True,
        description="Include detailed evidence matrix",
    )
    include_control_mappings: bool = Field(
        default=True,
        description="Include guardrail control mappings",
    )
    include_nonconformities: bool = Field(
        default=True,
        description="Include nonconformities summary",
    )
