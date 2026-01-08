#!/usr/bin/env python3
"""
ACGS-2 Example 02: AI Model Approval Workflow - FastAPI Service

A FastAPI service demonstrating how to build an approval workflow API
that integrates with OPA for policy-based decision making.

Usage:
    # Start OPA first:
    docker compose up -d

    # Run the API server:
    uvicorn app:app --reload --port 8000

    # Test the approval endpoint:
    curl -X POST http://localhost:8000/api/models/approve \
        -H "Content-Type: application/json" \
        -d '{"model_id": "test-model", "risk_score": 0.3}'

Environment Variables:
    OPA_URL: URL for OPA service (default: http://localhost:8181)
    ENVIRONMENT: Deployment environment (default: development)
    CORS_ORIGINS: Comma-separated list of allowed origins
        Development: Defaults to localhost origins if not set
        Production: Must be explicitly set, wildcards not allowed

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging  # noqa: I001
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from approval_models import (
    ErrorResponse,
    HealthResponse,
    ModelApprovalRequest,
    ModelApprovalResponse,
    RiskCategory,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OPA connection configuration
OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181")

# Policy paths for OPA queries
POLICY_APPROVAL = "ai/model/approval"
POLICY_RISK = "ai/model/risk"

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))


def get_cors_origins() -> list[str]:
    """
    Get CORS origins with environment-aware security defaults.

    Development: Uses localhost origins
    Production/Staging: Requires explicit CORS_ORIGINS env var, no wildcards allowed

    Returns:
        List of allowed CORS origins

    Raises:
        ValueError: If production environment uses wildcard or missing CORS_ORIGINS
    """
    cors_env_var = os.getenv("CORS_ORIGINS")

    # Development environment defaults
    if ENVIRONMENT.lower() in ("development", "dev"):
        default_origins = (
            "http://localhost:3000,http://localhost:8080,http://localhost:5173,"
            "http://127.0.0.1:3000,http://127.0.0.1:8080,http://127.0.0.1:5173"
        )
        origins_str = cors_env_var or default_origins
    else:
        # Production/Staging: require explicit configuration
        if not cors_env_var:
            raise ValueError(
                f"SECURITY ERROR: CORS_ORIGINS environment variable must be "
                f"explicitly set in {ENVIRONMENT} environment. "
                "Wildcard origins are not allowed in production."
            )
        origins_str = cors_env_var

    # Parse and validate origins
    origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

    # Production wildcard validation
    if ENVIRONMENT.lower() in ("production", "prod", "staging", "stage"):
        if "*" in origins:
            raise ValueError(
                f"SECURITY ERROR: Wildcard CORS origins not allowed in "
                f"{ENVIRONMENT} environment. This is a critical security "
                "vulnerability. Specify explicit allowed origins."
            )
        # Validate HTTPS in production
        for origin in origins:
            is_production = ENVIRONMENT.lower() in ("production", "prod")
            if is_production and not origin.startswith("https://"):
                logger.warning(
                    f"WARNING: Non-HTTPS origin '{origin}' in production "
                    "environment. This may pose security risks."
                )

    logger.info(f"CORS configured for {ENVIRONMENT}: {len(origins)} origins allowed")
    return origins


def check_opa_health() -> bool:
    """
    Verify OPA is running and healthy.

    Returns:
        True if OPA is healthy, False otherwise
    """
    try:
        response = requests.get(f"{OPA_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def query_opa(policy_path: str, input_data: dict) -> dict:
    """
    Query OPA policy with input data.

    Args:
        policy_path: The policy package path (e.g., "ai/model/approval/allowed")
        input_data: Dictionary containing the policy input

    Returns:
        Dictionary containing the policy evaluation result

    Raises:
        HTTPException: If OPA is unreachable or returns an error
    """
    url = f"{OPA_URL}/v1/data/{policy_path}"
    try:
        response = requests.post(
            url,
            json={"input": input_data},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to OPA: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPA service is unavailable. Please ensure OPA is running.",
        ) from e
    except requests.exceptions.Timeout as e:
        logger.error(f"OPA request timed out: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OPA request timed out.",
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"OPA request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OPA request failed: {str(e)}",
        ) from e


def build_opa_input(request: ModelApprovalRequest) -> dict:
    """
    Build OPA input from the approval request.

    Transforms the simplified API request into the full OPA input format
    expected by the model_approval.rego and risk_assessment.rego policies.
    """
    input_data = {
        "model": {
            "id": request.model_id,
            "name": request.model_name or request.model_id,
            "version": request.model_version,
            "type": request.model_type,
            "risk_score": request.risk_score,
        },
        "compliance": {
            "bias_tested": request.compliance.bias_tested,
            "documentation_complete": request.compliance.documentation_complete,
            "security_reviewed": request.compliance.security_reviewed,
        },
        "deployment": {
            "environment": request.deployment.environment,
            "region": request.deployment.region,
        },
    }

    # Add reviewer info if provided
    if request.reviewer:
        input_data["reviewer"] = {
            "id": request.reviewer.id,
            "approved": request.reviewer.approved,
        }

    return input_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Model Approval Service")
    logger.info(f"OPA URL: {OPA_URL}")

    if check_opa_health():
        logger.info("OPA is healthy and ready")
    else:
        logger.warning("OPA is not reachable - some endpoints may fail")

    yield

    # Shutdown
    logger.info("Shutting down AI Model Approval Service")


# Create FastAPI app
app = FastAPI(
    title="AI Model Approval API",
    description="ACGS-2 Example: Policy-based AI model approval workflow",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware with environment-aware security
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the service status and OPA connectivity.
    """
    opa_connected = check_opa_health()
    return HealthResponse(
        status="healthy" if opa_connected else "degraded",
        opa_connected=opa_connected,
        message="Service is running" if opa_connected else "OPA is not reachable",
    )


@app.post(
    "/api/models/approve",
    response_model=ModelApprovalResponse,
    responses={
        200: {"description": "Approval decision returned successfully"},
        503: {"model": ErrorResponse, "description": "OPA service unavailable"},
    },
)
async def approve_model(request: ModelApprovalRequest):
    """
    Evaluate an AI model for deployment approval.

    This endpoint queries OPA policies to determine if the model
    should be approved for deployment based on:
    - Risk score and category
    - Compliance status (bias testing, documentation, security review)
    - Target environment (staging vs production)
    - Reviewer approval (for medium/high risk models)

    Returns a detailed response with the approval decision and
    any denial reasons if applicable.
    """
    # Build OPA input from request
    opa_input = build_opa_input(request)

    # Query OPA for approval decision
    approval_result = query_opa(f"{POLICY_APPROVAL}/status", opa_input)
    status_data = approval_result.get("result", {})

    # Extract values with defaults
    approved = status_data.get("allowed", False)
    risk_category_str = status_data.get("risk_category", "unknown")
    compliance_passed = status_data.get("compliance_passed", False)
    denial_reasons = status_data.get("denial_reasons", [])

    # Handle case where denial_reasons might be null from OPA
    if denial_reasons is None:
        denial_reasons = []

    # Convert risk category string to enum
    try:
        risk_category = RiskCategory(risk_category_str)
    except ValueError:
        risk_category = RiskCategory.UNKNOWN

    # Determine if reviewer is required
    requires_reviewer = risk_category in (RiskCategory.HIGH, RiskCategory.MEDIUM) and (
        request.deployment.environment == "production"
    )

    return ModelApprovalResponse(
        model_id=request.model_id,
        approved=approved,
        risk_category=risk_category,
        compliance_passed=compliance_passed,
        requires_reviewer=requires_reviewer,
        denial_reasons=denial_reasons,
        environment=request.deployment.environment,
        evaluated_at=datetime.now(timezone.utc),
    )


@app.get("/api/models/risk-categories", response_model=dict[str, Any])
async def get_risk_categories():
    """
    Get information about risk categories and thresholds.

    This is a utility endpoint to help users understand
    the risk classification system.
    """
    return {
        "categories": [
            {"name": "low", "score_range": "0.0 - 0.3", "auto_approve": True},
            {"name": "medium", "score_range": "0.3 - 0.7", "auto_approve": "staging only"},
            {"name": "high", "score_range": "0.7 - 1.0", "auto_approve": False},
        ],
        "thresholds": {"low_max": 0.3, "high_min": 0.7},
        "requirements": {
            "all_categories": [
                "bias_tested",
                "documentation_complete",
                "security_reviewed",
            ],
            "medium_production": ["reviewer_approved"],
            "high_all_environments": ["reviewer_approved"],
        },
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unexpected errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
