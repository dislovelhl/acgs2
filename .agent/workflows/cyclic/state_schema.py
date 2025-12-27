"""
ACGS-2 Global State Schema
Constitutional Hash: cdd01ef066bc6cf2

Strictly typed state schema for CEOS V1.0 cyclic orchestration.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# Import centralized constitutional hash
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class StateMetadata(BaseModel):
    """Metadata for the global state."""
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    constitutional_hash: str = CONSTITUTIONAL_HASH


class GlobalState(BaseModel):
    """
    Persistent, strictly typed Global State for CEOS.
    
    This object is mutated by nodes in the state graph.
    """
    # Unique identifier for this state session
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Message history or event log
    history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Shared memory / context
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Orchestration control
    next_node: Optional[str] = None
    is_finished: bool = False
    
    # Human-in-the-Loop Interrupt
    interrupt_required: bool = False
    interrupt_message: Optional[str] = None
    
    # Metadata
    metadata: StateMetadata = Field(default_factory=StateMetadata)
    
    # Error handling
    errors: List[str] = Field(default_factory=list)

    def update_timestamp(self):
        """Update the last_updated timestamp."""
        self.metadata.last_updated = datetime.utcnow()

    def add_error(self, error: str):
        """Add an error and set interrupt if critical."""
        self.errors.append(error)
        self.update_timestamp()

    def log_event(self, node_name: str, event_data: Dict[str, Any]):
        """Log a node execution event."""
        self.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "node": node_name,
            "data": event_data
        })
        self.update_timestamp()


__all__ = ["GlobalState", "StateMetadata"]
