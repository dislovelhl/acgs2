"""
ACGS-2 Tenant Onboarding Wizard Service
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade guided tenant onboarding with step-by-step setup,
validation, and automated configuration.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ...models import Tenant, TenantTier
from ...service import TenantManagementService
from .models import (
    ComplianceConfigurationRequest,
    IntegrationSetupRequest,
    OnboardingCompletionSummary,
    OnboardingSession,
    OnboardingStatus,
    OnboardingStep,
    OnboardingValidationResult,
    OrganizationSetupRequest,
    OrganizationType,
    PolicyInitializationRequest,
    SecuritySetupRequest,
    TestingValidationRequest,
    UserInvitationRequest,
)

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TenantOnboardingWizard:
    """
    Guided tenant onboarding wizard service.

    Provides step-by-step tenant setup with validation, automated configuration,
    and comprehensive onboarding experience.
    """

    def __init__(self, tenant_service: TenantManagementService):
        self.tenant_service = tenant_service

        # Session management
        self._sessions: Dict[str, OnboardingSession] = {}
        self._session_timeout_hours = 24

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the onboarding wizard service."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._session_cleanup_loop())

        logger.info("Tenant onboarding wizard started")

    async def stop(self):
        """Stop the onboarding wizard service."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Tenant onboarding wizard stopped")

    async def create_session(self, created_by: str) -> OnboardingSession:
        """Create a new onboarding session."""
        session = OnboardingSession(created_by=created_by)
        self._sessions[session.id] = session

        logger.info(f"Created onboarding session: {session.id} for user {created_by}")
        return session

    async def get_session(self, session_id: str) -> Optional[OnboardingSession]:
        """Get an onboarding session."""
        session = self._sessions.get(session_id)
        if session and session.is_expired(self._session_timeout_hours):
            await self._cleanup_session(session_id)
            return None
        return session

    async def process_step(
        self, session_id: str, step: OnboardingStep, request_data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """
        Process a wizard step with validation and configuration.

        Args:
            session_id: The onboarding session ID
            step: The step to process
            request_data: The step data

        Returns:
            Validation result
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or expired")

        if session.status != OnboardingStatus.IN_PROGRESS:
            raise ValueError(f"Session {session_id} is not in progress")

        # Validate step sequence
        if step != session.current_step:
            return OnboardingValidationResult(
                step=step,
                valid=False,
                errors=[f"Invalid step sequence. Current step is {session.current_step.value}"],
            )

        # Process the step
        try:
            result = await self._process_step_data(session, step, request_data)
            if result.valid:
                session.advance_step(request_data)
                logger.info(f"Completed step {step.value} for session {session_id}")
            else:
                session.get_current_step().mark_failed(result.errors)
                logger.warning(f"Step {step.value} validation failed for session {session_id}")

            return result

        except Exception as e:
            logger.error(f"Error processing step {step.value}: {e}")
            return OnboardingValidationResult(
                step=step, valid=False, errors=[f"Processing error: {str(e)}"]
            )

    async def _process_step_data(
        self, session: OnboardingSession, step: OnboardingStep, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process and validate step data."""

        if step == OnboardingStep.ORGANIZATION_SETUP:
            return await self._process_organization_setup(session, data)
        elif step == OnboardingStep.COMPLIANCE_CONFIGURATION:
            return await self._process_compliance_configuration(session, data)
        elif step == OnboardingStep.SECURITY_SETUP:
            return await self._process_security_setup(session, data)
        elif step == OnboardingStep.POLICY_INITIALIZATION:
            return await self._process_policy_initialization(session, data)
        elif step == OnboardingStep.USER_INVITATION:
            return await self._process_user_invitation(session, data)
        elif step == OnboardingStep.INTEGRATION_SETUP:
            return await self._process_integration_setup(session, data)
        elif step == OnboardingStep.TESTING_VALIDATION:
            return await self._process_testing_validation(session, data)
        else:
            # Skip validation for welcome and completion steps
            return OnboardingValidationResult(step=step, valid=True)

    async def _process_organization_setup(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process organization setup step."""
        try:
            request = OrganizationSetupRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.ORGANIZATION_SETUP,
                valid=False,
                errors=[f"Invalid data: {str(e)}"],
            )

        # Validate organization details
        errors = []

        # Check for duplicate names (would need tenant service integration)
        # For now, just basic validation

        if not request.name.replace("-", "").replace("_", "").isalnum():
            errors.append(
                "Organization name must contain only alphanumeric characters, hyphens, and underscores"
            )

        # Determine tenant tier based on organization type
        tier_mapping = {
            OrganizationType.STARTUP: TenantTier.FREE,
            OrganizationType.ENTERPRISE: TenantTier.ENTERPRISE,
            OrganizationType.GOVERNMENT: TenantTier.ENTERPRISE,
            OrganizationType.FINANCIAL: TenantTier.ENTERPRISE_PLUS,
            OrganizationType.HEALTHCARE: TenantTier.ENTERPRISE_PLUS,
        }
        suggested_tier = tier_mapping.get(request.organization_type, TenantTier.PROFESSIONAL)

        if errors:
            return OnboardingValidationResult(
                step=OnboardingStep.ORGANIZATION_SETUP, valid=False, errors=errors
            )

        # Store validated data
        session.session_data["organization"] = {
            **request.model_dump(),
            "suggested_tier": suggested_tier.value,
        }

        return OnboardingValidationResult(
            step=OnboardingStep.ORGANIZATION_SETUP,
            valid=True,
            recommendations=[f"Suggested tier: {suggested_tier.value}"],
        )

    async def _process_compliance_configuration(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process compliance configuration step."""
        try:
            request = ComplianceConfigurationRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.COMPLIANCE_CONFIGURATION,
                valid=False,
                errors=[f"Invalid data: {str(e)}"],
            )

        # Validate compliance requirements
        warnings = []
        recommendations = []

        if "GDPR" in [f.value for f in request.selected_frameworks]:
            if not request.data_processing_agreement:
                warnings.append("GDPR compliance requires data processing agreements")

        if "HIPAA" in [f.value for f in request.selected_frameworks]:
            if not request.privacy_officer_designated:
                warnings.append("HIPAA compliance requires designated privacy officer")

        # Store compliance data
        session.session_data["compliance"] = request.model_dump()

        return OnboardingValidationResult(
            step=OnboardingStep.COMPLIANCE_CONFIGURATION,
            valid=True,
            warnings=warnings,
            recommendations=recommendations,
        )

    async def _process_security_setup(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process security setup step."""
        try:
            request = SecuritySetupRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.SECURITY_SETUP, valid=False, errors=[f"Invalid data: {str(e)}"]
            )

        recommendations = []

        # Validate security settings
        if request.security_level == "maximum" and not request.mfa_required:
            return OnboardingValidationResult(
                step=OnboardingStep.SECURITY_SETUP,
                valid=False,
                errors=["Maximum security level requires MFA"],
            )

        if request.audit_retention_days < 365:
            recommendations.append(
                "Consider increasing audit retention to at least 365 days for compliance"
            )

        # Store security data
        session.session_data["security"] = request.model_dump()

        return OnboardingValidationResult(
            step=OnboardingStep.SECURITY_SETUP, valid=True, recommendations=recommendations
        )

    async def _process_policy_initialization(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process policy initialization step."""
        try:
            request = PolicyInitializationRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.POLICY_INITIALIZATION,
                valid=False,
                errors=[f"Invalid data: {str(e)}"],
            )

        # Validate policy settings
        if request.auto_approval_threshold > 0.8:
            return OnboardingValidationResult(
                step=OnboardingStep.POLICY_INITIALIZATION,
                valid=False,
                errors=["Auto-approval threshold above 0.8 requires additional risk assessment"],
            )

        # Store policy data
        session.session_data["policies"] = request.model_dump()

        return OnboardingValidationResult(
            step=OnboardingStep.POLICY_INITIALIZATION,
            valid=True,
            recommendations=["Review and customize generated policies before deployment"],
        )

    async def _process_user_invitation(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process user invitation step."""
        try:
            request = UserInvitationRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.USER_INVITATION, valid=False, errors=[f"Invalid data: {str(e)}"]
            )

        # Validate invitations
        errors = []
        for i, invitation in enumerate(request.invitations):
            if not invitation.get("email") or "@" not in invitation["email"]:
                errors.append(f"Invalid email in invitation {i + 1}")

        if not request.admin_users:
            errors.append("At least one admin user must be designated")

        if errors:
            return OnboardingValidationResult(
                step=OnboardingStep.USER_INVITATION, valid=False, errors=errors
            )

        # Store invitation data
        session.session_data["users"] = request.model_dump()

        return OnboardingValidationResult(
            step=OnboardingStep.USER_INVITATION,
            valid=True,
            recommendations=["Send invitations promptly to ensure timely onboarding"],
        )

    async def _process_integration_setup(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process integration setup step."""
        try:
            request = IntegrationSetupRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.INTEGRATION_SETUP,
                valid=False,
                errors=[f"Invalid data: {str(e)}"],
            )

        # Validate integrations
        if request.enable_api_access and not request.api_rate_limits:
            request.api_rate_limits = {"default": 1000, "burst": 2000}

        # Store integration data
        session.session_data["integrations"] = request.model_dump()

        return OnboardingValidationResult(
            step=OnboardingStep.INTEGRATION_SETUP,
            valid=True,
            recommendations=["Test integrations before going to production"],
        )

    async def _process_testing_validation(
        self, session: OnboardingSession, data: Dict[str, Any]
    ) -> OnboardingValidationResult:
        """Process testing validation step."""
        try:
            request = TestingValidationRequest(**data)
        except Exception as e:
            return OnboardingValidationResult(
                step=OnboardingStep.TESTING_VALIDATION,
                valid=False,
                errors=[f"Invalid data: {str(e)}"],
            )

        # Run validation tests
        errors = []
        warnings = []

        # Basic configuration validation
        required_configs = ["organization", "compliance", "security"]
        for config in required_configs:
            if config not in session.session_data:
                errors.append(f"Missing {config} configuration")

        if errors:
            return OnboardingValidationResult(
                step=OnboardingStep.TESTING_VALIDATION, valid=False, errors=errors
            )

        # Store testing data
        session.session_data["testing"] = request.model_dump()

        return OnboardingValidationResult(
            step=OnboardingStep.TESTING_VALIDATION,
            valid=True,
            warnings=warnings,
            recommendations=["Monitor system performance after deployment"],
        )

    async def complete_onboarding(self, session_id: str) -> OnboardingCompletionSummary:
        """Complete the onboarding process and create the tenant."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status != OnboardingStatus.IN_PROGRESS:
            raise ValueError(f"Session {session_id} is not in progress")

        # Validate all required data is present
        required_data = ["organization", "compliance", "security", "policies", "users"]
        for data_key in required_data:
            if data_key not in session.session_data:
                raise ValueError(f"Missing required data: {data_key}")

        # Create the tenant
        org_data = session.session_data["organization"]
        compliance_data = session.session_data["compliance"]
        session.session_data["security"]

        # Map organization type to tier
        tier_mapping = {
            "startup": TenantTier.FREE,
            "enterprise": TenantTier.ENTERPRISE,
            "government": TenantTier.ENTERPRISE,
            "financial": TenantTier.ENTERPRISE_PLUS,
            "healthcare": TenantTier.ENTERPRISE_PLUS,
        }
        tier = tier_mapping.get(
            org_data.get("organization_type", "enterprise"), TenantTier.ENTERPRISE
        )

        try:
            # Create tenant
            tenant = await self.tenant_service.create_tenant(
                request=Tenant(
                    name=org_data["name"],
                    display_name=org_data["display_name"],
                    description=org_data.get("description"),
                    contact_email=org_data["contact_email"],
                    contact_name=org_data.get("contact_name"),
                    contact_phone=org_data.get("contact_phone"),
                    organization_name=org_data["display_name"],  # Use display name
                    organization_size=org_data["organization_size"],
                    industry=org_data["industry"],
                    tier=tier,
                    data_residency=org_data.get("data_residency"),
                    compliance_requirements=[
                        f.value for f in compliance_data["selected_frameworks"]
                    ],
                    created_by=session.created_by,
                    owned_by=session.created_by,
                ),
                created_by_user=session.created_by,
            )

            # Update session
            session.tenant_id = tenant.id
            session.status = OnboardingStatus.COMPLETED
            session.completed_at = datetime.utcnow()

            # Calculate setup duration
            setup_duration = int((session.completed_at - session.started_at).total_seconds() / 60)

            # Create completion summary
            summary = OnboardingCompletionSummary(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                setup_duration_minutes=setup_duration,
                resources_created={
                    "tenant": 1,
                    "policies": len(
                        session.session_data.get("policies", {}).get("selected_templates", [])
                    ),
                    "users": len(session.session_data.get("users", {}).get("invitations", [])),
                },
                integrations_configured=[
                    (
                        "API Access"
                        if session.session_data.get("integrations", {}).get("enable_api_access")
                        else None
                    ),
                    (
                        "SIEM Export"
                        if session.session_data.get("integrations", {}).get("enable_siem_export")
                        else None
                    ),
                ],
                next_steps=[
                    "Activate your tenant (requires admin approval)",
                    "Invite team members using the user management interface",
                    "Configure additional policies and workflows",
                    "Set up monitoring and alerting",
                    "Review compliance reports and audit logs",
                ],
                support_resources=[
                    "ACGS-2 Documentation: https://docs.acgs2.com",
                    "Community Forum: https://community.acgs2.com",
                    "Support Portal: https://support.acgs2.com",
                    "API Reference: https://api.acgs2.com",
                ],
            )

            # Clean up session
            await self._cleanup_session(session_id)

            logger.info(f"Completed onboarding for tenant: {tenant.id}")
            return summary

        except Exception as e:
            session.status = OnboardingStatus.FAILED
            logger.error(f"Failed to complete onboarding: {e}")
            raise

    async def _session_cleanup_loop(self):
        """Background task for cleaning up expired sessions."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")

    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        expired_sessions = []
        for session_id, session in self._sessions.items():
            if session.is_expired(self._session_timeout_hours):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self._cleanup_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    async def _cleanup_session(self, session_id: str):
        """Clean up a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        total_sessions = len(self._sessions)
        active_sessions = sum(
            1 for s in self._sessions.values() if s.status == OnboardingStatus.IN_PROGRESS
        )
        completed_sessions = sum(
            1 for s in self._sessions.values() if s.status == OnboardingStatus.COMPLETED
        )
        failed_sessions = sum(
            1 for s in self._sessions.values() if s.status == OnboardingStatus.FAILED
        )

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "completion_rate": (
                (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
            ),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


# Convenience functions
async def create_onboarding_session(created_by: str) -> OnboardingSession:
    """Create a new onboarding session."""
    wizard = get_onboarding_wizard()
    return await wizard.create_session(created_by)


async def process_onboarding_step(
    session_id: str, step: OnboardingStep, data: Dict[str, Any]
) -> OnboardingValidationResult:
    """Process an onboarding step."""
    wizard = get_onboarding_wizard()
    return await wizard.process_step(session_id, step, data)


async def complete_tenant_onboarding(session_id: str) -> OnboardingCompletionSummary:
    """Complete tenant onboarding."""
    wizard = get_onboarding_wizard()
    return await wizard.complete_onboarding(session_id)


# Global instance
_onboarding_wizard: Optional[TenantOnboardingWizard] = None


def get_onboarding_wizard() -> TenantOnboardingWizard:
    """Get the global onboarding wizard instance."""
    global _onboarding_wizard
    if _onboarding_wizard is None:
        # This would need to be properly initialized with tenant service
        # For now, return None to indicate not configured
        raise RuntimeError(
            "Onboarding wizard not initialized. Call initialize_onboarding_wizard() first."
        )
    return _onboarding_wizard


def initialize_onboarding_wizard(tenant_service: TenantManagementService) -> TenantOnboardingWizard:
    """Initialize the global onboarding wizard."""
    global _onboarding_wizard
    _onboarding_wizard = TenantOnboardingWizard(tenant_service)
    return _onboarding_wizard


__all__ = [
    "CONSTITUTIONAL_HASH",
    "TenantOnboardingWizard",
    "OnboardingSession",
    "OnboardingStep",
    "OnboardingStatus",
    "OnboardingValidationResult",
    "OnboardingCompletionSummary",
    "OrganizationSetupRequest",
    "ComplianceConfigurationRequest",
    "SecuritySetupRequest",
    "PolicyInitializationRequest",
    "UserInvitationRequest",
    "IntegrationSetupRequest",
    "TestingValidationRequest",
    "create_onboarding_session",
    "process_onboarding_step",
    "complete_tenant_onboarding",
    "get_onboarding_wizard",
    "initialize_onboarding_wizard",
]
