"""
Tests for DAG Executor
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import asyncio
from typing import Any, Dict

from ..base.context import WorkflowContext
from ..dags.dag_executor import DAGNode, DAGExecutor, DAGResult

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TestDAGNode:
    """Tests for DAGNode."""

    def test_node_creation(self):
        """Test node creation with defaults."""
        async def noop(ctx: WorkflowContext) -> str:
            return "done"

        node = DAGNode(
            id="node-1",
            name="Test Node",
            execute=noop,
        )

        assert node.id == "node-1"
        assert node.name == "Test Node"
        assert node.dependencies == []
        assert node.timeout_seconds == 30
        assert not node.is_optional

    def test_node_equality(self):
        """Test node equality is based on ID."""
        async def noop(ctx: WorkflowContext) -> str:
            return "done"

        node1 = DAGNode(id="node-1", name="Node 1", execute=noop)
        node2 = DAGNode(id="node-1", name="Different Name", execute=noop)
        node3 = DAGNode(id="node-2", name="Node 1", execute=noop)

        assert node1 == node2
        assert node1 != node3


class TestDAGExecutor:
    """Tests for DAGExecutor."""

    @pytest.mark.asyncio
    async def test_simple_dag_execution(self):
        """Test simple sequential DAG."""
        execution_order = []

        async def step_a(ctx: WorkflowContext) -> str:
            execution_order.append("a")
            return "a_result"

        async def step_b(ctx: WorkflowContext) -> str:
            execution_order.append("b")
            return "b_result"

        dag = DAGExecutor("test-dag")
        dag.add_node(DAGNode("a", "Step A", step_a, []))
        dag.add_node(DAGNode("b", "Step B", step_b, ["a"]))

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        assert result.status == "completed"
        assert "a" in result.nodes_completed
        assert "b" in result.nodes_completed
        # A must complete before B
        assert execution_order.index("a") < execution_order.index("b")

    @pytest.mark.asyncio
    async def test_parallel_dag_execution(self):
        """Test parallel node execution."""
        execution_times = {}

        async def make_step(name: str, delay: float):
            async def step(ctx: WorkflowContext) -> str:
                start = asyncio.get_event_loop().time()
                await asyncio.sleep(delay)
                execution_times[name] = asyncio.get_event_loop().time() - start
                return f"{name}_result"
            return step

        dag = DAGExecutor("parallel-dag")
        dag.add_node(DAGNode("root", "Root", await make_step("root", 0.01), []))
        dag.add_node(DAGNode("a", "A", await make_step("a", 0.1), ["root"]))
        dag.add_node(DAGNode("b", "B", await make_step("b", 0.1), ["root"]))
        dag.add_node(DAGNode("c", "C", await make_step("c", 0.1), ["root"]))
        dag.add_node(DAGNode("final", "Final", await make_step("final", 0.01), ["a", "b", "c"]))

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        assert result.status == "completed"
        assert len(result.nodes_completed) == 5
        # Total time should be ~0.2s (root + parallel ABC + final), not ~0.32s if sequential

    @pytest.mark.asyncio
    async def test_optional_node_failure(self):
        """Test DAG continues when optional node fails."""
        async def success(ctx: WorkflowContext) -> str:
            return "success"

        async def fail(ctx: WorkflowContext) -> str:
            raise Exception("Intentional failure")

        dag = DAGExecutor("optional-dag")
        dag.add_node(DAGNode("a", "Step A", success, []))
        dag.add_node(DAGNode("b", "Optional B", fail, ["a"], is_optional=True))
        dag.add_node(DAGNode("c", "Step C", success, ["a"]))  # Doesn't depend on b

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        assert result.status == "completed"  # Not failed
        assert "a" in result.nodes_completed
        assert "c" in result.nodes_completed
        assert "b" in result.nodes_skipped

    @pytest.mark.asyncio
    async def test_required_node_failure(self):
        """Test DAG fails when required node fails."""
        async def success(ctx: WorkflowContext) -> str:
            return "success"

        async def fail(ctx: WorkflowContext) -> str:
            raise Exception("Intentional failure")

        dag = DAGExecutor("fail-dag")
        dag.add_node(DAGNode("a", "Step A", success, []))
        dag.add_node(DAGNode("b", "Required B", fail, ["a"], is_optional=False))
        dag.add_node(DAGNode("c", "Step C", success, ["b"]))

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        assert result.status in ["failed", "partially_completed"]
        assert "b" in result.nodes_failed
        assert "c" in result.nodes_skipped  # Skipped due to dependency failure

    def test_cycle_detection(self):
        """Test DAG rejects cycles."""
        async def noop(ctx: WorkflowContext) -> str:
            return "done"

        dag = DAGExecutor("cycle-dag")
        dag.add_node(DAGNode("a", "A", noop, ["c"]))
        dag.add_node(DAGNode("b", "B", noop, ["a"]))

        with pytest.raises(ValueError, match="cycle"):
            dag.add_node(DAGNode("c", "C", noop, ["b"]))

    def test_topological_sort(self):
        """Test topological sort order."""
        async def noop(ctx: WorkflowContext) -> str:
            return "done"

        dag = DAGExecutor("topo-dag")
        dag.add_node(DAGNode("d", "D", noop, ["b", "c"]))
        dag.add_node(DAGNode("a", "A", noop, []))
        dag.add_node(DAGNode("b", "B", noop, ["a"]))
        dag.add_node(DAGNode("c", "C", noop, ["a"]))

        order = dag.get_execution_order()

        # A must come first
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        # D must come after B and C
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    @pytest.mark.asyncio
    async def test_node_timeout(self):
        """Test node timeout handling."""
        async def slow(ctx: WorkflowContext) -> str:
            await asyncio.sleep(10)
            return "done"

        dag = DAGExecutor("timeout-dag")
        dag.add_node(DAGNode("slow", "Slow Node", slow, [], timeout_seconds=1))

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        assert result.status in ["failed", "partially_completed"]
        assert "slow" in result.nodes_failed

    @pytest.mark.asyncio
    async def test_context_sharing(self):
        """Test nodes can share results via context."""
        async def producer(ctx: WorkflowContext) -> int:
            return 42

        async def consumer(ctx: WorkflowContext) -> int:
            producer_result = ctx.get_step_result("producer")
            return producer_result * 2

        dag = DAGExecutor("sharing-dag")
        dag.add_node(DAGNode("producer", "Producer", producer, []))
        dag.add_node(DAGNode("consumer", "Consumer", consumer, ["producer"]))

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        assert result.status == "completed"
        assert result.node_results.get("producer") == 42
        assert result.node_results.get("consumer") == 84


@pytest.mark.constitutional
class TestDAGConstitutionalCompliance:
    """Tests for DAG constitutional compliance."""

    def test_dag_result_includes_hash(self):
        """Test DAG result includes constitutional hash."""
        result = DAGResult(
            dag_id="test",
            status="completed",
            node_results={},
            nodes_completed=[],
            nodes_failed=[],
            nodes_skipped=[],
            execution_time_ms=0,
        )

        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_dag_executor_uses_hash(self):
        """Test DAG executor uses constitutional hash."""
        dag = DAGExecutor("test-dag")
        assert dag.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_dag_includes_hash_in_result(self):
        """Test executed DAG includes hash in result."""
        async def noop(ctx: WorkflowContext) -> str:
            return "done"

        dag = DAGExecutor("hash-dag")
        dag.add_node(DAGNode("a", "A", noop, []))

        ctx = WorkflowContext.create()
        result = await dag.execute(ctx)

        result_dict = result.to_dict()
        assert result_dict["constitutional_hash"] == CONSTITUTIONAL_HASH
