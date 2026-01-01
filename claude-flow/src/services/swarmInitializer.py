#!/usr/bin/env python3
"""
Swarm Initializer for ACGS-2 Claude Flow CLI

This script initializes a swarm with specified topology and configuration.
"""

import asyncio
import json
import os
import sys
import uuid

# Add the ACGS-2 core to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../acgs2-core"))

try:
    from enhanced_agent_bus import CONSTITUTIONAL_HASH, EnhancedAgentBus
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Failed to import EnhancedAgentBus: {e}"}))
    sys.exit(1)


async def initialize_swarm(
    topology: str, max_agents: int, strategy: str, auto_spawn: bool, memory: bool, github: bool
):
    """Initialize a swarm with the given configuration"""
    try:
        # Create bus instance
        bus = EnhancedAgentBus()

        # Start the bus
        await bus.start()

        # Generate unique swarm ID
        swarm_id = f"swarm-{topology}-{uuid.uuid4().hex[:8]}"

        # Create swarm configuration
        swarm_config = {
            "swarm_id": swarm_id,
            "topology": topology,
            "max_agents": max_agents,
            "strategy": strategy,
            "auto_spawn": auto_spawn,
            "memory_enabled": memory,
            "github_enabled": github,
            "created_at": asyncio.get_event_loop().time(),
            "active_agents": 0,
            "tenant_id": "default",
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        # Store swarm configuration persistently
        await _persist_swarm_config(swarm_id, swarm_config)

        # Also store in bus memory for immediate access
        bus._swarms = getattr(bus, "_swarms", {})
        bus._swarms[swarm_id] = swarm_config

        # Initialize topology-specific setup
        if topology == "hierarchical":
            # Create coordinator agent for hierarchical topology
            coordinator_id = f"coordinator-{swarm_id}"
            await bus.register_agent(
                agent_id=coordinator_id,
                agent_type="coordinator",
                capabilities=["coordination", "orchestration", "task-distribution"],
                tenant_id="default",
            )
            swarm_config["coordinator_agent"] = coordinator_id

        elif topology == "star":
            # Similar setup for star topology
            coordinator_id = f"star-coordinator-{swarm_id}"
            await bus.register_agent(
                agent_id=coordinator_id,
                agent_type="coordinator",
                capabilities=["coordination", "centralized-control"],
                tenant_id="default",
            )
            swarm_config["coordinator_agent"] = coordinator_id

        # Initialize memory system if enabled
        if memory:
            # TODO: Initialize persistent memory storage
            swarm_config["memory_backend"] = "redis"  # Placeholder

        # Initialize GitHub integration if enabled
        if github:
            # TODO: Initialize GitHub API clients and webhooks
            swarm_config["github_webhook_url"] = f"https://api.example.com/webhooks/{swarm_id}"

        # Stop the bus
        await bus.stop()

        return {"success": True, "swarmId": swarm_id, "config": swarm_config}

    except Exception as e:
        return {"success": False, "error": f"Exception during swarm initialization: {str(e)}"}


async def _persist_swarm_config(swarm_id: str, config: dict):
    """Persist swarm configuration to file storage"""
    try:
        # Create storage directory if it doesn't exist
        storage_dir = os.path.join(os.path.dirname(__file__), "../../storage")
        os.makedirs(storage_dir, exist_ok=True)

        # Save swarm configuration
        config_file = os.path.join(storage_dir, f"swarm_{swarm_id}.json")
        with open(config_file, "w") as f:
            json.dump({**config, "persisted_at": asyncio.get_event_loop().time()}, f, indent=2)

    except Exception as e:
        # Log error but don't fail initialization
        print(f"Warning: Failed to persist swarm config: {e}", file=sys.stderr)


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
                        print(
                            f"Warning: Failed to load swarm config {filename}: {e}", file=sys.stderr
                        )
    except Exception as e:
        print(f"Warning: Failed to load swarm configs: {e}", file=sys.stderr)

    return swarms


def main():
    """Main entry point for the script"""
    if len(sys.argv) < 7:
        error_msg = (
            "Usage: python swarmInitializer.py "
            "<topology> <max_agents> <strategy> <auto_spawn> <memory> <github>"
        )
        print(json.dumps({"success": False, "error": error_msg}))
        sys.exit(1)

    topology = sys.argv[1]
    max_agents = int(sys.argv[2])
    strategy = sys.argv[3]
    auto_spawn = sys.argv[4].lower() == "true"
    memory = sys.argv[5].lower() == "true"
    github = sys.argv[6].lower() == "true"

    # Validate inputs
    valid_topologies = ["mesh", "hierarchical", "ring", "star"]
    valid_strategies = ["balanced", "parallel", "sequential"]

    if topology not in valid_topologies:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Invalid topology: {topology}. Valid: {', '.join(valid_topologies)}",
                }
            )
        )
        sys.exit(1)

    if strategy not in valid_strategies:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Invalid strategy: {strategy}. Valid: {', '.join(valid_strategies)}",
                }
            )
        )
        sys.exit(1)

    if not (1 <= max_agents <= 100):
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Invalid max_agents: {max_agents}. Must be between 1 and 100",
                }
            )
        )
        sys.exit(1)

    # Run the async function
    result = asyncio.run(
        initialize_swarm(topology, max_agents, strategy, auto_spawn, memory, github)
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
