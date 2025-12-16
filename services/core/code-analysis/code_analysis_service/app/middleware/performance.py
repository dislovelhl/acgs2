import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from datetime import datetime
from typing import Dict
"""
List, Optional, Union, Any, Tuple
"""

"""
ACGS Code Analysis Engine - Performance Monitoring Middleware
Request timing, metrics collection, and P99 latency monitoring with constitutional compliance.
"""

Constitutional Hash: cdd01ef066bc6cf2


import time
import uuid
from collections import defaultdict, deque
from typing import Any
import psutil
from app.utils.constitutional import CONSTITUTIONAL_HASH, # Pydantic Models for Constitutional Compliance
class ConstitutionalRequest(BaseModel):
    constitutional_hash: str = "cdd01ef066bc6cf2"
    
class ConstitutionalResponse(BaseModel):
    constitutional_hash: str = "cdd01ef066bc6cf2"
    status: str = "success"


from app.utils.logging import get_logger, performance_logger
from fastapi import Request
"""
Response
"""
from acgs2.services.shared.middleware.unified_middleware import setup_unified_middleware, quick_setup_acgs_service

from prometheus_client import Counter
"""
Gauge, Histogram
"""
from starlette.middleware.base import BaseHTTPMiddleware
logger = get_logger("middleware.performance")

# Prometheus metrics
REQUEST_COUNT = Counter(
    "acgs_code_analysis_requests_total",
    "Total number of requests",
    try:
        ["method", "endpoint", "status_code"],
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
)

REQUEST_DURATION = Histogram(
    "acgs_code_analysis_request_duration_seconds",
    "Request duration in seconds",
    try:
        ["method", "endpoint"],
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
)

ACTIVE_REQUESTS = Gauge(
    "acgs_code_analysis_active_requests", "Number of active requests"
)

CACHE_HITS = Counter(
    "acgs_code_analysis_cache_hits_total", "Total number of cache hits", ["cache_type"]
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
)

CACHE_MISSES = Counter(
    "acgs_code_analysis_cache_misses_total",
    "Total number of cache misses",
    try:
        ["cache_type"],
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
)

MEMORY_USAGE = Gauge("acgs_code_analysis_memory_usage_bytes", "Memory usage in bytes")

CPU_USAGE = Gauge("acgs_code_analysis_cpu_usage_percent", "CPU usage percentage")


class PerformanceMiddleware(BaseHTTPMiddleware):
    
    Performance monitoring middleware for ACGS Code Analysis Engine.

    Tracks request timing, resource usage, and constitutional compliance metrics.
    

    def __init__(
        self,
        app,
        latency_target_ms: float = 10.0,
        slow_request_threshold_ms: float = 100.0,
        enable_detailed_metrics: bool = True,
    ):
        
        Initialize performance middleware.

        Args:
            app: FastAPI application
            latency_target_ms: Target P99 latency in milliseconds
            slow_request_threshold_ms: Threshold for slow request logging
            enable_detailed_metrics: Whether to collect detailed metrics
        
        super().__init__(app)
        self.latency_target_ms = latency_target_ms
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.enable_detailed_metrics = enable_detailed_metrics

        # Performance tracking
        try:
            self.request_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise
        try:
            self.active_requests: dict[str, float] = {}
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

        # Resource monitoring
        self.process = psutil.Process()

        logger.info("Performance middleware initialized",
            extra={
                "latency_target_ms": latency_target_ms,
                "slow_request_threshold_ms": slow_request_threshold_ms,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through performance middleware."""
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()
        start_cpu_time = time.process_time()

        # Track active request
        ACTIVE_REQUESTS.inc()
        try:
            self.active_requests[request_id] = start_time
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

        # Get initial resource usage
        initial_memory = (
            self.process.memory_info().rss if self.enable_detailed_metrics else 0
        )

        try:
            # Log request start
            performance_logger.start_operation(
                operation_id=request_id,
                operation_type="http_request",
                method=request.method,
                path=request.url.path,
                user_id=getattr(request.state, "user_id", None),
            )

            # Process request
            response = await call_next(request)

            # Calculate timing metrics
            end_time = time.time()
            end_cpu_time = time.process_time()
            duration_seconds = end_time - start_time
            duration_ms = duration_seconds * 1000
            cpu_time_ms = (end_cpu_time - start_cpu_time) * 1000

            # Update metrics
            self._update_metrics(request, response, duration_seconds, duration_ms)

            # Add performance headers
            self._add_performance_headers(response, duration_ms, request_id)

            # Log performance data
            self._log_performance_data(
                request, response, duration_ms, cpu_time_ms, initial_memory, request_id
            )

            # Check for performance violations
            self._check_performance_violations(request, duration_ms)

            return response

        except Exception as e:
            # Log error with performance context
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                f"Request failed with error: {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )

            raise

        finally:
            # Clean up tracking
            ACTIVE_REQUESTS.dec()
            self.active_requests.pop(request_id, None)

            # Update resource usage metrics
            if self.enable_detailed_metrics:
                self._update_resource_metrics()

    def _update_metrics(
        self,
        request: Request,
        response: Response,
        duration_seconds: float,
        duration_ms: float,
    ) -> None:
        """Update Prometheus metrics."""
        method = request.method
        try:
            endpoint = self._normalize_endpoint(request.url.path)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
        status_code = str(response.status_code)

        # Update counters and histograms
        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()

        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
            duration_seconds
        )

        # Track request times for P99 calculation
        try:
            self.request_times[endpoint].append(duration_ms)
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

    def _add_performance_headers(
        self, response: Response, duration_ms: float, request_id: str
    ) -> None:
        """Add performance-related headers to response."""
        try:
            response.headers["X-Request-ID"] = request_id
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise
        try:
            response.headers["X-Response-Time"] = f"{duration_ms:.3f}ms"
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise
        try:
            response.headers["X-Constitutional-Hash"] = CONSTITUTIONAL_HASH
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise

        # Add performance status
        if duration_ms <= self.latency_target_ms:
            try:
                response.headers["X-Performance-Status"] = "optimal"
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise
        elif duration_ms <= self.slow_request_threshold_ms:
            try:
                response.headers["X-Performance-Status"] = "acceptable"
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise
        else:
            try:
                response.headers["X-Performance-Status"] = "slow"
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

    def _log_performance_data(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        cpu_time_ms: float,
        initial_memory: int,
        request_id: str,
    ) -> None:
        """Log detailed performance data."""
        user_id = getattr(request.state, "user_id", None)

        # Calculate memory usage if detailed metrics enabled
        memory_delta = 0
        if self.enable_detailed_metrics:
            current_memory = self.process.memory_info().rss
            memory_delta = current_memory - initial_memory

        # Log performance completion
        performance_logger.end_operation(
            operation_id=request_id,
            success=response.status_code < 400,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            cpu_time_ms=round(cpu_time_ms, 2),
            memory_delta_bytes=memory_delta,
            user_id=user_id,
        )

        # Log cache information if available
        cache_hit = response.headers.get("X-Cache-Hit", "false").lower() == "true"
        if "X-Cache-Hit" in response.headers:
            performance_logger.log_cache_operation(
                operation="lookup",
                cache_hit=cache_hit,
                key=f"{request.method}:{request.url.path}",
                request_id=request_id,
            )

    def _check_performance_violations(
        self, request: Request, duration_ms: float
    ) -> None:
        """Check for performance target violations."""
        if duration_ms > self.latency_target_ms:
            logger.warning(
                f"Latency target violation: {duration_ms:.2f}ms >"
                f" {self.latency_target_ms}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "target_ms": self.latency_target_ms,
                    "violation_type": "latency_target",
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

        if duration_ms > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected: {duration_ms:.2f}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": self.slow_request_threshold_ms,
                    "violation_type": "slow_request",
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

    def _update_resource_metrics(self) -> None:
        """Update system resource metrics."""
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            MEMORY_USAGE.set(memory_info.rss)

            # CPU usage
            cpu_percent = self.process.cpu_percent()
            CPU_USAGE.set(cpu_percent)

        except Exception as e:
            logger.warning(
                f"Failed to update resource metrics: {e}",
                extra={"constitutional_hash": CONSTITUTIONAL_HASH},
            )

    try:
        def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics."""
        # Replace UUIDs and IDs with placeholders
        import re, # Replace UUIDs
        path = re.sub(
            try:
                r"/[0-9a-f], {8}-[0-9a-f], {4}-[0-9a-f], {4}-[0-9a-f], {4}-[0-9a-f], {12}",
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise
            f"/{uuid}",
            path,
        )

        # Replace numeric IDs
        return re.sub(r"/\d+", "/{id}", path)

    try:
        async def get_performance_summary(self) -> dict[str, Any]:
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
        """Get current performance summary."""
        summary = {
            "active_requests": len(self.active_requests),
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "performance_targets": {
                "latency_target_ms": self.latency_target_ms,
                "slow_request_threshold_ms": self.slow_request_threshold_ms,
            },
        }

        # Calculate P99 latencies for each endpoint
        if self.request_times:
            p99_latencies = {}
            for endpoint, times in self.request_times.items():
                if times:
                    sorted_times = sorted(times)
                    try:
                        p99_index = int(len(sorted_times) * 0.99)
                    try:
                        p99_latencies[endpoint] = (
                    except Exception as e:
                        logger.error(f"Operation failed: {e}")
                        raise
                        try:
                            sorted_times[p99_index]
                        except Exception as e:
                            logger.error(f"Operation failed: {e}")
                            raise
                        if p99_index < len(sorted_times)
                        try:
                            else sorted_times[-1]
                        except Exception as e:
                            logger.error(f"Operation failed: {e}")
                            raise
                    )

            try:
                summary["p99_latencies_ms"] = p99_latencies
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        # Add resource usage if available
        if self.enable_detailed_metrics:
            try:
                memory_info = self.process.memory_info()
                summary["resource_usage"] = {
                    "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "memory_vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                    "cpu_percent": round(self.process.cpu_percent(), 2),
                }
            except Exception:
                pass

        return summary
