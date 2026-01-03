"""
EU AI Act compliance models and data structures
Constitutional Hash: cdd01ef066bc6cf2

Models for EU AI Act compliance documentation, validation, and reporting
for high-risk AI systems per EU Regulation 2024/1689.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    """EU AI Act risk levels for AI systems"""

    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


class HighRiskCategory(str, Enum):
    """EU AI Act Article 6 high-risk AI system categories"""

    BIOMETRIC_IDENTIFICATION = "biometric_identification"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"
    EDUCATION_VOCATIONAL = "education_vocational"
    EMPLOYMENT_WORKPLACE = "employment_workplace"
    ACCESS_TO_ESSENTIAL_SERVICES = "access_to_essential_services"
    LAW_ENFORCEMENT = "law_enforcement"
    MIGRATION_ASYLUM = "migration_asylum"
    ADMINISTRATION_OF_JUSTICE = "administration_of_justice"


class ComplianceStatus(str, Enum):
    """Compliance validation status"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_ASSESSED = "not_assessed"


class FindingSeverity(str, Enum):
    """Severity levels for compliance findings"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EUAIActComplianceFinding(BaseModel):
    """Individual compliance finding from validation"""

    finding_id: str = Field(..., description="Unique finding identifier")
    article: str = Field(..., description="EU AI Act article reference (e.g., 'Article 9')")
    requirement: str = Field(..., description="Specific requirement text")
    status: ComplianceStatus = Field(..., description="Compliance status")
    severity: FindingSeverity = Field(..., description="Finding severity")
    description: str = Field(..., description="Detailed finding description")
    evidence: Optional[str] = Field(None, description="Evidence or proof of compliance")
    remediation: Optional[str] = Field(None, description="Recommended remediation steps")
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(), description="When finding was assessed"
    )


class EUAIActComplianceChecklist(BaseModel):
    """EU AI Act compliance checklist for high-risk AI systems"""

    system_name: str = Field(..., description="High-risk AI system identifier")
    system_version: str = Field(..., description="System version")
    organization_name: str = Field(..., description="Organization deploying the system")
    assessment_date: date = Field(..., description="Date of compliance assessment")
    assessor_name: str = Field(..., description="Name of person conducting assessment")
    assessor_role: str = Field(..., description="Role of assessor")
    high_risk_category: HighRiskCategory = Field(..., description="High-risk category per Article 6")
    findings: List[EUAIActComplianceFinding] = Field(
        default_factory=list, description="Compliance findings"
    )
    overall_status: ComplianceStatus = Field(..., description="Overall compliance status")
    notes: Optional[str] = Field(None, description="Additional assessment notes")

    @field_validator("assessment_date")
    @classmethod
    def validate_assessment_date(cls, v: date) -> date:
        """Ensure assessment date is not in the future."""
        if v > date.today():
            raise ValueError("Assessment date cannot be in the future")
        return v


class RiskFactor(BaseModel):
    """Individual risk factor in risk assessment"""

    factor_id: str = Field(..., description="Unique risk factor identifier")
    category: str = Field(..., description="Risk category (e.g., 'Data Quality', 'Bias')")
    description: str = Field(..., description="Risk factor description")
    likelihood: str = Field(..., description="Likelihood assessment (e.g., 'High', 'Medium', 'Low')")
    impact: str = Field(..., description="Impact assessment (e.g., 'High', 'Medium', 'Low')")
    risk_level: RiskLevel = Field(..., description="Calculated risk level")
    mitigation_measures: List[str] = Field(
        default_factory=list, description="Mitigation measures for this risk"
    )


class EUAIActRiskAssessment(BaseModel):
    """Article 9 Risk Assessment Model"""

    system_name: str = Field(..., description="High-risk AI system identifier")
    system_version: str = Field(..., description="System version")
    organization_name: str = Field(..., description="Organization name")
    assessment_date: date = Field(..., description="Date of risk assessment")
    assessor_name: str = Field(..., description="Name of person conducting assessment")
    assessor_qualifications: str = Field(..., description="Assessor qualifications/credentials")
    high_risk_category: HighRiskCategory = Field(..., description="High-risk category per Article 6")
    system_description: str = Field(..., description="Description of the AI system")
    intended_purpose: str = Field(..., description="Intended purpose of the AI system")
    risk_factors: List[RiskFactor] = Field(..., description="Identified risk factors")
    overall_risk_level: RiskLevel = Field(..., description="Overall risk level assessment")
    mitigation_measures: List[str] = Field(
        default_factory=list, description="Overall mitigation measures"
    )
    residual_risks: List[str] = Field(
        default_factory=list, description="Residual risks after mitigation"
    )
    review_date: Optional[date] = Field(None, description="Planned review date for reassessment")

    @field_validator("assessment_date")
    @classmethod
    def validate_assessment_date(cls, v: date) -> date:
        """Ensure assessment date is not in the future."""
        if v > date.today():
            raise ValueError("Assessment date cannot be in the future")
        return v


class HumanOversightMeasure(BaseModel):
    """Individual human oversight measure"""

    measure_id: str = Field(..., description="Unique measure identifier")
    measure_type: str = Field(
        ..., description="Type of oversight (e.g., 'Pre-deployment review', 'Real-time monitoring')"
    )
    description: str = Field(..., description="Description of the oversight measure")
    responsible_role: str = Field(..., description="Role responsible for this measure")
    frequency: str = Field(..., description="Frequency of oversight (e.g., 'Continuous', 'Daily')")
    triggers: List[str] = Field(
        default_factory=list, description="Triggers that activate this oversight measure"
    )
    documentation: Optional[str] = Field(None, description="Documentation reference")


class EUAIActHumanOversight(BaseModel):
    """Article 14 Human Oversight Model"""

    system_name: str = Field(..., description="High-risk AI system identifier")
    system_version: str = Field(..., description="System version")
    organization_name: str = Field(..., description="Organization name")
    assessment_date: date = Field(..., description="Date of human oversight assessment")
    assessor_name: str = Field(..., description="Name of person conducting assessment")
    oversight_measures: List[HumanOversightMeasure] = Field(
        ..., description="Human oversight measures implemented"
    )
    oversight_effectiveness: str = Field(
        ..., description="Assessment of oversight effectiveness"
    )
    escalation_procedures: List[str] = Field(
        default_factory=list, description="Procedures for escalating issues to human oversight"
    )
    training_requirements: List[str] = Field(
        default_factory=list, description="Training requirements for human overseers"
    )
    documentation_references: List[str] = Field(
        default_factory=list, description="References to oversight documentation"
    )

    @field_validator("assessment_date")
    @classmethod
    def validate_assessment_date(cls, v: date) -> date:
        """Ensure assessment date is not in the future."""
        if v > date.today():
            raise ValueError("Assessment date cannot be in the future")
        return v


class QuarterlyComplianceMetrics(BaseModel):
    """Quarterly compliance metrics"""

    quarter: str = Field(..., description="Quarter identifier (e.g., '2024-Q1')")
    period_start: date = Field(..., description="Quarter start date")
    period_end: date = Field(..., description="Quarter end date")
    total_assessments: int = Field(..., description="Total compliance assessments conducted")
    compliant_systems: int = Field(..., description="Number of compliant systems")
    non_compliant_systems: int = Field(..., description="Number of non-compliant systems")
    partial_compliance_systems: int = Field(..., description="Number of partially compliant systems")
    critical_findings: int = Field(..., description="Number of critical findings")
    high_findings: int = Field(..., description="Number of high-severity findings")
    remediation_actions_taken: int = Field(..., description="Number of remediation actions taken")


class EUAIActQuarterlyReport(BaseModel):
    """Quarterly compliance report"""

    organization_name: str = Field(..., description="Organization name")
    report_period: QuarterlyComplianceMetrics = Field(..., description="Quarter metrics")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(), description="Report generation timestamp"
    )
    generated_by: str = Field(..., description="System/user that generated the report")
    systems_assessed: List[str] = Field(
        ..., description="List of AI systems assessed during the quarter"
    )
    key_findings: List[str] = Field(..., description="Key compliance findings summary")
    remediation_actions: List[str] = Field(
        default_factory=list, description="Remediation actions taken or planned"
    )
    next_quarter_priorities: List[str] = Field(
        default_factory=list, description="Priorities for next quarter"
    )
    executive_summary: str = Field(..., description="Executive summary of compliance status")
