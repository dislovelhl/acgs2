"""
ACGS-2 Component Interfaces

Abstract base classes defining the contracts that each component must implement.
These interfaces ensure compatibility with the architecture manifest specifications.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from .schemas import (
    AuditEntry,
    ContextBundle,
    CoreEnvelope,
    MemoryRecord,
    MultiStepPlan,
    ReasoningPlan,
    SafetyDecision,
    TelemetryEvent,
    ToolCallRequest,
    ToolResult,
    TrainingEvent,
    UserRequest,
    UserResponse,
)

# =============================================================================
# Base Component Interface
# =============================================================================


class ComponentInterface(ABC):
    """Base interface for all ACGS-2 components."""

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Component identifier for logging and tracing."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for monitoring."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Graceful shutdown."""
        pass


# =============================================================================
# User Interface Gateway Interface
# =============================================================================


class UserInterfaceGatewayInterface(ComponentInterface):
    """Interface for the User Interface Gateway (UIG) service."""

    @abstractmethod
    async def handle_request(
        self, request: UserRequest, session_id: Optional[str] = None
    ) -> UserResponse:
        """Handle incoming user request through full Flow A."""
        pass

    @abstractmethod
    async def validate_session(self, session_id: str) -> bool:
        """Validate session exists and is active."""
        pass

    @abstractmethod
    async def create_session(self, metadata: Dict[str, Any]) -> str:
        """Create new user session."""
        pass


# =============================================================================
# Safety Alignment System Interface
# =============================================================================


class SafetyAlignmentSystemInterface(ComponentInterface):
    """Interface for the Safety Alignment System (SAS)."""

    @abstractmethod
    async def check_request(self, envelope: CoreEnvelope) -> SafetyDecision:
        """Check if a user request is safe to process."""
        pass

    @abstractmethod
    async def check_plan(self, plan: ReasoningPlan, context: ContextBundle) -> SafetyDecision:
        """Check if a reasoning plan is safe to execute."""
        pass

    @abstractmethod
    async def check_tool_call(self, tool_request: ToolCallRequest) -> SafetyDecision:
        """Check if a tool call is safe to execute."""
        pass

    @abstractmethod
    async def get_policy_version(self) -> str:
        """Get current policy version."""
        pass

    @abstractmethod
    async def update_policy(self, new_policy: Dict[str, Any]) -> bool:
        """Update safety policy (admin operation)."""
        pass


# =============================================================================
# Distributed Memory System Interface
# =============================================================================


class DistributedMemorySystemInterface(ComponentInterface):
    """Interface for the Distributed Memory System (DMS)."""

    @abstractmethod
    async def retrieve(self, session_id: str, query: Optional[str] = None) -> ContextBundle:
        """Retrieve context bundle for session."""
        pass

    @abstractmethod
    async def write(self, record: MemoryRecord, envelope: CoreEnvelope) -> Dict[str, Any]:
        """Write memory record with provenance."""
        pass

    @abstractmethod
    async def search_facts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search long-term facts using RAG."""
        pass

    @abstractmethod
    async def get_session_history(self, session_id: str) -> List[str]:
        """Get conversation history for session."""
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> bool:
        """Clear session data (privacy operation)."""
        pass

    @abstractmethod
    async def write_checkpoint(
        self, plan_id: str, step_idx: int, data: Dict[str, Any], envelope: CoreEnvelope
    ) -> str:
        """Write orchestration checkpoint."""
        pass

    @abstractmethod
    async def read_checkpoint(self, plan_id: str, step_idx: int) -> Optional[Dict[str, Any]]:
        """Read orchestration checkpoint."""
        pass


# =============================================================================
# Tool Mediation System Interface
# =============================================================================


class ToolMediationSystemInterface(ComponentInterface):
    """Interface for the Tool Mediation System (TMS)."""

    @abstractmethod
    async def execute(self, request: ToolCallRequest, envelope: CoreEnvelope) -> ToolResult:
        """Execute tool after safety validation."""
        pass

    @abstractmethod
    async def register_tool(self, name: str, capability: str, handler: callable) -> bool:
        """Register new tool capability."""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        pass

    @abstractmethod
    async def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get execution statistics for tool."""
        pass

    @abstractmethod
    async def validate_tool_args(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Validate tool arguments."""
        pass


# =============================================================================
# Core Reasoning Engine Interface
# =============================================================================


class CoreReasoningEngineInterface(ComponentInterface):
    """Interface for the Core Reasoning Engine (CRE)."""

    @abstractmethod
    async def reason(self, envelope: CoreEnvelope, context: ContextBundle) -> Dict[str, Any]:
        """Perform reasoning and generate response."""
        pass

    @abstractmethod
    async def generate_plan(self, query: str, context: ContextBundle) -> ReasoningPlan:
        """Generate execution plan for query."""
        pass

    @abstractmethod
    async def synthesize_response(
        self, query: str, tool_results: List[ToolResult], context: ContextBundle
    ) -> str:
        """Synthesize final response from tool results."""
        pass

    @abstractmethod
    async def handle_refusal(self, decision: SafetyDecision) -> str:
        """Generate appropriate refusal message."""
        pass

    @abstractmethod
    async def get_reasoning_trace(self, request_id: str) -> List[Dict[str, Any]]:
        """Get reasoning trace for debugging."""
        pass

    @abstractmethod
    async def generate_multi_step_plan(
        self, query: str, context: ContextBundle
    ) -> Optional[MultiStepPlan]:
        """Generate multi-step execution plan for complex tasks."""
        pass

    @abstractmethod
    async def execute_multi_step_plan(
        self, plan: MultiStepPlan, envelope: CoreEnvelope
    ) -> Dict[str, Any]:
        """Execute multi-step plan with checkpointing and error handling."""
        pass


# =============================================================================
# Observability System Interface
# =============================================================================


class ObservabilitySystemInterface(ComponentInterface):
    """Interface for the Observability System (OBS)."""

    @abstractmethod
    async def emit_event(self, event: TelemetryEvent) -> None:
        """Emit telemetry event."""
        pass

    @abstractmethod
    async def get_metrics(self, component: str, time_range: Dict[str, str]) -> Dict[str, Any]:
        """Get metrics for component."""
        pass

    @abstractmethod
    async def get_traces(self, request_id: str) -> List[TelemetryEvent]:
        """Get trace for request."""
        pass

    @abstractmethod
    async def alert_on_anomaly(self, component: str, metric: str, threshold: float) -> None:
        """Trigger alert for anomalous metric."""
        pass


# =============================================================================
# Audit Ledger Interface
# =============================================================================


class AuditLedgerInterface(ComponentInterface):
    """Interface for the Audit Ledger (AUD)."""

    @abstractmethod
    async def append_entry(self, entry: AuditEntry) -> str:
        """Append audit entry."""
        pass

    @abstractmethod
    async def query_by_request(self, request_id: str) -> List[AuditEntry]:
        """Query entries by request ID."""
        pass

    @abstractmethod
    async def query_by_session(self, session_id: str) -> List[AuditEntry]:
        """Query entries by session ID."""
        pass

    @abstractmethod
    async def verify_integrity(self) -> bool:
        """Verify audit chain integrity."""
        pass

    @abstractmethod
    async def get_compliance_report(self, time_range: Dict[str, str]) -> Dict[str, Any]:
        """Generate compliance report."""
        pass


# =============================================================================
# Neural Pattern Training Interface
# =============================================================================


class NeuralPatternTrainingInterface(ComponentInterface):
    """Interface for the Neural Pattern Training (NPT) component."""

    @abstractmethod
    async def receive_training_event(self, event: TrainingEvent) -> None:
        """Receive training event for learning."""
        pass

    @abstractmethod
    async def export_dataset(
        self, filters: Dict[str, Any], limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Export curated training dataset."""
        pass

    @abstractmethod
    async def run_evaluation(
        self, dataset_filters: Dict[str, Any], evaluation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run evaluation pipeline."""
        pass

    @abstractmethod
    async def publish_pattern_update(
        self, evaluation_results: Dict[str, Any], pattern_metadata: Dict[str, Any]
    ) -> str:
        """Publish updated patterns."""
        pass


# =============================================================================
# Component Factory Protocol
# =============================================================================


class ComponentFactory(Protocol):
    """Protocol for component factories."""

    async def create_uig(self, config: Dict[str, Any]) -> UserInterfaceGatewayInterface:
        """Create UIG instance."""
        ...

    async def create_sas(self, config: Dict[str, Any]) -> SafetyAlignmentSystemInterface:
        """Create SAS instance."""
        ...

    async def create_dms(self, config: Dict[str, Any]) -> DistributedMemorySystemInterface:
        """Create DMS instance."""
        ...

    async def create_tms(self, config: Dict[str, Any]) -> ToolMediationSystemInterface:
        """Create TMS instance."""
        ...

    async def create_cre(self, config: Dict[str, Any]) -> CoreReasoningEngineInterface:
        """Create CRE instance."""
        ...

    async def create_obs(self, config: Dict[str, Any]) -> ObservabilitySystemInterface:
        """Create OBS instance."""
        ...

    async def create_aud(self, config: Dict[str, Any]) -> AuditLedgerInterface:
        """Create AUD instance."""
        ...
