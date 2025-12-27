# ACGS-2 Project Overview

## Purpose
ACGS-2 (Advanced Constitutional Governance System 2) is an enterprise platform implementing constitutional AI governance with formal verification, multi-agent coordination, and real-time performance optimization.

## Constitutional Hash
**`cdd01ef066bc6cf2`** - Required for all operations. Must be included in all message processing and file headers.

## Key Metrics (Production Targets)
- P99 Latency: <5ms (achieved: 1.31ms)
- Throughput: >100 RPS (achieved: 770.4 RPS)
- Cache Hit Rate: >85% (achieved: 95%)
- Constitutional Compliance: 100%

## Core Components
1. **Enhanced Agent Bus** - Core message bus (Python + optional Rust backend)
2. **Deliberation Layer** - AI-powered review system for high-risk decisions
3. **47 Microservices** - Policy Registry, Audit, Search, etc.
4. **OPA Policies** - Rego-based policy enforcement

## Current Status
- Production-ready with comprehensive monitoring
- Python 3.13 migration completed
- 8 ML models deployed (93.1%-100% accuracy)
- Architecture refactoring planned (see todo.md)
