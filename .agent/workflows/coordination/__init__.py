"""
ACGS-2 Coordination Workflows
Constitutional Hash: cdd01ef066bc6cf2

Multi-agent coordination workflow implementations:
- VotingWorkflow: Consensus-based decision making
- DiscoveryWorkflow: Agent capability discovery
- HandoffWorkflow: Agent-to-agent task handoff
- SwarmWorkflow: Swarm intelligence coordination
"""

from .voting import VotingWorkflow, VotingResult, VotingStrategy
from .handoff import HandoffWorkflow, HandoffResult

__all__ = [
    "VotingWorkflow",
    "VotingResult",
    "VotingStrategy",
    "HandoffWorkflow",
    "HandoffResult",
]
