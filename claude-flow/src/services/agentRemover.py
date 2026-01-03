#!/usr/bin/env python3
"""
Agent Remover for ACGS-2 Claude Flow CLI

This script removes an agent from the swarm and deletes its persisted information.
"""

import asyncio
import json
import os
import sys

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


async def remove_agent(agent_id: str):
    """Remove an agent from the swarm and delete its persisted information"""
    try:
        # First, try to unregister from the EnhancedAgentBus
        try:
            bus = EnhancedAgentBus()
            await bus.start()
            await bus.unregister_agent(agent_id)
            await bus.stop()
        except Exception as e:
            # Log but don't fail - the agent file removal is the primary goal
            log_warning(logger, f"Could not unregister agent from bus: {e}")

        # Remove the persisted agent file
        removed = await _remove_agent_file(agent_id)

        if removed:
            return {
                "success": True,
                "agentId": agent_id,
                "message": f"Agent {agent_id} removed successfully",
            }
        else:
            return {
                "success": False,
                "error": f"Agent {agent_id} not found in storage",
            }

    except Exception as e:
        return {"success": False, "error": f"Exception during agent removal: {str(e)}"}


async def _remove_agent_file(agent_id: str) -> bool:
    """Remove the persisted agent file from storage"""
    try:
        storage_dir = os.path.join(os.path.dirname(__file__), "../../storage")
        agent_file = os.path.join(storage_dir, f"agent_{agent_id}.json")

        if os.path.exists(agent_file):
            os.remove(agent_file)
            return True
        else:
            # Check if any file contains this agent_id (handle different naming)
            if os.path.exists(storage_dir):
                for filename in os.listdir(storage_dir):
                    if filename.startswith("agent_") and filename.endswith(".json"):
                        filepath = os.path.join(storage_dir, filename)
                        try:
                            with open(filepath, "r") as f:
                                agent_data = json.load(f)
                                if agent_data.get("agent_id") == agent_id:
                                    os.remove(filepath)
                                    return True
                        except (json.JSONDecodeError, IOError):
                            continue
            return False

    except Exception as e:
        log_warning(logger, f"Failed to remove agent file: {e}")
        return False


def main():
    """Main entry point for the script"""
    if len(sys.argv) < 2:
        error_msg = "Usage: python agentRemover.py <agent_id>"
        log_error_result(logger, error_msg)
        sys.exit(1)

    agent_id = sys.argv[1]

    # Run the async function
    result = asyncio.run(remove_agent(agent_id))
    log_success_result(logger, result)


if __name__ == "__main__":
    main()
