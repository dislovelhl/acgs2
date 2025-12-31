from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
try:
    from ..utils import get_iso_timestamp
    from ..models import AgentMessage, get_enum_value, MessageType, CONSTITUTIONAL_HASH
except ImportError:
    try:
        from utils import get_iso_timestamp  # type: ignore
        from models import AgentMessage, get_enum_value, MessageType, CONSTITUTIONAL_HASH  # type: ignore
    except ImportError:
        import sys, os
        d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if d not in sys.path: sys.path.append(d)
        from utils import get_iso_timestamp  # type: ignore
        from models import AgentMessage, get_enum_value, MessageType, CONSTITUTIONAL_HASH  # type: ignore

logger = logging.getLogger(__name__)

# Mock classes for test friendliness when LangChain is missing
class ChatPromptTemplate:
    @classmethod
    def from_template(cls, template: str):
        mock = MagicMock()
        mock.format_messages.return_value = []
        return mock

class SystemMessagePromptTemplate: pass
class HumanMessagePromptTemplate: pass
class JsonOutputParser:
    def parse(self, text: str): return {}
class ChatOpenAI:
    def __init__(self, *args, **kwargs): pass
    async def ainvoke(self, *args, **kwargs):
        mock = MagicMock()
        mock.content = "{}"
        return mock

try:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import (
        ChatPromptTemplate,
        SystemMessagePromptTemplate,
        HumanMessagePromptTemplate
    )
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    from unittest.mock import MagicMock
    LANGCHAIN_AVAILABLE = False

class LLMAssistant:
    """LLM-powered assistant for deliberation decision support."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4"):
        self.model_name = model_name
        self.llm = None
        if LANGCHAIN_AVAILABLE:
            try: self.llm = ChatOpenAI(model_name=model_name, temperature=0.1, openai_api_key=api_key)
            except Exception as e: logger.warning(f"LLM init failed: {e}")

    async def _invoke_llm(self, prompt_tmpl: str, **kwargs) -> Dict[str, Any]:
        if not self.llm: return {}
        try:
            prompt = ChatPromptTemplate.from_template(prompt_tmpl)
            resp = await self.llm.ainvoke(prompt.format_messages(**kwargs, constitutional_hash=CONSTITUTIONAL_HASH))
            return JsonOutputParser().parse(resp.content)
        except Exception as e:
            logger.error(f"LLM invoke failed: {e}")
            return {}

    async def analyze_message_impact(self, message: AgentMessage) -> Dict[str, Any]:
        if not self.llm: return self._fallback_analysis(message)
        template = """
        CONSTITUTIONAL CONSTRAINT: All analysis must validate against hash {constitutional_hash}

        Security Analysis: Evaluate the message from {from_agent} to {to_agent} for security risks.
        Performance Analysis: Assess if this message impacts system performance.
        Compliance Analysis: Verify compliance with the current constitutional policies.

        Content: {content}
        Message Type: {message_type}

        Identify risk_level, recommended_decision, and suggested mitigations.
        Return JSON with: risk_level, requires_human_review, recommended_decision, confidence, reasoning, impact_areas, mitigations, constitutional_hash
        """
        res = await self._invoke_llm(
            template,
            from_agent=message.from_agent,
            to_agent=message.to_agent,
            content=str(message.content)[:500],
            message_type=message.message_type.value if hasattr(message.message_type, "value") else message.message_type
        )
        if not res: return self._fallback_analysis(message)
        res.update({"analyzed_by": "llm_analyzer", "timestamp": get_iso_timestamp(), "message_id": message.message_id})
        return res

    async def generate_decision_reasoning(self, message: AgentMessage, votes: List[Dict[str, Any]], human_decision: Optional[str] = None) -> Dict[str, Any]:
        if not self.llm: return self._fallback_reasoning(message, votes, human_decision)
        template = """
        **Action Under Review:** {message_type}

        DELIBERATION CONTEXT
        Review the following votes for action {message_id} to recipient {recipient}.
        Votes: {votes}
        Human Input: {human_decision}

        CONSTITUTIONAL CONSTRAINT: Hash {constitutional_hash} must be validated

        Return JSON with: process_summary, consensus_analysis, final_recommendation, reasoning, concerns, follow_up_actions, constitutional_hash
        """
        res = await self._invoke_llm(
            template,
            message_type=message.message_type.value if hasattr(message.message_type, "value") else message.message_type,
            message_id=message.message_id,
            recipient=message.to_agent,
            votes=str(votes)[:500],
            human_decision=human_decision or "None"
        )
        if not res: return self._fallback_reasoning(message, votes, human_decision)
        res.update({"generated_by": "llm_reasoner", "timestamp": get_iso_timestamp()})
        return res

    async def analyze_deliberation_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._fallback_analysis_trends(history)

    def _fallback_analysis_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not history:
            return {
                "patterns": [],
                "threshold_recommendations": "Maintain current threshold",
                "risk_trends": "stable"
            }

        approved = sum(1 for h in history if h.get("outcome") == "approved")
        total = len(history)
        rate = approved / total if total > 0 else 0

        rec = "Maintain current threshold"
        if rate > 0.8: rec = "Systematic high approval observed. Consider lowering deliberation threshold for efficiency."
        elif rate < 0.4: rec = "High rejection rate observed. Consider raising deliberation threshold or updating policies."

        return {
            "patterns": [f"Approval rate: {rate:.1%}"],
            "threshold_recommendations": rec,
            "risk_trends": "improving" if rate > 0.6 else "stable"
        }

    def _fallback_analysis(self, message: AgentMessage) -> Dict[str, Any]:
        text = str(message.content).lower()
        risk = "low"
        if "breach" in text: risk = "critical"
        elif any(k in text for k in ["emergency", "critical", "security", "violation"]): risk = "high"

        rev = risk in ["critical", "high"]
        return {
            "risk_level": risk, "requires_human_review": rev, "recommended_decision": "review" if rev else "approve",
            "confidence": 0.5, "reasoning": ["Fallback rule-based analysis"], "impact_areas": {"security": "Medium" if "security" in text else "Low"},
            "mitigations": ["Monitor execution"], "analyzed_by": "enhanced_fallback_analyzer", "timestamp": get_iso_timestamp(), "constitutional_hash": CONSTITUTIONAL_HASH
        }

    def _fallback_reasoning(self, message: AgentMessage, votes: List[Dict[str, Any]], human_decision: Optional[str]) -> Dict[str, Any]:
        app = sum(1 for v in votes if str(v.get("vote")).lower() == "approve")
        total = len(votes)
        rate = app / total if total > 0 else 0
        final = human_decision.lower() if human_decision else ("approve" if rate >= 0.6 else "review")
        return {
            "process_summary": f"Fallback deliberation: {app}/{total} approved", "consensus_analysis": f"Strength: {rate:.1%}",
            "final_recommendation": final, "reasoning": "Fallback vote synthesis", "concerns": [], "follow_up_actions": ["Monitor"],
            "generated_by": "enhanced_fallback_reasoner", "timestamp": get_iso_timestamp(), "constitutional_hash": CONSTITUTIONAL_HASH
        }

    def _extract_message_summary(self, message: AgentMessage) -> str:
        content_str = str(message.content)
        if len(content_str) > 500:
            content_str = content_str[:497] + "..."
        summary = [
            f"Message ID: {message.message_id}",
            f"Type: {message.message_type.value}",
            f"From Agent: {message.from_agent}",
            f"To Agent: {message.to_agent}",
            f"Content: {content_str}"
        ]
        if message.payload:
            payload_str = str(message.payload)
            if len(payload_str) > 200:
                payload_str = payload_str[:197] + "..."
            summary.append(f"Payload: {payload_str}")
        return "\n".join(summary)

    def _summarize_votes(self, votes: List[Dict[str, Any]]) -> str:
        if not votes:
            return "No votes recorded"
        total = len(votes)
        approvals = sum(1 for v in votes if v.get("vote") == "approve")
        rejections = sum(1 for v in votes if v.get("vote") == "reject")

        summary = [
            f"Total votes: {total}",
            f"Approve: {approvals}",
            f"Reject: {rejections}",
            "Sample reasoning:"
        ]
        for v in votes[:3]:
            # Handle list or dict for votes
            if isinstance(v, dict):
                v_type = v.get("vote", "unknown")
                reason = v.get("reasoning", "No reasoning provided")
            else:
                v_type = "unknown"
                reason = str(v)
            if len(reason) > 100:
                reason = reason[:97] + "..."
            summary.append(f"- {v_type}: {reason}")
        return "\n".join(summary)

    def _summarize_deliberation_history(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "No deliberation history available"
        total = len(history)
        approved = sum(1 for h in history if h.get("outcome") == "approved")
        rejected = sum(1 for h in history if h.get("outcome") == "rejected")
        timed_out = sum(1 for h in history if h.get("outcome") == "timed_out")
        avg_impact = sum(h.get("impact_score", 0.0) for h in history) / total

        return (
            f"Total deliberations: {total}\n"
            f"Approved: {approved}\n"
            f"Rejected: {rejected}\n"
            f"Timed out: {timed_out}\n"
            f"Average impact score: {avg_impact:.2f}"
        )

_llm_assistant = None
def get_llm_assistant(**kwargs) -> LLMAssistant:
    global _llm_assistant
    if not _llm_assistant: _llm_assistant = LLMAssistant(**kwargs)
    return _llm_assistant
def reset_llm_assistant():
    global _llm_assistant
    _llm_assistant = None

__all__ = ["LLMAssistant", "get_llm_assistant", "reset_llm_assistant", "ChatPromptTemplate", "SystemMessagePromptTemplate", "HumanMessagePromptTemplate", "JsonOutputParser"]
