# ADR 002: Blockchain-Backed Audit Trail

## Status
Accepted

## Context
Agent actions in a governance system must be immutable and verifiable by external third parties. Traditional centralized logs are susceptible to tampering or accidental deletion.

## Decision
We will integrate a decentralized audit backend:
1. **Data Structure**: Use Merkle Trees to batch agent actions.
2. **Persistence**: Commit Merkle Roots to the Solana blockchain (main) with Avalanche as a secondary/high-throughput option.
3. **Privacy**: Use Zero-Knowledge Proofs (ZKP) to prove that a specific action was valid without revealing the full content of the message on-chain.

## Consequences
- **Positive**: Cryptographic proof of every decision.
- **Positive**: High resistance to internal data breaches.
- **Negative**: Latency in finality (mitigated by local batching).
- **Negative**: Operational cost (gas fees) associated with chain commits.
