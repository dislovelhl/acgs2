# ACGS-2 Workspace Rules — Types, Style, FastAPI Patterns, Errors

## Type system (mandatory)

### Always use project type aliases

Import from `src/core/shared/types.py` instead of using `Any`:

```python
from src.core.shared.types import (
    # JSON types
    JSONDict, JSONValue, JSONList, JSONPrimitive,

    # Agent/Workflow
    AgentID, AgentContext, AgentState, AgentInfo,
    WorkflowID, WorkflowContext, StepResult,

    # Messaging
    MessageID, MessagePayload, MessageHeaders, MessageMetadata,
    EventID, EventData, EventContext,

    # Policy/Governance
    PolicyID, PolicyData, PolicyContext, PolicyDecision,
    ConstitutionalContext, DecisionData, VerificationResult,

    # Auth/Security
    AuthToken, AuthCredentials, TenantID, CorrelationID,

    # Config
    ConfigDict, ConfigValue, EnvVars,

    # Observability
    AuditEntry, LogContext, MetricData, SpanContext,
)
```

### Type hints rules

1. Prefer specific types over `Any` — use `JSONDict`, `JSONValue`, or domain types.
2. Use `TypedDict` for known dictionary shapes (like `AgentInfo`).
3. Use Pydantic models for validated data structures.
4. Use `Protocol` for structural typing (e.g., `SupportsCache`, `SupportsValidation`).
5. Use TypeVars for generic functions: `T`, `ModelT`, `ConfigT`, `ResponseT`.

### When `Any` is acceptable

- Third-party library returns without type stubs.
- Truly dynamic data with unknown structure.
- Generic wrappers where TypeVar doesn't fit.

## Python code style (ruff + black + mypy)

- Line length: 100
- Target version: Python 3.11+

### Imports order (ruff isort)

1. Standard library
2. Third-party
3. First-party (`src`, `shared`, `services`, `enhanced_agent_bus`)

Example:

```python
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.core.shared.types import JSONDict, PolicyID
from src.core.shared.auth import get_current_user
```

## Naming conventions

| Type            | Convention          | Example                               |
| --------------- | ------------------- | ------------------------------------- |
| Classes         | PascalCase          | `PolicyEvaluator`, `AgentMessage`     |
| Functions       | snake_case          | `validate_policy`, `get_agent_status` |
| Constants       | SCREAMING_SNAKE     | `CONSTITUTIONAL_HASH`, `MAX_RETRIES`  |
| Type Aliases    | PascalCase          | `JSONDict`, `PolicyData`              |
| Pydantic Models | PascalCase + suffix | `PolicyRequest`, `AgentResponse`      |

## FastAPI patterns

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])

class PolicyCreate(BaseModel):
    """Create policy request."""
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., description="Policy content in Rego format")
    tenant_id: str | None = None

class PolicyResponse(BaseModel):
    """Policy response model."""
    id: PolicyID
    name: str
    created_at: datetime
    constitutional_hash: str = Field(default="cdd01ef066bc6cf2")

@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy: PolicyCreate,
    current_user: User = Depends(get_current_user),
) -> PolicyResponse:
    """Create a new policy with constitutional validation."""
    # Implementation
```

## Docstrings

```python
def validate_constitutional_compliance(
    message: AgentMessage,
    context: ConstitutionalContext,
) -> VerificationResult:
    """
    Validate message against constitutional governance rules.

    Args:
        message: The agent message to validate.
        context: Constitutional context including hash verification.

    Returns:
        VerificationResult with compliance status and any violations.

    Raises:
        ConstitutionalViolationError: If message violates governance rules.
    """
```

## Common imports (reference)

```python
# FastAPI
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Pydantic
from pydantic import BaseModel, Field, validator, root_validator
from pydantic_settings import BaseSettings

# Async
import asyncio
from typing import AsyncGenerator

# Testing
import pytest
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock, MagicMock, patch

# Project shared
from src.core.shared.types import JSONDict, PolicyID, AgentID, TenantID
from src.core.shared.config.settings import get_settings
from src.core.shared.logging import get_logger
from src.core.shared.metrics import get_metrics
```

## Error handling (reference pattern)

```python
from fastapi import HTTPException, status

class ConstitutionalViolationError(Exception):
    """Raised when an operation violates constitutional governance."""
    def __init__(self, message: str, violations: list[str]):
        self.message = message
        self.violations = violations
        super().__init__(message)

# In endpoint:
try:
    result = await validate_constitutional_compliance(message)
except ConstitutionalViolationError as e:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "constitutional_violation",
            "message": e.message,
            "violations": e.violations,
            "constitutional_hash": "cdd01ef066bc6cf2",
        },
    )
```
