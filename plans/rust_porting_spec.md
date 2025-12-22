# Technical Specification: Porting Deliberation Layer, Security, and Audit to Rust

## 1. Overview
This specification outlines the porting of the ACGS-2 Deliberation Layer, Prompt Injection Detection, and Audit Reporting from Python to Rust. The goal is to achieve governance parity while leveraging Rust's performance for high-throughput agent communication.

## 2. Core Components to Port

### 2.1 Deliberation Layer (`deliberation.rs`)

#### 2.1.1 Impact Scorer
The `ImpactScorer` must implement multi-dimensional scoring with the following factors:
- **Semantic Score**: Use `ort` (ONNX Runtime) to run DistilBERT embeddings. Compare message content against high-impact keywords using cosine similarity.
- **Permission Score**: Evaluate risk based on requested tools (e.g., `admin`, `transfer`, `delete` are high risk).
- **Volume Score**: Track request rates per agent using a sliding window (e.g., 60 seconds).
- **Context Score**: Evaluate based on time of day (night-time anomalies) and payload values (e.g., transaction amounts > 10,000).
- **Drift Score**: Detect behavioral anomalies by comparing current impact to historical mean per agent.
- **Priority & Type**: Map `MessagePriority` and `MessageType` to impact factors.

**Data Structures:**
```rust
pub struct ScoringConfig {
    pub semantic_weight: f32,
    pub permission_weight: f32,
    pub volume_weight: f32,
    pub context_weight: f32,
    pub drift_weight: f32,
    pub priority_weight: f32,
    pub type_weight: f32,
}

pub struct ImpactScorer {
    config: ScoringConfig,
    onnx_session: Option<ort::Session>,
    tokenizer: Option<tokenizers::Tokenizer>,
    agent_request_rates: DashMap<String, Vec<DateTime<Utc>>>,
    agent_impact_history: DashMap<String, Vec<f32>>,
}
```

#### 2.1.2 Adaptive Router
The `AdaptiveRouter` manages dual-path routing and threshold learning.
- **Dual-Path Routing**: Route to "Fast Path" (direct delivery) or "Deliberation Path" (queue for review) based on `impact_threshold`.
- **Learning Mechanism**: Adjust `impact_threshold` based on feedback (False Positives/Negatives).

**Data Structures:**
```rust
pub struct AdaptiveRouter {
    impact_threshold: AtomicF32, // Using atomic for thread-safe updates
    routing_history: DashMap<String, RoutingDecision>,
    performance_metrics: DashMap<String, u64>,
}
```

### 2.2 Security Layer (`security.rs`)

#### 2.2.1 Prompt Injection Detection
Port the regex-based detection from `core.py` to Rust.
- **Patterns**: Include all patterns from `PROMPT_INJECTION_PATTERNS`.
- **Optimization**: Use `once_cell` or `lazy_static` for pre-compiled regex.

### 2.3 Audit Layer (`audit.rs`)

#### 2.3.1 Audit Client
Asynchronous reporting of validation results and decisions.
- **Transport**: Use `reqwest` for HTTP reporting.
- **Performance**: Implement a non-blocking buffer/channel to ensure audit reporting doesn't slow down the fast path.

## 3. External Dependencies (Rust)
- `ort`: ONNX Runtime for BERT embeddings.
- `tokenizers`: HuggingFace tokenizers for text processing.
- `dashmap`: Concurrent hash maps for thread-safe state management.
- `reqwest`: Async HTTP client for audit reporting.
- `serde` / `serde_json`: Serialization for messages and logs.
- `chrono`: Time management for volume and context scoring.
- `regex`: Pattern matching for prompt injection.
- `rayon`: Parallel validation (already used in `lib.rs`).
- `atomic_float`: For thread-safe threshold adjustments.

## 4. Implementation Strategy
1.  **Phase 1: Foundation**: Update `Cargo.toml` with new dependencies.
2.  **Phase 2: Security & Audit**: Refine `security.rs` and `audit.rs` to match Python parity.
3.  **Phase 3: Impact Scorer (Basic)**: Implement multi-dimensional scoring without ONNX first.
4.  **Phase 4: ONNX Integration**: Add `ort` and `tokenizers` for full semantic scoring.
5.  **Phase 5: Adaptive Router**: Implement the feedback loop and threshold learning.
6.  **Phase 6: Integration**: Update `MessageProcessor` in `lib.rs` to use the new components.

## 5. Governance Parity Requirements
- **Constitutional Hash**: All operations must validate against `cdd01ef066bc6cf2`.
- **Decision Logic**: Must match Python's weighted scoring and thresholding exactly to ensure consistent governance across backends.
- **Audit Trail**: Every decision (ALLOW/DENY) must be logged with the same metadata as the Python implementation.
