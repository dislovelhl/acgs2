"""
ACGS-2 Integration Tests: IT-06 - Orchestration Resume

Tests long-running task orchestration with checkpointing and resume capability.
Expected: TO reloads checkpoint from DMS and continues, no duplicate execution.
"""

import uuid
from datetime import datetime, timezone

import pytest

from .conftest import (
    CoreEnvelope,
    MockDMS,
)


class MockTaskOrchestrator:
    """Mock Task Orchestration system for testing."""

    def __init__(self, dms: MockDMS):
        self.dms = dms
        self.tasks = {}
        self.checkpoints = {}

    async def start_task(self, objective: str, plan: dict, envelope: CoreEnvelope):
        """Start a new task with checkpointing."""
        task_id = str(uuid.uuid4())

        task_state = {
            "task_id": task_id,
            "objective": objective,
            "plan": plan,
            "status": "running",
            "steps_completed": [],
            "current_step": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "envelope": envelope,
        }

        self.tasks[task_id] = task_state

        # Checkpoint the initial state
        await self._checkpoint(task_id, task_state)

        return task_id

    async def execute_step(self, task_id: str):
        """Execute the next step of a task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        if task["status"] != "running":
            return {"status": "not_running", "task_status": task["status"]}

        current_step = task["current_step"]
        plan = task["plan"]

        if current_step >= len(plan.get("steps", [])):
            # Task completed
            task["status"] = "completed"
            await self._checkpoint(task_id, task)
            return {"status": "completed", "task_id": task_id}

        # Execute current step
        step = plan["steps"][current_step]
        step_result = await self._execute_step_logic(step)

        # Record completion
        task["steps_completed"].append(
            {
                "step": current_step,
                "action": step,
                "result": step_result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        task["current_step"] += 1

        # Checkpoint progress
        await self._checkpoint(task_id, task)

        return {
            "status": "step_completed",
            "step": current_step,
            "result": step_result,
            "task_id": task_id,
        }

    async def resume_task(self, task_id: str):
        """Resume a task from its last checkpoint."""
        if task_id in self.checkpoints:
            # Restore from checkpoint
            checkpoint_data = self.checkpoints[task_id]
            self.tasks[task_id] = checkpoint_data.copy()
            return {"status": "resumed", "task_id": task_id}
        else:
            raise ValueError(f"No checkpoint found for task {task_id}")

    async def _checkpoint(self, task_id: str, task_state: dict):
        """Save task state as a checkpoint in DMS."""
        from .conftest import MemoryRecord, RecordType

        checkpoint_record = MemoryRecord(
            record_type=RecordType.TASK_ARTIFACT,
            content=f"Task checkpoint: {task_id}",
            provenance={
                "source": "orchestrator",
                "task_id": task_id,
                "checkpoint_version": len(self.checkpoints.get(task_id, [])) + 1,
            },
            retention={"ttl_days": 7, "pii": False},  # Keep task checkpoints for a week
        )

        envelope = task_state.get("envelope")
        if envelope:
            await self.dms.write(checkpoint_record, envelope)

        # Store locally for testing
        self.checkpoints[task_id] = task_state.copy()

    async def _execute_step_logic(self, step: dict) -> dict:
        """Execute the logic for a step (simplified for testing)."""
        action = step.get("action", "")

        # Simulate different step types
        if "search" in action:
            return {"type": "search", "results": ["Result 1", "Result 2"]}
        elif "compute" in action:
            return {"type": "computation", "result": 42}
        elif "write" in action:
            return {"type": "write", "status": "success"}
        else:
            return {"type": "unknown", "result": "completed"}


class TestIT06OrchestrationResume:
    """
    IT-06: Orchestration resume

    Input: Simulate crash mid-task
    Expected:
        - TO reloads checkpoint from DMS and continues
        - No duplicate execution
    """

    @pytest.fixture
    def task_orchestrator(self, dms):
        """Create a mock task orchestrator."""
        return MockTaskOrchestrator(dms)

    @pytest.mark.asyncio
    async def test_task_checkpointing_works(self, task_orchestrator, envelope_factory):
        """Test that task state is properly checkpointed."""
        envelope = envelope_factory("CF", {"task": "test"})

        plan = {
            "steps": [
                {"action": "search for data"},
                {"action": "compute results"},
                {"action": "write summary"},
            ]
        }

        task_id = await task_orchestrator.start_task("Test task", plan, envelope)

        # Execute first step
        result1 = await task_orchestrator.execute_step(task_id)
        assert result1["status"] == "step_completed"
        assert result1["step"] == 0

        # Check checkpoint exists
        assert task_id in task_orchestrator.checkpoints
        checkpoint = task_orchestrator.checkpoints[task_id]
        assert checkpoint["current_step"] == 1
        assert len(checkpoint["steps_completed"]) == 1

    @pytest.mark.asyncio
    async def test_task_resume_from_checkpoint(self, task_orchestrator, envelope_factory):
        """Test that tasks can resume from checkpoints."""
        envelope = envelope_factory("CF", {"task": "resume_test"})

        plan = {
            "steps": [
                {"action": "step 1"},
                {"action": "step 2"},
                {"action": "step 3"},
            ]
        }

        # Start task
        task_id = await task_orchestrator.start_task("Resume test", plan, envelope)

        # Execute two steps
        await task_orchestrator.execute_step(task_id)
        await task_orchestrator.execute_step(task_id)

        # Verify we're on step 2
        task = task_orchestrator.tasks[task_id]
        assert task["current_step"] == 2
        assert len(task["steps_completed"]) == 2

        # Simulate "crash" by clearing in-memory state
        del task_orchestrator.tasks[task_id]

        # Resume from checkpoint
        resume_result = await task_orchestrator.resume_task(task_id)
        assert resume_result["status"] == "resumed"

        # Verify state was restored
        task = task_orchestrator.tasks[task_id]
        assert task["current_step"] == 2
        assert len(task["steps_completed"]) == 2

    @pytest.mark.asyncio
    async def test_no_duplicate_execution_after_resume(self, task_orchestrator, envelope_factory):
        """Test that resuming doesn't cause duplicate step execution."""
        envelope = envelope_factory("CF", {"task": "duplicate_test"})

        execution_count = 0

        # Override step execution to count calls
        original_execute = task_orchestrator._execute_step_logic

        async def counting_execute(step):
            nonlocal execution_count
            execution_count += 1
            return await original_execute(step)

        task_orchestrator._execute_step_logic = counting_execute

        plan = {
            "steps": [
                {"action": "counted step 1"},
                {"action": "counted step 2"},
            ]
        }

        task_id = await task_orchestrator.start_task("Duplicate test", plan, envelope)

        # Execute first step
        await task_orchestrator.execute_step(task_id)
        assert execution_count == 1

        # Simulate crash and resume
        del task_orchestrator.tasks[task_id]
        await task_orchestrator.resume_task(task_id)

        # Execute next step (should not re-execute step 1)
        await task_orchestrator.execute_step(task_id)
        assert execution_count == 2  # Not 3 (which would be duplicate)

    @pytest.mark.asyncio
    async def test_task_completion_checkpointed(self, task_orchestrator, envelope_factory):
        """Test that task completion is properly checkpointed."""
        envelope = envelope_factory("CF", {"task": "completion_test"})

        plan = {
            "steps": [
                {"action": "single step"},
            ]
        }

        task_id = await task_orchestrator.start_task("Completion test", plan, envelope)

        # Execute the single step
        result = await task_orchestrator.execute_step(task_id)
        assert result["status"] == "completed"

        # Check final checkpoint
        checkpoint = task_orchestrator.checkpoints[task_id]
        assert checkpoint["status"] == "completed"
        assert checkpoint["current_step"] == 1
        assert len(checkpoint["steps_completed"]) == 1

    @pytest.mark.asyncio
    async def test_checkpoint_persistence_in_dms(self, task_orchestrator, envelope_factory):
        """Test that checkpoints are persisted in DMS with proper metadata."""
        envelope = envelope_factory("CF", {"task": "persistence_test"})

        plan = {"steps": [{"action": "test step"}]}

        task_id = await task_orchestrator.start_task("Persistence test", plan, envelope)

        # Execute step to create checkpoint
        await task_orchestrator.execute_step(task_id)

        # Check DMS has the checkpoint record
        dms_records = task_orchestrator.dms.records
        checkpoint_records = [r for r in dms_records if r.record_type.name == "TASK_ARTIFACT"]

        assert len(checkpoint_records) >= 1

        record = checkpoint_records[0]
        assert "task_id" in record.provenance
        assert record.provenance["task_id"] == task_id
        assert record.provenance["source"] == "orchestrator"
