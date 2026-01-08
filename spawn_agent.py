#!/usr/bin/env python3
"""
Simple agent spawner for ACGS-2 coordination framework
"""

import asyncio
import json
import os
import sys

# Add the ACGS-2 core to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src/core"))


async def spawn_agent():
    """Spawn an agent using the EnhancedAgentBus"""
    try:
        from enhanced_agent_bus.core import EnhancedAgentBus

        # Create bus instance
        bus = EnhancedAgentBus()

        # Start the bus
        await bus.start()

        # Agent configuration
        agent_name = "coder-agent-1"
        agent_type = "coder"
        agent_id = f"{agent_type}-{agent_name.lower().replace(' ', '-')}-{hash(agent_name) % 10000}"
        skills = ["python", "typescript", "development", "coding"]

        # Register the agent
        success = await bus.register_agent(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=skills,
            tenant_id="default",
        )

        # Stop the bus
        await bus.stop()

        if success:
            result = {
                "success": True,
                "agentId": agent_id,
                "agentType": agent_type,
                "capabilities": skills,
                "message": f"Agent {agent_name} spawned successfully with ID {agent_id}",
            }
        else:
            result = {"success": False, "error": "Failed to register agent with bus"}

        print(json.dumps(result, indent=2))
        return result

    except Exception as e:
        error_result = {"success": False, "error": f"Exception during agent spawning: {str(e)}"}
        print(json.dumps(error_result, indent=2))
        return error_result


if __name__ == "__main__":
    asyncio.run(spawn_agent())
