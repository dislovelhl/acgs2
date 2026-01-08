"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Policy Playground - FastAPI Application

Provides a web-based API for policy validation, evaluation, and example policies.
Integrates with OPA for Rego policy testing and experimentation.

Usage:
    cd src/core/playground
    uvicorn app:app --reload --port 8080

API Endpoints:
    POST /api/validate - Validate Rego policy syntax
    POST /api/evaluate - Evaluate policy with test input
    GET /api/examples - Get example policies
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Import OPA service from CLI module (reuse existing implementation)
try:
    from cli.opa_service import (
        OPAConnectionError,
        OPAService,
        PolicyEvaluationResult,
        PolicyValidationResult,
    )
except ImportError:
    # Handle import when running from playground directory
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from cli.opa_service import (
        OPAConnectionError,
        OPAService,
        PolicyEvaluationResult,
        PolicyValidationResult,
    )

# Import example policies
try:
    from playground.examples import (
        example_to_dict,
        get_example_by_id,
        get_example_categories,
        get_example_policies,
    )
except ImportError:
    from .examples import (
        example_to_dict,
        get_example_by_id,
        get_example_categories,
        get_example_policies,
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
PLAYGROUND_PORT = int(os.getenv("PLAYGROUND_PORT", "8080"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Global OPA service instance
opa_service: Optional[OPAService] = None


# Pydantic models for request/response
class ValidateRequest(BaseModel):
    """Request body for policy validation."""

    policy: str = Field(..., description="Rego policy content to validate")


class ValidateResponse(BaseModel):
    """Response body for policy validation."""

    valid: bool = Field(..., description="Whether the policy is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")


class EvaluateRequest(BaseModel):
    """Request body for policy evaluation."""

    policy: str = Field(..., description="Rego policy content to evaluate")
    input: Dict[str, Any] = Field(default_factory=dict, description="Input data for evaluation")
    path: Optional[str] = Field(
        default=None,
        description="Policy path to query (e.g., 'playground.rbac'). "
        "If not provided, queries all data.",
    )


class EvaluateResponse(BaseModel):
    """Response body for policy evaluation."""

    success: bool = Field(..., description="Whether evaluation succeeded")
    result: Optional[Any] = Field(default=None, description="Evaluation result")
    allowed: Optional[bool] = Field(default=None, description="Allow decision if present")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ExampleSummary(BaseModel):
    """Summary of an example policy."""

    id: str
    name: str
    description: str
    category: str
    difficulty: str
    tags: List[str]


class ExampleDetail(BaseModel):
    """Full details of an example policy."""

    id: str
    name: str
    description: str
    category: str
    policy: str
    test_input: Dict[str, Any]
    expected_result: Dict[str, Any]
    explanation: str
    difficulty: str
    tags: List[str]


class HealthResponse(BaseModel):
    """Response body for health check."""

    status: str
    service: str
    opa_status: Optional[str] = None
    opa_url: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initialize and cleanup OPA client."""
    global opa_service

    # Startup
    logger.info("Starting Policy Playground API")
    logger.info(f"OPA URL: {OPA_URL}")

    opa_service = OPAService(opa_url=OPA_URL, timeout=10.0)
    await opa_service._ensure_async_client()

    # Check OPA connectivity
    health = await opa_service.async_health_check()
    if health.get("status") == "healthy":
        logger.info("Connected to OPA server")
    else:
        logger.warning(f"OPA server not available: {health}")

    logger.info("Policy Playground API started")

    yield

    # Shutdown
    logger.info("Shutting down Policy Playground API")

    if opa_service:
        await opa_service.aclose()

    logger.info("Policy Playground API stopped")


# Create FastAPI app
app = FastAPI(
    title="Policy Playground API",
    description="Interactive API for testing and learning Rego policies with OPA integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
# Intentionally permissive for playground (unauthenticated trial access)
cors_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
]

# Allow all origins in development/debug mode
if DEBUG:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# API Endpoints


@app.post("/api/validate", response_model=ValidateResponse)
async def validate_policy(request: ValidateRequest) -> ValidateResponse:
    """
    Validate Rego policy syntax.

    Checks the policy for syntax errors without deploying it to OPA.
    Returns detailed error messages with line/column positions.
    """
    if not opa_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPA service not initialized",
        )

    try:
        result: PolicyValidationResult = await opa_service.async_validate_policy(request.policy)

        return ValidateResponse(
            valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
        )

    except OPAConnectionError as e:
        logger.warning(f"OPA connection error during validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OPA server unavailable: {e.reason}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during policy validation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        ) from e


@app.post("/api/evaluate", response_model=EvaluateResponse)
async def evaluate_policy(request: EvaluateRequest) -> EvaluateResponse:
    """
    Evaluate policy with test input.

    Temporarily loads the policy into OPA, evaluates it against the provided
    input data, and returns the result.
    """
    if not opa_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPA service not initialized",
        )

    try:
        # Determine policy path from package declaration if not provided
        policy_path = request.path or "data"

        # If path is provided as package name, convert to data path
        if policy_path and not policy_path.startswith("data"):
            policy_path = f"data.{policy_path.replace('.', '/')}"

        result: PolicyEvaluationResult = await opa_service.async_evaluate_policy(
            policy_content=request.policy,
            input_data=request.input,
            policy_path=policy_path,
        )

        return EvaluateResponse(
            success=result.success,
            result=result.result,
            allowed=result.allowed,
            error=result.reason if not result.success else None,
        )

    except OPAConnectionError as e:
        logger.warning(f"OPA connection error during evaluation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OPA server unavailable: {e.reason}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during policy evaluation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        ) from e


@app.get("/api/examples", response_model=List[ExampleDetail])
async def get_examples(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get example policies.

    Returns pre-built example policies for learning Rego. Examples can be
    filtered by category, difficulty level, or tag.
    """
    try:
        # Start with all examples
        examples = get_example_policies()

        # Apply filters
        if category:
            categories = get_example_categories()
            examples = categories.get(category, [])

        if difficulty:
            examples = [ex for ex in examples if ex.difficulty == difficulty]

        if tag:
            examples = [ex for ex in examples if tag in ex.tags]

        # Convert to dicts for JSON serialization
        return [example_to_dict(ex) for ex in examples]

    except Exception as e:
        logger.exception("Error fetching examples")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch examples: {str(e)}",
        ) from e


@app.get("/api/examples/{example_id}", response_model=ExampleDetail)
async def get_example_by_id_endpoint(example_id: str) -> Dict[str, Any]:
    """
    Get a specific example policy by ID.

    Returns the full example including policy code, test input, and explanation.
    """
    example = get_example_by_id(example_id)

    if not example:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Example not found: {example_id}",
        )

    return example_to_dict(example)


@app.get("/api/examples/categories/list")
async def list_categories() -> Dict[str, List[ExampleSummary]]:
    """
    Get examples grouped by category.

    Returns a dictionary mapping category names to lists of example summaries.
    """
    categories = get_example_categories()

    return {
        cat: [
            {
                "id": ex.id,
                "name": ex.name,
                "description": ex.description,
                "category": ex.category,
                "difficulty": ex.difficulty,
                "tags": ex.tags,
            }
            for ex in examples
        ]
        for cat, examples in categories.items()
    }


# Health check endpoints


@app.get("/health/live", response_model=HealthResponse)
async def liveness_check() -> HealthResponse:
    """Kubernetes liveness probe."""
    return HealthResponse(status="alive", service="policy-playground")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Kubernetes readiness probe."""
    if not opa_service:
        return HealthResponse(
            status="not_ready",
            service="policy-playground",
            opa_status="not_initialized",
        )

    health = await opa_service.async_health_check()

    return HealthResponse(
        status="ready" if health.get("status") == "healthy" else "degraded",
        service="policy-playground",
        opa_status=health.get("status"),
        opa_url=health.get("opa_url"),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """General health check endpoint."""
    return await readiness_check()


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "service": "Policy Playground API",
        "version": "1.0.0",
        "description": "Interactive API for testing and learning Rego policies",
        "endpoints": {
            "validate": "POST /api/validate",
            "evaluate": "POST /api/evaluate",
            "examples": "GET /api/examples",
            "health": "GET /health",
        },
        "playground": "/playground",
    }


# Exception handlers


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if DEBUG else "An unexpected error occurred",
        },
    )


# Mount static files for frontend (if exists)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/playground", StaticFiles(directory=frontend_path, html=True), name="playground")
    logger.info(f"Mounted frontend from {frontend_path}")

# Export for uvicorn
__all__ = ["app"]
