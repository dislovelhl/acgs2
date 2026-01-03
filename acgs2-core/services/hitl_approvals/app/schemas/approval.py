"""Constitutional Hash: cdd01ef066bc6cf2
Pydantic schemas for approval requests and chains
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ApprovalStepBase(BaseModel):
    order: int
    role: str
    description: Optional[str] = None
    timeout_minutes: int
    required_approvals: int = 1
    can_escalate: bool = True
    escalation_role: Optional[str] = None


class ApprovalStepCreate(ApprovalStepBase):
    pass


class ApprovalStepSchema(ApprovalStepBase):
    id: UUID

    class Config:
        from_attributes = True


class ApprovalChainBase(BaseModel):
    name: str
    description: Optional[str] = None
    priority: str
    max_escalation_level: int = 3
    emergency_override_role: Optional[str] = None


class ApprovalChainCreate(ApprovalChainBase):
    steps: List[ApprovalStepCreate]


class ApprovalChainSchema(ApprovalChainBase):
    id: UUID
    steps: List[ApprovalStepSchema]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalDecisionBase(BaseModel):
    approver_id: str
    decision: str
    rationale: Optional[str] = None


class ApprovalDecisionCreate(ApprovalDecisionBase):
    step_id: UUID


class ApprovalDecisionSchema(ApprovalDecisionBase):
    id: UUID
    request_id: UUID
    step_id: UUID
    timestamp: datetime

    class Config:
        from_attributes = True


class ApprovalRequestBase(BaseModel):
    decision_id: str
    tenant_id: str
    requested_by: str
    title: str
    description: Optional[str] = None
    priority: str
    context: Dict[str, Any]


class ApprovalRequestCreate(ApprovalRequestBase):
    chain_id: Optional[UUID] = None


class ApprovalRequestSchema(ApprovalRequestBase):
    id: UUID
    chain_id: UUID
    status: str
    current_step_index: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    approvals: List[ApprovalDecisionSchema] = []

    class Config:
        from_attributes = True


class AuditLogSchema(BaseModel):
    id: UUID
    request_id: UUID
    action: str
    actor_id: Optional[str] = None
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True
