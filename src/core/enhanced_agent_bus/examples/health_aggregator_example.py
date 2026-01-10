"""
ACGS-2 Enhanced Agent Bus - Health Aggregator Usage Example
Constitutional Hash: cdd01ef066bc6cf2

Example demonstrating how to use the health aggregator service.
"""

import asyncio
import logging

from core.enhanced_agent_bus.health_aggregator import (
    HealthAggregator,
    HealthAggregatorConfig,
    SystemHealthStatus,
    get_health_aggregator,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def alert_on_degraded(report):
    """Example callback: Alert when system becomes degraded."""
    if report.status == SystemHealthStatus.DEGRADED:
        logger.warning(
            f"🟡 ALERT: System degraded! "
            f"Health score: {report.health_score:.2f}, "
            f"Degraded services: {report.degraded_services}"
        )


async def alert_on_critical(report):
    """Example callback: Alert when system becomes critical."""
    if report.status == SystemHealthStatus.CRITICAL:
        logger.error(
            f"🔴 CRITICAL ALERT: System critical! "
            f"Health score: {report.health_score:.2f}, "
            f"Critical services: {report.critical_services}"
        )


async def main():
    """Main example demonstrating health aggregator usage."""

    # Create configuration
    config = HealthAggregatorConfig(
        enabled=True,
        history_window_minutes=5,
        health_check_interval_seconds=2.0,  # Check every 2 seconds
        degraded_threshold=0.7,
        critical_threshold=0.5,
    )

    # Create health aggregator
    aggregator = HealthAggregator(config=config)

    # Register callbacks for health changes
    aggregator.on_health_change(alert_on_degraded)
    aggregator.on_health_change(alert_on_critical)

    # Start monitoring
    await aggregator.start()
    logger.info("Health aggregator started")

    try:
        # Monitor for 30 seconds
        for i in range(15):
            await asyncio.sleep(2)

            # Get current health
            health = aggregator.get_system_health()

            # Log health status
            status_emoji = {
                SystemHealthStatus.HEALTHY: "🟢",
                SystemHealthStatus.DEGRADED: "🟡",
                SystemHealthStatus.CRITICAL: "🔴",
                SystemHealthStatus.UNKNOWN: "⚪",
            }

            logger.info(
                f"{status_emoji.get(health.status, '❓')} System Health: {health.status.value} "
                f"(score: {health.health_score:.2f}) - "
                f"Breakers: {health.total_breakers} total, "
                f"{health.closed_breakers} closed, "
                f"{health.half_open_breakers} half-open, "
                f"{health.open_breakers} open"
            )

            # Show metrics every 10 seconds
            if i % 5 == 0:
                metrics = aggregator.get_metrics()
                logger.info(
                    f"📊 Metrics: {metrics['snapshots_collected']} snapshots, "
                    f"{metrics['callbacks_fired']} callbacks, "
                    f"{metrics['history_size']} history entries"
                )

        # Get health history
        history = aggregator.get_health_history(window_minutes=5)
        logger.info(f"📈 Health history: {len(history)} snapshots in last 5 minutes")

        # Print history summary
        if history:
            avg_score = sum(s.health_score for s in history) / len(history)
            logger.info(f"📊 Average health score: {avg_score:.3f}")

            # Show status distribution
            status_counts = {}
            for snapshot in history:
                status = snapshot.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            logger.info(f"📊 Status distribution: {status_counts}")

    finally:
        # Stop aggregator
        await aggregator.stop()
        logger.info("Health aggregator stopped")


async def example_with_custom_breakers():
    """Example showing custom circuit breaker registration."""
    from core.enhanced_agent_bus.health_aggregator import CIRCUIT_BREAKER_AVAILABLE

    if not CIRCUIT_BREAKER_AVAILABLE:
        logger.warning("Circuit breaker support not available")
        return

    # Import circuit breaker
    import pybreaker

    # Create custom circuit breakers
    class MockCircuitBreaker:
        def __init__(self, state):
            self.current_state = state
            self.fail_counter = 0
            self.success_counter = 0

    # Create aggregator
    aggregator = HealthAggregator()

    # Register custom circuit breakers
    breaker1 = MockCircuitBreaker(pybreaker.STATE_CLOSED)
    breaker2 = MockCircuitBreaker(pybreaker.STATE_HALF_OPEN)
    breaker3 = MockCircuitBreaker(pybreaker.STATE_OPEN)

    aggregator.register_circuit_breaker("database_service", breaker1)
    aggregator.register_circuit_breaker("cache_service", breaker2)
    aggregator.register_circuit_breaker("api_gateway", breaker3)

    # Get health report
    health = aggregator.get_system_health()

    logger.info("System health with custom breakers:")
    logger.info(f"  Status: {health.status.value}")
    logger.info(f"  Health score: {health.health_score:.2f}")
    logger.info(f"  Circuit details: {health.circuit_details}")
    logger.info(f"  Degraded services: {health.degraded_services}")
    logger.info(f"  Critical services: {health.critical_services}")


async def example_singleton_usage():
    """Example using global singleton pattern."""

    # Get global health aggregator singleton
    aggregator = get_health_aggregator()

    # Start monitoring
    await aggregator.start()
    logger.info("Global health aggregator started")

    # Monitor for 10 seconds
    await asyncio.sleep(10)

    # Get health report
    health = aggregator.get_system_health()
    logger.info(f"Global health status: {health.status.value}")

    # Stop monitoring
    await aggregator.stop()
    logger.info("Global health aggregator stopped")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ACGS-2 Health Aggregator Examples")
    logger.info("Constitutional Hash: cdd01ef066bc6cf2")
    logger.info("=" * 60)

    # Run main example
    logger.info("\n--- Example 1: Basic Health Monitoring ---")
    asyncio.run(main())

    logger.info("\n--- Example 2: Custom Circuit Breakers ---")
    asyncio.run(example_with_custom_breakers())

    logger.info("\n--- Example 3: Singleton Usage ---")
    asyncio.run(example_singleton_usage())

    logger.info("\n" + "=" * 60)
    logger.info("Examples completed")
    logger.info("=" * 60)
