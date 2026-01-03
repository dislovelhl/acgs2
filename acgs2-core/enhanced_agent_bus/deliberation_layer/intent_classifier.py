"""
ACGS-2 SDPC - Intent Classifier
Constitutional Hash: cdd01ef066bc6cf2

Categorizes user intent for dynamic routing and prompt compilation.
"""

import logging
import json
from enum import Enum
from typing import Any, Dict, Optional

import litellm
from ..config import BusConfiguration


class IntentType(Enum):
    FACTUAL = "factual"  # High precision, requires GraphCheck & ASC
    CREATIVE = "creative"  # High fluency, relaxed factual constraints
    REASONING = "reasoning"  # Complex logic, triggers AMPO branching
    GENERAL = "general"  # Default/conversational intent


logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies user intent to determine optimal processing strategies."""

    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        config: Optional[BusConfiguration] = None
    ):
        self.model_name = model_name
        self.config = config or BusConfiguration()
        # In a real implementation, we would load a distilled LLM or BERT model here.
        # For Phase 1, we use dynamic heuristic pattern matching with an LLM fallback hook.
        logger.info(f"IntentClassifier initialized with model: {model_name}")

    def classify(self, content: str) -> IntentType:
        """Determines the intent type of the provided content."""
        content_lower = content.lower()

        # Heuristic Pattern Matching (Fast Path)
        if any(
            word in content_lower
            for word in ["calculate", "prove", "reason", "step by step", "analyze"]
        ):
            return IntentType.REASONING

        if any(
            word in content_lower
            for word in [
                "tell me about",
                "who is",
                "what is",
                "where is",
                "what happened in",
                "date of",
                "historical",
                "how many",
            ]
        ):
            return IntentType.FACTUAL

        if any(
            word in content_lower
            for word in ["write a story", "poem", "joke", "creative", "imagine", "song"]
        ):
            return IntentType.CREATIVE

        # Default to general intent
        return IntentType.GENERAL

    async def classify_async(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> IntentType:
        """Asynchronous classification with optional context/LLM fallback."""
        # 1. Try heuristic classification first
        intent = self.classify(content)

        # 2. If intent is GENERAL (ambiguous), fallback to LLM
        if intent == IntentType.GENERAL and self.config.llm_model:
            try:
                # Prepare prompt for intent classification
                system_prompt = f"""
                Classify the following user input into one of these categories:
                - factual: Question about facts, data, history, or specific entities.
                - creative: Request for story, poem, song, or creative writing.
                - reasoning: Complex logical problem, math, or step-by-step analysis.
                - general: Simple greeting, conversational filler, or ambiguous request.

                Respond with ONLY the category name in lowercase.
                """

                response = await litellm.acompletion(
                    model=self.config.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    max_tokens=self.config.llm_max_tokens,
                    temperature=0,
                    caching=self.config.llm_use_cache
                )

                llm_intent = response.choices[0].message.content.strip().lower()

                # Map LLM response to IntentType
                for it in IntentType:
                    if it.value == llm_intent:
                        logger.info(f"LLM classified intent as: {llm_intent} (heuristic was GENERAL)")
                        return it

                logger.warning(f"LLM returned unknown intent: {llm_intent}, falling back to GENERAL")

            except Exception as e:
                logger.error(f"LLM intent classification failed: {str(e)}")

        return intent
