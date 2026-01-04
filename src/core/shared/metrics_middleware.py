"""
Prometheus metrics middleware for FastAPI
Constitutional Hash: cdd01ef066bc6cf2
"""

import time
from typing import Callable

from fastapi import Request
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware

# Define metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status", "service"]
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint", "service"]
)
CACHE_HITS_TOTAL = Counter("cache_hits_total", "Total cache hits", ["cache_type", "service"])
CACHE_MISSES_TOTAL = Counter("cache_misses_total", "Total cache misses", ["cache_type", "service"])


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic Prometheus metrics collection.
    """

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        endpoint = request.url.path
        method = request.method
        status = response.status_code

        # Record metrics
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status=status, service=self.service_name
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method, endpoint=endpoint, service=self.service_name
        ).observe(duration)

        return response


def instrument_app(app, service_name: str):
    """Instrument a FastAPI app with metrics."""
    app.add_middleware(MetricsMiddleware, service_name=service_name)

    # Mount metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
