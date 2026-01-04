"""
LangGraph-Style Governance Orchestration
=========================================

Constitutional Hash: cdd01ef066bc6cf2

Implements graph-based multi-agent governance workflows with:
- Conditional branching
- State persistence
- Checkpointing
- Human-in-the-loop support

References:
- LangGraph at Scale (LinkedIn, Uber, 400+ companies)
- CrewAI (100,000+ agent executions/day)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the governance graph."""
    CLASSIFIER = "classifier"
    VALIDATOR = "validator"
    DELIBERATOR = "deliberator"
    EXECUTOR = "executor"
    AUDITOR = "auditor"
    HUMAN = "human"  # Human-in-the-loop


@dataclass
class GovernanceState:
    """
    State flowing through the governance graph.

    Follows the Memory Object Protocol - workflow execution
    is the mutation of this persistent, typed state.
    """
    request_id: str
    action: str
    context: Dict[str, Any]
    classification: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    deliberation_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None
    current_node: str = "start"
    history: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action": self.action,
            "context": self.context,
            "classification": self.classification,
            "validation_result": self.validation_result,
            "deliberation_result": self.deliberation_result,
            "execution_result": self.execution_result,
            "audit_id": self.audit_id,
            "current_node": self.current_node,
            "history": self.history,
            "errors": self.errors,
            "metadata": self.metadata,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class GraphNode:
    """A node in the governance graph."""
    name: str
    node_type: NodeType
    handler: Callable[[GovernanceState], Awaitable[GovernanceState]]

    async def execute(self, state: GovernanceState) -> GovernanceState:
        """Execute the node handler."""
        state.history.append(self.name)
        state.current_node = self.name
        return await self.handler(state)


@dataclass
class GraphEdge:
    """An edge connecting nodes in the graph."""
    source: str
    target: str
    condition: Optional[Callable[[GovernanceState], bool]] = None

    def should_traverse(self, state: GovernanceState) -> bool:
        """Check if edge should be traversed."""
        if self.condition is None:
            return True
        return self.condition(state)


@dataclass
class Checkpoint:
    """A checkpoint for state persistence."""
    checkpoint_id: str
    state: GovernanceState
    timestamp: datetime
    node: str


class StateCheckpointer:
    """
    Persists state for recovery and human-in-the-loop.

    Enables:
    - State inspection during execution
    - Hot-patching of variables
    - Resume from checkpoint
    """

    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}

    async def save(self, state: GovernanceState) -> str:
        """Save checkpoint of current state."""
        checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            state=GovernanceState(**state.to_dict()),  # Deep copy
            timestamp=datetime.utcnow(),
            node=state.current_node,
        )

        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint_id

    async def load(self, checkpoint_id: str) -> Optional[GovernanceState]:
        """Load state from checkpoint."""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint:
            return checkpoint.state
        return None

    async def list_checkpoints(
        self,
        request_id: str
    ) -> List[Checkpoint]:
        """List checkpoints for a request."""
        return [
            cp for cp in self._checkpoints.values()
            if cp.state.request_id == request_id
        ]


class GovernanceGraph:
    """
    LangGraph-style governance workflow graph.

    Implements:
    - Conditional branching based on state
    - State persistence with checkpointing
    - Human-in-the-loop interrupts
    - Error recovery
    """

    def __init__(
        self,
        checkpointer: Optional[StateCheckpointer] = None
    ):
        """
        Initialize governance graph.

        Args:
            checkpointer: Optional state checkpointer
        """
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._start_node: Optional[str] = None
        self._end_nodes: Set[str] = set()
        self._interrupt_nodes: Set[str] = set()

        self.checkpointer = checkpointer or StateCheckpointer()

        self._stats = {
            "executions": 0,
            "completed": 0,
            "interrupted": 0,
            "errors": 0,
        }

        logger.info("Initialized GovernanceGraph")

    def add_node(
        self,
        name: str,
        handler: Callable[[GovernanceState], Awaitable[GovernanceState]],
        node_type: NodeType = NodeType.EXECUTOR
    ) -> "GovernanceGraph":
        """Add a node to the graph."""
        node = GraphNode(
            name=name,
            node_type=node_type,
            handler=handler,
        )
        self._nodes[name] = node
        return self

    def add_edge(
        self,
        source: str,
        target: str
    ) -> "GovernanceGraph":
        """Add an unconditional edge."""
        edge = GraphEdge(source=source, target=target)
        self._edges.append(edge)
        return self

    def add_conditional_edges(
        self,
        source: str,
        router: Callable[[GovernanceState], str],
        routes: Dict[str, str]
    ) -> "GovernanceGraph":
        """
        Add conditional edges based on router function.

        Args:
            source: Source node
            router: Function that returns route key from state
            routes: Mapping of route keys to target nodes
        """
        for route_key, target in routes.items():
            condition = lambda state, key=route_key: router(state) == key
            edge = GraphEdge(source=source, target=target, condition=condition)
            self._edges.append(edge)
        return self

    def set_entry_point(self, node: str) -> "GovernanceGraph":
        """Set the entry point node."""
        self._start_node = node
        return self

    def set_finish(self, node: str) -> "GovernanceGraph":
        """Set a finish node."""
        self._end_nodes.add(node)
        return self

    def set_interrupt_before(self, node: str) -> "GovernanceGraph":
        """Set a node to interrupt before (for HITL)."""
        self._interrupt_nodes.add(node)
        return self

    async def invoke(
        self,
        initial_state: GovernanceState
    ) -> GovernanceState:
        """
        Execute the graph from initial state.

        Args:
            initial_state: Starting state

        Returns:
            Final state after execution
        """
        self._stats["executions"] += 1

        state = initial_state
        current_node = self._start_node

        if not current_node:
            raise ValueError("No start node defined")

        while current_node:
            # Check for interrupt
            if current_node in self._interrupt_nodes:
                self._stats["interrupted"] += 1
                await self.checkpointer.save(state)
                state.metadata["interrupted_at"] = current_node
                break

            # Execute current node
            node = self._nodes.get(current_node)
            if not node:
                raise ValueError(f"Node not found: {current_node}")

            try:
                state = await node.execute(state)
            except Exception as e:
                state.errors.append(f"{current_node}: {str(e)}")
                self._stats["errors"] += 1
                logger.error(f"Node {current_node} failed: {e}")
                break

            # Check if finished
            if current_node in self._end_nodes:
                self._stats["completed"] += 1
                break

            # Find next node
            next_node = await self._get_next_node(current_node, state)
            current_node = next_node

        return state

    async def _get_next_node(
        self,
        current: str,
        state: GovernanceState
    ) -> Optional[str]:
        """Get next node based on edges and state."""
        for edge in self._edges:
            if edge.source == current and edge.should_traverse(state):
                return edge.target
        return None

    async def resume(
        self,
        checkpoint_id: str,
        state_updates: Optional[Dict[str, Any]] = None
    ) -> GovernanceState:
        """
        Resume execution from checkpoint.

        Enables hot-patching of state variables.
        """
        state = await self.checkpointer.load(checkpoint_id)
        if not state:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        # Apply state updates (hot-patching)
        if state_updates:
            for key, value in state_updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)

        # Remove interrupt status
        interrupted_at = state.metadata.pop("interrupted_at", None)
        if interrupted_at and interrupted_at in self._interrupt_nodes:
            self._interrupt_nodes.discard(interrupted_at)

        return await self.invoke(state)

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            **self._stats,
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "interrupt_nodes": len(self._interrupt_nodes),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class GovernanceGraphBuilder:
    """
    Builder for standard governance graph patterns.

    Provides pre-built patterns for common workflows.
    """

    @staticmethod
    async def classify_request(state: GovernanceState) -> GovernanceState:
        """Classifier node handler."""
        action_lower = state.action.lower()

        if any(word in action_lower for word in ["delete", "critical", "admin"]):
            state.classification = "complex"
        elif any(word in action_lower for word in ["validate", "check", "verify"]):
            state.classification = "requires_validation"
        else:
            state.classification = "simple"

        return state

    @staticmethod
    async def validate_constitutionally(state: GovernanceState) -> GovernanceState:
        """Validator node handler."""
        # Check constitutional hash
        valid = state.constitutional_hash == CONSTITUTIONAL_HASH

        state.validation_result = {
            "valid": valid,
            "constitutional_hash_verified": valid,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return state

    @staticmethod
    async def deliberate(state: GovernanceState) -> GovernanceState:
        """Deliberator node handler."""
        # Simulate deliberation
        state.deliberation_result = {
            "decision": "approved",
            "confidence": 0.85,
            "deliberation_time_ms": 50,
        }
        return state

    @staticmethod
    async def execute_decision(state: GovernanceState) -> GovernanceState:
        """Executor node handler."""
        state.execution_result = {
            "status": "executed",
            "action": state.action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return state

    @staticmethod
    async def audit_and_anchor(state: GovernanceState) -> GovernanceState:
        """Auditor node handler."""
        state.audit_id = f"audit-{uuid.uuid4().hex[:8]}"
        return state

    @staticmethod
    def route_by_complexity(state: GovernanceState) -> str:
        """Route based on classification complexity."""
        if state.classification == "simple":
            return "simple"
        elif state.classification == "complex":
            return "complex"
        else:
            return "requires_validation"

    @classmethod
    def build_standard_graph(cls) -> GovernanceGraph:
        """
        Build standard governance graph.

        Flow:
        classifier -> (simple) -> executor -> auditor
                   -> (complex) -> deliberator -> executor -> auditor
                   -> (requires_validation) -> validator -> deliberator -> ...
        """
        graph = GovernanceGraph()

        # Add nodes
        graph.add_node("classifier", cls.classify_request, NodeType.CLASSIFIER)
        graph.add_node("validator", cls.validate_constitutionally, NodeType.VALIDATOR)
        graph.add_node("deliberator", cls.deliberate, NodeType.DELIBERATOR)
        graph.add_node("executor", cls.execute_decision, NodeType.EXECUTOR)
        graph.add_node("auditor", cls.audit_and_anchor, NodeType.AUDITOR)

        # Set entry and exit
        graph.set_entry_point("classifier")
        graph.set_finish("auditor")

        # Add conditional edges from classifier
        graph.add_conditional_edges(
            "classifier",
            cls.route_by_complexity,
            {
                "simple": "executor",
                "complex": "deliberator",
                "requires_validation": "validator",
            }
        )

        # Add remaining edges
        graph.add_edge("validator", "deliberator")
        graph.add_edge("deliberator", "executor")
        graph.add_edge("executor", "auditor")

        return graph


def create_governance_graph() -> GovernanceGraph:
    """Factory function to create standard governance graph."""
    return GovernanceGraphBuilder.build_standard_graph()
