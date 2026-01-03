"""
ACGS-2 DAG Executor
Constitutional Hash: cdd01ef066bc6cf2

Directed Acyclic Graph execution engine with maximum parallelism.
Executes independent nodes concurrently using asyncio.as_completed.
"""

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from ..base.context import WorkflowContext
from ..base.step import StepCompensation

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Import for constitutional validation
try:
    from enhanced_agent_bus.exceptions import ConstitutionalHashMismatchError
except ImportError:

    class ConstitutionalHashMismatchError(Exception):
        """Constitutional hash validation failed."""

        def __init__(self, expected: str, actual: str):
            self.expected = expected
            self.actual = actual
            super().__init__(f"Constitutional hash mismatch: expected {expected}, got {actual}")


logger = logging.getLogger(__name__)


@dataclass
class DAGNode:
    """
    Represents a node in the execution DAG.

    Attributes:
        id: Unique node identifier
        name: Human-readable node name
        execute: Async function to execute
        dependencies: List of node IDs this node depends on
        compensation: Optional compensation for rollback
        timeout_seconds: Maximum execution time
        is_optional: If True, failure doesn't stop DAG execution
        cache_key: Optional key for result caching. If provided, result is cached.
    """

    id: str
    name: str
    execute: Callable[[WorkflowContext], Awaitable[Any]]
    dependencies: List[str] = field(default_factory=list)
    compensation: Optional[StepCompensation] = None
    timeout_seconds: int = 30
    is_optional: bool = False
    requires_constitutional_check: bool = True
    cache_key: Optional[str] = None

    # Runtime state
    result: Optional[Any] = field(default=None, init=False)
    error: Optional[str] = field(default=None, init=False)
    started_at: Optional[datetime] = field(default=None, init=False)
    completed_at: Optional[datetime] = field(default=None, init=False)
    execution_time_ms: float = field(default=0.0, init=False)
    priority: int = field(default=0, init=False)  # Calculated based on dependencies

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, DAGNode):
            return self.id == other.id
        return False


@dataclass
class DAGResult:
    """Result of DAG execution."""

    dag_id: str
    status: str  # "completed", "failed", "partially_completed"
    node_results: Dict[str, Any]
    nodes_completed: List[str]
    nodes_failed: List[str]
    nodes_skipped: List[str]
    execution_time_ms: float
    constitutional_hash: str = CONSTITUTIONAL_HASH
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "dag_id": self.dag_id,
            "status": self.status,
            "node_results": self.node_results,
            "nodes_completed": self.nodes_completed,
            "nodes_failed": self.nodes_failed,
            "nodes_skipped": self.nodes_skipped,
            "execution_time_ms": self.execution_time_ms,
            "constitutional_hash": self.constitutional_hash,
            "errors": self.errors,
        }


class DAGExecutor:
    """
    DAG execution engine with maximum parallelism.

    Executes workflow as a Directed Acyclic Graph, running independent
    nodes concurrently using asyncio.as_completed for optimal throughput.

    Features:
    - Topological sort for execution order
    - Maximum parallelism for independent nodes
    - Constitutional validation at node boundaries
    - Compensation support for rollback
    - Cycle detection
    - Priority scheduling (critical path optimization)
    - Result caching for idempotent nodes

    Example:
        dag = DAGExecutor("validation-dag")
        dag.add_node(DAGNode("hash_check", "Validate Hash", validate_hash, []))
        dag.add_node(DAGNode("policy_check", "Check Policy", evaluate_policy, ["hash_check"]))
        dag.add_node(DAGNode("impact_score", "Calculate Impact", calculate_impact, ["hash_check"]))
        dag.add_node(DAGNode("decision", "Make Decision", decide, ["policy_check", "impact_score"]))

        result = await dag.execute(context)
    """

    def __init__(
        self,
        dag_id: Optional[str] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
        max_parallel_nodes: int = 10,
        result_cache: Optional[Dict[str, Any]] = None,
        fail_closed: bool = True,
    ):
        """
        Initialize DAG executor.

        Args:
            dag_id: Unique DAG identifier
            constitutional_hash: Expected constitutional hash
            max_parallel_nodes: Maximum nodes to execute concurrently
            result_cache: Optional dictionary to share results across executions
            fail_closed: If True (default), constitutional hash mismatch raises error.
                        SECURITY: Should always be True in production.
        """
        self.dag_id = dag_id or str(uuid.uuid4())
        self.constitutional_hash = constitutional_hash
        self.max_parallel_nodes = max_parallel_nodes
        self._external_cache = result_cache if result_cache is not None else {}
        self._fail_closed = fail_closed

        self._nodes: Dict[str, DAGNode] = {}
        self._compensations: List[StepCompensation] = []
        self._completed: Set[str] = set()
        self._failed: Set[str] = set()
        self._skipped: Set[str] = set()
        self._results: Dict[str, Any] = {}
        self._errors: List[str] = []
        self._dependents: Dict[str, List[str]] = {}

    def _validate_constitutional_hash(self, context: WorkflowContext) -> bool:
        """
        Validate constitutional hash from context.

        SECURITY FIX (audit finding 2025-12): DAGExecutor must validate
        constitutional hash before executing nodes that require it.

        Args:
            context: Workflow context containing constitutional_hash

        Returns:
            True if valid, False if invalid (when fail_closed=False)

        Raises:
            ConstitutionalHashMismatchError: If hash mismatch and fail_closed=True
        """
        # Get hash from context or use expected
        context_hash = context.step_results.get("constitutional_hash", self.constitutional_hash)

        is_valid = context_hash == self.constitutional_hash

        if not is_valid:
            error_msg = (
                f"DAG {self.dag_id}: Constitutional hash mismatch - "
                f"expected {self.constitutional_hash}, got {context_hash}"
            )

            if self._fail_closed:
                logger.error(error_msg)
                raise ConstitutionalHashMismatchError(
                    expected=self.constitutional_hash, actual=context_hash
                )
            else:
                logger.warning(
                    f"{error_msg} - continuing (fail_closed=False) "
                    "WARNING: This should not be used in production"
                )

        return is_valid

    def add_node(self, node: DAGNode) -> "DAGExecutor":
        """
        Add a node to the DAG.

        Validates that dependencies exist and no cycles are created.

        Args:
            node: DAGNode to add

        Returns:
            Self for chaining

        Raises:
            ValueError: If dependencies don't exist or cycle detected
        """
        # Validate dependencies exist
        for dep_id in node.dependencies:
            if dep_id not in self._nodes and dep_id != node.id:
                # Dependency might be added later, just warn
                logger.debug(
                    f"DAG {self.dag_id}: Node '{node.id}' depends on '{dep_id}' (not yet added)"
                )

        self._nodes[node.id] = node

        # Check for cycles after adding
        if self._has_cycle():
            del self._nodes[node.id]
            raise ValueError(f"Adding node '{node.id}' creates a cycle in the DAG")

        return self

    def _has_cycle(self) -> bool:
        """Check if the DAG has a cycle using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def _calculate_priorities(self):
        """
        Calculate execution priority for each node based on the number of dependents.
        Nodes that unblock more downstream work get higher priority.
        """
        # Build adjacency list (reverse dependencies)
        self._dependents = {node_id: [] for node_id in self._nodes}
        for node_id, node in self._nodes.items():
            for dep_id in node.dependencies:
                if dep_id in self._dependents:
                    self._dependents[dep_id].append(node_id)

        # Calculate subtree size for each node (simplified criticality)
        # Higher number of total downstream nodes = higher priority
        memo = {}

        def count_downstream(node_id: str) -> int:
            if node_id in memo:
                return memo[node_id]

            count = 0
            for child_id in self._dependents.get(node_id, []):
                count += 1 + count_downstream(child_id)

            memo[node_id] = count
            return count

        for node_id, node in self._nodes.items():
            node.priority = count_downstream(node_id)

    def _topological_sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm.

        Returns:
            List of node IDs in execution order
        """
        # Calculate in-degrees
        in_degree: Dict[str, int] = {node_id: 0 for node_id in self._nodes}
        for node in self._nodes.values():
            for dep_id in node.dependencies:
                if dep_id in self._nodes:
                    in_degree[node.id] = in_degree.get(node.id, 0) + 1

        # Start with nodes that have no dependencies
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # Reduce in-degree of dependent nodes
            for other_id, other_node in self._nodes.items():
                if node_id in other_node.dependencies:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        return result

    def _get_ready_nodes(self) -> List[DAGNode]:
        """
        Get nodes that are ready to execute.

        Sorted by priority (critical path first).
        """
        ready = []
        for node_id, node in self._nodes.items():
            if node_id in self._completed or node_id in self._failed or node_id in self._skipped:
                continue

            # Check if all dependencies are completed
            deps_satisfied = all(
                dep_id in self._completed or dep_id in self._skipped
                for dep_id in node.dependencies
                if dep_id in self._nodes
            )

            # Check if any required dependency failed
            deps_failed = any(
                dep_id in self._failed
                for dep_id in node.dependencies
                if dep_id in self._nodes and not self._nodes[dep_id].is_optional
            )

            if deps_failed:
                self._skipped.add(node_id)
                continue

            if deps_satisfied:
                ready.append(node)

        # Sort by priority descending (smart scheduling)
        ready.sort(key=lambda n: n.priority, reverse=True)

        return ready[: self.max_parallel_nodes]

    async def execute(self, context: WorkflowContext) -> DAGResult:
        """
        Execute the DAG with maximum parallelism.

        Uses asyncio.as_completed to process nodes as they finish,
        allowing dependent nodes to start as soon as possible.

        Args:
            context: Workflow context for execution

        Returns:
            DAGResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        context.set_step_result("_dag_id", self.dag_id)

        # Calculate priorities before execution
        self._calculate_priorities()

        logger.info(f"DAG {self.dag_id}: Starting execution with {len(self._nodes)} nodes")

        try:
            while len(self._completed) + len(self._failed) + len(self._skipped) < len(self._nodes):
                # Get nodes ready for execution
                ready_nodes = self._get_ready_nodes()

                if not ready_nodes:
                    # No more nodes can run
                    break

                # Execute ready nodes in parallel
                tasks = {
                    asyncio.create_task(self._execute_node(node, context)): node
                    for node in ready_nodes
                }

                # Process as completed
                for coro in asyncio.as_completed(tasks.keys()):
                    try:
                        node_id, result, success = await coro
                        node = self._nodes[node_id]

                        if success:
                            self._completed.add(node_id)
                            self._results[node_id] = result
                            context.set_step_result(node_id, result)
                        else:
                            if node.is_optional:
                                self._skipped.add(node_id)
                            else:
                                self._failed.add(node_id)
                                self._errors.append(f"Node '{node_id}' failed: {node.error}")

                    except Exception as e:
                        # Find which node this was
                        for task, node in tasks.items():
                            if task.done() and task == coro:
                                if node.is_optional:
                                    self._skipped.add(node.id)
                                else:
                                    self._failed.add(node.id)
                                    self._errors.append(f"Node '{node.id}' exception: {e}")
                                break

        except Exception as e:
            self._errors.append(f"DAG execution error: {e}")
            logger.exception(f"DAG {self.dag_id}: Execution error: {e}")

        # Determine final status
        status = "completed"
        if self._failed:
            status = "failed" if len(self._completed) == 0 else "partially_completed"

        # Run compensations if there were failures
        if self._failed:
            await self._run_compensations(context)

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        logger.info(
            f"DAG {self.dag_id}: Execution {status} "
            f"({len(self._completed)} completed, {len(self._failed)} failed, "
            f"{len(self._skipped)} skipped, {execution_time:.2f}ms)"
        )

        return DAGResult(
            dag_id=self.dag_id,
            status=status,
            node_results=self._results.copy(),
            nodes_completed=list(self._completed),
            nodes_failed=list(self._failed),
            nodes_skipped=list(self._skipped),
            execution_time_ms=execution_time,
            constitutional_hash=self.constitutional_hash,
            errors=self._errors.copy(),
        )

    async def _execute_node(self, node: DAGNode, context: WorkflowContext) -> tuple:
        """
        Execute a single DAG node.

        SECURITY FIX (audit finding 2025-12): Now validates constitutional
        hash before executing nodes that require it.

        Returns:
            Tuple of (node_id, result, success)
        """
        node.started_at = datetime.now(timezone.utc)

        # SECURITY FIX: Validate constitutional hash BEFORE execution
        # if the node requires it (audit finding 2025-12)
        if node.requires_constitutional_check:
            try:
                self._validate_constitutional_hash(context)
                logger.debug(
                    f"DAG {self.dag_id}: Node '{node.id}' constitutional validation passed"
                )
            except ConstitutionalHashMismatchError as e:
                node.error = str(e)
                logger.error(
                    f"DAG {self.dag_id}: Node '{node.id}' failed constitutional validation"
                )
                return (node.id, None, False)

        # Check cache if key is present
        if node.cache_key and node.cache_key in self._external_cache:
            logger.info(
                f"DAG {self.dag_id}: Cache hit for node '{node.id}' (key: {node.cache_key})"
            )
            node.result = self._external_cache[node.cache_key]
            node.completed_at = datetime.now(timezone.utc)
            node.execution_time_ms = 0.0
            return (node.id, node.result, True)

        # Register compensation BEFORE execution
        if node.compensation:
            self._compensations.append(node.compensation)

        try:
            # Execute with timeout
            result = await asyncio.wait_for(node.execute(context), timeout=node.timeout_seconds)

            # Update state
            node.result = result
            node.completed_at = datetime.now(timezone.utc)
            node.execution_time_ms = (node.completed_at - node.started_at).total_seconds() * 1000

            # Cache result
            if node.cache_key:
                self._external_cache[node.cache_key] = result

            logger.debug(
                f"DAG {self.dag_id}: Node '{node.id}' completed ({node.execution_time_ms:.2f}ms)"
            )

            return (node.id, result, True)

        except asyncio.TimeoutError:
            node.error = f"Timeout after {node.timeout_seconds}s"
            logger.warning(f"DAG {self.dag_id}: Node '{node.id}' timed out")
            return (node.id, None, False)

        except Exception as e:
            node.error = str(e)
            logger.warning(f"DAG {self.dag_id}: Node '{node.id}' failed: {e}")
            return (node.id, None, False)

    async def _run_compensations(self, context: WorkflowContext) -> None:
        """Run compensations in LIFO order."""
        if not self._compensations:
            return

        logger.info(f"DAG {self.dag_id}: Running {len(self._compensations)} compensations")

        for compensation in reversed(self._compensations):
            try:
                comp_input = {
                    "dag_id": self.dag_id,
                    "compensation_name": compensation.name,
                    "context": context.step_results,
                    "idempotency_key": compensation.idempotency_key
                    or f"{self.dag_id}:{compensation.name}",
                }

                await compensation.execute(comp_input)
                logger.info(f"DAG {self.dag_id}: Compensation '{compensation.name}' completed")

            except Exception as e:
                logger.error(f"DAG {self.dag_id}: Compensation '{compensation.name}' failed: {e}")
                self._errors.append(f"Compensation '{compensation.name}' failed: {e}")

    def get_execution_order(self) -> List[str]:
        """Get the topological execution order of nodes."""
        return self._topological_sort()

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[DAGNode]:
        """Get all nodes in the DAG."""
        return list(self._nodes.values())


__all__ = [
    "DAGNode",
    "DAGExecutor",
    "DAGResult",
]
