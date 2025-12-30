"""
ACGS-2 Prometheus Metrics Instrumentation Module
Constitutional Hash: cdd01ef066bc6cf2

This module provides standardized Prometheus metrics for all ACGS-2 services.
"""

import asyncio
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# Constitutional Hash for governance validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# ============================================================================
# Metric Registration Helpers (handle duplicate registration gracefully)
# ============================================================================

# Cache for registered metrics to avoid re-registration
_METRICS_CACHE = {}


def _find_existing_metric(name: str):
    """Find an existing metric by name in the registry."""
    try:
        # Check if metric is registered by name directly
        if name in REGISTRY._names_to_collectors:
            return REGISTRY._names_to_collectors[name]

        # Also check for metric objects by their _name attribute
        for collector in REGISTRY._names_to_collectors.values():
            if hasattr(collector, "_name") and collector._name == name:
                return collector
    except Exception:
        pass
    return None


def _get_or_create_histogram(name: str, description: str, labels: list, buckets: list = None):
    """Get existing or create new histogram metric."""
    global _METRICS_CACHE
    if name in _METRICS_CACHE:
        return _METRICS_CACHE[name]

    # Check if already exists in registry
    existing = _find_existing_metric(name)
    if existing:
        _METRICS_CACHE[name] = existing
        return existing

    kwargs = {"labelnames": labels}
    if buckets:
        kwargs["buckets"] = buckets

    try:
        metric = Histogram(name, description, **kwargs)
        _METRICS_CACHE[name] = metric
        return metric
    except ValueError:
        # Race condition - try to find again
        existing = _find_existing_metric(name)
        if existing:
            _METRICS_CACHE[name] = existing
            return existing
        raise


def _get_or_create_counter(name: str, description: str, labels: list):
    """Get existing or create new counter metric."""
    global _METRICS_CACHE
    if name in _METRICS_CACHE:
        return _METRICS_CACHE[name]

    # Check if already exists in registry
    existing = _find_existing_metric(name)
    if existing:
        _METRICS_CACHE[name] = existing
        return existing

    try:
        metric = Counter(name, description, labelnames=labels)
        _METRICS_CACHE[name] = metric
        return metric
    except ValueError:
        # Race condition - try to find again
        existing = _find_existing_metric(name)
        if existing:
            _METRICS_CACHE[name] = existing
            return existing
        raise


def _get_or_create_gauge(name: str, description: str, labels: list):
    """Get existing or create new gauge metric."""
    global _METRICS_CACHE
    if name in _METRICS_CACHE:
        return _METRICS_CACHE[name]

    # Check if already exists in registry
    existing = _find_existing_metric(name)
    if existing:
        _METRICS_CACHE[name] = existing
        return existing

    try:
        metric = Gauge(name, description, labelnames=labels)
        _METRICS_CACHE[name] = metric
        return metric
    except ValueError:
        # Race condition - try to find again
        existing = _find_existing_metric(name)
        if existing:
            _METRICS_CACHE[name] = existing
            return existing
        raise


def _get_or_create_info(name: str, description: str):
    """Get existing or create new info metric."""
    global _METRICS_CACHE
    if name in _METRICS_CACHE:
        return _METRICS_CACHE[name]

    # Check if already exists in registry
    existing = _find_existing_metric(name)
    if existing:
        _METRICS_CACHE[name] = existing
        return existing

    try:
        metric = Info(name, description)
        _METRICS_CACHE[name] = metric
        return metric
    except ValueError:
        # Race condition - try to find again
        existing = _find_existing_metric(name)
        if existing:
            _METRICS_CACHE[name] = existing
            return existing
        raise


# ============================================================================
# HTTP Request Metrics
# ============================================================================

HTTP_REQUEST_DURATION = _get_or_create_histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "service"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
)

HTTP_REQUESTS_TOTAL = _get_or_create_counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "service", "status"]
)

HTTP_REQUESTS_IN_PROGRESS = _get_or_create_gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint", "service"],
)

# ============================================================================
# Constitutional Compliance Metrics
# ============================================================================

CONSTITUTIONAL_VALIDATIONS_TOTAL = _get_or_create_counter(
    "constitutional_validations_total",
    "Total constitutional validation checks",
    ["service", "result"],
)

CONSTITUTIONAL_VIOLATIONS_TOTAL = _get_or_create_counter(
    "constitutional_violations_total",
    "Total constitutional violations detected",
    ["service", "violation_type"],
)

CONSTITUTIONAL_VALIDATION_DURATION = _get_or_create_histogram(
    "constitutional_validation_duration_seconds",
    "Time spent on constitutional validation",
    ["service"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ============================================================================
# Message Bus Metrics
# ============================================================================

MESSAGE_PROCESSING_DURATION = _get_or_create_histogram(
    "message_processing_duration_seconds",
    "Message processing time in seconds",
    ["message_type", "priority"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

MESSAGES_TOTAL = _get_or_create_counter(
    "messages_total", "Total messages processed", ["message_type", "priority", "status"]
)

MESSAGE_QUEUE_DEPTH = _get_or_create_gauge(
    "message_queue_depth", "Current depth of message queue", ["queue_name", "priority"]
)

# ============================================================================
# Cache Metrics
# ============================================================================

CACHE_HITS_TOTAL = _get_or_create_counter(
    "cache_hits_total", "Total cache hits", ["cache_name", "operation"]
)

CACHE_MISSES_TOTAL = _get_or_create_counter(
    "cache_misses_total", "Total cache misses", ["cache_name", "operation"]
)

CACHE_SIZE = _get_or_create_gauge("cache_size_bytes", "Current cache size in bytes", ["cache_name"])

# ============================================================================
# Workflow Metrics
# ============================================================================

WORKFLOW_EXECUTION_DURATION = _get_or_create_histogram(
    "workflow_execution_duration_seconds",
    "Time spent executing a workflow",
    ["workflow_name", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0],
)

WORKFLOW_EXECUTIONS_TOTAL = _get_or_create_counter(
    "workflow_executions_total", "Total workflow executions", ["workflow_name", "status"]
)

WORKFLOW_STEP_DURATION = _get_or_create_histogram(
    "workflow_step_duration_seconds",
    "Time spent executing a workflow step",
    ["workflow_name", "step_name", "status"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

WORKFLOW_STEP_RETRIES_TOTAL = _get_or_create_counter(
    "workflow_step_retries_total", "Total workflow step retries", ["workflow_name", "step_name"]
)

# ============================================================================
# Service Info
# ============================================================================

SERVICE_INFO = _get_or_create_info("acgs2_service", "ACGS-2 service information")

# ============================================================================
# Decorators for Easy Instrumentation
# ============================================================================


def _fire_and_forget_metric(metric_fn: Callable, *args, **kwargs):
    """Execute a metric update without blocking the main event loop."""
    try:
        # Most Prometheus operations are fast, but we ensure they don't block
        # if the registry or collectors have overhead.
        # In a high-throughput async environment, we use create_task for non-critical monitoring.
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.call_soon(metric_fn, *args, **kwargs)
        else:
            metric_fn(*args, **kwargs)
    except Exception:
        # Metrics failures should NEVER block or crash the application
        pass


def track_request_metrics(service: str, endpoint: str):
    """
    Decorator to track HTTP request metrics.

    Usage:
        @track_request_metrics('api_gateway', '/api/v1/validate')
        async def validate_endpoint(request):
            ...
    """

    def decorator(func: Callable):
        # Pre-bind labels that don't change for this decorator instance
        # method is dynamic, so we can't fully pre-bind everything here easily
        # but we can improve the wrapper logic.

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            method = kwargs.get("method", "GET")

            # Fire-and-forget increment
            _fire_and_forget_metric(
                HTTP_REQUESTS_IN_PROGRESS.labels(
                    method=method, endpoint=endpoint, service=service
                ).inc
            )

            start_time = time.perf_counter()
            status = "200"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "500"
                raise
            finally:
                duration = time.perf_counter() - start_time
                # Fire-and-forget observation and total count
                _fire_and_forget_metric(
                    HTTP_REQUEST_DURATION.labels(
                        method=method, endpoint=endpoint, service=service
                    ).observe,
                    duration,
                )
                _fire_and_forget_metric(
                    HTTP_REQUESTS_TOTAL.labels(
                        method=method, endpoint=endpoint, service=service, status=status
                    ).inc
                )
                _fire_and_forget_metric(
                    HTTP_REQUESTS_IN_PROGRESS.labels(
                        method=method, endpoint=endpoint, service=service
                    ).dec
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            method = kwargs.get("method", "GET")

            # Fire-and-forget increment (sync version)
            _fire_and_forget_metric(
                HTTP_REQUESTS_IN_PROGRESS.labels(
                    method=method, endpoint=endpoint, service=service
                ).inc
            )

            start_time = time.perf_counter()
            status = "200"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "500"
                raise
            finally:
                duration = time.perf_counter() - start_time
                _fire_and_forget_metric(
                    HTTP_REQUEST_DURATION.labels(
                        method=method, endpoint=endpoint, service=service
                    ).observe,
                    duration,
                )
                _fire_and_forget_metric(
                    HTTP_REQUESTS_TOTAL.labels(
                        method=method, endpoint=endpoint, service=service, status=status
                    ).inc
                )
                _fire_and_forget_metric(
                    HTTP_REQUESTS_IN_PROGRESS.labels(
                        method=method, endpoint=endpoint, service=service
                    ).dec
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_constitutional_validation(service: str):
    """
    Decorator to track constitutional validation metrics.
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                _fire_and_forget_metric(
                    CONSTITUTIONAL_VALIDATIONS_TOTAL.labels(service=service, result="success").inc
                )
                return result
            except Exception as e:
                _fire_and_forget_metric(
                    CONSTITUTIONAL_VALIDATIONS_TOTAL.labels(service=service, result="failure").inc
                )
                _fire_and_forget_metric(
                    CONSTITUTIONAL_VIOLATIONS_TOTAL.labels(
                        service=service, violation_type=type(e).__name__
                    ).inc
                )
                raise
            finally:
                duration = time.perf_counter() - start_time
                _fire_and_forget_metric(
                    CONSTITUTIONAL_VALIDATION_DURATION.labels(service=service).observe, duration
                )

        return wrapper

    return decorator


def track_message_processing(message_type: str, priority: str = "normal"):
    """
    Decorator to track message processing metrics.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start_time
                _fire_and_forget_metric(
                    MESSAGE_PROCESSING_DURATION.labels(
                        message_type=message_type, priority=priority
                    ).observe,
                    duration,
                )
                _fire_and_forget_metric(
                    MESSAGES_TOTAL.labels(
                        message_type=message_type, priority=priority, status=status
                    ).inc
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start_time
                _fire_and_forget_metric(
                    MESSAGE_PROCESSING_DURATION.labels(
                        message_type=message_type, priority=priority
                    ).observe,
                    duration,
                )
                _fire_and_forget_metric(
                    MESSAGES_TOTAL.labels(
                        message_type=message_type, priority=priority, status=status
                    ).inc
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# Metrics Endpoint Helper
# ============================================================================


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


def set_service_info(
    service_name: str, version: str, constitutional_hash: str = CONSTITUTIONAL_HASH
):
    """Set service information metrics."""
    SERVICE_INFO.info(
        {
            "service_name": service_name,
            "version": version,
            "constitutional_hash": constitutional_hash,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
    )


# ============================================================================
# FastAPI Integration
# ============================================================================


def create_metrics_endpoint():
    """
    Create a FastAPI metrics endpoint.

    Usage:
        from fastapi import FastAPI
        from shared.metrics import create_metrics_endpoint

        app = FastAPI()
        app.add_api_route('/metrics', create_metrics_endpoint())
    """
    from fastapi import Response

    async def metrics_endpoint():
        return Response(content=get_metrics(), media_type=get_metrics_content_type())

    return metrics_endpoint


__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    # Metrics
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUESTS_IN_PROGRESS",
    "CONSTITUTIONAL_VALIDATIONS_TOTAL",
    "CONSTITUTIONAL_VIOLATIONS_TOTAL",
    "CONSTITUTIONAL_VALIDATION_DURATION",
    "MESSAGE_PROCESSING_DURATION",
    "MESSAGES_TOTAL",
    "MESSAGE_QUEUE_DEPTH",
    "CACHE_HITS_TOTAL",
    "CACHE_MISSES_TOTAL",
    "CACHE_SIZE",
    "SERVICE_INFO",
    "WORKFLOW_EXECUTION_DURATION",
    "WORKFLOW_EXECUTIONS_TOTAL",
    "WORKFLOW_STEP_DURATION",
    "WORKFLOW_STEP_RETRIES_TOTAL",
    # Decorators
    "track_request_metrics",
    "track_constitutional_validation",
    "track_message_processing",
    # Helpers
    "get_metrics",
    "get_metrics_content_type",
    "set_service_info",
    "create_metrics_endpoint",
]
