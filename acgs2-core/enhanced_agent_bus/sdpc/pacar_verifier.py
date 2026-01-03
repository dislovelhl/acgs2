"""
ACGS-2 SDPC - PACAR Verifier
Agentic Verification (PACAR) for complex deliberative audit.
Constitutional Hash: cdd01ef066bc6cf2

Orchestrates multi-agent critique and validation.
"""

import logging
from typing import Any, Dict, Optional

from ..deliberation_layer.llm_assistant import get_llm_assistant
from .pacar_manager import PACARManager
from .conversation import MessageRole
from ..config import BusConfiguration

logger = logging.getLogger(__name__)


class PACARVerifier:
    """Orchestrates Red Team and Validator agents for agentic verification."""

    def __init__(self, config: Optional[BusConfiguration] = None):
        self.config = config or BusConfiguration.from_environment()
        self.assistant = get_llm_assistant()
        self.manager = PACARManager(config=self.config)
        logger.info("PACARVerifier initialized for SDPC Phase 2 (Multi-turn enabled)")

    async def verify(
        self, content: str, original_intent: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the PACAR (Proactive Agentic Critique and Review) workflow.
        1. Red Team: Adversarial audit to find weaknesses.
        2. Validator: Review content and Red Team critique for final consensus.
        """
        logger.info(f"Executing PACAR multi-agent verification (Session: {session_id})")

        from ..models import CONSTITUTIONAL_HASH

        red_team_prompt = (
            f"Role: Adversarial Auditor (Red Team)\n"
            f"Goal: Identify hallucinations, logic gaps, or security risks in the proposed response.\n"
            f"Constitutional Hash: {CONSTITUTIONAL_HASH}\n\n"
            f"Original Intent: {original_intent}\n"
            f"Proposed Content: {content}\n\n"
            f"Be extremely critical. Analyze if the content fully addresses the intent without introducing safety risks."
        )

        validator_prompt = (
            f"Role: Consensus Validator\n"
            f"Goal: Final approval of the content by considering the Red Team's critique.\n"
            f"Constitutional Hash: {CONSTITUTIONAL_HASH}\n\n"
            f"Task: Review the original content and the adversarial critique. If the risks are mitigated or minor, approve. "
            f"If critical issues remain, reject."
        )

        try:
            # Stage 1: Red Team Audit
            if session_id:
                await self.manager.add_message(
                    session_id, MessageRole.USER, content, {"intent": original_intent}
                )
                context_state = await self.manager.get_state(session_id)
                history_dicts = [
                    {"role": m.role.value, "content": m.content} for m in context_state.messages
                ]

                red_team_analysis = await self.assistant.ainvoke_multi_turn(
                    sys_prompt=red_team_prompt, messages=history_dicts
                )
            else:
                # Single turn fallback
                red_team_analysis = await self.assistant.analyze_message_impact(content)

            # Stage 2: Validator Review (simulate by adding red team critique to context)
            critique = red_team_analysis.get("reasoning", "No specific critique provided.")
            if session_id:
                await self.manager.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    f"Red Team Critique: {critique}",
                    {"type": "red_team_critique"},
                )
                context_state = await self.manager.get_state(session_id)
                history_dicts = [
                    {"role": m.role.value, "content": m.content} for m in context_state.messages
                ]

                final_analysis = await self.assistant.ainvoke_multi_turn(
                    sys_prompt=validator_prompt, messages=history_dicts
                )
            else:
                final_analysis = red_team_analysis  # Simple fallback

            # 3. Decision and Metrics
            is_valid = final_analysis.get("recommended_decision", "approve") == "approve"
            risk_level = final_analysis.get("risk_level", "low")
            if risk_level in ["high", "critical"]:
                is_valid = False

            confidence = final_analysis.get("confidence", 0.5)

            # Combine metrics if available
            metrics = {}
            if "_metrics" in red_team_analysis:
                metrics["red_team"] = red_team_analysis["_metrics"]
            if "_metrics" in final_analysis:
                metrics["validator"] = final_analysis["_metrics"]

            result = {
                "is_valid": is_valid,
                "confidence": confidence,
                "critique": critique,
                "validator_reasoning": final_analysis.get("reasoning", []),
                "mitigations": final_analysis.get("mitigations", []),
                "consensus_reached": True,
                "metrics": metrics,
            }

            if session_id:
                await self.manager.add_message(
                    session_id,
                    MessageRole.ASSISTANT,
                    f"Final Verification Decision: {'Approved' if is_valid else 'Rejected'}. Reason: {result['validator_reasoning']}",
                    {"type": "verification_result", "is_valid": is_valid},
                )

            return result

        except Exception as e:
            logger.error(f"PACAR verification failed: {e}")
            return {"is_valid": False, "confidence": 0.0, "reason": str(e)}
