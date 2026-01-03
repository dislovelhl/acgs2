#!/usr/bin/env python3
"""
Agent Spawner for ACGS-2 Claude Flow CLI

This script provides a bridge between the Node.js CLI and the Python EnhancedAgentBus.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the ACGS-2 core to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../acgs2-core"))

from ..utils.logging_config import log_error_result, log_success_result, log_warning, setup_logging

# Setup logging
logger = setup_logging(__name__, json_format=True)

try:
    from enhanced_agent_bus import EnhancedAgentBus
except ImportError as e:
    log_error_result(logger, f"Failed to import EnhancedAgentBus: {e}")
    sys.exit(1)


async def spawn_agent(agent_name: str, agent_type: str, skills: list, tenant_id: str = "default"):
    """Spawn an agent using the EnhancedAgentBus"""
    try:
        # Create bus instance
        bus = EnhancedAgentBus()

        # Start the bus
        await bus.start()

        # Generate agent ID
        agent_id = f"{agent_type}-{agent_name.lower().replace(' ', '-')}-{hash(agent_name) % 10000}"

        # Map agent types to capabilities
        base_capabilities = {
            "coder": ["python", "javascript", "typescript", "coding", "development"],
            "researcher": ["research", "analysis", "data-collection", "synthesis"],
            "analyst": ["data-analysis", "reporting", "insights", "visualization"],
            "tester": ["testing", "qa", "validation", "automation"],
            "coordinator": [
                "coordination",
                "orchestration",
                "workflow-management",
                "task-distribution",
            ],
        }

        # Combine base capabilities with provided skills
        capabilities = base_capabilities.get(agent_type, []) + skills

        # Register the agent
        success = await bus.register_agent(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            tenant_id=tenant_id,
        )

        # Persist agent information if registration was successful
        if success:
            await _persist_agent_info(
                agent_id,
                {
                    "name": agent_name,
                    "type": agent_type,
                    "capabilities": capabilities,
                    "status": "active",
                    "created_at": datetime.now().timestamp(),
                    "last_active": datetime.now().timestamp(),
                    "tenant_id": "default",
                    "swarm_id": None,  # TODO: Associate with current swarm
                },
            )

        # Stop the bus
        await bus.stop()

        if success:
            return {
                "success": True,
                "agentId": agent_id,
                "agentType": agent_type,
                "capabilities": capabilities,
            }
        else:
            return {"success": False, "error": "Failed to register agent with bus"}

    except Exception as e:
        return {"success": False, "error": f"Exception during agent spawning: {str(e)}"}


async def _persist_agent_info(agent_id: str, agent_info: dict):
    """Persist agent information to file storage"""
    try:
        # Create storage directory if it doesn't exist
        storage_dir = os.path.join(os.path.dirname(__file__), "../../storage")
        os.makedirs(storage_dir, exist_ok=True)

        # Save agent information
        agent_file = os.path.join(storage_dir, f"agent_{agent_id}.json")
        with open(agent_file, "w") as f:
            json.dump(
                {"agent_id": agent_id, **agent_info, "persisted_at": datetime.now().timestamp()},
                f,
                indent=2,
            )

    except Exception as e:
        # Log error but don't fail spawning
        log_warning(logger, f"Warning: Failed to persist agent info: {e}")


def main():
    """Main entry point for the script"""
    if len(sys.argv) < 4:
        error_msg = "Usage: python agentSpawner.py <agent_name> <agent_type> <skills_json>"
        log_error_result(logger, error_msg)
        sys.exit(1)

    agent_name = sys.argv[1]
    agent_type = sys.argv[2]

    try:
        skills = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []
    except json.JSONDecodeError:
        skills = []

    # Run the async function
    result = asyncio.run(spawn_agent(agent_name, agent_type, skills))
    log_success_result(logger, result)


if __name__ == "__main__":
    main()
