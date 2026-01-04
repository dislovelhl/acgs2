"""
OpenTelemetry Configuration for ACGS-2 Services
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def init_otel(service_name: str, app: Optional[Any] = None, export_to_console: bool = False) -> None:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service.
        app: Optional FastAPI application to instrument.
        export_to_console: Whether to export spans to console (useful for local development).
    """
    resource = Resource(attributes={"service.name": service_name, "service.version": "1.0.0"})

    provider = TracerProvider(resource=resource)

    if export_to_console:
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor().instrument_app(app)


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID if a span is active."""
    span = trace.get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().trace_id, "032x")
    return None
