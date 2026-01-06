#!/usr/bin/env python3
"""
Test script to verify the rate limiter _send_error fix.
This reproduces the original issue and verifies the fix.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "acgs2-core"))

from unittest.mock import AsyncMock

from src.core.shared.security.rate_limiter import RateLimitMiddleware, RateLimitResult


async def test_send_error_fix():
    """Test that _send_error method works correctly with proper ASGI parameters."""

    # Create middleware
    middleware = RateLimitMiddleware(None)

    # Mock ASGI scope, receive, and send
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }
    receive = AsyncMock()
    send = AsyncMock()

    # Create a rate limit result that triggers error response
    result = RateLimitResult(
        allowed=False,
        limit=100,
        remaining=0,
        reset_at=1234567890,
        retry_after=60,
        scope=None,
        key="test",
    )

    # This should not raise an exception anymore
    try:
        await middleware._send_error(scope, receive, send, result)
        print("✅ _send_error method executed successfully")

        # Verify that send was called with proper ASGI messages
        assert send.call_count == 2, f"Expected 2 calls to send, got {send.call_count}"

        # Check first call (response start)
        start_call = send.call_args_list[0][0][0]
        assert start_call["type"] == "http.response.start"
        assert start_call["status"] == 429

        # Check second call (response body)
        body_call = send.call_args_list[1][0][0]
        assert body_call["type"] == "http.response.body"
        assert "Too Many Requests" in str(body_call["body"])

        print("✅ ASGI response format is correct")

    except TypeError as e:
        if "'NoneType' object is not subscriptable" in str(e):
            print("❌ Original bug still exists!")
            raise
        else:
            print(f"❌ Unexpected TypeError: {e}")
            raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    print("Testing rate limiter _send_error fix...")
    asyncio.run(test_send_error_fix())
    print("✅ All tests passed!")
