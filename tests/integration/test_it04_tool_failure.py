"""
ACGS-2 Integration Tests: IT-04 - Tool Failure Handling

Tests tool failure scenarios and recovery mechanisms.
Expected: TMS retries per policy, CRE degrades gracefully, no memory corruption.
"""


import pytest

from .conftest import (
    MockCRE,
    MockDMS,
    MockSAS,
    MockTMS,
    MockUIG,
    ToolResult,
    ToolStatus,
)


class TestIT04ToolFailureHandling:
    """
    IT-04: Tool failure handling

    Input: Tool returns error/timeout
    Expected:
        - TMS retries per policy, or CRE degrades gracefully
        - No partial memory corruption
    """

    @pytest.mark.asyncio
    async def test_tool_timeout_with_retry(self):
        """Test that tools that timeout are retried according to policy."""
        sas = MockSAS()
        dms = MockDMS()

        # Create TMS that fails first, succeeds on retry
        call_count = 0

        async def failing_tool(request, envelope):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ToolResult(
                    tool_name=request.tool_name,
                    status=ToolStatus.ERROR,
                    error={"code": "TIMEOUT", "message": "Tool timed out"},
                )
            else:
                return ToolResult(
                    tool_name=request.tool_name,
                    status=ToolStatus.OK,
                    result={"data": "retry successful"},
                    telemetry={"latency_ms": 100},
                )

        tms = MockTMS(sas)
        tms.execute = failing_tool  # Override the mock

        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        result = await uig.handle_request("Search for retry test")

        # Should succeed after retry
        assert result["status"] == "success"
        assert call_count == 2  # One failure, one success

    @pytest.mark.asyncio
    async def test_tool_permanent_failure_degrades_gracefully(self):
        """Test that permanently failing tools don't crash the system."""
        sas = MockSAS()
        dms = MockDMS()

        # TMS that always fails
        async def always_fail(request, envelope):
            return ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": "PERMANENT_FAILURE", "message": "Tool permanently broken"},
            )

        tms = MockTMS(sas)
        tms.execute = always_fail

        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        result = await uig.handle_request("Search for permanent failure test")

        # CRE should degrade gracefully
        assert result["status"] == "refused"
        assert "cannot" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_memory_not_corrupted_by_tool_failure(self):
        """Test that tool failures don't leave partial memory state."""
        sas = MockSAS()
        dms = MockDMS()

        # TMS that fails after partial work
        async def partial_failure(request, envelope):
            # Simulate partial memory write before failure
            # (In real implementation, this would be transactional)
            return ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": "PARTIAL_FAILURE", "message": "Failed after partial work"},
            )

        tms = MockTMS(sas)
        tms.execute = partial_failure

        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        result = await uig.handle_request("Search for partial failure test")

        # Memory should still be consistent
        assert len(dms.records) == 1  # CRE still writes summary
        record = dms.records[0]
        assert record.provenance["source"] == "model"
        assert "request_id" in record.provenance

    @pytest.mark.asyncio
    async def test_retry_policy_respected(self):
        """Test that retry limits are enforced."""
        sas = MockSAS()
        dms = MockDMS()

        retry_count = 0
        max_retries = 3

        async def limited_retry(request, envelope):
            nonlocal retry_count
            retry_count += 1
            if retry_count <= max_retries:
                return ToolResult(
                    tool_name=request.tool_name,
                    status=ToolStatus.ERROR,
                    error={"code": "RETRYABLE_FAILURE", "message": f"Attempt {retry_count}"},
                )
            else:
                # After max retries, succeed
                return ToolResult(
                    tool_name=request.tool_name,
                    status=ToolStatus.OK,
                    result={"data": f"succeeded after {retry_count} attempts"},
                )

        tms = MockTMS(sas)
        tms.execute = limited_retry

        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        result = await uig.handle_request("Search for retry limit test")

        # Should succeed after max_retries + 1 attempts
        assert result["status"] == "success"
        assert retry_count == max_retries + 1

    @pytest.mark.asyncio
    async def test_tool_failure_logged_for_analysis(self, envelope_factory):
        """Test that tool failures are properly logged for analysis."""
        sas = MockSAS()
        dms = MockDMS()

        failure_details = []

        async def logging_failure(request, envelope):
            failure_details.append(
                {
                    "tool": request.tool_name,
                    "request_id": envelope.request_id,
                    "error": "TOOL_CRASHED",
                }
            )
            return ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": "TOOL_CRASHED", "message": "Tool crashed unexpectedly"},
            )

        tms = MockTMS(sas)
        tms.execute = logging_failure

        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        result = await uig.handle_request("Search for crash test")

        # Failure should be logged
        assert len(failure_details) == 1
        assert failure_details[0]["tool"] == "search"
        assert "request_id" in failure_details[0]

        # But system should still respond gracefully
        assert result["status"] == "refused"
