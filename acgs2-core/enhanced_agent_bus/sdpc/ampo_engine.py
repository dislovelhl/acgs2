"""
ACGS-2 SDPC - AMPO Engine
Automatic Multi-Branched Prompt Optimization (AMPO)
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging

from ..deliberation_layer.intent_classifier import IntentType

logger = logging.getLogger(__name__)


class AMPOEngine:
    """
    Compiles user intent into optimized, multi-branched system prompts.
    Treatment: Intent as source code, Prompt as compiled binary.
    """

    def __init__(self, evolution_controller=None):
        self.branching_strategies = {
            IntentType.FACTUAL: self._factual_branch,
            IntentType.CREATIVE: self._creative_branch,
            IntentType.REASONING: self._reasoning_branch,
            IntentType.GENERAL: self._general_branch,
        }
        self.evolution_controller = evolution_controller
        logger.info("AMPOEngine initialized with Evolution support")

    def compile(self, intent: IntentType, content: str) -> str:
        """Compiles the optimal prompt based on intent and content."""
        strategy = self.branching_strategies.get(intent, self._general_branch)
        base_prompt = strategy(content)

        # Phase 3: Inject dynamic mutations if available
        if self.evolution_controller:
            mutations = self.evolution_controller.get_mutations(intent)
            if mutations:
                logger.info(f"Injecting {len(mutations)} mutations into {intent.value} prompt")
                mutation_block = "\n".join(mutations)
                return f"{mutation_block}\n\n{base_prompt}"

        return base_prompt

    def _factual_branch(self, content: str) -> str:
        """Branch for factual precision."""
        return (
            "You are a factual precision agent. Your primary goal is accuracy.\n"
            "1. GROUNDING: Verify all claims against retrieved context.\n"
            "2. CITATION: Cite sources using [Anchor] format.\n"
            "3. UNCERTAINTY: If the answer is not in the context, state 'I do not have enough information'.\n"
            f"User Request: {content}"
        )

    def _creative_branch(self, content: str) -> str:
        """Branch for creative fluency."""
        return (
            "You are a creative assistant. Prioritize fluency, imagery, and engagement.\n"
            "Avoid dry, factual restricted tones unless requested.\n"
            f"User Request: {content}"
        )

    def _reasoning_branch(self, content: str) -> str:
        """Branch for multi-step reasoning."""
        return (
            "You are a reasoning agent. Breakdown the problem into atomic steps.\n"
            "1. State the objective.\n"
            "2. Identify constraints.\n"
            "3. Execute step-by-step logic.\n"
            "4. Verify the final result against the initial objective.\n"
            f"User Request: {content}"
        )

    def _general_branch(self, content: str) -> str:
        """Default conversational branch."""
        return f"You are a helpful assistant. User Request: {content}"
