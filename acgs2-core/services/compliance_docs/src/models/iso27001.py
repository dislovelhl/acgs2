"""
ISO 27001:2022 compliance models and data structures
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ISO27001Theme(str):
    """ISO 27001:2022 themes enumeration"""
    PEOPLE = "people"
    PHYSICAL = "physical"
    TECHNOLOGICAL = "technological"


class ISO27001Control(BaseModel):
    """ISO 27001:2022 control structure"""

    control_id: str = Field(..., description="Control identifier (e.g., A.5.1, A.9.2)")
    control_name: str = Field(..., description="Control name")
    theme: ISO27001Theme = Field(..., description="Control theme (People, Physical, Technological)")
    objective: str = Field(..., description="Control objective")
    description: str = Field(..., description="Detailed control description")
    implementation_guidance: str = Field(..., description="Implementation guidance")
    guardrail_mapping: List[str] = Field(..., description="ACGS-2 guardrail components implementing this control")
    evidence_required: List[str] = Field(..., description="Types of evidence needed for compliance")
    risk_level: str = Field(..., description="Risk level (Low, Medium, High)")


class ISO27001Evidence(BaseModel):
    """Evidence data for ISO 27001 compliance"""

    framework: str = Field(default="iso27001", description="Compliance framework")
    standard_version: str = Field(default="ISO 27001:2022", description="ISO standard version")
    controls: List[ISO27001Control] = Field(..., description="ISO 27001 controls with mappings")
    assessment_period: str = Field(..., description="Assessment period")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(), description="When this evidence was generated")
    version: str = Field(default="1.0", description="Evidence version")


class ISO27001StatementOfApplicability(BaseModel):
    """ISO 27001 Statement of Applicability"""

    organization_name: str = Field(..., description="Organization name")
    standard_version: str = Field(default="ISO 27001:2022", description="ISO standard version")
    assessment_date: date = Field(..., description="Date of applicability assessment")
    controls: List[ISO27001Control] = Field(..., description="Controls with applicability status")
    justification: str = Field(..., description="Justification for control selection")
    exclusions: List[Dict[str, Any]] = Field(default_factory=list, description="Excluded controls with justification")


class ISO27001ComplianceReport(BaseModel):
    """Complete ISO 27001 compliance report data"""

    organization_name: str = Field(..., description="Organization name")
    certification_scope: str = Field(..., description="Scope of ISO 27001 certification")
    assessment_period: str = Field(..., description="Assessment period")
    statement_of_applicability: ISO27001StatementOfApplicability = Field(..., description="Statement of Applicability")
    evidence_matrix: List[Dict[str, Any]] = Field(..., description="Evidence matrix for all controls")
    compliance_status: Dict[str, Any] = Field(..., description="Overall compliance status")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    next_audit_date: Optional[date] = Field(None, description="Date of next scheduled audit")
