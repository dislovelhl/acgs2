"""
Tests for Base Workflow Abstractions
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
from typing import Any, Dict

import pytest

from ..base.context import WorkflowContext
from ..base.result import WorkflowResult, WorkflowStatus
from ..base.step import StepCompensation, WorkflowStep
from ..base.workflow import BaseWorkflow

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class TestWorkflowContext:
    """Tests for WorkflowContext."""

    def test_create_context(self):
        """Test context creation with factory method."""
        ctx = WorkflowContext.create(tenant_id="tenant-1")

        assert ctx.workflow_id is not None
        assert ctx.tenant_id == "tenant-1"
        assert ctx.constitutional_hash == CONSTITUTIONAL_HASH
        assert ctx.trace_id is not None

    def test_step_results(self):
        """Test step result storage and retrieval."""
        ctx = WorkflowContext.create()

        ctx.set_step_result("step1", {"value": 42})

        assert ctx.has_step_result("step1")
        assert ctx.get_step_result("step1") == {"value": 42}
        assert not ctx.has_step_result("step2")
        assert ctx.get_step_result("step2") is None

    def test_child_context(self):
        """Test child context creation and inheritance."""
        parent = WorkflowContext.create(tenant_id="tenant-1", metadata={"key": "value"})
        parent.set_step_result("parent_step", "result")

        child = parent.create_child_context()

        assert child.parent_workflow_id == parent.workflow_id
        assert child.tenant_id == parent.tenant_id
        assert child.trace_id == parent.trace_id
        assert child.metadata == parent.metadata
        assert not child.has_step_result("parent_step")

    def test_merge_child_results(self):
        """Test merging results from child context."""
        parent = WorkflowContext.create()
        child = parent.create_child_context()

        child.set_step_result("child_step", "child_result")
        child.add_error("child error")

        parent.merge_child_results(child, prefix="child:")

        assert parent.get_step_result("child:child_step") == "child_result"
        assert "child error" in parent.errors

    def test_serialization(self):
        """Test context to_dict and from_dict."""
        ctx = WorkflowContext.create(tenant_id="tenant-1")
        ctx.set_step_result("step1", "result1")

        data = ctx.to_dict()
        restored = WorkflowContext.from_dict(data)

        assert restored.workflow_id == ctx.workflow_id
        assert restored.tenant_id == ctx.tenant_id
        assert restored.get_step_result("step1") == "result1"


class TestWorkflowResult:
    """Tests for WorkflowResult."""

    def test_success_factory(self):
        """Test success result creation."""
        result = WorkflowResult.success(
            workflow_id="wf-1",
            output={"result": "done"},
            execution_time_ms=100.0,
            steps_completed=["step1", "step2"],
        )

        assert result.is_successful
        assert not result.is_failed
        assert result.status == WorkflowStatus.COMPLETED
        assert result.output == {"result": "done"}

    def test_failure_factory(self):
        """Test failure result creation."""
        result = WorkflowResult.failure(
            workflow_id="wf-1",
            errors=["Step failed"],
            execution_time_ms=50.0,
            steps_completed=["step1"],
            steps_failed=["step2"],
        )

        assert result.is_failed
        assert not result.is_successful
        assert result.status == WorkflowStatus.FAILED

    def test_compensated_status(self):
        """Test compensated failure result."""
        result = WorkflowResult.failure(
            workflow_id="wf-1",
            errors=["Step failed"],
            execution_time_ms=150.0,
            steps_completed=["step1"],
            steps_failed=["step2"],
            compensations_executed=["comp1", "comp2"],
        )

        assert result.status == WorkflowStatus.COMPENSATED
        assert result.is_compensated

    def test_serialization(self):
        """Test result to_dict and from_dict."""
        result = WorkflowResult.success(
            workflow_id="wf-1",
            output={"key": "value"},
            execution_time_ms=100.0,
            steps_completed=["step1"],
        )

        data = result.to_dict()
        restored = WorkflowResult.from_dict(data)

        assert restored.workflow_id == result.workflow_id
        assert restored.status == result.status
        assert restored.output == result.output


class TestWorkflowStep:
    """Tests for WorkflowStep."""

    @pytest.mark.asyncio
    async def test_step_execution(self):
        """Test step execute function."""

        async def execute_fn(input: Dict[str, Any]) -> str:
            return f"processed: {input.get('data')}"

        step = WorkflowStep(
            name="test_step",
            execute=execute_fn,
        )

        result = await step.execute({"data": "test"})
        assert result == "processed: test"

    @pytest.mark.asyncio
    async def test_step_with_compensation(self):
        """Test step with compensation."""
        executed = []

        async def execute_fn(input: Dict[str, Any]) -> str:
            executed.append("execute")
            return "done"

        async def compensate_fn(input: Dict[str, Any]) -> None:
            executed.append("compensate")

        step = WorkflowStep(
            name="test_step",
            execute=execute_fn,
            compensation=StepCompensation(
                name="undo_test",
                execute=compensate_fn,
            ),
        )

        await step.execute({})
        assert step.compensation is not None
        await step.compensation.execute({})

        assert executed == ["execute", "compensate"]


class SimpleWorkflow(BaseWorkflow):
    """Simple test workflow implementation."""

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        # Validate constitutional hash
        if not await self.validate_constitutional_hash():
            return WorkflowResult.failure(
                workflow_id=self.workflow_id,
                errors=["Constitutional hash validation failed"],
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=[],
                steps_failed=["hash_validation"],
            )

        # Simple step
        self.context.set_step_result("process", input.get("data", "default"))

        return WorkflowResult.success(
            workflow_id=self.workflow_id,
            output={"processed": self.context.get_step_result("process")},
            execution_time_ms=self.context.get_elapsed_time_ms(),
            steps_completed=["hash_validation", "process"],
        )


class TestBaseWorkflow:
    """Tests for BaseWorkflow."""

    @pytest.mark.asyncio
    async def test_workflow_run(self):
        """Test basic workflow execution."""
        workflow = SimpleWorkflow(workflow_id="test")

        result = await workflow.run({"data": "test_value"})

        assert result.is_successful
        assert result.output["processed"] == "test_value"

    @pytest.mark.asyncio
    async def test_constitutional_hash_validation(self):
        """Test constitutional hash is validated."""
        workflow = SimpleWorkflow(
            workflow_id="test",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        result = await workflow.run({})

        assert result.is_successful
        assert workflow.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_workflow_timeout(self):
        """Test workflow timeout handling."""

        class SlowWorkflow(BaseWorkflow):
            async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
                await asyncio.sleep(10)  # Long operation
                return WorkflowResult.success(
                    workflow_id=self.workflow_id,
                    output={},
                    execution_time_ms=0,
                    steps_completed=[],
                )

        workflow = SlowWorkflow(
            workflow_id="slow",
            timeout_seconds=0.1,  # Very short timeout
        )

        result = await workflow.run({})

        assert result.status == WorkflowStatus.TIMED_OUT


@pytest.mark.constitutional
class TestConstitutionalCompliance:
    """Tests for constitutional compliance."""

    def test_constitutional_hash_in_context(self):
        """Test constitutional hash is present in context."""
        ctx = WorkflowContext.create()
        assert ctx.constitutional_hash == CONSTITUTIONAL_HASH

    def test_constitutional_hash_in_result(self):
        """Test constitutional hash is present in result."""
        result = WorkflowResult.success(
            workflow_id="wf-1",
            output={},
            execution_time_ms=0,
            steps_completed=[],
        )
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_workflow_validates_hash(self):
        """Test workflow validates constitutional hash."""
        workflow = SimpleWorkflow(
            workflow_id="test",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        # Should pass validation
        is_valid = await workflow.validate_constitutional_hash()
        assert is_valid

    @pytest.mark.asyncio
    async def test_workflow_rejects_invalid_hash(self):
        """Test workflow rejects invalid constitutional hash."""
        workflow = SimpleWorkflow(
            workflow_id="test",
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        # Should raise ConstitutionalHashMismatchError with wrong hash
        from ..base.workflow import ConstitutionalHashMismatchError

        with pytest.raises(ConstitutionalHashMismatchError):
            await workflow.validate_constitutional_hash("wrong_hash")
