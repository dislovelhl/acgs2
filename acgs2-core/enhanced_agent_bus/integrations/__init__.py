"""
ACGS-2 Enhanced Agent Bus Integrations Module
Constitutional Hash: cdd01ef066bc6cf2

This module provides integration clients for connecting the Enhanced Agent Bus
to external services. These clients handle the communication, error handling,
and data transformation needed to interact with external systems.

Available Integrations:
- MLGovernanceClient: Client for the Adaptive Learning Engine service,
  enabling real-time governance model training via outcome reporting.

Usage:
    from enhanced_agent_bus.integrations import MLGovernanceClient

    # Initialize the client
    client = MLGovernanceClient(base_url="http://adaptive-learning-engine:8001")

    # Report governance outcomes for model training
    await client.report_outcome(
        features={"action": "deploy", "resource": "production"},
        label=True,  # Outcome was approved
        weight=1.0,
    )

Design Principles:
- All clients use async HTTP to avoid blocking the main event loop
- Circuit breaker pattern for resilience against service failures
- Graceful degradation when external services are unavailable
- Comprehensive error handling with detailed logging
- Retry logic with exponential backoff for transient failures
"""

import os

# Constitutional hash for governance validation
CONSTITUTIONAL_HASH = os.environ.get("CONSTITUTIONAL_HASH", "cdd01ef066bc6cf2")

# Imports will be added as integration clients are implemented
# from .ml_governance import MLGovernanceClient, MLGovernanceConfig

__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    # Integration clients (to be added in subtask-8-2)
    # "MLGovernanceClient",
    # "MLGovernanceConfig",
]
