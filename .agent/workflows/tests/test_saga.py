"""
Tests for Saga Implementation
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import asyncio
from typing import Any, Dict, List

from ..base.context import WorkflowContext
from ..sagas.base_saga import BaseSaga, SagaStep, SagaResult, SagaStatus
from ..sagas.distributed_tx import DistributedTransactionSaga
from ..sagas.policy_update import PolicyUpdateSaga
from ..sagas.registration import AgentRegistrationSaga
from ..base.activities import DefaultActivities

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TestSagaStep:
    """Tests for SagaStep."""

    def test_step_creation(self):
        """Test step creation with defaults."""
        async def execute(input: Dict[str, Any]) -> str:
            return "done"

        step = SagaStep(
            name="test_step",
            execute=execute,
        )

        assert step.name == "test_step"
        assert step.compensate is None
        assert step.is_critical
        assert step.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_step_execution(self):
        """Test step execute function."""
        async def execute(input: Dict[str, Any]) -> str:
            return f"processed: {input.get('data')}"

        step = SagaStep(name="test", execute=execute)

        result = await step.execute({"data": "test"})
        assert result == "processed: test"


class TestBaseSaga:
    """Tests for BaseSaga."""

    @pytest.mark.asyncio
    async def test_simple_saga_success(self):
        """Test simple saga with all steps succeeding."""
        execution_order = []

        async def step1(input: Dict[str, Any]) -> str:
            execution_order.append("step1")
            return "step1_result"

        async def step2(input: Dict[str, Any]) -> str:
            execution_order.append("step2")
            return "step2_result"

        saga = BaseSaga("test-saga")
        saga.add_step(SagaStep("step1", step1))
        saga.add_step(SagaStep("step2", step2))

        ctx = WorkflowContext.create()
        result = await saga.execute(ctx, {"data": "test"})

        assert result.status == SagaStatus.COMPLETED
        assert execution_order == ["step1", "step2"]
        assert "step1" in result.steps_completed
        assert "step2" in result.steps_completed

    @pytest.mark.asyncio
    async def test_saga_with_compensation(self):
        """Test saga runs compensations on failure."""
        execution_order = []

        async def step1(input: Dict[str, Any]) -> str:
            execution_order.append("step1_execute")
            return "done"

        async def comp1(input: Dict[str, Any]) -> None:
            execution_order.append("step1_compensate")

        async def step2(input: Dict[str, Any]) -> str:
            execution_order.append("step2_execute")
            return "done"

        async def comp2(input: Dict[str, Any]) -> None:
            execution_order.append("step2_compensate")

        async def step3(input: Dict[str, Any]) -> str:
            execution_order.append("step3_execute")
            raise Exception("Intentional failure")

        saga = BaseSaga("comp-saga")
        saga.add_step(SagaStep("step1", step1, comp1))
        saga.add_step(SagaStep("step2", step2, comp2))
        saga.add_step(SagaStep("step3", step3))

        ctx = WorkflowContext.create()
        result = await saga.execute(ctx, {})

        assert result.status == SagaStatus.COMPENSATED
        # Compensations should run in LIFO order
        assert execution_order == [
            "step1_execute",
            "step2_execute",
            "step3_execute",
            "step2_compensate",  # LIFO: step2 first
            "step1_compensate",  # Then step1
        ]

    @pytest.mark.asyncio
    async def test_saga_lifo_compensation_order(self):
        """Test compensations run in strict LIFO order."""
        compensation_order = []

        async def make_step(name: str):
            async def execute(input: Dict[str, Any]) -> str:
                return f"{name}_done"
            return execute

        async def make_comp(name: str):
            async def compensate(input: Dict[str, Any]) -> None:
                compensation_order.append(name)
            return compensate

        async def failing_step(input: Dict[str, Any]) -> str:
            raise Exception("Fail")

        saga = BaseSaga("lifo-saga")
        saga.add_step(SagaStep("a", await make_step("a"), await make_comp("a")))
        saga.add_step(SagaStep("b", await make_step("b"), await make_comp("b")))
        saga.add_step(SagaStep("c", await make_step("c"), await make_comp("c")))
        saga.add_step(SagaStep("d", failing_step))

        ctx = WorkflowContext.create()
        await saga.execute(ctx, {})

        # Strict LIFO: c, b, a
        assert compensation_order == ["c", "b", "a"]

    @pytest.mark.asyncio
    async def test_saga_partial_compensation(self):
        """Test saga handles partial compensation failure."""
        async def success_step(input: Dict[str, Any]) -> str:
            return "done"

        async def success_comp(input: Dict[str, Any]) -> None:
            pass

        async def fail_comp(input: Dict[str, Any]) -> None:
            raise Exception("Compensation failed")

        async def fail_step(input: Dict[str, Any]) -> str:
            raise Exception("Step failed")

        saga = BaseSaga("partial-saga", max_compensation_retries=1)
        saga.add_step(SagaStep("a", success_step, success_comp))
        saga.add_step(SagaStep("b", success_step, fail_comp))
        saga.add_step(SagaStep("c", fail_step))

        ctx = WorkflowContext.create()
        result = await saga.execute(ctx, {})

        assert result.status == SagaStatus.PARTIALLY_COMPENSATED
        assert "a" in result.compensations_executed
        assert "b" in result.compensations_failed

    @pytest.mark.asyncio
    async def test_saga_non_critical_step(self):
        """Test saga continues on non-critical step failure."""
        execution_order = []

        async def step1(input: Dict[str, Any]) -> str:
            execution_order.append("step1")
            return "done"

        async def optional_step(input: Dict[str, Any]) -> str:
            execution_order.append("optional")
            raise Exception("Optional failed")

        async def step3(input: Dict[str, Any]) -> str:
            execution_order.append("step3")
            return "done"

        saga = BaseSaga("optional-saga")
        saga.add_step(SagaStep("step1", step1))
        saga.add_step(SagaStep("optional", optional_step, is_critical=False))
        saga.add_step(SagaStep("step3", step3))

        ctx = WorkflowContext.create()
        result = await saga.execute(ctx, {})

        # Should complete despite optional step failure
        assert result.status == SagaStatus.COMPLETED
        assert execution_order == ["step1", "optional", "step3"]

    @pytest.mark.asyncio
    async def test_saga_timeout(self):
        """Test saga handles step timeout."""
        async def slow_step(input: Dict[str, Any]) -> str:
            await asyncio.sleep(10)
            return "done"

        saga = BaseSaga("timeout-saga")
        saga.add_step(SagaStep("slow", slow_step, timeout_seconds=1))

        ctx = WorkflowContext.create()
        result = await saga.execute(ctx, {})

        assert result.status in [SagaStatus.FAILED, SagaStatus.COMPENSATED]
        assert "slow" in result.steps_failed

    @pytest.mark.asyncio
    async def test_saga_chaining(self):
        """Test add_step returns self for chaining."""
        async def step(input: Dict[str, Any]) -> str:
            return "done"

        saga = (
            BaseSaga("chain-saga")
            .add_step(SagaStep("a", step))
            .add_step(SagaStep("b", step))
            .add_step(SagaStep("c", step))
        )

        ctx = WorkflowContext.create()
        result = await saga.execute(ctx, {})

        assert result.status == SagaStatus.COMPLETED
        assert len(result.steps_completed) == 3


class TestSagaResult:
    """Tests for SagaResult."""

    def test_result_creation(self):
        """Test result creation with defaults."""
        result = SagaResult(
            saga_id="test",
            status=SagaStatus.COMPLETED,
            steps_completed=["a", "b"],
            steps_failed=[],
            compensations_executed=[],
            compensations_failed=[],
            execution_time_ms=100.0,
        )

        assert result.saga_id == "test"
        assert result.status == SagaStatus.COMPLETED
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_result_serialization(self):
        """Test result to_dict."""
        result = SagaResult(
            saga_id="test",
            status=SagaStatus.COMPLETED,
            steps_completed=["a"],
            steps_failed=[],
            compensations_executed=[],
            compensations_failed=[],
            execution_time_ms=50.0,
            output={"key": "value"},
        )

        data = result.to_dict()

        assert data["saga_id"] == "test"
        assert data["status"] == "completed"
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert data["output"] == {"key": "value"}


@pytest.mark.constitutional
class TestSagaConstitutionalCompliance:
    """Tests for saga constitutional compliance."""

    @pytest.mark.asyncio
    async def test_saga_includes_hash_in_step_input(self):
        """Test saga passes constitutional hash to steps."""
        received_hash = None

        async def capture_hash(input: Dict[str, Any]) -> str:
            nonlocal received_hash
            received_hash = input.get("constitutional_hash")
            return "done"

        saga = BaseSaga("hash-saga")
        saga.add_step(SagaStep("capture", capture_hash))

        ctx = WorkflowContext.create()
        await saga.execute(ctx, {})

        assert received_hash == CONSTITUTIONAL_HASH


class TestExtendedSagas:
    """Tests for specialized saga implementations."""

    @pytest.mark.asyncio
    async def test_distributed_transaction_success(self):
        """Test successful distributed transaction."""
        class MockActivities(DefaultActivities):
            async def execute_agent_task(self, agent_id, task_name, payload):
                return {"status": "ok", "agent_id": agent_id}

        ctx = WorkflowContext.create()
        input_data = {
            "target_agent": "agent-1",
            "processor_agent": "agent-2",
            "amount": 100
        }
        
        result = await DistributedTransactionSaga.run_standard_tx(ctx, input_data, MockActivities())
        assert result.status == SagaStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_policy_update_success(self):
        """Test successful policy update saga."""
        class MockActivities(DefaultActivities):
            async def evaluate_policy(self, workflow_id, policy_path, input_data):
                return {"allowed": True}
            async def record_audit(self, workflow_id, event_type, event_data):
                return "audit-id"

        ctx = WorkflowContext.create()
        saga = PolicyUpdateSaga(constitutional_hash=CONSTITUTIONAL_HASH)
        saga.activities = MockActivities()
        
        result = await saga.execute(ctx, {
            "policy_id": "p1",
            "new_version": "2.0",
            "canary_agents": ["a1"]
        })
        
        assert result.status == SagaStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_registration_success(self):
        """Test successful agent registration saga."""
        class MockActivities(DefaultActivities):
            async def evaluate_policy(self, workflow_id, policy_path, input_data):
                return {"allowed": True}
            async def record_audit(self, workflow_id, event_type, event_data):
                return "audit-id"

        ctx = WorkflowContext.create()
        saga = AgentRegistrationSaga(constitutional_hash=CONSTITUTIONAL_HASH)
        saga.activities = MockActivities()
        
        result = await saga.execute(ctx, {
            "agent_id": "new-agent",
            "identity_proof": "proof-data",
            "capabilities": ["llm"]
        })
        
        assert result.status == SagaStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_saga_includes_hash_in_compensation_input(self):
        """Test saga passes constitutional hash to compensations."""
        received_hash = None

        async def step(input: Dict[str, Any]) -> str:
            return "done"

        async def capture_comp(input: Dict[str, Any]) -> None:
            nonlocal received_hash
            received_hash = input.get("constitutional_hash")

        async def fail_step(input: Dict[str, Any]) -> str:
            raise Exception("Fail")

        saga = BaseSaga("comp-hash-saga")
        saga.add_step(SagaStep("capture", step, capture_comp))
        saga.add_step(SagaStep("fail", fail_step))

        ctx = WorkflowContext.create()
        await saga.execute(ctx, {})

        assert received_hash == CONSTITUTIONAL_HASH
