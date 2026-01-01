import asyncio
import logging
from enhanced_agent_bus.opa_client import OPAClient

logger = logging.getLogger(__name__)


async def test_opa_security():
    client = OPAClient(mode="fallback")

    logger.info("--- Testing Policy Path Validation ---")
    res = await client.evaluate_policy({"test": 1}, "data.acgs..invalid")
    if res["allowed"] is False and "Path traversal" in res["reason"]:
        logger.info("PASS: Caught invalid path (..)")
    else:
        logger.error(f"FAIL: Result: {res}")

    res = await client.evaluate_policy({"test": 1}, "data.acgs;injection")
    if res["allowed"] is False and "Invalid policy path" in res["reason"]:
        logger.info("PASS: Caught injection path (;)")
    else:
        logger.error(f"FAIL: Result: {res}")

    logger.info("\n--- Testing Input Size Validation ---")
    large_input = {"data": "x" * (1024 * 600)}  # > 512KB
    res = await client.evaluate_policy(large_input, "data.acgs.allow")
    if res["allowed"] is False and "exceeds maximum allowed size" in res["reason"]:
        logger.info("PASS: Caught large input")
    else:
        logger.error(f"FAIL: Result: {res}")

    logger.info("\n--- Testing Error Sanitization ---")
    # Wrap a fake error
    try:
        raise Exception(
            "Sensitive URL: https://admin:password@opa.internal/v1/data?token=secret123"
        )
    except Exception as e:
        sanitized = client._sanitize_error(e)
        logger.debug(f"Original: {e}")
        logger.debug(f"Sanitized: {sanitized}")
        if "password" not in sanitized and "secret123" not in sanitized:
            logger.info("PASS: Error sanitized")
        else:
            logger.error("FAIL: Error NOT sanitized")


if __name__ == "__main__":
    asyncio.run(test_opa_security())
