#!/usr/bin/env python3
"""
OPA Client Module for ACGS-2 Governance Workflow

Provides a robust OPA client with connection handling, retry logic, caching,
and batch evaluation capabilities. This module handles all OPA communication
for the governance workflow orchestrator.

Usage:
    from src.opa_client import OPAClient, OPAConfig

    config = OPAConfig(
        url="http://localhost:8181",
        timeout=5,
        max_retries=3,
        retry_delay=1.0
    )
    client = OPAClient(config)

    # Health check
    if not client.health_check():
        print("OPA is not available")

    # Evaluate a policy
    result = client.evaluate_policy(
        policy_path="acgs2/constitutional/validate",
        input_data={"action_type": "read_data", ...}
    )

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

# Configure logging
logger = logging.getLogger(__name__)


# Custom exceptions for OPA client errors
class OPAConnectionError(Exception):
    """Raised when OPA service is unreachable"""

    pass


class OPAPolicyError(Exception):
    """Raised when policy evaluation fails"""

    pass


class OPATimeoutError(Exception):
    """Raised when OPA request times out"""

    pass


@dataclass
class OPAConfig:
    """Configuration for OPA client connection"""

    url: str = "http://localhost:8181"
    timeout: int = 5
    max_retries: int = 3
    retry_delay: float = 1.0


class OPAClient:
    """
    Robust OPA client with health checks, retry logic, and response caching.

    This client handles all communication with the OPA service, providing
    robust error handling, exponential backoff retry logic, and optional
    caching for improved performance.

    Attributes:
        base_url: Base URL for OPA service (e.g., http://localhost:8181)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        session: Persistent HTTP session for connection pooling
        _cache: Simple in-memory cache for policy evaluations
    """

    def __init__(self, config: OPAConfig):
        """
        Initialize OPA client with configuration.

        Args:
            config: OPAConfig instance with connection settings
        """
        self.base_url = config.url.rstrip("/")
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._cache: dict[str, dict] = {}

        logger.info(f"OPA client initialized for {self.base_url}")

    def health_check(self) -> bool:
        """
        Check if OPA service is available and healthy.

        Returns:
            True if OPA is healthy and responding, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.debug("OPA health check passed")
            else:
                logger.warning(f"OPA health check failed with status {response.status_code}")
            return is_healthy
        except requests.exceptions.RequestException as e:
            logger.error(f"OPA health check failed: {e}")
            return False

    def evaluate_policy(self, policy_path: str, input_data: dict, use_cache: bool = False) -> dict:
        """
        Evaluate a policy with input data, with optional caching and retry logic.

        Args:
            policy_path: OPA policy path (e.g., "acgs2/constitutional/validate")
            input_data: Dictionary containing the policy input
            use_cache: If True, cache the result and return cached results for
                      identical requests (default: False for governance decisions)

        Returns:
            Dictionary containing the policy evaluation result from OPA

        Raises:
            OPAConnectionError: If OPA service is unreachable
            OPATimeoutError: If the request times out
            OPAPolicyError: If policy evaluation returns an error

        Example:
            result = client.evaluate_policy(
                policy_path="acgs2/agent_actions/evaluate",
                input_data={
                    "action_type": "read_data",
                    "environment": "production",
                    "resource": "customer_data"
                }
            )
            allowed = result.get("result", {}).get("allowed", False)
        """
        # Check cache if enabled
        cache_key = self._make_cache_key(policy_path, input_data)
        if use_cache and cache_key in self._cache:
            logger.debug(f"Cache hit for policy {policy_path}")
            return self._cache[cache_key]

        # Prepare the request
        url = f"{self.base_url}/v1/data/{policy_path}"
        payload = {"input": input_data}

        # Execute with retry logic
        def _query() -> dict:
            try:
                response = self.session.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                # Cache the result if caching is enabled
                if use_cache:
                    self._cache[cache_key] = result

                return result

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Failed to connect to OPA at {self.base_url}: {e}")
                raise OPAConnectionError(
                    f"OPA service is unreachable at {self.base_url}. Please ensure OPA is running."
                ) from e

            except requests.exceptions.Timeout as e:
                logger.error(f"OPA request timed out after {self.timeout}s: {e}")
                raise OPATimeoutError(f"OPA request timed out after {self.timeout} seconds") from e

            except requests.exceptions.HTTPError as e:
                logger.error(
                    f"OPA policy evaluation failed for {policy_path}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                raise OPAPolicyError(
                    f"Policy evaluation failed: {e.response.status_code} - {e.response.text}"
                ) from e

            except requests.exceptions.RequestException as e:
                logger.error(f"OPA request failed: {e}")
                raise OPAPolicyError(f"OPA request failed: {str(e)}") from e

        # Retry with exponential backoff
        return self._retry_with_backoff(_query)

    def evaluate_policies_batch(self, evaluations: list[tuple[str, dict]]) -> list[dict]:
        """
        Batch evaluate multiple policies in sequence.

        This method evaluates multiple policies sequentially. For true parallel
        evaluation, consider using asyncio or threading.

        Args:
            evaluations: List of (policy_path, input_data) tuples

        Returns:
            List of policy evaluation results in the same order as input

        Raises:
            OPAConnectionError: If OPA service is unreachable
            OPATimeoutError: If any request times out
            OPAPolicyError: If any policy evaluation fails

        Example:
            results = client.evaluate_policies_batch([
                ("acgs2/constitutional/validate", action_request),
                ("acgs2/agent_actions/evaluate", action_request),
                ("acgs2/hitl/determine", action_request),
            ])
            constitutional_result, action_result, hitl_result = results
        """
        logger.info(f"Batch evaluating {len(evaluations)} policies")
        results = []

        for i, (policy_path, input_data) in enumerate(evaluations, 1):
            logger.debug(f"Evaluating policy {i}/{len(evaluations)}: {policy_path}")
            result = self.evaluate_policy(policy_path, input_data, use_cache=False)
            results.append(result)

        logger.info(f"Successfully evaluated {len(results)} policies")
        return results

    def clear_cache(self) -> None:
        """
        Clear the internal response cache.

        This should be called when you want to ensure fresh policy evaluations,
        such as after policy updates or at the start of a new governance workflow.
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.debug(f"Cleared {cache_size} cached policy evaluations")

    def _retry_with_backoff(self, func: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the function

        Raises:
            Exception: The last exception raised after all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (OPAConnectionError, OPATimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} retry attempts exhausted for OPA request")

        # If we get here, all retries failed
        raise last_exception  # type: ignore

    def _make_cache_key(self, policy_path: str, input_data: dict) -> str:
        """
        Generate a cache key from policy path and input data.

        Args:
            policy_path: OPA policy path
            input_data: Input data dictionary

        Returns:
            String cache key
        """
        # Simple cache key - in production, use a proper hash function
        # For now, convert input_data to sorted JSON string for consistent keys
        import json

        input_str = json.dumps(input_data, sort_keys=True)
        return f"{policy_path}:{input_str}"

    def close(self) -> None:
        """
        Close the HTTP session and release resources.

        Call this when you're done using the client to ensure proper cleanup.
        """
        self.session.close()
        logger.info("OPA client session closed")

    def __enter__(self) -> "OPAClient":
        """Support for context manager (with statement)"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cleanup when exiting context manager"""
        self.close()


# Convenience function for quick one-off evaluations
def evaluate_policy(
    policy_path: str, input_data: dict, opa_url: str = "http://localhost:8181"
) -> dict:
    """
    Convenience function for one-off policy evaluations.

    This function creates a client, evaluates the policy, and cleans up.
    For multiple evaluations, create an OPAClient instance directly.

    Args:
        policy_path: OPA policy path (e.g., "acgs2/constitutional/validate")
        input_data: Dictionary containing the policy input
        opa_url: OPA service URL (default: http://localhost:8181)

    Returns:
        Dictionary containing the policy evaluation result

    Raises:
        OPAConnectionError: If OPA service is unreachable
        OPATimeoutError: If the request times out
        OPAPolicyError: If policy evaluation fails

    Example:
        result = evaluate_policy(
            policy_path="acgs2/constitutional/validate",
            input_data={"action_type": "read_data"}
        )
    """
    config = OPAConfig(url=opa_url)
    with OPAClient(config) as client:
        return client.evaluate_policy(policy_path, input_data)
