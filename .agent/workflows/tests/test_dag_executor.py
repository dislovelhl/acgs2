"""
Tests for DAG Executor
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio

import pytest

from ..base.context import WorkflowContext
from ..dags.dag_executor import DAGExecutor, DAGNode, DAGResult

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


class TestDAGOptimization:
    """Tests for DAG optimizations (Caching, Priority)."""

    @pytest.mark.asyncio
    async def test_result_caching(self):
        """Test result caching avoids re-execution."""
        execution_count = 0

        async def expensive_op(ctx: WorkflowContext) -> str:
            nonlocal execution_count
            execution_count += 1
            return "expensive_result"

        cache = {}
        dag = DAGExecutor("cache-dag", result_cache=cache)

        # First run: Should execute
        dag.add_node(DAGNode("n1", "Node 1", expensive_op, [], cache_key="key-1"))
        await dag.execute(WorkflowContext.create())
        assert execution_count == 1
        assert cache["key-1"] == "expensive_result"

        # Second run: Should use cache
        dag2 = DAGExecutor("cache-dag-2", result_cache=cache)
        dag2.add_node(DAGNode("n1", "Node 1", expensive_op, [], cache_key="key-1"))
        await dag2.execute(WorkflowContext.create())
        assert execution_count == 1  # Count should NOT increase

    @pytest.mark.asyncio
    async def test_priority_scheduling(self):
        """Test nodes with more dependents get priority."""
        execution_order = []

        async def step(name):
            async def func(ctx):
                execution_order.append(name)
                return name

            return func

        # limit parallelism to 1 to force serialization based on priority
        dag = DAGExecutor("priority-dag", max_parallel_nodes=1)

        # Critical path: A -> B -> C (A has 2 dependents total)
        # Less critical: D -> E (D has 1 dependent total)
        # Leaf: F (0 dependents)

        # Execution logic adds priority based on number of descendants
        # A: dependents=[B, C], B->C. A unblocks B. B unblocks C.
        #   Let's ensure the priority logic: "subtree size"
        #   A -> B -> C
        #   A -> D (so A has B, D as direct deps)

        # Let's try a simple meaningful priority test
        # A -> B -> C -> D (Chain length 4)
        # E -> F (Chain length 2)
        # Both A and E are ready initially. A should be picked first because it's the head of a longer chain.

        # Structure:
        # A -> B -> C -> D
        # E -> F

        dag.add_node(DAGNode("d", "D", await step("d"), ["c"]))
        dag.add_node(DAGNode("c", "C", await step("c"), ["b"]))
        dag.add_node(DAGNode("b", "B", await step("b"), ["a"]))
        dag.add_node(DAGNode("a", "A", await step("a"), []))

        dag.add_node(DAGNode("f", "F", await step("f"), ["e"]))
        dag.add_node(DAGNode("e", "E", await step("e"), []))

        await dag.execute(WorkflowContext.create())

        # A has priority 3 (B, C, D)
        # E has priority 1 (F)
        # So A should run before E

        # Note: B has priority 2, E has priority 1.
        # But B becomes ready only after A finishes.
        # So execution should be A -> (B or E?).
        # Wait, max_parallel=1.

        # 1. Ready: [A (p=3), E (p=1)] -> Pick A.
        #    Completed: A. Ready: [B (p=2), E (p=1)].
        # 2. Pick B.
        #    Completed: B. Ready: [C (p=1), E (p=1)].
        #    Tie-breaking is not strictly defined but priority helps.

        assert execution_order[0] == "a"
        # We at least know A runs before E because A has higher priority
        assert execution_order.index("a") < execution_order.index("e")
