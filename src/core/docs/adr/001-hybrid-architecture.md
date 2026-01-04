# ADR 001: Hybrid Rust/Python Architecture for Agent Bus

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Status
Accepted & Implemented (v2.3.0)

## Date
2025-12-31 (Phase 3.6 confirmed)

## Context
ACGS-2 requires both high developer accessibility (Python) and extreme message processing throughput (Rust). A pure Python implementation struggles with the computational overhead of constitutional validation at scale, while a pure Rust implementation increases the barrier for agent development.

## Decision
Implement hybrid architecture:
1. **Core Processing Engine**: Rust for constitutional hash validation and high-frequency message routing [`enhanced_agent_bus/rust/Cargo.toml`](../enhanced_agent_bus/rust/Cargo.toml).
2. **Agent SDK & Orchestration**: Python for rich async SDK.
3. **Integration**: PyO3 FFI (`pyo3 = "0.22"`) exposes Rust as Python module.

## Consequences

### Positive
- 10-100x performance in validation (Tokio 1.40 async).
- Python SDK accessibility.

### Negative
- CI/CD Rust builds.
- FFI debugging.

### Post Phase 3.6
- Confirmed: PyO3 0.22, Tokio 1.40, ONNX 2.1 integration.
- Modularity: Rust core decoupled via traits.
