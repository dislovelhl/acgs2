#!/usr/bin/env python3
"""
Task Orchestrator for ACGS-2 Claude Flow CLI

This script provides task orchestration across the ACGS-2 agent swarm.
Implements various orchestration strategies and priority handling.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

# Add the ACGS-2 core to the path
sys.path.insert(0, "/home/dislove/document/acgs2/acgs2-core")

from ..utils.logging_config import log_error_result, log_success_result, setup_logging

# Setup logging
logger = setup_logging(__name__, json_format=True)

try:
    from enhanced_agent_bus import CONSTITUTIONAL_HASH, EnhancedAgentBus
    from enhanced_agent_bus.models import AgentMessage, MessageType, Priority
except ImportError as e:
    log_error_result(logger, f"Failed to import ACGS-2 modules: {e}")
    sys.exit(1)


class TaskOrchestrator:
    """Orchestrates complex tasks across the agent swarm."""

    def __init__(self):
        self.bus = None

    async def initialize(self):
        """Initialize the orchestrator with ACGS-2 bus."""
        try:
            self.bus = EnhancedAgentBus()
            await self.bus.start()
            return True
        except Exception:
            return False

    async def cleanup(self):
        """Clean up resources."""
        if self.bus:
            await self.bus.stop()

    async def orchestrate_task(
        self, task_description: str, strategy: str, priority: str
    ) -> Dict[str, Any]:
        """Orchestrate a task using the specified strategy."""

        if not await self.initialize():
            return {"success": False, "error": "Failed to initialize ACGS-2 bus"}

        try:
            # Generate unique identifiers
            task_id = f"task-{uuid.uuid4().hex[:16]}"
            workflow_id = f"workflow-{uuid.uuid4().hex[:16]}"

            # Map priority to internal values
            priority_map = {
                "low": "low",
                "medium": "medium",
                "high": "high",
                "critical": "critical",
            }
            internal_priority = priority_map.get(priority.lower(), "medium")

            # Map strategy to orchestration approach
            strategy_config = self._get_strategy_config(strategy)

            # Create task orchestration workflow
            workflow_input = {
                "task_id": task_id,
                "workflow_id": workflow_id,
                "task_description": task_description,
                "strategy": strategy,
                "priority": internal_priority,
                "strategy_config": strategy_config,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }

            # Submit task to the swarm via message bus
            result = await self._submit_orchestration_task(workflow_input)

            if result["success"]:
                return {
                    "success": True,
                    "taskId": task_id,
                    "workflowId": workflow_id,
                    "strategy": strategy,
                    "priority": internal_priority,
                    "status": "submitted",
                    "estimated_completion": self._estimate_completion_time(strategy, priority),
                }
            else:
                return {"success": False, "error": result.get("error", "Task submission failed")}

        except Exception as e:
            return {"success": False, "error": f"Exception during task orchestration: {str(e)}"}
        finally:
            await self.cleanup()

    def _get_strategy_config(self, strategy: str) -> Dict[str, Any]:
        """Get configuration for the specified orchestration strategy."""

        strategies = {
            "sequential": {
                "type": "sequential",
                "parallelism": 1,
                "agent_selection": "specialized",
                "coordination_mode": "linear",
            },
            "parallel": {
                "type": "parallel",
                "parallelism": "auto",
                "agent_selection": "available",
                "coordination_mode": "concurrent",
            },
            "hierarchical": {
                "type": "hierarchical",
                "parallelism": 3,
                "agent_selection": "coordinator_first",
                "coordination_mode": "supervised",
            },
            "consensus": {
                "type": "consensus",
                "parallelism": "majority",
                "agent_selection": "diverse",
                "coordination_mode": "voting",
            },
        }

        return strategies.get(strategy.lower(), strategies["parallel"])

    async def _submit_orchestration_task(self, workflow_input: Dict[str, Any]) -> Dict[str, Any]:
        """Submit the orchestration task to the ACGS-2 bus."""

        try:
            # Map priority string to Priority enum
            priority_map = {
                "low": Priority.LOW,
                "medium": Priority.MEDIUM,
                "high": Priority.HIGH,
                "critical": Priority.CRITICAL,
            }
            message_priority = priority_map.get(workflow_input["priority"], Priority.MEDIUM)

            # Create AgentMessage for task orchestration
            message = AgentMessage(
                message_type=MessageType.COMMAND,
                content={
                    "task_description": workflow_input["task_description"],
                    "strategy": workflow_input["strategy"],
                    "priority": workflow_input["priority"],
                    "workflow_id": workflow_input["workflow_id"],
                    "strategy_config": workflow_input["strategy_config"],
                    "task_id": workflow_input["task_id"],
                },
                from_agent="claude-flow-cli",
                to_agent="swarm-coordinator",  # This should be configurable or discovered
                priority=message_priority,
                tenant_id="default",  # Should be configurable
                constitutional_hash=workflow_input["constitutional_hash"],
            )

            # Send message through the bus
            result = await self.bus.send_message(message)

            if result.is_valid:
                return {"success": True}
            else:
                return {"success": False, "error": f"Message validation failed: {result.errors}"}

        except Exception as e:
            return {"success": False, "error": f"Failed to submit task: {str(e)}"}

    def _estimate_completion_time(self, strategy: str, priority: str) -> str:
        """Estimate task completion time based on strategy and priority."""
        # Simple estimation logic - in a real implementation this would be more sophisticated
        base_times = {
            "low": "2-4 hours",
            "medium": "30-60 minutes",
            "high": "10-30 minutes",
            "critical": "5-15 minutes",
        }
        return base_times.get(priority.lower(), "1-2 hours")


async def orchestrate_task(task_description: str, strategy: str, priority: str) -> Dict[str, Any]:
    """Main orchestration function."""

    orchestrator = TaskOrchestrator()
    try:
        return await orchestrator.orchestrate_task(task_description, strategy, priority)
    finally:
        await orchestrator.cleanup()


def main():
    """Main entry point for the script"""

    if len(sys.argv) < 4:
        error_msg = "Usage: python taskOrchestrator.py " "<task_description> <strategy> <priority>"
        log_error_result(logger, error_msg)
        sys.exit(1)

    task_description = sys.argv[1]
    strategy = sys.argv[2]
    priority = sys.argv[3]

    # Validate inputs
    valid_strategies = ["sequential", "parallel", "hierarchical", "consensus"]
    valid_priorities = ["low", "medium", "high", "critical"]

    if strategy.lower() not in valid_strategies:
        log_error_result(
            logger, f"Invalid strategy. Valid strategies: {', '.join(valid_strategies)}"
        )
        sys.exit(1)

    if priority.lower() not in valid_priorities:
        log_error_result(
            logger, f"Invalid priority. Valid priorities: {', '.join(valid_priorities)}"
        )
        sys.exit(1)

    # Run the async function
    result = asyncio.run(orchestrate_task(task_description, strategy, priority))
    log_success_result(logger, result)


if __name__ == "__main__":
    main()
