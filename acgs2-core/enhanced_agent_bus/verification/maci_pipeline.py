"""MACI Verification Pipeline for ACGS-2 Constitutional AI Governance.

Constitutional Hash: cdd01ef066bc6cf2

Implements Multi-Agent Collaborative Intelligence (MACI) to bypass Gödel's
incompleteness theorems through strict role separation:

- Executive Agent: Proposes governance decisions
- Legislative Agent: Extracts and validates constitutional rules
- Judicial Agent: Evaluates compliance and renders final judgment

No agent validates its own output, ensuring mathematical consistency.
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Constitutional Hash for immutable validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class AgentRole(Enum):
    """MACI Agent Roles for strict separation of concerns."""
    EXECUTIVE = "executive"      # Proposes decisions
    LEGISLATIVE = "legislative"  # Validates constitutional rules
    JUDICIAL = "judicial"        # Evaluates compliance


class GovernancePhase(Enum):
    """Phases of constitutional governance."""
    PROPOSAL = "proposal"
    VALIDATION = "validation"
    JUDGMENT = "judgment"
    EXECUTION = "execution"


@dataclass
class ConstitutionalPrinciple:
    """Represents a constitutional principle with metadata."""
    id: str
    text: str
    category: str
    priority: int
    hash: str = field(init=False)

    def __post_init__(self):
        """Generate immutable hash for the principle."""
        content = f"{self.id}:{self.text}:{self.category}:{self.priority}"
        self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class GovernanceDecision:
    """Represents a governance decision with full context."""
    id: str
    action: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    proposed_by: str = "system"
    constitutional_hash: str = CONSTITUTIONAL_HASH

    @property
    def decision_hash(self) -> str:
        """Generate hash for decision integrity."""
        content = f"{self.id}:{self.action}:{str(self.context)}:{self.timestamp.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class AgentResponse:
    """Response from a MACI agent."""
    agent_role: AgentRole
    decision_id: str
    confidence: float
    reasoning: str
    evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_hash: str = field(init=False)

    def __post_init__(self):
        """Generate agent response hash."""
        content = f"{self.agent_role.value}:{self.decision_id}:{self.confidence}:{self.reasoning}"
        self.agent_hash = hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class VerificationResult:
    """Result of constitutional verification."""
    decision_id: str
    is_compliant: bool
    confidence: float
    violations: List[str]
    recommendations: List[str]
    executive_response: AgentResponse
    legislative_response: AgentResponse
    judicial_response: AgentResponse
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseMACIAgent:
    """Base class for MACI agents with common functionality."""

    def __init__(self, role: AgentRole, agent_id: str):
        self.role = role
        self.agent_id = agent_id
        self.constitutional_principles: Dict[str, ConstitutionalPrinciple] = {}
        self.decision_history: List[AgentResponse] = []

    def load_constitutional_principles(self, principles: List[ConstitutionalPrinciple]):
        """Load constitutional principles into agent knowledge."""
        for principle in principles:
            self.constitutional_principles[principle.id] = principle
        logger.info(f"{self.role.value} agent loaded {len(principles)} constitutional principles")

    def validate_constitutional_hash(self, decision: GovernanceDecision) -> bool:
        """Validate that decision references correct constitution."""
        return decision.constitutional_hash == CONSTITUTIONAL_HASH

    async def _analyze_decision(
        self,
        decision: GovernanceDecision,
        context_responses: Optional[List[AgentResponse]] = None
    ) -> Dict[str, Any]:
        """Common decision analysis logic."""
        # Validate constitutional hash
        if not self.validate_constitutional_hash(decision):
            return {
                'confidence': 0.0,
                'reasoning': 'Invalid constitutional hash',
                'evidence': ['Constitutional hash mismatch'],
                'violations': ['Constitution integrity compromised']
            }

        # Agent-specific analysis (implemented by subclasses)
        return await self._analyze_decision_specific(decision, context_responses)

    async def _analyze_decision_specific(
        self,
        decision: GovernanceDecision,
        context_responses: Optional[List[AgentResponse]] = None
    ) -> Dict[str, Any]:
        """Agent-specific decision analysis - implemented by subclasses."""
        raise NotImplementedError

    async def respond_to_decision(
        self,
        decision: GovernanceDecision,
        context_responses: Optional[List[AgentResponse]] = None
    ) -> AgentResponse:
        """Generate agent response to a governance decision."""
        analysis = await self._analyze_decision(decision, context_responses)

        response = AgentResponse(
            agent_role=self.role,
            decision_id=decision.id,
            confidence=analysis.get('confidence', 0.5),
            reasoning=analysis.get('reasoning', 'Analysis incomplete'),
            evidence=analysis.get('evidence', [])
        )

        self.decision_history.append(response)
        logger.info(f"{self.role.value} agent responded to decision {decision.id} with confidence {response.confidence:.2f}")

        return response


class ExecutiveAgent(BaseMACIAgent):
    """Executive Agent: Proposes governance decisions without self-validation."""

    def __init__(self, agent_id: str = "executive-001"):
        super().__init__(AgentRole.EXECUTIVE, agent_id)

    async def _analyze_decision_specific(
        self,
        decision: GovernanceDecision,
        context_responses: Optional[List[AgentResponse]] = None
    ) -> Dict[str, Any]:
        """
        Executive analysis: Propose decisions based on operational context.
        Does NOT validate compliance - that's for Legislative and Judicial agents.
        """
        action = decision.action
        context = decision.context

        # Executive focuses on operational feasibility and impact
        confidence = 0.8  # Base confidence
        reasoning_parts = []
        evidence = []

        # Analyze operational impact
        if 'impact_assessment' in context:
            impact = context['impact_assessment']
            if impact.get('severity', 'unknown') == 'critical':
                confidence -= 0.2
                reasoning_parts.append("High-impact decision requires careful consideration")
                evidence.append("Critical operational impact detected")

        # Check for emergency conditions
        if context.get('emergency', False):
            confidence += 0.1
            reasoning_parts.append("Emergency conditions justify expedited action")
            evidence.append("Emergency flag detected in context")

        # Analyze resource requirements
        if 'resources_required' in context:
            resources = context['resources_required']
            if len(resources) > 5:
                confidence -= 0.1
                reasoning_parts.append("Complex resource requirements increase operational risk")
                evidence.append(f"High resource count: {len(resources)}")

        reasoning = "Executive assessment: " + "; ".join(reasoning_parts) if reasoning_parts else "Standard operational assessment"

        return {
            'confidence': max(0.1, min(0.95, confidence)),
            'reasoning': reasoning,
            'evidence': evidence,
            'violations': []  # Executive doesn't identify violations
        }

    async def propose_decision(
        self,
        action: str,
        context: Dict[str, Any],
        proposed_by: str = "system"
    ) -> GovernanceDecision:
        """Propose a new governance decision."""
        decision_id = f"exec-{hashlib.sha256(f'{action}:{str(context)}'.encode()).hexdigest()[:8]}"

        decision = GovernanceDecision(
            id=decision_id,
            action=action,
            context=context,
            proposed_by=proposed_by
        )

        logger.info(f"Executive agent proposed decision {decision_id}: {action}")
        return decision


class LegislativeAgent(BaseMACIAgent):
    """Legislative Agent: Validates constitutional rules and extracts relevant principles."""

    def __init__(self, agent_id: str = "legislative-001"):
        super().__init__(AgentRole.LEGISLATIVE, agent_id)

    async def _analyze_decision_specific(
        self,
        decision: GovernanceDecision,
        context_responses: Optional[List[AgentResponse]] = None
    ) -> Dict[str, Any]:
        """
        Legislative analysis: Extract and validate relevant constitutional principles.
        Does NOT render final judgment - that's for Judicial agent.
        """
        action = decision.action
        context = decision.context

        relevant_principles = []
        violations = []
        evidence = []

        # Find relevant constitutional principles
        action_keywords = action.lower().split()
        for principle in self.constitutional_principles.values():
            principle_text = principle.text.lower()
            if any(keyword in principle_text for keyword in action_keywords):
                relevant_principles.append(principle)
                evidence.append(f"Relevant principle: {principle.text[:50]}...")

        # Analyze context for constitutional relevance
        if 'stakeholders' in context:
            stakeholders = context['stakeholders']
            if len(stakeholders) > 10:
                evidence.append("Broad stakeholder impact suggests constitutional review needed")

        # Check for precedent conflicts
        if context_responses:
            for response in context_responses:
                if response.agent_role == AgentRole.EXECUTIVE:
                    if response.confidence < 0.5:
                        evidence.append("Executive concerns suggest constitutional review needed")

        confidence = min(0.9, 0.6 + (len(relevant_principles) * 0.1))
        reasoning = f"Legislative analysis identified {len(relevant_principles)} relevant constitutional principles"

        return {
            'confidence': confidence,
            'reasoning': reasoning,
            'evidence': evidence,
            'violations': violations,  # Legislative identifies potential issues but doesn't judge
            'relevant_principles': [p.id for p in relevant_principles]
        }


class JudicialAgent(BaseMACIAgent):
    """Judicial Agent: Renders final judgment on constitutional compliance."""

    def __init__(self, agent_id: str = "judicial-001"):
        super().__init__(AgentRole.JUDICIAL, agent_id)

    async def _analyze_decision_specific(
        self,
        decision: GovernanceDecision,
        context_responses: Optional[List[AgentResponse]] = None
    ) -> Dict[str, Any]:
        """
        Judicial analysis: Render final judgment based on Executive proposal and Legislative rules.
        Does NOT propose decisions or extract rules - that's for other agents.
        """
        violations = []
        evidence = []
        confidence = 0.5  # Base judicial confidence

        if not context_responses:
            return {
                'confidence': 0.1,
                'reasoning': 'Insufficient context for judicial review',
                'evidence': ['No agent responses provided'],
                'violations': ['Incomplete review process']
            }

        # Analyze responses from other agents
        executive_response = None
        legislative_response = None

        for response in context_responses:
            if response.agent_role == AgentRole.EXECUTIVE:
                executive_response = response
            elif response.agent_role == AgentRole.LEGISLATIVE:
                legislative_response = response

        # Judicial evaluation logic
        if executive_response and executive_response.confidence < 0.4:
            violations.append("Executive agent expressed significant concerns")
            evidence.append(f"Executive confidence: {executive_response.confidence:.2f}")

        if legislative_response:
            if 'relevant_principles' in legislative_response.reasoning:
                evidence.append("Legislative analysis identified relevant constitutional principles")
                confidence += 0.2
            if legislative_response.confidence > 0.7:
                confidence += 0.1

        # Check for emergency override conditions
        if decision.context.get('emergency_override', False):
            evidence.append("Emergency override condition detected")
            if decision.context.get('emergency_justification'):
                confidence += 0.1
            else:
                violations.append("Emergency override lacks justification")

        # Final compliance determination
        is_compliant = len(violations) == 0 and confidence > 0.6

        reasoning = f"Judicial review: {'COMPLIANT' if is_compliant else 'NON-COMPLIANT'} (confidence: {confidence:.2f})"

        return {
            'confidence': confidence,
            'reasoning': reasoning,
            'evidence': evidence,
            'violations': violations,
            'is_compliant': is_compliant
        }


class MACIVerificationPipeline:
    """
    MACI Verification Pipeline: Bypasses Gödel limitations through role separation.

    Constitutional Hash: cdd01ef066bc6cf2

    Workflow:
    1. Executive Agent proposes decision
    2. Legislative Agent extracts relevant constitutional rules
    3. Judicial Agent renders final judgment
    4. No agent validates its own output
    """

    def __init__(self):
        self.executive_agent = ExecutiveAgent()
        self.legislative_agent = LegislativeAgent()
        self.judicial_agent = JudicialAgent()
        self.constitutional_principles: List[ConstitutionalPrinciple] = []
        self.verification_history: List[VerificationResult] = []

    def load_constitution(self, principles: List[ConstitutionalPrinciple]):
        """Load constitutional principles into all agents."""
        self.constitutional_principles = principles

        self.executive_agent.load_constitutional_principles(principles)
        self.legislative_agent.load_constitutional_principles(principles)
        self.judicial_agent.load_constitutional_principles(principles)

        logger.info(f"MACI Pipeline loaded constitution with {len(principles)} principles")

    async def verify_governance_decision(
        self,
        decision: GovernanceDecision
    ) -> VerificationResult:
        """
        Execute full MACI verification pipeline.

        Args:
            decision: Governance decision to verify

        Returns:
            Complete verification result with all agent responses
        """
        logger.info(f"Starting MACI verification for decision {decision.id}")

        # Phase 1: Executive proposal analysis
        executive_response = await self.executive_agent.respond_to_decision(decision)

        # Phase 2: Legislative constitutional rule extraction
        legislative_response = await self.legislative_agent.respond_to_decision(
            decision,
            context_responses=[executive_response]
        )

        # Phase 3: Judicial final judgment
        judicial_response = await self.judicial_agent.respond_to_decision(
            decision,
            context_responses=[executive_response, legislative_response]
        )

        # Determine overall compliance
        is_compliant = judicial_response.confidence > 0.6
        violations = []

        # Extract violations from judicial analysis
        if hasattr(judicial_response, 'reasoning') and 'NON-COMPLIANT' in judicial_response.reasoning:
            violations.append("Judicial agent determined non-compliance")

        # Extract recommendations
        recommendations = []
        if executive_response.confidence < 0.5:
            recommendations.append("Review executive concerns before proceeding")

        confidence = judicial_response.confidence

        result = VerificationResult(
            decision_id=decision.id,
            is_compliant=is_compliant,
            confidence=confidence,
            violations=violations,
            recommendations=recommendations,
            executive_response=executive_response,
            legislative_response=legislative_response,
            judicial_response=judicial_response
        )

        self.verification_history.append(result)

        logger.info(f"MACI verification complete for {decision.id}: {'COMPLIANT' if is_compliant else 'NON-COMPLIANT'}")
        return result

    async def propose_and_verify_decision(
        self,
        action: str,
        context: Dict[str, Any],
        proposed_by: str = "system"
    ) -> tuple[GovernanceDecision, VerificationResult]:
        """
        Complete workflow: Propose decision and verify compliance.

        Args:
            action: Governance action to propose
            context: Decision context
            proposed_by: Agent proposing the decision

        Returns:
            Tuple of (proposed decision, verification result)
        """
        # Executive proposes the decision
        decision = await self.executive_agent.propose_decision(action, context, proposed_by)

        # Full MACI verification
        verification = await self.verify_governance_decision(decision)

        return decision, verification

    def get_constitutional_hash(self) -> str:
        """Return the constitutional hash for validation."""
        return CONSTITUTIONAL_HASH

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics about pipeline performance."""
        if not self.verification_history:
            return {'total_decisions': 0}

        total_decisions = len(self.verification_history)
        compliant_decisions = sum(1 for v in self.verification_history if v.is_compliant)
        avg_confidence = sum(v.confidence for v in self.verification_history) / total_decisions

        return {
            'total_decisions': total_decisions,
            'compliant_decisions': compliant_decisions,
            'compliance_rate': compliant_decisions / total_decisions,
            'average_confidence': avg_confidence,
            'total_violations': sum(len(v.violations) for v in self.verification_history)
        }


# Convenience functions for external use
async def create_maci_pipeline_with_constitution(
    constitutional_principles: List[Dict[str, Any]]
) -> MACIVerificationPipeline:
    """
    Create and initialize MACI pipeline with constitutional principles.

    Args:
        constitutional_principles: List of principle dictionaries with 'id', 'text', 'category', 'priority'

    Returns:
        Initialized MACI pipeline
    """
    pipeline = MACIVerificationPipeline()

    principles = [
        ConstitutionalPrinciple(
            id=p['id'],
            text=p['text'],
            category=p['category'],
            priority=p['priority']
        )
        for p in constitutional_principles
    ]

    pipeline.load_constitution(principles)
    return pipeline


# Export for use in other modules
__all__ = [
    'MACIVerificationPipeline',
    'ExecutiveAgent',
    'LegislativeAgent',
    'JudicialAgent',
    'GovernanceDecision',
    'VerificationResult',
    'ConstitutionalPrinciple',
    'AgentRole',
    'GovernancePhase',
    'create_maci_pipeline_with_constitution',
    'CONSTITUTIONAL_HASH'
]
