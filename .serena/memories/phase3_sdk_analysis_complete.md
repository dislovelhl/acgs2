# Phase 3: SDK Model Analysis - Complete

## Constitutional Hash: cdd01ef066bc6cf2

## Date: 2025-01-20

## Summary

Analyzed the SDK models for alleged "duplication" with internal models. Conclusion: **No consolidation needed** - the separation is intentional architectural design.

## Analysis Findings

### SDK Architecture (Intentionally Standalone)

The `sdk/python/acgs2_sdk` package is designed to be distributed via PyPI as a standalone package for external users. It has **no dependencies** on internal ACGS-2 modules.

**SDK Dependencies (from pyproject.toml):**
- httpx>=0.25.0
- pydantic>=2.5.0
- websockets>=12.0
- tenacity>=8.2.0

**No internal dependencies:** The SDK doesn't import from `shared/`, `enhanced_agent_bus/`, or any internal modules.

### Model Differences (By Design)

| Aspect | SDK Models | Internal Models |
|--------|------------|-----------------|
| Framework | Pydantic (validation) | dataclasses (performance) |
| Purpose | External API contracts | Internal processing |
| Distribution | PyPI package | Part of monorepo |
| Users | External developers | Internal services |

### CONSTITUTIONAL_HASH Duplication

The SDK has its own `constants.py` with `CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"`. This is **correct** because:
1. SDK cannot import from internal `shared/constants.py`
2. SDK must be self-contained for external distribution
3. Both values must match for constitutional compliance

### Enum Differences

**MessageType:**
- SDK: COMMAND, QUERY, EVENT, RESPONSE, ERROR
- Internal: Adds GOVERNANCE_REQUEST, GOVERNANCE_RESPONSE, CONSTITUTIONAL_VALIDATION, TASK_REQUEST, TASK_RESPONSE

**Priority:**
- SDK: Uses string values ("critical", "high", "normal", "low")
- Internal: Uses int values (0, 1, 2, 3)

These differences are acceptable since the SDK communicates via HTTP/JSON where string enums are more interoperable.

## Recommendation

**No changes needed.** The current architecture correctly separates:
- External API client (SDK with Pydantic)
- Internal processing (enhanced_agent_bus with dataclasses)

## Future Consideration

If synchronization becomes an issue, consider:
1. A shared schema definition (e.g., OpenAPI spec)
2. Code generation for SDK models from internal definitions
3. CI checks to verify enum/constant consistency

## Files Reviewed

- `/sdk/python/acgs2_sdk/models.py` - Pydantic models for API
- `/sdk/python/acgs2_sdk/constants.py` - SDK-specific constants
- `/sdk/python/pyproject.toml` - SDK configuration (standalone)
- `/enhanced_agent_bus/models.py` - Internal dataclass models
- `/shared/constants.py` - Canonical constants source
