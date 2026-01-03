"""
SOC 2 Type II compliance models and data structures
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class SOC2TrustServiceCriteria(str):
    """SOC 2 Trust Service Criteria enumeration"""

    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class SOC2ControlMapping(BaseModel):
    """Mapping of guardrail controls to SOC 2 controls"""

    control_id: str = Field(..., description="SOC 2 control identifier (e.g., CC1.1, CC2.2)")
    control_name: str = Field(..., description="SOC 2 control name")
    criteria: SOC2TrustServiceCriteria = Field(..., description="Trust Service Criteria")
    description: str = Field(..., description="Control description")
    guardrail_mapping: List[str] = Field(
        ..., description="List of ACGS-2 guardrail components that implement this control"
    )
    evidence_sources: List[str] = Field(..., description="Sources of evidence for this control")
    testing_frequency: str = Field(
        ..., description="How often this control is tested (e.g., 'Quarterly', 'Annually')"
    )
    last_tested: Optional[date] = Field(None, description="Date of last control test")
    test_results: str = Field(..., description="Results of last control test")


class SOC2Evidence(BaseModel):
    """Evidence data for SOC 2 compliance"""

    framework: str = Field(default="soc2", description="Compliance framework")
    criteria: SOC2TrustServiceCriteria = Field(..., description="Trust Service Criteria")
    period_start: date = Field(..., description="Start date of evidence period")
    period_end: date = Field(..., description="End date of evidence period")
    controls: List[SOC2ControlMapping] = Field(..., description="SOC 2 controls with mappings")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(), description="When this evidence was generated"
    )
    version: str = Field(default="1.0", description="Evidence version")

    @validator("period_end")
    def period_end_after_start(cls, v, values):
        if "period_start" in values and v < values["period_start"]:
            raise ValueError("period_end must be after period_start")
        return v


class SOC2ReportMetadata(BaseModel):
    """Metadata for SOC 2 compliance reports"""

    organization_name: str = Field(..., description="Organization name")
    report_period: str = Field(
        ..., description="Reporting period (e.g., 'January 1, 2024 - December 31, 2024')"
    )
    auditor_name: str = Field(..., description="Name of auditing firm")
    audit_type: str = Field(default="Type II", description="SOC 2 audit type")
    criteria_covered: List[SOC2TrustServiceCriteria] = Field(
        ..., description="TSC criteria covered"
    )
    report_date: date = Field(..., description="Date report was issued")


class SOC2ComplianceReport(BaseModel):
    """Complete SOC 2 compliance report data"""

    metadata: SOC2ReportMetadata = Field(..., description="Report metadata")
    evidence: SOC2Evidence = Field(..., description="Compliance evidence")
    executive_summary: str = Field(..., description="Executive summary of findings")
    control_effectiveness: Dict[str, Any] = Field(
        ..., description="Control effectiveness assessment"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )
