"""
SOC 2 Type II Pydantic models for Compliance Documentation Service

Models for SOC 2 Trust Service Criteria (TSC) control mapping,
evidence collection, and report generation.

SOC 2 covers five Trust Service Criteria:
- Security (CC): Common Criteria controls
- Availability (A): System availability controls
- Processing Integrity (PI): Data processing accuracy
- Confidentiality (C): Data confidentiality controls
- Privacy (P): Personal information protection
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


class TrustServiceCriteria(str, Enum):
    """SOC 2 Trust Service Criteria categories"""

    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class ControlEffectiveness(str, Enum):
    """Control design and operating effectiveness status"""

    EFFECTIVE = "effective"
    INEFFECTIVE = "ineffective"
    NOT_TESTED = "not_tested"
    PARTIALLY_EFFECTIVE = "partially_effective"


class SOC2Control(ComplianceBaseModel):
    """Individual SOC 2 control definition"""

    control_id: str = Field(
        ...,
        description="SOC 2 control identifier (e.g., CC1.1, A1.2)",
    )
    criteria: TrustServiceCriteria = Field(
        ...,
        description="Trust Service Criteria category",
    )
    title: str = Field(
        ...,
        description="Control title",
    )
    description: str = Field(
        ...,
        description="Detailed control description",
    )
    control_objective: str = Field(
        ...,
        description="What the control aims to achieve",
    )
    implementation_guidance: Optional[str] = Field(
        default=None,
        description="Guidance for implementing this control",
    )
    testing_procedures: list[str] = Field(
        default_factory=list,
        description="Procedures for testing control effectiveness",
    )


class SOC2ControlMapping(ComplianceBaseModel):
    """Mapping of guardrail controls to SOC 2 controls"""

    mapping_id: str = Field(
        ...,
        description="Unique identifier for this mapping",
    )
    soc2_control_id: str = Field(
        ...,
        description="SOC 2 control identifier",
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
        description="Explanation of how the guardrail satisfies the SOC 2 control",
    )
    coverage_percentage: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Percentage of control coverage (0-100)",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Identified gaps in control coverage",
    )
    compensating_controls: list[str] = Field(
        default_factory=list,
        description="Compensating controls for identified gaps",
    )


class SOC2ControlEvidence(ControlEvidence):
    """Evidence record specific to SOC 2 controls"""

    criteria: TrustServiceCriteria = Field(
        ...,
        description="Trust Service Criteria category",
    )
    design_effectiveness: ControlEffectiveness = Field(
        default=ControlEffectiveness.NOT_TESTED,
        description="Design effectiveness of the control",
    )
    operating_effectiveness: ControlEffectiveness = Field(
        default=ControlEffectiveness.NOT_TESTED,
        description="Operating effectiveness of the control",
    )
    testing_period_start: Optional[datetime] = Field(
        default=None,
        description="Start of the testing period for Type II",
    )
    testing_period_end: Optional[datetime] = Field(
        default=None,
        description="End of the testing period for Type II",
    )
    sample_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Sample size used for testing",
    )
    exceptions_noted: int = Field(
        default=0,
        ge=0,
        description="Number of exceptions noted during testing",
    )
    exception_details: list[str] = Field(
        default_factory=list,
        description="Details of any exceptions noted",
    )


class TrustServiceCriteriaSection(ComplianceBaseModel):
    """A section covering one Trust Service Criteria in a SOC 2 report"""

    criteria: TrustServiceCriteria = Field(
        ...,
        description="Trust Service Criteria category",
    )
    in_scope: bool = Field(
        default=True,
        description="Whether this criteria is in scope for the audit",
    )
    controls: list[SOC2Control] = Field(
        default_factory=list,
        description="Controls within this criteria",
    )
    evidence: list[SOC2ControlEvidence] = Field(
        default_factory=list,
        description="Evidence collected for this criteria",
    )
    overall_effectiveness: ControlEffectiveness = Field(
        default=ControlEffectiveness.NOT_TESTED,
        description="Overall effectiveness of controls in this criteria",
    )


class SystemDescription(ComplianceBaseModel):
    """SOC 2 Type II system description"""

    system_name: str = Field(
        ...,
        description="Name of the system being evaluated",
    )
    system_description: str = Field(
        ...,
        description="Detailed description of the system",
    )
    principal_service_commitments: list[str] = Field(
        default_factory=list,
        description="Commitments made to users of the system",
    )
    system_requirements: list[str] = Field(
        default_factory=list,
        description="Requirements the system must meet",
    )
    components: list[str] = Field(
        default_factory=list,
        description="Major system components",
    )
    boundaries: str = Field(
        default="",
        description="System boundaries and scope",
    )
    infrastructure: str = Field(
        default="",
        description="Infrastructure supporting the system",
    )
    software: str = Field(
        default="",
        description="Software components of the system",
    )
    people: str = Field(
        default="",
        description="Roles and personnel involved in system operations",
    )
    data: str = Field(
        default="",
        description="Types of data processed by the system",
    )
    processes: str = Field(
        default="",
        description="Key business processes",
    )


class SOC2ReportData(VersionedDocument):
    """Complete data model for a SOC 2 Type II report"""

    report_type: str = Field(
        default="Type II",
        description="SOC 2 report type (Type I or Type II)",
    )
    organization_name: str = Field(
        ...,
        description="Name of the service organization",
    )
    service_auditor: str = Field(
        default="",
        description="Name of the service auditor firm",
    )
    audit_period_start: datetime = Field(
        ...,
        description="Start of the audit period",
    )
    audit_period_end: datetime = Field(
        ...,
        description="End of the audit period",
    )
    system_description: SystemDescription = Field(
        ...,
        description="Description of the system under audit",
    )
    criteria_sections: list[TrustServiceCriteriaSection] = Field(
        default_factory=list,
        description="Trust Service Criteria sections",
    )
    control_mappings: list[SOC2ControlMapping] = Field(
        default_factory=list,
        description="Control mappings to guardrail controls",
    )
    management_assertion: str = Field(
        default="",
        description="Management's assertion about the system",
    )
    auditor_opinion: str = Field(
        default="",
        description="Service auditor's opinion",
    )
    subservice_organizations: list[str] = Field(
        default_factory=list,
        description="Subservice organizations used",
    )
    complementary_user_entity_controls: list[str] = Field(
        default_factory=list,
        description="Controls expected to be in place at user entities",
    )


class SOC2EvidenceMatrix(ComplianceBaseModel):
    """Evidence matrix for SOC 2 controls"""

    matrix_id: str = Field(
        ...,
        description="Unique identifier for this matrix",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    audit_period: str = Field(
        ...,
        description="Audit period description",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this matrix was generated",
    )
    criteria_in_scope: list[TrustServiceCriteria] = Field(
        default_factory=list,
        description="Trust Service Criteria in scope",
    )
    evidence_records: list[SOC2ControlEvidence] = Field(
        default_factory=list,
        description="All evidence records in the matrix",
    )
    total_controls: int = Field(
        default=0,
        ge=0,
        description="Total number of controls in scope",
    )
    controls_tested: int = Field(
        default=0,
        ge=0,
        description="Number of controls tested",
    )
    controls_effective: int = Field(
        default=0,
        ge=0,
        description="Number of controls found effective",
    )
    controls_with_exceptions: int = Field(
        default=0,
        ge=0,
        description="Number of controls with exceptions",
    )


class SOC2ExportRequest(ComplianceBaseModel):
    """Request model for SOC 2 report export"""

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
    criteria_in_scope: list[TrustServiceCriteria] = Field(
        default_factory=lambda: list(TrustServiceCriteria),
        description="Trust Service Criteria to include",
    )
    include_system_description: bool = Field(
        default=True,
        description="Include system description section",
    )
    include_evidence_matrix: bool = Field(
        default=True,
        description="Include detailed evidence matrix",
    )
    include_control_mappings: bool = Field(
        default=True,
        description="Include guardrail control mappings",
    )
