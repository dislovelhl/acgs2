# ADR 003: Constitutional AI Governance Integration

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Status
Accepted & Implemented (v2.3.0)

## Date
2025-12-31 (Phase 3.6 confirmed)

## Context
Autonomous agents require flexible governance beyond hard-coded rules for LLM-driven behaviors.

## Decision
1. **Constitution**: Versioned principles document.
2. **Impact Scoring**: Semantic models (DistilBERT/ONNX).
3. **Deliberation Layer**: Intercept high-impact messages for HITL/multi-agent review.

## Consequences

### Positive
- Intent-based safety.
- Prevents breakout scenarios.

### Negative
- Latency for high-risk.
- Scoring false positives.

### Post Phase 3.6
- Aligned with agent bus refactors.
- New validators/exceptions integrated.
- OPA enhancements pending Phase 3.7.