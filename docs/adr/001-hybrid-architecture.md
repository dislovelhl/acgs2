# ADR 001: Hybrid Rust/Python Architecture for Agent Bus

## Status
Accepted

## Context
ACGS-2 requires both high developer accessibility (Python) and extreme message processing throughput (Rust). A pure Python implementation struggles with the computational overhead of constitutional validation at scale, while a pure Rust implementation increases the barrier for agent development.

## Decision
We will implement a hybrid architecture:
1. **Core Processing Engine**: Written in Rust for validating constitutional hashes and high-frequency message routing.
2. **Agent SDK & Orchestration**: Written in Python to provide a rich, async-first experience for developers.
3. **Integration**: Use PyO3 or C-bindings to expose the Rust engine as a Python module (`enhanced_agent_bus.rust`).

## Consequences
- **Positive**: 10-100x performance increase in core validation logic.
- **Positive**: Developers can still write agents in pure Python.
- **Negative**: Increased CI/CD complexity (need to build Rust crates).
- **Negative**: Potential memory safety/debugging challenges across the FFI boundary.
