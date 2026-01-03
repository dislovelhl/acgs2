"""Constitutional Hash: cdd01ef066bc6cf2
SQLAlchemy models for approval requests and audit trail
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ApprovalRequest(Base):
    """Model for an approval request instance"""

    __tablename__ = "approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_id = Column(UUID(as_uuid=True), ForeignKey("approval_chains.id"), nullable=False)
    decision_id = Column(
        String, nullable=False, index=True
    )  # Reference to the original AI decision
    tenant_id = Column(String, nullable=False, index=True)
    requested_by = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    priority = Column(String, nullable=False)  # low, standard, high, critical
    context = Column(JSON, nullable=False)  # AI decision context
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, approved, rejected, escalated, timed_out, cancelled
    current_step_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)

    # Relationships
    chain = relationship("ApprovalChain", back_populates="requests")
    approvals = relationship(
        "ApprovalDecision", back_populates="request", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "ApprovalAuditLog", back_populates="request", cascade="all, delete-orphan"
    )


class ApprovalDecision(Base):
    """Model for an individual approval/rejection decision"""

    __tablename__ = "approval_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id"), nullable=False)
    approver_id = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # approved, rejected
    rationale = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    request = relationship("ApprovalRequest", back_populates="approvals")


class ApprovalAuditLog(Base):
    """Model for approval audit trail"""

    __tablename__ = "approval_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False)
    action = Column(
        String, nullable=False
    )  # created, approved, rejected, escalated, timeout, cancelled
    actor_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    context = Column(JSON)  # Additional details about the action
    ip_address = Column(String)

    # Relationships
    request = relationship("ApprovalRequest", back_populates="audit_logs")
