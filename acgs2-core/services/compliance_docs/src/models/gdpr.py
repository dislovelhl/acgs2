"""
GDPR Article 30 compliance models and data structures
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GDPRDataCategory(str):
    """GDPR personal data categories"""

    PERSONAL_IDENTIFIERS = "personal_identifiers"
    FINANCIAL_DATA = "financial_data"
    HEALTH_DATA = "health_data"
    LOCATION_DATA = "location_data"
    COMMUNICATION_DATA = "communication_data"
    BEHAVIORAL_DATA = "behavioral_data"
    SENSITIVE_DATA = "sensitive_data"


class GDPRProcessingPurpose(str):
    """GDPR processing purposes"""

    AI_GOVERNANCE = "ai_governance"
    SECURITY_MONITORING = "security_monitoring"
    AUDIT_LOGGING = "audit_logging"
    COMPLIANCE_REPORTING = "compliance_reporting"
    SYSTEM_MAINTENANCE = "system_maintenance"


class GDPRLegalBasis(str):
    """GDPR legal bases for processing"""

    LEGITIMATE_INTEREST = "legitimate_interest"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    PUBLIC_TASK = "public_task"
    CONSENT = "consent"
    VITAL_INTEREST = "vital_interest"


class GDPRRecipientCategory(str):
    """Categories of recipients of personal data"""

    PROCESSORS = "processors"
    CONTROLLERS = "controllers"
    AUTHORITIES = "authorities"
    INTERNAL_RECIPIENTS = "internal_recipients"


class GDPRProcessingActivity(BaseModel):
    """GDPR processing activity record"""

    activity_id: str = Field(..., description="Unique identifier for the processing activity")
    name: str = Field(..., description="Name of the processing activity")
    purpose: GDPRProcessingPurpose = Field(..., description="Purpose of processing")
    legal_basis: GDPRLegalBasis = Field(..., description="Legal basis for processing")
    data_categories: List[GDPRDataCategory] = Field(
        ..., description="Categories of personal data processed"
    )
    data_subjects: List[str] = Field(
        ..., description="Categories of data subjects (e.g., 'Users', 'Customers')"
    )
    recipients: Dict[GDPRRecipientCategory, List[str]] = Field(
        ..., description="Recipients of personal data"
    )
    retention_period: str = Field(..., description="Retention period for personal data")
    security_measures: List[str] = Field(..., description="Security measures implemented")
    transfers: List[Dict[str, Any]] = Field(
        default_factory=list, description="International data transfers"
    )


class GDPRArticle30Record(BaseModel):
    """GDPR Article 30 Records of Processing Activities"""

    controller_name: str = Field(..., description="Name and contact details of the controller")
    controller_representative: Optional[str] = Field(
        None, description="Controller representative (if applicable)"
    )
    dpo_contact: str = Field(..., description="Data Protection Officer contact details")
    record_date: date = Field(..., description="Date this record was created/updated")
    processing_activities: List[GDPRProcessingActivity] = Field(
        ..., description="List of processing activities"
    )
    version: str = Field(default="1.0", description="Record version")

    @validator("record_date")
    def record_date_not_future(cls, v):
        if v > date.today():
            raise ValueError("record_date cannot be in the future")
        return v


class GDPRDataProtectionImpactAssessment(BaseModel):
    """GDPR DPIA summary for high-risk processing"""

    activity_id: str = Field(..., description="Processing activity ID")
    assessment_date: date = Field(..., description="Date of DPIA")
    risk_level: str = Field(..., description="Risk level assessment (High, Medium, Low)")
    risks_identified: List[str] = Field(..., description="Identified risks to rights and freedoms")
    measures_implemented: List[str] = Field(..., description="Measures to address identified risks")
    residual_risks: List[str] = Field(
        default_factory=list, description="Residual risks after mitigation"
    )
    review_date: Optional[date] = Field(None, description="Date for DPIA review")


class GDPRComplianceReport(BaseModel):
    """Complete GDPR compliance report"""

    organization_name: str = Field(..., description="Organization name")
    reporting_period: str = Field(..., description="Reporting period")
    records_of_processing: GDPRArticle30Record = Field(..., description="Article 30 records")
    dpia_summaries: List[GDPRDataProtectionImpactAssessment] = Field(
        default_factory=list, description="DPIA summaries"
    )
    data_breaches: List[Dict[str, Any]] = Field(
        default_factory=list, description="Data breach records"
    )
    subject_rights_requests: Dict[str, int] = Field(
        default_factory=dict, description="Subject rights requests by type"
    )
    compliance_status: Dict[str, Any] = Field(..., description="Overall GDPR compliance status")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )
