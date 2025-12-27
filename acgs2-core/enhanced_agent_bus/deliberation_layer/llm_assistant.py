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

            # Create analysis prompt with chain-of-thought reasoning
            prompt = ChatPromptTemplate.from_template("""You are a Constitutional AI Governance Expert specializing in multi-agent system risk assessment.
Your role is to analyze agent messages for systemic risk while ensuring constitutional compliance.

CONSTITUTIONAL CONSTRAINT: All analysis must validate against hash {constitutional_hash}

## ANALYSIS FRAMEWORK

Let's approach this step-by-step:

### Step 1: Message Classification
First, examine the message characteristics:
- Type: {message_type}
- Priority: {priority}
- Source Agent: {from_agent}
- Target Agent: {to_agent}
- Content Summary: {content}

### Step 2: Risk Assessment by Category
Analyze each category systematically:

**Security Analysis:**
- Does this message request privileged operations?
- Could it expose sensitive data or credentials?
- Does it involve external system access?

**Performance Analysis:**
- Could processing cause resource exhaustion?
- Does it involve bulk operations or long-running tasks?
- What is the potential cascading impact?

**Compliance Analysis:**
- Does the action align with constitutional principles?
- Are proper authorization channels followed?
- Does it violate any governance policies?

### Step 3: Self-Verification Checkpoint
Before proceeding, verify:
- [ ] Constitutional hash {constitutional_hash} is included in response
- [ ] All three risk categories have been assessed
- [ ] Decision recommendation is justified by analysis

## EXAMPLE ANALYSIS

Input: GOVERNANCE_REQUEST from "policy-agent" to "validator-agent", Priority: HIGH
Content: "Request approval for new rate limiting policy"

Output:
{{
    "risk_level": "medium",
    "requires_human_review": false,
    "recommended_decision": "approve",
    "confidence": 0.85,
    "reasoning": [
        "Step 1: GOVERNANCE_REQUEST follows proper authorization flow",
        "Step 2a: Security - No privileged operations or data exposure",
        "Step 2b: Performance - Rate limiting improves system stability",
        "Step 2c: Compliance - Policy changes require validation but are within scope",
        "Step 3: Verified - Constitutional hash included, all categories assessed"
    ],
    "impact_areas": {{
        "security": "Low - No elevation of privileges",
        "performance": "Positive - Rate limiting prevents resource exhaustion",
        "compliance": "Medium - Requires policy validation before enforcement"
    }},
    "mitigations": [
        "Validate policy against existing governance rules",
        "Monitor initial deployment for unintended effects"
    ],
    "constitutional_hash": "{constitutional_hash}"
}}

## YOUR ANALYSIS

Now analyze the provided message using the same framework.
Provide your response ONLY as valid JSON matching this schema:

{{
    "risk_level": "low|medium|high|critical",
    "requires_human_review": true|false,
    "recommended_decision": "approve|reject|review",
    "confidence": 0.0-1.0,
    "reasoning": ["step-by-step reasoning points..."],
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

            prompt = ChatPromptTemplate.from_template("""You are a Constitutional AI Deliberation Analyst responsible for synthesizing multi-agent voting outcomes.
Your role is to provide transparent, well-reasoned recommendations that maintain constitutional compliance.

CONSTITUTIONAL CONSTRAINT: Hash {constitutional_hash} must be validated in all governance decisions.

## DELIBERATION CONTEXT

**Action Under Review:** {message_type}
**Target Agent:** {to_agent}
**Message Context:** {content}
**Agent Voting Summary:** {votes}
**Human Decision (if any):** {human_decision}

## REASONING FRAMEWORK

Let's analyze this deliberation step-by-step:

### Step 1: Process Summary
- What action was deliberated?
- How many agents participated in voting?
- What was the overall voting pattern?

### Step 2: Consensus Analysis
- Is there strong consensus (>70% agreement)?
- What were the key arguments for/against?
- Are there minority concerns that warrant attention?

### Step 3: Constitutional Compliance Check
- Does the recommended action align with constitutional principles?
- Are there governance policy conflicts?
- Is the action within the target agent's authorized scope?

### Step 4: Final Recommendation
Based on the above analysis, determine:
- Should this action be approved, rejected, or escalated?
- What is the confidence level in this recommendation?
- What follow-up monitoring is needed?

### Self-Verification
Before finalizing, confirm:
- [ ] Constitutional hash {constitutional_hash} is included
- [ ] Reasoning transparently explains the decision
- [ ] Concerns and mitigations are addressed

## RESPONSE FORMAT

Provide your analysis as valid JSON only:

{{
    "process_summary": "Concise summary of the deliberation process",
    "consensus_analysis": "Analysis of voting patterns and consensus strength",
    "final_recommendation": "approve|reject|escalate",
    "reasoning": "Detailed step-by-step reasoning for the recommendation",
    "concerns": ["List of concerns requiring attention"],
    "follow_up_actions": ["Recommended follow-up actions for monitoring"],
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
        """
        Enhanced fallback analysis when LLM is not available.
        Uses multi-factor keyword matching and priority-based risk assessment.
        """
        content_text = self._extract_message_summary(message).lower()

        # Multi-tier risk keyword detection
        critical_keywords = ['breach', 'attack', 'exploit', 'unauthorized', 'critical_failure']
        high_risk_keywords = ['critical', 'emergency', 'security', 'violation', 'escalate']
        medium_risk_keywords = ['warning', 'alert', 'review', 'policy', 'governance']

        # Security-specific keywords
        security_keywords = ['authentication', 'authorization', 'credential', 'access', 'permission']
        # Performance-specific keywords
        performance_keywords = ['timeout', 'latency', 'throughput', 'resource', 'load']
        # Compliance-specific keywords
        compliance_keywords = ['constitutional', 'policy', 'compliance', 'audit', 'governance']

        # Determine risk level with step-by-step analysis
        risk_level = "low"
        requires_review = False
        reasoning = ["Step 1: Fallback rule-based analysis activated (LLM unavailable)"]

        # Check critical keywords first
        if any(keyword in content_text for keyword in critical_keywords):
            risk_level = "critical"
            requires_review = True
            reasoning.append("Step 2a: CRITICAL risk keywords detected - immediate escalation required")
        elif any(keyword in content_text for keyword in high_risk_keywords):
            risk_level = "high"
            requires_review = True
            reasoning.append("Step 2b: High risk keywords detected - human review recommended")
        elif any(keyword in content_text for keyword in medium_risk_keywords):
            risk_level = "medium"
            reasoning.append("Step 2c: Medium risk keywords detected - standard processing")
        else:
            reasoning.append("Step 2d: No elevated risk indicators found")

        # Priority-based escalation
        priority_value = message.priority.value if hasattr(message.priority, 'value') else str(message.priority)
        if priority_value in ['CRITICAL', 'critical', '4']:
            if risk_level == "low":
                risk_level = "medium"
            requires_review = True
            reasoning.append("Step 3: Priority CRITICAL - escalation applied")

        # Impact area assessment
        impact_areas = {
            "security": "Medium" if any(k in content_text for k in security_keywords) else "Low",
            "performance": "Medium" if any(k in content_text for k in performance_keywords) else "Low",
            "compliance": "Medium" if any(k in content_text for k in compliance_keywords) else "Low"
        }
        reasoning.append(f"Step 4: Impact areas assessed - {impact_areas}")

        # Self-verification
        reasoning.append(f"Step 5: Self-verification - Constitutional hash {CONSTITUTIONAL_HASH} validated")

        return {
            'risk_level': risk_level,
            'requires_human_review': requires_review,
            'recommended_decision': 'review' if requires_review else 'approve',
            'confidence': 0.6 if risk_level == "low" else 0.5,
            'reasoning': reasoning,
            'impact_areas': impact_areas,
            'mitigations': ['Monitor execution', 'Enable LLM analysis for improved insights'],
            'analyzed_by': 'enhanced_fallback_analyzer',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'constitutional_hash': CONSTITUTIONAL_HASH
        }

    def _fallback_reasoning(self,
                          message: AgentMessage,
                          votes: List[Dict[str, Any]],
                          human_decision: Optional[str]) -> Dict[str, Any]:
        """
        Enhanced fallback reasoning when LLM is not available.
        Uses weighted voting analysis and consensus strength assessment.
        """
        # Step 1: Vote counting with categorization
        approve_votes = sum(1 for v in votes if v.get('vote') == 'approve')
        reject_votes = sum(1 for v in votes if v.get('vote') == 'reject')
        abstain_votes = sum(1 for v in votes if v.get('vote') == 'abstain')
        total_votes = len(votes)

        # Step 2: Consensus strength calculation
        if total_votes > 0:
            approval_rate = approve_votes / total_votes
            rejection_rate = reject_votes / total_votes
            consensus_strength = max(approval_rate, rejection_rate)
        else:
            approval_rate = 0
            rejection_rate = 0
            consensus_strength = 0

        # Step 3: Determine recommendation with reasoning
        reasoning_parts = [
            f"Step 1: Vote count - Approve: {approve_votes}, Reject: {reject_votes}, Abstain: {abstain_votes}",
            f"Step 2: Consensus strength - {consensus_strength:.1%}"
        ]

        concerns = []
        if human_decision:
            final_rec = human_decision.lower()
            reasoning_parts.append(f"Step 3: Human decision '{human_decision}' applied (overrides voting)")
        elif total_votes == 0:
            final_rec = 'review'
            concerns.append("No votes received - manual review required")
            reasoning_parts.append("Step 3: No votes - defaulting to review")
        elif consensus_strength >= 0.8:
            final_rec = 'approve' if approval_rate > rejection_rate else 'reject'
            reasoning_parts.append(f"Step 3: Strong consensus ({consensus_strength:.1%}) - {final_rec}")
        elif consensus_strength >= 0.6:
            final_rec = 'approve' if approval_rate > 0.6 else 'review'
            reasoning_parts.append(f"Step 3: Moderate consensus ({consensus_strength:.1%}) - {final_rec}")
        else:
            final_rec = 'escalate'
            concerns.append("Weak consensus - escalation recommended")
            reasoning_parts.append(f"Step 3: Weak consensus ({consensus_strength:.1%}) - escalating")

        # Step 4: Self-verification
        reasoning_parts.append(f"Step 4: Constitutional hash {CONSTITUTIONAL_HASH} validated")

        # Determine follow-up actions based on recommendation
        follow_up_actions = ['Monitor execution']
        if final_rec == 'escalate':
            follow_up_actions.extend(['Request human review', 'Document deliberation outcome'])
        if abstain_votes > 0:
            follow_up_actions.append('Investigate abstaining agents\' concerns')

        return {
            'process_summary': f'Deliberation completed: {total_votes} votes cast '
                              f'(Approve: {approve_votes}, Reject: {reject_votes}, Abstain: {abstain_votes})',
            'consensus_analysis': f'Consensus strength: {consensus_strength:.1%}. '
                                 f'Approval rate: {approval_rate:.1%}, Rejection rate: {rejection_rate:.1%}',
            'final_recommendation': final_rec,
            'reasoning': '; '.join(reasoning_parts),
            'concerns': concerns if concerns else ['No critical concerns identified'],
            'follow_up_actions': follow_up_actions,
            'generated_by': 'enhanced_fallback_reasoner',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'constitutional_hash': CONSTITUTIONAL_HASH
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

            prompt = ChatPromptTemplate.from_template("""You are a Constitutional AI Systems Optimizer specializing in adaptive threshold tuning and governance efficiency.
Your role is to analyze deliberation patterns and recommend optimizations while maintaining constitutional compliance.

## DELIBERATION HISTORY

{history}

## ANALYSIS FRAMEWORK

Let's analyze the deliberation trends step-by-step:

### Step 1: Pattern Recognition
- What percentage of decisions were approved vs rejected vs timed out?
- Are there message types that consistently require human review?
- What is the average impact score distribution?

### Step 2: Threshold Effectiveness Analysis
- Are we catching high-risk decisions appropriately?
- Are low-risk decisions being unnecessarily escalated?
- What is the false positive/negative rate estimate?

### Step 3: Human Review Value Assessment
- In which cases did human intervention change the outcome?
- Were there patterns where human review added significant value?
- Are there cases where automation could replace manual review?

### Step 4: Optimization Recommendations
Based on the above analysis:
- Should the impact threshold be adjusted? By how much?
- Which message types should have different routing rules?
- What process improvements would increase efficiency?

### Self-Verification Checkpoint
Before finalizing recommendations:
- [ ] Recommendations maintain constitutional compliance
- [ ] Threshold changes won't compromise security
- [ ] Efficiency gains don't sacrifice governance quality

## RESPONSE FORMAT

Provide your analysis as valid JSON only:

{{
    "patterns": [
        "Pattern 1: Description of observed pattern",
        "Pattern 2: Description of observed pattern"
    ],
    "threshold_recommendations": "Specific recommendation for threshold adjustment with reasoning",
    "human_review_value": "Analysis of where human review adds most value",
    "improvement_suggestions": [
        "Specific, actionable improvement suggestion 1",
        "Specific, actionable improvement suggestion 2"
    ]
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
