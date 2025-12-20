# ADR 003: Constitutional AI Governance Integration

## Status
Accepted

## Context
Autonomous agents can exhibit unpredictable behavior that violates safety or legal guidelines. Hard-coded rules are too brittle for LLM-driven agents.

## Decision
We will implement "Constitutional'AI" as the primary governance mechanism:
1. **The Constitution**: A versioned document containing high-level principles (e.g., "Do not authorize payments >$10k without human approval").
2. **Impact Scoring**: Use semantic models (BERT) to score the intent of agent messages.
3. **Deliberation Layer**: Intercept messages that exceed safety thresholds and route them for further scrutiny (HITL or Multi-agent consensus).

## Consequences
- **Positive**: Flexible, intent-based safety enforcement.
- **Positive**: Prevents "breakout" scenarios where agents bypass hard-coded filters.
- **Negative**: Adds latency to high-risk decisions.
- **Negative**: Semantic scoring can have false positives/negatives.
