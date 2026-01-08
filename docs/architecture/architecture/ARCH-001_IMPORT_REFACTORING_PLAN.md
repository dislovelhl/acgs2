# ARCH-001: Import Refactoring Plan

**Constitutional Hash:** cdd01ef066bc6cf2

## Files Identified for Refactoring

Total files needing refactoring: 330

### 1. message_processor.py
- **File:** src/core/enhanced_agent_bus/message_processor.py
- **Complexity Score:** 80
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 14

### 2. imports.py
- **File:** src/core/enhanced_agent_bus/imports.py
- **Complexity Score:** 80
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 14

### 3. agent_bus.py
- **File:** src/core/enhanced_agent_bus/agent_bus.py
- **Complexity Score:** 60
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 10

### 4. integration.py
- **File:** src/core/enhanced_agent_bus/deliberation_layer/integration.py
- **Complexity Score:** 50
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 8

### 5. core.py
- **File:** src/core/enhanced_agent_bus/core.py
- **Complexity Score:** 40
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 6

### 6. registry.py
- **File:** src/core/enhanced_agent_bus/registry.py
- **Complexity Score:** 35
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 5

### 7. opa_client.py
- **File:** src/core/enhanced_agent_bus/opa_client.py
- **Complexity Score:** 30
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 4

### 8. hitl_manager.py
- **File:** src/core/enhanced_agent_bus/deliberation_layer/hitl_manager.py
- **Complexity Score:** 30
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 4

### 9. compat.py
- **File:** src/core/enhanced_agent_bus/.venv/lib/python3.12/site-packages/pip/_vendor/distlib/compat.py
- **Complexity Score:** 30
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 4

### 10. compat.py
- **File:** src/core/enhanced_agent_bus/venv/lib/python3.12/site-packages/pip/_vendor/distlib/compat.py
- **Complexity Score:** 30
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 4

### 11. processing_strategies.py
- **File:** src/core/enhanced_agent_bus/processing_strategies.py
- **Complexity Score:** 25
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 3

### 12. validation_strategies.py
- **File:** src/core/enhanced_agent_bus/validation_strategies.py
- **Complexity Score:** 25
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 3

### 13. maci_enforcement.py
- **File:** src/core/enhanced_agent_bus/maci_enforcement.py
- **Complexity Score:** 25
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 3

### 14. kafka_bus.py
- **File:** src/core/enhanced_agent_bus/kafka_bus.py
- **Complexity Score:** 25
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 3

### 15. llm_assistant.py
- **File:** src/core/enhanced_agent_bus/deliberation_layer/llm_assistant.py
- **Complexity Score:** 25
- **Uses Centralized Imports:** False
- **Has Try/Except Imports:** True
- **Relative Import Fallbacks:** 3

## Refactoring Strategy

### Phase 1: Consolidate Import Usage
Ensure all files use the centralized imports module (.imports) for optional dependencies.

### Phase 2: Simplify Import Patterns
Replace complex try/except import blocks with simpler patterns:

```python
# Instead of:
try:
    from .models import AgentMessage
except ImportError:
    from models import AgentMessage  # type: ignore

# Use:
from .models import AgentMessage
```

### Phase 3: Remove Fallback Complexity
Eliminate relative import fallbacks by ensuring proper package structure.

### Phase 4: Implement Lazy Loading
For heavy optional dependencies, implement lazy loading patterns.

---
**Generated:** cdd01ef066bc6cf2
