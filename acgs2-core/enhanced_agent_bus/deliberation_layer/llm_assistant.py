"""
ACGS-2 Deliberation Layer - LLM Assistant
Uses LangChain and GPT-4 to provide decision reasoning and analysis.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
except ImportError:
    # Fallback if langchain not available
    ChatOpenAI = None
    ChatPromptTemplate = None
    JsonOutputParser = None

try:
    from ..models import AgentMessage
except ImportError:
    # Fallback for direct execution or testing
    from models import AgentMessage  # type: ignore


logger = logging.getLogger(__name__)


class LLMAssistant:
    """LLM-powered assistant for deliberation decision support."""

    def __init__(self, openai_api_key: Optional[str] = None, model_name: str = "gpt-4"):
        """
        Initialize the LLM assistant.

        Args:
            openai_api_key: OpenAI API key (can also be set via environment)
            model_name: GPT model to use
        """
        self.model_name = model_name
        self.llm = None

        if ChatOpenAI:
            try:
                self.llm = ChatOpenAI(
                    model_name=model_name,
                    temperature=0.1,  # Low temperature for consistent reasoning
                    openai_api_key=openai_api_key
                )
                logger.info(f"Initialized LLM assistant with {model_name}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to initialize LLM assistant due to configuration error: {e}")
            except (ImportError, ModuleNotFoundError) as e:
                logger.warning(f"Failed to initialize LLM assistant due to missing dependency: {e}")
            except OSError as e:
                logger.warning(f"Failed to initialize LLM assistant due to environment error: {e}")
        else:
            logger.warning("LangChain not available, LLM features disabled")

    async def analyze_message_impact(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Analyze message impact using LLM reasoning.

        Returns:
            Analysis with risk assessment and recommendations
        """
        if not self.llm:
            return self._fallback_analysis(message)

        try:
            # Prepare message content for analysis
            content_summary = self._extract_message_summary(message)

            # Create analysis prompt
            prompt = ChatPromptTemplate.from_template("""
            Analyze systemic risk for the following message change set.
            Constraint: Must match hash {constitutional_hash}

            Message Details:
            - Type: {message_type}
            - Priority: {priority}
            - Content Summary: {content}
            - From Agent: {from_agent}
            - To Agent: {to_agent}

            Categories for analysis: Security, Performance, Compliance.

            Please provide:
            1. Risk assessment for each category
            2. Potential impacts if processed automatically
            3. Required: Mitigations for identified threats
            4. Recommended decision (approve/reject/review)
            5. Confidence level (0-1)

            Provide your analysis in the following JSON format:
            {{
                "risk_level": "low|medium|high|critical",
                "requires_human_review": true|false,
                "recommended_decision": "approve|reject|review",
                "confidence": 0.0-1.0,
                "reasoning": ["point1", "point2", ...],
                "impact_areas": {{"security": "...", "performance": "...", "compliance": "..."}},
                "mitigations": ["mitigation1", "mitigation2", ...],
                "constitutional_hash": "{constitutional_hash}"
            }}
            """)

            # Format prompt
            formatted_prompt = prompt.format_messages(
                message_type=message.message_type.value,
                priority=message.priority.value if hasattr(message.priority, 'value') else str(message.priority),
                content=content_summary,
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                constitutional_hash=CONSTITUTIONAL_HASH
            )

            # Get LLM response
            response = await self.llm.ainvoke(formatted_prompt)

            # Parse JSON response
            parser = JsonOutputParser()
            analysis = parser.parse(response.content)

            # Add metadata
            analysis.update({
                'analyzed_by': 'llm_assistant',
                'model': self.model_name,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message_id': message.message_id
            })

            logger.info(f"LLM analysis completed for message {message.message_id}: "
                       f"risk={analysis.get('risk_level')}, decision={analysis.get('recommended_decision')}")

            return analysis

        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"LLM analysis failed for message {message.message_id} due to data error: {type(e).__name__}: {e}")
            return self._fallback_analysis(message)
        except (AttributeError, RuntimeError) as e:
            logger.error(f"LLM analysis failed for message {message.message_id} due to runtime error: {e}")
            return self._fallback_analysis(message)
        except OSError as e:
            logger.error(f"LLM analysis failed for message {message.message_id} due to I/O error: {e}")
            return self._fallback_analysis(message)

    async def generate_decision_reasoning(self,
                                        message: AgentMessage,
                                        votes: List[Dict[str, Any]],
                                        human_decision: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive reasoning for a deliberation decision.

        Args:
            message: The message being deliberated
            votes: List of agent votes
            human_decision: Human decision if available

        Returns:
            Detailed reasoning analysis
        """
        if not self.llm:
            return self._fallback_reasoning(message, votes, human_decision)

        try:
            # Prepare context
            content_summary = self._extract_message_summary(message)
            vote_summary = self._summarize_votes(votes)

            prompt = ChatPromptTemplate.from_template("""
            Evaluate action {message_type} on target {to_agent} (Deliberation Request).
            Context: {content}
            Impact Params: {votes}
            Constraint: Must match hash {constitutional_hash}

            Please provide:
            1. Summary of the deliberation process
            2. Analysis of agent consensus (if any)
            3. Final recommendation with detailed reasoning
            4. Any concerns or additional considerations
            5. Suggested follow-up actions

            Format as JSON:
            {{
                "process_summary": "brief summary",
                "consensus_analysis": "analysis of votes",
                "final_recommendation": "approve|reject|escalate",
                "reasoning": "detailed reasoning",
                "concerns": ["concern1", "concern2"],
                "follow_up_actions": ["action1", "action2"],
                "constitutional_hash": "{constitutional_hash}"
            }}
            """)

            formatted_prompt = prompt.format_messages(
                message_type=message.message_type.value,
                to_agent=message.to_agent,
                content=content_summary,
                votes=vote_summary,
                human_decision=human_decision or "pending",
                constitutional_hash=CONSTITUTIONAL_HASH
            )

            response = await self.llm.ainvoke(formatted_prompt)
            parser = JsonOutputParser()
            reasoning = parser.parse(response.content)

            reasoning.update({
                'generated_by': 'llm_assistant',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            return reasoning

        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"LLM reasoning generation failed due to data error: {type(e).__name__}: {e}")
            return self._fallback_reasoning(message, votes, human_decision)
        except (AttributeError, RuntimeError) as e:
            logger.error(f"LLM reasoning generation failed due to runtime error: {e}")
            return self._fallback_reasoning(message, votes, human_decision)
        except OSError as e:
            logger.error(f"LLM reasoning generation failed due to I/O error: {e}")
            return self._fallback_reasoning(message, votes, human_decision)

    def _extract_message_summary(self, message: AgentMessage) -> str:
        """Extract a summary of the message content for LLM analysis."""
        content_parts = []

        # Add basic message info
        content_parts.append(f"Message ID: {message.message_id}")
        content_parts.append(f"Type: {message.message_type.value}")

        # Extract content
        if message.content:
            content_str = str(message.content)
            # Truncate if too long
            if len(content_str) > 500:
                content_str = content_str[:500] + "..."
            content_parts.append(f"Content: {content_str}")

        # Extract payload
        if message.payload:
            payload_str = str(message.payload)
            if len(payload_str) > 300:
                payload_str = payload_str[:300] + "..."
            content_parts.append(f"Payload: {payload_str}")

        return "\n".join(content_parts)

    def _summarize_votes(self, votes: List[Dict[str, Any]]) -> str:
        """Summarize agent votes for LLM context."""
        if not votes:
            return "No votes recorded"

        summary_parts = []
        approve_count = sum(1 for v in votes if v.get('vote') == 'approve')
        reject_count = sum(1 for v in votes if v.get('vote') == 'reject')
        abstain_count = sum(1 for v in votes if v.get('vote') == 'abstain')

        summary_parts.append(f"Total votes: {len(votes)}")
        summary_parts.append(f"Approve: {approve_count}, Reject: {reject_count}, Abstain: {abstain_count}")

        # Add sample reasoning
        if votes:
            sample_vote = votes[0]
            reasoning = sample_vote.get('reasoning', 'No reasoning provided')
            if len(reasoning) > 100:
                reasoning = reasoning[:100] + "..."
            summary_parts.append(f"Sample reasoning: {reasoning}")

        return "; ".join(summary_parts)

    def _fallback_analysis(self, message: AgentMessage) -> Dict[str, Any]:
        """Fallback analysis when LLM is not available."""
        # Simple rule-based analysis
        risk_level = "medium"
        requires_review = False

        # Check for high-risk keywords
        content_text = self._extract_message_summary(message).lower()
        high_risk_keywords = ['critical', 'emergency', 'security', 'breach', 'violation']

        if any(keyword in content_text for keyword in high_risk_keywords):
            risk_level = "high"
            requires_review = True

        return {
            'risk_level': risk_level,
            'requires_human_review': requires_review,
            'recommended_decision': 'review' if requires_review else 'approve',
            'confidence': 0.5,
            'reasoning': ['Rule-based analysis (LLM unavailable)'],
            'impact_areas': ['governance'],
            'analyzed_by': 'fallback_analyzer',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _fallback_reasoning(self,
                          message: AgentMessage,
                          votes: List[Dict[str, Any]],
                          human_decision: Optional[str]) -> Dict[str, Any]:
        """Fallback reasoning when LLM is not available."""
        approve_votes = sum(1 for v in votes if v.get('vote') == 'approve')
        total_votes = len(votes)

        if human_decision:
            final_rec = human_decision.lower()
        elif total_votes > 0 and approve_votes / total_votes > 0.6:
            final_rec = 'approve'
        else:
            final_rec = 'review'

        return {
            'process_summary': f'Message deliberated with {total_votes} agent votes',
            'consensus_analysis': f'{approve_votes}/{total_votes} votes to approve',
            'final_recommendation': final_rec,
            'reasoning': 'Automated consensus analysis (LLM unavailable)',
            'concerns': [],
            'follow_up_actions': ['Monitor execution'],
            'generated_by': 'fallback_reasoner',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    async def analyze_deliberation_trends(self,
                                        deliberation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze trends in deliberation decisions for threshold optimization.

        Args:
            deliberation_history: List of past deliberation records

        Returns:
            Trend analysis and recommendations
        """
        if not self.llm or not deliberation_history:
            return self._fallback_trend_analysis(deliberation_history)

        try:
            # Prepare history summary
            history_summary = self._summarize_deliberation_history(deliberation_history)

            prompt = ChatPromptTemplate.from_template("""
            Analyze the following deliberation history and provide insights for optimizing the impact threshold.

            History Summary:
            {history}

            Please provide:
            1. Patterns in high-risk vs low-risk decisions
            2. Recommended threshold adjustments
            3. Areas where human review was particularly valuable
            4. Suggestions for improving the automated routing

            Format as JSON:
            {{
                "patterns": ["pattern1", "pattern2"],
                "threshold_recommendations": "recommendations",
                "human_review_value": "analysis",
                "improvement_suggestions": ["suggestion1", "suggestion2"]
            }}
            """)

            formatted_prompt = prompt.format_messages(history=history_summary)
            response = await self.llm.ainvoke(formatted_prompt)
            parser = JsonOutputParser()
            analysis = parser.parse(response.content)

            return analysis

        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Trend analysis failed due to data error: {type(e).__name__}: {e}")
            return self._fallback_trend_analysis(deliberation_history)
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Trend analysis failed due to runtime error: {e}")
            return self._fallback_trend_analysis(deliberation_history)
        except OSError as e:
            logger.error(f"Trend analysis failed due to I/O error: {e}")
            return self._fallback_trend_analysis(deliberation_history)

    def _summarize_deliberation_history(self, history: List[Dict[str, Any]]) -> str:
        """Summarize deliberation history for LLM analysis."""
        if not history:
            return "No deliberation history available"

        total = len(history)
        approved = sum(1 for h in history if h.get('outcome') == 'approved')
        rejected = sum(1 for h in history if h.get('outcome') == 'rejected')
        timed_out = sum(1 for h in history if h.get('outcome') == 'timed_out')

        avg_impact = sum(h.get('impact_score', 0) for h in history) / max(total, 1)

        return f"""
        Total deliberations: {total}
        Approved: {approved} ({approved/total*100:.1f}%)
        Rejected: {rejected} ({rejected/total*100:.1f}%)
        Timed out: {timed_out} ({timed_out/total*100:.1f}%)
        Average impact score: {avg_impact:.3f}
        """

    def _fallback_trend_analysis(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback trend analysis."""
        if not history:
            return {
                'patterns': ['No history available'],
                'threshold_recommendations': 'Maintain current threshold',
                'human_review_value': 'Unable to analyze',
                'improvement_suggestions': ['Collect more data']
            }

        approved = sum(1 for h in history if h.get('outcome') == 'approved')
        total = len(history)
        approval_rate = approved / total

        recommendations = "Maintain current threshold"
        if approval_rate > 0.8:
            recommendations = "Consider lowering threshold to reduce deliberation load"
        elif approval_rate < 0.3:
            recommendations = "Consider raising threshold to ensure important decisions are reviewed"

        return {
            'patterns': [f'Approval rate: {approval_rate:.2f}'],
            'threshold_recommendations': recommendations,
            'human_review_value': 'Basic statistical analysis',
            'improvement_suggestions': ['Enable LLM analysis for better insights']
        }


# Global assistant instance
_llm_assistant = None

def get_llm_assistant() -> LLMAssistant:
    """Get or create global LLM assistant instance."""
    global _llm_assistant
    if _llm_assistant is None:
        _llm_assistant = LLMAssistant()
    return _llm_assistant
