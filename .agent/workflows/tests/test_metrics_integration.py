"""
Tests for Prometheus Metrics Integration
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from prometheus_client import REGISTRY

from ..base.step import WorkflowStep
from ..base.workflow import BaseWorkflow


class MockWorkflow(BaseWorkflow):
    def __init__(self, **kwargs):
        super().__init__(workflow_name="MockWorkflow", **kwargs)

    async def execute(self, input_data):
        step = WorkflowStep(name="step1", execute=self.step1)
        await self.run_step(step, input_data)
        return await self.complete({"ok": True})

    async def step1(self, input_data):
        return "done"


@pytest.mark.asyncio
async def test_workflow_metrics_emission():
    """Test that metrics are emitted on workflow execution."""
    workflow = MockWorkflow()

    # Execute workflow
    await workflow.run({})

    # Check executions total metric
    # Note: Regsitry values might require labels
    labels = {"workflow_name": "MockWorkflow", "status": "completed"}

    val = REGISTRY.get_sample_value("workflow_executions_total", labels)
    assert val is not None
    assert val >= 1


@pytest.mark.asyncio
async def test_step_metrics_emission():
    """Test that individual step metrics are emitted."""
    workflow = MockWorkflow()

    await workflow.run({})

    labels = {"workflow_name": "MockWorkflow", "step_name": "step1", "status": "success"}

    val = REGISTRY.get_sample_value("workflow_step_duration_seconds_count", labels)
    assert val is not None
    assert val >= 1
