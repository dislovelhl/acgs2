"""
LLM Reasoner for Constitutional Retrieval System

Integrates retrieved constitutional documents and precedents with LLM reasoning
to provide enhanced decision support for fuzzy legal scenarios.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .retrieval_engine import RetrievalEngine

logger = logging.getLogger(__name__)


class LLMReasoner:
    """LLM-powered reasoner that integrates retrieved context for decision enhancement."""

    def __init__(self, retrieval_engine: RetrievalEngine,
                 openai_api_key: Optional[str] = None,
                 model_name: str = "gpt-4"):
        """
        Initialize LLM reasoner.

        Args:
            retrieval_engine: Engine for retrieving relevant documents
            openai_api_key: OpenAI API key
            model_name: GPT model to use
        """
        self.retrieval_engine = retrieval_engine
        self.model_name = model_name
        self.llm = None

        if LANGCHAIN_AVAILABLE:
            try:
                self.llm = ChatOpenAI(
                    model_name=model_name,
                    temperature=0.1,  # Low temperature for consistent legal reasoning
                    openai_api_key=openai_api_key
                )
                logger.info(f"Initialized LLM reasoner with {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM reasoner: {e}")
        else:
            logger.warning("LangChain not available, LLM reasoning disabled")

    async def reason_with_context(self, query: str, context_documents: List[Dict[str, Any]],
                                decision_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform reasoning with retrieved constitutional context.

        Args:
            query: The legal question or scenario
            context_documents: Retrieved relevant documents
            decision_criteria: Additional decision criteria

        Returns:
            Reasoning result with recommendation and confidence
        """
        if not self.llm:
            return self._fallback_reasoning(query, context_documents, decision_criteria)

        try:
            # Prepare context summary
            context_summary = self._summarize_context(context_documents)

            # Create reasoning prompt
            prompt = ChatPromptTemplate.from_template("""
            You are a constitutional law expert providing reasoned analysis for a legal decision.
            Your task is to analyze the given legal scenario using relevant constitutional provisions
            and precedents, then provide a well-reasoned recommendation.

            Legal Scenario:
            {query}

            Relevant Constitutional Context:
            {context}

            Decision Criteria:
            {criteria}

            Please provide:
            1. Summary of the legal issue
            2. Analysis of applicable constitutional provisions
            3. Relevant precedents and their application
            4. Your reasoned recommendation
            5. Confidence level in your analysis (0-1)
            6. Key factors influencing the decision
            7. Potential counterarguments or alternative interpretations

            Format as JSON:
            {{
                "issue_summary": "brief summary of the legal issue",
                "constitutional_analysis": "analysis of relevant provisions",
                "precedent_application": "how precedents apply",
                "recommendation": "approve|deny|further_review",
                "confidence": 0.0-1.0,
                "key_factors": ["factor1", "factor2"],
                "counterarguments": ["argument1", "argument2"],
                "reasoning_trace": "step-by-step reasoning process"
            }}
            """)

            criteria_text = self._format_decision_criteria(decision_criteria)

            formatted_prompt = prompt.format_messages(
                query=query,
                context=context_summary,
                criteria=criteria_text
            )

            # Get LLM response
            response = await self.llm.ainvoke(formatted_prompt)
            parser = JsonOutputParser()
            reasoning_result = parser.parse(response.content)

            # Add metadata
            reasoning_result.update({
                'reasoned_by': 'llm_reasoner',
                'model': self.model_name,
                'context_documents_used': len(context_documents),
                'timestamp': datetime.utcnow().isoformat(),
                'query': query
            })

            logger.info(f"LLM reasoning completed for query: {query[:50]}...")
            return reasoning_result

        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            return self._fallback_reasoning(query, context_documents, decision_criteria)

    async def analyze_precedent_conflict(self, case_description: str,
                                       conflicting_precedents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze conflicts between multiple precedents.

        Args:
            case_description: Description of the current case
            conflicting_precedents: List of potentially conflicting precedents

        Returns:
            Analysis of precedent conflicts and resolution approach
        """
        if not self.llm:
            return self._fallback_conflict_analysis(case_description, conflicting_precedents)

        try:
            # Summarize precedents
            precedent_summaries = []
            for i, precedent in enumerate(conflicting_precedents):
                summary = self._summarize_precedent(precedent)
                precedent_summaries.append(f"Precedent {i+1}: {summary}")

            precedents_text = "\n".join(precedent_summaries)

            prompt = ChatPromptTemplate.from_template("""
            You are analyzing potential conflicts between legal precedents in the context of a new case.

            Current Case:
            {case_description}

            Potentially Conflicting Precedents:
            {precedents}

            Please analyze:
            1. Whether there is a genuine conflict between these precedents
            2. The nature and scope of any conflict
            3. How to reconcile or distinguish the precedents
            4. Recommended approach for the current case
            5. Factors that might influence precedent selection

            Format as JSON:
            {{
                "conflict_exists": true|false,
                "conflict_nature": "description of the conflict",
                "reconciliation_approach": "how to resolve the conflict",
                "recommended_approach": "approach for current case",
                "influencing_factors": ["factor1", "factor2"],
                "precedent_hierarchy": ["most_relevant", "less_relevant"]
            }}
            """)

            formatted_prompt = prompt.format_messages(
                case_description=case_description,
                precedents=precedents_text
            )

            response = await self.llm.ainvoke(formatted_prompt)
            parser = JsonOutputParser()
            analysis = parser.parse(response.content)

            analysis.update({
                'analyzed_by': 'llm_reasoner',
                'precedents_analyzed': len(conflicting_precedents),
                'timestamp': datetime.utcnow().isoformat()
            })

            return analysis

        except Exception as e:
            logger.error(f"Precedent conflict analysis failed: {e}")
            return self._fallback_conflict_analysis(case_description, conflicting_precedents)

    async def generate_decision_explanation(self, decision: Dict[str, Any],
                                          context_used: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable explanation of the decision.

        Args:
            decision: The decision result
            context_used: Context documents used in decision

        Returns:
            Natural language explanation
        """
        if not self.llm:
            return self._fallback_explanation(decision, context_used)

        try:
            # Prepare context summary
            context_summary = "\n".join([
                f"- {doc.get('payload', {}).get('title', 'Unknown')}: {doc.get('payload', {}).get('content', '')[:200]}..."
                for doc in context_used[:3]  # Limit to top 3
            ])

            prompt = ChatPromptTemplate.from_template("""
            Generate a clear, concise explanation of this legal decision for stakeholders.

            Decision Details:
            {decision}

            Key Context Used:
            {context}

            Please provide a natural language explanation that:
            - Summarizes the decision
            - Explains the key reasoning
            - Highlights relevant constitutional principles
            - Notes any uncertainties or caveats

            Keep the explanation professional, clear, and accessible to non-lawyers.
            """)

            decision_text = f"""
            Recommendation: {decision.get('recommendation', 'Unknown')}
            Confidence: {decision.get('confidence', 0.0)}
            Key Factors: {', '.join(decision.get('key_factors', []))}
            """

            formatted_prompt = prompt.format_messages(
                decision=decision_text,
                context=context_summary
            )

            response = await self.llm.ainvoke(formatted_prompt)
            explanation = response.content.strip()

            return explanation

        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return self._fallback_explanation(decision, context_used)

    async def assess_decision_consistency(self, decision: Dict[str, Any],
                                        historical_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess consistency of current decision with historical decisions.

        Args:
            decision: Current decision
            historical_decisions: Previous similar decisions

        Returns:
            Consistency analysis
        """
        if not self.llm or not historical_decisions:
            return self._fallback_consistency_check(decision, historical_decisions)

        try:
            # Summarize historical decisions
            historical_summary = "\n".join([
                f"Case {i+1}: {hist.get('recommendation', 'Unknown')} "
                f"(confidence: {hist.get('confidence', 0.0)})"
                for i, hist in enumerate(historical_decisions[:5])
            ])

            prompt = ChatPromptTemplate.from_template("""
            Assess the consistency of a current legal decision with historical decisions.

            Current Decision:
            Recommendation: {current_recommendation}
            Confidence: {current_confidence}
            Key Factors: {current_factors}

            Historical Decisions:
            {historical}

            Please evaluate:
            1. Overall consistency with historical decisions
            2. Any deviations and their justification
            3. Patterns in decision making
            4. Recommendations for maintaining consistency

            Format as JSON:
            {{
                "consistency_score": 0.0-1.0,
                "consistency_level": "high|medium|low",
                "deviations": ["deviation1", "deviation2"],
                "patterns_identified": ["pattern1", "pattern2"],
                "consistency_recommendations": ["rec1", "rec2"]
            }}
            """)

            formatted_prompt = prompt.format_messages(
                current_recommendation=decision.get('recommendation', 'Unknown'),
                current_confidence=decision.get('confidence', 0.0),
                current_factors=', '.join(decision.get('key_factors', [])),
                historical=historical_summary
            )

            response = await self.llm.ainvoke(formatted_prompt)
            parser = JsonOutputParser()
            analysis = parser.parse(response.content)

            return analysis

        except Exception as e:
            logger.error(f"Consistency assessment failed: {e}")
            return self._fallback_consistency_check(decision, historical_decisions)

    def _summarize_context(self, documents: List[Dict[str, Any]]) -> str:
        """Summarize retrieved context documents."""
        if not documents:
            return "No relevant context documents found."

        summaries = []
        for doc in documents[:5]:  # Limit to top 5
            payload = doc.get('payload', {})
            title = payload.get('title', payload.get('doc_id', 'Unknown Document'))
            content = payload.get('content', '')[:300]  # Truncate content
            score = doc.get('score', 0.0)

            summary = f"Document: {title}\nRelevance: {score:.3f}\nContent: {content}..."
            summaries.append(summary)

        return "\n\n".join(summaries)

    def _format_decision_criteria(self, criteria: Optional[Dict[str, Any]]) -> str:
        """Format decision criteria for LLM context."""
        if not criteria:
            return "No specific decision criteria provided. Use general constitutional principles."

        criteria_items = []
        for key, value in criteria.items():
            criteria_items.append(f"- {key}: {value}")

        return "\n".join(criteria_items)

    def _summarize_precedent(self, precedent: Dict[str, Any]) -> str:
        """Summarize a single precedent."""
        payload = precedent.get('payload', {})
        case_id = payload.get('case_id', 'Unknown')
        outcome = payload.get('outcome', 'Unknown')
        court = payload.get('court', 'Unknown Court')

        content = payload.get('content', '')[:200]
        return f"Case {case_id} ({court}): {outcome} - {content}..."

    def _fallback_reasoning(self, query: str, context_documents: List[Dict[str, Any]],
                          decision_criteria: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback reasoning when LLM is unavailable."""
        # Simple rule-based reasoning
        context_count = len(context_documents)

        # Basic decision logic
        if context_count == 0:
            recommendation = "further_review"
            confidence = 0.3
        elif any(doc.get('score', 0) > 0.8 for doc in context_documents):
            recommendation = "approve"
            confidence = 0.7
        else:
            recommendation = "further_review"
            confidence = 0.5

        return {
            'issue_summary': f'Legal query: {query[:100]}...',
            'constitutional_analysis': f'Based on {context_count} relevant documents',
            'precedent_application': 'Automated analysis (LLM unavailable)',
            'recommendation': recommendation,
            'confidence': confidence,
            'key_factors': ['document_relevance', 'context_availability'],
            'counterarguments': ['Limited analysis without LLM'],
            'reasoning_trace': 'Rule-based fallback reasoning',
            'reasoned_by': 'fallback_reasoner',
            'timestamp': datetime.utcnow().isoformat()
        }

    def _fallback_conflict_analysis(self, case_description: str,
                                  conflicting_precedents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback conflict analysis."""
        return {
            'conflict_exists': len(conflicting_precedents) > 1,
            'conflict_nature': 'Multiple precedents identified',
            'reconciliation_approach': 'Manual review recommended',
            'recommended_approach': 'further_review',
            'influencing_factors': ['precedent_count', 'similarity_scores'],
            'precedent_hierarchy': [f'precedent_{i+1}' for i in range(len(conflicting_precedents))],
            'analyzed_by': 'fallback_analyzer'
        }

    def _fallback_explanation(self, decision: Dict[str, Any],
                            context_used: List[Dict[str, Any]]) -> str:
        """Fallback explanation generation."""
        recommendation = decision.get('recommendation', 'Unknown')
        confidence = decision.get('confidence', 0.0)
        context_count = len(context_used)

        return f"""
        Decision: {recommendation}
        Confidence Level: {confidence:.2f}
        Context Documents Used: {context_count}

        This decision was made based on automated analysis of relevant constitutional
        documents and precedents. For detailed legal reasoning, please consult with
        legal experts. (LLM explanation unavailable)
        """.strip()

    def _fallback_consistency_check(self, decision: Dict[str, Any],
                                  historical_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback consistency check."""
        if not historical_decisions:
            return {
                'consistency_score': 1.0,
                'consistency_level': 'high',
                'deviations': [],
                'patterns_identified': ['First decision in series'],
                'consistency_recommendations': ['Establish baseline']
            }

        # Simple consistency check
        current_rec = decision.get('recommendation', '')
        historical_recs = [hist.get('recommendation', '') for hist in historical_decisions]

        matches = sum(1 for rec in historical_recs if rec == current_rec)
        consistency_score = matches / len(historical_recs)

        level = 'high' if consistency_score > 0.8 else 'medium' if consistency_score > 0.5 else 'low'

        return {
            'consistency_score': consistency_score,
            'consistency_level': level,
            'deviations': ['Consistency analysis limited without LLM'],
            'patterns_identified': [f'{matches}/{len(historical_recs)} matching recommendations'],
            'consistency_recommendations': ['Use LLM for detailed analysis']
        }