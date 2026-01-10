import logging

# Core orchestrator
# Context management
from .context import (
    ContextManager,
    ConversationContext,
    ConversationState,
    Message,
    MessageRole,
    UserProfile,
)
from .core import (
    AIAssistant,
    AssistantConfig,
    AssistantState,
    ConversationListener,
    ProcessingResult,
    create_assistant,
)

# Dialog management
from .dialog import (
    ActionType,
    ConversationFlow,
    DialogAction,
    DialogManager,
    DialogPolicy,
    FlowNode,
    RuleBasedDialogPolicy,
)

# Agent Bus integration
from .integration import AgentBusIntegration, GovernanceDecision, IntegrationConfig

# NLU components
from .nlu import (
    BasicSentimentAnalyzer,
    EntityExtractor,
    IntentClassifier,
    NLUEngine,
    NLUResult,
    PatternEntityExtractor,
    RuleBasedIntentClassifier,
    SentimentAnalyzer,
)

# Response generation
from .response import (
    HybridResponseGenerator,
    LLMResponseGenerator,
    PersonalityConfig,
    ResponseConfig,
    ResponseGenerator,
    TemplateResponseGenerator,
)

logger = logging.getLogger(__name__)
"""
ACGS-2 AI Assistant Framework
Constitutional Hash: cdd01ef066bc6cf2

Production-ready AI assistant with constitutional governance integration.
Provides NLU, dialog management, and response generation with constitutional validation.

Example usage:
    from core.enhanced_agent_bus.ai_assistant import AIAssistant, create_assistant

    # Quick start
    assistant = await create_assistant(name="My Assistant")
    result = await assistant.process_message(
        user_id="user123",
        message="What is my order status?"
    )
    logging.info(result.response_text)

    # Full control
    from core.enhanced_agent_bus.ai_assistant import (
        AIAssistant,
        AssistantConfig,
        NLUEngine,
        DialogManager,
        ResponseGenerator,
    )

    config = AssistantConfig(
        name="Custom Assistant",
        enable_governance=True,
    )
    assistant = AIAssistant(config=config)
    await assistant.initialize()
"""

# Import centralized constitutional hash with fallback
try:
    from core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

__version__ = "1.0.0"
__constitutional_hash__ = CONSTITUTIONAL_HASH

__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    # Core
    "AIAssistant",
    "AssistantConfig",
    "AssistantState",
    "ProcessingResult",
    "ConversationListener",
    "create_assistant",
    # Context
    "ConversationContext",
    "ContextManager",
    "ConversationState",
    "Message",
    "MessageRole",
    "UserProfile",
    # NLU
    "NLUEngine",
    "NLUResult",
    "IntentClassifier",
    "RuleBasedIntentClassifier",
    "EntityExtractor",
    "PatternEntityExtractor",
    "SentimentAnalyzer",
    "BasicSentimentAnalyzer",
    # Dialog
    "DialogManager",
    "DialogAction",
    "ActionType",
    "DialogPolicy",
    "RuleBasedDialogPolicy",
    "ConversationFlow",
    "FlowNode",
    # Response
    "ResponseGenerator",
    "TemplateResponseGenerator",
    "LLMResponseGenerator",
    "HybridResponseGenerator",
    "ResponseConfig",
    "PersonalityConfig",
    # Integration
    "AgentBusIntegration",
    "IntegrationConfig",
    "GovernanceDecision",
]
