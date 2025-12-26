"""
ACGS-2 AI Assistant Framework
Constitutional Hash: cdd01ef066bc6cf2

Production-ready AI assistant with constitutional governance integration.
Provides NLU, dialog management, and response generation with constitutional validation.

Example usage:
    from enhanced_agent_bus.ai_assistant import AIAssistant, create_assistant

    # Quick start
    assistant = await create_assistant(name="My Assistant")
    result = await assistant.process_message(
        user_id="user123",
        message="What is my order status?"
    )
    print(result.response_text)

    # Full control
    from enhanced_agent_bus.ai_assistant import (
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
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

__version__ = "1.0.0"
__constitutional_hash__ = CONSTITUTIONAL_HASH

# Core orchestrator
from .core import (
    AIAssistant,
    AssistantConfig,
    AssistantState,
    ProcessingResult,
    ConversationListener,
    create_assistant,
)

# Context management
from .context import (
    ConversationContext,
    ContextManager,
    ConversationState,
    Message,
    MessageRole,
    UserProfile,
)

# NLU components
from .nlu import (
    NLUEngine,
    NLUResult,
    IntentClassifier,
    RuleBasedIntentClassifier,
    EntityExtractor,
    PatternEntityExtractor,
    SentimentAnalyzer,
    BasicSentimentAnalyzer,
)

# Dialog management
from .dialog import (
    DialogManager,
    DialogAction,
    ActionType,
    DialogPolicy,
    RuleBasedDialogPolicy,
    ConversationFlow,
    FlowNode,
)

# Response generation
from .response import (
    ResponseGenerator,
    TemplateResponseGenerator,
    LLMResponseGenerator,
    HybridResponseGenerator,
    ResponseConfig,
    PersonalityConfig,
)

# Agent Bus integration
from .integration import (
    AgentBusIntegration,
    IntegrationConfig,
    GovernanceDecision,
)

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
