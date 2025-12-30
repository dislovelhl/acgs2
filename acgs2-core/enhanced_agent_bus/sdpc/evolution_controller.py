"""
ACGS-2 SDPC - Evolution Controller
Manages the feedback loop between verification results and prompt optimization.
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from typing import Dict, List, Optional

from ..deliberation_layer.intent_classifier import IntentType

logger = logging.getLogger(__name__)


class EvolutionController:
    """
    Tracks verification results and triggers prompt mutations in AMPO.
    Implements a simplified self-evolution loop.
    """

    def __init__(self, failure_threshold: int = 3):
        # failure_history tracks consecutive failures for each intent branch
        self.failure_history: Dict[IntentType, int] = {
            IntentType.FACTUAL: 0,
            IntentType.CREATIVE: 0,
            IntentType.REASONING: 0,
            IntentType.GENERAL: 0,
        }
        self.failure_threshold = failure_threshold

        # dynamic_mutations maps intent to list of additional instructions
        self.dynamic_mutations: Dict[IntentType, List[str]] = {
            IntentType.FACTUAL: [],
            IntentType.CREATIVE: [],
            IntentType.REASONING: [],
            IntentType.GENERAL: [],
        }

        logger.info(f"EvolutionController initialized with failure_threshold={failure_threshold}")

    def record_feedback(self, intent: IntentType, verification_results: Dict[str, bool]) -> None:
        """
        Records verification feedback for a specific intent branch.
        Trigger mutation if failures cross threshold.
        """
        # A result is a failure if any critical verification (ASC, Graph, PACAR) is False
        is_success = all(verification_results.values())

        if not is_success:
            self.failure_history[intent] += 1
            logger.warning(
                f"Verification failure recorded for {intent.value}. Count: {self.failure_history[intent]}"
            )

            if self.failure_history[intent] >= self.failure_threshold:
                self._trigger_mutation(intent)
        else:
            # Reset failure count on success (simplified linear model)
            if self.failure_history[intent] > 0:
                logger.info(
                    f"Successful verification for {intent.value}. Resetting failure history."
                )
            self.failure_history[intent] = 0

    def _trigger_mutation(self, intent: IntentType) -> None:
        """Injects corrective instructions into the prompt branch."""
        mutation_map = {
            IntentType.FACTUAL: "MUTATION: Extreme Grounding enforced. Cross-verify every date and location.",
            IntentType.REASONING: "MUTATION: Chain-of-Thought verified. Explicitly list logical dependencies between steps.",
            IntentType.CREATIVE: "MUTATION: Tone Adjustment. Ensure higher variety in sentence structure and imagery.",
            IntentType.GENERAL: "MUTATION: Conciseness. Reduce verbosity and focus on direct answers.",
        }

        new_instruction = mutation_map.get(intent, "MUTATION: Adhere strictly to user constraints.")

        if new_instruction not in self.dynamic_mutations[intent]:
            logger.info(f"Triggering mutation for {intent.value}: {new_instruction}")
            self.dynamic_mutations[intent].append(new_instruction)

        # Reset counter after mutation to allow new baseline
        self.failure_history[intent] = 0

    def get_mutations(self, intent: IntentType) -> List[str]:
        """Returns active mutations for the requested intent."""
        return self.dynamic_mutations.get(intent, [])

    def reset_mutations(self, intent: Optional[IntentType] = None) -> None:
        """Clears mutations for a specific intent or all intents."""
        if intent:
            self.dynamic_mutations[intent] = []
            self.failure_history[intent] = 0
        else:
            for it in self.dynamic_mutations:
                self.dynamic_mutations[it] = []
                self.failure_history[it] = 0
        logger.info("SDPC mutations reset.")
