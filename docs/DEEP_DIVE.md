# ACGS-2 Deep-Dive Documentation

This document provides a comprehensive technical guide to the ACGS-2 repository, focusing on its core architecture, security mechanisms, and governance frameworks.

## 1. Core Architecture: Enhanced Agent Bus

The **Enhanced Agent Bus** is the central backbone of the ACGS-2 system, facilitating secure and governed communication between agents.

### 1.1 Message Processing Engine (`MessageProcessor`)

The `MessageProcessor` orchestrates the validation and routing of messages. It employs several key design patterns:

- **Strategy Pattern**: Selects between Python, Rust, and OPA-based processing strategies based on environment and performance requirements.
- **Composite Pattern**: Allows combining multiple validation and processing steps into a single workflow.
- **Circuit Breaker**: Implements resiliency by preventing system overload upon repeated failures.

### 1.2 Performance Optimization (`rust-perf`)

Performance-critical operations are offloaded to Rust extensions (`acgs2_perf`):

- **Sinkhorn-Knopp Projection**: Stabilizes consensus matrices by ensuring they are doubly stochastic.
- **Fast Hashing/Checksums**: Optimized FNV-1a and additive checksums for cache keys and integrity checks.
- **Batch Operations**: Faster string normalization and filtering than equivalent Python code.

## 2. Governance: CCAI Democratic Framework

The **Collective Constitutional AI (CCAI)** framework implements Challenge 5: Democratic AI Governance.

### 2.1 Polis-Style Deliberation

The system uses a democratic deliberation engine:

- **Opinion Clustering**: PCA and K-Means clustering identify distinct stakeholder viewpoints.
- **Cross-Group Consensus**: Prevents polarization by requiring agreement across diverse stakeholder groups (Technical, Ethical, User, etc.).
- **Stability Layer (mHC)**: Uses Manifold-Constrained HyperConnections to ensure mathematical stability in consensus aggregation, capped to prevent single-group dominance.

### 2.2 SDPC (Self-Developing Policy Control)

Integrated into the message hot path, SDPC provides:

- **ASC (Automated Semantic Check)**: Validates statements against constitutional requirements.
- **Graph-Grounding**: Verifies information against a knowledge graph.
- **PACAR (Proactive Autonomous Conflict Resolution)**: Resolves conflicts in multi-agent tasks.

## 3. Security and Compliance

### 3.1 Multi-Tenant Isolation

Strict isolation is maintained via the `TenantValidator`, which enforces normalized, lowercase, and strictly formatted tenant IDs.

### 3.2 Prompt Injection Detection

The `PromptInjectionDetector` uses a multi-layered approach:

- **Core Patterns**: Regex-based detection for common injection techniques.
- **Semantic Analysis**: Advanced severity-based classification.
- **Sanitization**: Automatic filtering of dangerous instruction overrides.

### 3.3 Authorization (OPA)

Open Policy Agent (OPA) is used for fine-grained authorization, hardcoded to **fail-closed** for maximum security.

## 4. Configuration Management

Configuration is managed via a unified, Pydantic-based system in `src/core/shared/config/unified.py`. It includes:

- **Environment-Specific Validation**: Blocks security risks like wildcard CORS in production.
- **Credential Safety**: Ensures sensitive keys meet minimum strength requirements and are not left as placeholders.
