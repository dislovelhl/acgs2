"""
ACGS-2 API Schemas

Additional Pydantic models and schemas for the REST API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")


class ComponentHealth(BaseModel):
    """Health status for a component."""

    component: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")


class AuditEntrySummary(BaseModel):
    """Summary of an audit entry."""

    entry_id: str = Field(..., description="Audit entry ID")
    timestamp: str = Field(..., description="Entry timestamp")
    actor: str = Field(..., description="Component that created the entry")
    action_type: str = Field(..., description="Type of action audited")
    summary: str = Field(..., description="Human-readable summary")


class TrainingDatasetInfo(BaseModel):
    """Information about a training dataset."""

    name: str = Field(..., description="Dataset name/key")
    size: int = Field(..., description="Number of samples")
    last_updated: str = Field(..., description="Last update timestamp")
    filters: Dict[str, Any] = Field(..., description="Dataset filter criteria")


class EvaluationResult(BaseModel):
    """Result of a model evaluation."""

    evaluation_id: str = Field(..., description="Unique evaluation ID")
    timestamp: str = Field(..., description="Evaluation timestamp")
    dataset_size: int = Field(..., description="Size of evaluation dataset")
    metrics: Dict[str, Any] = Field(..., description="Evaluation metrics")
    recommendations: List[str] = Field(..., description="Improvement recommendations")


class PatternVersion(BaseModel):
    """Information about a pattern version."""

    version_id: str = Field(..., description="Pattern version ID")
    timestamp: str = Field(..., description="Version creation timestamp")
    evaluation_results: Dict[str, Any] = Field(..., description="Results that led to this version")
    metadata: Dict[str, Any] = Field(..., description="Version metadata")
