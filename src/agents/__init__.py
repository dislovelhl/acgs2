"""
ACGS-2 Agent SDK Integration Package.

This package provides Claude Agent SDK-based agents for automated governance operations:
- Governance Policy Analysis Agent
- Constitutional Compliance Review Agent
- Regulatory Research Agent
- C4 Documentation Generation Agent
"""

from .base import AgentConfig, BaseGovernanceAgent
from .c4_docs_agent import C4DocsAgent
from .compliance_review_agent import ComplianceReviewAgent
from .governance_policy_agent import GovernancePolicyAgent
from .regulatory_research_agent import RegulatoryResearchAgent

__all__ = [
    "BaseGovernanceAgent",
    "AgentConfig",
    "GovernancePolicyAgent",
    "ComplianceReviewAgent",
    "RegulatoryResearchAgent",
    "C4DocsAgent",
]
