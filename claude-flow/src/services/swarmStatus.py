#!/usr/bin/env python3
"""
Swarm Status Checker for ACGS-2 Claude Flow CLI

This script retrieves the current status of the active swarm.
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


async def get_swarm_status():
    """Get the current status of the active swarm"""
    try:
        # Load persisted swarm configurations
        swarms = await _load_swarm_configs()

        if not swarms:
            return {"success": True, "status": {}}

        # For now, return the most recently created swarm
        # In a production system, you'd want to handle multiple swarms
        most_recent_swarm = None
        most_recent_time = 0

        for swarm_id, swarm_config in swarms.items():
            created_time = swarm_config.get("created_at", 0)
            if created_time > most_recent_time:
                most_recent_time = created_time
                most_recent_swarm = (swarm_id, swarm_config)

        if not most_recent_swarm:
            return {"success": True, "status": {}}

        swarm_id, swarm_config = most_recent_swarm

        # Get active agents count
        active_agents = 0
        try:
            # Try to query agent registry from bus
            bus = EnhancedAgentBus()
            await bus.start()

            if hasattr(bus, "_registry") and bus._registry:
                # Get actual agent count from registry
                registry_agents = await bus._registry.list_agents()
                active_agents = len(registry_agents)
            else:
                # Fallback: count coordinator agents
                active_agents = 1 if swarm_config.get("coordinator_agent") else 0

            await bus.stop()

        except Exception:
            # Fallback to coordinator count
            active_agents = 1 if swarm_config.get("coordinator_agent") else 0

        # Calculate utilization
        max_agents = swarm_config.get("max_agents", 8)
        utilization_percent = (active_agents / max_agents) * 100 if max_agents > 0 else 0

        # Build status response
        status = {
            **swarm_config,
            "active_agents": active_agents,
            "utilization_percent": utilization_percent,
            "status": "active" if active_agents > 0 else "initialized",
        }

        return {"success": True, "status": status}

    except Exception as e:
        return {"success": False, "error": f"Exception getting swarm status: {str(e)}"}


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
        log_warning(logger, f"Failed to load swarm configs: {e}")

    return swarms


def main():
    """Main entry point"""
    # Run the async function
    result = asyncio.run(get_swarm_status())
    log_success_result(logger, result)


if __name__ == "__main__":
    main()
