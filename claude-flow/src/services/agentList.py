#!/usr/bin/env python3
"""
Agent List for ACGS-2 Claude Flow CLI

This script retrieves the list of active agents in the swarm.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# Add the ACGS-2 core to the path - validates ACGS-2 availability
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../acgs2-core"))

from ..utils.logging_config import log_error_result, log_success_result, log_warning, setup_logging

# Setup logging
logger = setup_logging(__name__, json_format=True)

try:
    import enhanced_agent_bus  # noqa: F401 - validates ACGS-2 availability
except ImportError as e:
    log_error_result(logger, f"Failed to import EnhancedAgentBus: {e}")
    sys.exit(1)


async def list_agents():
    """List all active agents in the swarm"""
    try:
        # Load persisted agent information
        agents = await _load_agent_info()

        # Also try to get swarm coordinator agents
        try:
            swarms = await _load_swarm_configs()
            for swarm_id, swarm_config in swarms.items():
                if swarm_config.get("coordinator_agent"):
                    coordinator_id = swarm_config["coordinator_agent"]
                    # Only add if not already in the list
                    if not any(agent["id"] == coordinator_id for agent in agents):
                        agent = {
                            "id": coordinator_id,
                            "name": f"Coordinator-{swarm_id.split('-')[-1]}",
                            "type": "coordinator",
                            "status": "active",
                            "capabilities": ["coordination", "orchestration", "task-distribution"],
                            "created_at": swarm_config.get(
                                "created_at", datetime.now(timezone.utc).timestamp()
                            ),
                            "last_active": datetime.now(timezone.utc).timestamp(),
                            "tenant_id": swarm_config.get("tenant_id", "default"),
                        }
                        agents.append(agent)
        except Exception:
            # Ignore swarm loading errors
            pass

        return {"success": True, "agents": agents}

    except Exception as e:
        return {"success": False, "error": f"Exception listing agents: {str(e)}"}


async def _load_agent_info() -> list:
    """Load all persisted agent information"""
    agents = []
    try:
        storage_dir = os.path.join(os.path.dirname(__file__), "../../storage")
        if os.path.exists(storage_dir):
            for filename in os.listdir(storage_dir):
                if filename.startswith("agent_") and filename.endswith(".json"):
                    try:
                        with open(os.path.join(storage_dir, filename), "r") as f:
                            agent_data = json.load(f)
                            agent = {
                                "id": agent_data.get("agent_id"),
                                "name": agent_data.get(
                                    "name", agent_data.get("agent_id", "").split("-")[-1]
                                ),
                                "type": agent_data.get("type", "unknown"),
                                "status": agent_data.get("status", "active"),
                                "capabilities": agent_data.get("capabilities", []),
                                "created_at": agent_data.get(
                                    "created_at", datetime.now(timezone.utc).timestamp()
                                ),
                                "last_active": agent_data.get(
                                    "last_active", datetime.now(timezone.utc).timestamp()
                                ),
                                "tenant_id": agent_data.get("tenant_id", "default"),
                            }
                            agents.append(agent)
                    except Exception as e:
                        log_warning(logger, f"Failed to load agent info {filename}: {e}")
    except Exception as e:
        log_warning(logger, f"Warning: Failed to load agent info: {e}")

    return agents


async def _load_swarm_configs() -> dict:
    """Load all persisted swarm configurations"""
    swarms = {}
    try:
        storage_dir = os.path.join(os.path.dirname(__file__), "../../storage")
        if os.path.exists(storage_dir):
            for filename in os.listdir(storage_dir):
                if filename.startswith("swarm_") and filename.endswith(".json"):
                    try:
                        with open(os.path.join(storage_dir, filename), "r") as f:
                            config = json.load(f)
                            swarm_id = config.get("swarm_id")
                            if swarm_id:
                                swarms[swarm_id] = config
                    except Exception as e:
                        log_warning(logger, f"Failed to load swarm config {filename}: {e}")
    except Exception as e:
        log_warning(logger, f"Warning: Failed to load swarm configs: {e}")

    return swarms


def main():
    """Main entry point"""
    # Run the async function
    result = asyncio.run(list_agents())
    log_success_result(logger, result)


if __name__ == "__main__":
    main()
