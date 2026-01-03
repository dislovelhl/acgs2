"""
SQLAlchemy models for approval chains and steps
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ApprovalChain(Base):
    """Model for a complete approval chain definition"""

    __tablename__ = "approval_chains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    priority = Column(String, nullable=False)  # low, standard, high, critical
    max_escalation_level = Column(Integer, default=3)
    emergency_override_role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = relationship(
        "ApprovalStep",
        back_populates="chain",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.order",
    )
    requests = relationship("ApprovalRequest", back_populates="chain")


class ApprovalStep(Base):
    """Model for a single step in an approval chain"""

    __tablename__ = "approval_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_id = Column(UUID(as_uuid=True), ForeignKey("approval_chains.id"), nullable=False)
    order = Column(Integer, nullable=False)
    role = Column(String, nullable=False)
    description = Column(String)
    timeout_minutes = Column(Integer, nullable=False)
    required_approvals = Column(Integer, default=1)
    can_escalate = Column(Boolean, default=True)
    escalation_role = Column(String)

    # Relationships
    chain = relationship("ApprovalChain", back_populates="steps")
