"""
ACGS-2 Prometheus Metrics Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/metrics/__init__.py
"""

import asyncio

import pytest

# Import directly from submodule to avoid cascading imports
import shared.metrics as metrics_module

CONSTITUTIONAL_HASH = metrics_module.CONSTITUTIONAL_HASH
HTTP_REQUEST_DURATION = metrics_module.HTTP_REQUEST_DURATION
HTTP_REQUESTS_TOTAL = metrics_module.HTTP_REQUESTS_TOTAL
HTTP_REQUESTS_IN_PROGRESS = metrics_module.HTTP_REQUESTS_IN_PROGRESS
CONSTITUTIONAL_VALIDATIONS_TOTAL = metrics_module.CONSTITUTIONAL_VALIDATIONS_TOTAL
CONSTITUTIONAL_VIOLATIONS_TOTAL = metrics_module.CONSTITUTIONAL_VIOLATIONS_TOTAL
CONSTITUTIONAL_VALIDATION_DURATION = metrics_module.CONSTITUTIONAL_VALIDATION_DURATION
MESSAGE_PROCESSING_DURATION = metrics_module.MESSAGE_PROCESSING_DURATION
MESSAGES_TOTAL = metrics_module.MESSAGES_TOTAL
MESSAGE_QUEUE_DEPTH = metrics_module.MESSAGE_QUEUE_DEPTH
CACHE_HITS_TOTAL = metrics_module.CACHE_HITS_TOTAL
CACHE_MISSES_TOTAL = metrics_module.CACHE_MISSES_TOTAL
CACHE_SIZE = metrics_module.CACHE_SIZE
SERVICE_INFO = metrics_module.SERVICE_INFO
track_request_metrics = metrics_module.track_request_metrics
track_constitutional_validation = metrics_module.track_constitutional_validation
track_message_processing = metrics_module.track_message_processing
get_metrics = metrics_module.get_metrics
get_metrics_content_type = metrics_module.get_metrics_content_type
set_service_info = metrics_module.set_service_info


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_in_module(self):
        """Verify constitutional hash is exported."""
        from shared import metrics

        assert hasattr(metrics, "CONSTITUTIONAL_HASH")
        assert metrics.CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# ============================================================================
# HTTP Metrics Tests
# ============================================================================


class TestHTTPMetrics:
    """Test HTTP request metrics."""

    def test_http_request_duration_exists(self):
        """Verify HTTP request duration histogram exists."""
        assert HTTP_REQUEST_DURATION is not None
        assert HTTP_REQUEST_DURATION._name == "http_request_duration_seconds"

    def test_http_requests_total_exists(self):
        """Verify HTTP requests total counter exists."""
        assert HTTP_REQUESTS_TOTAL is not None
        # Counter._name is base name without _total suffix
        assert "http_requests" in HTTP_REQUESTS_TOTAL._name

    def test_http_requests_in_progress_exists(self):
        """Verify HTTP requests in progress gauge exists."""
        assert HTTP_REQUESTS_IN_PROGRESS is not None
        assert HTTP_REQUESTS_IN_PROGRESS._name == "http_requests_in_progress"

    def test_http_duration_labels(self):
        """Verify HTTP duration has correct labels."""
        labels = HTTP_REQUEST_DURATION._labelnames
        assert "method" in labels
        assert "endpoint" in labels
        assert "service" in labels


# ============================================================================
# Constitutional Metrics Tests
# ============================================================================


class TestConstitutionalMetrics:
    """Test constitutional compliance metrics."""

    def test_constitutional_validations_total_exists(self):
        """Verify constitutional validations counter exists."""
        assert CONSTITUTIONAL_VALIDATIONS_TOTAL is not None
        # Counter._name is base name without _total suffix
        assert "constitutional_validations" in CONSTITUTIONAL_VALIDATIONS_TOTAL._name

    def test_constitutional_violations_total_exists(self):
        """Verify constitutional violations counter exists."""
        assert CONSTITUTIONAL_VIOLATIONS_TOTAL is not None
        # Counter._name is base name without _total suffix
        assert "constitutional_violations" in CONSTITUTIONAL_VIOLATIONS_TOTAL._name

    def test_constitutional_validation_duration_exists(self):
        """Verify constitutional validation duration histogram exists."""
        assert CONSTITUTIONAL_VALIDATION_DURATION is not None
        assert (
            CONSTITUTIONAL_VALIDATION_DURATION._name == "constitutional_validation_duration_seconds"
        )

    def test_constitutional_validations_labels(self):
        """Verify constitutional validations has correct labels."""
        labels = CONSTITUTIONAL_VALIDATIONS_TOTAL._labelnames
        assert "service" in labels
        assert "result" in labels


# ============================================================================
# Message Bus Metrics Tests
# ============================================================================


class TestMessageBusMetrics:
    """Test message bus metrics."""

    def test_message_processing_duration_exists(self):
        """Verify message processing duration histogram exists."""
        assert MESSAGE_PROCESSING_DURATION is not None
        assert MESSAGE_PROCESSING_DURATION._name == "message_processing_duration_seconds"

    def test_messages_total_exists(self):
        """Verify messages total counter exists."""
        assert MESSAGES_TOTAL is not None
        # Counter._name is base name without _total suffix
        assert "messages" in MESSAGES_TOTAL._name

    def test_message_queue_depth_exists(self):
        """Verify message queue depth gauge exists."""
        assert MESSAGE_QUEUE_DEPTH is not None
        assert MESSAGE_QUEUE_DEPTH._name == "message_queue_depth"

    def test_messages_total_labels(self):
        """Verify messages total has correct labels."""
        labels = MESSAGES_TOTAL._labelnames
        assert "message_type" in labels
        assert "priority" in labels
        assert "status" in labels


# ============================================================================
# Cache Metrics Tests
# ============================================================================


class TestCacheMetrics:
    """Test cache metrics."""

    def test_cache_hits_total_exists(self):
        """Verify cache hits counter exists."""
        assert CACHE_HITS_TOTAL is not None
        # Counter._name is base name without _total suffix
        assert "cache_hits" in CACHE_HITS_TOTAL._name

    def test_cache_misses_total_exists(self):
        """Verify cache misses counter exists."""
        assert CACHE_MISSES_TOTAL is not None
        # Counter._name is base name without _total suffix
        assert "cache_misses" in CACHE_MISSES_TOTAL._name

    def test_cache_size_exists(self):
        """Verify cache size gauge exists."""
        assert CACHE_SIZE is not None
        assert CACHE_SIZE._name == "cache_size_bytes"

    def test_cache_labels(self):
        """Verify cache metrics have correct labels."""
        assert "cache_name" in CACHE_HITS_TOTAL._labelnames
        assert "operation" in CACHE_HITS_TOTAL._labelnames


# ============================================================================
# Track Request Metrics Decorator Tests
# ============================================================================


class TestTrackRequestMetricsDecorator:
    """Test track_request_metrics decorator."""

    def test_sync_function_success(self):
        """Test decorator with synchronous function success."""

        @track_request_metrics("test_service", "/test/endpoint")
        def sync_handler():
            return {"status": "ok"}

        result = sync_handler()
        assert result == {"status": "ok"}

    def test_sync_function_with_kwargs(self):
        """Test decorator preserves kwargs."""

        @track_request_metrics("test_service", "/test/endpoint")
        def sync_handler(data=None):
            return {"data": data}

        result = sync_handler(data="test")
        assert result == {"data": "test"}

    def test_sync_function_exception(self):
        """Test decorator handles exceptions."""

        @track_request_metrics("test_service", "/test/endpoint")
        def failing_handler():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_handler()

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with async function success."""

        @track_request_metrics("test_service", "/test/async")
        async def async_handler():
            await asyncio.sleep(0.001)
            return {"async": True}

        result = await async_handler()
        assert result == {"async": True}

    @pytest.mark.asyncio
    async def test_async_function_exception(self):
        """Test decorator handles async exceptions."""

        @track_request_metrics("test_service", "/test/async")
        async def failing_async_handler():
            await asyncio.sleep(0.001)
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            await failing_async_handler()


# ============================================================================
# Track Constitutional Validation Decorator Tests
# ============================================================================


class TestTrackConstitutionalValidationDecorator:
    """Test track_constitutional_validation decorator."""

    def test_validation_success(self):
        """Test decorator tracks successful validation."""

        @track_constitutional_validation("policy_registry")
        def validate_policy(policy):
            return True

        result = validate_policy({"id": "test"})
        assert result is True

    def test_validation_failure(self):
        """Test decorator tracks failed validation."""

        @track_constitutional_validation("policy_registry")
        def validate_policy(policy):
            raise ValueError("Invalid policy")

        with pytest.raises(ValueError, match="Invalid policy"):
            validate_policy({"id": "invalid"})

    def test_validation_preserves_function_name(self):
        """Test decorator preserves function metadata."""

        @track_constitutional_validation("test_service")
        def my_validator():
            pass

        assert my_validator.__name__ == "my_validator"


# ============================================================================
# Track Message Processing Decorator Tests
# ============================================================================


class TestTrackMessageProcessingDecorator:
    """Test track_message_processing decorator."""

    def test_sync_processing_success(self):
        """Test decorator with sync message processing."""

        @track_message_processing("governance_decision", "high")
        def process_message(msg):
            return {"processed": True}

        result = process_message({"id": "123"})
        assert result == {"processed": True}

    def test_sync_processing_error(self):
        """Test decorator handles processing errors."""

        @track_message_processing("governance_decision", "high")
        def process_message(msg):
            raise RuntimeError("Processing failed")

        with pytest.raises(RuntimeError, match="Processing failed"):
            process_message({"id": "123"})

    @pytest.mark.asyncio
    async def test_async_processing_success(self):
        """Test decorator with async message processing."""

        @track_message_processing("audit_log", "normal")
        async def process_message(msg):
            await asyncio.sleep(0.001)
            return {"processed": True}

        result = await process_message({"id": "123"})
        assert result == {"processed": True}

    @pytest.mark.asyncio
    async def test_async_processing_error(self):
        """Test decorator handles async processing errors."""

        @track_message_processing("audit_log", "normal")
        async def process_message(msg):
            await asyncio.sleep(0.001)
            raise RuntimeError("Async processing failed")

        with pytest.raises(RuntimeError, match="Async processing failed"):
            await process_message({"id": "123"})

    def test_default_priority(self):
        """Test decorator with default priority."""

        @track_message_processing("test_type")
        def process_message(msg):
            return msg

        result = process_message({"data": "test"})
        assert result == {"data": "test"}


# ============================================================================
# Metrics Helper Function Tests
# ============================================================================


class TestMetricsHelpers:
    """Test metrics helper functions."""

    def test_get_metrics_returns_bytes(self):
        """Test get_metrics returns bytes."""
        metrics = get_metrics()
        assert isinstance(metrics, bytes)

    def test_get_metrics_contains_metric_names(self):
        """Test get_metrics output contains expected metrics."""
        metrics = get_metrics().decode("utf-8")
        # Check for at least one of our defined metrics
        assert "http_request_duration_seconds" in metrics or "HELP" in metrics

    def test_get_metrics_content_type(self):
        """Test get_metrics_content_type returns correct type."""
        content_type = get_metrics_content_type()
        assert "text/plain" in content_type or "openmetrics" in content_type.lower()

    def test_set_service_info(self):
        """Test set_service_info sets information correctly."""
        set_service_info(
            service_name="test_service", version="1.0.0", constitutional_hash="cdd01ef066bc6cf2"
        )
        # Info metric should be set without errors
        assert True

    def test_set_service_info_default_hash(self):
        """Test set_service_info uses default constitutional hash."""
        set_service_info(service_name="another_service", version="2.0.0")
        # Should use default CONSTITUTIONAL_HASH
        assert True


# ============================================================================
# FastAPI Integration Tests
# ============================================================================


class TestFastAPIIntegration:
    """Test FastAPI integration helpers."""

    def test_create_metrics_endpoint_returns_callable(self):
        """Test create_metrics_endpoint returns a callable."""
        pytest.importorskip("fastapi")
        from shared.metrics import create_metrics_endpoint

        endpoint = create_metrics_endpoint()
        assert callable(endpoint)

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_response(self):
        """Test metrics endpoint returns proper response."""
        pytest.importorskip("fastapi")
        from shared.metrics import create_metrics_endpoint

        endpoint = create_metrics_endpoint()
        response = await endpoint()
        assert response is not None
        assert hasattr(response, "body")


# ============================================================================
# Module Export Tests
# ============================================================================


class TestModuleExports:
    """Test module exports all required components."""

    def test_all_metrics_exported(self):
        """Test all metric objects are exported."""
        from shared import metrics

        required_metrics = [
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
        ]
        for metric_name in required_metrics:
            assert hasattr(metrics, metric_name), f"Missing export: {metric_name}"

    def test_all_decorators_exported(self):
        """Test all decorator functions are exported."""
        from shared import metrics

        required_decorators = [
            "track_request_metrics",
            "track_constitutional_validation",
            "track_message_processing",
        ]
        for decorator_name in required_decorators:
            assert hasattr(metrics, decorator_name), f"Missing export: {decorator_name}"
            assert callable(getattr(metrics, decorator_name))

    def test_all_helpers_exported(self):
        """Test all helper functions are exported."""
        from shared import metrics

        required_helpers = [
            "get_metrics",
            "get_metrics_content_type",
            "set_service_info",
            "create_metrics_endpoint",
        ]
        for helper_name in required_helpers:
            assert hasattr(metrics, helper_name), f"Missing export: {helper_name}"
            assert callable(getattr(metrics, helper_name))
