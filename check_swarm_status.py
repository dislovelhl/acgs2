#!/usr/bin/env python3
"""
Simple swarm status checker for ACGS-2 coordination framework
"""

import json
import os
from datetime import datetime


def check_swarm_status():
    """Check the current swarm status from storage"""

    # Path to storage directory
    storage_dir = "src/claude-flow/claude-flow/storage"

    if not os.path.exists(storage_dir):
        return

    # Load swarm configurations
    swarms = {}
    agents = []

    for filename in os.listdir(storage_dir):
        filepath = os.path.join(storage_dir, filename)

        if filename.startswith("swarm_") and filename.endswith(".json"):
            try:
                with open(filepath, "r") as f:
                    config = json.load(f)
                    swarm_id = config.get("swarm_id")
                    if swarm_id:
                        swarms[swarm_id] = config
            except Exception:
                pass

        elif filename.startswith("agent_") and filename.endswith(".json"):
            try:
                with open(filepath, "r") as f:
                    agent_info = json.load(f)
                    agents.append(agent_info)
            except Exception:
                pass

    if not swarms:
        return

    # Get the most recent swarm
    most_recent_swarm = None
    most_recent_time = 0

    for swarm_id, swarm_config in swarms.items():
        created_time = swarm_config.get("created_at", 0)
        if created_time > most_recent_time:
            most_recent_time = created_time
            most_recent_swarm = (swarm_id, swarm_config)

    if not most_recent_swarm:
        return

    swarm_id, swarm_config = most_recent_swarm

    # Count active agents
    active_agents = len([a for a in agents if a.get("status") == "active"])

    # Calculate utilization
    max_agents = swarm_config.get("max_agents", 5)
    utilization_percent = (active_agents / max_agents) * 100 if max_agents > 0 else 0

    # Build status response
    status = {
        "swarm_id": swarm_id,
        "topology": swarm_config.get("topology", "unknown"),
        "max_agents": max_agents,
        "strategy": swarm_config.get("strategy", "unknown"),
        "active_agents": active_agents,
        "utilization_percent": utilization_percent,
        "status": "active" if active_agents > 0 else "initialized",
        "created_at": datetime.fromtimestamp(most_recent_time).isoformat()
        if most_recent_time
        else None,
        "agents": agents,
    }

    result = {"success": True, "status": status}

    return result


if __name__ == "__main__":
    check_swarm_status()
