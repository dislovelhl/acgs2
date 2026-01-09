"""
ACGS-2 OPA Client - Usage Examples
Constitutional Hash: cdd01ef066bc6cf2

Examples of using the OPA client for policy evaluation and authorization.
"""

import asyncio
import logging
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import CONSTITUTIONAL_HASH  # noqa: E402
from opa_client import (  # noqa: E402
    OPAClient,
    close_opa_client,
    get_opa_client,
    initialize_opa_client,
)

logger = logging.getLogger(__name__)


async def example_basic_usage():
    """Example 1: Basic OPA client usage with context manager."""
    logger.info("\n=== Example 1: Basic Usage ===")

    async with OPAClient(mode="fallback") as client:
        # Simple policy evaluation
        input_data = {
            "agent_id": "agent_001",
            "action": "read",
            "resource": "document_123",
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        result = await client.evaluate_policy(input_data, policy_path="data.acgs.allow")

        logger.info(f"Policy evaluation result: {result['allowed']}")
        logger.info(f"Reason: {result['reason']}")
        logger.info(f"Mode: {result['metadata']['mode']}")


async def example_constitutional_validation():
    """Example 2: Constitutional validation of messages."""
    logger.info("\n=== Example 2: Constitutional Validation ===")

    async with OPAClient(mode="fallback") as client:
        # Create a message
        message = {
            "message_id": "msg_001",
            "from_agent": "agent_sender",
            "to_agent": "agent_receiver",
            "message_type": "command",
            "content": {"action": "process_data", "data": [1, 2, 3]},
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        # Validate the message
        validation_result = await client.validate_constitutional(message)

        logger.info(f"Is valid: {validation_result.is_valid}")
        if validation_result.errors:
            logger.error(f"Errors: {validation_result.errors}")
        if validation_result.warnings:
            logger.warning(f"Warnings: {validation_result.warnings}")


async def example_agent_authorization():
    """Example 3: Agent authorization checking."""
    logger.info("\n=== Example 3: Agent Authorization ===")

    async with OPAClient(mode="fallback") as client:
        # Check if agent can read a resource
        can_read = await client.check_agent_authorization(
            agent_id="agent_001",
            action="read",
            resource="sensitive_document",
            context={
                "role": "analyst",
                "clearance_level": 3,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        logger.info(f"Agent can read: {can_read}")

        # Check if agent can write to a resource
        can_write = await client.check_agent_authorization(
            agent_id="agent_001",
            action="write",
            resource="sensitive_document",
            context={
                "role": "analyst",
                "clearance_level": 3,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

        logger.info(f"Agent can write: {can_write}")


async def example_with_caching():
    """Example 4: Policy evaluation with caching."""
    logger.info("\n=== Example 4: Caching Performance ===")

    client = OPAClient(mode="fallback", enable_cache=True, cache_ttl=300)  # 5 minutes
    await client.initialize()

    input_data = {"agent_id": "agent_001", "constitutional_hash": CONSTITUTIONAL_HASH}

    # First evaluation (cache miss)
    start = time.time()
    result1 = await client.evaluate_policy(input_data, "data.acgs.allow")
    time1 = time.time() - start

    # Second evaluation (cache hit)
    start = time.time()
    result2 = await client.evaluate_policy(input_data, "data.acgs.allow")
    time2 = time.time() - start

    logger.info(f"First evaluation: {time1 * 1000:.2f}ms")
    logger.info(f"Second evaluation (cached): {time2 * 1000:.2f}ms")
    logger.info(f"Speedup: {time1 / time2:.1f}x")

    # Print cache statistics
    stats = client.get_stats()
    logger.info(f"Cache size: {stats['cache_size']} entries")

    await client.close()


async def example_http_mode():
    """Example 5: Using HTTP mode with OPA server."""
    logger.info("\n=== Example 5: HTTP Mode (requires OPA server) ===")

    # This example requires an OPA server running at localhost:8181
    client = OPAClient(opa_url="http://localhost:8181", mode="http", timeout=5.0)

    try:
        await client.initialize()

        # Check health
        health = await client.health_check()
        logger.info(f"OPA server health: {health['status']}")

        if health["status"] == "healthy":
            # Evaluate a policy
            input_data = {
                "agent_id": "agent_001",
                "action": "read",
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }

            result = await client.evaluate_policy(input_data, policy_path="data.acgs.allow")

            logger.info(f"Policy result: {result['allowed']}")
        else:
            logger.info("OPA server not available, skipping HTTP mode example")

    except Exception as e:
        logger.info(f"HTTP mode not available: {e}")
        logger.info("This is expected if OPA server is not running")
    finally:
        await client.close()


async def example_load_policy():
    """Example 6: Loading a policy into OPA."""
    logger.info("\n=== Example 6: Loading Policy (HTTP mode) ===")

    client = OPAClient(opa_url="http://localhost:8181", mode="http")

    try:
        await client.initialize()

        # Define a Rego policy
        policy_content = """
        package acgs.example

        default allow = false

        # Allow if agent has valid constitutional hash
        allow {
            input.constitutional_hash == "cdd01ef066bc6cf2"
            input.action == "read"
        }

        # Allow admins to do anything
        allow {
            input.role == "admin"
            input.constitutional_hash == "cdd01ef066bc6cf2"
        }
        """

        # Load the policy
        success = await client.load_policy("example_policy", policy_content)

        if success:
            logger.info("Policy loaded successfully")

            # Test the policy
            input_data = {"action": "read", "constitutional_hash": CONSTITUTIONAL_HASH}

            result = await client.evaluate_policy(input_data, policy_path="data.acgs.example.allow")

            logger.info(f"Policy evaluation: {result['allowed']}")
        else:
            logger.error("Failed to load policy (OPA server may not be running)")

    except Exception as e:
        logger.info(f"Policy loading not available: {e}")
    finally:
        await client.close()


async def example_global_client():
    """Example 7: Using the global client singleton."""
    logger.info("\n=== Example 7: Global Client Singleton ===")

    # Initialize global client
    await initialize_opa_client(opa_url="http://localhost:8181", mode="fallback")

    # Use global client functions

    client = get_opa_client()

    input_data = {"agent_id": "agent_001", "constitutional_hash": CONSTITUTIONAL_HASH}

    result = await client.evaluate_policy(input_data, "data.acgs.allow")
    logger.info(f"Evaluation result: {result['allowed']}")

    # Clean up
    await close_opa_client()


async def example_batch_evaluations():
    """Example 8: Batch policy evaluations."""
    logger.info("\n=== Example 8: Batch Evaluations ===")

    async with OPAClient(mode="fallback", enable_cache=True) as client:
        # Create multiple evaluation tasks
        agents = ["agent_001", "agent_002", "agent_003", "agent_004"]

        tasks = [
            client.check_agent_authorization(
                agent_id=agent,
                action="read",
                resource="document_123",
                context={"constitutional_hash": CONSTITUTIONAL_HASH},
            )
            for agent in agents
        ]

        # Execute all evaluations concurrently
        results = await asyncio.gather(*tasks)

        # Print results
        for agent, authorized in zip(agents, results, strict=True):
            logger.info(f"{agent}: {'Authorized' if authorized else 'Denied'}")


async def example_error_handling():
    """Example 9: Error handling and fallback behavior."""
    logger.error("\n=== Example 9: Error Handling ===")

    async with OPAClient(mode="fallback") as client:
        # Test with invalid constitutional hash
        invalid_message = {
            "message_id": "msg_002",
            "from_agent": "agent_sender",
            "to_agent": "agent_receiver",
            "constitutional_hash": "invalid_hash_123",
        }

        validation_result = await client.validate_constitutional(invalid_message)

        logger.info(f"Is valid: {validation_result.is_valid}")
        if not validation_result.is_valid:
            logger.error(f"Errors: {validation_result.errors}")

        # The client should handle errors gracefully
        try:
            result = await client.evaluate_policy(invalid_message, policy_path="data.acgs.allow")
            logger.info(f"Evaluation with invalid hash: {result['allowed']}")
            logger.info(f"Reason: {result['reason']}")
        except Exception as e:
            logger.error(f"Exception caught: {e}")


async def example_statistics():
    """Example 10: Client statistics and monitoring."""
    logger.info("\n=== Example 10: Statistics ===")

    async with OPAClient(mode="fallback", enable_cache=True) as client:
        # Perform some evaluations
        for i in range(5):
            await client.evaluate_policy(
                {"agent_id": f"agent_{i}", "constitutional_hash": CONSTITUTIONAL_HASH},
                "data.acgs.allow",
            )

        # Get statistics
        stats = client.get_stats()
        logger.info(f"Mode: {stats['mode']}")
        logger.info(f"Cache enabled: {stats['cache_enabled']}")
        logger.info(f"Cache size: {stats['cache_size']}")
        logger.info(f"Cache backend: {stats['cache_backend']}")

        # Get health status
        health = await client.health_check()
        logger.info(f"Health status: {health['status']}")


async def main():
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("ACGS-2 OPA Client Examples")
    logger.info("Constitutional Hash: cdd01ef066bc6cf2")
    logger.info("=" * 60)

    examples = [
        example_basic_usage,
        example_constitutional_validation,
        example_agent_authorization,
        example_with_caching,
        example_http_mode,
        example_load_policy,
        example_global_client,
        example_batch_evaluations,
        example_error_handling,
        example_statistics,
    ]

    for example in examples:
        try:
            await example()
        except Exception as e:
            logger.error(f"Error in {example.__name__}: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("Examples completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
