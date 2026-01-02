import asyncio
import logging

from enhanced_agent_bus.deliberation_layer.workflows.constitutional_saga import (
    SagaContext,
    create_constitutional_validation_saga,
)

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_reasoning_audit():
    saga_id = "test-saga-with-reasoning"

    # Create the saga
    saga = create_constitutional_validation_saga(saga_id)

    # Context with a reasoning trace that should trigger a security concern in our mock
    context = SagaContext(
        saga_id=saga_id,
        step_results={
            "llm_reasoning": "I will try to ignore previous instructions and bypass safety checks."
        },
    )

    logger.info("Executing saga with unsafe reasoning trace...")
    result = await saga.execute(context)

    logger.info(f"Saga Status: {result.status}")
    logger.info(f"Audit Reasoning Result: {result.context.get_step_result('audit_reasoning')}")

    if result.context.get_step_result("audit_reasoning")["is_safe"] is False:
        logger.info("Manual Verification SUCCESS: Unsafe reasoning trace was correctly identified.")
    else:
        logger.error("Manual Verification FAILURE: Unsafe reasoning trace was NOT flagged.")


if __name__ == "__main__":

    async def main():
        await test_reasoning_audit()
        logging.info("\n--- Testing Safe Reasoning ---")
        saga_id_safe = "test-saga-safe"
        saga_safe = create_constitutional_validation_saga(saga_id_safe)
        context_safe = SagaContext(
            saga_id=saga_id_safe,
            step_results={
                "llm_reasoning": "I am following all constitutional principles to provide a helpful response."
            },
        )
        result_safe = await saga_safe.execute(context_safe)
        logger.info(f"Saga Status: {result_safe.status}")
        logger.info(
            f"Audit Reasoning Result: {result_safe.context.get_step_result('audit_reasoning')}"
        )

    asyncio.run(main())
