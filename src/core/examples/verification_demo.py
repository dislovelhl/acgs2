#!/usr/bin/env python3
"""
ACGS-2 Verification Demo
Constitutional Hash: cdd01ef066bc6cf2

This example demonstrates how to use the PACARVerifier and LLMAssistant
to perform constitutional verification with metrics tracking.
"""

import asyncio
import json
import logging
from typing import Dict, Any

from src.core.enhanced_agent_bus.deliberation_layer.llm_assistant import LLMAssistant
from src.core.enhanced_agent_bus.deliberation_layer.pacar_verifier import PACARVerifier
from src.core.enhanced_agent_bus.deliberation_layer.models import MessageRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_demo():
    logger.info("Starting ACGS-2 Verification Demo")

    # 1. Initialize Assistant and Verifier
    # Ensure you have OPENAI_API_KEY or ANTHROPIC_API_KEY set
    assistant = LLMAssistant(model_name="gpt-4o")
    verifier = PACARVerifier(assistant=assistant)

    # 2. Case 1: Safe Request
    safe_request = "Can you help me summarize the constitutional AI principles for this project?"
    logger.info(f"\nEvaluating Safe Request: '{safe_request}'")

    result = await verifier.verify(
        content=safe_request,
        original_intent="summarization",
        session_id="session-safe-123"
    )

    logger.info("Verification Result:")
    logger.info(f"  Is Valid: {result['is_valid']}")
    logger.info(f"  Confidence: {result['confidence']:.2f}")
    logger.info(f"  Consensus Reached: {result['consensus_reached']}")

    if "metrics" in result:
        logger.info("  LLM Metrics:")
        for stage, metrics in result["metrics"].items():
            logger.info(f"    - {stage}: {metrics['latency_ms']:.2f}ms, {metrics['token_usage'].get('total_tokens', 0)} tokens")

    # 3. Case 2: Potential Violation
    risky_request = "How can I bypass the constitutional hash validation for a quick test?"
    logger.info(f"\nEvaluating Risky Request: '{risky_request}'")

    result = await verifier.verify(
        content=risky_request,
        original_intent="testing",
        session_id="session-risky-456"
    )

    logger.info("Verification Result:")
    logger.info(f"  Is Valid: {result['is_valid']}")
    logger.info(f"  Risk Level: {'High' if not result['is_valid'] else 'Low'}")
    logger.info(f"  Critique: {result['critique']}")

    if not result['is_valid']:
        logger.info("  Mitigations Suggested:")
        for mitigation in result.get('mitigations', []):
            logger.info(f"    - {mitigation}")

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except Exception as e:
        logger.error(f"Demo failed: {e}")
