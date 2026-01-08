"""
ACGS-2 Enhanced Agent Bus - Graph-based Workflows (LangGraph Pattern)
Constitutional Hash: cdd01ef066bc6cf2

Implements stateful cyclic graphs for multi-agent governance orchestration.
Features conditional branching, state persistence, and human-in-the-loop interrupts.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    TypeVar,
)

from .workflow_base import CONSTITUTIONAL_HASH, WorkflowContext

logger = logging.getLogger(__name__)

TState = TypeVar("TState", bound=Dict[str, Any])


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GraphNode:
    """A node in the state graph representing an agent or a function."""

    name: str
    func: Callable[[TState], Awaitable[TState]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge in the state graph."""

    source: str
    target: str
    condition: Optional[Callable[[TState], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateGraph:
    """
    LangGraph-style state machine for multi-agent orchestration.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, state_schema: Any):
        self.state_schema = state_schema
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.entry_point: Optional[str] = None
        self.finish_point: Optional[str] = "END"

        # State persistence and checkpointing
        self._checkpoints: List[TState] = []
        self._interrupts: Set[str] = set()  # Node names where to interrupt

    def add_node(self, name: str, func: Callable[[TState], Awaitable[TState]]) -> "StateGraph":
        """Add a node to the graph."""
        self.nodes[name] = GraphNode(name=name, func=func)
        return self

    def add_edge(
        self, source: str, target: str, condition: Optional[Callable[[TState], bool]] = None
    ) -> "StateGraph":
        """Add an edge between nodes."""
        if source not in self.nodes and source != "START":
            raise ValueError(f"Source node {source} not found")
        if target not in self.nodes and target != "END":
            raise ValueError(f"Target node {target} not found")

        self.edges.append(GraphEdge(source=source, target=target, condition=condition))
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        """Set the starting node of the graph."""
        if name not in self.nodes:
            raise ValueError(f"Node {name} not found")
        self.entry_point = name
        return self

    def add_interrupt(self, node_name: str) -> "StateGraph":
        """Add an interrupt point for Human-in-the-Loop."""
        self._interrupts.add(node_name)
        return self

    async def execute(
        self, initial_state: TState, context: Optional[WorkflowContext] = None
    ) -> TState:
        """
        Execute the state graph.

        Args:
            initial_state: The starting state
            context: Optional workflow context

        Returns:
            The final state
        """
        if not self.entry_point:
            raise ValueError("Entry point not set")

        current_node = self.entry_point
        state = initial_state
        self._checkpoints.append(state.copy())

        logger.info(f"[{CONSTITUTIONAL_HASH}] Starting graph execution from {current_node}")

        while current_node != "END":
            # 1. Check for interrupts (Human-in-the-Loop)
            if current_node in self._interrupts:
                logger.info(f"[{CONSTITUTIONAL_HASH}] Interrupting execution at {current_node}")
                # In a real implementation, we would wait for a signal here
                if context:
                    await context.wait_for_signal(f"resume_{current_node}")

            # 2. Execute node
            node = self.nodes[current_node]

            try:
                state = await node.func(state)
                self._checkpoints.append(state.copy())
            except Exception as e:
                logger.error(f"[{CONSTITUTIONAL_HASH}] Node {current_node} failed: {e}")
                raise e

            # 3. Determine next node
            next_node = self._get_next_node(current_node, state)
            if not next_node:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] No valid edge from {current_node}, terminating."
                )
                break

            current_node = next_node

        logger.info(f"[{CONSTITUTIONAL_HASH}] Graph execution completed")
        return state

    def _get_next_node(self, current_node: str, state: TState) -> Optional[str]:
        """Determine the next node based on edges and current state."""
        possible_edges = [e for e in self.edges if e.source == current_node]

        for edge in possible_edges:
            if edge.condition is None or edge.condition(state):
                return edge.target

        return None

    def get_history(self) -> List[TState]:
        """Get the history of state checkpoints."""
        return self._checkpoints


class GovernanceGraph(StateGraph):
    """
    Specialized graph for multi-agent governance.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self):
        super().__init__(state_schema={})
        self._build_standard_governance_graph()

    def _build_standard_governance_graph(self):
        """Build a standard governance workflow graph."""
        # Nodes
        self.add_node("classify", self._classify_node)
        self.add_node("validate", self._validate_node)
        self.add_node("deliberate", self._deliberate_node)
        self.add_node("execute", self._execute_node)
        self.add_node("audit", self._audit_node)

        # Edges
        self.set_entry_point("classify")

        self.add_edge("classify", "execute", condition=lambda s: s.get("complexity") == "simple")
        self.add_edge(
            "classify", "validate", condition=lambda s: s.get("complexity") == "requires_validation"
        )
        self.add_edge(
            "classify", "deliberate", condition=lambda s: s.get("complexity") == "complex"
        )

        self.add_edge("validate", "deliberate")
        self.add_edge("deliberate", "execute")
        self.add_edge("execute", "audit")
        self.add_edge("audit", "END")

    async def _classify_node(self, state: TState) -> TState:
        # Mock classification logic
        content = state.get("content", "")
        if "critical" in content:
            state["complexity"] = "complex"
        elif "validate" in content:
            state["complexity"] = "requires_validation"
        else:
            state["complexity"] = "simple"
        return state

    async def _validate_node(self, state: TState) -> TState:
        state["validated"] = True
        return state

    async def _deliberate_node(self, state: TState) -> TState:
        state["deliberated"] = True
        return state

    async def _execute_node(self, state: TState) -> TState:
        state["executed"] = True
        return state

    async def _audit_node(self, state: TState) -> TState:
        state["audited"] = True
        return state
