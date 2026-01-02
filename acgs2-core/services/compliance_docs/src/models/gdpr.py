"""
GDPR Pydantic models for Compliance Documentation Service

Models for GDPR Article 30 Records of Processing Activities,
data flow documentation, and compliance evidence.

Article 30 requires documentation of:
- Processing purposes
- Categories of data subjects and personal data
- Recipients of personal data
- Transfers to third countries
- Retention periods
- Technical and organizational security measures
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ComplianceBaseModel, VersionedDocument


class EntityRole(str, Enum):
    """GDPR entity role"""

    CONTROLLER = "controller"
    PROCESSOR = "processor"
    JOINT_CONTROLLER = "joint_controller"


class LawfulBasis(str, Enum):
    """GDPR lawful basis for processing (Article 6)"""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataCategory(str, Enum):
    """Categories of personal data"""

    BASIC_IDENTITY = "basic_identity"
    CONTACT_DETAILS = "contact_details"
    FINANCIAL = "financial"
    EMPLOYMENT = "employment"
    LOCATION = "location"
    ONLINE_IDENTIFIERS = "online_identifiers"
    BIOMETRIC = "biometric"
    HEALTH = "health"
    RACIAL_ETHNIC = "racial_ethnic"
    POLITICAL_OPINIONS = "political_opinions"
    RELIGIOUS_BELIEFS = "religious_beliefs"
    TRADE_UNION = "trade_union"
    SEXUAL_ORIENTATION = "sexual_orientation"
    CRIMINAL_RECORDS = "criminal_records"
    OTHER = "other"


class DataSubjectCategory(str, Enum):
    """Categories of data subjects"""

    CUSTOMERS = "customers"
    EMPLOYEES = "employees"
    JOB_APPLICANTS = "job_applicants"
    CONTRACTORS = "contractors"
    SUPPLIERS = "suppliers"
    WEBSITE_VISITORS = "website_visitors"
    MINORS = "minors"
    PATIENTS = "patients"
    STUDENTS = "students"
    MEMBERS = "members"
    OTHER = "other"


class TransferMechanism(str, Enum):
    """Legal mechanisms for international data transfers"""

    ADEQUACY_DECISION = "adequacy_decision"
    STANDARD_CONTRACTUAL_CLAUSES = "standard_contractual_clauses"
    BINDING_CORPORATE_RULES = "binding_corporate_rules"
    DEROGATIONS = "derogations"
    CERTIFICATION = "certification"
    CODE_OF_CONDUCT = "code_of_conduct"
    NOT_APPLICABLE = "not_applicable"


class ContactDetails(ComplianceBaseModel):
    """Contact information for GDPR entities"""

    name: str = Field(
        ...,
        description="Name of the contact person or organization",
    )
    email: Optional[str] = Field(
        default=None,
        description="Email address",
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number",
    )
    address: Optional[str] = Field(
        default=None,
        description="Postal address",
    )


class DataProtectionOfficer(ContactDetails):
    """Data Protection Officer information"""

    is_required: bool = Field(
        default=False,
        description="Whether DPO appointment is mandatory",
    )
    appointment_date: Optional[datetime] = Field(
        default=None,
        description="Date DPO was appointed",
    )
    registration_reference: Optional[str] = Field(
        default=None,
        description="Supervisory authority registration reference",
    )


class DataRecipient(ComplianceBaseModel):
    """Recipient of personal data"""

    recipient_id: str = Field(
        ...,
        description="Unique identifier for this recipient",
    )
    name: str = Field(
        ...,
        description="Name of the recipient organization",
    )
    category: str = Field(
        default="",
        description="Category of recipient (e.g., service provider, authority)",
    )
    country: str = Field(
        default="",
        description="Country where recipient is located",
    )
    is_third_country: bool = Field(
        default=False,
        description="Whether recipient is in a third country (outside EEA)",
    )
    transfer_mechanism: TransferMechanism = Field(
        default=TransferMechanism.NOT_APPLICABLE,
        description="Legal mechanism for the transfer",
    )
    purpose: str = Field(
        default="",
        description="Purpose for sharing data with this recipient",
    )
    contract_reference: Optional[str] = Field(
        default=None,
        description="Reference to data processing agreement",
    )


class RetentionPolicy(ComplianceBaseModel):
    """Data retention policy"""

    data_category: DataCategory = Field(
        ...,
        description="Category of personal data",
    )
    retention_period: str = Field(
        ...,
        description="Retention period description (e.g., '7 years after contract end')",
    )
    retention_basis: str = Field(
        default="",
        description="Legal or business basis for retention",
    )
    deletion_process: str = Field(
        default="",
        description="Description of deletion/anonymization process",
    )
    review_date: Optional[datetime] = Field(
        default=None,
        description="Next scheduled review of retention policy",
    )


class SecurityMeasure(ComplianceBaseModel):
    """Technical or organizational security measure"""

    measure_id: str = Field(
        ...,
        description="Unique identifier for this measure",
    )
    category: str = Field(
        ...,
        description="Category (technical or organizational)",
    )
    name: str = Field(
        ...,
        description="Name of the security measure",
    )
    description: str = Field(
        default="",
        description="Description of the measure",
    )
    implementation_status: str = Field(
        default="implemented",
        description="Status (implemented, planned, not_implemented)",
    )
    controls_reference: list[str] = Field(
        default_factory=list,
        description="References to related controls (e.g., ISO 27001)",
    )


class ProcessingActivity(ComplianceBaseModel):
    """Individual processing activity for Article 30 records"""

    activity_id: str = Field(
        ...,
        description="Unique identifier for this processing activity",
    )
    name: str = Field(
        ...,
        description="Name of the processing activity",
    )
    description: str = Field(
        ...,
        description="Description of the processing activity",
    )
    purposes: list[str] = Field(
        ...,
        min_length=1,
        description="Purposes of the processing",
    )
    lawful_basis: list[LawfulBasis] = Field(
        ...,
        min_length=1,
        description="Lawful basis for processing",
    )
    lawful_basis_details: str = Field(
        default="",
        description="Details supporting the lawful basis",
    )
    data_categories: list[DataCategory] = Field(
        default_factory=list,
        description="Categories of personal data processed",
    )
    special_categories: bool = Field(
        default=False,
        description="Whether special category data is processed",
    )
    special_categories_basis: Optional[str] = Field(
        default=None,
        description="Legal basis for processing special categories (Article 9)",
    )
    data_subject_categories: list[DataSubjectCategory] = Field(
        default_factory=list,
        description="Categories of data subjects",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Sources of personal data",
    )
    recipients: list[DataRecipient] = Field(
        default_factory=list,
        description="Recipients of personal data",
    )
    retention_policies: list[RetentionPolicy] = Field(
        default_factory=list,
        description="Retention policies for data in this activity",
    )
    security_measures: list[SecurityMeasure] = Field(
        default_factory=list,
        description="Technical and organizational security measures",
    )
    dpia_required: bool = Field(
        default=False,
        description="Whether DPIA is required for this activity",
    )
    dpia_reference: Optional[str] = Field(
        default=None,
        description="Reference to DPIA if conducted",
    )
    automated_decision_making: bool = Field(
        default=False,
        description="Whether automated decision-making/profiling is used",
    )
    automated_decision_details: Optional[str] = Field(
        default=None,
        description="Details of automated decision-making if applicable",
    )
    system_references: list[str] = Field(
        default_factory=list,
        description="IT systems involved in this processing",
    )
    status: str = Field(
        default="active",
        description="Status of the processing activity (active, inactive, planned)",
    )
    last_review_date: Optional[datetime] = Field(
        default=None,
        description="Date of last review",
    )


class ControllerRecord(VersionedDocument):
    """Article 30(1) - Records of processing for controllers"""

    record_id: str = Field(
        ...,
        description="Unique identifier for this record",
    )
    role: EntityRole = Field(
        default=EntityRole.CONTROLLER,
        description="Entity role (always controller for this record type)",
    )
    controller_name: str = Field(
        ...,
        description="Name of the controller",
    )
    controller_contact: ContactDetails = Field(
        ...,
        description="Controller contact details",
    )
    joint_controllers: list[ContactDetails] = Field(
        default_factory=list,
        description="Joint controllers if applicable",
    )
    representative: Optional[ContactDetails] = Field(
        default=None,
        description="EU representative if controller is outside EEA",
    )
    dpo: Optional[DataProtectionOfficer] = Field(
        default=None,
        description="Data Protection Officer information",
    )
    processing_activities: list[ProcessingActivity] = Field(
        default_factory=list,
        description="All processing activities",
    )
    total_activities: int = Field(
        default=0,
        ge=0,
        description="Total number of processing activities",
    )


class ProcessorRecord(VersionedDocument):
    """Article 30(2) - Records of processing for processors"""

    record_id: str = Field(
        ...,
        description="Unique identifier for this record",
    )
    role: EntityRole = Field(
        default=EntityRole.PROCESSOR,
        description="Entity role (always processor for this record type)",
    )
    processor_name: str = Field(
        ...,
        description="Name of the processor",
    )
    processor_contact: ContactDetails = Field(
        ...,
        description="Processor contact details",
    )
    representative: Optional[ContactDetails] = Field(
        default=None,
        description="EU representative if processor is outside EEA",
    )
    dpo: Optional[DataProtectionOfficer] = Field(
        default=None,
        description="Data Protection Officer information",
    )
    controllers: list[ContactDetails] = Field(
        default_factory=list,
        description="Controllers on whose behalf processing is done",
    )
    processing_categories: list[str] = Field(
        default_factory=list,
        description="Categories of processing carried out",
    )
    sub_processors: list[DataRecipient] = Field(
        default_factory=list,
        description="Sub-processors used",
    )
    international_transfers: list[DataRecipient] = Field(
        default_factory=list,
        description="International transfers outside EEA",
    )
    security_measures: list[SecurityMeasure] = Field(
        default_factory=list,
        description="Technical and organizational security measures",
    )


class DataFlowMapping(ComplianceBaseModel):
    """Visual data flow mapping for processing activities"""

    flow_id: str = Field(
        ...,
        description="Unique identifier for this data flow",
    )
    name: str = Field(
        ...,
        description="Name of the data flow",
    )
    description: str = Field(
        default="",
        description="Description of the data flow",
    )
    processing_activity_id: str = Field(
        ...,
        description="Related processing activity",
    )
    data_source: str = Field(
        ...,
        description="Source of the data",
    )
    data_destination: str = Field(
        ...,
        description="Destination of the data",
    )
    data_categories: list[DataCategory] = Field(
        default_factory=list,
        description="Categories of data in this flow",
    )
    transfer_method: str = Field(
        default="",
        description="Method of data transfer",
    )
    encryption_in_transit: bool = Field(
        default=True,
        description="Whether data is encrypted in transit",
    )
    crosses_border: bool = Field(
        default=False,
        description="Whether flow crosses international borders",
    )


class GDPRReportData(VersionedDocument):
    """Complete data model for a GDPR compliance report"""

    report_id: str = Field(
        ...,
        description="Unique identifier for this report",
    )
    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    entity_role: EntityRole = Field(
        ...,
        description="Primary role (controller or processor)",
    )
    reporting_period_start: datetime = Field(
        ...,
        description="Start of the reporting period",
    )
    reporting_period_end: datetime = Field(
        ...,
        description="End of the reporting period",
    )
    controller_record: Optional[ControllerRecord] = Field(
        default=None,
        description="Controller Article 30(1) record",
    )
    processor_record: Optional[ProcessorRecord] = Field(
        default=None,
        description="Processor Article 30(2) record",
    )
    data_flows: list[DataFlowMapping] = Field(
        default_factory=list,
        description="Data flow mappings",
    )
    supervisory_authority: Optional[ContactDetails] = Field(
        default=None,
        description="Lead supervisory authority",
    )
    compliance_status: str = Field(
        default="in_progress",
        description="Overall compliance status",
    )


class GDPRExportRequest(ComplianceBaseModel):
    """Request model for GDPR report export"""

    organization_name: str = Field(
        ...,
        description="Name of the organization",
    )
    entity_role: EntityRole = Field(
        ...,
        description="Primary role (controller or processor)",
    )
    reporting_period_start: datetime = Field(
        ...,
        description="Start of the reporting period",
    )
    reporting_period_end: datetime = Field(
        ...,
        description="End of the reporting period",
    )
    include_controller_record: bool = Field(
        default=True,
        description="Include Article 30(1) controller record",
    )
    include_processor_record: bool = Field(
        default=False,
        description="Include Article 30(2) processor record",
    )
    include_data_flows: bool = Field(
        default=True,
        description="Include data flow mappings",
    )
    include_security_measures: bool = Field(
        default=True,
        description="Include security measures details",
    )
