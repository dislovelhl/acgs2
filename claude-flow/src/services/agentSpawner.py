#!/usr/bin/env python3
"""
Agent Spawner for ACGS-2 Claude Flow CLI

This script provides a bridge between the Node.js CLI and the Python EnhancedAgentBus.
"""

import sys
import json
import asyncio
import os

# Add the ACGS-2 core to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../acgs2-core'))

try:
    from enhanced_agent_bus import EnhancedAgentBus, CONSTITUTIONAL_HASH
except ImportError as e:
    print(json.dumps({
        "success": False,
        "error": f"Failed to import EnhancedAgentBus: {e}"
    }))
    sys.exit(1)

async def spawn_agent(agent_name: str, agent_type: str, skills: list):
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
            'coder': ['python', 'javascript', 'typescript', 'coding', 'development'],
            'researcher': ['research', 'analysis', 'data-collection', 'synthesis'],
            'analyst': ['data-analysis', 'reporting', 'insights', 'visualization'],
            'tester': ['testing', 'qa', 'validation', 'automation'],
            'coordinator': ['coordination', 'orchestration', 'workflow-management', 'task-distribution']
        }

        # Combine base capabilities with provided skills
        capabilities = base_capabilities.get(agent_type, []) + skills

        # Register the agent
        success = await bus.register_agent(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            tenant_id="default"  # TODO: Make configurable
        )

        # Stop the bus
        await bus.stop()

        if success:
            return {
                "success": True,
                "agentId": agent_id,
                "agentType": agent_type,
                "capabilities": capabilities
            }
        else:
            return {
                "success": False,
                "error": "Failed to register agent with bus"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Exception during agent spawning: {str(e)}"
        }

def main():
    """Main entry point for the script"""
    if len(sys.argv) < 4:
        print(json.dumps({
            "success": False,
            "error": "Usage: python agentSpawner.py <agent_name> <agent_type> <skills_json>"
        }))
        sys.exit(1)

    agent_name = sys.argv[1]
    agent_type = sys.argv[2]

    try:
        skills = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []
    except json.JSONDecodeError:
        skills = []

    # Run the async function
    result = asyncio.run(spawn_agent(agent_name, agent_type, skills))
    print(json.dumps(result))

if __name__ == "__main__":
    main()
