# Split Large adaptive_governance.py into Domain Modules

## Overview

The file src/core/enhanced_agent_bus/adaptive_governance.py has grown to 1768 lines and handles multiple responsibilities: impact scoring, threshold management, governance decisions, model training, and feedback handling. This violates the Single Responsibility Principle and makes the code difficult to navigate, test, and maintain.

## Rationale

Very large files increase cognitive load, make code reviews harder, and often lead to merge conflicts. Smaller, focused modules are easier to test, maintain, and reason about. The file currently contains at least 5 major classes that could be separate modules.

---
*This spec was created from ideation and is pending detailed specification.*
