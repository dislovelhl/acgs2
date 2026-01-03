"""
ACGS-2 Tenant Onboarding Wizard Models
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive models for guided tenant onboarding and setup.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class OnboardingStep(str, Enum):
    """Onboarding wizard steps."""

    WELCOME = "welcome"
    ORGANIZATION_SETUP = "organization_setup"
    COMPLIANCE_CONFIGURATION = "compliance_configuration"
    SECURITY_SETUP = "security_setup"
    POLICY_INITIALIZATION = "policy_initialization"
    USER_INVITATION = "user_invitation"
    INTEGRATION_SETUP = "integration_setup"
    TESTING_VALIDATION = "testing_validation"
    COMPLETION = "completion"


class OnboardingStatus(str, Enum):
    """Onboarding session status."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class OrganizationType(str, Enum):
    """Types of organizations."""

    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    FINANCIAL = "financial"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    NON_PROFIT = "non_profit"
    STARTUP = "startup"
    OTHER = "other"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    SOC2 = "SOC2"
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI-DSS"
    EU_AI_ACT = "EU_AI_ACT"
    NIST_RMF = "NIST_RMF"
    CCPA = "CCCPA"


class SecurityLevel(str, Enum):
    """Security configuration levels."""

    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"


class WizardStep(BaseModel):
    """Individual wizard step configuration."""

    step: OnboardingStep
    title: str
    description: str
    required: bool = True
    completed: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)
    validation_errors: List[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 5

    def mark_completed(self, data: Optional[Dict[str, Any]] = None):
        """Mark step as completed."""
        self.completed = True
        if data:
            self.data.update(data)
        self.validation_errors = []

    def mark_failed(self, errors: List[str]):
        """Mark step as failed with validation errors."""
        self.completed = False
        self.validation_errors = errors


class OnboardingSession(BaseModel):
    """Tenant onboarding session."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None
    created_by: str  # User ID who started onboarding
    status: OnboardingStatus = OnboardingStatus.IN_PROGRESS

    # Progress tracking
    current_step: OnboardingStep = OnboardingStep.WELCOME
    steps: List[WizardStep] = Field(default_factory=list)
    completed_steps: List[OnboardingStep] = Field(default_factory=list)

    # Metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    # Session data
    session_data: Dict[str, Any] = Field(default_factory=dict)

    # Progress metrics
    total_steps: int = 9
    estimated_completion_time_minutes: int = 45

    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.steps:
            self._initialize_steps()

    def _initialize_steps(self):
        """Initialize all onboarding steps."""
        self.steps = [
            WizardStep(
                step=OnboardingStep.WELCOME,
                title="Welcome to ACGS-2",
                description="Get started with your enterprise AI governance platform",
                required=True,
                estimated_duration_minutes=2,
            ),
            WizardStep(
                step=OnboardingStep.ORGANIZATION_SETUP,
                title="Organization Setup",
                description="Configure your organization details and preferences",
                required=True,
                estimated_duration_minutes=5,
            ),
            WizardStep(
                step=OnboardingStep.COMPLIANCE_CONFIGURATION,
                title="Compliance Configuration",
                description="Set up compliance frameworks and requirements",
                required=True,
                estimated_duration_minutes=8,
            ),
            WizardStep(
                step=OnboardingStep.SECURITY_SETUP,
                title="Security Configuration",
                description="Configure security policies and access controls",
                required=True,
                estimated_duration_minutes=6,
            ),
            WizardStep(
                step=OnboardingStep.POLICY_INITIALIZATION,
                title="Policy Initialization",
                description="Create your first governance policies",
                required=True,
                estimated_duration_minutes=10,
            ),
            WizardStep(
                step=OnboardingStep.USER_INVITATION,
                title="User Management",
                description="Invite team members and set up roles",
                required=True,
                estimated_duration_minutes=5,
            ),
            WizardStep(
                step=OnboardingStep.INTEGRATION_SETUP,
                title="Integration Setup",
                description="Configure integrations and API access",
                required=False,
                estimated_duration_minutes=7,
            ),
            WizardStep(
                step=OnboardingStep.TESTING_VALIDATION,
                title="Testing & Validation",
                description="Validate your setup and run initial tests",
                required=True,
                estimated_duration_minutes=5,
            ),
            WizardStep(
                step=OnboardingStep.COMPLETION,
                title="Setup Complete",
                description="Your ACGS-2 platform is ready to use",
                required=True,
                estimated_duration_minutes=2,
            ),
        ]

    def get_current_step(self) -> WizardStep:
        """Get the current step."""
        for step in self.steps:
            if step.step == self.current_step:
                return step
        raise ValueError(f"Current step {self.current_step} not found")

    def advance_step(self, step_data: Optional[Dict[str, Any]] = None) -> bool:
        """Advance to the next step."""
        current_step_obj = self.get_current_step()
        current_step_obj.mark_completed(step_data)

        if current_step_obj.step not in self.completed_steps:
            self.completed_steps.append(current_step_obj.step)

        # Find next step
        current_index = next(
            (i for i, s in enumerate(self.steps) if s.step == self.current_step), -1
        )

        if current_index < len(self.steps) - 1:
            self.current_step = self.steps[current_index + 1].step
            self.last_activity = datetime.utcnow()
            return True
        else:
            # All steps completed
            self.status = OnboardingStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            return False

    def go_to_step(self, step: OnboardingStep) -> bool:
        """Go to a specific step."""
        if step not in [s.step for s in self.steps]:
            return False

        self.current_step = step
        self.last_activity = datetime.utcnow()
        return True

    def get_progress_percentage(self) -> float:
        """Get completion percentage."""
        if not self.steps:
            return 0.0

        completed_count = sum(1 for step in self.steps if step.completed)
        return (completed_count / len(self.steps)) * 100

    def get_estimated_time_remaining(self) -> int:
        """Get estimated minutes remaining."""
        remaining_steps = [s for s in self.steps if not s.completed]
        return sum(s.estimated_duration_minutes for s in remaining_steps)

    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if session has expired."""
        return (datetime.utcnow() - self.last_activity).total_seconds() > (timeout_hours * 3600)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "created_by": self.created_by,
            "status": self.status.value,
            "current_step": self.current_step.value,
            "completed_steps": [s.value for s in self.completed_steps],
            "progress_percentage": self.get_progress_percentage(),
            "estimated_time_remaining": self.get_estimated_time_remaining(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_activity": self.last_activity.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


# Step-specific request/response models


class OrganizationSetupRequest(BaseModel):
    """Organization setup request."""

    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None

    organization_type: OrganizationType
    industry: str
    organization_size: str = Field(description="e.g., '1-10', '11-50', '51-200', etc.")

    contact_email: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None

    data_residency: Optional[str] = Field(
        default=None, description="Region code for data residency"
    )

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class ComplianceConfigurationRequest(BaseModel):
    """Compliance configuration request."""

    selected_frameworks: List[ComplianceFramework] = Field(min_items=1)
    primary_framework: ComplianceFramework

    # Framework-specific settings
    data_processing_agreement: bool = False
    international_data_transfers: bool = False
    privacy_officer_designated: bool = False

    # Custom compliance requirements
    additional_requirements: List[str] = Field(default_factory=list)

    # Risk assessment
    risk_tolerance: str = Field(default="medium", description="low, medium, high")


class SecuritySetupRequest(BaseModel):
    """Security setup request."""

    security_level: SecurityLevel = SecurityLevel.STANDARD

    # Authentication settings
    mfa_required: bool = True
    password_policy: Dict[str, Any] = Field(default_factory=dict)

    # Access control
    default_user_role: str = "viewer"
    admin_approval_required: bool = True

    # Audit settings
    audit_retention_days: int = Field(default=365, ge=30, le=2555)
    real_time_monitoring: bool = True

    # Encryption settings
    encrypt_data_at_rest: bool = True
    encrypt_data_in_transit: bool = True


class PolicyInitializationRequest(BaseModel):
    """Policy initialization request."""

    # Template selection
    use_templates: bool = True
    selected_templates: List[str] = Field(default_factory=list)

    # Custom policies
    custom_policies: List[Dict[str, Any]] = Field(default_factory=list)

    # Policy settings
    auto_approval_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    human_review_required: bool = True

    # Categories to enable
    enable_content_moderation: bool = True
    enable_bias_detection: bool = True
    enable_factual_accuracy: bool = True
    enable_safety_checks: bool = True


class UserInvitationRequest(BaseModel):
    """User invitation request."""

    invitations: List[Dict[str, Any]] = Field(min_items=1)

    # Invitation settings
    invitation_expiry_days: int = Field(default=7, ge=1, le=30)
    welcome_email_template: str = "default"

    # Role assignments
    default_role: str = "viewer"
    admin_users: List[str] = Field(default_factory=list)


class IntegrationSetupRequest(BaseModel):
    """Integration setup request."""

    # API access
    enable_api_access: bool = True
    api_rate_limits: Dict[str, int] = Field(default_factory=dict)

    # Webhooks
    webhook_endpoints: List[str] = Field(default_factory=list)

    # External integrations
    enable_slack: bool = False
    enable_teams: bool = False
    enable_jira: bool = False

    # SIEM integration
    enable_siem_export: bool = True
    siem_provider: Optional[str] = None  # "splunk", "datadog", "elasticsearch"


class TestingValidationRequest(BaseModel):
    """Testing validation request."""

    run_basic_tests: bool = True
    run_integration_tests: bool = False
    run_load_tests: bool = False

    # Validation checks
    validate_compliance: bool = True
    validate_security: bool = True
    validate_performance: bool = True

    # Test configuration
    test_duration_minutes: int = Field(default=5, ge=1, le=60)


class OnboardingValidationResult(BaseModel):
    """Result of onboarding validation."""

    step: OnboardingStep
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class OnboardingCompletionSummary(BaseModel):
    """Summary of completed onboarding."""

    tenant_id: str
    tenant_name: str
    setup_duration_minutes: int
    resources_created: Dict[str, int] = Field(default_factory=dict)
    integrations_configured: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    support_resources: List[str] = Field(default_factory=list)

    completion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    constitutional_hash: str = Field(default="cdd01ef066bc6cf2", alias="constitutionalHash")
