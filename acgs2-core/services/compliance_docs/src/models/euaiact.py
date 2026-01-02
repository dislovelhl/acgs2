"""
EU AI Act Pydantic models for Compliance Documentation Service

Models for EU AI Act risk classification, conformity assessment,
and technical documentation requirements.

The EU AI Act (2024) categorizes AI systems by risk level:
- Unacceptable risk: Prohibited practices (Article 5)
- High risk: Subject to strict requirements (Annex III)
- Limited risk: Transparency obligations (Article 52)
- Minimal risk: No specific requirements
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ComplianceBaseModel, VersionedDocument


class RiskLevel(str, Enum):
    """EU AI Act risk classification levels"""

    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


class ProviderRole(str, Enum):
    """Role in the AI system value chain"""

    PROVIDER = "provider"
    DEPLOYER = "deployer"
    IMPORTER = "importer"
    DISTRIBUTOR = "distributor"
    AUTHORIZED_REPRESENTATIVE = "authorized_representative"


class HighRiskCategory(str, Enum):
    """High-risk AI system categories (Annex III)"""

    BIOMETRIC = "biometric_identification"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"
    EDUCATION_TRAINING = "education_training"
    EMPLOYMENT = "employment"
    ESSENTIAL_SERVICES = "essential_services"
    LAW_ENFORCEMENT = "law_enforcement"
    MIGRATION_ASYLUM = "migration_asylum"
    JUSTICE_DEMOCRACY = "justice_democracy"


class ConformityAssessmentType(str, Enum):
    """Type of conformity assessment procedure"""

    INTERNAL_CONTROL = "internal_control"
    NOTIFIED_BODY = "notified_body"
    QUALITY_MANAGEMENT = "quality_management"


class TransparencyObligation(str, Enum):
    """Transparency obligations for limited risk systems"""

    AI_INTERACTION_DISCLOSURE = "ai_interaction_disclosure"
    EMOTION_RECOGNITION_DISCLOSURE = "emotion_recognition_disclosure"
    BIOMETRIC_CATEGORIZATION_DISCLOSURE = "biometric_categorization_disclosure"
    DEEPFAKE_DISCLOSURE = "deepfake_disclosure"


class RiskAssessmentResult(ComplianceBaseModel):
    """Result of AI system risk classification"""

    assessment_id: str = Field(
        ...,
        description="Unique identifier for this assessment",
    )
    system_name: str = Field(
        ...,
        description="Name of the AI system",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Classified risk level",
    )
    high_risk_category: Optional[HighRiskCategory] = Field(
        default=None,
        description="High-risk category if applicable",
    )
    classification_rationale: str = Field(
        ...,
        description="Rationale for the risk classification",
    )
    assessed_by: str = Field(
        default="",
        description="Person or team that performed the assessment",
    )
    assessment_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date of the assessment",
    )
    review_required_by: Optional[datetime] = Field(
        default=None,
        description="Date by which reassessment is required",
    )
    prohibited_practices_check: list[str] = Field(
        default_factory=list,
        description="Prohibited practices checked (Article 5)",
    )
    is_prohibited: bool = Field(
        default=False,
        description="Whether the system falls under prohibited practices",
    )


class AISystemDescription(ComplianceBaseModel):
    """Detailed description of an AI system"""

    system_id: str = Field(
        ...,
        description="Unique identifier for the AI system",
    )
    name: str = Field(
        ...,
        description="Name of the AI system",
    )
    version: str = Field(
        default="1.0.0",
        description="Version of the AI system",
    )
    description: str = Field(
        ...,
        description="Detailed description of the system's purpose and function",
    )
    intended_purpose: str = Field(
        ...,
        description="Intended purpose as per Article 3",
    )
    intended_users: list[str] = Field(
        default_factory=list,
        description="Categories of intended users",
    )
    deployment_context: str = Field(
        default="",
        description="Context in which the system will be deployed",
    )
    ai_techniques: list[str] = Field(
        default_factory=list,
        description="AI techniques used (e.g., machine learning, neural networks)",
    )
    training_data_description: str = Field(
        default="",
        description="Description of training data used",
    )
    input_data_types: list[str] = Field(
        default_factory=list,
        description="Types of input data processed",
    )
    output_description: str = Field(
        default="",
        description="Description of system outputs",
    )
    hardware_requirements: str = Field(
        default="",
        description="Hardware requirements for deployment",
    )
    software_dependencies: list[str] = Field(
        default_factory=list,
        description="Software dependencies",
    )


class ProviderInformation(ComplianceBaseModel):
    """Information about the AI system provider"""

    provider_id: str = Field(
        ...,
        description="Unique identifier for the provider",
    )
    name: str = Field(
        ...,
        description="Legal name of the provider",
    )
    address: str = Field(
        default="",
        description="Registered address",
    )
    country: str = Field(
        default="",
        description="Country of establishment",
    )
    contact_email: str = Field(
        default="",
        description="Contact email address",
    )
    contact_phone: Optional[str] = Field(
        default=None,
        description="Contact phone number",
    )
    authorized_representative: Optional[str] = Field(
        default=None,
        description="EU authorized representative if provider is outside EU",
    )
    role: ProviderRole = Field(
        default=ProviderRole.PROVIDER,
        description="Role in the AI value chain",
    )


class QualityManagementSystem(ComplianceBaseModel):
    """Quality management system requirements for high-risk AI"""

    qms_id: str = Field(
        ...,
        description="Quality management system identifier",
    )
    is_implemented: bool = Field(
        default=False,
        description="Whether QMS is fully implemented",
    )
    policies_documentation: list[str] = Field(
        default_factory=list,
        description="QMS policies documented",
    )
    design_procedures: str = Field(
        default="",
        description="Procedures for AI system design",
    )
    development_procedures: str = Field(
        default="",
        description="Procedures for development and testing",
    )
    data_management_procedures: str = Field(
        default="",
        description="Procedures for data management",
    )
    risk_management_procedures: str = Field(
        default="",
        description="Risk management procedures",
    )
    post_market_monitoring: str = Field(
        default="",
        description="Post-market monitoring procedures",
    )
    incident_reporting_procedures: str = Field(
        default="",
        description="Serious incident reporting procedures",
    )
    last_audit_date: Optional[datetime] = Field(
        default=None,
        description="Date of last QMS audit",
    )
    certification_reference: Optional[str] = Field(
        default=None,
        description="QMS certification reference (e.g., ISO 9001)",
    )


class RiskManagementRecord(ComplianceBaseModel):
    """Risk management system record (Article 9)"""

    record_id: str = Field(
        ...,
        description="Risk management record identifier",
    )
    risk_identification_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date risk was identified",
    )
    risk_description: str = Field(
        ...,
        description="Description of the identified risk",
    )
    risk_category: str = Field(
        default="",
        description="Category of risk (e.g., safety, fundamental rights)",
    )
    likelihood: str = Field(
        default="medium",
        description="Likelihood of risk (low, medium, high)",
    )
    severity: str = Field(
        default="medium",
        description="Severity of impact (low, medium, high)",
    )
    affected_stakeholders: list[str] = Field(
        default_factory=list,
        description="Stakeholders affected by this risk",
    )
    mitigation_measures: list[str] = Field(
        default_factory=list,
        description="Measures to mitigate the risk",
    )
    residual_risk: str = Field(
        default="",
        description="Description of residual risk after mitigation",
    )
    accepted_by: Optional[str] = Field(
        default=None,
        description="Person who accepted the residual risk",
    )
    review_date: Optional[datetime] = Field(
        default=None,
        description="Next scheduled review date",
    )


class DataGovernanceRecord(ComplianceBaseModel):
    """Data governance practices (Article 10)"""

    record_id: str = Field(
        ...,
        description="Data governance record identifier",
    )
    dataset_name: str = Field(
        ...,
        description="Name of the dataset",
    )
    dataset_purpose: str = Field(
        default="",
        description="Purpose of the dataset (training, validation, testing)",
    )
    data_collection_method: str = Field(
        default="",
        description="How data was collected",
    )
    data_quality_measures: list[str] = Field(
        default_factory=list,
        description="Data quality measures applied",
    )
    bias_detection_methods: list[str] = Field(
        default_factory=list,
        description="Methods used to detect and address bias",
    )
    bias_findings: list[str] = Field(
        default_factory=list,
        description="Bias findings and remediation actions",
    )
    data_gaps_identified: list[str] = Field(
        default_factory=list,
        description="Identified gaps in training data",
    )
    personal_data_processing: bool = Field(
        default=False,
        description="Whether personal data is processed",
    )
    gdpr_compliance_reference: Optional[str] = Field(
        default=None,
        description="Reference to GDPR compliance documentation",
    )


class TechnicalDocumentation(VersionedDocument):
    """Technical documentation requirements (Article 11, Annex IV)"""

    documentation_id: str = Field(
        ...,
        description="Technical documentation identifier",
    )
    system_description: AISystemDescription = Field(
        ...,
        description="Detailed system description",
    )
    provider_info: ProviderInformation = Field(
        ...,
        description="Provider information",
    )
    risk_assessment: RiskAssessmentResult = Field(
        ...,
        description="Risk classification result",
    )
    design_specifications: str = Field(
        default="",
        description="Design specifications and architecture",
    )
    development_process: str = Field(
        default="",
        description="Description of development process",
    )
    validation_testing: str = Field(
        default="",
        description="Validation and testing procedures",
    )
    performance_metrics: dict = Field(
        default_factory=dict,
        description="Performance metrics and benchmarks",
    )
    accuracy_metrics: dict = Field(
        default_factory=dict,
        description="Accuracy and robustness metrics",
    )
    risk_management_records: list[RiskManagementRecord] = Field(
        default_factory=list,
        description="Risk management records",
    )
    data_governance_records: list[DataGovernanceRecord] = Field(
        default_factory=list,
        description="Data governance records",
    )
    human_oversight_measures: list[str] = Field(
        default_factory=list,
        description="Human oversight measures (Article 14)",
    )
    cybersecurity_measures: list[str] = Field(
        default_factory=list,
        description="Cybersecurity measures (Article 15)",
    )
    instructions_for_use: str = Field(
        default="",
        description="Instructions for use",
    )
    change_log: list[str] = Field(
        default_factory=list,
        description="Log of substantial modifications",
    )


class ConformityAssessment(ComplianceBaseModel):
    """Conformity assessment documentation (Article 43)"""

    assessment_id: str = Field(
        ...,
        description="Conformity assessment identifier",
    )
    system_id: str = Field(
        ...,
        description="AI system being assessed",
    )
    assessment_type: ConformityAssessmentType = Field(
        ...,
        description="Type of conformity assessment",
    )
    notified_body: Optional[str] = Field(
        default=None,
        description="Notified body if applicable",
    )
    assessment_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date of assessment",
    )
    assessment_result: str = Field(
        default="pending",
        description="Result of assessment (pending, passed, failed)",
    )
    requirements_checked: list[str] = Field(
        default_factory=list,
        description="Requirements verified during assessment",
    )
    nonconformities: list[str] = Field(
        default_factory=list,
        description="Nonconformities identified",
    )
    corrective_actions: list[str] = Field(
        default_factory=list,
        description="Corrective actions required",
    )
    certificate_number: Optional[str] = Field(
        default=None,
        description="Certificate number if issued",
    )
    certificate_expiry: Optional[datetime] = Field(
        default=None,
        description="Certificate expiry date",
    )
    eu_declaration_reference: Optional[str] = Field(
        default=None,
        description="Reference to EU declaration of conformity",
    )


class EUDeclarationOfConformity(ComplianceBaseModel):
    """EU Declaration of Conformity (Article 47)"""

    declaration_id: str = Field(
        ...,
        description="Declaration identifier",
    )
    system_id: str = Field(
        ...,
        description="AI system covered",
    )
    system_name: str = Field(
        ...,
        description="Name of the AI system",
    )
    provider_info: ProviderInformation = Field(
        ...,
        description="Provider information",
    )
    declaration_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date of declaration",
    )
    applicable_legislation: list[str] = Field(
        default_factory=list,
        description="Applicable EU legislation",
    )
    harmonised_standards: list[str] = Field(
        default_factory=list,
        description="Harmonised standards applied",
    )
    conformity_assessment_reference: str = Field(
        default="",
        description="Reference to conformity assessment",
    )
    notified_body_number: Optional[str] = Field(
        default=None,
        description="Notified body number if applicable",
    )
    signatory_name: str = Field(
        default="",
        description="Name of signatory",
    )
    signatory_position: str = Field(
        default="",
        description="Position of signatory",
    )
    ce_marking_applied: bool = Field(
        default=False,
        description="Whether CE marking has been applied",
    )


class EUAIActReportData(VersionedDocument):
    """Complete data model for EU AI Act compliance report"""

    report_id: str = Field(
        ...,
        description="Unique report identifier",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    organization_role: ProviderRole = Field(
        ...,
        description="Role in the AI value chain",
    )
    reporting_period_start: datetime = Field(
        ...,
        description="Start of reporting period",
    )
    reporting_period_end: datetime = Field(
        ...,
        description="End of reporting period",
    )
    ai_systems: list[AISystemDescription] = Field(
        default_factory=list,
        description="AI systems covered in this report",
    )
    risk_assessments: list[RiskAssessmentResult] = Field(
        default_factory=list,
        description="Risk assessments for each system",
    )
    technical_documentation: list[TechnicalDocumentation] = Field(
        default_factory=list,
        description="Technical documentation for high-risk systems",
    )
    conformity_assessments: list[ConformityAssessment] = Field(
        default_factory=list,
        description="Conformity assessments performed",
    )
    declarations_of_conformity: list[EUDeclarationOfConformity] = Field(
        default_factory=list,
        description="EU Declarations of Conformity",
    )
    qms: Optional[QualityManagementSystem] = Field(
        default=None,
        description="Quality management system details",
    )
    transparency_obligations_met: list[TransparencyObligation] = Field(
        default_factory=list,
        description="Transparency obligations satisfied",
    )
    high_risk_systems_count: int = Field(
        default=0,
        ge=0,
        description="Number of high-risk AI systems",
    )
    limited_risk_systems_count: int = Field(
        default=0,
        ge=0,
        description="Number of limited-risk AI systems",
    )
    minimal_risk_systems_count: int = Field(
        default=0,
        ge=0,
        description="Number of minimal-risk AI systems",
    )


class EUAIActExportRequest(ComplianceBaseModel):
    """Request model for EU AI Act report export"""

    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    organization_role: ProviderRole = Field(
        ...,
        description="Role in the AI value chain",
    )
    reporting_period_start: datetime = Field(
        ...,
        description="Start of reporting period",
    )
    reporting_period_end: datetime = Field(
        ...,
        description="End of reporting period",
    )
    include_risk_assessments: bool = Field(
        default=True,
        description="Include risk assessments",
    )
    include_technical_documentation: bool = Field(
        default=True,
        description="Include technical documentation",
    )
    include_conformity_assessments: bool = Field(
        default=True,
        description="Include conformity assessments",
    )
    include_qms_details: bool = Field(
        default=True,
        description="Include QMS details",
    )
    ai_system_ids: list[str] = Field(
        default_factory=list,
        description="Specific AI systems to include (empty = all)",
    )
