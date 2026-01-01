# ACGS-2 GPU Acceleration Architecture Comparison

**Constitutional Hash:** cdd01ef066bc6cf2
**Date:** 2025-12-29
**Status:** Analysis Complete

## Executive Summary

The GPU acceleration work integrates directly into the **Deliberation Layer** of ACGS-2's Enhanced Agent Bus. Analysis shows DistilBERT inference in `ImpactScorer` is the **only compute-bound ML component** warranting GPU acceleration, while all other ACGS-2 ML components are I/O-bound or heuristic-based.

## ACGS-2 ML Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ENHANCED AGENT BUS                                │
│                        (agent_bus.py)                                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  DELIBERATION LAYER                                                 │ │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────┐  │ │
│  │  │  AdaptiveRouter │ │  ImpactScorer   │ │   OPAGuard           │  │ │
│  │  │  - Fast lane    │ │  - DistilBERT   │ │   - Risk scoring     │  │ │
│  │  │  - Deliberation │ │  - Keyword      │ │   - Constitutional   │  │ │
│  │  │  - Threshold    │ │  - ONNX Runtime │ │   - Multi-sig        │  │ │
│  │  └─────────────────┘ └────────┬────────┘ └──────────────────────┘  │ │
│  │                               │                                     │ │
│  │  ┌─────────────────┐ ┌───────▼─────────┐ ┌──────────────────────┐  │ │
│  │  │ MultiApprover   │ │ NEW: Profiling  │ │   LLMAssistant       │  │ │
│  │  │ - Workflow      │ │ - model_profiler│ │   - OpenAI API       │  │ │
│  │  │ - Escalation    │ │ - tensorrt_opt  │ │   - Claude API       │  │ │
│  │  │ - Notification  │ │ - benchmark     │ │   - Fallback logic   │  │ │
│  │  └─────────────────┘ └─────────────────┘ └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────┐ ┌───────────────────┐ ┌─────────────────────┐   │
│  │  ACL Adapters      │ │  Observability    │ │   AI Assistant      │   │
│  │  - OPA Adapter     │ │  - Telemetry      │ │   - NLU             │   │
│  │  - Z3 Adapter      │ │  - Decorators     │ │   - Dialog          │   │
│  │  - Registry        │ │  - Timeout Budget │ │   - Context         │   │
│  └────────────────────┘ └───────────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## ML Components Analysis

### 1. ImpactScorer (GPU ACCELERATION TARGET)
**Location:** `deliberation_layer/impact_scorer.py`
**ML Backend:** DistilBERT (distilbert-base-uncased)
**Purpose:** Calculate semantic similarity for message impact routing

| Metric | Value | Bottleneck | GPU Benefit |
|--------|-------|------------|-------------|
| P99 Latency | 25.24ms | Compute-bound | **YES - TensorRT** |
| CPU Usage | 798.6% | 8 cores saturated | GPU offload |
| Inference Type | Transformer | Dense GEMM ops | CUDA cores |

**New GPU Infrastructure:**
- `profiling/model_profiler.py` - GPU decision analyzer
- `profiling/benchmark_gpu_decision.py` - Load testing
- `deliberation_layer/tensorrt_optimizer.py` - ONNX/TensorRT pipeline
- `deliberation_layer/optimized_models/distilbert_base_uncased.onnx` - Exported model

### 2. OPAGuard Risk Scoring
**Location:** `deliberation_layer/opa_guard.py`
**ML Backend:** Rule-based heuristics
**Purpose:** Constitutional compliance and risk assessment

| Metric | Value | Bottleneck | GPU Benefit |
|--------|-------|------------|-------------|
| P99 Latency | <1ms | I/O-bound | **NO** |
| CPU Usage | <5% | Waiting on network | N/A |
| Inference Type | Heuristic | Simple rules | CPU optimal |

**Key Methods:**
- `_calculate_risk_score()` - Heuristic risk calculation
- `_determine_risk_level()` - Threshold-based classification
- `_identify_risk_factors()` - Pattern matching

### 3. AdaptiveRouter
**Location:** `deliberation_layer/adaptive_router.py`
**ML Backend:** Threshold-based routing with ImpactScorer
**Purpose:** Fast lane vs deliberation path routing

| Metric | Value | Bottleneck | GPU Benefit |
|--------|-------|------------|-------------|
| P99 Latency | <0.1ms | None | **NO** |
| CPU Usage | <1% | Negligible | N/A |
| Inference Type | Threshold | Simple comparison | CPU optimal |

**Key Methods:**
- `route_message()` - Routes based on impact score threshold
- `_route_to_fast_lane()` - Low-impact path
- `_route_to_deliberation()` - High-impact path requiring review

### 4. LLMAssistant
**Location:** `deliberation_layer/llm_assistant.py`
**ML Backend:** External LLM APIs (OpenAI/Claude)
**Purpose:** Message analysis, decision reasoning, trend analysis

| Metric | Value | Bottleneck | GPU Benefit |
|--------|-------|------------|-------------|
| P99 Latency | 500-2000ms | Network-bound | **NO** |
| CPU Usage | <5% | Waiting on API | N/A |
| Inference Type | Remote API | LLM providers | External GPU |

**Key Methods:**
- `analyze_message_impact()` - LLM-based impact analysis
- `generate_decision_reasoning()` - Explainable AI
- `_fallback_analysis()` - Rule-based when API unavailable

### 5. MultiApprover Workflow
**Location:** `deliberation_layer/multi_approver.py`
**ML Backend:** None (pure orchestration)
**Purpose:** Multi-signature approval workflows

| Metric | Value | Bottleneck | GPU Benefit |
|--------|-------|------------|-------------|
| P99 Latency | <1ms | None | **NO** |
| CPU Usage | <1% | Event-driven | N/A |
| Inference Type | State machine | Workflow engine | CPU optimal |

## GPU Integration Architecture

### Current State (CPU-Only)
```
Message → ImpactScorer (DistilBERT on CPU, 25ms)
       → AdaptiveRouter (threshold check, <0.1ms)
       → OPAGuard (risk calculation, <1ms)
       → LLMAssistant (API call, 500ms+)
       → MultiApprover (workflow, <1ms)
```

### Target State (GPU-Accelerated)
```
Message → ImpactScorer (TensorRT on GPU, <5ms) ← GPU ACCELERATED
       → AdaptiveRouter (threshold check, <0.1ms)
       → OPAGuard (risk calculation, <1ms)
       → LLMAssistant (API call, 500ms+)
       → MultiApprover (workflow, <1ms)
```

## Integration Points

### 1. ImpactScorer GPU Integration
```python
# Current (CPU)
from transformers import AutoModel, AutoTokenizer
self.model = AutoModel.from_pretrained(model_name)
embeddings = self.model(**inputs).last_hidden_state.mean(dim=1)

# Future (GPU with TensorRT)
from .tensorrt_optimizer import TensorRTOptimizer
self.optimizer = TensorRTOptimizer(model_name)
self.optimizer.load_tensorrt_engine()  # or ONNX Runtime fallback
embeddings = self.optimizer.infer(text)
```

### 2. Profiling Integration
```python
# Already integrated into ImpactScorer
from ..profiling import get_global_profiler

with self._get_profiling_context("impact_scorer_distilbert"):
    outputs = self.model(**inputs)
```

### 3. Fallback Chain
```
TensorRT GPU → ONNX Runtime GPU → ONNX Runtime CPU → PyTorch CPU → Keyword Matching
     │              │                   │                  │              │
   <2ms           <5ms               <15ms              ~25ms           <1ms
```

## Performance Comparison Matrix

| Component | Current P99 | Target P99 | GPU Needed | Reason |
|-----------|-------------|------------|------------|--------|
| ImpactScorer (DistilBERT) | 25.24ms | <5ms | **YES** | Compute-bound, 798% CPU |
| ImpactScorer (ONNX) | 39.15ms | <5ms | **YES** | TensorRT optimization |
| ImpactScorer (Keyword) | <1ms | <1ms | NO | Already optimal |
| OPAGuard | <1ms | <1ms | NO | Heuristic-based |
| AdaptiveRouter | <0.1ms | <0.1ms | NO | Simple threshold |
| LLMAssistant | 500-2000ms | 500-2000ms | NO | Network-bound |
| MultiApprover | <1ms | <1ms | NO | Workflow engine |

## Files Created/Modified

### New Files (GPU Infrastructure)
| File | Purpose | LOC |
|------|---------|-----|
| `profiling/__init__.py` | Module exports | 30 |
| `profiling/model_profiler.py` | GPU decision analyzer | 517 |
| `profiling/benchmark_gpu_decision.py` | Benchmark script | 431 |
| `deliberation_layer/tensorrt_optimizer.py` | ONNX/TensorRT pipeline | 600 |
| `deliberation_layer/optimized_models/*.onnx` | Optimized model | - |
| `GPU_ACCELERATION.md` | Documentation | 180 |

### Modified Files (Optimizations)
| File | Changes | Impact |
|------|---------|--------|
| `impact_scorer.py` | Extracted inference methods, nullcontext pattern | 26% code reduction |
| `impact_scorer.py` | Added profiling integration | More accurate metrics |

## Recommendations

### Immediate Actions
1. **Deploy ImpactScorer with TensorRT** on GPU infrastructure
2. **No changes needed** for OPAGuard, AdaptiveRouter, LLMAssistant, MultiApprover
3. **Monitor profiling metrics** via Prometheus for production optimization

### Architecture Alignment
- GPU acceleration is **surgically targeted** at the single compute-bound component
- **Constitutional compliance maintained** - GPU optimization doesn't affect validation logic
- **Fallback chain** ensures system reliability without GPU
- **Profiling infrastructure** enables ongoing optimization decisions

### Production Checklist
- [ ] Deploy to GPU server with CUDA 12.1+
- [ ] Convert ONNX to TensorRT engine
- [ ] Benchmark with production traffic patterns
- [ ] Configure Prometheus GPU metrics
- [ ] Update ImpactScorer to use GPU backend

## Constitutional Compliance

All GPU acceleration code maintains ACGS-2 constitutional hash verification:
```
Constitutional Hash: cdd01ef066bc6cf2
```

GPU optimization affects **inference performance only**, not constitutional validation logic.

---

*This architecture comparison demonstrates surgical GPU optimization targeting only the compute-bound DistilBERT inference while preserving the integrity of ACGS-2's constitutional governance framework.*
