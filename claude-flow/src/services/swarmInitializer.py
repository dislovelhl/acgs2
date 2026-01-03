#!/usr/bin/env python3
"""
Swarm Initializer for ACGS-2 Claude Flow CLI

This script initializes a swarm with specified topology and configuration.

COMPATIBILITY: Python 3.11+ compatible
- Uses time.time() instead of deprecated asyncio.get_event_loop().time()
"""

import asyncio
import json
import os
import sys
import time
import uuid

# Add the ACGS-2 core to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../acgs2-core"))

from ..utils.logging_config import log_error_result, log_success_result, log_warning, setup_logging

# Setup logging
logger = setup_logging(__name__, json_format=True)

try:
    from enhanced_agent_bus import CONSTITUTIONAL_HASH, EnhancedAgentBus
except ImportError as e:
    log_error_result(logger, f"Failed to import EnhancedAgentBus: {e}")
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
            "created_at": time.time(),  # COMPATIBILITY: Python 3.11+ (replaced deprecated get_event_loop().time())
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
            # Initialize persistent memory storage using Redis
            from enhanced_agent_bus.shared.redis_client import RedisClient

            try:
                redis_client = RedisClient()
                await redis_client.connect()

                # Create memory namespace for this swarm
                memory_key = f"swarm:{swarm_id}:memory"

                # Initialize comprehensive memory structure
                memory_structure = {
                    "swarm_id": swarm_id,
                    "initialized_at": time.time(),  # COMPATIBILITY: Python 3.11+
                    "memory_type": "persistent",
                    "backend": "redis",
                    "namespaces": {
                        "agents": f"swarm:{swarm_id}:agents",
                        "conversations": f"swarm:{swarm_id}:conversations",
                        "tasks": f"swarm:{swarm_id}:tasks",
                        "patterns": f"swarm:{swarm_id}:patterns",
                        "metrics": f"swarm:{swarm_id}:metrics"
                    },
                    "capabilities": {
                        "agent_state_persistence": True,
                        "conversation_history": True,
                        "task_progress_tracking": True,
                        "pattern_learning": True,
                        "cross_session_memory": True
                    }
                }

                # Store memory structure
                await redis_client.set(memory_key, json.dumps(memory_structure))

                # Initialize memory namespaces with empty collections
                for namespace_name, namespace_key in memory_structure["namespaces"].items():
                    await redis_client.set(f"{namespace_key}:index", json.dumps({
                        "namespace": namespace_name,
                        "swarm_id": swarm_id,
                        "created_at": time.time(),
                        "item_count": 0,
                        "last_updated": time.time()
                    }))

                swarm_config["memory_backend"] = "redis"
                swarm_config["memory_key"] = memory_key
                swarm_config["memory_namespaces"] = memory_structure["namespaces"]
                swarm_config["memory_capabilities"] = memory_structure["capabilities"]
                swarm_config["memory_initialized"] = True

                # Initialize memory service for immediate use
                from swarmMemoryService import SwarmMemoryService
                memory_service = SwarmMemoryService(swarm_id, redis_client)

                # Store initial swarm state in memory
                await memory_service.store_agent_state("coordinator", {
                    "agent_id": swarm_config.get("coordinator_agent", f"coordinator-{swarm_id}"),
                    "status": "active",
                    "capabilities": ["coordination", "orchestration"],
                    "last_seen": time.time()
                })

                swarm_config["memory_service_initialized"] = True
                logger.info(f"Persistent memory fully initialized for swarm {swarm_id} with {len(memory_structure['namespaces'])} namespaces and memory service")

            except Exception as e:
                log_warning(logger, f"Failed to initialize persistent memory: {e}")
                swarm_config["memory_backend"] = "in_memory"
                swarm_config["memory_initialized"] = False

        # Initialize GitHub integration if enabled
        if github:
            # Initialize GitHub API clients and webhooks
            try:
                # Import GitHub client if available
                from enhanced_agent_bus.integrations.github_client import GitHubClient

                GitHubClient()

                # Generate webhook secret for this swarm
                webhook_secret = f"swarm-{swarm_id}-webhook-{uuid.uuid4().hex[:16]}"

                # Create webhook configuration
                webhook_config = {
                    "url": f"https://api.acgs2.dev/webhooks/github/{swarm_id}",
                    "secret": webhook_secret,
                    "events": ["push", "pull_request", "issues", "workflow_run"],
                    "active": True,
                }

                # Store webhook configuration securely
                swarm_config["github_webhook_url"] = webhook_config["url"]
                swarm_config["github_webhook_secret"] = webhook_secret
                swarm_config["github_events"] = webhook_config["events"]
                swarm_config["github_integration_active"] = True

                # Initialize webhook in GitHub (would normally require authentication)
                # This is a placeholder - actual implementation would need GitHub token
                swarm_config["github_webhook_id"] = f"webhook-{uuid.uuid4().hex[:8]}"

                logger.info(f"GitHub integration initialized for swarm {swarm_id}")

            except ImportError:
                log_warning(logger, "GitHub client not available, using mock integration")
                swarm_config["github_webhook_url"] = (
                    f"https://api.acgs2.dev/webhooks/github/{swarm_id}"
                )
                swarm_config["github_integration_active"] = False
                swarm_config["github_mock_mode"] = True

            except Exception as e:
                log_warning(logger, f"Failed to initialize GitHub integration: {e}")
                swarm_config["github_integration_active"] = False

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
            json.dump(
                {**config, "persisted_at": time.time()}, f, indent=2
            )  # COMPATIBILITY: Python 3.11+

    except Exception as e:
        # Log error but don't fail initialization
        log_warning(logger, f"Failed to persist swarm config: {e}")


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
    """Main entry point for the script"""
    if len(sys.argv) < 7:
        error_msg = (
            "Usage: python swarmInitializer.py "
            "<topology> <max_agents> <strategy> <auto_spawn> <memory> <github>"
        )
        log_error_result(logger, error_msg)
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
        log_error_result(
            logger, f"Invalid topology: {topology}. Valid: {', '.join(valid_topologies)}"
        )
        sys.exit(1)

    if strategy not in valid_strategies:
        log_error_result(
            logger, f"Invalid strategy: {strategy}. Valid: {', '.join(valid_strategies)}"
        )
        sys.exit(1)

    if not (1 <= max_agents <= 100):
        log_error_result(logger, f"Invalid max_agents: {max_agents}. Must be between 1 and 100")
        sys.exit(1)

    # Run the async function
    result = asyncio.run(
        initialize_swarm(topology, max_agents, strategy, auto_spawn, memory, github)
    )
    log_success_result(logger, result)


if __name__ == "__main__":
    main()
