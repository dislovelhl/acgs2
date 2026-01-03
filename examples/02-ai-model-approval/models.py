"""
ACGS-2 Example 02: AI Model Approval Workflow - Data Models

Pydantic models for type-safe request/response handling in the
model approval workflow API.

Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskCategory(str, Enum):
    """Risk category classification based on risk score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ComplianceStatus(BaseModel):
    """Compliance check status for AI models."""

    bias_tested: bool = Field(default=False, description="Whether bias testing has been completed")
    documentation_complete: bool = Field(
        default=False, description="Whether documentation is complete"
    )
    security_reviewed: bool = Field(
        default=False, description="Whether security review has been completed"
    )


class ReviewerInfo(BaseModel):
    """Reviewer information for model approval."""

    id: Optional[str] = Field(default=None, description="Reviewer email or identifier")
    approved: bool = Field(default=False, description="Whether the reviewer has approved")


class DeploymentInfo(BaseModel):
    """Deployment target information."""

    environment: str = Field(
        default="staging", description="Target environment (staging/production)"
    )
    region: Optional[str] = Field(default=None, description="Deployment region")


class ModelApprovalRequest(BaseModel):
    """
    Request model for AI model approval.

    This is a simplified request format for the example API.
    The full OPA policy input is constructed from these fields.
    """

    model_id: str = Field(..., min_length=1, max_length=255, description="Unique model identifier")
    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Risk score from 0.0 (low risk) to 1.0 (high risk)"
    )
    model_name: Optional[str] = Field(
        default=None, max_length=255, description="Human-readable model name"
    )
    model_version: Optional[str] = Field(default="1.0.0", description="Model version string")
    model_type: Optional[str] = Field(default="ml_model", description="Type of AI model")
    compliance: ComplianceStatus = Field(
        default_factory=ComplianceStatus, description="Compliance check status"
    )
    deployment: DeploymentInfo = Field(
        default_factory=DeploymentInfo, description="Deployment target information"
    )
    reviewer: Optional[ReviewerInfo] = Field(
        default=None, description="Reviewer information (required for high-risk models)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model_id": "gpt-classifier-v1",
                    "risk_score": 0.25,
                    "model_name": "Customer Intent Classifier",
                    "compliance": {
                        "bias_tested": True,
                        "documentation_complete": True,
                        "security_reviewed": True,
                    },
                    "deployment": {"environment": "staging"},
                },
                {
                    "model_id": "autonomous-agent-v2",
                    "risk_score": 0.85,
                    "model_name": "Autonomous Support Agent",
                    "compliance": {
                        "bias_tested": True,
                        "documentation_complete": True,
                        "security_reviewed": True,
                    },
                    "deployment": {"environment": "production"},
                    "reviewer": {"id": "alice@company.com", "approved": True},
                },
            ]
        }
    }


class ModelApprovalResponse(BaseModel):
    """
    Response model for AI model approval decision.

    Contains the approval decision along with detailed context
    about how the decision was made.
    """

    model_id: str = Field(..., description="Model identifier from the request")
    approved: bool = Field(..., description="Whether the model is approved for deployment")
    risk_category: RiskCategory = Field(..., description="Determined risk category")
    compliance_passed: bool = Field(..., description="Whether all compliance checks passed")
    requires_reviewer: bool = Field(
        default=False, description="Whether reviewer approval is required"
    )
    denial_reasons: list[str] = Field(
        default_factory=list, description="List of reasons if approval was denied"
    )
    environment: str = Field(..., description="Target deployment environment")
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of evaluation"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model_id": "gpt-classifier-v1",
                    "approved": True,
                    "risk_category": "low",
                    "compliance_passed": True,
                    "requires_reviewer": False,
                    "denial_reasons": [],
                    "environment": "staging",
                    "evaluated_at": "2026-01-02T12:00:00Z",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service health status")
    opa_connected: bool = Field(..., description="Whether OPA is reachable")
    message: Optional[str] = Field(default=None, description="Additional status message")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")
