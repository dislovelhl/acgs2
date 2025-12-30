"""
ACGS-2 NeMo-Agent-Toolkit Integration
Constitutional Hash: cdd01ef066bc6cf2

Bridges ACGS-2 constitutional governance with NVIDIA NeMo-Agent-Toolkit
for enterprise-grade AI agent deployment with constitutional compliance.
"""

from nemo_agent_toolkit.agent_wrapper import (
    ConstitutionalAgentWrapper,
    wrap_crewai_agent,
    wrap_langchain_agent,
    wrap_llamaindex_agent,
)
from nemo_agent_toolkit.constitutional_guardrails import (
    ConstitutionalGuardrails,
    GuardrailConfig,
    GuardrailResult,
)
from nemo_agent_toolkit.mcp_bridge import (
    ACGS2MCPClient,
    ACGS2MCPServer,
    ConstitutionalMCPTool,
)
from nemo_agent_toolkit.profiler import (
    ConstitutionalProfiler,
    GovernanceMetrics,
)

CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"

__all__ = [
    "CONSTITUTIONAL_HASH",
    "ConstitutionalGuardrails",
    "GuardrailConfig",
    "GuardrailResult",
    "ACGS2MCPServer",
    "ACGS2MCPClient",
    "ConstitutionalMCPTool",
    "ConstitutionalAgentWrapper",
    "wrap_langchain_agent",
    "wrap_llamaindex_agent",
    "wrap_crewai_agent",
    "ConstitutionalProfiler",
    "GovernanceMetrics",
]

__version__ = "2.0.0"
