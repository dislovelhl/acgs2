"""
Policy Check API endpoints for CI/CD pipeline integration.

Provides policy validation endpoints that can be called by CI/CD pipelines
(GitHub Actions, GitLab CI) to validate resources against governance policies.
"""

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import UserClaims, get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/policy", tags=["Policy Validation"])

# OPA URL from environment
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")


# Enums
class ResourceType(str, Enum):
    """Types of resources that can be validated."""

    CODE = "code"
    KUBERNETES = "kubernetes"
    TERRAFORM = "terraform"
    DOCKER = "docker"
    CONFIG = "config"
    SCRIPT = "script"
    UNKNOWN = "unknown"


class ViolationSeverity(str, Enum):
    """Severity levels for policy violations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Request Models
class ResourceInfo(BaseModel):
    """Information about a resource to validate."""

    path: str = Field(..., description="Path to the resource file")
    type: Optional[str] = Field(None, description="Resource type (code, kubernetes, etc.)")
    content: Optional[str] = Field(None, description="Resource content (optional)")
    files: Optional[List[str]] = Field(None, description="List of files if this is a directory")

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class CIContext(BaseModel):
    """Context information from CI/CD pipeline."""

    # GitHub Actions context
    github_repository: Optional[str] = Field(None, description="GitHub repository")
    github_ref: Optional[str] = Field(None, description="GitHub ref")
    github_sha: Optional[str] = Field(None, description="GitHub commit SHA")
    github_actor: Optional[str] = Field(None, description="GitHub actor")
    github_event_name: Optional[str] = Field(None, description="GitHub event name")
    github_run_id: Optional[str] = Field(None, description="GitHub run ID")
    github_run_number: Optional[str] = Field(None, description="GitHub run number")

    # GitLab CI context
    gitlab_project: Optional[str] = Field(None, description="GitLab project path")
    gitlab_ref: Optional[str] = Field(None, description="GitLab ref")
    gitlab_sha: Optional[str] = Field(None, description="GitLab commit SHA")
    gitlab_pipeline_id: Optional[str] = Field(None, description="GitLab pipeline ID")
    gitlab_job_id: Optional[str] = Field(None, description="GitLab job ID")
    gitlab_user: Optional[str] = Field(None, description="GitLab user")
    gitlab_mr_iid: Optional[str] = Field(None, description="GitLab MR IID")
    ci_platform: Optional[str] = Field(None, description="CI platform name")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="allow",
    )


class PolicyValidationRequest(BaseModel):
    """Request model for policy validation."""

    resources: List[ResourceInfo] = Field(..., description="Resources to validate", min_length=1)
    resource_type: Optional[str] = Field(None, description="Overall resource type for validation")
    policy_id: Optional[str] = Field(None, description="Specific policy ID to validate against")
    context: Optional[CIContext] = Field(None, description="CI/CD context information")
    strict_mode: bool = Field(default=False, description="Fail on any validation error")
    include_recommendations: bool = Field(
        default=True, description="Include recommendations in response"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @field_validator("resource_type", mode="before")
    @classmethod
    def normalize_resource_type(cls, v: Optional[str]) -> Optional[str]:
        """Normalize resource type to lowercase."""
        if v is not None:
            return v.lower()
        return v


# Response Models
class PolicyViolation(BaseModel):
    """A single policy violation."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Violation ID")
    severity: ViolationSeverity = Field(
        default=ViolationSeverity.INFO, description="Violation severity"
    )
    policy_id: Optional[str] = Field(None, description="Policy ID that was violated")
    policy_name: Optional[str] = Field(None, description="Human-readable policy name")
    rule_id: Optional[str] = Field(None, description="Specific rule ID")
    message: str = Field(..., description="Violation message")
    description: Optional[str] = Field(None, description="Detailed description")
    file: Optional[str] = Field(None, description="File path where violation occurred")
    resource_path: Optional[str] = Field(None, description="Resource path")
    line: Optional[int] = Field(None, description="Line number")
    column: Optional[int] = Field(None, description="Column number")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional violation details")
    remediation: Optional[str] = Field(None, description="How to fix the violation")

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class ValidationSummary(BaseModel):
    """Summary of validation results."""

    total_resources: int = Field(..., description="Total resources validated")
    total_violations: int = Field(..., description="Total violations found")
    critical_count: int = Field(default=0, description="Critical severity count")
    high_count: int = Field(default=0, description="High severity count")
    medium_count: int = Field(default=0, description="Medium severity count")
    low_count: int = Field(default=0, description="Low severity count")
    info_count: int = Field(default=0, description="Info severity count")
    policies_evaluated: int = Field(default=0, description="Number of policies evaluated")
    validation_time_ms: int = Field(default=0, description="Validation time in milliseconds")


class PolicyValidationResponse(BaseModel):
    """Response model for policy validation."""

    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Request ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp",
    )
    passed: bool = Field(..., description="Whether validation passed")
    violations: List[PolicyViolation] = Field(
        default_factory=list, description="List of violations"
    )
    summary: ValidationSummary = Field(..., description="Validation summary")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )
    dry_run: bool = Field(default=False, description="Whether this was a dry run")
    opa_available: bool = Field(
        default=True, description="Whether OPA was available for validation"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class PolicyInfo(BaseModel):
    """Information about an available policy."""

    id: str = Field(..., description="Policy ID")
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    version: Optional[str] = Field(None, description="Policy version")
    resource_types: List[str] = Field(default_factory=list, description="Applicable resource types")
    severity: ViolationSeverity = Field(
        default=ViolationSeverity.MEDIUM, description="Default severity"
    )
    enabled: bool = Field(default=True, description="Whether policy is enabled")


class PoliciesListResponse(BaseModel):
    """Response model for listing policies."""

    policies: List[PolicyInfo] = Field(..., description="Available policies")
    total: int = Field(..., description="Total number of policies")


# Built-in demo policies for testing when OPA is unavailable
DEMO_POLICIES = [
    PolicyInfo(
        id="acgs2-security-001",
        name="No hardcoded secrets",
        description="Ensures no hardcoded secrets in code",
        version="1.0.0",
        resource_types=["code", "config"],
        severity=ViolationSeverity.CRITICAL,
    ),
    PolicyInfo(
        id="acgs2-security-002",
        name="Require HTTPS",
        description="Ensures all external URLs use HTTPS",
        version="1.0.0",
        resource_types=["code", "config", "kubernetes"],
        severity=ViolationSeverity.HIGH,
    ),
    PolicyInfo(
        id="acgs2-k8s-001",
        name="No privileged containers",
        description="Ensures Kubernetes pods do not run as privileged",
        version="1.0.0",
        resource_types=["kubernetes"],
        severity=ViolationSeverity.HIGH,
    ),
    PolicyInfo(
        id="acgs2-k8s-002",
        name="Resource limits required",
        description="Ensures Kubernetes containers have resource limits",
        version="1.0.0",
        resource_types=["kubernetes"],
        severity=ViolationSeverity.MEDIUM,
    ),
    PolicyInfo(
        id="acgs2-terraform-001",
        name="Encryption at rest",
        description="Ensures storage resources have encryption enabled",
        version="1.0.0",
        resource_types=["terraform"],
        severity=ViolationSeverity.HIGH,
    ),
    PolicyInfo(
        id="acgs2-docker-001",
        name="No latest tag",
        description="Ensures Docker images use specific version tags",
        version="1.0.0",
        resource_types=["docker"],
        severity=ViolationSeverity.MEDIUM,
    ),
]


async def check_opa_health() -> bool:
    """Check if OPA is available and healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OPA_URL}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"OPA health check failed: {e}")
        return False


async def evaluate_policies_with_opa(
    resources: List[ResourceInfo],
    resource_type: Optional[str],
    policy_id: Optional[str],
    context: Optional[CIContext],
) -> tuple[bool, List[PolicyViolation]]:
    """
    Evaluate policies using OPA.

    Returns:
        Tuple of (opa_available, violations)
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build OPA input
            input_data = {
                "resources": [r.model_dump() for r in resources],
                "resource_type": resource_type,
                "policy_id": policy_id,
                "context": context.model_dump() if context else {},
            }

            # Query OPA for policy evaluation
            # The path depends on how policies are organized in OPA
            opa_path = "/v1/data/acgs2/policy/validate"
            if policy_id:
                # Query specific policy
                opa_path = f"/v1/data/acgs2/policies/{policy_id}/validate"

            response = await client.post(
                f"{OPA_URL}{opa_path}",
                json={"input": input_data},
            )

            if response.status_code == 200:
                result = response.json()
                opa_result = result.get("result", {})

                # Parse OPA response into violations
                violations = []
                for v in opa_result.get("violations", []):
                    violations.append(
                        PolicyViolation(
                            severity=ViolationSeverity(v.get("severity", "info")),
                            policy_id=v.get("policy_id"),
                            policy_name=v.get("policy_name"),
                            rule_id=v.get("rule_id"),
                            message=v.get("message", "Policy violation"),
                            description=v.get("description"),
                            file=v.get("file"),
                            resource_path=v.get("resource_path"),
                            line=v.get("line"),
                            column=v.get("column"),
                            details=v.get("details"),
                            remediation=v.get("remediation"),
                        )
                    )

                return True, violations
            elif response.status_code == 404:
                # Policy or path not found - OPA is available but no policies loaded
                logger.info(f"OPA path not found: {opa_path}")
                return True, []
            else:
                logger.warning(f"OPA returned status {response.status_code}")
                return False, []

    except httpx.TimeoutException:
        logger.warning("OPA request timed out")
        return False, []
    except httpx.ConnectError:
        logger.warning("Could not connect to OPA")
        return False, []
    except Exception as e:
        logger.exception(f"Error querying OPA: {e}")
        return False, []


def run_builtin_checks(
    resources: List[ResourceInfo],
    resource_type: Optional[str],
) -> List[PolicyViolation]:
    """
    Run built-in policy checks when OPA is unavailable.

    These are simple pattern-based checks for demonstration purposes.
    """
    violations = []

    for resource in resources:
        content = resource.content or ""
        file_path = resource.path
        res_type = resource.type or resource_type or "unknown"

        # Check for hardcoded secrets (simple pattern matching)
        secret_patterns = [
            ("password", "Potential hardcoded password found"),
            ("secret_key", "Potential hardcoded secret key found"),
            ("api_key", "Potential hardcoded API key found"),
            ("AWS_SECRET", "Potential AWS secret found"),
            ("private_key", "Potential private key found"),
        ]

        for pattern, message in secret_patterns:
            if pattern.lower() in content.lower():
                # Check if it looks like an assignment (not just a variable reference)
                lines = content.lower().split("\n")
                for line_num, line in enumerate(lines, 1):
                    if pattern.lower() in line and "=" in line:
                        violations.append(
                            PolicyViolation(
                                severity=ViolationSeverity.HIGH,
                                policy_id="acgs2-security-001",
                                policy_name="No hardcoded secrets",
                                message=message,
                                description=(
                                    "Hardcoded secrets should be moved to "
                                    "environment variables or a secrets manager"
                                ),
                                file=file_path,
                                line=line_num,
                                remediation="Use environment variables or secrets manager",
                            )
                        )
                        break

        # Check for HTTP URLs (should use HTTPS)
        if "http://" in content and "localhost" not in content and "127.0.0.1" not in content:
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                if "http://" in line and "localhost" not in line and "127.0.0.1" not in line:
                    violations.append(
                        PolicyViolation(
                            severity=ViolationSeverity.MEDIUM,
                            policy_id="acgs2-security-002",
                            policy_name="Require HTTPS",
                            message="HTTP URL found, should use HTTPS",
                            description="External URLs should use HTTPS for security",
                            file=file_path,
                            line=line_num,
                            remediation="Change http:// to https://",
                        )
                    )
                    break

        # Kubernetes-specific checks
        if res_type == "kubernetes" or file_path.endswith((".yaml", ".yml")):
            # Check for privileged containers
            if "privileged: true" in content:
                violations.append(
                    PolicyViolation(
                        severity=ViolationSeverity.HIGH,
                        policy_id="acgs2-k8s-001",
                        policy_name="No privileged containers",
                        message="Privileged container detected",
                        description="Running containers as privileged is a security risk",
                        file=file_path,
                        remediation="Set privileged: false or remove the setting",
                    )
                )

            # Check for missing resource limits
            if "containers:" in content and "resources:" not in content:
                violations.append(
                    PolicyViolation(
                        severity=ViolationSeverity.MEDIUM,
                        policy_id="acgs2-k8s-002",
                        policy_name="Resource limits required",
                        message="Container missing resource limits",
                        description="Containers should have CPU and memory limits defined",
                        file=file_path,
                        remediation="Add resources.limits section to container spec",
                    )
                )

        # Docker-specific checks
        if res_type == "docker" or "dockerfile" in file_path.lower():
            # Check for latest tag
            if ":latest" in content or (
                "FROM " in content
                and ":latest" not in content
                and ":" not in content.split("FROM ")[1].split()[0]
                if "FROM " in content
                else False
            ):
                violations.append(
                    PolicyViolation(
                        severity=ViolationSeverity.MEDIUM,
                        policy_id="acgs2-docker-001",
                        policy_name="No latest tag",
                        message="Docker image using 'latest' tag or no tag",
                        description="Using 'latest' tag or no tag makes builds non-reproducible",
                        file=file_path,
                        remediation="Use a specific version tag for Docker images",
                    )
                )

    return violations


def build_summary(
    resources: List[ResourceInfo],
    violations: List[PolicyViolation],
    validation_time_ms: int,
    policies_evaluated: int,
) -> ValidationSummary:
    """Build validation summary from violations."""
    severity_counts = {
        ViolationSeverity.CRITICAL: 0,
        ViolationSeverity.HIGH: 0,
        ViolationSeverity.MEDIUM: 0,
        ViolationSeverity.LOW: 0,
        ViolationSeverity.INFO: 0,
    }

    for v in violations:
        severity_counts[v.severity] += 1

    return ValidationSummary(
        total_resources=len(resources),
        total_violations=len(violations),
        critical_count=severity_counts[ViolationSeverity.CRITICAL],
        high_count=severity_counts[ViolationSeverity.HIGH],
        medium_count=severity_counts[ViolationSeverity.MEDIUM],
        low_count=severity_counts[ViolationSeverity.LOW],
        info_count=severity_counts[ViolationSeverity.INFO],
        policies_evaluated=policies_evaluated,
        validation_time_ms=validation_time_ms,
    )


def generate_recommendations(
    violations: List[PolicyViolation],
    opa_available: bool,
) -> List[str]:
    """Generate recommendations based on violations."""
    recommendations = []

    if not opa_available:
        recommendations.append(
            "Connect to a running OPA instance for comprehensive policy validation"
        )

    if not violations:
        return recommendations

    # Group by severity
    critical_high = [
        v for v in violations if v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.HIGH)
    ]

    if len(critical_high) > 5:
        recommendations.append(
            f"Address the {len(critical_high)} critical/high severity issues as a priority"
        )

    # Check for patterns
    secret_violations = [v for v in violations if v.policy_id == "acgs2-security-001"]
    if secret_violations:
        recommendations.append(
            "Consider using a secrets management solution (HashiCorp Vault, AWS Secrets Manager)"
        )

    k8s_violations = [v for v in violations if v.policy_id and v.policy_id.startswith("acgs2-k8s")]
    if k8s_violations:
        recommendations.append(
            "Review Kubernetes security best practices and Pod Security Standards"
        )

    return recommendations


# API Endpoints
@router.post(
    "/validate",
    response_model=PolicyValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate resources against policies",
    description="Validate resources against governance policies for CI/CD integration",
)
async def validate_policies(
    request: PolicyValidationRequest,
    current_user: UserClaims = Depends(get_current_user),
) -> PolicyValidationResponse:
    """
    Validate resources against ACGS2 governance policies.

    This endpoint is designed to be called by CI/CD pipelines (GitHub Actions,
    GitLab CI) to validate resources before deployment.

    Returns a list of policy violations with severity levels, file locations,
    and remediation suggestions.
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Log the validation request
        ci_platform = "unknown"
        if request.context:
            if request.context.github_repository:
                ci_platform = "github"
            elif request.context.gitlab_project:
                ci_platform = "gitlab"
            elif request.context.ci_platform:
                ci_platform = request.context.ci_platform

        logger.info(
            f"Policy validation request: {len(request.resources)} resources, "
            f"type={request.resource_type}, policy={request.policy_id}, platform={ci_platform}, "
            f"user={current_user.sub}, tenant={current_user.tenant_id}"
        )

        # Try to evaluate with OPA first
        opa_available, opa_violations = await evaluate_policies_with_opa(
            resources=request.resources,
            resource_type=request.resource_type,
            policy_id=request.policy_id,
            context=request.context,
        )

        # If OPA is not available or returned no results, run built-in checks
        if not opa_available or (opa_available and not opa_violations and not request.policy_id):
            builtin_violations = run_builtin_checks(
                resources=request.resources,
                resource_type=request.resource_type,
            )
            violations = (
                opa_violations + builtin_violations if opa_available else builtin_violations
            )
        else:
            violations = opa_violations

        # Calculate validation time
        end_time = datetime.now(timezone.utc)
        validation_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Build summary
        summary = build_summary(
            resources=request.resources,
            violations=violations,
            validation_time_ms=validation_time_ms,
            policies_evaluated=len(DEMO_POLICIES) if not opa_available else 0,
        )

        # Determine if validation passed
        # By default, fail on critical or high severity violations
        passed = not any(
            v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.HIGH) for v in violations
        )

        # In strict mode, fail on any violation
        if request.strict_mode and violations:
            passed = False

        # Generate recommendations
        recommendations = []
        if request.include_recommendations:
            recommendations = generate_recommendations(violations, opa_available)

        response = PolicyValidationResponse(
            passed=passed,
            violations=violations,
            summary=summary,
            recommendations=recommendations,
            dry_run=not opa_available,
            opa_available=opa_available,
        )

        logger.info(
            f"Policy validation complete: passed={passed}, "
            f"violations={len(violations)}, time={validation_time_ms}ms, "
            f"user={current_user.sub}, tenant={current_user.tenant_id}"
        )

        return response

    except Exception as e:
        logger.exception(f"Error during policy validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy validation failed: {str(e)}",
        ) from None


@router.get(
    "/policies",
    response_model=PoliciesListResponse,
    summary="List available policies",
    description="List all available governance policies",
)
async def list_policies(
    resource_type: Optional[str] = None,
    enabled_only: bool = True,
    current_user: UserClaims = Depends(get_current_user),
) -> PoliciesListResponse:
    """
    List available governance policies.

    Optionally filter by resource type and enabled status.
    """
    # Log the request with user/tenant context for audit trail
    logger.info(
        f"List policies request: resource_type={resource_type}, enabled_only={enabled_only}, "
        f"user={current_user.sub}, tenant={current_user.tenant_id}"
    )

    # Check if OPA is available
    opa_available = await check_opa_health()

    if opa_available:
        try:
            # Try to get policies from OPA
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{OPA_URL}/v1/data/acgs2/policies")
                if response.status_code == 200:
                    result = response.json()
                    opa_policies = result.get("result", {})

                    policies = []
                    for policy_id, policy_data in opa_policies.items():
                        if isinstance(policy_data, dict):
                            policies.append(
                                PolicyInfo(
                                    id=policy_id,
                                    name=policy_data.get("name", policy_id),
                                    description=policy_data.get("description"),
                                    version=policy_data.get("version"),
                                    resource_types=policy_data.get("resource_types", []),
                                    severity=ViolationSeverity(
                                        policy_data.get("severity", "medium")
                                    ),
                                    enabled=policy_data.get("enabled", True),
                                )
                            )

                    # Filter by resource type
                    if resource_type:
                        policies = [p for p in policies if resource_type in p.resource_types]

                    # Filter by enabled status
                    if enabled_only:
                        policies = [p for p in policies if p.enabled]

                    logger.info(
                        f"List policies complete: returned {len(policies)} policies from OPA, "
                        f"user={current_user.sub}, tenant={current_user.tenant_id}"
                    )

                    return PoliciesListResponse(policies=policies, total=len(policies))
        except Exception as e:
            logger.warning(f"Failed to get policies from OPA: {e}")

    # Return demo policies if OPA is unavailable
    policies = list(DEMO_POLICIES)

    # Filter by resource type
    if resource_type:
        policies = [p for p in policies if resource_type in p.resource_types]

    # Filter by enabled status
    if enabled_only:
        policies = [p for p in policies if p.enabled]

    logger.info(
        f"List policies complete: returned {len(policies)} policies, "
        f"user={current_user.sub}, tenant={current_user.tenant_id}"
    )

    return PoliciesListResponse(policies=policies, total=len(policies))


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyInfo,
    summary="Get policy details",
    description="Get details of a specific policy",
)
async def get_policy(policy_id: str) -> PolicyInfo:
    """Get details of a specific policy."""
    # Check demo policies first
    for policy in DEMO_POLICIES:
        if policy.id == policy_id:
            return policy

    # Check OPA if available
    opa_available = await check_opa_health()
    if opa_available:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{OPA_URL}/v1/data/acgs2/policies/{policy_id}")
                if response.status_code == 200:
                    result = response.json()
                    policy_data = result.get("result", {})

                    if policy_data:
                        return PolicyInfo(
                            id=policy_id,
                            name=policy_data.get("name", policy_id),
                            description=policy_data.get("description"),
                            version=policy_data.get("version"),
                            resource_types=policy_data.get("resource_types", []),
                            severity=ViolationSeverity(policy_data.get("severity", "medium")),
                            enabled=policy_data.get("enabled", True),
                        )
        except Exception as e:
            logger.warning(f"Failed to get policy from OPA: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Policy not found: {policy_id}",
    )


@router.get(
    "/health",
    summary="Policy validation health check",
    description="Check if policy validation is available",
)
async def policy_health() -> Dict[str, Any]:
    """Check policy validation health status."""
    opa_available = await check_opa_health()

    return {
        "status": "healthy",
        "opa_available": opa_available,
        "opa_url": OPA_URL,
        "builtin_policies": len(DEMO_POLICIES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
