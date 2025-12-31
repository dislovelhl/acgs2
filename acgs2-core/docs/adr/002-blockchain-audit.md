# ADR 002: Blockchain-Anchored Audit Trails

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Status
Accepted & Implemented (v2.3.0)

## Date
2025-12-31 (Phase 3.6 confirmed)

## Context
Agent actions must be immutable and verifiable. Centralized logs vulnerable to tampering.

## Decision
1. **Merkle Trees**: Batch actions.
2. **Anchoring**: Solana mainnet (primary), PostgreSQL metadata.
3. **Privacy**: ZKP proofs for validation without content disclosure.

## Consequences

### Positive
- Cryptographic non-repudiation.
- Breach-resistant audits.

### Negative
- Commit latency (batched).
- Gas costs.

### Post Phase 3.6
- Integrated with enhanced agent bus refactors.
- AuditClient API optimized, dead code removed.